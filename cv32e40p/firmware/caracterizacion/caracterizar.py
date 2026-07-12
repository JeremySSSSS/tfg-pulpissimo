#!/usr/bin/env python3
"""Caracterizacion de coeficientes energeticos — script UNICO para los 2 metodos:

  bucles    (M1): un bucle dominado por categoria, aislada contra idle.
                  coef_i = (P_cat - P_idle) * T / n_i   (div usa DIVCYC)
  regresion (M2): programas mixtos reales; regresion SIN intercepto con P_idle
                  FIJO:  P_med - P_idle = sum e_i * (n_i / T)

Cada metodo guarda datos.csv y coeficientes.csv en su directorio (bucles/ o
regresion/) y sube a su pestaña del Sheet. verificar.py consume esos
coeficientes.csv con el mismo formato comun.

Uso:
    python3 caracterizar.py bucles --repeats 2
    python3 caracterizar.py bucles alu mul div
    python3 caracterizar.py regresion
    python3 caracterizar.py regresion --refit
    python3 caracterizar.py regresion --pidle bucles
"""
import argparse
import csv
import os
import statistics
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "comun"))
import jtag      # noqa: E402
import modelo    # noqa: E402
import sheet     # noqa: E402

F_CLK = modelo.F_CLK
DIR_BUCLES = os.path.join(HERE, "bucles")
DIR_REGR = os.path.join(HERE, "regresion")

# --- comun a ambos metodos -------------------------------------------------

def run_make(met_dir):
    subprocess.run(["make", "-B", "all"], cwd=os.path.join(met_dir, "fuentes"), check=True)


def find_elf(prog, met_dir):
    # idle.elf vive en bucles/ (es el run de referencia del piso para ambos)
    for cand in (os.path.join(met_dir, "elf", f"{prog}.elf"),
                 os.path.join(DIR_BUCLES, "elf", f"{prog}.elf"),
                 os.path.join(HERE, "pares", "elf", f"{prog}.elf"), prog):
        if os.path.exists(cand):
            return cand
    raise FileNotFoundError(f"{prog}.elf no existe (corre 'make' en {met_dir}/fuentes)")


def medir_uno(prog, elf, inbox):
    """Corre un elf por JTAG y devuelve (P_med, T, contadores, temp_str)."""
    if prog == "idle":
        # idle (wfi) es robusto a la inflacion del JTAG (una ventana de idle
        # inflada sigue midiendo idle) y tiene IPC~0 por diseno -> 1 corrida.
        # Si la fila del ESP32 no llega (subida perdida), se reintenta la
        # MEDIDA completa hasta 3 veces en vez de abortar la campana.
        for intento in range(1, 4):
            words = jtag.run_one(elf)
            try:
                P_med = inbox.get_pavg()
                break
            except TimeoutError:
                if intento == 3:
                    raise
                print(f"    idle: ventana sin P_avg del ESP32; REINTENTO "
                      f"({intento}/3)")
    else:
        words, P_med = jtag.run_medido(elf, inbox.get_pavg)
    w = [modelo.to_int(x) for x in words]
    cont = modelo.contadores(w)
    T = cont["mcycle"] / F_CLK
    # Variantes de ciclo de trabajo: mcycle se CONGELA durante el wfi, asi que
    # mcycle/F_CLK es solo el tiempo ACTIVO. La ventana real (la que promedia el
    # ESP32) es activo/duty, exacto por construccion (suenos proporcionales).
    if prog.endswith("_d60"):
        T /= 0.60
    elif prog.endswith("_d30"):
        T /= 0.30
    tC = jtag.ultima_temp_cC                 # temperatura del die (XADC), centi-C
    tstr = f"{tC/100:.2f}" if tC is not None else ""
    return P_med, T, cont, tstr


def subir_sheet(hoja, **campos):
    try:    # la pestaña del Sheet es secundaria: datos.csv ya tiene la fila
        sheet.subir(hoja, **campos)
    except Exception as e:
        print(f"    [aviso] no se pudo subir a '{hoja}' ({e}); sigo (esta en datos.csv)")


