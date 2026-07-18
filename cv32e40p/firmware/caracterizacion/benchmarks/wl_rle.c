/* Compresion RLE real: codifica y decodifica un buffer de 4 KiB con rachas
 * (como una fila de imagen con zonas planas) y verifica la ida y vuelta.
 * Codigo C normal: recorridos de memoria, comparaciones y ramas. */
#ifndef REPS
#define REPS 2500
#endif

#define N 4096

static unsigned char SRC[N], ENC[2 * N], DEC[N];

static unsigned rle_encode(const unsigned char *in, unsigned n, unsigned char *out) {
  unsigned o = 0, i = 0;
  while (i < n) {
    unsigned char v = in[i];
    unsigned run = 1;
    while (i + run < n && in[i + run] == v && run < 255) run++;
    out[o++] = (unsigned char)run;
    out[o++] = v;
    i += run;
  }
  return o;
}

static unsigned rle_decode(const unsigned char *in, unsigned n, unsigned char *out) {
  unsigned o = 0;
  for (unsigned i = 0; i + 1 < n; i += 2)
    for (unsigned r = 0; r < in[i]; r++) out[o++] = in[i + 1];
  return o;
}

void run_workload(void) {
  volatile unsigned sink = 0;
  unsigned s = 0xBEEF01u;
  unsigned i = 0;
  while (i < N) {                       /* rachas de largo 1..32 */
    s = s * 1103515245u + 12345u;
    unsigned run = 1 + ((s >> 12) & 31);
    unsigned char v = (unsigned char)(s >> 24);
    for (unsigned r = 0; r < run && i < N; r++) SRC[i++] = v;
  }
  for (int r = 0; r < REPS; r++) {
    unsigned ne = rle_encode(SRC, N, ENC);
    unsigned nd = rle_decode(ENC, ne, DEC);
    unsigned ok = (nd == N);
    for (unsigned k = 0; k < N; k += 64) ok &= (DEC[k] == SRC[k]);
    sink += ne + ok;
    SRC[(r * 97u) & (N - 1)] ^= 1;      /* el buffer cambia entre pasadas */
  }
}
