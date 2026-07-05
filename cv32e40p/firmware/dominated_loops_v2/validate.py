#!/usr/bin/env python3
"""Validacion held-out de los coeficientes del Metodo 2.

Ajusta e_i con runs.csv (las 9 ejecuciones de calibracion) y los aplica a
ejecuciones NUEVAS, no usadas en el ajuste, leidas de runs_valid.csv
(p.ej. valid.elf: mezcla fija de las 7 categorias por iteracion). Reporta
la energia predicha (Sum e_i*n_i + p_div*c_div) contra la medida (P_avg*T).

Entrada de runs_valid.csv: mismo formato que runs.csv
    name, P_avg_W, w0, w1, ..., w17   (x/18xw &results)
"""
import os

import regresion as m2


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    cal_runs = m2.load_runs(os.path.join(here, "runs.csv"))
    _, A, b, _ = m2.build_design(cal_runs)
    e, dropped, _ = m2.fit_coefficients(A, b)

    val_path = os.path.join(here, "runs_valid.csv")
    val_runs = m2.load_runs(val_path)
    if not val_runs:
        print(f"{val_path} no tiene corridas todavia.")
        print("Agrega una fila:  name,P_avg_W,w0..w17  (x/18xw &results de valid.elf)")
        return

    names, Av, bv, Ts = m2.build_design(val_runs)
    pred = Av @ e

    print(f"Coeficientes ajustados con runs.csv ({len(cal_runs)} ejecuciones de calibracion):")
    for (label, _), val in zip(m2.COLS, e):
        unit = "pJ/ciclo" if label == "p_div" else "pJ/instr"
        tag = "   <- sin datos" if label in dropped else ""
        print(f"   {label:8s} = {val*1e12:12.2f} {unit}{tag}")

    print("\nValidacion held-out (corridas no usadas en el ajuste):")
    print(f"   {'name':10s} {'T[s]':>7s} {'E_med[J]':>10s} {'E_est[J]':>10s} {'err%':>7s}")
    for name, Em, Ee, T in zip(names, bv, pred, Ts):
        err = 100 * (Ee - Em) / Em if Em else float("nan")
        print(f"   {name:10s} {T:7.2f} {Em:10.3f} {Ee:10.3f} {err:7.2f}")


if __name__ == "__main__":
    main()
