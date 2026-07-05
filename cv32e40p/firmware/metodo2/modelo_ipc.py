#!/usr/bin/env python3
"""Demuestra que agregar los CICLOS (T, de mcycle) al modelo lo vuelve robusto
al IPC -- el arreglo del Problema A, sin tocar el RTL.

Compara dos modelos, ambos validados HELD-OUT (se deja un programa afuera del
ajuste y se predice):
  A) solo instrucciones:  E = sum e_i * n_i           <- ciego al IPC, falla
  B) ciclos + instrucc.:  E = a*T + sum e_din_i * n_i  <- T captura el IPC

El termino a*T es la energia estatica (a ~ P_idle); T sale de mcycle y refleja
los stalls/flushes que las instrucciones solas no ven. Por eso B predice bien
el codigo de bajo IPC (dijkstra) aunque no lo haya visto.
"""
import os
import numpy as np
import regresion as m2

HERE = os.path.dirname(os.path.abspath(__file__))
runs = m2.load_runs(os.path.join(HERE, "runs_m2_avg.csv"))


def fit_predict(holdout, use_time):
    cal = [r for r in runs if r[0] != holdout]
    names, A, b, Ts = m2.build_design(cal)
    if use_time:
        A = np.column_stack([A, np.array(Ts)])      # agrega columna de tiempo (ciclos)
    coef, *_ = np.linalg.lstsq(A, b, rcond=None)
    # held-out
    hn, Ah, bh, Th = m2.build_design([r for r in runs if r[0] == holdout])
    if use_time:
        Ah = np.column_stack([Ah, np.array(Th)])
    Eh = float(Ah @ coef)
    return 100 * (Eh - bh[0]) / bh[0], coef


print("Validacion HELD-OUT (se deja el programa afuera del ajuste y se predice):")
print(f"{'programa':10s} {'A: solo n_i':>14s} {'B: + tiempo T':>14s}")
worst = []
for r in runs:
    prog = r[0]
    errA, _ = fit_predict(prog, use_time=False)
    errB, cB = fit_predict(prog, use_time=True)
    flag = "  <-- bajo IPC" if prog == "dijkstra" else ""
    print(f"{prog:10s} {errA:13.2f}% {errB:13.2f}%{flag}")
    worst.append((abs(errA), abs(errB)))

mA = sum(w[0] for w in worst) / len(worst)
mB = sum(w[1] for w in worst) / len(worst)
print(f"\nerror absoluto medio held-out:  A (solo n_i) = {mA:.2f}%   "
      f"B (+ tiempo) = {mB:.2f}%")

# El coeficiente del tiempo en B deberia ~ P_idle (la potencia estatica)
_, cB = fit_predict("dijkstra", use_time=True)
print(f"\ncoeficiente del termino T (modelo B) = {cB[-1]:.3f} W   (~ P_idle, la estatica)")
