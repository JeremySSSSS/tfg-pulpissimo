// Regresión pseudoaleatoria del clasificador v2.
//
// Mezcla las 6 categorías enteras en orden IMPREDECIBLE (xorshift32 con
// semilla fija -> reproducible), con operandos de división aleatorios.
// Cubre lo que los bucles dominados no ejercitan: las TRANSICIONES entre
// categorías (cascada cambiando de rama ciclo a ciclo, branches del
// despachador mezclados con los de la carga, divisiones intercaladas).
//
// No hay conteo esperado fijo: la verdad la pone el golden model sobre el
// trace (por eso, a diferencia de clasif_smoke, la región medida puede ser
// C normal: lo que inserte el compilador también se retira y también se
// clasifica). FLOAT queda en 0 (el tb se elabora con FPU=0).
//
// Uso:  TEST=clasif_v2/clasif_rand [SKIPRTL=1] ./run_clasif_v2_xsim.sh

#include <stdint.h>
#include <stdio.h>

#define SEED  0xC0FFEE01u
#define ITERS 1500u

static volatile uint32_t buf[8];
static volatile uint32_t out[8];

static inline uint32_t xorshift32(uint32_t *s) {
  uint32_t x = *s;
  x ^= x << 13;
  x ^= x >> 17;
  x ^= x << 5;
  *s = x;
  return x;
}

int main(void) {
  uint32_t rng = SEED;

  // ===== RESET de los 16 CSR (filtrado: csr_access). Desde aquí y hasta
  // la lectura, TODO lo que se retire cuenta (también el código del
  // despachador que genere el compilador).
  asm volatile(
      "csrw 0xBC0, x0\n csrw 0xBC1, x0\n csrw 0xBC2, x0\n csrw 0xBC3, x0\n"
      "csrw 0xBC4, x0\n csrw 0xBC5, x0\n csrw 0xBC6, x0\n csrw 0xBC7, x0\n"
      "csrw 0xBC8, x0\n csrw 0xBC9, x0\n csrw 0xBCA, x0\n csrw 0xBCB, x0\n"
      "csrw 0xBCC, x0\n csrw 0xBCD, x0\n csrw 0xBCE, x0\n csrw 0xBCF, x0\n"
      ::: "memory");

  for (uint32_t i = 0; i < ITERS; i++) {
    uint32_t r = xorshift32(&rng);
    uint32_t a = xorshift32(&rng);
    uint32_t b = xorshift32(&rng) | 1u;   // divisor nunca cero

    switch (r % 6u) {
      case 0:  // ALU simple
        asm volatile("add  t0, %0, %1\n xor t1, t0, %0\n"
                     "slli t2, t1, 3\n  sltu t3, t2, %1\n"
                     :: "r"(a), "r"(b) : "t0", "t1", "t2", "t3");
        break;
      case 1:  // MUL
        asm volatile("mul t0, %0, %1\n mul t1, t0, %0\n mul t2, t1, %1\n"
                     :: "r"(a), "r"(b) : "t0", "t1", "t2");
        break;
      case 2:  // MULH
        asm volatile("mulh t0, %0, %1\n mulhu t1, %0, %1\n mulhsu t2, %0, %1\n"
                     :: "r"(a), "r"(b) : "t0", "t1", "t2");
        break;
      case 3:  // DIV con operandos aleatorios (latencia data-dependent)
        asm volatile("div t0, %0, %1\n remu t1, %0, %1\n"
                     :: "r"(a), "r"(b) : "t0", "t1");
        break;
      case 4:  // MEM
        asm volatile("sw %0, 0(%2)\n sw %1, 4(%2)\n"
                     "lw t0, 0(%2)\n lw t1, 4(%2)\n"
                     :: "r"(a), "r"(b), "r"(buf) : "t0", "t1", "memory");
        break;
      default: // CTRL: branch dependiente de datos (a veces tomado, a veces no)
        asm volatile("andi t0, %0, 1\n"
                     "beqz t0, 1f\n"
                     "addi t1, zero, 7\n"
                     "1:\n"
                     :: "r"(r) : "t0", "t1");
        break;
    }
  }

  // ===== LECTURA (filtrada): cierra la ventana del golden =====
  asm volatile(
      "csrr t0, 0xBC0\n csrr t1, 0xBC2\n csrr t2, 0xBC4\n csrr t3, 0xBC6\n"
      "csrr t4, 0xBC8\n csrr t5, 0xBCA\n csrr t6, 0xBCC\n csrr a6, 0xBCE\n"
#ifdef WAVES_HOLD
      "wfi\n"
      "9: j 9b\n"
#endif
      "sw t0,  0(%[out])\n sw t1,  4(%[out])\n"
      "sw t2,  8(%[out])\n sw t3, 12(%[out])\n"
      "sw t4, 16(%[out])\n sw t5, 20(%[out])\n"
      "sw t6, 24(%[out])\n sw a6, 28(%[out])\n"
      :
      : [out] "r"(out)
      : "t0", "t1", "t2", "t3", "t4", "t5", "t6", "a6", "memory");

  printf("CLASIF alu=%u mul=%u mulh=%u div=%u mem=%u ctrl=%u float=%u divcyc=%u\n",
         (unsigned)out[0], (unsigned)out[1], (unsigned)out[2], (unsigned)out[3],
         (unsigned)out[4], (unsigned)out[5], (unsigned)out[6], (unsigned)out[7]);
  printf("RAND seed=0x%08x iters=%u (golden decide; sin conteo esperado fijo)\n",
         SEED, (unsigned)ITERS);
  return 0;
}
