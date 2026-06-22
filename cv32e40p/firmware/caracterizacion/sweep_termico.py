#!/usr/bin/env python3
"""Barrido termico del idle -> ajusta P_idle(T) (TFG).

Corre idle.elf CORTO (~15 s) en loop mientras la placa se CALIENTA, logueando para
cada medida la temperatura del die (XADC, por jtag) y el P_idle (ESP32). Al final
ajusta la recta P_idle(T) = a + b*T por minimos cuadrados. Como el leakage sube con
la temperatura, b > 0; esa recta corrige la deriva termica del piso.

IMPORTANTE: arrancar con la placa FRIA (recien prendida tras enfriarse) para tener
barrido de temperatura. Si la placa ya esta en equilibrio (~39 C) todos los puntos
caen juntos y no se puede ajustar.

Uso:
    python3 sweep_termico.py --n 40     # 40 medidas (~13 min) desde placa fria
    python3 sweep_termico.py --fit      # solo re-ajusta el CSV ya tomado
"""
import argparse
import csv
import os
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "comun"))
import jtag    # noqa: E402
import sheet   # noqa: E402

FUENTES = os.path.join(HERE, "metodo3_regresion", "fuentes")
ELF = os.path.join(HERE, "metodo3_regresion", "elf", "idle_sweep.elf")
CSV = os.path.join(HERE, "pidle_temp.csv")
RISCV = os.environ.get("RISCV", "/home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18")
CC = f"{RISCV}/bin/riscv32-unknown-elf-gcc"


def build_idle_corto():
    """idle de ~15 s (IDLE_REPS=50). idle.S es auto-contenido (su propio _start)."""
    subprocess.run(
        [CC, "-nostdlib", "-nostartfiles", "-static", "-Os", "-g", "-mabi=ilp32",
         "-Wl,-T,link.ld", "-Wl,--build-id=none", "-I.", "-march=rv32imc",
         "-DIDLE_REPS=50", "-o", ELF, "idle.S"],
        cwd=FUENTES, check=True)


def esperar_inbox(seen, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        filas = sheet.leer("inbox")
        if len(filas) > seen:
            return filas[-1], len(filas)
        time.sleep(3)
    raise TimeoutError("timeout esperando P_idle del ESP32")


def fit(csvpath):
    T, P = [], []
    with open(csvpath) as f:
        for r in csv.DictReader(f):
            if r["temp_C"] and r["P_idle_W"]:
                T.append(float(r["temp_C"]))
                P.append(float(r["P_idle_W"]))
    T, P = np.array(T), np.array(P)
    if len(T) < 3:
        print("pocos puntos para ajustar (>=3)")
        return
    spread = T.max() - T.min()
    A = np.vstack([np.ones_like(T), T]).T
    (a, b), *_ = np.linalg.lstsq(A, P, rcond=None)
    pred = a + b * T
    ss_tot = ((P - P.mean()) ** 2).sum()
    r2 = 1 - ((P - pred) ** 2).sum() / ss_tot if ss_tot > 0 else float("nan")
    print(f"\n=== AJUSTE P_idle(T) ===  (n={len(T)})")
    print(f"  P_idle(T) = {a:.4f} W + {b*1e3:.3f} mW/C * (T - 0)")
    print(f"  barrido T : {T.min():.1f} .. {T.max():.1f} C   ({spread:.1f} C)")
    print(f"  P_idle    : {P.min():.4f} .. {P.max():.4f} W   ({(P.max()-P.min())*1e3:.1f} mW)")
    print(f"  pendiente : {b*1e3:.2f} mW/C   R2={r2:.4f}")
    if spread < 3:
        print("  [AVISO] barrido < 3 C: arranca con la placa MAS fria para un ajuste util.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40, help="numero de medidas de idle")
    ap.add_argument("--fit", action="store_true", help="solo re-ajusta el CSV existente")
    args = ap.parse_args()

    if args.fit:
        fit(CSV)
        return

    build_idle_corto()
    # cada corrida arranca FRESCA: archiva un CSV previo para no mezclar bases de
    # P_idle de sesiones distintas (la deriva inter-sesion arruina el ajuste).
    if os.path.exists(CSV):
        bak = CSV.replace(".csv", time.strftime("_%Y%m%d_%H%M.csv.bak"))
        os.rename(CSV, bak)
        print(f"(corrida previa archivada en {os.path.basename(bak)})")
    seen = len(sheet.leer("inbox"))
    print("Barrido termico: arranca con la placa FRIA. Idle ~15 s x cada medida.\n")
    with open(CSV, "w", newline="") as fd:
        wr = csv.writer(fd)
        wr.writerow(["hora", "temp_C", "P_idle_W"])
        for i in range(1, args.n + 1):
            jtag.run_one(ELF)
            tC = jtag.ultima_temp_cC
            fila, seen = esperar_inbox(seen)
            P = float(str(fila["p_avg"]).replace(",", "."))
            t = f"{tC/100:.2f}" if tC is not None else ""
            wr.writerow([time.strftime("%H:%M:%S"), t, f"{P:.6f}"])
            fd.flush()
            print(f"  [{i:2d}/{args.n}]  T = {t} C   P_idle = {P:.4f} W")
    fit(CSV)


if __name__ == "__main__":
    main()
