# benchmarks — cargas de validación

Las 14 cargas con las que se valida la estimación (`../verificar.py`). Ninguna se
usa para calibrar: son el conjunto reservado que decide si los coeficientes
generalizan. Cubren algoritmos reales (`sha256`, `floyd`, `bsearch`, `primes`,
`conv`, `ycbcr`, `bitcount`, `fixmul`) y cargas de estrés
dirigidas a las categorías con poco soporte natural:

- `wl_wmul.S` — densa en `mulh` (≈58 % del retiro). Fue la carga que expuso la
  sobreatribución de `mulh` en M2.
- `wl_divsum.S` — densa en `div` (≈50 %), divisor con operandos variables.
- `wl_mixed.S` — mezcla balanceada de las cuatro categorías enteras principales.
- `wl_fpalu.S`, `wl_fpmem.S`, `wl_fpgain.S` — cargas float (los patrones que la
  FPU del bitstream ejecuta de forma estable).

## Cargas reales en C

Además del conjunto oficial hay seis cargas escritas como programas C
normales, algoritmos completos compilados por GCC sin ajustar la mezcla de
instrucciones (pedidas para validar con código realista):

- `wl_aes128.c` — cifrado AES-128 de un buffer de 1 KiB (tablas + XOR/shifts).
- `wl_dijkstra.c` — caminos mínimos en un grafo de 32 nodos.
- `wl_dct8x8.c` — DCT 8×8 entera en punto fijo Q15, estilo JPEG (mul/mulh
  reales por los productos de 64 bits).
- `wl_rle.c` — compresión RLE con verificación de ida y vuelta.
- `wl_sieve.c` — criba de Eratóstenes hasta 8192 con mapa de bits.
- `wl_qsort.c` — quicksort recursivo de 512 enteros con verificación.
- `wl_pctstats.c` — estadísticas por ventanas de tamaño variable: medias y
  porcentajes con **divisiones de divisor variable** (div/rem reales).
- `wl_reloj.c` — timestamps a dd:hh:mm:ss + formateo decimal: **divisiones
  por constantes** que este GCC emite como divu/remu reales (típico de
  firmware: relojes, calendarios).
- `wl_gray.c` — RGB→luminancia por píxel en **float** (fadd/fmul/fcvt, sin
  fmadd por `-ffp-contract=off`; mismo patrón por elemento probado estable
  en `ycbcr`). La única no-entera: probarla con una corrida corta primero.

Cobertura conjunta verificada por desensamblado: alu/mem/ctrl en todas, mul
en todas, mulh en `dct8x8` (lazos calientes del punto fijo), div en
`pctstats` y `reloj`, float en `gray`.

Todas menos `gray` son enteras (sin FPU, corren seguro en este bitstream). El `REPS` de
cada una apunta a ventanas de ~15–35 s a 10 MHz; se ajusta en el Makefile si
la primera corrida queda corta o larga.

`harness.S` + `link.ld` + `platform.inc` forman el arnés común: resetean los CSR
del clasificador, corren el kernel un número fijo de repeticiones y dejan los
conteos listos para que el banco los lea por JTAG.

Los ELF de `md5`, `logistic` y `fpctrl` permanecen compilados pero están fuera
del conjunto oficial (sustituidos por `wmul`, `divsum` y `mixed` para que la
validación no estuviera dominada por cargas casi idénticas ricas en `alu`).

Compilar todo: `make` (usa la toolchain RISC-V del proyecto).
