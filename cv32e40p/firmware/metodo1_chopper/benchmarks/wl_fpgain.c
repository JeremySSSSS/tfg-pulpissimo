/* Escalado de senal (gain + offset): out[i] = in[i]*g + off. Operacion REAL de
 * DSP/audio. DIAGNOSTICO del deadlock de la FPU: se compila SIN FMA
 * (-fno-fp-contract -> fmul + fadd separados, no fmadd) y el checksum lee los
 * BITS del float como int (sin fcvt float->int). Asi aisla si el cuelgue lo
 * dispara FMA/fcvt (entonces evitandolos un float real SI corre) o si es el
 * flw+arith FP en si (entonces float es invalidable en este bitstream). Sin libc. */
#ifndef REPS
#define REPS 2000
#endif
#define N 1024

static float in[N], out[N];

void run_workload(void) {
  /* floats LITERALES (sin fcvt int->float) -> el programa NO usa fcvt en ningun lado */
  static const float seed[8] = {0.5f, 1.25f, 2.75f, 4.0f, 8.5f, 16.25f, 32.75f, 64.0f};
  for (int i = 0; i < N; i++) in[i] = seed[i & 7];

  volatile int sink = 0;
  for (int rep = 0; rep < REPS; rep++) {
    for (int i = 0; i < N; i++)
      out[i] = in[i] * 1.5f + 0.5f;        /* fmul + fadd (sin FMA con -fno-fp-contract) */
    sink ^= *(volatile int*)&out[rep % N]; /* lee los bits del float como int -> sin fcvt */
  }
  (void)sink;
}
