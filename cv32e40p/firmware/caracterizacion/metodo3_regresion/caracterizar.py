#!/usr/bin/env python3
"""Metodo 3 (REGRESION lineal, estilo EfiMon) - caracterizacion.

A diferencia de aislar cada categoria (metodo 1 bucles / metodo 2 chopper), aqui
se corre un CONJUNTO de M PROGRAMAS REALES y MIXTOS, con perfiles de instruccion
DISTINTOS entre si, se mide la potencia TOTAL de cada uno (P_avg absoluto -> ESP32
con ads1115_read.ino) y se ajustan los coeficientes por minimos cuadrados.

P_idle FIJO (no es incognita): se toma el ya caracterizado en m1/m2. Asi el modelo
queda en su forma DINAMICA y SIN INTERCEPTO (7 incognitas, no 8):

    delta_k = P_med_k - P_idle = sum_i e_i*(n_i,k/T_k) + e_div*(c_div,k/T_k)

Motivo: a 10 MHz, midiendo toda la placa por +5V, los P_med varian muy poco entre
programas (~10 mW sobre ~9 W). Con P_idle como intercepto LIBRE el ajuste se
degenera (el intercepto se va por encima de todos los P_med y los coef salen
negativos). Fijando P_idle al valor ya caracterizado se quita esa degeneracion y
las categorias bien soportadas (alu/mem/ctrl/float) salen positivas y del orden
de m1/m2. Las debiles (mulh = 1 programa; div = anti-correlacionado con la
potencia por el stall del divisor) quedan como limitacion documentada.

REGLAS del metodo (EfiMon):
  - Calibracion = M programas MIXTOS, instrucciones DISTINTAS entre si (no bucles
    aislados de una categoria: eso es metodo 1/2). M > 7 incognitas (default 10).
  - DISTINTOS a los de verificacion (benchmarks/): el held-out se valida con
    verificar.py --metodo 3 sobre benchmarks/ (que NO entran en este ajuste).
  - P_idle NO se ajusta: por defecto se MIDE idle.elf en esta misma sesion
    (--pidle medir, mismo piso) -> evita la deriva de reusar un idle de otra hora.
    Alternativas: --pidle bucles|chopper (lo reusa de m1/m2) o un numero.

Conjunto de calibracion por defecto (fuentes/ -> elf/), 10 kernels mixtos:
sort, matmul, crc, strings, gcd, bsearch, dotprod, histogram, modpow, vecscale.
Con --pidle medir, idle.elf (de metodo1_bucles) corre PRIMERO como referencia.

Guarda datos.csv (crudo, incl. la fila idle) + coeficientes.csv (formato comun) +
pestaña 'regresion'. Requiere OpenOCD :3333 y ads1115_read.ino flasheado.

Uso:
    python3 caracterizar.py                       # mide idle + 10 mixtos, ajusta
    python3 caracterizar.py --pidle bucles        # P_idle reusado de m1 (no mide idle)
    python3 caracterizar.py --refit --pidle bucles # re-ajusta datos.csv con P_idle de m1
    python3 caracterizar.py --refit               # re-ajusta usando la fila idle de datos.csv
"""
import argparse
import csv
import os
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "comun"))
import jtag      # noqa: E402
import modelo    # noqa: E402
import sheet     # noqa: E402

F_CLK = modelo.F_CLK
# categorias del modelo y el contador que regresiona cada una (div va por ciclo)
DYN = ["alu", "mul", "mulh", "div", "mem", "ctrl", "float"]
REGR = {"alu": "n_alu", "mul": "n_mul", "mulh": "n_mulh", "div": "c_div",
        "mem": "n_mem", "ctrl": "n_ctrl", "float": "n_float"}
# de donde se toma el P_idle FIJO (su coeficientes.csv)
PIDLE_FUENTE = {"bucles": "metodo1_bucles", "chopper": "metodo2_chopper"}
# conjunto de calibracion por defecto: 13 programas REALES y MIXTOS (fuentes/),
# REDISENADOS para decorrelacionar (bajar VIF): cada categoria barre bajo->alto
# independiente; mulh/div/float en 3 programas c/u; anclas alu-bajo (memcpy/fsm).
DEFAULT = ["memcpy", "fsm", "crc", "matmul", "mulhash64", "dotprod", "gcd",
           "modpow", "trialdiv", "fpoly", "vecscale", "histogram", "sort"]
