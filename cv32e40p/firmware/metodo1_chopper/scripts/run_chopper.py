#!/usr/bin/env python3
"""Captura la medicion diferencial (chopper) por categoria.

Para cada categoria: carga y corre <cat>.elf por JTAG/GDB (alterna categoria/idle
~5 min), y al terminar lee del Sheet el DELTA que subio el ESP32 (potencia
dinamica de la categoria sobre el idle, ya con la deriva cancelada).

El ESP32 debe tener flasheado chopper_read.ino. Requiere OpenOCD en :3333.

Uso:
    python3 run_chopper.py alu mul mulh div mem ctrl float
    python3 run_chopper.py --repeats 2 alu div ctrl
"""
import argparse
import csv
import os
import statistics
import time

import fetch_sheet as fs
import run_and_log as ral

HERE = os.path.dirname(os.path.abspath(__file__))


def wait_new_row(seen, timeout=180, poll=3):
    t0 = time.time()
    while time.time() - t0 < timeout:
        rows = fs.fetch_rows()
        if len(rows) > seen:
            return rows[-1], rows
        print(f"    esperando el delta del ESP32... ({time.time()-t0:4.0f}s/{timeout}s)")
        time.sleep(poll)
    raise TimeoutError("timeout esperando el delta en el Sheet")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("categories", nargs="+")
    ap.add_argument("--repeats", type=int, default=1)
    args = ap.parse_args()

    out = os.path.join(HERE, "chopper_results.csv")
    import modelo
    modelo.ensure_fecha(out)
    new = not os.path.exists(out)
    seen = len(fs.fetch_rows())
    acc = {c: [] for c in args.categories}   # delta (dinamica)
    pbase = []                                # P_idle (fase pasiva) de cada corrida

    with open(out, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["fecha", "categoria", "repeticion", "delta_W", "P_idle_W", "n_alto", "n_bajo"])
        for cat in args.categories:
            elf = os.path.join(HERE, "..", "elf", f"{cat}.elf")
            if not os.path.exists(elf):
                print(f"{cat}: no existe {elf} (corre 'make' en fuentes/)")
                continue
            for r in range(1, args.repeats + 1):
                print(f"==> {cat} repeticion {r}/{args.repeats}  (chopper ~5 min, paciencia)")
                ral.run_one(elf)                      # corre ~5 min hasta ebreak
                row, rows = wait_new_row(seen)
                seen = len(rows)
                delta = row["p_avg"]                  # delta = avgH - avgL (dinamica)
                avgH = row["valor"]                   # potencia fase categoria
                p_idle = avgH - delta                 # = avgL = base pasiva
                nH, nL = row["samples"], row["duration_ms"]
                w.writerow([modelo.now_str(), cat, r, delta, p_idle, nH, nL]); f.flush()
                acc[cat].append(delta)
                pbase.append(p_idle)
                print(f"    DELTA = {delta*1000:.3f} mW   P_idle(base) = {p_idle:.4f} W  (nH={nH} nL={nL})")
                time.sleep(5)

    print("\n=== METODO 1 (chopper): resultado fisico ===")
    if pbase:
        print(f"  P_idle (linea base pasiva, promedio) = {statistics.mean(pbase):.4f} W\n")
    print("  Potencia dinamica por categoria (sobre el reposo):")
    for cat, ds in acc.items():
        if not ds:
            continue
        m = statistics.mean(ds)
        sd = statistics.pstdev(ds) if len(ds) > 1 else 0.0
        print(f"     {cat:6s} = {m*1000:8.3f} mW  (+/- {sd*1000:.3f}, n={len(ds)})")
    print(f"\nMediciones guardadas en {out}")

    # Genera los COEFICIENTES del modelo desde la caracterizacion recien medida
    # (delta de chopper_results.csv x CPI de cpi_categorias.csv). Mismo modulo que
    # usa validar_chopper.py -> el coeficiente sale de la propia caracterizacion.
    try:
        import modelo
        coef = modelo.build_model()
        print("\n" + modelo.format_coeffs(*coef))
        print(f"\nCoeficientes guardados en {modelo.write_coeffs(*coef)}")
    except (FileNotFoundError, KeyError) as e:
        print(f"\n(coeficientes NO generados: falta {e}. Hacen falta las 7 categorias en "
              f"chopper_results.csv + cpi_categorias.csv -> corre 'python3 recuperar_datos.py')")


if __name__ == "__main__":
    main()
