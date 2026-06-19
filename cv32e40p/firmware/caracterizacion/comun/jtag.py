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
GDB_SCRIPT = """\
set pagination off
set confirm off
target remote :3333
monitor reset halt
load
continue
x/18xw &results
"""

_LINE = re.compile(r"^0x[0-9a-fA-F]+:(\s+0x[0-9a-fA-F]+)+\s*$")
_WORD = re.compile(r"0x[0-9a-fA-F]+")
_PROMPT = re.compile(r"^(\(gdb\)\s*)+")
_BAD = ("Could not read registers", "not supported by this target", "is `exec'")


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
            return words
        print(f"    (intento {intento}/{RETRIES}: {len(words)}/18 words, reintento...)")
        time.sleep(2)
    raise RuntimeError(f"{elf}: fallo tras {RETRIES} intentos.\n--- ultima salida GDB ---\n{out}")
