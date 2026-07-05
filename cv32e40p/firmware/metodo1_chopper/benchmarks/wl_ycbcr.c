/* RGB -> YCbCr: conversion de espacio de color (paso 1 del codec JPEG, ITU-R
 * BT.601). Algoritmo REAL, uso masivo (imagen/video). Float-pesado: por pixel
 * son 3 productos-punto (9 fmul + 6 fadd). Cada pixel es INDEPENDIENTE y los 3
 * canales Y/Cb/Cr NO dependen entre si -> 3 flujos FP independientes, sin cadena
 * serial larga -> deberia correr (a diferencia de nbody/fir/mandel que acumulan
 * o iteran en serie). Los 3 canales se pliegan en un acumulador ENTERO (cast a
 * int) -> nada de cadena FP, y el compilador no los elimina como dead-code.
 * Sin almacenar Y/Cb/Cr (solo R,G,B en memoria) para entrar en L2. Sin libc. */
#ifndef REPS
#define REPS 1000
#endif
#define N 64                       /* imagen N x N pixeles */
#define NP (N * N)

static float R[NP], G[NP], B[NP];

void run_workload(void) {
  unsigned s = 2463534242u;
  for (int i = 0; i < NP; i++) {
    s^=s<<13; s^=s>>17; s^=s<<5; R[i] = (float)(s & 0xFF);
    s^=s<<13; s^=s>>17; s^=s<<5; G[i] = (float)(s & 0xFF);
    s^=s<<13; s^=s>>17; s^=s<<5; B[i] = (float)(s & 0xFF);
  }

  volatile int sink = 0;
  for (int rep = 0; rep < REPS; rep++) {
    int acc = 0;
    for (int i = 0; i < NP; i++) {
      float r = R[i], g = G[i], b = B[i];
      float y  =  0.299000f*r + 0.587000f*g + 0.114000f*b;          /* 3 canales */
      float cb = -0.168736f*r - 0.331264f*g + 0.500000f*b + 128.0f; /* independientes */
      float cr =  0.500000f*r - 0.418688f*g - 0.081312f*b + 128.0f; /* entre si */
      acc ^= (int)y ^ (int)cb ^ (int)cr;     /* pliega los 3 -> ninguno muere */
    }
    sink ^= acc;
  }
  (void)sink;
}
