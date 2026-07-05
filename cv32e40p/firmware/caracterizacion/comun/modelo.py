#!/usr/bin/env python3

import csv

F_CLK = 10e6
MASK32 = 0xFFFFFFFF
# word LO de cada contador en 'results' (dump del harness: 16 CSR + mcycle ini/fin)
WLO = {"alu": 0, "mul": 2, "mulh": 4, "div_n": 6, "mem": 8, "ctrl": 10,
       "float": 12, "divcyc": 14}
INSTR = ["alu", "mul", "mulh", "mem", "ctrl", "float"]   # coef por instruccion
# 'div' va por CICLO (DIVCYC), no por instruccion (modelo hibrido)


def to_int(s):
    s = s.strip()
    return int(s, 16) if s.lower().startswith("0x") else int(s)


def val(w, lo):
    return w[lo] + (w[lo + 1] << 32)


def cargar_coeficientes(path):
    """Lee un coeficientes.csv (formato comun) -> (P_idle, {cat: coef})."""
    P_idle = None
    coef = {}
    with open(path) as f:
        for row in csv.reader(f):
            # salta comentarios, encabezado y filas vacias/mutiladas (p.ej. la
            # linea '#...' que LibreOffice re-guarda como ',,')
            if not row or not row[0].strip() or row[0].startswith("#") or row[0] == "parametro":
                continue
            name = row[0].strip()
            c = float(row[1])
            if name == "P_idle":
                P_idle = c
            else:
                coef[name] = c
    return P_idle, coef


def potencia_dinamica(w, coef):
    """P DINAMICA [W] del run (w = 18 words de 'results'). Es el MODELO en si:
    energia de las instrucciones / T. SIN idle."""
    T_cyc = (w[17] - w[16]) & MASK32
    E = sum(coef.get(c, 0.0) * val(w, WLO[c]) for c in INSTR)   # por instruccion
    E += coef.get("div", 0.0) * val(w, WLO["divcyc"])           # div por ciclo
    return E / (T_cyc / F_CLK)


def predecir(w, P_idle, coef):
    """P TOTAL aprox [W] = P_idle (estatica) + P dinamica. El idle se suma SOLO
    aqui, al final del calculo; el modelo en si (potencia_dinamica) es dinamico."""
    return P_idle + potencia_dinamica(w, coef)


def contadores(w):
    """Decodifica TODOS los contadores del clasificador de los 18 words, para
    guardarlos junto a cada corrida (todo lo posible)."""
    return {
        "n_alu":   val(w, WLO["alu"]),
        "n_mul":   val(w, WLO["mul"]),
        "n_mulh":  val(w, WLO["mulh"]),
        "n_div":   val(w, WLO["div_n"]),
        "c_div":   val(w, WLO["divcyc"]),
        "n_mem":   val(w, WLO["mem"]),
        "n_ctrl":  val(w, WLO["ctrl"]),
        "n_float": val(w, WLO["float"]),
        "mcycle":  (w[17] - w[16]) & MASK32,
    }


# orden de columnas de contadores (para CSV/Sheet)
COLS_CONTADORES = ["n_alu", "n_mul", "n_mulh", "n_div", "c_div",
                   "n_mem", "n_ctrl", "n_float", "mcycle"]
