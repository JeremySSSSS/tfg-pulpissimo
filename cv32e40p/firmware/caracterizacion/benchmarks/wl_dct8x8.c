/* DCT-II 8x8 entera en punto fijo Q15, como la etapa de transformada de un
 * compresor de imagen tipo JPEG. Codigo C normal: productos de 32x32 bits con
 * intermedio de 64 (mul + mulh reales), acumulacion y memoria. Se transforman
 * los bloques de una "imagen" de 32x32 pixeles generada deterministicamente. */
#ifndef REPS
#define REPS 1500
#endif

/* cos((2j+1) i pi / 16) * sqrt(2/8) en Q15; fila 0 con sqrt(1/8) */
static const short C[8][8] = {
  { 11585, 11585, 11585, 11585, 11585, 11585, 11585, 11585},
  { 16069, 13623,  9102,  3196, -3196, -9102,-13623,-16069},
  { 15137,  6270, -6270,-15137,-15137, -6270,  6270, 15137},
  { 13623, -3196,-16069, -9102,  9102, 16069,  3196,-13623},
  { 11585,-11585,-11585, 11585, 11585,-11585,-11585, 11585},
  {  9102,-16069,  3196, 13623,-13623, -3196, 16069, -9102},
  {  6270,-15137, 15137, -6270, -6270, 15137,-15137,  6270},
  {  3196, -9102, 13623,-16069, 16069,-13623,  9102, -3196}};

static short IMG[32][32];
static int   TMP[8][8], OUT[8][8];

static void dct8x8(int by, int bx) {
  /* filas: TMP = C * bloque */
  for (int i = 0; i < 8; i++)
    for (int j = 0; j < 8; j++) {
      long long acc = 0;
      for (int k = 0; k < 8; k++)
        acc += (long long)C[i][k] * IMG[by + k][bx + j];
      TMP[i][j] = (int)(acc >> 15);
    }
  /* columnas: OUT = TMP * C^T */
  for (int i = 0; i < 8; i++)
    for (int j = 0; j < 8; j++) {
      long long acc = 0;
      for (int k = 0; k < 8; k++)
        acc += (long long)TMP[i][k] * C[j][k];
      OUT[i][j] = (int)(acc >> 15);
    }
}

void run_workload(void) {
  volatile int sink = 0;
  unsigned s = 0xC0FFEEu;
  for (int y = 0; y < 32; y++)
    for (int x = 0; x < 32; x++) {
      s = s * 1103515245u + 12345u;
      IMG[y][x] = (short)((s >> 20) & 255) - 128;   /* pixel centrado */
    }
  for (int r = 0; r < REPS; r++) {
    for (int by = 0; by < 32; by += 8)
      for (int bx = 0; bx < 32; bx += 8) {
        dct8x8(by, bx);
        sink += OUT[0][0] + OUT[7][7];
      }
    IMG[r & 31][(r * 7) & 31] ^= 0x55;   /* la imagen cambia entre pasadas */
  }
}
