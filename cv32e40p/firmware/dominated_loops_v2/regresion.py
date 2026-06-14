#!/usr/bin/env python3
"""Metodo 2 — regresion por histograma para el clasificador v2.

Resuelve  E = N . e  por minimos cuadrados (ec. de la tesis), donde cada fila
es una ejecucion: E la energia medida y N el histograma de instrucciones por
categoria. La columna de DIVISION usa c_div (ciclos), no n_div (modelo hibrido);
su coeficiente es p_div (energia por ciclo de division).

Entrada: runs.csv (misma carpeta). Una fila por ejecucion:
    name, P_avg_W, w0, w1, ..., w17
donde w0..w17 son los 18 words de 'results' (x/18xw 0x1c0082c0), en hex (0x..)
o decimal. P_avg_W es la potencia promedio de la ventana (del ESP32).

Salida: coeficientes e_i, p_div, R^2, numero de condicion, y predicho vs medido.

Sin separar potencia estatica (supuesto del modelo): queda absorbida en los e_i.
"""
import csv
import os
import sys

try:
    import numpy as np
except ImportError:
    sys.exit("Falta numpy:  pip install numpy")

F_CLK = 10e6  # Hz (medir con frequency_probe; ajustar si cambia)
MASK32 = 0xFFFFFFFF

# Columnas del modelo y su word LO en 'results'. DIV usa c_div (DIVCYC), no n_div.
COLS = [
    ("e_alu",   0),    # n_alu
    ("e_mul",   2),    # n_mul
    ("e_mulh",  4),    # n_mulh
    ("p_div",  14),    # c_div  (DIVCYC) — hibrido
    ("e_mem",   8),    # n_mem
    ("e_ctrl", 10),    # n_ctrl
    ("e_float",12),    # n_float
]


def to_int(s):
    s = s.strip()
    return int(s, 16) if s.lower().startswith("0x") else int(s)


def load_runs(path):
    runs = []
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0].strip().startswith("#") or row[0].strip() == "name":
                continue
            name = row[0].strip()
            pbar = float(row[1])
            w = [to_int(x) for x in row[2:20]]
            runs.append((name, pbar, w))
    return runs


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "runs.csv")
    runs = load_runs(path)
    if len(runs) < len(COLS):
        print(f"Aviso: {len(runs)} ejecuciones para {len(COLS)} incognitas. "
              f"Necesitas M > N ({len(COLS)}) para sobredeterminar.\n")

    names, A, b, Ts = [], [], [], []
    for name, pbar, w in runs:
        val = lambda lo: w[lo] + (w[lo + 1] << 32)          # contador 64b LO/HI
        T_cyc = (w[17] - w[16]) & MASK32                    # mcycle fin-ini (wrap)
        T = T_cyc / F_CLK
        E = pbar * T                                        # Joules
        A.append([val(lo) for _, lo in COLS])
        b.append(E)
        Ts.append(T)
        names.append(name)

    A = np.array(A, dtype=float)
    b = np.array(b, dtype=float)

    # Categorias sin ninguna ejecucion que las ejercite -> columna vacia
    # (singular). Se resuelven solo las que tienen datos.
    active = [j for j in range(A.shape[1]) if np.any(A[:, j] != 0)]
    dropped = [COLS[j][0] for j in range(len(COLS)) if j not in active]
    Ar = A[:, active]
    er, *_ = np.linalg.lstsq(Ar, b, rcond=None)
    e = np.zeros(len(COLS))
    for idx, j in enumerate(active):
        e[j] = er[idx]

    pred = A @ e
    ss_res = float(np.sum((b - pred) ** 2))
    ss_tot = float(np.sum((b - b.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    cond = float(np.linalg.cond(Ar))

    print("=" * 64)
    print(f"  Regresion Metodo 2  ({len(runs)} ejecuciones, {len(COLS)} incognitas, "
          f"f_clk={F_CLK/1e6:.0f} MHz)")
    print("=" * 64)
    print("\nCoeficientes (energia por instruccion; p_div por ciclo de division):")
    for (label, _), val in zip(COLS, e):
        unit = "pJ/ciclo" if label == "p_div" else "pJ/instr"
        tag = "   <- sin datos (categoria no medida)" if label in dropped else ""
        print(f"   {label:8s} = {val*1e12:12.2f} {unit}{tag}")

    print(f"\n  R^2                 = {r2:.5f}")
    print(f"  Numero de condicion = {cond:.3e}", end="")
    if cond > 1e3:
        print("   <- ALTO: matriz mal condicionada (mezclas poco diversas)")
    else:
        print("   (ok)")

    print("\nPredicho vs medido por ejecucion:")
    print(f"   {'name':10s} {'T[s]':>7s} {'E_med[J]':>10s} {'E_est[J]':>10s} {'err%':>7s}")
    for nm, Em, Ee, T in zip(names, b, pred, Ts):
        err = 100 * (Ee - Em) / Em if Em else float("nan")
        print(f"   {nm:10s} {T:7.2f} {Em:10.3f} {Ee:10.3f} {err:7.2f}")

    print("\nNota: los e_i absorben la estatica (supuesto del modelo). A 10 MHz")
    print("la estatica domina => predicen bien la energia total aunque la firma")
    print("dinamica por categoria quede enterrada. Mirar R^2 y condicion.")


if __name__ == "__main__":
    main()
