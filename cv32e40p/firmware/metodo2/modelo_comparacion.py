#!/usr/bin/env python3
"""Compara tres modelos de estimacion de energia por validacion leave-one-out
(deja cada programa afuera, ajusta con el resto, lo predice). Cuantifica cuanto
aporta cada componente:

  1) SOLO INSTRUCCIONES   E = sum e_i*n_i        (el clasificador solo)
  2) SOLO TIEMPO          E = a*T                (el reloj solo, a ~ P_idle)
  3) COMPLETO             E = a*T + sum e_i*n_i  (los dos)

Entrada: runs_m2_avg.csv. Salida: error held-out por programa + resumen.
"""
import os
import numpy as np
import regresion as m2

HERE = os.path.dirname(os.path.abspath(__file__))
runs = m2.load_runs(os.path.join(HERE, "runs_m2_avg.csv"))
names, N, E, Ts = m2.build_design(runs)
T = np.array(Ts)
M = len(names)


def design(idx, model):
    """matriz de diseno para el programa idx segun el modelo"""
    n = N[idx]
    if model == "instr":
        return n
    if model == "time":
        return np.array([T[idx]])
    if model == "full":
        return np.append(n, T[idx])


def loo(model):
    errs = []
    for i in range(M):
        rows = [j for j in range(M) if j != i]
        A = np.array([design(j, model) for j in rows])
        b = E[rows]
        coef, *_ = np.linalg.lstsq(A, b, rcond=None)
        pred = float(design(i, model) @ coef)
        errs.append(100 * (pred - E[i]) / E[i])
    return np.array(errs)

eI = loo("instr")
eT = loo("time")
eF = loo("full")

print("Error held-out (leave-one-out) por programa [%]:")
print(f"{'programa':10s} {'solo instr':>11s} {'solo tiempo':>12s} {'completo':>10s}")
for nm, a, b, c in zip(names, eI, eT, eF):
    print(f"{nm:10s} {a:11.2f} {b:12.2f} {c:10.2f}")

print("-" * 45)
def stats(e): return f"{np.mean(np.abs(e)):6.2f} {np.max(np.abs(e)):6.2f}"
print(f"{'abs medio / max':10s} {stats(eI):>11s}  {stats(eT):>11s}  {stats(eF):>9s}")
print()
print(f"  SOLO INSTRUCCIONES (clasificador): abs {np.mean(np.abs(eI)):.2f}%  (max {np.max(np.abs(eI)):.2f}%)")
print(f"  SOLO TIEMPO (reloj):               abs {np.mean(np.abs(eT)):.2f}%  (max {np.max(np.abs(eT)):.2f}%)")
print(f"  COMPLETO (tiempo + clasificador):  abs {np.mean(np.abs(eF)):.2f}%  (max {np.max(np.abs(eF)):.2f}%)")
print()
print(f"  -> el tiempo solo ya da {np.mean(np.abs(eT)):.2f}%; agregar el clasificador")
print(f"     lo mejora a {np.mean(np.abs(eF)):.2f}% (aporte ~{np.mean(np.abs(eT))-np.mean(np.abs(eF)):.2f} pp)")
