# benchmarks — cargas de validación (BEEBS)

La validación del modelo se hace con **kernels de BEEBS** (Pallister, Hollis
y Bennett, 2013 — la suite estándar de benchmarks energéticos para
embebidos), con las fuentes **sin modificar** en `beebs/` (licencia GPL, ver
`beebs/LICENSE`). `beebs_wrap.c` conecta su interfaz estándar
(`initialise_benchmark`/`benchmark`/`verify_benchmark`) al `run_workload()`
del harness y provee los stubs de libc que algunos kernels referencian
(printf de depuración, strlen, memset/memcpy, floor). Ninguna carga participa
en la calibración.

## El conjunto

- `mont64` — multiplicación de Montgomery de 64 bits (**mul + mulh densos**,
  aritmética de 128 bits).
- `ud` — descomposición LU entera (**divisiones reales** por pivotes).
- `jfdctint` — DCT entera de JPEG (mul denso).
- `nettleaes` — AES de la biblioteca Nettle (alu + mem).
- `dijkstra` — caminos mínimos (versión MiBench small; mem + ctrl).
- `huffbench` — compresión/descompresión de Huffman (mem + ctrl).
- `levenshtein` — distancia de edición entre cadenas (mem + alu).
- `ns` — búsqueda en arreglo multidimensional (mem + ctrl).
- `aqsort` — quicksort de enteros (sglib, `-DQUICK_SORT`; mem + ctrl).
- `wl_gray.c` — la única **propia**: RGB→luminancia por píxel en float
  (fadd/fmul/fcvt sin fmadd, `-ffp-contract=off`).

El `REPS` de cada kernel (Makefile) apunta a ventanas de ~15–35 s a 10 MHz;
ajustar tras la primera corrida.

## Por qué gray no es de BEEBS

Se revisaron TODOS los kernels float de la suite contra la FPU de este
bitstream y ninguno resultó ejecutable:

- `ludcmp`, `minver`, `qurt`, `sqrt`, `newlib-*`: usan fdiv/fsqrt, fuera del
  conjunto probado de la FPU.
- `matmult-float`: acumulación dependiente (el patrón que colgó a saxpy).
- `fqsort` (qsort de floats): solo comparaciones fle/flt — **colgó en HW**
  (comparaciones FP densas, tercer patrón inestable).
- `perlin` (stb_perlin): solo fadd/fmul/fsub/fcvt/feq — **colgó en HW**
  (cadenas de lerps de ~6–9 ops FP dependientes).
- El resto de los float de BEEBS usa `double` (soft-float: no ejercita la FPU).

`gray` usa el único patrón que este bitstream ejecuta estable: aritmética FP
con operandos independientes espaciada por memoria y enteros (igual que las
pruebas exitosas del hardware). Los kernels retirados quedan en `beebs/`
como evidencia (fqsort.c, perlin.c) con sus reglas comentadas en el Makefile.

## Conjunto anterior (retirado)

Los `wl_*.S` en ensamblador de histograma fijo (sha256, wmul, divsum, fp*,
etc.) fueron el conjunto de validación original; se retiraron del build al
migrar la validación a código real de BEEBS, y se conservan como referencia
de las mediciones históricas en `validaciones/` y `verificacion.csv`.
`harness.S` + `link.ld` + `platform.inc` siguen siendo el arnés común.
