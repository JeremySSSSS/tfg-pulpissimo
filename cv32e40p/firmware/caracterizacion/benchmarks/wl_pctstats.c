/* Estadisticas reales con DIVISION genuina: lecturas de un "sensor" agrupadas
 * en ventanas de tamano variable; por ventana se calcula la media
 * (suma/cuenta, cuenta VARIABLE) y el porcentaje del total
 * (cuenta*100/total). Como los divisores no son constantes, el compilador no
 * puede reemplazar la division por multiplicacion: emite div/rem reales. */
#ifndef REPS
#define REPS 4000
#endif

#define N 2048

static unsigned short LECT[N];

void run_workload(void) {
  volatile unsigned sink = 0;
  unsigned s = 0xACE1u;
  for (int i = 0; i < N; i++) {          /* señal pseudoaleatoria con deriva */
    s = s * 1103515245u + 12345u;
    LECT[i] = (unsigned short)(512 + ((s >> 16) & 255) + i / 8);
  }
  for (int r = 0; r < REPS; r++) {
    /* total VARIABLE entre pasadas: si fuera constante, el compilador
     * reemplazaria la division del porcentaje por multiplicacion */
    unsigned i = 0, total = N - ((unsigned)r & 31), acc = 0;
    unsigned semilla = 0x1234u + (unsigned)r;
    while (i < N) {
      semilla = semilla * 1103515245u + 12345u;
      unsigned cuenta = 3 + ((semilla >> 20) & 63);   /* ventana de 3..66 */
      if (cuenta > N - i) cuenta = N - i;
      unsigned suma = 0;
      for (unsigned k = 0; k < cuenta; k++) suma += LECT[i + k];
      unsigned media = suma / cuenta;                 /* div variable */
      unsigned resto = suma % cuenta;                 /* rem variable */
      unsigned pct   = cuenta * 100u / total;         /* div variable */
      acc += media + resto + pct;
      i += cuenta;
    }
    sink += acc;
    LECT[(r * 31u) & (N - 1)] ^= 3;
  }
}
