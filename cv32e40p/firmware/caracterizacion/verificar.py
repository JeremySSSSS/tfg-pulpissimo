#!/usr/bin/env python3
"""Verificador COMUN a los 2 metodos. Carga cualquier .elf, lo corre por JTAG,
recupera el P_avg medido del Sheet (pestaña 'inbox'), y predice la potencia con
los coeficientes del metodo elegido (--metodo bucles|regresion). Compara
predicho vs medido y lo guarda en la pestaña 'verificacion' del Sheet + un CSV local.

Uso:
    python3 verificar.py --metodo regresion sha256 md5 floyd
    python3 verificar.py --metodo 1 aes            # 1=bucles 2=regresion
"""
import argparse
import csv
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "comun"))
import sheet      # noqa: E402
import modelo     # noqa: E402
import jtag       # noqa: E402

METODOS = {"bucles": "bucles", "regresion": "regresion"}

# idle CORTO para el chequeo/re-anclaje de la linea base (~5 s de ventana vs los
# ~20 s del idle de caracterizacion): 17 reps x 0.3 s. Suficiente para detectar
# una deriva de >2 mW (ruido de la ventana corta: ~0.5 mW).
IDLE_CHECK_ELF = os.path.join(HERE, "bucles", "elf", "idle_check.elf")


def build_idle_check():
    if os.path.exists(IDLE_CHECK_ELF):
        return
    riscv = os.environ.get("RISCV",
                           "/home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18")
    subprocess.run(
        [f"{riscv}/bin/riscv32-unknown-elf-gcc",
         "-nostdlib", "-nostartfiles", "-static", "-Os", "-g", "-mabi=ilp32",
         "-Wl,-T,link.ld", "-Wl,--build-id=none", "-I.", "-march=rv32imc",
         "-DIDLE_REPS=17", "-o", IDLE_CHECK_ELF, "idle.S"],
        cwd=os.path.join(HERE, "bucles", "fuentes"), check=True)
ALIAS = {"1": "bucles", "2": "regresion"}
VERIF_CSV = os.path.join(HERE, "verificacion.csv")