ELF_DIR = os.path.join(HERE, "elf")
FUENTES = os.path.join(HERE, "fuentes")
DATOS_CSV = os.path.join(HERE, "datos.csv")
COEF_CSV = os.path.join(HERE, "coeficientes.csv")
HOJA = "regresion"


def run_make():
    subprocess.run(["make", "-B", "all"], cwd=FUENTES, check=True)


def find_elf(prog):
    # idle.elf se reusa de metodo1_bucles (es el run de referencia del piso)
    for cand in (os.path.join(ELF_DIR, f"{prog}.elf"),
                 os.path.join(ROOT, "metodo1_bucles", "elf", f"{prog}.elf"), prog):
        if os.path.exists(cand):
            return cand
    raise FileNotFoundError(f"{prog}.elf no esta en {ELF_DIR} (corre 'make' en fuentes/)")


def cargar_pidle(fuente):
    """fuente = 'bucles'|'chopper' (lee P_idle de su coeficientes.csv) o un numero."""
    try:
        return float(fuente)
    except ValueError:
        pass
    if fuente not in PIDLE_FUENTE:
        sys.exit(f"--pidle invalido: {fuente} (usa bucles|chopper o un numero en W)")
    path = os.path.join(ROOT, PIDLE_FUENTE[fuente], "coeficientes.csv")
    P_idle, _ = modelo.cargar_coeficientes(path)
    if P_idle is None:
        sys.exit(f"no encontre P_idle en {path}; caracteriza primero ese metodo")
    return P_idle


