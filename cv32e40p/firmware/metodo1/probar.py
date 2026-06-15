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
import csv
import os
import statistics
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


def load_m1_dynamic(path):
    """Modelo corregido: separa estatica de dinamica.
    Devuelve (P_idle [W], e_din [J/instr]) donde
      e_din_i = (P_loop_i - P_idle) * T_i / n_i   (energia dinamica por instruccion,
                solo el exceso sobre idle, medido en cada bucle dominado).
    El modelo es  E = P_idle*T + sum e_din_i * n_i  (T de mcycle -> ve el IPC)."""
    by_cat, p_idle = {}, []
    with open(path) as f:
        for r in csv.DictReader(f):
            if r["unit"] == "W":
                p_idle.append(float(r["p_avg_w"]))      # idle = linea base
            else:
                by_cat.setdefault(r["category"], []).append(r)
    P_idle = statistics.mean(p_idle)
    e_din = np.zeros(len(m2.COLS))
    for j, (label, lo) in enumerate(m2.COLS):
        cat = label[2:]                                  # "e_alu"->"alu", "p_div"->"div"
        vals = []
        for r in by_cat[cat]:
            p = float(r["p_avg_w"]); T = float(r["T_s"])
            ni = int(r[f"w{lo}"], 16) + (int(r[f"w{lo+1}"], 16) << 32)
            vals.append((p - P_idle) * T / ni)           # J por instruccion (dinamica)
        e_din[j] = statistics.mean(vals)
    return P_idle, e_din


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
    path = os.path.join(here, "runs_m1.csv")
    e = load_m1_coeffs(path)                    # modelo A: E = sum e_i*n_i
    P_idle, e_din = load_m1_dynamic(path)       # modelo B: E = P_idle*T + sum e_din_i*n_i

    print(f"P_idle = {P_idle:.4f} W   (linea base estatica)\n")
    print("Coeficientes: total (modelo A) vs dinamico (modelo B = exceso sobre idle)")
    print(f"   {'cat':8s} {'e_total':>14s} {'e_dinamico':>14s} {'din/total':>10s}")
    for (label, _), et, ed in zip(m2.COLS, e, e_din):
        unit = "pJ/cic" if label == "p_div" else "pJ/ins"
        frac = 100 * ed / et if et else 0.0
        print(f"   {label:8s} {et*1e12:11.1f}{unit} {ed*1e12:11.1f}{unit} {frac:9.2f}%")
    print("   (din/total chico => a 10 MHz casi toda la energia es ESTATICA)\n")

    seen = len(fs.fetch_rows())
    print(f"{'programa':10s} {'T[s]':>7s} {'P_med':>7s} | {'P_estA':>7s} {'errA%':>7s} |"
          f" {'P_estB':>7s} {'errB%':>7s}")
    print(f"{'':10s} {'':>7s} {'(med)':>7s} | {'(Σe·n)':>7s} {'':>7s} |"
          f" {'(Pidle·T+Σedin·n)':>7s}")
    rA, rB = [], []
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

        P_med = p_avg
        P_estA = float(e @ n) / T                          # modelo A (actual)
        P_estB = P_idle + float(e_din @ n) / T             # modelo B (corregido)
        errA = 100 * (P_estA - P_med) / P_med
        errB = 100 * (P_estB - P_med) / P_med
        print(f"{prog:10s} {T:7.2f} {P_med:7.4f} | {P_estA:7.4f} {errA:7.2f} |"
              f" {P_estB:7.4f} {errB:7.2f}")
        rA.append(abs(errA)); rB.append(abs(errB))
        time.sleep(5)                   # deja subir al ESP32

    if rA:
        print(f"\nerror absoluto medio en potencia ({len(rA)} prog):")
        print(f"   modelo A (actual, E=Σe·n)            = {sum(rA)/len(rA):.2f}%")
        print(f"   modelo B (corregido, E=Pidle·T+Σedin·n) = {sum(rB)/len(rB):.2f}%")


if __name__ == "__main__":
    main()
