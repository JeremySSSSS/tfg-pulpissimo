// Harness común de los bucles dominados v2 (uno por categoría).
//
// Flujo: reset de los 16 CSR (un solo bloque asm, sin instrucciones del
// compilador en medio) -> loop_body(ITERS, opa, opb) del .S de la categoría
// -> lectura de los 8 contadores -> printf (batch/golden) o wfi (GUI).
//
// La ventana medida incluye la llamada/retorno y el setup de argumentos:
// eso es overhead real del bucle y el modelo dorado lo cuenta igual, así
// que el PASS sigue siendo exacto y la dominancia reportada es la real.
//
// Selección por defines (los pone run_clasif_v2_xsim.sh):
//   -DLOOP_MEM    opa = puntero al buffer
//   -DLOOP_FLOAT  habilita mstatus.FS antes de empezar
//   -DDIV_MIN / -DDIV_MAX  operandos de latencia mínima/máxima (default:
//                          pseudoaleatorios)
//   -DITERS=n     iteraciones (default 8 -> 512 instrucciones objetivo)

#include <stdint.h>
#include <stdio.h>

#ifndef ITERS
#define ITERS 8u
#endif

extern void loop_body(uint32_t iters, uint32_t opa, uint32_t opb);

static volatile uint32_t buf[16];
static volatile uint32_t out[8];

#if defined(DIV_MIN)
#define OPA 3u           // divisor >> dividendo: el divisor serial termina rápido
#define OPB 0x40000000u
#elif defined(DIV_MAX)
#define OPA 0x7FFFFFFFu  // dividendo grande / 1: latencia máxima
#define OPB 1u
#else
#define OPA 0x12345678u
#define OPB 0x9A7u
#endif

int main(void) {
#ifdef LOOP_FLOAT
  // mstatus.FS = Initial (bit 13) para habilitar la FPU
  asm volatile("li t0, 8192\n csrs mstatus, t0" ::: "t0");
#endif

  uint32_t opa = OPA;
  uint32_t opb = OPB;
#ifdef LOOP_MEM
  opa = (uint32_t)buf;
#endif

  // Reset de los 16 CSR en UN solo bloque: el modelo dorado abre la ventana
  // tras el 16.º write, y no puede colarse nada del compilador en medio.
  asm volatile(
      "csrw 0xBC0, x0\n csrw 0xBC1, x0\n csrw 0xBC2, x0\n csrw 0xBC3, x0\n"
      "csrw 0xBC4, x0\n csrw 0xBC5, x0\n csrw 0xBC6, x0\n csrw 0xBC7, x0\n"
      "csrw 0xBC8, x0\n csrw 0xBC9, x0\n csrw 0xBCA, x0\n csrw 0xBCB, x0\n"
      "csrw 0xBCC, x0\n csrw 0xBCD, x0\n csrw 0xBCE, x0\n csrw 0xBCF, x0\n");

  loop_body(ITERS, opa, opb);

  asm volatile(
      "csrr t0, 0xBC0\n"  // ALU
      "csrr t1, 0xBC2\n"  // MUL
      "csrr t2, 0xBC4\n"  // MULH
      "csrr t3, 0xBC6\n"  // DIV
      "csrr t4, 0xBC8\n"  // MEM
      "csrr t5, 0xBCA\n"  // CTRL
      "csrr t6, 0xBCC\n"  // FLOAT
      "csrr a6, 0xBCE\n"  // DIVCYC
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

  unsigned total = out[0] + out[1] + out[2] + out[3] + out[4] + out[5] + out[6];
  printf("TOTAL=%u iters=%u\n", total, (unsigned)ITERS);
  return 0;
}
