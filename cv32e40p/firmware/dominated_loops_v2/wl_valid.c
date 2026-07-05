/* VALIDACION: programa nuevo (no usado en calibracion) que mezcla las 7
 * categorias. mul+mulh via multiplicacion de 64 bits, div/rem, mem (arreglos),
 * ctrl (if/loops), float independiente (fmul+fadd sin cadena, -ffp-contract=off). */
#ifndef REPS
#define REPS 30000
#endif
#define N 32
static int a[N], b[N];
static float fa[N], fb[N], fc[N];
void run_workload(void){
  volatile long long sink=0;
  for(int r=0;r<REPS;r++){
    for(int i=0;i<N;i++){ a[i]=(i*7+r)&255; b[i]=((i*13+r)&127)|1;
                          fa[i]=(float)a[i]; fb[i]=(float)(b[i]+1); }
    long long acc=0;
    for(int i=0;i<N;i++){
      int x=a[i], y=b[i];
      acc += (long long)x * (long long)(y+7);   /* mul + mulh (64b) */
      acc += x / y;                              /* div  */
      acc += x % (y+3);                          /* rem  */
      if(x & 1) acc += (long long)x<<2; else acc -= x>>1;  /* ctrl + alu */
    }
    for(int i=0;i<N;i++) fc[i]=fa[i]*fb[i]+fa[i];   /* float independiente */
    float fs=0.0f; for(int i=0;i<N;i++) fs+=fc[i];
    sink += acc + (long long)fs;
  }
  (void)sink;
}
