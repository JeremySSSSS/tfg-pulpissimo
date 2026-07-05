#!/usr/bin/env python3
"""Ejecuta una lista de .elf por JTAG/GDB y vuelca 'results' (18 words)
automaticamente -- sin transcribir 'x/18xw &results' a mano.

Requiere OpenOCD corriendo (gdb server riscv.cpu en :3333).

Uso:
    python3 run_and_log.py alu.elf div.elf valid.elf

Agrega una fila "name,w0,...,w17" a captures.csv por cada .elf (P_avg se
agrega despues, viene del ESP32/Sheet). Reusa el mismo flujo de
run_sequence.sh: target remote, monitor reset halt, load, continue.
"""
import csv
import os
import re
import subprocess
import sys
import time

GDB_BIN = os.environ.get("GDB_BIN", "gdb-multiarch")
RETRIES = int(os.environ.get("RETRIES", "5"))
GDB_SCRIPT = """\
set pagination off
set confirm off
target remote :3333
monitor reset halt
load
continue
x/18xw &results
"""

LINE_RE = re.compile(r"^0x[0-9a-fA-F]+:(\s+0x[0-9a-fA-F]+)+\s*$")
WORD_RE = re.compile(r"0x[0-9a-fA-F]+")
PROMPT_RE = re.compile(r"^(\(gdb\)\s*)+")
BAD_CONN_MARKERS = (
    "Could not read registers",
    "not supported by this target",
    "is `exec'",
)


def run_one(elf):
    out = ""
    for attempt in range(1, RETRIES + 1):
        proc = subprocess.run(
            [GDB_BIN, elf],
            input=GDB_SCRIPT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
        )
        out = proc.stdout

        if any(marker in out for marker in BAD_CONN_MARKERS):
            print(f"    (intento {attempt}/{RETRIES}: conexion JTAG inestable, reintentando...)")
            time.sleep(2)
            continue

        words = []
        for line in out.splitlines():
            line = PROMPT_RE.sub("", line.strip())
            if LINE_RE.match(line):
                _, rest = line.split(":", 1)
                words.extend(WORD_RE.findall(rest))

        if len(words) == 18:
            return words

        print(f"    (intento {attempt}/{RETRIES}: solo {len(words)}/18 words, reintentando...)")
        time.sleep(2)

    raise RuntimeError(f"{elf}: fallo tras {RETRIES} intentos.\n--- ultima salida GDB ---\n{out}")


def main(argv):
    if len(argv) < 2:
        sys.exit("Uso: run_and_log.py elf1 [elf2 ...]")

    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(here, "captures.csv")
    new_file = not os.path.exists(out_path)

    with open(out_path, "a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["name"] + [f"w{i}" for i in range(18)])
        for elf in argv[1:]:
            name = os.path.splitext(os.path.basename(elf))[0]
            print(f"==> {elf}")
            words = run_one(elf)
            writer.writerow([name] + words)
            f.flush()
            print(f"    {name}: " + " ".join(words))

    print(f"\nGuardado en {out_path}")


if __name__ == "__main__":
    main(sys.argv)
