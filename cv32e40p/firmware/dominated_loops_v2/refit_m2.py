#!/usr/bin/env python3
"""Reajusta el Metodo 2 con runs_m2_avg.csv (salida de run_method2.py: P_avg
promediado sobre varias repeticiones por programa, w0..w17 deterministicos).

Separa la fila 'valid' (si esta presente) como validacion held-out -- el
resto son las ejecuciones de calibracion. Reporta:
  - coeficientes nuevos (runs_m2_avg) vs los originales (runs.csv, una sola
    medicion por programa)
  - R^2 y numero de condicion del ajuste nuevo
  - predicho vs medido por ejecucion de calibracion
  - validacion held-out contra 'valid' (si esta en runs_m2_avg.csv)
"""
import os

import numpy as np

import regresion as m2


def main():
    here = os.path.dirname(os.path.abspath(__file__))

    avg_path = os.path.join(here, "runs_m2_avg.csv")
    runs = m2.load_runs(avg_path)
    if not runs:
        print(f"{avg_path} no existe o esta vacio. Corre primero run_method2.py.")
        return

    # El set de calibracion de M2 es FIJO: los 9 programas de runs.csv. Otros
    # nombres en runs_m2_avg.csv (p.ej. bsearch/dotprod para validate_new.py)
    # se ignoran aqui -- no deben contaminar el ajuste de M2.
    cal_names = {r[0] for r in m2.load_runs(os.path.join(here, "runs.csv"))}
    cal_runs = [r for r in runs if r[0] in cal_names]
    val_runs = [r for r in runs if r[0] == "valid"]
    ignored = sorted({r[0] for r in runs} - cal_names - {"valid"})
    if ignored:
        print(f"(ignorando en runs_m2_avg.csv, no son calibracion de M2: {ignored})\n")

    names, A, b, Ts = m2.build_design(cal_runs)
    e, dropped, Ar = m2.fit_coefficients(A, b)

    pred = A @ e
    ss_res = float(np.sum((b - pred) ** 2))
    ss_tot = float(np.sum((b - b.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    cond = float(np.linalg.cond(Ar))

    # Coeficientes originales (runs.csv, una sola medicion por programa) para comparar.
    orig_path = os.path.join(here, "runs.csv")
    orig_e = None
    if os.path.exists(orig_path):
        orig_runs = m2.load_runs(orig_path)
        _, Ao, bo, _ = m2.build_design(orig_runs)
        orig_e, _, _ = m2.fit_coefficients(Ao, bo)

    print("=" * 72)
    print(f"  Metodo 2 reajustado con runs_m2_avg.csv "
          f"({len(cal_runs)} ejecuciones, {len(m2.COLS)} incognitas)")
    print("=" * 72)

    print(f"\n{'coef':10s} {'runs.csv (1 medicion)':>22s} {'runs_m2_avg (promedio)':>24s} {'diff%':>8s}")
    for j, (label, _) in enumerate(m2.COLS):
        unit = "pJ/ciclo" if label == "p_div" else "pJ/instr"
        tag = "  <- sin datos" if label in dropped else ""
        new_v = e[j] * 1e12
        if orig_e is not None:
            old_v = orig_e[j] * 1e12
            diff = 100 * (new_v - old_v) / old_v if old_v else float("nan")
            print(f"{label:10s} {old_v:22.2f} {new_v:24.2f} {diff:8.2f}{tag}")
        else:
            print(f"{label:10s} {'--':>22s} {new_v:24.2f}{tag}")

    print(f"\n  R^2                 = {r2:.5f}")
    print(f"  Numero de condicion = {cond:.3e}", end="")
    print("   <- ALTO: matriz mal condicionada" if cond > 1e3 else "   (ok)")

    print("\nPredicho vs medido (calibracion, runs_m2_avg.csv):")
    print(f"   {'name':10s} {'T[s]':>7s} {'E_med[J]':>10s} {'E_est[J]':>10s} {'err%':>7s}")
    for nm, Em, Ee, T in zip(names, b, pred, Ts):
        err = 100 * (Ee - Em) / Em if Em else float("nan")
        print(f"   {nm:10s} {T:7.2f} {Em:10.3f} {Ee:10.3f} {err:7.2f}")

    if val_runs:
        vnames, Av, bv, Tv = m2.build_design(val_runs)
        predv = Av @ e
        print("\nValidacion held-out ('valid', promedio de varias corridas):")
        print(f"   {'name':10s} {'T[s]':>7s} {'E_med[J]':>10s} {'E_est[J]':>10s} {'err%':>7s}")
        for nm, Em, Ee, T in zip(vnames, bv, predv, Tv):
            err = 100 * (Ee - Em) / Em if Em else float("nan")
            print(f"   {nm:10s} {T:7.2f} {Em:10.3f} {Ee:10.3f} {err:7.2f}")
    else:
        print("\n(no hay fila 'valid' en runs_m2_avg.csv -- sin validacion held-out)")


if __name__ == "__main__":
    main()
