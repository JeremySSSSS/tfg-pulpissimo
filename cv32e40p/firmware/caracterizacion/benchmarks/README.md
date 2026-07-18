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

## Cargas reales (BEEBS)

Además del conjunto oficial hay nueve kernels de **BEEBS** (Pallister,
Hollis y Bennett, 2013 — la suite estándar de benchmarks energéticos para
embebidos), con las fuentes **sin modificar** en `beebs/` (licencia GPL,
ver `beebs/LICENSE`) y adaptadas por `beebs_wrap.c`, que conecta su
interfaz `initialise/benchmark/verify` al `run_workload()` del harness y
provee los stubs de libc (printf de depuración, strlen, memset/memcpy):

- `mont64` — multiplicación de Montgomery de 64 bits (aritmética de 128 bits:
  **mul + mulh densos**).
- `ud` — descomposición LU entera (**divisiones reales** por pivotes).
- `jfdctint` — DCT entera de JPEG.
- `nettleaes` — AES de la biblioteca Nettle.
- `dijkstra` — caminos mínimos (versión MiBench small).
- `huffbench` — compresión/descompresión de Huffman.
- `levenshtein` — distancia de edición entre cadenas.
- `ns` — búsqueda en arreglo multidimensional.
- `aqsort` — quicksort de arreglo de enteros (sglib, `-DQUICK_SORT`).
- `fqsort` — **RETIRADO**: quicksort de floats con solo comparaciones
  fle.s/flt.s (cero aritmética FP), pero aun así colgó en hardware: su
  lazo interno emite comparaciones FP densas (load→flt.s→branch pegados),
  tercer patrón que la FPU del bitstream no ejecuta de forma estable
  (junto con las cadenas dependientes y las ráfagas densas).
- `wl_gray.c` — la única **propia**: RGB→luminancia por píxel en float
  (fadd/fmul/fcvt sin fmadd). Se mantiene porque los kernels float de BEEBS
  usan `double` (soft-float, no ejercita la FPU) o acumulaciones dependientes
  que esta FPU no ejecuta de forma estable. Probarla con una corrida corta
  primero.

Cobertura del conjunto verificada por desensamblado: alu/mem/ctrl en todos,
mulh en `mont64`, div en `ud`/`huffbench`/`jfdctint`/`nettleaes`, float en
`gray`. El `REPS` de cada uno (en el Makefile) apunta a ventanas de
~15–35 s a 10 MHz; ajustar tras la primera corrida.

`harness.S` + `link.ld` + `platform.inc` forman el arnés común: resetean los CSR
del clasificador, corren el kernel un número fijo de repeticiones y dejan los
conteos listos para que el banco los lea por JTAG.

Los ELF de `md5`, `logistic` y `fpctrl` permanecen compilados pero están fuera
del conjunto oficial (sustituidos por `wmul`, `divsum` y `mixed` para que la
validación no estuviera dominada por cargas casi idénticas ricas en `alu`).

Compilar todo: `make` (usa la toolchain RISC-V del proyecto).
