#!/usr/bin/env python3
"""Recupera y consolida en CSVs (trazables) todos los datos importantes del
metodo chopper, leyendo cada uno de su FUENTE (nada hardcodeado):

  1. cpi_categorias.csv  <- ../../metodo1/runs_m1.csv  (CPI = T_ciclos / n_i de
     los bucles dominados puros). Necesario para pasar delta[W] -> energia/instr.
  2. sim_potencia.csv     <- ../../../example_tb/core/power_sim/power_<cat>.rpt
     (potencia dinamica del core aislado a 10 MHz, para la validacion cruzada).
  3. chopper_historico.csv + chopper_results.csv  <- el chopper_results.csv
     existente: separa el historico (NOP + wfi, justifica el cambio de
     referencia) y deja un chopper_results.csv LIMPIO solo con las filas wfi,
     con el nombre de categoria normalizado (alu_wfi -> alu). Esa es la
     caracterizacion vigente; la re-caracterizacion agrega filas aca.
"""
import csv
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
MASK32 = 0xFFFFFFFF
CATS = ["alu", "mul", "mulh", "div", "mem", "ctrl", "float"]
WLO = {"alu": 0, "mul": 2, "mulh": 4, "div_n": 6, "mem": 8, "ctrl": 10, "float": 12}


def to_int(s):
    s = s.strip()
    return int(s, 16) if s.lower().startswith("0x") else int(s)


# ---------- 1. CPI de los bucles dominados ----------
def recuperar_cpi():
    src = os.path.join(HERE, "..", "..", "metodo1", "runs_m1.csv")
    out = os.path.join(HERE, "cpi_categorias.csv")
    rows = []
    with open(src) as f:
        for r in csv.reader(f):
            if not r or r[0].strip() in ("category", "") or r[0].startswith("#"):
                continue
            cat = r[0].strip()
            if cat not in ("alu", "mul", "mulh", "mem", "ctrl", "float"):
                continue                       # div va por ciclos (DIVCYC), sin CPI
            w = [to_int(x) for x in r[7:25]]
            T_cyc = (w[17] - w[16]) & MASK32
            n_i = w[WLO[cat]] + (w[WLO[cat] + 1] << 32)
            rows.append((cat, T_cyc, n_i, T_cyc / n_i))
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["# CPI por categoria = T_ciclos / n_instr de los bucles dominados puros (../../metodo1/runs_m1.csv)"])
        w.writerow(["categoria", "T_ciclos", "n_instr", "CPI"])
        for cat, T, n, cpi in rows:
            w.writerow([cat, T, n, f"{cpi:.4f}"])
    print(f"  cpi_categorias.csv  ({len(rows)} categorias)")


# ---------- 2. potencia de la simulacion ----------
def recuperar_sim():
    pdir = os.path.join(HERE, "..", "..", "..", "example_tb", "core", "power_sim")
    out = os.path.join(HERE, "sim_potencia.csv")
    rows = []
    for cat in CATS:
        rpt = os.path.join(pdir, f"power_{cat}.rpt")
        if not os.path.exists(rpt):
            continue
        with open(rpt) as f:
            txt = f.read()
        m = re.search(r"\|\s*Dynamic \(W\)\s*\|\s*([0-9.]+)", txt)
        if m:
            rows.append((cat, float(m.group(1))))
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["# Potencia dinamica del core CV32E40P aislado, OOC synth + SAIF + report_power @10 MHz"])
        w.writerow(["categoria", "P_din_sim_W", "P_din_sim_mW"])
        for cat, p in rows:
            w.writerow([cat, f"{p:.4f}", f"{p*1e3:.1f}"])
    print(f"  sim_potencia.csv    ({len(rows)} categorias)")


# ---------- 3. separar historico / limpio del chopper ----------
def recuperar_chopper():
    src = os.path.join(HERE, "chopper_results.csv")
    if not os.path.exists(src):
        print("  (no hay chopper_results.csv que separar)")
        return
    with open(src) as f:
        rows = list(csv.reader(f))
    header = rows[0]
    body = [r for r in rows[1:] if r]
    # historico = todo (NOP + wfi) -> justifica el cambio de referencia
    with open(os.path.join(HERE, "chopper_historico.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(body)
    # limpio = solo wfi, categoria normalizada (alu_wfi -> alu)
    limpio = []
    for r in body:
        if r[0].endswith("_wfi"):
            r = list(r); r[0] = r[0][:-4]
            limpio.append(r)
    with open(src, "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(limpio)
    print(f"  chopper_historico.csv ({len(body)} filas)  +  chopper_results.csv LIMPIO ({len(limpio)} filas wfi)")


if __name__ == "__main__":
    print("Recuperando datos a CSV:")
    recuperar_cpi()
    recuperar_sim()
    recuperar_chopper()
    print("Listo.")
