#!/usr/bin/env python3
"""Aplica el modelo con TIEMPO a los coeficientes de M1 (bucles dominados).

M1 calibra e_i en bucles aislados; aca se aplican esos coeficientes FIJOS a los
programas reales (../metodo2/runs_m2_avg.csv), que son todos held-out para M1
(no se usaron para calibrar). Compara:
  A) M1 solo instrucciones:  E = sum e_i^M1 * n_i
  B) M1 + tiempo:            E = P_idle*T + sum e_din_i^M1 * n_i

P_idle y e_din salen del mismo M1 (runs_m1.csv): la idle da P_idle, y cada
e_din_i = (P_loop_i - P_idle)*T/n_i es la energia dinamica por instruccion.
"""
import csv
import os
import numpy as np

import regresion as m2
from validate_m1 import load_m1_coeffs
from probar import load_m1_dynamic

HERE = os.path.dirname(os.path.abspath(__file__))
F_CLK = 10e6
MASK32 = 0xFFFFFFFF

e_tot = load_m1_coeffs(os.path.join(HERE, "runs_m1.csv"))            # totales
P_idle, e_din = load_m1_dynamic(os.path.join(HERE, "runs_m1.csv"))   # base + dinamicos

test_path = os.path.join(HERE, "..", "metodo2", "runs_m2_avg.csv")
runs = m2.load_runs(test_path)
names, A, b, Ts = m2.build_design(runs)

print(f"Coeficientes M1 aplicados a programas reales (held-out para M1).  P_idle={P_idle:.3f} W\n")
print(f"{'programa':10s} {'A: solo n_i':>14s} {'B: + tiempo T':>14s}")
eA, eB = [], []
for nm, Em, n, T in zip(names, b, A, Ts):
    EA = float(e_tot @ n)                  # A: total
    EB = P_idle * T + float(e_din @ n)     # B: estatica(tiempo) + dinamica
    errA = 100 * (EA - Em) / Em
    errB = 100 * (EB - Em) / Em
    flag = "  <-- bajo IPC" if nm == "dijkstra" else ""
    print(f"{nm:10s} {errA:13.2f}% {errB:13.2f}%{flag}")
    eA.append(abs(errA)); eB.append(abs(errB))

print(f"\nerror absoluto medio:  A (solo n_i) = {sum(eA)/len(eA):.2f}%   "
      f"B (+ tiempo) = {sum(eB)/len(eB):.2f}%")
