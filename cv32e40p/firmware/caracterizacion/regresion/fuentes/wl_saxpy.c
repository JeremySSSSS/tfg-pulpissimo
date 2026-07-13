/* SAXPY: v = A[i]*s + B[i] sobre arreglos float, con relleno de operandos por
 * vuelta: FLOAT (~25%, fmul+fadd+fcvt) + MEM (~25%, 2 cargas + 1 escritura
 * por elemento) en partes iguales. Razon de ser: cubre la region float+mem
 * densa del espacio de composicion --- el perfil de las cargas flotantes de
 * validacion (fpgain: 23% float + 38% mem) --- que fpoly (float alto, mem
 * 10%) y vecscale (26/13) no alcanzan: sin ella la regresion nunca ve el
 * costo del float acompañado de trafico real de memoria. Patron INDEPENDIENTE
 * por elemento (fmul+fadd sin cadena, -ffp-contract=off evita fmadd): el
 * unico patron FP estable en este bitstream, igual que dotprod/vecscale. */
#ifndef REPS
#define REPS 85000
#endif
#define N 64
static float A[N], B[N], C[N];
void run_workload(void){
  volatile int sink=0;
  const float s=1.0009765625f;
  for(int r=0;r<REPS;r++){
    for(int i=0;i<N;i++){                       /* operandos frescos por vuelta */
      A[i]=(float)(((i*13+r)&255)-128);         /* fcvt + store */
      B[i]=(float)((i*7-r)&127);                /* fcvt + store */
    }
    int acc=0;
    for(int i=0;i<N;i++){
      float v=A[i]*s+B[i];                      /* 2 loads + fmul + fadd */
      C[i]=v;                                   /* store */
      acc+=(int)v;                              /* fcvt; acumula en entero */
    }
    sink+=acc;
  }
  (void)sink;
}
