#!/usr/bin/env python3
"""Metodo 1 (bucles homogeneos) - caracterizacion.

Cada ELF abre una unica ventana GPIO, ejecuta un bucle dominado por una categoria,
cierra la ventana y vuelca los contadores a 'results'. El ESP32 debe tener
ads1115_read.ino flasheado, porque aqui se mide P_avg absoluto, no delta chopper.

Modelo:
    P_idle se mide con idle.elf.
    Para cada categoria: delta = P_cat - P_idle.
    coef_i = delta * T / n_i                  [J/instr]
    coef_div = delta * T / c_div              [J/ciclo]

Uso:
    python3 caracterizar.py --repeats 1
    python3 caracterizar.py --repeats 2 idle alu mul div
"""
import argparse
import csv
import os
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'comun'))
import jtag      # noqa: E402
import modelo    # noqa: E402
import sheet     # noqa: E402

F_CLK = modelo.F_CLK
CATS = ['idle', 'alu', 'mul', 'mulh', 'div', 'mem', 'ctrl', 'float']
COEF_CATS = ['alu', 'mul', 'mulh', 'div', 'mem', 'ctrl', 'float']
DENOM = {
    'alu': 'n_alu',
    'mul': 'n_mul',
    'mulh': 'n_mulh',
    'div': 'c_div',
    'mem': 'n_mem',
    'ctrl': 'n_ctrl',
    'float': 'n_float',
}
DATOS_CSV = os.path.join(HERE, 'datos.csv')
COEF_CSV = os.path.join(HERE, 'coeficientes.csv')
HOJA = 'bucles'


def fnum(x):
    return float(str(x).replace(',', '.'))


def run_make():
    subprocess.run(['make', '-B', 'all'], cwd=os.path.join(HERE, 'fuentes'), check=True)


def esperar_inbox(seen, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        filas = sheet.leer('inbox')
        if len(filas) > seen:
            return filas[-1], len(filas)
        print(f"    esperando P_avg del ESP32... ({time.time()-t0:4.0f}s/{timeout}s)")
        time.sleep(3)
    raise TimeoutError("timeout esperando P_avg en 'inbox'")


def elf_path(cat):
    return os.path.join(HERE, 'elf', f'{cat}.elf')


def stats_run(words):
    w = [modelo.to_int(x) if isinstance(x, str) else x for x in words]
    cont = modelo.contadores(w)
    T = cont['mcycle'] / F_CLK
    return w, cont, T


def promedio(rows, key):
    return statistics.mean(r[key] for r in rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('categorias', nargs='*', default=CATS,
                    help='categorias a medir; si se omite mide idle+7 categorias')
    ap.add_argument('--repeats', '--repeat', type=int, default=1)
    ap.add_argument('--no-build', action='store_true', help='no recompilar ELF antes de medir')
    args = ap.parse_args()

    cats = args.categorias or CATS
    invalid = [c for c in cats if c not in CATS]
    if invalid:
        sys.exit(f"categorias invalidas: {', '.join(invalid)}")
    if 'idle' not in cats:
        cats = ['idle'] + cats

    if not args.no_build:
        run_make()

    seen = len(sheet.leer('inbox'))
    runs = {c: [] for c in cats}

    new = not os.path.exists(DATOS_CSV)
    with open(DATOS_CSV, 'a', newline='') as fd:
        wr = csv.writer(fd)
        if new:
            wr.writerow(['fecha', 'categoria', 'rep', 'P_med_W', 'P_idle_ref_W', 'delta_W',
                         'T_s', 'denom', 'coef'] + modelo.COLS_CONTADORES)

        for cat in cats:
            elf = elf_path(cat)
            if not os.path.exists(elf):
                sys.exit(f"falta {elf}; corre make en {os.path.join(HERE, 'fuentes')}")
            for rep in range(1, args.repeats + 1):
                def get_pavg():
                    nonlocal seen
                    fila, seen = esperar_inbox(seen)
                    return fnum(fila['p_avg'])

                if cat == 'idle':
                    # idle (wfi) robusto a la inflacion del JTAG, IPC~0 por diseno -> 1 corrida
                    print(f"==> {cat} rep {rep}/{args.repeats}  (idle wfi)")
                    words = jtag.run_one(elf)
                    P_med = get_pavg()
                else:
                    print(f"==> {cat} rep {rep}/{args.repeats}  (bucle homogeneo, hasta 5x limpia)")
                    words, P_med = jtag.run_one_limpio(elf, get_pavg)
                _, cont, T = stats_run(words)
                rec = {'P_med': P_med, 'T': T, 'cont': cont}
                runs[cat].append(rec)

                ts = time.strftime('%Y-%m-%d %H:%M:%S')
                wr.writerow([ts, cat, rep, f'{P_med:.6f}', '', '', f'{T:.6f}', '', '']
                            + [cont[k] for k in modelo.COLS_CONTADORES])
                fd.flush()
                sheet.subir(HOJA, categoria=cat, rep=rep, P_med_W=f'{P_med:.6f}',
                            T_s=f'{T:.6f}', **{k: cont[k] for k in modelo.COLS_CONTADORES})
                print(f"    P_med = {P_med:.4f} W   T = {T:.1f} s")
                time.sleep(3)

    P_idle = promedio(runs['idle'], 'P_med')
    coefs = {}
    resumen = []
    for cat in COEF_CATS:
        if cat not in runs or not runs[cat]:
            continue
        cat_coefs = []
        deltas = []
        denoms = []
        for r in runs[cat]:
            delta = r['P_med'] - P_idle
            denom = r['cont'][DENOM[cat]]
            if denom <= 0:
                raise RuntimeError(f'{cat}: denominador {DENOM[cat]} es 0')
            cat_coefs.append(delta * r['T'] / denom)
            deltas.append(delta)
            denoms.append(denom)
        coefs[cat] = statistics.mean(cat_coefs)
        resumen.append((cat, statistics.mean(deltas), statistics.mean(denoms), coefs[cat], len(cat_coefs)))

    with open(COEF_CSV, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow([f"# Metodo 1 (bucles homogeneos). Generado {time.strftime('%Y-%m-%d %H:%M:%S')}.",
                    'coef=(P_cat-P_idle)*T/n; div usa DIVCYC.'])
        w.writerow(['parametro', 'coef', 'unidad'])
        w.writerow(['P_idle', f'{P_idle:.6f}', 'W'])
        for cat in COEF_CATS:
            if cat not in coefs:
                continue
            unidad = 'J/ciclo' if cat == 'div' else 'J/instr'
            w.writerow([cat, f'{coefs[cat]:.6e}', unidad])

    # Resumen por consola (datos.csv ya quedo escrito en streaming arriba).
    print(f"\nP_idle = {P_idle:.4f} W")
    for cat, delta, denom, coef, n in resumen:
        unidad = 'J/ciclo' if cat == 'div' else 'J/instr'
        print(f"  {cat:6s} delta={delta*1e3:7.3f} mW  denom={denom:.0f}  coef={coef:.6e} {unidad}  (n={n})")

    print(f"\nGuardado: {DATOS_CSV}, {COEF_CSV} + pestaña '{HOJA}' del Sheet.")


if __name__ == '__main__':
    main()
