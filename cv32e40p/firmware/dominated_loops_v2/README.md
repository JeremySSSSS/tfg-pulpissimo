# Caracterización energética v2 (clasificador de 16 CSR)

Firmware físico (FPGA Nexys A7, bitstream v2) y solver para caracterizar los
coeficientes `eᵢ` del modelo `E = Σ eᵢ·nᵢ` por los **dos métodos** del TFG.

## Firmware

Todos envuelven la región de interés con una ventana en **GPIO8** (al ESP32) y
vuelcan los 16 CSR del clasificador + `mcycle` inicio/fin a `results`
(18 words). **Leer siempre por símbolo:** `x/18xw &results` (cada `.elf` ubica
`results` en distinta dirección).

| Grupo | Archivos | Uso |
|---|---|---|
| **Dominados** (M1) | `dominated_loop_v2.S` → `alu/mul/mulh/div/mem/ctrl/float/idle.elf` | un bucle por categoría (puntos extremos) |
| **Cargas reales** (M2) | `harness.S` + `wl_*.c` → `sort/matmul/crc/strings/gcd/fir.elf` | programas con mezcla natural de instrucciones |

`make` compila todo. Conteos por categoría tuneados para durar ~13 s
(`*_LOOP_COUNT`, `REPS`). El divisor y el float son lentos → menos iteraciones.

Notas:
- `div` usa el divisor serial (4–32 cic/op): pocas iteraciones.
- `float`: usar ops **independientes** (no cadena `s+=`) para que la FPU
  pipelinee; evitar `fmadd.s` (lento en este bitstream) con `-ffp-contract=off`.

## Solver (Método 2 — regresión)

`regresion.py` lee `runs.csv` (una fila por ejecución: `name,P_avg_W,w0..w17`)
y resuelve `E = N·e` por mínimos cuadrados. La columna de división usa `c_div`
(ciclos DIVCYC), no `n_div` (modelo híbrido). Reporta `eᵢ`, `p_div`, R² y número
de condición. La estática queda absorbida en los `eᵢ` (supuesto del modelo).

```bash
python3 regresion.py
```

## Resultado de referencia (2026-06-13, 10 MHz, 9 ejecuciones)

| eᵢ | valor | | eᵢ | valor |
|---|---|---|---|---|
| e_alu | 515 nJ | | e_ctrl | 1915 nJ |
| e_mul | 695 nJ | | e_mulh | 2519 nJ |
| e_float | 626 nJ | | p_div | 480 nJ/ciclo |
| e_mem | 844 nJ | | | |

**R² = 0.9995 · número de condición = 31.7 · error ±5 %** por carga.

Los coeficientes escalan con los ciclos por categoría (la estática a 10 MHz
domina); el modelo predice el consumo total de programas reales a ±5 %.
