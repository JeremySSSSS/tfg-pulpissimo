#!/usr/bin/env python3
"""Carga un .elf por JTAG/GDB, lo corre hasta ebreak y devuelve los 18 words de
'results' (16 CSR del clasificador + mcycle ini/fin). Comun a los 3 metodos y al
verificador. Requiere OpenOCD (gdb server riscv.cpu en :3333).
"""
import os
import re
import subprocess
import time

GDB_BIN = os.environ.get("GDB_BIN", "gdb-multiarch")
RETRIES = int(os.environ.get("RETRIES", "5"))
GDB_TIMEOUT = int(os.environ.get("GDB_TIMEOUT", "480"))   # load + corrida larga
# Tras volcar 'results', con el core halteado en ebreak, lee la temperatura del
# die por el XADC: habilita los pines GPIO io_19..30 (GPIO_EN + modo input) y lee
# GPIO_IN -> codigo de 12 bits del XADC (ver pulp_temp.h). 'TEMPCODE' lo parsea el
# Python. Inofensivo si el bitstream no tiene XADC (devuelve 0).
GDB_SCRIPT = """\
set pagination off
set confirm off
target remote :3333
monitor reset halt
load
continue
x/18xw &results
set {unsigned int}0x1A10100C = 0
set {unsigned int}0x1A101080 = {unsigned int}0x1A101080 | 0x7ff80000
printf "TEMPCODE %u\\n", ({unsigned int}0x1A101100 >> 19) & 0xfff
"""

_LINE = re.compile(r"^0x[0-9a-fA-F]+:(\s+0x[0-9a-fA-F]+)+\s*$")
_WORD = re.compile(r"0x[0-9a-fA-F]+")
_PROMPT = re.compile(r"^(\(gdb\)\s*)+")
_TEMP = re.compile(r"TEMPCODE\s+(\d+)")
_BAD = ("Could not read registers", "not supported by this target", "is `exec'")
MASK32 = 0xFFFFFFFF

# temperatura del die (centi-grados) de la ULTIMA corrida de run_one; None si no
# se pudo leer. Conversion Xilinx: T = code*503.975/4096 - 273.15.
ultima_temp_cC = None


def _temp_cC_de(code):
    return (code * 50397) // 4096 - 27315   # centi-grados (C x 100)


def mcycle_de(words):
    """T en ciclos = (mcycle_fin - mcycle_ini) & 32b, de los 18 words de results."""
    w = [int(x, 16) for x in words]
    return (w[17] - w[16]) & MASK32


def ninstr_de(words):
    """Instrucciones RETIRADAS = suma de las 7 categorias (LO+HI<<32), SIN divcyc
    (que son ciclos, no instr). Indices LO en results: alu0 mul2 mulh4 div6 mem8
    ctrl10 float12 (divcyc14 se excluye)."""
    w = [int(x, 16) for x in words]
    return sum(w[i] + (w[i + 1] << 32) for i in (0, 2, 4, 6, 8, 10, 12))


def run_one(elf):
    """Devuelve los 18 words (strings hex) de 'results' tras correr el elf."""
    out = ""
    for intento in range(1, RETRIES + 1):
        out = subprocess.run([GDB_BIN, elf], input=GDB_SCRIPT, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, timeout=GDB_TIMEOUT).stdout
        if any(m in out for m in _BAD):
            print(f"    (intento {intento}/{RETRIES}: JTAG inestable, reintento...)")
            time.sleep(2)
            continue
        words = []
        for line in out.splitlines():
            line = _PROMPT.sub("", line.strip())
            if _LINE.match(line):
                _, rest = line.split(":", 1)
                words.extend(_WORD.findall(rest))
        if len(words) == 18:
            global ultima_temp_cC
            mt = _TEMP.search(out)
            ultima_temp_cC = _temp_cC_de(int(mt.group(1))) if mt else None
            return words
        print(f"    (intento {intento}/{RETRIES}: {len(words)}/18 words, reintento...)")
        time.sleep(2)
    raise RuntimeError(f"{elf}: fallo tras {RETRIES} intentos.\n--- ultima salida GDB ---\n{out}")


IPC_MAX = 1.02     # IPC fisico maximo (single-issue); > esto = mcycle corrupto (wrap)


def run_one_limpio(elf, get_pavg, reps=5, tol=0.02):
    """Corre `elf` hasta `reps` veces y devuelve (words, P_med) de la corrida LIMPIA.
    Motivo: el FT232H inestable haltea el core durante `continue`; como
    dcsr.stopcount=0, mcycle SIGUE contando durante el halt Y la ventana GPIO del
    ESP queda abierta -> mcycle y P_med salen inflados/diluidos de forma NO
    determinista (mismo programa -> mcycle varia hasta 74x). A veces mcycle se lee
    CORRUPTO-chico (wrap > 2^32) dando IPC>1 imposible.

    Seleccion robusta SIN suponer un IPC esperado (sirve para alu de alto IPC,
    para div/idle de IPC bajo POR DISENO, etc.): la ejecucion es DETERMINISTA, asi
    que la corrida limpia es la de MENOR mcycle VALIDO (un halt solo SUMA ciclos
    parados). Valido = IPC<=1.02 (descarta wraps). `get_pavg()` espera y devuelve
    el P_med del ESP de la corrida recien hecha (misma ventana fisica que mcycle).
    Early-stop cuando dos corridas validas COINCIDEN en mcycle (valor reproducible
    = sin halt). Avisa solo si nunca se estabiliza (JTAG ruidoso de verdad)."""
    validas = []       # (mcycle, words, pmed)
    estable = False
    for i in range(1, reps + 1):
        words = run_one(elf)
        mc = mcycle_de(words)
        ni = ninstr_de(words)
        ipc = ni / mc if mc else 1e9
        pmed = get_pavg()
        if ipc > IPC_MAX:
            print(f"    corrida {i}/{reps}: mcycle={mc:,}  IPC={ipc:.2f} CORRUPTA (wrap), descarto")
            continue
        validas.append((mc, words, pmed))
        validas.sort(key=lambda r: r[0])
        mejor = validas[0][0]
        marca = "  <- mas limpia (min)" if mc == mejor else f"  (inflada {mc/mejor:.1f}x)"
        print(f"    corrida {i}/{reps}: mcycle={mc:,}  IPC={ipc:.3f}  T={mc/1e7:.1f}s  P={pmed:.4f}W{marca}")
        # reproducible: las dos menores coinciden -> determinista -> limpia
        if len(validas) >= 2 and abs(validas[0][0] - validas[1][0]) <= tol * validas[0][0]:
            estable = True
            break
    if not validas:
        raise RuntimeError(f"{elf}: ninguna corrida valida en {reps} (mcycle siempre corrupto/wrap)")
    if not estable and len(validas) >= 2:
        print(f"    [AVISO] mcycle no se estabilizo ({len(validas)} corridas distintas): JTAG "
              f"ruidoso, uso la de menor mcycle. Reasenta el cable / baja adapter_khz / revisa el shunt.")
    return validas[0][1], validas[0][2]
