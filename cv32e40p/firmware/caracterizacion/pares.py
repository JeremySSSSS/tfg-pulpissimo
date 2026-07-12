#!/usr/bin/env python3
"""Pares diferenciales: despeja e_ctrl y e_mulh de la RESTA de dos variantes
identicas salvo la categoria en disputa. Tercer camino, independiente del
aislamiento (M1) y de la regresion (M2):

    e = (E_A - E_B) / (n_A - n_B),   E_i = (P_i - P_idle) * T_i

- ctrl: mismo computo con el lazo enrollado (un salto tomado por cuerpo) vs
  desenrollado x8 (mismos conteos de TODO lo demas, saltos 8:1).
- mulh: bloques identicos con y sin 16 mulh intercalados en el computo.

Uso:  python3 pares.py     (banco arriba; ~2 min: idle + 4 ventanas)
"""
import csv
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "comun"))
import jtag    # noqa: E402
import sheet   # noqa: E402
import modelo  # noqa: E402

# referencia para el veredicto (campana final 11-jul)
M1 = {"ctrl": 5.526, "mulh": 5.819}
M2 = {"ctrl": 8.955, "mulh": 3.753}

inbox = sheet.Inbox()


def medir(nombre, elf):
    print(f"==> {nombre}...")
    words, P = jtag.run_medido(elf, inbox.get_pavg)
    w = [modelo.to_int(x) for x in words]
    c = modelo.contadores(w)
    T = c["mcycle"] / modelo.F_CLK
    tC = jtag.ultima_temp_cC
    print(f"    P = {P:.4f} W   T = {T:.1f} s   temp = {tC/100 if tC else 0:.2f} C")
    return {"P": P, "T": T, "c": c}


def main():
    print("==> idle de sesion...")
    for i in range(3):
        jtag.run_one(os.path.join(HERE, "bucles", "elf", "idle.elf"))
        try:
            P_idle = inbox.get_pavg()
            break
        except TimeoutError:
            if i == 2:
                raise
            print("    idle sin P_avg; reintento")
    print(f"    P_idle = {P_idle:.4f} W")

    r = {}
    for n in ("ctrl_rolled", "ctrl_unrolled", "mulh_con", "mulh_sin"):
        r[n] = medir(n, os.path.join(HERE, "pares", "elf", n + ".elf"))

    def E(n):
        return (r[n]["P"] - P_idle) * r[n]["T"]

    e_ctrl = (E("ctrl_rolled") - E("ctrl_unrolled")) / \
             (r["ctrl_rolled"]["c"]["n_ctrl"] - r["ctrl_unrolled"]["c"]["n_ctrl"])
    e_mulh = (E("mulh_con") - E("mulh_sin")) / \
             (r["mulh_con"]["c"]["n_mulh"] - r["mulh_sin"]["c"]["n_mulh"])

    print("\n=== VEREDICTO DIFERENCIAL ===")
    print(f"  e_ctrl = {e_ctrl*1e9:6.3f} nJ    (M1: {M1['ctrl']}  M2: {M2['ctrl']})")
    print(f"  e_mulh = {e_mulh*1e9:6.3f} nJ    (M1: {M1['mulh']}  M2: {M2['mulh']})")

    out = os.path.join(HERE, "pares", "pares.csv")
    new = not os.path.exists(out)
    with open(out, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["fecha", "P_idle_W", "e_ctrl_nJ", "e_mulh_nJ"]
                       + [f"{n}_{k}" for n in r for k in ("P", "T")])
        w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), f"{P_idle:.6f}",
                    f"{e_ctrl*1e9:.4f}", f"{e_mulh*1e9:.4f}"]
                   + [f"{r[n][k]:.6f}" for n in r for k in ("P", "T")])
    print(f"guardado en {out}")


if __name__ == "__main__":
    main()
