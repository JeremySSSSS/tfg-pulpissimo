#!/usr/bin/env python3
"""Verificador COMUN a los 3 metodos. Carga cualquier .elf, lo corre por JTAG,
recupera el P_avg medido del Sheet (pestaña 'inbox'), y predice la potencia con
los coeficientes del metodo elegido (--metodo bucles|chopper|regresion). Compara
predicho vs medido y lo guarda en la pestaña 'verificacion' del Sheet + un CSV local.

Uso:
    python3 verificar.py --metodo chopper sha256 md5 floyd
    python3 verificar.py --metodo 1 aes            # 1=bucles 2=chopper 3=regresion
"""
import argparse
import csv
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "comun"))
import sheet      # noqa: E402
import modelo     # noqa: E402
import jtag       # noqa: E402

METODOS = {"bucles": "metodo1_bucles", "chopper": "metodo2_chopper",
           "regresion": "metodo3_regresion"}
ALIAS = {"1": "bucles", "2": "chopper", "3": "regresion"}
VERIF_CSV = os.path.join(HERE, "verificacion.csv")


def find_elf(prog):
    for cand in (os.path.join(HERE, "benchmarks", f"{prog}.elf"), prog):
        if os.path.exists(cand):
            return cand
    raise FileNotFoundError(f"{prog}.elf no esta en benchmarks/ (ni es una ruta valida)")


def esperar_inbox(seen, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        filas = sheet.leer("inbox")
        if len(filas) > seen:
            return filas[-1], len(filas)
        print(f"    esperando P_avg del ESP32... ({time.time()-t0:4.0f}s/{timeout}s)")
        time.sleep(3)
    raise TimeoutError("timeout esperando fila nueva en 'inbox'")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metodo", required=True, help="bucles|chopper|regresion (o 1|2|3)")
    ap.add_argument("programas", nargs="+")
    args = ap.parse_args()

    met = ALIAS.get(args.metodo, args.metodo)
    if met not in METODOS:
        sys.exit(f"metodo invalido: {args.metodo}  (usa bucles|chopper|regresion o 1|2|3)")
    coef_path = os.path.join(HERE, METODOS[met], "coeficientes.csv")
    if not os.path.exists(coef_path):
        sys.exit(f"falta {coef_path} -> caracteriza primero con metodo {met}")

    P_idle, coef = modelo.cargar_coeficientes(coef_path)
    print(f"=== Verificacion (metodo: {met}) ===")
    print(f"  P_idle = {P_idle:.4f} W   coeficientes: {', '.join(sorted(coef))}\n")

    new = not os.path.exists(VERIF_CSV)
    fcsv = open(VERIF_CSV, "a", newline="")
    wr = csv.writer(fcsv)
    if new:
        wr.writerow(["fecha", "metodo", "programa", "T_s", "P_med_W", "P_pred_W", "err_pct"]
                    + modelo.COLS_CONTADORES)

    seen = len(sheet.leer("inbox"))
    print(f"{'programa':12s} {'P_med[W]':>9s} {'P_pred[W]':>10s} {'err%':>7s}  T[s]")
    errs = []
    for prog in args.programas:
        elf = find_elf(prog)
        print(f"==> corriendo {prog} por JTAG...")
        w = [modelo.to_int(x) for x in jtag.run_one(elf)]
        fila, seen = esperar_inbox(seen)
        pbar = float(fila["p_avg"].replace(",", "."))
        T = ((w[17] - w[16]) & modelo.MASK32) / modelo.F_CLK
        P_pred = modelo.predecir(w, P_idle, coef)
        err = 100 * (P_pred - pbar) / pbar
        errs.append(abs(err))
        cont = modelo.contadores(w)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        sheet.subir("verificacion", metodo=met, programa=prog, T_s=f"{T:.3f}",
                    P_med_W=f"{pbar:.6f}", P_pred_W=f"{P_pred:.6f}", err_pct=f"{err:.4f}",
                    **{k: cont[k] for k in modelo.COLS_CONTADORES})
        wr.writerow([ts, met, prog, f"{T:.3f}", f"{pbar:.6f}", f"{P_pred:.6f}", f"{err:.4f}"]
                    + [cont[k] for k in modelo.COLS_CONTADORES])
        fcsv.flush()
        print(f"{prog:12s} {pbar:9.4f} {P_pred:10.4f} {err:7.2f}  {T:5.1f}")

    fcsv.close()
    if errs:
        print(f"\nerror absoluto medio = {sum(errs)/len(errs):.2f}%   "
              f"max = {max(errs):.2f}%   (objetivo <10%)")
    print(f"Guardado en {VERIF_CSV} y en la pestaña 'verificacion' del Sheet.")


if __name__ == "__main__":
    main()
