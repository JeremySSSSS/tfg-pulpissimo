/* bitcount (MiBench): cuenta los bits en 1 de un arreglo de enteros por el
 * metodo de Kernighan (x &= x-1 borra el bit bajo -> itera tantas veces como
 * bits en 1). Algoritmo REAL de benchmark embebido. Perfil ALU (and, sub) +
 * CTRL con ramas DATA-DEPENDENT (el lazo interno depende de cuantos bits hay) +
 * MEM (el arreglo). Entero, sin libc. */
#ifndef REPS
#define REPS 5000
#endif
#define N 1024

static unsigned data[N];

static int bitcount(unsigned x) {
  int n = 0;
  while (x) { x &= x - 1; n++; }      /* Kernighan: ramas data-dependent */
  return n;
}

void run_workload(void) {
  unsigned s = 2463534242u;
  for (int i = 0; i < N; i++) { s^=s<<13; s^=s>>17; s^=s<<5; data[i] = s; }

  volatile unsigned sink = 0;
  for (int rep = 0; rep < REPS; rep++) {
    unsigned total = 0;
    for (int i = 0; i < N; i++)
      total += bitcount(data[i]);
    sink += total;
    data[rep % N] += (unsigned)rep;    /* varia un poco */
  }
  (void)sink;
}
