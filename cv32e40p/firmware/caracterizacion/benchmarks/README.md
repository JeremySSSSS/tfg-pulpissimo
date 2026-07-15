# benchmarks — cargas de validación

Las 14 cargas con las que se valida la estimación (`../verificar.py`). Ninguna se
usa para calibrar: son el conjunto reservado que decide si los coeficientes
generalizan. Cubren algoritmos reales (`sha256`, `md5`→retirada, `floyd`,
`bsearch`, `primes`, `conv`, `ycbcr`, `bitcount`, `fixmul`) y cargas de estrés
dirigidas a las categorías con poco soporte natural:

- `wl_wmul.S` — densa en `mulh` (≈58 % del retiro). Fue la carga que expuso la
  sobreatribución de `mulh` en M2.
- `wl_divsum.S` — densa en `div` (≈50 %), divisor con operandos variables.
- `wl_mixed.S` — mezcla balanceada de las cuatro categorías enteras principales.
- `wl_fpalu.S`, `wl_fpmem.S`, `wl_fpgain.S` — cargas float (los patrones que la
  FPU del bitstream ejecuta de forma estable).

`harness.S` + `link.ld` + `platform.inc` forman el arnés común: resetean los CSR
del clasificador, corren el kernel un número fijo de repeticiones y dejan los
conteos listos para que el banco los lea por JTAG.

Los ELF de `md5`, `logistic` y `fpctrl` permanecen compilados pero están fuera
del conjunto oficial (sustituidos por `wmul`, `divsum` y `mixed` para que la
validación no estuviera dominada por cargas casi idénticas ricas en `alu`).

Compilar todo: `make` (usa la toolchain RISC-V del proyecto).
