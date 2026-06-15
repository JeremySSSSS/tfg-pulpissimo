#!/usr/bin/env python3
"""Prueba los coeficientes M1 de HOY (metodo1/runs_m1.csv) contra un programa real.

Para cada programa que le pases:
  1. lo corre en hardware por JTAG/GDB (captura los 18 words),
  2. lee su P_avg real del Sheet (lo que midio el ESP32),
  3. calcula E_med = P_avg * T  (energia REAL medida),
  4. calcula E_est = sum e_i^M1 * n_i  (energia ESTIMADA con los coef de hoy),
  5. imprime ambas y el error.

Los .elf de los programas reales se toman de ../dominated_loops_v2/.

Requiere OpenOCD corriendo (:3333) y el Sheet del ESP32 publicado.

Uso:
    python3 probar.py valid
    python3 probar.py gcd sort crc valid bsearch dotprod
"""
import os
import sys
import time

import numpy as np

import fetch_sheet as fs
import regresion as m2
import run_and_log as ral
from validate_m1 import load_m1_coeffs

F_CLK = 10e6
MASK32 = 0xFFFFFFFF
HERE = os.path.dirname(os.path.abspath(__file__))
# Busca el .elf primero local (mix1/mix2/mix3), luego en dominated_loops_v2
# (valid/gcd/sort/crc/...).
ELF_DIRS = [HERE, os.path.join(HERE, "..", "dominated_loops_v2")]


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
        sys.exit("Uso: python3 probar.py <programa> [<programa> ...]   "
                 "(p.ej. valid gcd sort crc bsearch dotprod)")

    here = os.path.dirname(os.path.abspath(__file__))
    e = load_m1_coeffs(os.path.join(here, "runs_m1.csv"))   # coeficientes de HOY

    print("Coeficientes M1 usados (runs_m1.csv de hoy):")
    for (label, _), val in zip(m2.COLS, e):
        unit = "pJ/ciclo" if label == "p_div" else "pJ/instr"
        print(f"   {label:8s} = {val*1e12:12.2f} {unit}")
    print()

    seen = len(fs.fetch_rows())
    print(f"{'programa':10s} {'T[s]':>7s} {'P_med[W]':>9s} {'P_est[W]':>9s} {'errP%':>7s}"
          f"   {'E_med[J]':>10s} {'E_est[J]':>10s}")
    results = []
    for prog in progs:
        elf = find_elf(prog)
        if elf is None:
            print(f"{prog:10s}  ELF no encontrado (ni local ni en dominated_loops_v2)")
            continue
        words = ral.run_one(elf)
        w16, w17 = int(words[16], 16), int(words[17], 16)
        T = ((w17 - w16) & MASK32) / F_CLK
        n = np.array([int(words[lo], 16) + (int(words[lo + 1], 16) << 32)
                      for _, lo in m2.COLS], float)

        row, rows = wait_new_row(seen)
        seen = len(rows)
        p_avg = row["p_avg"]

        E_med = p_avg * T               # energia real medida (P_avg * T)
        E_est = float(e @ n)            # energia estimada con coef de hoy
        P_med = p_avg                   # potencia real medida por el ESP32
        P_est = E_est / T               # potencia estimada = E_est / T
        err = 100 * (P_est - P_med) / P_med   # = error en energia (T se cancela)
        print(f"{prog:10s} {T:7.2f} {P_med:9.4f} {P_est:9.4f} {err:7.2f}"
              f"   {E_med:10.3f} {E_est:10.3f}")
        results.append((prog, err))
        time.sleep(5)                   # deja subir al ESP32

    if len(results) > 1:
        errs = [abs(er) for _, er in results]
        print(f"\nerror absoluto medio en potencia ({len(errs)} programas) = "
              f"{sum(errs)/len(errs):.2f}%")


if __name__ == "__main__":
    main()
