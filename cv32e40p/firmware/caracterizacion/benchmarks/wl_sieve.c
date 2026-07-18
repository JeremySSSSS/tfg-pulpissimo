/* Criba de Eratostenes real: primos hasta 8192 con mapa de bits, contados al
 * final. Codigo C normal: marcado en memoria con desplazamientos y ramas. */
#ifndef REPS
#define REPS 5000
#endif

#define N 8192

static unsigned MAPA[N / 32];

void run_workload(void) {
  volatile unsigned sink = 0;
  for (int r = 0; r < REPS; r++) {
    for (unsigned i = 0; i < N / 32; i++) MAPA[i] = 0;
    for (unsigned p = 2; p * p < N; p++)
      if (!(MAPA[p >> 5] & (1u << (p & 31))))
        for (unsigned m = p * p; m < N; m += p)
          MAPA[m >> 5] |= 1u << (m & 31);
    unsigned cuenta = 0;
    for (unsigned i = 2; i < N; i++)
      if (!(MAPA[i >> 5] & (1u << (i & 31)))) cuenta++;
    sink += cuenta;                     /* pi(8192) = 1028 */
  }
}