def esperar_inbox(seen, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        filas = sheet.leer("inbox")
        if len(filas) > seen:
            return filas[-1], len(filas)
        print(f"    esperando P_avg del ESP32... ({time.time()-t0:4.0f}s/{timeout}s)")
        time.sleep(3)
    raise TimeoutError("timeout esperando P_avg en 'inbox'")


def leer_datos():
    """Lee las corridas de datos.csv -> [(prog, P_med, T, cont)] (para --refit)."""
    rows = []
    with open(DATOS_CSV) as f:
        for r in csv.DictReader(f):
            cont = {k: int(r[k]) for k in modelo.COLS_CONTADORES}
            rows.append((r["programa"], float(r["P_med_W"]), cont["mcycle"] / F_CLK, cont))
    return rows


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


def escribir_coef(coefs, info, n, fuente):
    with open(COEF_CSV, "w", newline="") as f:
        wc = csv.writer(f)
        wc.writerow([f"# Metodo 3 (regresion lineal, EfiMon). Generado {time.strftime('%Y-%m-%d %H:%M:%S')}."
                     f" P_idle FIJO de '{fuente}' (no es incognita); SIN intercepto:"
                     f" delta=P_med-P_idle = sum e_i*(n_i/T). n={n} corridas,"
                     f" R2(vs0)={info['r2']:.4f}, RMSE={info['rmse']*1e3:.2f} mW, cond={info['cond']:.1f}"])
        wc.writerow(["parametro", "coef", "unidad"])
        wc.writerow(["P_idle", f"{info['P_idle']:.6f}", "W"])
        for c in DYN:
            unidad = "J/ciclo" if c == "div" else "J/instr"
            wc.writerow([c, f"{coefs[c]:.6e}", unidad])


def medir(progs, no_build):
    """Corre cada programa por JTAG, recupera P_avg del Sheet, escribe datos.csv."""
    if not no_build:
        run_make()
    elfs = {p: find_elf(p) for p in progs}
    seen = len(sheet.leer("inbox"))
    rows = []
    new = not os.path.exists(DATOS_CSV)
    with open(DATOS_CSV, "a", newline="") as fd:
        wr = csv.writer(fd)
        if new:
            wr.writerow(["fecha", "programa", "P_med_W", "T_s", "temp_C"] + modelo.COLS_CONTADORES)
        for i, prog in enumerate(progs, 1):
            def get_pavg():
                nonlocal seen
                fila, seen = esperar_inbox(seen)
                return float(str(fila["p_avg"]).replace(",", "."))

            if prog == "idle":
                # idle (wfi) es robusto a la inflacion del JTAG (una ventana de idle
                # inflada sigue midiendo idle) y tiene IPC~0 por diseno -> 1 corrida.
                print(f"==> [{i}/{len(progs)}] {prog} por JTAG...")
                words = jtag.run_one(elfs[prog])
                P_med = get_pavg()
            else:
                print(f"==> [{i}/{len(progs)}] {prog} por JTAG (hasta 5x, me quedo con la limpia)...")
                words, P_med = jtag.run_one_limpio(elfs[prog], get_pavg)
            w = [modelo.to_int(x) for x in words]
            cont = modelo.contadores(w)
            T = cont["mcycle"] / F_CLK
            tC = jtag.ultima_temp_cC                 # temperatura del die (XADC), centi-C
            tstr = f"{tC/100:.2f}" if tC is not None else ""
            rows.append((prog, P_med, T, cont))
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            wr.writerow([ts, prog, f"{P_med:.6f}", f"{T:.6f}", tstr]
                        + [cont[k] for k in modelo.COLS_CONTADORES])
            fd.flush()
            try:    # la pestaña del Sheet es secundaria: datos.csv ya tiene la fila
                sheet.subir(HOJA, programa=prog, P_med_W=f"{P_med:.6f}", T_s=f"{T:.6f}",
                            temp_C=tstr, **{k: cont[k] for k in modelo.COLS_CONTADORES})
            except Exception as e:
                print(f"    [aviso] no se pudo subir a '{HOJA}' ({e}); sigo (esta en datos.csv)")
            if tstr:
                print(f"    temp die = {tstr} C")
            print(f"    P_med = {P_med:.4f} W   T = {T:.1f} s")
            time.sleep(3)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("programas", nargs="*", default=DEFAULT,
                    help="conjunto de calibracion; si se omite usa el por defecto")
    ap.add_argument("--pidle", default="medir",
                    help="P_idle FIJO: 'medir' (corre idle.elf en ESTA sesion, default), "
                         "'bucles'|'chopper' (de su coeficientes.csv) o un numero en W")
    ap.add_argument("--refit", action="store_true",
                    help="NO mide: re-ajusta desde datos.csv (para reusar mediciones ya hechas)")
    ap.add_argument("--no-build", action="store_true", help="no recompilar ELF antes de medir")
    args = ap.parse_args()

    if args.refit:
        if not os.path.exists(DATOS_CSV):
            sys.exit(f"no existe {DATOS_CSV}; corre la medicion primero (sin --refit)")
        rows = leer_datos()
        print(f"--refit: {len(rows)} corridas leidas de datos.csv")
    else:
        progs = args.programas or DEFAULT
        if len(progs) < len(DYN) + 1:
            sys.exit(f"hacen falta >= {len(DYN)+1} programas mixtos (M > 7 incognitas); "
                     f"diste {len(progs)}")
        # con --pidle medir, idle.elf va PRIMERO en la misma sesion (mismo piso)
        run_list = (["idle"] + progs) if args.pidle == "medir" else progs
        rows = medir(run_list, args.no_build)

    # separa la corrida de referencia (idle) de las de calibracion
    cal_rows = [r for r in rows if r[0] != "idle"]
    idle_rows = [r for r in rows if r[0] == "idle"]
    if args.pidle == "medir":
        if not idle_rows:
            sys.exit("--pidle medir pero no hay corrida 'idle' (mide sin --refit, o usa --pidle bucles)")
        P_idle = idle_rows[-1][1]
        fuente = f"idle medido en sesion ({P_idle:.4f} W)"
    else:
        P_idle = cargar_pidle(args.pidle)
        fuente = args.pidle

    if len(cal_rows) < len(DYN) + 1:
        sys.exit(f"solo {len(cal_rows)} programas de calibracion; hacen falta >= {len(DYN)+1}")

    coefs, info = ajustar(cal_rows, P_idle)
    escribir_coef(coefs, info, len(cal_rows), fuente)

    print(f"  {len(cal_rows)} programas de calibracion:  R2(vs0)={info['r2']:.4f}  "
          f"RMSE={info['rmse']*1e3:.2f} mW  cond={info['cond']:.1f}")
    for c in DYN:
        unidad = "J/ciclo" if c == "div" else "J/instr"
        flag = "  <-- NEGATIVO (soporte debil / anti-correlacion)" if coefs[c] < 0 else ""
        print(f"  {c:6s} {coefs[c]:+.6e} {unidad}{flag}")
    print("\nresiduos por corrida (medido - ajustado):")
    for (prog, P_med, _, _), pa in zip(cal_rows, info["pred_abs"]):
        print(f"  {prog:14s} med={P_med:7.4f}  fit={pa:7.4f}  resid={(P_med-pa)*1e3:+7.2f} mW")
    print(f"\nGuardado: {COEF_CSV}")


if __name__ == "__main__":
    main()
