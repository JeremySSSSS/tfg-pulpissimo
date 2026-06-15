#!/usr/bin/env python3
"""Lee las mediciones P_avg subidas por el ESP32 al Google Sheet, vía export
CSV (el sheet debe estar compartido como "Cualquiera con el enlace -> Lector",
no requiere OAuth).

Columnas del sheet: timestamp, profile, valor, p_avg, samples, duration_ms.
Los numeros vienen con coma decimal (locale es-ES); se normalizan a punto.

Uso:
    python3 fetch_sheet.py            # imprime todas las filas
    python3 fetch_sheet.py valid       # solo filas con profile == valid
"""
import csv
import io
import sys
import urllib.request

SHEET_ID = "1r-CPppIW4S9jlf-RBHkMZ-023qpQITgnOVqtr7Z4tpI"
GID = "478088243"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"


def fetch_rows():
    with urllib.request.urlopen(URL) as resp:
        text = resp.read().decode("utf-8")
    rows = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) != 6:
            continue  # filas vacias o malformadas
        timestamp, profile, valor, p_avg, samples, duration_ms = row
        try:
            parsed = {
                "timestamp": timestamp,
                "profile": profile,
                "p_avg": float(p_avg.replace(",", ".")),
                "samples": int(samples),
                "duration_ms": int(duration_ms),
            }
        except ValueError:
            continue  # encabezado u otra fila no numerica
        rows.append(parsed)
    return rows


def main(argv):
    want = argv[1] if len(argv) > 1 else None
    for r in fetch_rows():
        if want and r["profile"] != want:
            continue
        print(f"{r['timestamp']}  profile={r['profile']:10s} "
              f"p_avg={r['p_avg']:.6f} W  samples={r['samples']}  "
              f"duration_ms={r['duration_ms']}")


if __name__ == "__main__":
    main(sys.argv)
