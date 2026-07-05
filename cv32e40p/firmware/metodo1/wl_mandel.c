/* Conjunto de Mandelbrot (escape-time): algoritmo real, clasico de graficos/
 * benchmarks FP. Para cada pixel itera z = z^2 + c hasta escapar (|z|>2) o
 * MAXIT. Perfil dominado por FLOAT (mul/add/sub) + CTRL. Cada pixel es
 * INDEPENDIENTE (sin acumulacion serial global) y la cadena por pixel esta
 * ACOTADA por MAXIT; sin fdiv en el lazo (los pasos dx/dy son constantes) ni
 * sqrt -> deberia correr (a diferencia de nbody/fir, que acumulaban en serie).
 * Si igual se traba, descartarlo como esos. Sin libc. */
#ifndef REPS
#define REPS 35
#endif
#define W 64
#define H 64
#define MAXIT 256

void run_workload(void){
  const float dx = 3.0f / W;          /* constante (folded por el compilador) */
  const float dy = 2.0f / H;
  volatile int sink = 0;
  for(int rep=0; rep<REPS; rep++){
    int total = 0;
    for(int py=0; py<H; py++){
      float y0 = (float)py * dy - 1.0f;
      for(int px=0; px<W; px++){
        float x0 = (float)px * dx - 2.0f;
        float x = 0.0f, y = 0.0f;
        int it = 0;
        while(it < MAXIT && x*x + y*y < 4.0f){
          float xt = x*x - y*y + x0;     /* fmul, fsub, fadd */
          y = 2.0f*x*y + y0;             /* fmul, fadd */
          x = xt;
          it++;
        }
        total += it;                     /* acumulacion ENTERA (segura) */
      }
    }
    sink += total;
  }
  (void)sink;
}
