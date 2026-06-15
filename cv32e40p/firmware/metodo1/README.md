# Método 1 — bucles dominados (clasificador v2, medición física)

Directorio limpio para la campaña M1. Una prueba por categoría, cada una ~32 s
a 10 MHz (duración fijada por `LOOP_COUNT` en cada wrapper `.S`).

## Archivos
- `<cat>.S` — un programa autocontenido por prueba (todo el bucle a la vista,
  sin `#ifdef` ni includes de cuerpo; solo incluye `platform.inc`).
  Categorías: `alu mul mulh div mem ctrl float idle`.
- `platform.inc`, `link.ld` — plataforma (16 CSR 0xBC0–0xBCF, mapa GPIO/L2).
- `Makefile` — `make all` compila los 8 `.elf` (float en rv32imfc, resto rv32imc).
- `run_method1.py` — ejecución automática + repeticiones (reusado).
- `run_and_log.py`, `fetch_sheet.py` — captura JTAG/GDB y lectura del Sheet.

## Uso
```bash
make all                  # genera los 8 .elf (~32 s c/u)
# con OpenOCD corriendo (gdb server :3333) y el Sheet del ESP32 publicado:
python3 run_method1.py --repeats 3 alu mul mulh div mem ctrl float idle
```
Resultado: `runs_m1.csv` (una fila por repetición: category, repeat, P_avg, T,
e_i = P_avg·T/n_i [p_div para div, P_idle para idle], + los 18 words de results).
Al final imprime media ± desviación y CV por categoría.

## Duraciones objetivo (~5 min @ 10 MHz — calibracion definitiva)
| cat | LOOP_COUNT | cic/iter aprox |
|-----|-----------:|---------------:|
| alu   |  45 000 000 | ~68  |
| mul   |  45 000 000 | ~68  |
| mulh  |   9 300 000 | ~324 |
| div   |   2 230 000 | ~1348 |
| mem   |  23 000 000 | ~131 |
| ctrl  |  22 800 000 | ~132 |
| float |  36 000 000 | ~84  |
| idle  | 750 000 000 | ~4   |

(El run previo de ~32 s quedo respaldado en `runs_m1_32s.csv`.)

La duración exacta sale de `mcycle` (w16/w17), no del estimado; los conteos solo
buscan superar los 30 s.
