#!/usr/bin/env python3
"""Diagnostico de FLOAT: corre fpgain.elf por JTAG (float minimo: flw+fmul+fadd,
SIN FMA ni fcvt) y dice si la FPU lo banca o se cuelga. Requiere OpenOCD :3333.
El firmware del ESP32 no importa (solo se mira si el programa llega a ebreak).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "comun"))
import jtag

nombre = sys.argv[1] if len(sys.argv) > 1 else "logistic"
elf = os.path.join(HERE, "benchmarks", f"{nombre}.elf")
print(f"Corriendo {nombre}.elf (float register-only)...")
print("Si en ~60 s NO dice COMPLETO -> se colgo: Ctrl-C.\n")

w = [int(x, 16) for x in jtag.run_one(elf)]
mcycle = (w[17] - w[16]) & 0xFFFFFFFF
print(f"COMPLETO ✅   mcycle={mcycle}  (~{mcycle/10e6:.1f} s)")
print("=> La FPU corre float sin FMA/fcvt. Podemos hacer un float benchmark REAL.")
