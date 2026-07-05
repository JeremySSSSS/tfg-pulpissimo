/* Conteo de primos por DIVISION DE PRUEBA (trial division): algoritmo real,
 * clasico de benchmarks. Para cada n prueba divisores d hasta sqrt(n) con n%d.
 * Perfil dominado por DIV/REM (ejercita el contador DIVCYC y p_div del modelo
 * hibrido) + MUL (d*d) + ALU/CTRL. Entero, sin libc, sin FP -> no se traba. */
#ifndef REPS
#define REPS 60
#endif
#define LIMIT 3000

void run_workload(void){
  volatile unsigned sink = 0;
  for(int rep=0; rep<REPS; rep++){
    unsigned count = 0;
    for(unsigned n=2; n<LIMIT; n++){
      int prime = 1;
      for(unsigned d=2; d*d<=n; d++){       /* d*d -> MUL */
        if(n % d == 0){ prime = 0; break; } /* n%d -> REM (categoria div) */
      }
      count += prime;
    }
    sink += count;
  }
  (void)sink;
}
