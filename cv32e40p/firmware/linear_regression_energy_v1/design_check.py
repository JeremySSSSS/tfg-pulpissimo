#!/usr/bin/env python3
"""Chequeo de condicionamiento del diseno de mezclas, SIN hardware.

Los conteos n_i por perfil son deterministas: dependen solo de los
"blocks" de cada categoria en energy_mix.S y de LOOP_COUNT. T se estima
con un modelo simple de ciclos por instruccion (c_i) por categoria.
Esto permite evaluar el numero de condicion del modelo
    P = P0 + sum(e_i * n_i/T)
ANTES de gastar tiempo en mediciones reales, y localizar la combinacion
casi colineal.

Categorias en orden: alu, mul, mulh, div(DIVCYC), mem, ctrl, float
"""
import numpy as np

LOOP_COUNT = 300000

# blocks por perfil: (overhead, alu, mul, mulh, div, mem, ctrl, float)
PROFILES_CURRENT = {
    "m00": (2, 10, 8, 1, 1, 1, 1, 1),
    "m01": (2, 1, 10, 8, 1, 1, 1, 1),
    "m02": (2, 1, 1, 10, 8, 1, 1, 1),
    "m03": (2, 1, 1, 1, 10, 8, 1, 1),
    "m04": (2, 1, 1, 1, 1, 10, 8, 1),
    "m05": (2, 1, 1, 1, 1, 1, 10, 8),
    "m06": (2, 8, 1, 1, 1, 1, 1, 10),
    "m07": (2, 4, 4, 4, 4, 4, 4, 4),
    "m08": (2, 7, 2, 7, 2, 7, 2, 7),
    "m09": (2, 2, 7, 2, 7, 2, 7, 2),
    "m10": (2, 5, 1, 9, 5, 1, 9, 1),
    "m11": (2, 1, 5, 1, 9, 5, 1, 9),
}

# instrucciones emitidas por "block" en cada categoria
MULT = dict(alu=4, mul=4, mulh=4, div=4, mem=8, ctrl=4, float=4)
# ciclos por instruccion/cuenta (aproximado; div ya en DIVCYC -> 1:1)
CYC = dict(alu=1.0, mul=2.0, mulh=2.0, div=1.0, mem=1.0, ctrl=2.0, float=1.3)
C_OVERHEAD = 1.0  # csrr zero, mcycle


def build(profiles):
    names, rows, Ts = [], [], []
    for name, (oh, alu, mul, mulh, div, mem, ctrl, flt) in profiles.items():
        blocks = dict(alu=alu, mul=mul, mulh=mulh, div=div, mem=mem, ctrl=ctrl, float=flt)
        n = {}
        for cat, b in blocks.items():
            n[cat] = b * MULT[cat] * LOOP_COUNT
        # div column = DIVCYC = n_div_instr * k_div (k_div ~ 21 cyc/op medido)
        k_div = 21.0
        divcyc = n["div"] * k_div
        T = oh * 4 * C_OVERHEAD * LOOP_COUNT
        for cat in ("alu", "mul", "mulh", "mem", "ctrl", "float"):
            T += n[cat] * CYC[cat]
        T += divcyc * CYC["div"]  # CYC[div]=1 -> divcyc ya en ciclos

        row = [n["alu"], n["mul"], n["mulh"], divcyc, n["mem"], n["ctrl"], n["float"]]
        names.append(name)
        rows.append(row)
        Ts.append(T)
    return names, np.array(rows, dtype=float), np.array(Ts, dtype=float)


def report(label, profiles):
    names, A, Ts = build(profiles)
    R = A / Ts[:, None]  # rates r_i = n_i / T
    X = np.column_stack([np.ones(len(names)), R])

    print(f"\n=== {label} ===")
    print(f"{'perfil':6s} " + " ".join(f"{c:>9s}" for c in
          ["alu", "mul", "mulh", "div(cyc)", "mem", "ctrl", "float", "T[cyc]"]))
    for nm, r, t in zip(names, R, Ts):
        print(f"{nm:6s} " + " ".join(f"{v:9.4f}" for v in r) + f" {t:12.0f}")

    # Suma ponderada de tasas (debe variar entre perfiles; si es ~constante
    # esta casi colineal con la columna de unos -> P0).
    weights = np.array([CYC["alu"], CYC["mul"], CYC["mulh"], CYC["div"],
                         CYC["mem"], CYC["ctrl"], CYC["float"]])
    s = R @ weights
    print(f"\nsum(c_i * r_i) por perfil (debe variar, NO ser ~constante):")
    print("  " + ", ".join(f"{nm}={v:.4f}" for nm, v in zip(names, s)))
    print(f"  rango = {s.max()-s.min():.4f}  (relativo: {(s.max()-s.min())/s.mean():.2%})")

    # condicion estandarizada (igual criterio que v3/regression.py)
    feat = X[:, 1:]
    z = (feat - feat.mean(axis=0)) / feat.std(axis=0)
    Xz = np.column_stack([np.ones(len(names)), z])
    cond = np.linalg.cond(Xz)
    print(f"\nnumero de condicion estandarizado = {cond:.3e}")
    return cond


if __name__ == "__main__":
    report("Diseno actual (m00-m11, overhead=2 fijo)", PROFILES_CURRENT)
