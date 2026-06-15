#!/usr/bin/env python3
"""Metodo 1 (bucles dominados): corre cada <cat>.elf de dominated_loop_v2.S
R veces, captura los 18 registros por JTAG/GDB (run_and_log.run_one) y el
P_avg correspondiente del Google Sheet (fetch_sheet.fetch_rows -- se detecta
la fila nueva por conteo de filas), calcula e_i = P_avg*T/n_i por repeticion
(p_div para 'div', P_idle directo para 'idle') y acumula en runs_m1.csv. Al
final imprime media +/- desviacion estandar por categoria.

Requiere OpenOCD corriendo (gdb server riscv.cpu en :3333) y el Sheet de
fetch_sheet.py compartido como lector publico.

Uso:
    python3 run_method1.py --repeats 3 alu mul mulh div mem ctrl float idle
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

# categoria -> (word LO en results para n_i, unidad del coeficiente)
CATCOL = {
    "alu":   (0,  "pJ/instr"),
    "mul":   (2,  "pJ/instr"),
    "mulh":  (4,  "pJ/instr"),
    "div":   (14, "pJ/ciclo"),   # DIVCYC -> p_div (modelo hibrido)
    "mem":   (8,  "pJ/instr"),
    "ctrl":  (10, "pJ/instr"),
    "float": (12, "pJ/instr"),
    "idle":  (None, "W"),        # P_idle directo (baseline, sin e_i)
}


def words_to_val(words, lo):
    return int(words[lo], 16) + (int(words[lo + 1], 16) << 32)


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
    ap.add_argument("categories", nargs="+", choices=list(CATCOL))
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(here, "runs_m1.csv")
    new_file = not os.path.exists(out_path)

    seen = len(fs.fetch_rows())
    results = {cat: [] for cat in args.categories}

    with open(out_path, "a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["category", "repeat", "p_avg_w", "duration_ms",
                              "T_s", "value", "unit"] + [f"w{i}" for i in range(18)])

        for cat in args.categories:
            elf = os.path.join(here, f"{cat}.elf")
            lo, unit = CATCOL[cat]
            for r in range(1, args.repeats + 1):
                print(f"==> {cat} repeticion {r}/{args.repeats}")
                print("    capturando via JTAG/GDB (load + continue, ~15-20s)...")
                words = ral.run_one(elf)
                print("    captura OK, w16/w17 =", words[16], words[17])
                w16 = int(words[16], 16)
                w17 = int(words[17], 16)
                T = ((w17 - w16) & MASK32) / F_CLK

                row, rows = wait_new_row(seen)
                seen = len(rows)
                p_avg = row["p_avg"]

                if lo is None:
                    value = p_avg
                else:
                    n_i = words_to_val(words, lo)
                    value = p_avg * T / n_i * 1e12  # pJ

                writer.writerow([cat, r, p_avg, row["duration_ms"], T, value, unit] + words)
                f.flush()
                results[cat].append(value)
                print(f"    P_avg={p_avg:.6f} W  T={T:.3f}s  -> {value:.2f} {unit}")

                # Da chance al ESP32 de terminar de subir antes de la proxima corrida.
                time.sleep(5)

    print(f"\nGuardado en {out_path}\n")
    print("Resumen de esta corrida:")
    for cat, vals in results.items():
        unit = CATCOL[cat][1]
        mean = statistics.mean(vals)
        sd = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        cv = 100 * sd / mean if mean else float("nan")
        print(f"   {cat:6s} = {mean:12.2f} +/- {sd:8.2f} {unit:9s} (CV={cv:.2f}%, n={len(vals)})")


if __name__ == "__main__":
    main()
