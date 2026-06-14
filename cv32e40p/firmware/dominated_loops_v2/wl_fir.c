/* FIR float: filtro de 16 taps — FLOAT (fmul/fadd) + MEM (loads float) + ALU/CTRL. */
#ifndef REPS
#define REPS 3000
#endif
#define NT 16
#define NS 96
static float x[NS], coef[NT], y[NS];
void run_workload(void){
  volatile float sink=0.0f;
  for(int r=0;r<REPS;r++){
    for(int i=0;i<NS;i++) x[i]=(float)((i*3+r)&15);
    for(int i=0;i<NT;i++) coef[i]=(float)(i+1)*0.1f;
    for(int n=NT;n<NS;n++){ float s=0.0f; for(int k=0;k<NT;k++) s+=coef[k]*x[n-k]; y[n]=s; }
    sink+=y[NT];
  }
  (void)sink;
}