def rotar_si_header_distinto(path, header):
    """Si datos.csv existe con OTRO encabezado (esquema viejo), lo aparta a
    datos_legacy_*.csv en vez de apendear filas desalineadas."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        actual = next(csv.reader(f), None)
    if actual != header:
        legado = path.replace(".csv", time.strftime("_legacy_%Y%m%d_%H%M.csv"))
        os.rename(path, legado)
        print(f"[aviso] {os.path.basename(path)} tenia esquema viejo -> movido a {os.path.basename(legado)}")


# --- metodo 1: bucles dominados ---------------------------------------------

CATS = ["idle", "alu", "mul", "mulh", "div", "mem", "ctrl", "float"]
COEF_CATS = ["alu", "mul", "mulh", "div", "mem", "ctrl", "float"]
DENOM = {"alu": "n_alu", "mul": "n_mul", "mulh": "n_mulh", "div": "c_div",
         "mem": "n_mem", "ctrl": "n_ctrl", "float": "n_float"}


def cmd_bucles(args):
    datos_csv = os.path.join(DIR_BUCLES, "datos.csv")
    coef_csv = os.path.join(DIR_BUCLES, "coeficientes.csv")

    cats = args.categorias or CATS
    invalid = [c for c in cats if c not in CATS]
    if invalid:
        sys.exit(f"categorias invalidas: {', '.join(invalid)}")
    if "idle" not in cats:
        cats = ["idle"] + cats

    if not args.no_build:
        run_make(DIR_BUCLES)
    for cat in cats:
        find_elf(cat, DIR_BUCLES)

    header = ["fecha", "categoria", "rep", "P_med_W", "T_s", "temp_C"] + modelo.COLS_CONTADORES
    rotar_si_header_distinto(datos_csv, header)
    inbox = sheet.Inbox()
    runs = {c: [] for c in cats}
    new = not os.path.exists(datos_csv)
    with open(datos_csv, "a", newline="") as fd:
        wr = csv.writer(fd)
        if new:
            wr.writerow(header)
        for cat in cats:
            elf = find_elf(cat, DIR_BUCLES)
            for rep in range(1, args.repeats + 1):
                extra = "(idle wfi)" if cat == "idle" else "(bucle dominado)"
                print(f"==> {cat} rep {rep}/{args.repeats}  {extra}")
                P_med, T, cont, tstr = medir_uno(cat, elf, inbox)
                runs[cat].append({"P_med": P_med, "T": T, "cont": cont, "temp": tstr})
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                wr.writerow([ts, cat, rep, f"{P_med:.6f}", f"{T:.6f}", tstr]
                            + [cont[k] for k in modelo.COLS_CONTADORES])
                fd.flush()
                subir_sheet("bucles", categoria=cat, rep=rep, P_med_W=f"{P_med:.6f}",
                            T_s=f"{T:.6f}", temp_C=tstr,
                            **{k: cont[k] for k in modelo.COLS_CONTADORES})
                print(f"    P_med = {P_med:.4f} W   T = {T:.1f} s")
                time.sleep(3)

    P_idle = statistics.mean(r["P_med"] for r in runs["idle"])
    # temperatura del die a la que se midio la linea base: la P_idle vale para esa
    # condicion termica; se guarda para poder corregir la deriva por temperatura.
    temps_idle = [float(r["temp"]) for r in runs["idle"] if r.get("temp")]
    T_idle = statistics.mean(temps_idle) if temps_idle else None
    coefs = {}
    resumen = []
    for cat in COEF_CATS:
        if not runs.get(cat):
            continue
        cat_coefs, deltas, denoms = [], [], []
        for r in runs[cat]:
            delta = r["P_med"] - P_idle
            denom = r["cont"][DENOM[cat]]
            if denom <= 0:
                raise RuntimeError(f"{cat}: denominador {DENOM[cat]} es 0")
            cat_coefs.append(delta * r["T"] / denom)
            deltas.append(delta)
            denoms.append(denom)
        coefs[cat] = statistics.mean(cat_coefs)
        resumen.append((cat, statistics.mean(deltas), statistics.mean(denoms),
                        coefs[cat], len(cat_coefs)))

    # Fusion con el archivo previo: una corrida parcial (p.ej. solo ctrl) NO
    # borra los coeficientes de las otras categorias. Es valido mezclar: cada
    # coef es un delta interno a SU sesion (P_cat y P_idle de la misma sesion);
    # P_idle/T_idle del archivo quedan los de HOY, que son los que la
    # verificacion de hoy necesita como linea base.
    if os.path.exists(coef_csv):
        try:
            _, prev = modelo.cargar_coeficientes(coef_csv)
            faltan = {c: v for c, v in prev.items()
                      if c in COEF_CATS and c not in coefs}
            if faltan:
                print(f"  (conservo del archivo previo: {', '.join(sorted(faltan))})")
                coefs.update(faltan)
        except Exception as e:
            print(f"  [aviso] no pude leer coeficientes previos ({e}); "
                  f"escribo solo lo medido")

    with open(coef_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([f"# Bucles dominados (M1). Generado {time.strftime('%Y-%m-%d %H:%M:%S')}.",
                    "coef=(P_cat-P_idle)*T/n; div usa DIVCYC."])
        w.writerow(["parametro", "coef", "unidad"])
        w.writerow(["P_idle", f"{P_idle:.6f}", "W"])
        if T_idle is not None:
            w.writerow(["T_idle", f"{T_idle:.2f}", "C"])
        for cat in COEF_CATS:
            if cat in coefs:
                unidad = "J/ciclo" if cat == "div" else "J/instr"
                w.writerow([cat, f"{coefs[cat]:.6e}", unidad])

    print(f"\nP_idle = {P_idle:.4f} W")
    for cat, delta, denom, coef, n in resumen:
        unidad = "J/ciclo" if cat == "div" else "J/instr"
        print(f"  {cat:6s} delta={delta*1e3:7.3f} mW  denom={denom:.0f}  coef={coef:.6e} {unidad}  (n={n})")
    print(f"\nGuardado: {datos_csv}, {coef_csv} + pestaña 'bucles' del Sheet.")


# --- metodo 2: regresion con linea base fija ---------------------------------

# categorias del modelo y el contador que regresiona cada una (div va por ciclo)
DYN = ["alu", "mul", "mulh", "div", "mem", "ctrl", "float"]
REGR = {"alu": "n_alu", "mul": "n_mul", "mulh": "n_mulh", "div": "c_div",
        "mem": "n_mem", "ctrl": "n_ctrl", "float": "n_float"}
DEFAULT_PROGS = ["memcpy", "fsm", "crc", "matmul", "mulhash64", "mulhscale",
                 "dotprod", "gcd", "modpow", "trialdiv", "radix", "fpoly",
                 "vecscale", "histogram", "sort"]


def cargar_pidle(fuente):
    """fuente = 'bucles' (lee P_idle de bucles/coeficientes.csv) o un numero en W."""
    try:
        return float(fuente)
    except ValueError:
        pass
    if fuente != "bucles":
        sys.exit(f"--pidle invalido: {fuente} (usa medir|bucles o un numero en W)")
    path = os.path.join(DIR_BUCLES, "coeficientes.csv")
    P_idle, _ = modelo.cargar_coeficientes(path)
    if P_idle is None:
        sys.exit(f"no encontre P_idle en {path}; caracteriza primero con 'bucles'")
    return P_idle


def _temp_f(s):
    """Temperatura del CSV/Sheet a float; tolera coma decimal (locale es-ES) y
    vacio. None si no se puede parsear -> sin correccion para esa corrida."""
    try:
        return float(str(s).replace(",", ".")) if s not in (None, "") else None
    except ValueError:
        return None


def leer_datos(datos_csv):
    """Lee las corridas de datos.csv -> [(prog, P_med, T, cont, temp)] (--refit)."""
    rows = []
    with open(datos_csv) as f:
        for r in csv.DictReader(f):
            cont = {k: int(r[k]) for k in modelo.COLS_CONTADORES}
            rows.append((r["programa"], float(r["P_med_W"]), cont["mcycle"] / F_CLK,
                         cont, r.get("temp_C", "")))
    return rows


def ajustar_efimon(cal_rows, idle_rows):
    """Ajuste al estilo EfiMon: NNLS CON INTERCEPTO sobre la potencia TOTAL.
    Requiere el barrido de intensidad (variantes _d60/_d30: misma composicion,
    distinta utilizacion), que decorrelaciona el modo comun de las categorias
    por diseno experimental. Las filas de idle (tasas 0) anclan el intercepto,
    que hace el papel de P_static (ec. 5 de EfiMon)."""
    from scipy.optimize import nnls
    rows = cal_rows + idle_rows
    R = np.array([[r[3][REGR[c]] / r[2] if r[2] > 0 else 0.0 for c in DYN]
                  for r in rows])
    y = np.array([r[1] for r in rows])
    X = np.hstack([np.ones((len(y), 1)), R])
    sd = X.std(0); sd[0] = 1.0; sd[sd == 0] = 1.0
    e, _ = nnls(X / sd, y)
    e = e / sd
    P_static = e[0]
    coefs = dict(zip(DYN, e[1:]))
    pred = X @ e
    resid = y - pred
    ss_res = float(resid @ resid)
    delta = y - P_static
    ss_tot = float(delta @ delta)
    info = {"P_idle": P_static,
            "r2": 1 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
            "rmse": (ss_res / len(y)) ** 0.5,
            "cond": float(np.linalg.cond(X / sd)),
            "pred_abs": pred[:len(cal_rows)]}
    return coefs, info


def ajustar_diferencial(rows, P_idle):
    """Regresion DIFERENCIAL no negativa (inspirada en EfiMon): separa la
    intensidad de la composicion. delta = alfa*r_total + sum extra_k * r_k,
    con NNLS (coeficientes >= 0). alfa = costo base por instruccion retirada
    (modo comun: fetch/pipeline); extra_k = sobrecosto de la categoria sobre
    ese base. Evita que el modo comun se vuelque en la columna de alu (la mas
    correlacionada con la tasa total). Coeficientes absolutos guardados:
    cat = alfa + extra; div por ciclo = extra_div; div_n = alfa (por instr)."""
    from scipy.optimize import nnls
    INSTR_CATS = ["alu", "mul", "mulh", "mem", "ctrl", "float"]
    rtot = np.array([sum(r[3][REGR[c]] for c in INSTR_CATS) + r[3]["n_div"]
                     for r in rows]) / np.array([r[2] for r in rows])
    Rx = np.array([[r[3][REGR[c]] / r[2] for c in DYN if c != "alu"] for r in rows])
    X = np.hstack([rtot[:, None], Rx])
    delta = np.array([r[1] for r in rows]) - P_idle
    sd = X.std(0); sd[sd == 0] = 1.0
    e, _ = nnls(X / sd, delta)
    e = e / sd
    alfa = e[0]
    extras = dict(zip([c for c in DYN if c != "alu"], e[1:]))
    coefs = {"alu": alfa, "div": extras["div"], "div_n": alfa}
    for c in INSTR_CATS[1:]:
        coefs[c] = alfa + extras[c]
    pred = X @ e
    resid = delta - pred
    ss_res = float(resid @ resid); ss_tot = float(delta @ delta)
    info = {"P_idle": P_idle, "alfa": alfa,
            "r2": 1 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
            "rmse": (ss_res / len(delta)) ** 0.5,
            "cond": float(np.linalg.cond(X / sd)),
            "pred_abs": pred + P_idle}
    return coefs, info


def ajustar(rows, P_idle):
    """Regresion SIN intercepto con P_idle FIJO: delta = P_med - P_idle = R @ e.
    R[k,c] = contador_c / T (tasa). Se escalan las columnas (solo dividir por sd,
    SIN centrar, para conservar el origen del modelo sin intercepto) y se resuelve
    por lstsq; luego se des-escala. Devuelve (coefs, info)."""
    R = np.array([[r[3][REGR[c]] / r[2] for c in DYN] for r in rows])
    delta = np.array([r[1] for r in rows]) - P_idle
    sd = R.std(0)
    sd[sd == 0] = 1.0
    Rs = R / sd
    e_s, *_ = np.linalg.lstsq(Rs, delta, rcond=None)
    e = e_s / sd
    pred = R @ e
    resid = delta - pred
    ss_res = float(resid @ resid)
    ss_tot = float(delta @ delta)                  # vs 0: no hay intercepto
    info = {
        "P_idle": P_idle,
        "r2": 1 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
        "rmse": (ss_res / len(delta)) ** 0.5,
        "cond": float(np.linalg.cond(Rs)),
        "pred_abs": pred + P_idle,                 # P predicha absoluta por corrida
    }
    return dict(zip(DYN, e)), info


def medir_regresion(progs, no_build, datos_csv):
    """Corre cada programa por JTAG, recupera P_avg del Sheet, escribe datos.csv."""
    if not no_build:
        run_make(DIR_REGR)
    elfs = {p: find_elf(p, DIR_REGR) for p in progs}
    header = ["fecha", "programa", "P_med_W", "T_s", "temp_C"] + modelo.COLS_CONTADORES
    rotar_si_header_distinto(datos_csv, header)
    inbox = sheet.Inbox()
    rows = []
    new = not os.path.exists(datos_csv)
    with open(datos_csv, "a", newline="") as fd:
        wr = csv.writer(fd)
        if new:
            wr.writerow(header)
        for i, prog in enumerate(progs, 1):
            extra = "" if prog == "idle" else ""
            print(f"==> [{i}/{len(progs)}] {prog} por JTAG...{extra}")
            P_med, T, cont, tstr = medir_uno(prog, elfs[prog], inbox)
            rows.append((prog, P_med, T, cont, tstr))
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            wr.writerow([ts, prog, f"{P_med:.6f}", f"{T:.6f}", tstr]
                        + [cont[k] for k in modelo.COLS_CONTADORES])
            fd.flush()
            subir_sheet("regresion", programa=prog, P_med_W=f"{P_med:.6f}", T_s=f"{T:.6f}",
                        temp_C=tstr, **{k: cont[k] for k in modelo.COLS_CONTADORES})
            if tstr:
                print(f"    temp die = {tstr} C")
            print(f"    P_med = {P_med:.4f} W   T = {T:.1f} s")
            time.sleep(3)
    return rows


def cmd_regresion(args):
    datos_csv = os.path.join(DIR_REGR, "datos.csv")
    coef_csv = os.path.join(DIR_REGR, "coeficientes.csv")

    if args.refit:
        if not os.path.exists(datos_csv):
            sys.exit(f"no existe {datos_csv}; corre la medicion primero (sin --refit)")
        rows = leer_datos(datos_csv)
        print(f"--refit: {len(rows)} corridas leidas de datos.csv")
    else:
        progs = args.programas or DEFAULT_PROGS
        if len(progs) < len(DYN) + 1:
            sys.exit(f"hacen falta >= {len(DYN)+1} programas mixtos (M > 7 incognitas); "
                     f"diste {len(progs)}")
        # con --pidle medir, idle.elf va PRIMERO en la misma sesion (mismo piso)
        if args.modelo == "efimon":
            progs = [v for q in progs for v in (q, q + "_d60", q + "_d30")]
            # pares diferenciales al set: filas que varian UNA categoria a la
            # vez (ctrl 8:1; mulh con/sin) -> anclan la atribucion de las
            # categorias en disputa con datos, sin trasplantes manuales
            progs += ["ctrl_rolled", "ctrl_unrolled", "mulh_con", "mulh_sin"]
        run_list = (["idle"] + progs) if args.pidle == "medir" else progs
        rows = medir_regresion(run_list, args.no_build, datos_csv)

    # separa la corrida de referencia (idle) de las de calibracion
    cal_rows = [r for r in rows if r[0] != "idle"]
    idle_rows = [r for r in rows if r[0] == "idle"]
    if args.pidle == "medir":
        if not idle_rows:
            sys.exit("--pidle medir pero no hay corrida 'idle' (mide sin --refit, o usa --pidle bucles)")
        P_idle = idle_rows[-1][1]
        T_idle = _temp_f(idle_rows[-1][4]) if len(idle_rows[-1]) > 4 else None
        fuente = f"idle medido en sesion ({P_idle:.4f} W)"
    else:
        P_idle = cargar_pidle(args.pidle)
        # si viene de bucles, hereda su T_idle; si es un numero suelto, no hay
        T_idle = modelo.ultimo_T_idle if args.pidle == "bucles" else None
        fuente = args.pidle

    if len(cal_rows) < len(DYN) + 1:
        sys.exit(f"solo {len(cal_rows)} programas de calibracion; hacen falta >= {len(DYN)+1}")

    if args.modelo == "efimon":
        if not idle_rows:
            sys.exit("--modelo efimon necesita la corrida de idle en sesion (--pidle medir)")
        coefs, info = ajustar_efimon(cal_rows, idle_rows)
        print(f"  modelo efimon: P_static (intercepto) = {info['P_idle']:.4f} W "
              f"(idle medido: {P_idle:.4f} W)")
        P_idle = info["P_idle"]
    elif args.modelo == "diferencial":
        coefs, info = ajustar_diferencial(cal_rows, P_idle)
        print(f"  modelo diferencial: alfa (costo base/instr) = {info['alfa']*1e9:.3f} nJ")
    else:
        coefs, info = ajustar(cal_rows, P_idle)

    with open(coef_csv, "w", newline="") as f:
        wc = csv.writer(f)
        desc = {"clasico": f"linea base FIJA de '{fuente}', SIN intercepto",
                "diferencial": "NNLS diferencial (alfa*r_total + sobrecostos)",
                "efimon": "NNLS CON INTERCEPTO ajustado (P_idle = P_static de la"
                          " regresion; barrido de intensidad d100/d60/d30)"}[args.modelo]
        wc.writerow([f"# Regresion (M2, modelo {args.modelo}). Generado {time.strftime('%Y-%m-%d %H:%M:%S')}."
                     f" {desc}. n={len(cal_rows)} corridas,"
                     f" R2={info['r2']:.4f}, RMSE={info['rmse']*1e3:.2f} mW, cond={info['cond']:.1f}"])
        wc.writerow(["parametro", "coef", "unidad"])
        wc.writerow(["P_idle", f"{info['P_idle']:.6f}", "W"])
        if T_idle is not None:
            wc.writerow(["T_idle", f"{T_idle:.2f}", "C"])
        for c in DYN:
            unidad = "J/ciclo" if c == "div" else "J/instr"
            wc.writerow([c, f"{coefs[c]:.6e}", unidad])
        if "div_n" in coefs:
            wc.writerow(["div_n", f"{coefs['div_n']:.6e}", "J/instr"])

    print(f"  {len(cal_rows)} programas de calibracion:  R2(vs0)={info['r2']:.4f}  "
          f"RMSE={info['rmse']*1e3:.2f} mW  cond={info['cond']:.1f}")
    for c in DYN:
        unidad = "J/ciclo" if c == "div" else "J/instr"
        flag = "  <-- NEGATIVO (soporte debil / anti-correlacion)" if coefs[c] < 0 else ""
        print(f"  {c:6s} {coefs[c]:+.6e} {unidad}{flag}")
    print("\nresiduos por corrida (medido - ajustado):")
    for r, pa in zip(cal_rows, info["pred_abs"]):
        prog, P_med = r[0], r[1]
        print(f"  {prog:14s} med={P_med:7.4f}  fit={pa:7.4f}  resid={(P_med-pa)*1e3:+7.2f} mW")
    print(f"\nGuardado: {coef_csv}")


# --- entrada ------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="metodo", required=True)

    ab = sub.add_parser("bucles", aliases=["1"], help="M1: bucles dominados por categoria")
    ab.add_argument("categorias", nargs="*", default=CATS,
                    help="categorias a medir; si se omite mide idle+7 categorias")
    ab.add_argument("--repeats", "--repeat", type=int, default=1)
    ab.add_argument("--no-build", action="store_true", help="no recompilar ELF antes de medir")
    ab.set_defaults(fn=cmd_bucles)

    ar = sub.add_parser("regresion", aliases=["2"], help="M2: regresion sobre programas mixtos")
    ar.add_argument("programas", nargs="*", default=DEFAULT_PROGS,
                    help="conjunto de calibracion; si se omite usa el por defecto")
    ar.add_argument("--modelo", default="clasico", choices=["clasico", "diferencial", "efimon"],
                    help="ajuste: 'clasico' (tasas por categoria, lstsq) o "
                         "'diferencial' (alfa*r_total + sobrecostos, NNLS) o "
                         "'efimon' (NNLS con intercepto + barrido de intensidad "
                         "_d60/_d30; corre 3 variantes por programa)")
    ar.add_argument("--pidle", default="medir",
                    help="P_idle FIJO: 'medir' (corre idle.elf en ESTA sesion, default), "
                         "'bucles' (de su coeficientes.csv) o un numero en W")
    ar.add_argument("--refit", action="store_true",
                    help="NO mide: re-ajusta desde datos.csv (para reusar mediciones ya hechas)")
    ar.add_argument("--no-build", action="store_true", help="no recompilar ELF antes de medir")
    ar.set_defaults(fn=cmd_regresion)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