def find_elf(prog):
    for cand in (os.path.join(HERE, "benchmarks", f"{prog}.elf"), prog):
        if os.path.exists(cand):
            return cand
    raise FileNotFoundError(f"{prog}.elf no esta en benchmarks/ (ni es una ruta valida)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metodo", required=True, help="bucles|regresion (o 1|2)")
    ap.add_argument("--pidle", default="temp",
                    help="linea base: 'temp' (P_idle del archivo corregido por la "
                         "temperatura del die de CADA corrida, default), 'medir' "
                         "(mide idle_check ahora), 'archivo' (tal cual) o un numero en W")
    ap.add_argument("programas", nargs="+")
    args = ap.parse_args()

    met = ALIAS.get(args.metodo, args.metodo)
    if met not in METODOS:
        sys.exit(f"metodo invalido: {args.metodo}  (usa bucles|regresion o 1|2)")
    coef_path = os.path.join(HERE, METODOS[met], "coeficientes.csv")
    if not os.path.exists(coef_path):
        sys.exit(f"falta {coef_path} -> caracteriza primero con metodo {met}")

    P_idle, coef = modelo.cargar_coeficientes(coef_path)
    print(f"=== Verificacion (metodo: {met}) ===")
    print(f"  coeficientes: {', '.join(sorted(coef))}")

    new = not os.path.exists(VERIF_CSV)
    fcsv = open(VERIF_CSV, "a", newline="")
    wr = csv.writer(fcsv)
    if new:
        wr.writerow(["fecha", "metodo", "programa", "T_s", "P_med_W", "P_pred_W", "err_pct", "temp_C"]
                    + modelo.COLS_CONTADORES)

    inbox = sheet.Inbox()

    # Linea base de ESTA sesion de validacion. El P_idle del coeficientes.csv
    # envejece (deriva termica + instrumento, ~mW en horas): si la validacion no
    # es inmediata a la caracterizacion, sesga TODAS las predicciones parejo.
    # La linea base pertenece a la sesion (protocolo paso 3) -> se mide aqui.
    # correccion por temperatura (modo 'temp'): P_idle del archivo se ajusta con
    # la pendiente del barrido y la temperatura del die de CADA corrida:
    #   P_base(run) = P_idle_ref + b*(T_run - T_ref)
    # Cubre la parte TERMICA de la deriva sin volver a medir idle; la parte de
    # instrumento (~mW en horas) queda como error aceptado (<0.5%, documentado).
    b_temp = None
    T_ref = modelo.ultimo_T_idle
    if args.pidle == "temp":
        b_temp = modelo.cargar_pendiente_termica(os.path.join(HERE, "pidle_fit.csv"))
        if b_temp is None or T_ref is None:
            falta = "pidle_fit.csv (corre el barrido)" if b_temp is None \
                    else "T_idle en coeficientes.csv (recaracteriza)"
            print(f"  [AVISO] sin correccion por temperatura (falta {falta}); "
                  f"uso P_idle del archivo tal cual = {P_idle:.4f} W\n")
            b_temp = None
        else:
            print(f"  P_idle(T) = {P_idle:.4f} W @ {T_ref:.2f} C  "
                  f"+  {b_temp*1e3:.2f} mW/C * (T_corrida - {T_ref:.2f} C)\n")
    elif args.pidle == "medir":
        build_idle_check()
        print("  midiendo P_idle de la sesion (idle_check, ~5 s)...")
        for intento in range(1, 4):
            jtag.run_one(IDLE_CHECK_ELF)
            try:
                P_ses = inbox.get_pavg()
                break
            except TimeoutError:
                if intento == 3:
                    raise
                print(f"    idle: ventana sin P_avg; REINTENTO ({intento}/3)")
        drift = 1e3 * (P_ses - P_idle)
        print(f"  P_idle sesion = {P_ses:.4f} W  (archivo: {P_idle:.4f} W, "
              f"deriva {drift:+.2f} mW)")
        if abs(drift) > 2.0:
            print(f"  [ALERTA] la linea base derivo {drift:+.1f} mW desde la "
                  f"caracterizacion (termico + instrumento). Re-anclada "
                  f"automaticamente; los coeficientes siguen validos (son deltas).")
        print()
        P_idle = P_ses
    elif args.pidle == "archivo":
        print(f"  P_idle = {P_idle:.4f} W (del coeficientes.csv)\n")
    else:
        P_idle = float(args.pidle)
        print(f"  P_idle = {P_idle:.4f} W (fijado por linea de comandos)\n")
    print(f"{'programa':12s} {'P_med[W]':>9s} {'P_din[W]':>9s} {'P_pred[W]':>10s} {'err%':>7s}  T[s]")
    errs = []
    for prog in args.programas:
        elf = find_elf(prog)
        print(f"==> corriendo {prog} por JTAG (hasta 5x, me quedo con la limpia)...")
        words, pbar = jtag.run_one_limpio(elf, inbox.get_pavg)
        w = [modelo.to_int(x) for x in words]
        T = ((w[17] - w[16]) & modelo.MASK32) / modelo.F_CLK
        P_din = modelo.potencia_dinamica(w, coef)   # el modelo (dinamica)
        cont = modelo.contadores(w)
        tC = jtag.ultima_temp_cC                      # temperatura del die (XADC)
        tstr = f"{tC/100:.2f}" if tC is not None else ""
        # base a la temperatura de ESTA corrida (0 si no hay pendiente/lectura)
        T_run = tC / 100 if tC is not None else None
        P_base = P_idle + modelo.correccion_termica(T_run, T_ref, b_temp)
        P_pred = P_base + P_din
        err = 100 * (P_pred - pbar) / pbar
        errs.append(abs(err))
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        sheet.subir("verificacion", metodo=met, programa=prog, T_s=f"{T:.3f}",
                    P_med_W=f"{pbar:.6f}", P_pred_W=f"{P_pred:.6f}", err_pct=f"{err:.4f}",
                    temp_C=tstr, **{k: cont[k] for k in modelo.COLS_CONTADORES})
        wr.writerow([ts, met, prog, f"{T:.3f}", f"{pbar:.6f}", f"{P_pred:.6f}", f"{err:.4f}", tstr]
                    + [cont[k] for k in modelo.COLS_CONTADORES])
        fcsv.flush()
        print(f"{prog:12s} {pbar:9.4f} {P_din:9.4f} {P_pred:10.4f} {err:7.2f}  {T:5.1f}  {tstr}C")

    fcsv.close()
    if errs:
        print(f"\nerror absoluto medio = {sum(errs)/len(errs):.2f}%   "
              f"max = {max(errs):.2f}%   (objetivo <10%)")
    print(f"Guardado en {VERIF_CSV} y en la pestaña 'verificacion' del Sheet.")


if __name__ == "__main__":
    main()
