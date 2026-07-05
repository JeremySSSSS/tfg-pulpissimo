/* Floyd-Warshall: caminos mas cortos entre TODOS los pares de nodos de un grafo
 * (algoritmo clasico, libro de algoritmos / routing). O(N^3) sobre matriz densa.
 * Perfil MUL (indexado 2D i*N+j) + MEM (la matriz) + ALU (sumas/min) + CTRL.
 * Entero, sin libc. N no es potencia de 2 -> el indexado usa MUL real. */
#ifndef REPS
#define REPS 400
#endif
#define N 50
#define INF 0x3fffffff

static int dist[N * N];

void run_workload(void) {
  unsigned s = 2463534242u;
  volatile int sink = 0;
  for (int rep = 0; rep < REPS; rep++) {
    /* grafo determinista con pesos pseudo-aleatorios */
    for (int i = 0; i < N; i++)
      for (int j = 0; j < N; j++) {
        s ^= s<<13; s ^= s>>17; s ^= s<<5;
        dist[i*N + j] = (i == j) ? 0 : (int)(1 + (s % 100));
      }
    /* relajacion all-pairs */
    for (int k = 0; k < N; k++)
      for (int i = 0; i < N; i++) {
        int dik = dist[i*N + k];
        for (int j = 0; j < N; j++) {
          int v = dik + dist[k*N + j];
          if (v < dist[i*N + j]) dist[i*N + j] = v;
        }
      }
    sink += dist[(rep % N)*N + ((rep*7) % N)];
  }
  (void)sink;
}
