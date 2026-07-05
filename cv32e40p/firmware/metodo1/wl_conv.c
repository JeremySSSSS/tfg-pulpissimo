/* Filtro FIR / convolucion 1D ENTERA: algoritmo real de DSP. Para cada muestra
 * de salida acumula sum_k sig[i+k]*kern[k]. Perfil dominado por MUL + MEM
 * (lecturas de sig/kern, escrituras de out) + ALU/CTRL. Acumulador ENTERO
 * (no FP) -> sin cadena serial FP, no se traba. Sin libc. Programa LARGO
 * (REPS alto) para dar una duracion distinta a los demas. */
#ifndef REPS
#define REPS 22000
#endif
#define N 512
#define K 16

static int sig[N], kern[K], out[N];

void run_workload(void){
  unsigned s = 2463534242u;
  for(int i=0;i<N;i++){ s^=s<<13; s^=s>>17; s^=s<<5; sig[i] = (int)(s % 256) - 128; }
  for(int i=0;i<K;i++){ s^=s<<13; s^=s>>17; s^=s<<5; kern[i] = (int)(s % 16) - 8; }

  volatile int sink = 0;
  for(int rep=0; rep<REPS; rep++){
    for(int i=0; i<N-K; i++){
      int acc = 0;
      for(int k=0; k<K; k++)
        acc += sig[i+k] * kern[k];       /* MUL + MEM + add (acc entero) */
      out[i] = acc;
    }
    sink += out[rep % (N-K)];
  }
  (void)sink;
}
