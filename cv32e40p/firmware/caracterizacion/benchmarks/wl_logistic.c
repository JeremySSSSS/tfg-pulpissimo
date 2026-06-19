/* Mapa logistico (caos / dinamica de poblaciones): x = r*x*(1-x). Algoritmo
 * REAL. Float REGISTER-ONLY: x evoluciona en un registro; r y las constantes se
 * cargan UNA vez antes del lazo -> SIN flw en el lazo caliente. Sin FMA
 * (-ffp-contract=off), sin fcvt en el lazo (el cast a int va al final). Es el
 * unico tipo de float que la FPU de este bitstream banca (como el bucle float
 * del chopper, que corre). Si ESTE corre -> podemos validar float con programas
 * register-only; si cuelga -> ni eso. */
#ifndef REPS
#define REPS 8000000
#endif

void run_workload(void) {
  float x = 0.5f;
  const float r = 3.9f;
  for (int i = 0; i < REPS; i++)
    x = r * x * (1.0f - x);            /* fsub, fmul, fmul -- todo en registros */
  volatile int sink = (int)(x * 1000.0f);   /* un fcvt al final, FUERA del lazo */
  (void)sink;
}
