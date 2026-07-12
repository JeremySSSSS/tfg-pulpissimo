#!/usr/bin/env python3
"""Reproducibilidad de coeficientes entre CAMPANAS (experimento de dispersion).

Agrupa las corridas de datos.csv en campanas (por cercania temporal), re-ajusta
cada campana con su metodo, y reporta por categoria: coeficiente de cada
campana, media y CV%% (dispersion observada). Para M2 evalua ademas cada juego
sobre las MISMAS corridas de validacion (estabilidad de prediccion offline).

Uso:  python3 reproducibilidad.py
"""
import csv
import os
import sys
from datetime import datetime

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "comun"))
sys.path.insert(0, HERE)
import caracterizar as C   # noqa: E402

CATS = ["alu", "mul", "mulh", "div", "mem", "ctrl", "float"]
NCOL = {"alu": "n_alu", "mul": "n_mul", "mulh": "n_mulh", "div": "c_div",
        "mem": "n_mem", "ctrl": "n_ctrl", "float": "n_float"}
SOPORTE = {"alu": 15, "ctrl": 15, "mem": 11, "mul": 5, "div": 4,
           "mulh": 3, "float": 3}
# fecha desde la cual el binario de cada bucle M1 es el definitivo
M1_DESDE = {"alu": "2026-07-05", "div": "2026-07-05", "ctrl": "2026-07-06 18:15",
            "mul": "2026-07-11", "mulh": "2026-07-11", "mem": "2026-07-11",
            "float": "2026-07-11"}
GAP_MIN = 25   # minutos sin corridas => campana nueva


def campanas(path, filtro=None):
    """Agrupa filas por cercania temporal -> lista de campanas (listas de dict)."""
    if not os.path.exists(path):
        return []
    rows = [r for r in csv.DictReader(open(path)) if not filtro or filtro(r)]
    rows.sort(key=lambda r: r["fecha"])
    grupos, previo = [], None
    for r in rows:
        t = datetime.strptime(r["fecha"], "%Y-%m-%d %H:%M:%S")
        if previo is None or (t - previo).total_seconds() > GAP_MIN * 60:
            grupos.append([])
        grupos[-1].append(r)
        previo = t
    return grupos


def cv(vals):
    v = np.array(vals)
    return 100 * v.std(ddof=1) / v.mean() if len(v) > 1 else float("nan")


# ---------- M2 (efimon: campanas con variantes _d60) ----------
def m2():
    # cada campana de regresion EMPIEZA con una fila idle (protocolo de
    # caracterizar.py): particionar ahi es robusto ante reinicios (una campana
    # abortada no contamina a la siguiente, cosa que el gap temporal no ve).
    # Filas de pares (ctrl_/mulh_) se ignoran: no son de calibracion.
    path = os.path.join(HERE, "regresion", "datos.csv")
    if not os.path.exists(path):
        return []
    rows = [r for r in csv.DictReader(open(path))
            if not r["programa"].startswith(("ctrl_", "mulh_"))]
    rows.sort(key=lambda r: r["fecha"])
    grupos = []
    for r in rows:
        if r["programa"] == "idle" or not grupos:
            grupos.append([])
        grupos[-1].append(r)
    # solo campanas efimon COMPLETAS (15 programas x 3 intensidades + idle)
    grupos = [g for g in grupos if any(r["programa"].endswith("_d60") for r in g)]
    juegos = []
    for g in grupos:
        cal, idle = [], []
        for r in g:
            cont = {k: int(r[k]) for k in NCOL.values()}
            cont["n_div"] = int(r["n_div"])
            T = int(r["mcycle"]) / 1e7
            if r["programa"].endswith("_d60"):
                T /= 0.60
            elif r["programa"].endswith("_d30"):
                T /= 0.30
            fila = (r["programa"], float(r["P_med_W"]), T, cont, r.get("temp_C", ""))
            (idle if r["programa"] == "idle" else cal).append(fila)
        if len(cal) < 40 or not idle:
            continue
        coefs, info = C.ajustar_efimon(cal, idle)
        coefs["_c0"] = info["P_idle"]
        coefs["_fecha"] = g[0]["fecha"][:16]
        juegos.append(coefs)
    return juegos


