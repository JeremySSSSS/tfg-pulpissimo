#!/usr/bin/env python3
"""Metodo 2 (regresion): ajusta los coeficientes e_i por minimos cuadrados a
partir de runs_m2_avg.csv (histogramas n_i + energia E de M programas mixtos).

Resuelve el sistema sobredeterminado  E = N . e  (M ecuaciones, 7 incognitas)
con numpy.linalg.lstsq. Reporta coeficientes, R^2, numero de condicion (que tan
diverso es el set -> que tan estable el ajuste) y predicho vs medido por programa.

Opcional: --holdout <prog>  deja ese programa afuera del ajuste y lo predice como
validacion held-out (no usado para calibrar).

Uso:
    python3 fit_m2.py
    python3 fit_m2.py --holdout dijkstra
"""
import argparse
import os

import numpy as np

import regresion as m2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", default=None,
                    help="programa a dejar fuera del ajuste (validacion held-out)")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "runs_m2_avg.csv")
    if not os.path.exists(path):
        raise SystemExit(f"{path} no existe. Corre primero run_method2.py.")

    runs = m2.load_runs(path)
    cal = [r for r in runs if r[0] != args.holdout]
    hld = [r for r in runs if r[0] == args.holdout]

    names, A, b, Ts = m2.build_design(cal)
    e, dropped, Ar = m2.fit_coefficients(A, b)

    pred = A @ e
    ss_res = float(np.sum((b - pred) ** 2))
    ss_tot = float(np.sum((b - b.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    cond = float(np.linalg.cond(Ar))

    print("=" * 70)
    print(f"  Metodo 2 (regresion)  -  {len(cal)} programas, {len(m2.COLS)} incognitas")
    print("=" * 70)
    print("\nCoeficientes ajustados (minimos cuadrados sobre todos los programas):")
    for (label, _), val in zip(m2.COLS, e):
        unit = "pJ/ciclo" if label == "p_div" else "pJ/instr"
        tag = "   <- sin datos (categoria no ejercida)" if label in dropped else ""
        print(f"   {label:8s} = {val*1e12:12.2f} {unit}{tag}")

    print(f"\n  R^2                 = {r2:.5f}")
    print(f"  Numero de condicion = {cond:.2f}", end="")
    print("   <- ALTO: set poco diverso, ajuste inestable" if cond > 1e3 else "   (ok, set diverso)")

    print("\nPredicho vs medido por programa (calibracion):")
    print(f"   {'name':10s} {'T[s]':>7s} {'E_med[J]':>10s} {'E_est[J]':>10s} {'err%':>7s}")
    for nm, Em, Ee, T in zip(names, b, pred, Ts):
        err = 100 * (Ee - Em) / Em if Em else float("nan")
        print(f"   {nm:10s} {T:7.2f} {Em:10.3f} {Ee:10.3f} {err:7.2f}")

    if hld:
        vn, Av, bv, Tv = m2.build_design(hld)
        pv = Av @ e
        print(f"\nValidacion HELD-OUT ('{args.holdout}', NO usado para calibrar):")
        for nm, Em, Ee, T in zip(vn, bv, pv, Tv):
            err = 100 * (Ee - Em) / Em if Em else float("nan")
            print(f"   {nm:10s} {T:7.2f} {Em:10.3f} {Ee:10.3f} {err:7.2f}")


if __name__ == "__main__":
    main()
