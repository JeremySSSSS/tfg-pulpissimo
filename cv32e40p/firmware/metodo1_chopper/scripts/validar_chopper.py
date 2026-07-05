#!/usr/bin/env python3
"""Valida el modelo del chopper contra programas reales. El CALCULO de los
coeficientes vive en modelo.py (compartido con run_chopper.py, que los genera
al caracterizar). Aca solo se predice y se compara contra lo medido.

Uso:
    python3 validar_chopper.py                       # coeficientes + tabla sim + validacion guardada
    python3 validar_chopper.py --run sha256 md5 ...  # corre por JTAG, mide y predice
    python3 validar_chopper.py --tabla               # re-imprime validacion.csv guardada
"""
import argparse
import csv
import os
import time

import modelo
from modelo import MASK32, CATS, F_CLK, to_int, build_model, predict

HERE = modelo.HERE
ELF_DIRS = [os.path.join(HERE, "..", "benchmarks")]
SIM_CSV = os.path.join(HERE, "sim_potencia.csv")
VALID_CSV = os.path.join(HERE, "validacion.csv")     # medido (P_med + contadores)
COMP_CSV = os.path.join(HERE, "comparacion.csv")     # comparacion (P_med vs P_pred vs err)


def show_sim(DELTA):
    if not os.path.exists(SIM_CSV):
        return
    sim = {}
    with open(SIM_CSV) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or row[0] == "categoria":
                continue
            sim[row[0]] = float(row[2])
    print("\n=== Validacion cruzada: chopper (placa) vs sim (core aislado) [mW] ===")
    print(f"  {'cat':6s} {'chopper':>8s} {'sim':>6s}")
    for c in CATS:
        s = f"{sim[c]:6.1f}" if c in sim else "   --"
        print(f"  {c:6s} {DELTA[c]*1e3:8.2f} {s}")


def find_elf(prog):
    for d in ELF_DIRS:
        p = os.path.join(d, f"{prog}.elf")
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f"{prog}.elf no esta en benchmarks/")


def run_live(progs, P_IDLE, e_dyn, p_div):
    import fetch_sheet as fs
    import run_and_log as ral
    seen = len(fs.fetch_rows())
    modelo.ensure_fecha(VALID_CSV)
    new = not os.path.exists(VALID_CSV)
    fcsv = open(VALID_CSV, "a", newline="")
    wr = csv.writer(fcsv)
    if new:
        wr.writerow(["fecha", "name", "P_med_W", "T_s"] + [f"w{i}" for i in range(18)])
    print(f"\n{'programa':10s} {'P_med[W]':>9s} {'P_pred[W]':>10s} {'err%':>7s}  T[s]")
    for prog in progs:
        elf = find_elf(prog)
        print(f"==> corriendo {prog} por JTAG...")
        words = ral.run_one(elf)
        w = [to_int(x) for x in words]
        t0 = time.time()
        while time.time() - t0 < 180:
            rows = fs.fetch_rows()
            if len(rows) > seen:
                break
            time.sleep(3)
        else:
            raise TimeoutError("timeout esperando P_avg del ESP32")
        pbar = rows[-1]["p_avg"]
        seen = len(rows)
        T = ((w[17] - w[16]) & MASK32) / F_CLK
        P_pred = predict(w, P_IDLE, e_dyn, p_div)
        err = 100 * (P_pred - pbar) / pbar
        wr.writerow([modelo.now_str(), prog, f"{pbar:.6f}", f"{T:.3f}"] + words)
        fcsv.flush()
        print(f"{prog:10s} {pbar:9.4f} {P_pred:10.4f} {err:7.2f}  {T:5.1f}")
    fcsv.close()
    print(f"\nMediciones guardadas en {VALID_CSV}")
    tabla_guardada(P_IDLE, e_dyn, p_div)   # resumen completo + escribe comparacion.csv


def tabla_guardada(P_IDLE, e_dyn, p_div):
    if not os.path.exists(VALID_CSV):
        print("\n(todavia no hay validacion.csv; corre con --run <prog...>)")
        return
    print(f"\n{'programa':10s} {'T[s]':>7s} {'P_med[W]':>9s} {'P_pred[W]':>10s} {'err%':>7s}")
    errs = []
    out = open(COMP_CSV, "w", newline="")
    wr = csv.writer(out)
    wr.writerow(["fecha", "name", "T_s", "P_med_W", "P_pred_W", "err_pct"])
    with open(VALID_CSV) as f:
        for r in csv.DictReader(f):
            w = [to_int(r[f"w{i}"]) for i in range(18)]
            pbar = float(r["P_med_W"])
            T = float(r["T_s"])
            P_pred = predict(w, P_IDLE, e_dyn, p_div)
            err = 100 * (P_pred - pbar) / pbar
            errs.append(abs(err))
            print(f"{r['name']:10s} {T:7.1f} {pbar:9.4f} {P_pred:10.4f} {err:7.2f}")
            wr.writerow([r.get("fecha", ""), r["name"], f"{T:.3f}", f"{pbar:.6f}", f"{P_pred:.6f}", f"{err:.4f}"])
    out.close()
    if errs:
        print(f"\nerror absoluto medio = {sum(errs)/len(errs):.2f}%   max = {max(errs):.2f}%   (objetivo <10%)")
        print(f"Comparacion guardada en {COMP_CSV}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", nargs="+", metavar="PROG")
    ap.add_argument("--tabla", action="store_true", help="re-imprime validacion.csv")
    args = ap.parse_args()

    # Si existe coeficientes.csv se usa ESE (asi podes crearlo/editarlo a mano
    # para pruebas); si no, se calcula de chopper_results.csv + cpi_categorias.csv.
    if os.path.exists(modelo.COEF_CSV):
        DELTA, P_IDLE, CPI, e_dyn, p_div, nrep = modelo.load_coeffs()
        print(f"(coeficientes leidos de {os.path.basename(modelo.COEF_CSV)})")
    else:
        DELTA, P_IDLE, CPI, e_dyn, p_div, nrep = build_model()
    print(modelo.format_coeffs(DELTA, P_IDLE, CPI, e_dyn, p_div, nrep))

    if args.run:
        run_live(args.run, P_IDLE, e_dyn, p_div)
    elif args.tabla:
        tabla_guardada(P_IDLE, e_dyn, p_div)
    else:
        show_sim(DELTA)
        tabla_guardada(P_IDLE, e_dyn, p_div)


if __name__ == "__main__":
    main()
