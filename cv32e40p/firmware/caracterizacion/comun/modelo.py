#!/usr/bin/env python3

import csv
import os

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


# temperatura del die (C) a la que se midio P_idle en el ultimo coeficientes.csv
# leido; None si el archivo no la trae. Registra la condicion termica de la base.
ultimo_T_idle = None


def cargar_coeficientes(path):
    """Lee un coeficientes.csv (formato comun) -> (P_idle, {cat: coef}).
    La temperatura de la linea base (fila 'T_idle', si existe) queda en el global
    modelo.ultimo_T_idle y NO se mete en coef."""
    global ultimo_T_idle
    ultimo_T_idle = None
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
            elif name == "T_idle":
                ultimo_T_idle = c
            else:
                coef[name] = c
    return P_idle, coef


def cargar_pendiente_termica(path):
    """Pendiente b [W/C] del ajuste P_idle(T) del barrido termico
    (pidle_fit.csv, fila 'b_W_per_C'). None si no hay barrido."""
    if not os.path.exists(path):
        return None
    with open(path) as f:
        for row in csv.reader(f):
            if row and row[0].strip() == "b_W_per_C":
                return float(row[1])
    return None


def correccion_termica(temp, T_idle, b):
    """Termino de fuga por temperatura de la linea base: b*(T - T_idle) [W].
    P_idle(T) = P_idle_ref + correccion_termica(T, T_ref, b). Devuelve 0 si
    falta algun dato (sin barrido o sin lectura de temperatura)."""
    if b is None or T_idle is None or temp is None:
        return 0.0
    return b * (temp - T_idle)


def potencia_dinamica(w, coef):
    """P DINAMICA [W] del run (w = 18 words de 'results'). Es el MODELO en si:
    energia de las instrucciones / T. SIN idle."""
    T_cyc = (w[17] - w[16]) & MASK32
    E = sum(coef.get(c, 0.0) * val(w, WLO[c]) for c in INSTR)   # por instruccion
    E += coef.get("div", 0.0) * val(w, WLO["divcyc"])           # div por ciclo
    E += coef.get("div_n", 0.0) * val(w, WLO["div_n"])          # div: costo base por instr (modelo diferencial)
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
