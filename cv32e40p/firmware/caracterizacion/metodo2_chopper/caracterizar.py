#!/usr/bin/env python3
"""Metodo 2 (CHOPPER) - caracterizacion. Para cada categoria corre su .elf (que
alterna categoria/idle con GPIO), recupera del Sheet ('inbox', donde sube el
ESP32 con chopper_read.ino) el DELTA = P(alto)-P(bajo) = dinamica de la categoria,
y P_idle. Convierte a coeficientes con el CPI de los bucles dominados:

    e_dyn_i = delta_i * CPI_i / f     [J/instr]   (alu,mul,mulh,mem,ctrl,float)
    p_div   = delta_div / f           [J/ciclo]    (div, hibrido)

Guarda: datos.csv (crudo), coeficientes.csv (formato comun), y sube ambos a la
pestaña 'chopper' del Sheet. Requiere OpenOCD :3333 y chopper_read.ino flasheado.

Uso:  python3 caracterizar.py --repeats 2 alu mul mulh div mem ctrl float
"""
import argparse
import csv
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "comun"))
import sheet   # noqa: E402
import jtag    # noqa: E402

F_CLK = 10e6
CATS = ["alu", "mul", "mulh", "div", "mem", "ctrl", "float"]
CPI_CSV = os.path.join(HERE, "cpi_categorias.csv")
DATOS_CSV = os.path.join(HERE, "datos.csv")
COEF_CSV = os.path.join(HERE, "coeficientes.csv")
HOJA = "chopper"


def cargar_cpi():
    cpi = {}
    with open(CPI_CSV) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or row[0] == "categoria":
                continue
            cpi[row[0]] = float(row[3])
    return cpi


def f2(x):
    return float(str(x).replace(",", "."))


def esperar_inbox(seen, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        filas = sheet.leer("inbox")
        if len(filas) > seen:
            return filas[-1], len(filas)
        print(f"    esperando el delta del ESP32... ({time.time()-t0:4.0f}s/{timeout}s)")
        time.sleep(3)
    raise TimeoutError("timeout esperando el delta en 'inbox'")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("categorias", nargs="+")
    ap.add_argument("--repeats", type=int, default=1)
    args = ap.parse_args()

    cpi = cargar_cpi()
    deltas = {c: [] for c in args.categorias}
    pidle = []
    seen = len(sheet.leer("inbox"))

    new = not os.path.exists(DATOS_CSV)
    fd = open(DATOS_CSV, "a", newline="")
    wd = csv.writer(fd)
    if new:
        wd.writerow(["fecha", "categoria", "rep", "delta_W", "P_idle_W", "avgH_W", "nH", "nL"])

    for cat in args.categorias:
        elf = os.path.join(HERE, "elf", f"{cat}.elf")
        if not os.path.exists(elf):
            print(f"{cat}: falta {elf} (corre 'make' en fuentes/)")
            continue
        for r in range(1, args.repeats + 1):
            print(f"==> {cat} rep {r}/{args.repeats}  (chopper ~5 min)")
            jtag.run_one(elf)                       # corre la alternancia hasta ebreak
            fila, seen = esperar_inbox(seen)
            delta = f2(fila["p_avg"])               # delta = avgH - avgL
            avgH = f2(fila["valor"])
            p_idle = avgH - delta                   # = avgL
            nH, nL = fila.get("samples", ""), fila.get("duration_ms", "")
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            wd.writerow([ts, cat, r, f"{delta:.6f}", f"{p_idle:.6f}", f"{avgH:.6f}", nH, nL]); fd.flush()
            sheet.subir(HOJA, categoria=cat, rep=r, delta_W=f"{delta:.6f}", P_idle_W=f"{p_idle:.6f}",
                        avgH_W=f"{avgH:.6f}", nH=nH, nL=nL)
            deltas[cat].append(delta)
            pidle.append(p_idle)
            print(f"    delta = {delta*1e3:.3f} mW   P_idle = {p_idle:.4f} W")
            time.sleep(3)
    fd.close()

    # --- coeficientes (formato comun) ---
    P_idle = statistics.mean(pidle)
    DELTA = {c: statistics.mean(v) for c, v in deltas.items() if v}
    with open(COEF_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([f"# Metodo 2 (chopper). Generado {time.strftime('%Y-%m-%d %H:%M:%S')}."
                    " coef = delta*CPI/f [J/instr], div = delta/f [J/ciclo]. CPI de cpi_categorias.csv"])
        w.writerow(["parametro", "coef", "unidad"])
        w.writerow(["P_idle", f"{P_idle:.6f}", "W"])
        for c in CATS:
            if c not in DELTA:
                continue
            if c == "div":
                w.writerow(["div", f"{DELTA['div']/F_CLK:.6e}", "J/ciclo"])
            else:
                w.writerow([c, f"{DELTA[c]*cpi[c]/F_CLK:.6e}", "J/instr"])
    print(f"\nP_idle = {P_idle:.4f} W")
    for c in CATS:
        if c in DELTA:
            print(f"  {c:6s} delta={DELTA[c]*1e3:7.3f} mW  (n={len(deltas[c])})")
    print(f"\nGuardado: {DATOS_CSV}, {COEF_CSV} + pestaña '{HOJA}' del Sheet.")


if __name__ == "__main__":
    main()
