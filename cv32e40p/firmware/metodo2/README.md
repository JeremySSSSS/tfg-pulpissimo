# Método 2 — regresión por histograma

Ajusta los 7 coeficientes `e_i` de una vez por **mínimos cuadrados** a partir de
varios programas **mixtos** (a diferencia de M1, que aísla cada categoría).

## El método
1. Correr M programas con mezclas variadas. De cada uno se mide:
   - el histograma `n_i` por categoría (de los CSR del clasificador),
   - la energía real `E = P_avg · T`.
2. Sistema sobredeterminado **E = N · e** (M ecuaciones, 7 incógnitas, M > 7).
3. Resolver con `numpy.linalg.lstsq` → la `e` que minimiza el error sobre todos.

## Set de calibración (diverso, para condicionar bien la regresión)
- **mix1, mix2, mix3** — mezclas de las 7 categorías en proporciones distintas
  (anclan FLOAT y MULH, que los programas reales casi no usan).
- **aes, dijkstra** — benchmarks reales (crypto, grafos).
- **gcd, sort, matmul, crc, strings** — cargas reales (de dominated_loops_v2).

Los `.elf` se reusan de `../metodo1/` y `../dominated_loops_v2/` (no se recompilan acá).

## Uso
```bash
# 1) Capturar histogramas + energía (con OpenOCD en :3333 y el ESP32 subiendo)
python3 run_method2.py --repeats 3 mix1 mix2 mix3 aes dijkstra gcd sort matmul crc strings
#    -> runs_m2.csv (crudo) + runs_m2_avg.csv (promedios)

# 2) Ajustar la regresión
python3 fit_m2.py
#    -> coeficientes, R^2, nº de condición, predicho vs medido

# 3) (opcional) validación held-out: deja un programa afuera y lo predice
python3 fit_m2.py --holdout dijkstra
```

## Archivos
- `run_method2.py` — captura JTAG/GDB + lectura del Sheet, con repeticiones.
- `regresion.py` — `build_design` (arma la matriz N) + `fit_coefficients` (lstsq).
- `fit_m2.py` — ajusta y reporta (R², condición, errores, held-out).
- `run_and_log.py`, `fetch_sheet.py` — captura de los 18 words y del P_avg.

## Nota (ver discusión de la tesis)
A 10 MHz M2 también colapsa a predecir ciclos × estática (`e_i ≈ P_idle·CPI_i/f`):
su R² alto NO significa que resuelva energía dinámica por categoría. Mismo muro
estructural que M1. Sirve para la comparación formal de los dos métodos.
