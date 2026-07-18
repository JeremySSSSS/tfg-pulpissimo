/* Quicksort real (recursivo, pivote mediana-de-tres) sobre un arreglo de 512
 * enteros pseudoaleatorios; se verifica el orden al final. Codigo C normal:
 * comparaciones, intercambios en memoria y recursion. */
#ifndef REPS
#define REPS 3000
#endif

#define N 512

static int A[N];

static void qs(int lo, int hi) {
  while (lo < hi) {
    int mid = lo + (hi - lo) / 2;
    /* mediana de tres al centro */
    if (A[mid] < A[lo]) { int t = A[mid]; A[mid] = A[lo]; A[lo] = t; }
    if (A[hi]  < A[lo]) { int t = A[hi];  A[hi]  = A[lo]; A[lo] = t; }
    if (A[hi]  < A[mid]){ int t = A[hi];  A[hi]  = A[mid];A[mid]= t; }
    int piv = A[mid], i = lo, j = hi;
    while (i <= j) {
      while (A[i] < piv) i++;
      while (A[j] > piv) j--;
      if (i <= j) { int t = A[i]; A[i] = A[j]; A[j] = t; i++; j--; }
    }
    /* recursion sobre la mitad chica, iteracion sobre la grande */
    if (j - lo < hi - i) { qs(lo, j); lo = i; }
    else                 { qs(i, hi); hi = j; }
  }
}

void run_workload(void) {
  volatile unsigned sink = 0;
  unsigned s = 0x5EED5EEDu;
  for (int r = 0; r < REPS; r++) {
    for (int i = 0; i < N; i++) {       /* arreglo nuevo en cada pasada */
      s = s * 1103515245u + 12345u;
      A[i] = (int)(s >> 8);
    }
    qs(0, N - 1);
    unsigned ok = 1;
    for (int i = 1; i < N; i++) ok &= (A[i - 1] <= A[i]);
    sink += ok + (unsigned)A[N / 2];
  }
}
