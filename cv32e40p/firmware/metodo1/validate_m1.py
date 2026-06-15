#!/usr/bin/env python3
"""Validacion de los coeficientes del Metodo 1 (bucles dominados, runs_m1.csv)
contra TODOS los programas medidos con 3 repeticiones en runs_m2_avg.csv
(misma fuente de energia que usa M2 -> comparacion apples-to-apples).

e_M1 = media de las 3 repeticiones por categoria en runs_m1.csv (idle no entra:
el modelo E=Sum e_i*n_i no separa estatica, igual que en M2). Se predice
E_est = A @ e_M1 para cada programa y se compara con E_med = P_avg*T.

alu/div/mulh/float son LA MISMA dominada usada para calibrar M1 -> no son
held-out para M1. El resto (gcd/sort/matmul/crc/strings/valid/bsearch/dotprod)
son programas reales/mixtos nunca usados por M1: validacion held-out genuina.
Se marca con (*) cada programa held-out cuyo |err| individual supera el 10%.
"""
import csv
import os
import statistics

import numpy as np

import regresion as m2

SHARED_WITH_M1 = {"alu", "div", "mulh", "float"}


def load_m1_coeffs(path):
    vals = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            if row["unit"] == "W":
                continue  # idle: no entra al modelo E=Sum e_i*n_i
            vals.setdefault(row["category"], []).append(float(row["value"]))
    means = {cat: statistics.mean(v) for cat, v in vals.items()}
    e = np.zeros(len(m2.COLS))
    for j, (label, _) in enumerate(m2.COLS):
        cat = label[2:]  # "e_alu" -> "alu", "p_div" -> "div"
        e[j] = means[cat] * 1e-12
    return e


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    e_m1 = load_m1_coeffs(os.path.join(here, "runs_m1.csv"))

    # Coeficientes M1 = locales (32s, recien sacados). Programas mixtos reales
    # para validar = los medidos en dominated_loops_v2 (aqui solo hay dominados).
    avg_path = os.path.join(here, "..", "dominated_loops_v2", "runs_m2_avg.csv")
    if not os.path.exists(avg_path):
        raise SystemExit(f"{avg_path} no existe.")
    runs = m2.load_runs(avg_path)

    names, A, b, Ts = m2.build_design(runs)
    pred = A @ e_m1

    print("Coeficientes M1 (runs_m1.csv, media de 3 repeticiones):")
    for (label, _), val in zip(m2.COLS, e_m1):
        unit = "pJ/ciclo" if label == "p_div" else "pJ/instr"
        print(f"   {label:8s} = {val*1e12:12.2f} {unit}")

    print("\nValidacion de M1 (runs_m2_avg.csv, E_est = Sum e_i^M1 * n_i):")
    print(f"   {'name':10s} {'T[s]':>7s} {'E_med[J]':>10s} {'E_est[J]':>10s} {'err%':>8s}  held-out de M1?")
    errs_independent = []
    for nm, Em, Ee, T in zip(names, b, pred, Ts):
        err = 100 * (Ee - Em) / Em if Em else float("nan")
        if nm in SHARED_WITH_M1:
            tag = "NO (= dominada de M1)"
        else:
            tag = "SI" + ("  (*) >10%" if abs(err) > 10 else "")
            errs_independent.append(err)
        print(f"   {nm:10s} {T:7.2f} {Em:10.3f} {Ee:10.3f} {err:8.2f}  {tag}")

    mean_signed = statistics.mean(errs_independent)
    mean_abs = statistics.mean(abs(x) for x in errs_independent)
    over10 = sum(1 for x in errs_independent if abs(x) > 10)
    print(f"\nSolo programas held-out (n={len(errs_independent)}):")
    print(f"   error medio (con signo) = {mean_signed:6.2f}%")
    print(f"   error absoluto medio    = {mean_abs:6.2f}%")
    print(f"   programas con |err|>10% = {over10}/{len(errs_independent)} "
          f"({'OK por programa' if over10 == 0 else 'la media pasa pero NO todos por separado'})")


if __name__ == "__main__":
    main()
