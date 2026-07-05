#!/usr/bin/env python3
"""Valida M1 y M2 contra programas NUEVOS -- nunca usados para calibrar
ninguno de los dos metodos -- leidos de runs_m2_avg.csv (salida de
run_method2.py).

e_M1 = medias de runs_m1.csv (bucles dominados, 3 repeticiones).
e_M2 = ajuste de runs.csv (9 programas de calibracion, 1 medicion cada uno).

Uso:
    python3 run_method2.py --repeats 3 bsearch dotprod
    python3 validate_new.py bsearch dotprod
"""
import os
import sys

import regresion as m2
from validate_m1 import load_m1_coeffs


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    names_wanted = sys.argv[1:]
    if not names_wanted:
        sys.exit("Uso: python3 validate_new.py <programa> [<programa> ...]  "
                  "(deben estar en runs_m2_avg.csv)")

    e_m1 = load_m1_coeffs(os.path.join(here, "runs_m1.csv"))

    cal_runs = m2.load_runs(os.path.join(here, "runs.csv"))
    _, Ac, bc, _ = m2.build_design(cal_runs)
    e_m2, _, _ = m2.fit_coefficients(Ac, bc)

    new_path = os.path.join(here, "runs_m2_avg.csv")
    if not os.path.exists(new_path):
        sys.exit(f"{new_path} no existe todavia.\n"
                 f"Corre primero: python3 run_method2.py --repeats 3 {' '.join(names_wanted)}")
    all_new = m2.load_runs(new_path)
    new_runs = [r for r in all_new if r[0] in names_wanted]
    missing = set(names_wanted) - {r[0] for r in new_runs}
    if missing:
        sys.exit(f"No estan en {new_path}: {sorted(missing)}\n"
                  f"Corre primero: python3 run_method2.py --repeats 3 {' '.join(sorted(missing))}")

    names, A, b, Ts = m2.build_design(new_runs)
    pred_m1 = A @ e_m1
    pred_m2 = A @ e_m2

    print(f"{'name':10s} {'T[s]':>7s} {'E_med[J]':>10s} "
          f"{'E_est_M1':>10s} {'err_M1%':>8s} "
          f"{'E_est_M2':>10s} {'err_M2%':>8s}")
    for nm, Em, T, e1, e2 in zip(names, b, Ts, pred_m1, pred_m2):
        err1 = 100 * (e1 - Em) / Em if Em else float("nan")
        err2 = 100 * (e2 - Em) / Em if Em else float("nan")
        print(f"{nm:10s} {T:7.2f} {Em:10.3f} {e1:10.3f} {err1:8.2f} {e2:10.3f} {err2:8.2f}")


if __name__ == "__main__":
    main()