# ---------- M1 (bucles: coeficiente por campana, binarios definitivos) ----------
def m1():
    grupos = campanas(os.path.join(HERE, "bucles", "datos.csv"))
    juegos = []
    for g in grupos:
        idle = [float(r["P_med_W"]) for r in g if r["categoria"] == "idle"]
        if not idle:
            continue
        Pi = np.mean(idle)
        coefs = {"_fecha": g[0]["fecha"][:16]}
        for c in CATS:
            rs = [r for r in g if r["categoria"] == c and r["fecha"] >= M1_DESDE[c]]
            if rs:
                vals = [(float(r["P_med_W"]) - Pi) * (int(r["mcycle"]) / 1e7)
                        / int(r[NCOL[c]]) for r in rs]
                coefs[c] = float(np.mean(vals))
        if len(coefs) > 1:
            juegos.append(coefs)
    return juegos


# ---------- estabilidad de prediccion (M2) sobre validacion fija ----------
def estabilidad(juegos):
    """Evalua cada juego de coeficientes sobre la ULTIMA sesion de validacion
    registrada en verificacion.csv (mismas corridas para todos los juegos)."""
    IDX = {"n_alu": 8, "n_mul": 9, "n_mulh": 10, "n_div": 11, "c_div": 12,
           "n_mem": 13, "n_ctrl": 14, "n_float": 15, "mcycle": 16}
    vcsv = os.path.join(HERE, "verificacion.csv")
    if not os.path.exists(vcsv):
        return None, []
    filas = [r for r in list(csv.reader(open(vcsv)))[1:]
             if len(r) >= 17 and r[1] == "regresion"]
    if not filas:
        return None, []
    # ultima sesion = bloque final de corridas separadas por < 20 min
    V, previo = [], None
    for r in reversed(filas):
        t = datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S")
        if previo is not None and (previo - t).total_seconds() > 20 * 60:
            break
        V.append(r)
        previo = t
    V.reverse()
    out = []
    for j in juegos:
        es = []
        for r in V:
            T = int(r[IDX["mcycle"]]) / 1e7
            pd = sum(j[c] * int(r[IDX[NCOL[c]]]) / T for c in CATS)
            es.append(100 * ((j["_c0"] + pd) - float(r[4])) / float(r[4]))
        e = np.array(es)
        out.append((j["_fecha"], abs(e).mean(), e.mean()))
    return f"{V[0][0][:16]} ({len(V)} corridas)", out


def tabla(nombre, juegos):
    print(f"\n=== {nombre}: {len(juegos)} campanas ===")
    if not juegos:
        print("  (ninguna campana valida en datos.csv)")
        return
    # coeficientes en nJ, campana por columna; media y CV% (dispersion) al final
    print(f"{'categoria':10s} " + " ".join(f"{j['_fecha'][5:]:>12s}" for j in juegos)
          + f" | {'media':>8s} {'CV%':>6s}  soporte")
    for c in CATS:
        vals = [j[c] * 1e9 for j in juegos if c in j]
        if not vals:
            continue
        fila = " ".join(f"{j[c]*1e9:12.3f}" if c in j else f"{'--':>12s}" for j in juegos)
        cvtxt = f"{cv(vals):6.1f}" if len(vals) > 1 else f"{'--':>6s}"
        print(f"{c:10s} {fila} | {np.mean(vals):8.3f} {cvtxt}  {SOPORTE[c]:2d} prog")
    print("(CV% = desviacion estandar / media entre campanas; -- = 1 sola campana)")


if __name__ == "__main__":
    j2 = m2()
    tabla("M2 efimon (re-ajuste por campana de regresion/datos.csv)", j2)
    if len(j2) > 1:
        sesion, res = estabilidad(j2)
        if sesion is None:
            print("\n(sin corridas de validacion M2 en verificacion.csv todavia: "
                  "corre 'verificar' y repite este analisis)")
        else:
            print(f"\nestabilidad de PREDICCION: cada juego de coeficientes evaluado"
                  f"\nsobre la misma sesion de validacion [{sesion}]:")
            for f, m, s in res:
                print(f"  coefs de {f}:  |error| medio = {m:.3f}%   sesgo = {s:+.3f}%")
            print("(si los CV altos de arriba NO se reflejan aqui, la inestabilidad vive"
                  "\n en direcciones que los programas reales no exploran)")
    tabla("M1 bucles (binarios definitivos, bucles/datos.csv)", m1())
