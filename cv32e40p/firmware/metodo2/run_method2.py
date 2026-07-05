#!/usr/bin/env python3
"""Metodo 2 (regresion): corre cada programa de calibracion (y opcionalmente
'valid' para la validacion held-out) R veces, captura los 18 registros por
JTAG/GDB (run_and_log.run_one) y el P_avg correspondiente del Google Sheet
(fetch_sheet.fetch_rows -- se detecta la fila nueva por conteo de filas), y
acumula en runs_m2.csv (una fila por repeticion).

Al final promedia P_avg por programa (w0..w17 son deterministicos: se toma
la primera repeticion) y escribe runs_m2_avg.csv en el formato de
regresion.load_runs (name,P_avg_W,w0..w17), listo para refit_m2.py.

Requiere OpenOCD corriendo (gdb server riscv.cpu en :3333) y el Sheet de
fetch_sheet.py compartido como lector publico.

Uso:
    python3 run_method2.py --repeats 3 alu div gcd sort matmul crc strings mulh float valid
"""
import argparse
import csv
import os
import statistics
import time

import fetch_sheet as fs
import run_and_log as ral

F_CLK = 10e6
MASK32 = 0xFFFFFFFF

_HERE = os.path.dirname(os.path.abspath(__file__))
# Los elfs del set de calibracion viven en metodo1/ (mix1/2/3, aes, dijkstra)
# y en dominated_loops_v2/ (gcd, sort, matmul, crc, strings). Se buscan en ambos.
ELF_DIRS = [os.path.join(_HERE, "..", "metodo1"),
            os.path.join(_HERE, "..", "dominated_loops_v2")]


def find_elf(prog):
    for d in ELF_DIRS:
        p = os.path.join(d, f"{prog}.elf")
        if os.path.exists(p):
            return p
    raise FileNotFoundError(
        f"{prog}.elf no esta en metodo1/ ni dominated_loops_v2/ "
        f"(compila ahi con 'make {prog}.elf')")


def wait_new_row(seen, timeout=120, poll=3):
    t0 = time.time()
    while time.time() - t0 < timeout:
        rows = fs.fetch_rows()
        if len(rows) > seen:
            return rows[-1], rows
        elapsed = time.time() - t0
        print(f"    esperando fila nueva en el Sheet... ({elapsed:4.0f}s/{timeout}s)")
        time.sleep(poll)
    raise TimeoutError("timeout esperando fila nueva en el Sheet")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("programs", nargs="+")
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    raw_path = os.path.join(here, "runs_m2.csv")
    avg_path = os.path.join(here, "runs_m2_avg.csv")
    new_file = not os.path.exists(raw_path)

    seen = len(fs.fetch_rows())
    captures = {prog: [] for prog in args.programs}  # prog -> list of (p_avg, words)

    with open(raw_path, "a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["name", "repeat", "p_avg_w", "duration_ms", "T_s"]
                             + [f"w{i}" for i in range(18)])

        for prog in args.programs:
            elf = find_elf(prog)
            for r in range(1, args.repeats + 1):
                print(f"==> {prog} repeticion {r}/{args.repeats}")
                print("    capturando via JTAG/GDB (load + continue, ~15-20s)...")
                words = ral.run_one(elf)
                print("    captura OK, w16/w17 =", words[16], words[17])
                w16 = int(words[16], 16)
                w17 = int(words[17], 16)
                T = ((w17 - w16) & MASK32) / F_CLK

                row, rows = wait_new_row(seen)
                seen = len(rows)
                p_avg = row["p_avg"]

                writer.writerow([prog, r, p_avg, row["duration_ms"], T] + words)
                f.flush()
                captures[prog].append((p_avg, words))
                print(f"    P_avg={p_avg:.6f} W  T={T:.3f}s")

                # Da chance al ESP32 de terminar de subir antes de la proxima corrida.
                time.sleep(5)

    print(f"\nGuardado en {raw_path}\n")
    print("Resumen de repetibilidad (P_avg):")

    # Conserva filas de programas de corridas previas que no esten en esta
    # invocacion (runs_m2_avg.csv actua como cache acumulativo por programa).
    existing = {}
    if os.path.exists(avg_path):
        with open(avg_path, newline="") as f:
            for row in csv.reader(f):
                if row and row[0] != "name":
                    existing[row[0]] = row

    for prog, caps in captures.items():
        p_avgs = [p for p, _ in caps]
        mean = statistics.mean(p_avgs)
        sd = statistics.pstdev(p_avgs) if len(p_avgs) > 1 else 0.0
        cv = 100 * sd / mean if mean else float("nan")
        print(f"   {prog:8s} P_avg = {mean:.6f} +/- {sd:.6f} W (CV={cv:.4f}%, n={len(p_avgs)})")
        words0 = caps[0][1]
        existing[prog] = [prog, f"{mean:.6f}"] + words0

    with open(avg_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "P_avg_W"] + [f"w{i}" for i in range(18)])
        for row in existing.values():
            writer.writerow(row)

    print(f"\nGuardado en {avg_path}")
    print("Siguiente paso: python3 refit_m2.py")


if __name__ == "__main__":
    main()
