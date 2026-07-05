#!/usr/bin/env python3
"""Prueba los coeficientes de M2 (ajustados de runs_m2_avg.csv) contra programas.

Para cada programa: lo corre por JTAG/GDB, lee P_avg del Sheet, calcula la
energia/potencia medida y la estimada con los coeficientes M2, y compara.

Util para probar M2 contra programas HELD-OUT (no usados para calibrar M2),
p.ej. los bucles dominados (alu/mul/mulh/div/mem/ctrl/float) o valid/bsearch/
dotprod. Los .elf se buscan en metodo1/ y dominated_loops_v2/.

Uso:
    python3 probar_m2.py alu mul mulh div mem ctrl float
    python3 probar_m2.py valid bsearch dotprod
"""
import os
import sys
import time

import numpy as np

import fetch_sheet as fs
import regresion as m2
import run_and_log as ral

F_CLK = 10e6
MASK32 = 0xFFFFFFFF
HERE = os.path.dirname(os.path.abspath(__file__))
ELF_DIRS = [os.path.join(HERE, "..", "metodo1"),
            os.path.join(HERE, "..", "dominated_loops_v2")]


def find_elf(prog):
    for d in ELF_DIRS:
        p = os.path.join(d, f"{prog}.elf")
        if os.path.exists(p):
            return p
    return None


def wait_new_row(seen, timeout=120, poll=3):
    t0 = time.time()
    while time.time() - t0 < timeout:
        rows = fs.fetch_rows()
        if len(rows) > seen:
            return rows[-1], rows
        print(f"    esperando fila nueva en el Sheet... ({time.time()-t0:4.0f}s/{timeout}s)")
        time.sleep(poll)
    raise TimeoutError("timeout esperando fila nueva en el Sheet")


def main():
    progs = sys.argv[1:]
    if not progs:
        sys.exit("Uso: python3 probar_m2.py <programa> [...]  "
                 "(p.ej. alu mul mulh div mem ctrl float valid)")

    # Coeficientes M2 = ajuste por minimos cuadrados de runs_m2_avg.csv.
    runs = m2.load_runs(os.path.join(HERE, "runs_m2_avg.csv"))
    _, Ac, bc, _ = m2.build_design(runs)
    e_m2, _, _ = m2.fit_coefficients(Ac, bc)

    print("Coeficientes M2 usados (ajuste de runs_m2_avg.csv):")
    for (label, _), val in zip(m2.COLS, e_m2):
        unit = "pJ/ciclo" if label == "p_div" else "pJ/instr"
        print(f"   {label:8s} = {val*1e12:12.2f} {unit}")
    print()

    seen = len(fs.fetch_rows())
    print(f"{'programa':10s} {'T[s]':>7s} {'P_med':>8s} {'P_est':>8s} {'errP%':>7s}"
          f"   {'E_med[J]':>10s} {'E_est[J]':>10s}")
    errs = []
    for prog in progs:
        elf = find_elf(prog)
        if elf is None:
            print(f"{prog:10s}  ELF no encontrado")
            continue
        words = ral.run_one(elf)
        w16, w17 = int(words[16], 16), int(words[17], 16)
        T = ((w17 - w16) & MASK32) / F_CLK
        n = np.array([int(words[lo], 16) + (int(words[lo + 1], 16) << 32)
                      for _, lo in m2.COLS], float)

        row, rows = wait_new_row(seen)
        seen = len(rows)
        p_avg = row["p_avg"]

        E_med = p_avg * T
        E_est = float(e_m2 @ n)
        P_med = p_avg
        P_est = E_est / T
        err = 100 * (P_est - P_med) / P_med
        print(f"{prog:10s} {T:7.2f} {P_med:8.4f} {P_est:8.4f} {err:7.2f}"
              f"   {E_med:10.3f} {E_est:10.3f}")
        errs.append(abs(err))
        time.sleep(5)

    if len(errs) > 1:
        print(f"\nerror absoluto medio ({len(errs)} programas) = {sum(errs)/len(errs):.2f}%")


if __name__ == "__main__":
    main()
