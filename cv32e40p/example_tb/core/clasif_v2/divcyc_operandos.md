# Ciclos de ocupación del divisor según operandos (justificación del modelo híbrido)

Corrida del 2026-07-04 con `run_clasif_v2_xsim.sh` (XSim, RTL de este árbol,
bucle `loop_div.S`: 512 div/divu/rem/remu por corrida, ITERS=8).

| Operandos            | Comando                              | n_div | c_div  | ciclos/div | golden |
|----------------------|--------------------------------------|-------|--------|------------|--------|
| favorables (min)     | `LOOP=div DIVOPS=min ./run_...`      | 512   | 2048   | 4.0        | PASS   |
| aleatorios (default) | `LOOP=div ./run_...`                 | 512   | 11776  | 23.0       | PASS   |
| desfavorables (max)  | `LOOP=div DIVOPS=max ./run_...`      | 512   | 17408  | 34.0       | PASS   |

En los tres casos DIV_CYC coincidió ciclo a ciclo con el estimado del trace
(`golden_clasif.py`). Rango 8.5x: un costo fijo por instrucción no puede
representar la división; el término por ciclo p_div*c_div sí.
