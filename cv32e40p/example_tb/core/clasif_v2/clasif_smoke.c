// Test dirigido del clasificador v2 (DISENO_CLASIFICADOR_V2.md).
//
// Toda la región medida vive en UN solo bloque asm volatile para que el
// compilador no inserte instrucciones entre el reset y la lectura de los
// contadores. Los operandos entran como inputs del bloque (se cargan antes
// del reset, fuera de la región medida).
//
// Conteos esperados (arquitecturales, región medida):
//   ALU   = 12  (10 ops ALU + 2 branches no tomados)
//   MUL   = 5
//   MULH  = 7   (3 mulh + 2 mulhu + 2 mulhsu)
//   DIV   = 6
//   MEM   = 8   (4 sw + 4 lw)
//   CTRL  = 5   (2 jal + 3 branches tomados)
//   FLOAT = 0
//   DIVCYC: rango sano [2*6, 40*6]
// Filtradas (no cuentan): 16 csrw reset, 2 fence, 2 csrr mcycle, lecturas.

#include <stdint.h>
#include <stdio.h>

static volatile uint32_t buf[4];
static volatile uint32_t out[8];

int main(void) {
  uint32_t big = 0x7FFFFFFFu;
  uint32_t one = 1u;
  uint32_t smalld = 3u;
  uint32_t divisor = 0x40000u;

  asm volatile(
      // ===== RESET de los 16 CSR (filtrado: csr_access) =====
      "csrw 0xBC0, x0\n csrw 0xBC1, x0\n csrw 0xBC2, x0\n csrw 0xBC3, x0\n"
      "csrw 0xBC4, x0\n csrw 0xBC5, x0\n csrw 0xBC6, x0\n csrw 0xBC7, x0\n"
      "csrw 0xBC8, x0\n csrw 0xBC9, x0\n csrw 0xBCA, x0\n csrw 0xBCB, x0\n"
      "csrw 0xBCC, x0\n csrw 0xBCD, x0\n csrw 0xBCE, x0\n csrw 0xBCF, x0\n"

      // ===== ALU simple: 10 =====
      "addi t0, zero, 1\n addi t0, t0, 1\n addi t0, t0, 1\n addi t0, t0, 1\n"
      "add  t1, t0, t0\n add  t1, t1, t0\n add  t1, t1, t0\n"
      "xor  t2, t0, t1\n"
      "slli t3, t0, 2\n"
      "sltu t4, t0, t1\n"

      "fence\n"                       // filtrada (system)

      // ===== MUL: 5 =====
      "mul t1, t0, t0\n mul t1, t1, t0\n mul t1, t1, t0\n"
      "mul t2, t0, t1\n mul t2, t2, t0\n"

      // ===== MULH: 7 =====
      "mulh   t3, %[big], %[big]\n mulh   t3, t3, %[big]\n mulh t3, t3, t3\n"
      "mulhu  t4, %[big], %[big]\n mulhu  t4, t4, %[big]\n"
      "mulhsu t5, %[big], %[big]\n mulhsu t5, t5, %[big]\n"

      "csrr a6, 0xB00\n"              // mcycle, filtrada (csr_access)

      // ===== DIV: 6 (operandos variados para DIVCYC) =====
      "div  t6, %[big],    %[one]\n"
      "divu t6, %[big],    %[one]\n"
      "div  t6, %[smalld], %[divisor]\n"
      "divu t6, %[smalld], %[divisor]\n"
      "rem  t6, %[big],    %[divisor]\n"
      "remu t6, %[smalld], %[one]\n"

      // ===== MEM: 8 (4 sw + 4 lw) =====
      "sw %[big],    0(%[buf])\n sw %[one],  4(%[buf])\n"
      "sw %[smalld], 8(%[buf])\n sw %[divisor], 12(%[buf])\n"
      "lw t0, 0(%[buf])\n lw t1, 4(%[buf])\n"
      "lw t2, 8(%[buf])\n lw t3, 12(%[buf])\n"

      "fence\n"                       // filtrada (system)

      // ===== CTRL/branches: 3 tomados + 2 no tomados + 2 jal =====
      // tomados saltan sobre un addi (que se anula y NO debe contarse)
      "beq zero, zero, 1f\n addi t5, zero, 0\n1:\n"
      "beq zero, zero, 2f\n addi t5, zero, 0\n2:\n"
      "bne zero, zero, 3f\n3:\n"      // no tomado -> ALU
      "beq %[one], zero, 4f\n4:\n"    // no tomado -> ALU
      "beq zero, zero, 5f\n addi t5, zero, 0\n5:\n"
      "jal a7, 6f\n6:\n"
      "jal a7, 7f\n7:\n"

      "csrr a6, 0xB00\n"              // mcycle, filtrada

      // ===== LECTURA (filtrada) y volcado =====
      "csrr t0, 0xBC0\n"              // ALU
      "csrr t1, 0xBC2\n"              // MUL
      "csrr t2, 0xBC4\n"              // MULH
      "csrr t3, 0xBC6\n"              // DIV
      "csrr t4, 0xBC8\n"              // MEM
      "csrr t5, 0xBCA\n"              // CTRL
      "csrr t6, 0xBCC\n"              // FLOAT
      "csrr a6, 0xBCE\n"              // DIVCYC
#ifdef WAVES_HOLD
      // Modo ondas (GUI): dormir el core aquí mismo, igual que el viejo
      // category_counter_freeze.c. Nada más ejecuta: los contadores quedan
      // congelados en sus valores finales hasta el fin de la simulación.
      "wfi\n"
      "9: j 9b\n"
#endif
      "sw t0,  0(%[out])\n sw t1,  4(%[out])\n"
      "sw t2,  8(%[out])\n sw t3, 12(%[out])\n"
      "sw t4, 16(%[out])\n sw t5, 20(%[out])\n"
      "sw t6, 24(%[out])\n sw a6, 28(%[out])\n"
      :
      : [big] "r"(big), [one] "r"(one), [smalld] "r"(smalld),
        [divisor] "r"(divisor), [buf] "r"(buf), [out] "r"(out)
      : "t0", "t1", "t2", "t3", "t4", "t5", "t6", "a6", "a7", "memory");

  printf("CLASIF alu=%u mul=%u mulh=%u div=%u mem=%u ctrl=%u float=%u divcyc=%u\n",
         (unsigned)out[0], (unsigned)out[1], (unsigned)out[2], (unsigned)out[3],
         (unsigned)out[4], (unsigned)out[5], (unsigned)out[6], (unsigned)out[7]);

  printf("EXPECTED alu=12 mul=5 mulh=7 div=6 mem=8 ctrl=5 float=0\n");
  return 0;
}
