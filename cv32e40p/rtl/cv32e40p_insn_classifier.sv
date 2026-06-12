// Instruction-category counters for CV32E40P.
//
// The counters are intentionally independent from the standard HPM counters:
// firmware can reset/read one category without reprogramming mhpmevent CSRs.

module cv32e40p_insn_classifier
  import cv32e40p_pkg::*;
(
    input logic clk_i,
    input logic rst_ni,

    input logic        retire_i,
    input logic        load_i,
    input logic        store_i,
    input logic        jump_i,
    input logic        branch_i,
    input logic        alu_en_i,
    input alu_opcode_e alu_operator_i,
    input logic        mult_en_i,
    input logic        apu_en_i,
    input logic        csr_access_i,

    input csr_num_e    csr_addr_i,
    input csr_opcode_e csr_op_i,
    input logic [31:0] csr_wdata_i,
    output logic       csr_hit_o,
    output logic [31:0] csr_rdata_o
);

  logic [63:0] arithmetic_q;
  logic [63:0] logic_q;
  logic [63:0] memory_q;
  logic [63:0] branch_q;
  logic [63:0] jump_q;
  logic [63:0] floating_q;

  logic csr_write;
  logic memory_insn;
  logic non_alu_category;
  logic alu_arithmetic;
  logic alu_logic;

  assign memory_insn      = load_i | store_i;
  assign non_alu_category = memory_insn | branch_i | jump_i | apu_en_i;

  always_comb begin
    alu_arithmetic = 1'b0;
    alu_logic      = 1'b0;

    unique case (alu_operator_i)
      ALU_ADD, ALU_SUB, ALU_ADDU, ALU_SUBU, ALU_ADDR, ALU_SUBR, ALU_ADDUR, ALU_SUBUR,
      ALU_LTS, ALU_LTU, ALU_LES, ALU_LEU, ALU_GTS, ALU_GTU, ALU_GES, ALU_GEU, ALU_EQ,
      ALU_NE, ALU_SLTS, ALU_SLTU, ALU_SLETS, ALU_SLETU, ALU_ABS, ALU_CLIP, ALU_CLIPU,
      ALU_MIN, ALU_MINU, ALU_MAX, ALU_MAXU, ALU_DIVU, ALU_DIV, ALU_REMU, ALU_REM:
      alu_arithmetic = 1'b1;

      ALU_XOR, ALU_OR, ALU_AND, ALU_SRA, ALU_SRL, ALU_ROR, ALU_SLL, ALU_BEXT, ALU_BEXTU,
      ALU_BINS, ALU_BCLR, ALU_BSET, ALU_BREV, ALU_FF1, ALU_FL1, ALU_CNT, ALU_CLB, ALU_EXTS,
      ALU_EXT, ALU_INS, ALU_SHUF, ALU_SHUF2, ALU_PCKLO, ALU_PCKHI:
      alu_logic = 1'b1;

      default: begin
        alu_arithmetic = 1'b0;
        alu_logic      = 1'b0;
      end
    endcase
  end

  always_comb begin
    csr_hit_o   = 1'b1;
    csr_rdata_o = 32'h0;

    unique case (csr_addr_i)
      CSR_CAT_ARITH_LO:  csr_rdata_o = arithmetic_q[31:0];
      CSR_CAT_ARITH_HI:  csr_rdata_o = arithmetic_q[63:32];
      CSR_CAT_LOGIC_LO:  csr_rdata_o = logic_q[31:0];
      CSR_CAT_LOGIC_HI:  csr_rdata_o = logic_q[63:32];
      CSR_CAT_MEMORY_LO: csr_rdata_o = memory_q[31:0];
      CSR_CAT_MEMORY_HI: csr_rdata_o = memory_q[63:32];
      CSR_CAT_BRANCH_LO: csr_rdata_o = branch_q[31:0];
      CSR_CAT_BRANCH_HI: csr_rdata_o = branch_q[63:32];
      CSR_CAT_JUMP_LO:   csr_rdata_o = jump_q[31:0];
      CSR_CAT_JUMP_HI:   csr_rdata_o = jump_q[63:32];
      CSR_CAT_FLOAT_LO:  csr_rdata_o = floating_q[31:0];
      CSR_CAT_FLOAT_HI:  csr_rdata_o = floating_q[63:32];
      default: begin
        csr_hit_o   = 1'b0;
        csr_rdata_o = 32'h0;
      end
    endcase
  end

  assign csr_write = csr_hit_o && (csr_op_i != CSR_OP_READ);

  always_ff @(posedge clk_i, negedge rst_ni) begin
    if (!rst_ni) begin
      arithmetic_q <= 64'h0;
      logic_q      <= 64'h0;
      memory_q     <= 64'h0;
      branch_q     <= 64'h0;
      jump_q       <= 64'h0;
      floating_q   <= 64'h0;
    end else begin
      if (retire_i && !csr_access_i) begin
        if (memory_insn) begin
          memory_q <= memory_q + 64'd1;
        end else if (branch_i) begin
          branch_q <= branch_q + 64'd1;
        end else if (jump_i) begin
          jump_q <= jump_q + 64'd1;
        end else if (apu_en_i) begin
          floating_q <= floating_q + 64'd1;
        end else if (mult_en_i || (alu_en_i && alu_arithmetic)) begin
          arithmetic_q <= arithmetic_q + 64'd1;
        end else if (alu_en_i && alu_logic && !non_alu_category) begin
          logic_q <= logic_q + 64'd1;
        end
      end

      if (csr_write) begin
        unique case (csr_addr_i)
          CSR_CAT_ARITH_LO:  arithmetic_q[31:0]  <= csr_wdata_i;
          CSR_CAT_ARITH_HI:  arithmetic_q[63:32] <= csr_wdata_i;
          CSR_CAT_LOGIC_LO:  logic_q[31:0]       <= csr_wdata_i;
          CSR_CAT_LOGIC_HI:  logic_q[63:32]      <= csr_wdata_i;
          CSR_CAT_MEMORY_LO: memory_q[31:0]      <= csr_wdata_i;
          CSR_CAT_MEMORY_HI: memory_q[63:32]     <= csr_wdata_i;
          CSR_CAT_BRANCH_LO: branch_q[31:0]      <= csr_wdata_i;
          CSR_CAT_BRANCH_HI: branch_q[63:32]     <= csr_wdata_i;
          CSR_CAT_JUMP_LO:   jump_q[31:0]        <= csr_wdata_i;
          CSR_CAT_JUMP_HI:   jump_q[63:32]       <= csr_wdata_i;
          CSR_CAT_FLOAT_LO:  floating_q[31:0]    <= csr_wdata_i;
          CSR_CAT_FLOAT_HI:  floating_q[63:32]   <= csr_wdata_i;
          default: ;
        endcase
      end
    end
  end

endmodule
