# regresion — método M2 (regresión estilo EfiMon)

Datos y programas del método M2: 15 programas de calibración con mezclas variadas
de categorías, cada uno ejecutado a tres intensidades (duty cycle 100/60/30 % por
inserción de ventanas de reposo), y ajuste de los coeficientes por mínimos
cuadrados no negativos (NNLS) con intercepto sobre la potencia total. Las corridas
de idle de cada campaña anclan el intercepto (potencia estática).

- `fuentes/` — los 15 programas de calibración y sus variantes de duty
  (`duty_variants.mk`). Los kernels `wl_mulhchain.c` y `wl_saxpy.c` están
  **retirados** del conjunto oficial: el primero ancla `mulh` pero contamina
  `alu`/`mem` (dependencia de contexto documentada en el TFG); el segundo cuelga
  la FPU del bitstream.
- `gen_duty.py` — genera una variante de duty nueva: mide los mcycle base del
  programa por JTAG, calcula `REPS`/`SLEEP_TICKS` para la intensidad pedida y
  agrega la regla al Makefile.
- `elf/` — binarios (cada programa × 3 intensidades).
- `datos.csv` — mediciones crudas; el ajuste usa la última campaña completa.
- `coeficientes.csv` — coeficientes oficiales del método.
- `campanas/` — respaldo por campaña para reproducibilidad.

Se corre con `python3 ../caracterizar.py regresion --modelo efimon` o desde la GUI
(que ya pasa el modelo oficial; el default de la CLI es `clasico`).
