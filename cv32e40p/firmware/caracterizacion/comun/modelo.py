#!/usr/bin/env python3
"""Modelo COMUN de prediccion de potencia. Lo usa verificar.py con los
coeficientes de CUALQUIER metodo (bucles / chopper / regresion), porque los 3
guardan su coeficientes.csv en el MISMO formato:

    parametro, coef, unidad
    P_idle,    5.0549,   W           # NO es coef del modelo: es el piso estatico
    alu,       2.009e-9, J/instr
    ...
    div,       3.40e-10, J/ciclo      # hibrido: por ciclo de DIVCYC

El MODELO es de potencia DINAMICA: sus coeficientes (J/instr, J/ciclo) son la
energia que cada instruccion gasta POR ENCIMA del reposo, y ya vienen limpios de
idle (los 3 metodos los derivan de un delta con el idle restado):

    P_dinamica = ( sum_i coef_i*n_i + coef_div*c_div ) / T

La potencia ESTATICA (P_idle) es un termino APARTE. La potencia TOTAL aproximada
suma el idle SOLO al final:

    P_total = P_idle + P_dinamica

P_idle se guarda en coeficientes.csv solo como referencia del piso estatico
(distinguido por unidad: W vs J/instr|J/ciclo), no como coeficiente del modelo.
n_i de los contadores del clasificador; c_div = DIVCYC; T = mcycle/f.
"""
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
            if not row or row[0].startswith("#") or row[0] == "parametro":
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
