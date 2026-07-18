/* Codigo real con DIVISION por constantes: convertir marcas de tiempo
 * (segundos) a dias + hh:mm:ss y formatear los digitos en decimal (div/mod
 * por 86400, 3600, 60 y 10). Nota: en otros compiladores estas divisiones se
 * vuelven multiplicaciones magicas (mulh), pero el GCC de esta toolchain,
 * con el divisor hardware del nucleo disponible, emite divu/remu reales
 * (verificado en el desensamblado: 15 div estaticas). Es una carga real de
 * division tipica de firmware: relojes, calendarios, formateo decimal. */
#ifndef REPS
#define REPS 60000
#endif

static char TXT[16];

static unsigned formatear(unsigned t) {
  unsigned dias = t / 86400u;  t %= 86400u;
  unsigned hh   = t / 3600u;   t %= 3600u;
  unsigned mm   = t / 60u;
  unsigned ss   = t % 60u;
  /* dd:hh:mm:ss en texto, digito por digito (div/mod 10 -> mulhu) */
  TXT[0]  = (char)('0' + dias / 10u % 10u);
  TXT[1]  = (char)('0' + dias % 10u);
  TXT[2]  = ':';
  TXT[3]  = (char)('0' + hh / 10u);
  TXT[4]  = (char)('0' + hh % 10u);
  TXT[5]  = ':';
  TXT[6]  = (char)('0' + mm / 10u);
  TXT[7]  = (char)('0' + mm % 10u);
  TXT[8]  = ':';
  TXT[9]  = (char)('0' + ss / 10u);
  TXT[10] = (char)('0' + ss % 10u);
  TXT[11] = 0;
  unsigned acc = 0;
  for (int i = 0; i < 11; i++) acc += (unsigned char)TXT[i];
  return acc;
}

void run_workload(void) {
  volatile unsigned sink = 0;
  unsigned t = 123456u;
  for (int r = 0; r < REPS; r++) {
    for (int k = 0; k < 32; k++) {
      sink += formatear(t);
      t = t * 1664525u + 1013904223u;   /* proxima "marca de tiempo" */
      t &= 0x7fffffu;                   /* hasta ~97 dias */
    }
  }
}
