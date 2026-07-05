#!/usr/bin/env python3
"""Modelo de potencia del chopper, TODO data-driven (lee CSVs, nada hardcodeado).
Lo comparten run_chopper.py (lo genera al caracterizar) y validar_chopper.py
(lo usa para predecir).

  chopper_results.csv -> delta_i [W] por categoria (promedio) y P_idle [W]
  cpi_categorias.csv  -> CPI_i

  e_dyn_i = delta_i * CPI_i / f      [J/instr]   (alu,mul,mulh,mem,ctrl,float)
  p_div   = delta_div / f            [J/ciclo-div]  (div: hibrido, usa DIVCYC)
  P_pred  = P_idle + ( sum_i e_dyn_i*n_i + p_div*c_div ) / T
"""
import csv
import datetime
import os
import statistics


def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_fecha(path):
    """Migra un CSV viejo agregando la columna 'fecha' al inicio (backfill: hoy)."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        rows = list(csv.reader(f))
    if rows and rows[0] and rows[0][0] != "fecha" and not rows[0][0].startswith("#"):
        today = datetime.date.today().isoformat()
        with open(path, "w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["fecha"] + rows[0])
            for r in rows[1:]:
                if r:
                    wr.writerow([today] + r)

F_CLK = 10e6
MASK32 = 0xFFFFFFFF
HERE = os.path.dirname(os.path.abspath(__file__))
CATS = ["alu", "mul", "mulh", "div", "mem", "ctrl", "float"]
# word LO de cada contador en 'results' (igual que el dump del harness)
WLO = {"alu": 0, "mul": 2, "mulh": 4, "div_n": 6, "mem": 8, "ctrl": 10,
       "float": 12, "divcyc": 14}
CHOPPER_CSV = os.path.join(HERE, "chopper_results.csv")
CPI_CSV = os.path.join(HERE, "cpi_categorias.csv")
COEF_CSV = os.path.join(HERE, "coeficientes.csv")


def to_int(s):
    s = s.strip()
    return int(s, 16) if s.lower().startswith("0x") else int(s)


def val(w, lo):
    return w[lo] + (w[lo + 1] << 32)


def load_chopper():
    """delta_i [W] (promedio de repeticiones) y P_idle [W] de chopper_results.csv."""
    deltas = {c: [] for c in CATS}
    pidle = []
    with open(CHOPPER_CSV) as f:
        for r in csv.DictReader(f):
            cat = r["categoria"].strip()
            if cat in deltas:
                deltas[cat].append(float(r["delta_W"]))
            pidle.append(float(r["P_idle_W"]))
    DELTA = {c: statistics.mean(v) for c, v in deltas.items() if v}
    return DELTA, statistics.mean(pidle), {c: len(v) for c, v in deltas.items()}


def load_cpi():
    cpi = {}
    with open(CPI_CSV) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or row[0] == "categoria":
                continue
            cpi[row[0]] = float(row[3])
    return cpi


def build_model():
    """Devuelve DELTA, P_IDLE, CPI, e_dyn (J/instr), p_div (J/ciclo), nrep."""
    DELTA, P_IDLE, nrep = load_chopper()
    CPI = load_cpi()
    e_dyn = {c: DELTA[c] * CPI[c] / F_CLK for c in CPI if c in DELTA}
    p_div = DELTA["div"] / F_CLK
    return DELTA, P_IDLE, CPI, e_dyn, p_div, nrep


def predict(w, P_IDLE, e_dyn, p_div):
    """P_pred [W] del modelo E=P_idle*T + sum e_dyn_i*n_i + p_div*c_div."""
    T_cyc = (w[17] - w[16]) & MASK32
    E_dyn = sum(e_dyn[c] * val(w, WLO[c]) for c in e_dyn)
    E_dyn += p_div * val(w, WLO["divcyc"])
    return P_IDLE + E_dyn / (T_cyc / F_CLK)


def format_coeffs(DELTA, P_IDLE, CPI, e_dyn, p_div, nrep):
    """Texto de la tabla de coeficientes (para imprimir)."""
    out = ["=== Coeficientes del modelo (de chopper_results.csv + cpi_categorias.csv) ===",
           f"  P_idle = {P_IDLE:.4f} W",
           f"  {'cat':6s} {'delta[mW]':>9s} {'CPI':>6s} {'coef':>14s}  reps"]
    for c in CATS:
        if c == "div":
            out.append(f"  {'div':6s} {DELTA['div']*1e3:9.3f} {'--':>6s} {p_div*1e12:9.1f} pJ/cic  {nrep['div']}")
        elif c in e_dyn:
            out.append(f"  {c:6s} {DELTA[c]*1e3:9.3f} {CPI[c]:6.2f} {e_dyn[c]*1e12:9.1f} pJ/ins  {nrep[c]}")
    return "\n".join(out)


def load_coeffs():
    """Lee coeficientes.csv y devuelve la MISMA tupla que build_model(), pero
    desde el archivo (permite crear/editar coeficientes a mano para pruebas)."""
    DELTA, CPI, e_dyn, nrep = {}, {}, {}, {}
    P_IDLE, p_div = None, None
    with open(COEF_CSV) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or row[0] == "parametro":
                continue
            name = row[0]
            if name == "P_idle":
                P_IDLE = float(row[3]); continue
            coef = float(row[3])
            if name == "div":
                p_div = coef
            else:
                e_dyn[name] = coef
            if row[1]:
                DELTA[name] = float(row[1])
            if row[2]:
                CPI[name] = float(row[2])
            if row[5]:
                nrep[name] = int(row[5])
    return DELTA, P_IDLE, CPI, e_dyn, p_div, nrep


def write_coeffs(DELTA, P_IDLE, CPI, e_dyn, p_div, nrep):
    """Guarda coeficientes.csv (trazable: delta, CPI y el coeficiente final)."""
    with open(COEF_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([f"# Coeficientes del modelo de potencia (generado {now_str()})."
                    " coef = e_dyn [J/instr] salvo div (p_div [J/ciclo])."
                    " Derivados de chopper_results.csv + cpi_categorias.csv"])
        w.writerow(["parametro", "delta_W", "CPI", "coef", "unidad", "reps"])
        w.writerow(["P_idle", "", "", f"{P_IDLE:.6f}", "W", ""])
        for c in CATS:
            if c == "div":
                w.writerow(["div", f"{DELTA['div']:.6f}", "", f"{p_div:.6e}", "J/ciclo", nrep["div"]])
            elif c in e_dyn:
                w.writerow([c, f"{DELTA[c]:.6f}", f"{CPI[c]:.4f}", f"{e_dyn[c]:.6e}", "J/instr", nrep[c]])
    return COEF_CSV
