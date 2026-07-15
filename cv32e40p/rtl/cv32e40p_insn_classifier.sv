// Clasificador de instrucciones v2 — categorías por unidad activa.
//
// 7 contadores de instrucciones retiradas + 1 contador de ciclos de
// ocupación del divisor (DIV_CYC), expuestos como 16 CSR (0xBC0-0xBCF)
// en pares LO/HI. Independientes de los HPM estándar: el firmware puede
// leer/resetear una categoría sin reprogramar mhpmevent.
//
// Criterio: categoría = unidad funcional que conmuta. Latencia constante →
// conteo por instrucción; latencia variable por datos (división) → además
// ciclos de ocupación. Branches: no tomado → ALU (solo un compare),
// tomado → CTRL (paga flush/refetch, mismo mecanismo que jal/jalr).

module cv32e40p_insn_classifier
  import cv32e40p_pkg::*;
(
    input logic clk_i,
    input logic rst_ni,

    // Eventos de retiro (flopeados ID->EX en id_stage, ya gateados por minstret)
    input logic        retire_i,        // mhpmevent_minstret
    input logic        load_i,          // mhpmevent_load
    input logic        store_i,         // mhpmevent_store
    input logic        jump_i,          // mhpmevent_jump (jal/jalr)
    input logic        branch_i,        // mhpmevent_branch (cualquier branch)
    input logic        branch_taken_i,  // mhpmevent_branch_taken (1 ciclo después de branch_i)

    // Estado de la instrucción en EX (registros de pipeline ID/EX)
    input logic        alu_en_i,
    input alu_opcode_e alu_operator_i,
    input logic        mult_en_i,
    input mul_opcode_e mult_operator_i,
    input logic        apu_en_i,

    // Filtros: instrucciones que no se cuentan en ninguna categoría
    input logic        csr_access_i,    // csr_access_ex (csrr/csrw/csrs/csrc)
    input logic        system_i,        // mhpmevent_system (mret/uret/dret/wfi/fence)

    // Interfaz CSR (lectura por multiplexor en el core, escritura directa)
    input  csr_num_e    csr_addr_i,
    input  csr_opcode_e csr_op_i,
    input  logic [31:0] csr_wdata_i,
    output logic        csr_hit_o,
    output logic [31:0] csr_rdata_o
);

  // Contadores (instrucciones, salvo divcyc_q = ciclos)
  logic [63:0] alu_q;      // ALU simple + branches no tomados
  logic [63:0] mul_q;      // mul (MAC, 1 ciclo)
  logic [63:0] mulh_q;     // mulh/mulhsu/mulhu (MAC, FSM ~4 ciclos)
  logic [63:0] div_q;      // div/divu/rem/remu (instrucciones)
  logic [63:0] mem_q;      // loads/stores (incl. flw/fsw)
  logic [63:0] ctrl_q;     // jal/jalr + branches tomados
  logic [63:0] float_q;    // cómputo FPU
  logic [63:0] divcyc_q;   // ciclos de ocupación del divisor

  // ---------------------------------------------------------------------
  // Detección por unidad
  // ---------------------------------------------------------------------
  logic memory_insn;
  logic div_op;
  logic is_div;
  logic is_mulh;
  logic is_mul;
  logic count_en;

  assign memory_insn = load_i | store_i;

  always_comb begin
    unique case (alu_operator_i)
      ALU_DIV, ALU_DIVU, ALU_REM, ALU_REMU: div_op = 1'b1;
      default:                              div_op = 1'b0;
    endcase
  end

  assign is_div  = alu_en_i && div_op;
  assign is_mulh = mult_en_i && (mult_operator_i == MUL_H);
  // Catch-all del multiplicador: todo lo que no es MUL_H cuenta como mul
  // (en RV32IMC solo se emite MUL_MAC32; los operadores Xpulp no aparecen)
  assign is_mul  = mult_en_i && (mult_operator_i != MUL_H);

  // Las instrucciones CSR y de sistema no se cuentan (el decoder las deja
  // con alu_en=1/ALU_SLTU por default y contaminarían ALU)
  assign count_en = retire_i && !csr_access_i && !system_i;

  // ---------------------------------------------------------------------
  // Branches: la decisión llega un ciclo después del retiro.
  // branch_i pulsa con la instrucción en EX; branch_taken_i pulsa al ciclo
  // siguiente si fue tomado. Se flopea branch_i para derivar el no-tomado.
  // ---------------------------------------------------------------------
  logic branch_q1;
  logic taken_inc;
  logic not_taken_inc;

  assign taken_inc     = branch_taken_i;
  assign not_taken_inc = branch_q1 && !branch_taken_i;

  // ---------------------------------------------------------------------
  // Incrementos por categoría. Cascada de prioridad:
  //   MEM -> branch (difiere 1 ciclo) -> CTRL/jump -> FLOAT -> DIV -> MULH
  //   -> MUL -> ALU simple
  // Cada contador puede recibir hasta 2 incrementos en el mismo ciclo
  // (el de la instrucción en EX y el de la resolución del branch anterior),
  // por eso se suman aritméticamente.
  // ---------------------------------------------------------------------
  logic mem_inc, jump_inc, float_inc, div_inc, mulh_inc, mul_inc, alu_inc;

  always_comb begin
    mem_inc   = 1'b0;
    jump_inc  = 1'b0;
    float_inc = 1'b0;
    div_inc   = 1'b0;
    mulh_inc  = 1'b0;
    mul_inc   = 1'b0;
    alu_inc   = 1'b0;

    if (count_en) begin
      if (memory_insn) begin
        mem_inc = 1'b1;
      end else if (branch_i) begin
        // se resuelve al ciclo siguiente como taken/not-taken
      end else if (jump_i) begin
        jump_inc = 1'b1;
      end else if (apu_en_i) begin
        float_inc = 1'b1;
      end else if (is_div) begin
        div_inc = 1'b1;
      end else if (is_mulh) begin
        mulh_inc = 1'b1;
      end else if (is_mul) begin
        mul_inc = 1'b1;
      end else if (alu_en_i) begin
        alu_inc = 1'b1;
      end
    end
  end

  // Ciclos de ocupación del divisor: los registros ID/EX retienen el
  // operador DIV durante todo el stall multiciclo, así que basta contar
  // cada ciclo en que EX contiene una división. Las burbujas del pipeline
  // cargan ALU_SLTU y no contaminan. Sin gateo por retire (cuenta ciclos,
  // no instrucciones).
  logic divcyc_inc;
  assign divcyc_inc = is_div;

  // ---------------------------------------------------------------------
  // Interfaz CSR: lectura
  // ---------------------------------------------------------------------
  always_comb begin
    csr_hit_o   = 1'b1;
    csr_rdata_o = 32'h0;

    unique case (csr_addr_i)
      CSR_CAT_ALU_LO:    csr_rdata_o = alu_q[31:0];
      CSR_CAT_ALU_HI:    csr_rdata_o = alu_q[63:32];
      CSR_CAT_MUL_LO:    csr_rdata_o = mul_q[31:0];
      CSR_CAT_MUL_HI:    csr_rdata_o = mul_q[63:32];
      CSR_CAT_MULH_LO:   csr_rdata_o = mulh_q[31:0];
      CSR_CAT_MULH_HI:   csr_rdata_o = mulh_q[63:32];
      CSR_CAT_DIV_LO:    csr_rdata_o = div_q[31:0];
      CSR_CAT_DIV_HI:    csr_rdata_o = div_q[63:32];
      CSR_CAT_MEM_LO:    csr_rdata_o = mem_q[31:0];
      CSR_CAT_MEM_HI:    csr_rdata_o = mem_q[63:32];
      CSR_CAT_CTRL_LO:   csr_rdata_o = ctrl_q[31:0];
      CSR_CAT_CTRL_HI:   csr_rdata_o = ctrl_q[63:32];
      CSR_CAT_FLOAT_LO:  csr_rdata_o = float_q[31:0];
      CSR_CAT_FLOAT_HI:  csr_rdata_o = float_q[63:32];
      CSR_CAT_DIVCYC_LO: csr_rdata_o = divcyc_q[31:0];
      CSR_CAT_DIVCYC_HI: csr_rdata_o = divcyc_q[63:32];
      default: begin
        csr_hit_o   = 1'b0;
        csr_rdata_o = 32'h0;
      end
    endcase
  end

  logic csr_write;
  assign csr_write = csr_hit_o && (csr_op_i != CSR_OP_READ);

  // ---------------------------------------------------------------------
  // Registros
  // ---------------------------------------------------------------------
  always_ff @(posedge clk_i, negedge rst_ni) begin
    if (!rst_ni) begin
      alu_q     <= 64'h0;
      mul_q     <= 64'h0;
      mulh_q    <= 64'h0;
      div_q     <= 64'h0;
      mem_q     <= 64'h0;
      ctrl_q    <= 64'h0;
      float_q   <= 64'h0;
      divcyc_q  <= 64'h0;
      branch_q1 <= 1'b0;
    end else begin
      branch_q1 <= count_en && branch_i;

      // ALU y CTRL pueden recibir 2 incrementos el mismo ciclo (instrucción
      // actual + resolución del branch del ciclo anterior)
      alu_q    <= alu_q + {63'b0, alu_inc} + {63'b0, not_taken_inc};
      ctrl_q   <= ctrl_q + {63'b0, jump_inc} + {63'b0, taken_inc};
      mem_q    <= mem_q + {63'b0, mem_inc};
      mul_q    <= mul_q + {63'b0, mul_inc};
      mulh_q   <= mulh_q + {63'b0, mulh_inc};
      div_q    <= div_q + {63'b0, div_inc};
      float_q  <= float_q + {63'b0, float_inc};
      divcyc_q <= divcyc_q + {63'b0, divcyc_inc};

      // Escritura CSR (prioridad sobre el conteo del mismo ciclo, igual que v1)
      if (csr_write) begin
        unique case (csr_addr_i)
          CSR_CAT_ALU_LO:    alu_q[31:0]      <= csr_wdata_i;
          CSR_CAT_ALU_HI:    alu_q[63:32]     <= csr_wdata_i;
          CSR_CAT_MUL_LO:    mul_q[31:0]      <= csr_wdata_i;
          CSR_CAT_MUL_HI:    mul_q[63:32]     <= csr_wdata_i;
          CSR_CAT_MULH_LO:   mulh_q[31:0]     <= csr_wdata_i;
          CSR_CAT_MULH_HI:   mulh_q[63:32]    <= csr_wdata_i;
          CSR_CAT_DIV_LO:    div_q[31:0]      <= csr_wdata_i;
          CSR_CAT_DIV_HI:    div_q[63:32]     <= csr_wdata_i;
          CSR_CAT_MEM_LO:    mem_q[31:0]      <= csr_wdata_i;
          CSR_CAT_MEM_HI:    mem_q[63:32]     <= csr_wdata_i;
          CSR_CAT_CTRL_LO:   ctrl_q[31:0]     <= csr_wdata_i;
          CSR_CAT_CTRL_HI:   ctrl_q[63:32]    <= csr_wdata_i;
          CSR_CAT_FLOAT_LO:  float_q[31:0]    <= csr_wdata_i;
          CSR_CAT_FLOAT_HI:  float_q[63:32]   <= csr_wdata_i;
          CSR_CAT_DIVCYC_LO: divcyc_q[31:0]   <= csr_wdata_i;
          CSR_CAT_DIVCYC_HI: divcyc_q[63:32]  <= csr_wdata_i;
          default: ;
        endcase
      end
    end
  end

endmodule
