#!/usr/bin/env python3
"""Modelo dorado del clasificador v2 (DISENO_CLASIFICADOR_V2.md).

Parsea el trace de instrucciones retiradas del CV32E40P (bhv/cv32e40p_tracer,
define CV32E40P_TRACE_EXECUTION), clasifica cada instruccion de la region
medida segun las reglas del esquema v2 y compara contra los valores de CSR
que el test imprimio por el printer virtual (linea "CLASIF ...").

Region medida: desde DESPUES del 16.o csr-write a 0xBC0-0xBCF (reset) hasta
ANTES del primer csr-read de 0xBC0 (lectura). Se detecta decodificando el hex
crudo (opcode SYSTEM + campo csr), independiente del formato del mnemonico.

PASS si los 7 contadores de instrucciones coinciden y DIV_CYC cae en el rango
sano [2*n_div, 40*n_div]. Codigo de salida 0/1.
"""
import re
import sys
import glob

# Los mnemonicos se normalizan quitando el prefijo "c." (el tracer imprime
# c.bne, c.jal, c.lwsp, ... para las comprimidas)
MEM = {"lw", "lh", "lhu", "lb", "lbu", "sw", "sh", "sb", "flw", "fsw",
       "lwsp", "swsp"}
BRANCH = {"beq", "bne", "blt", "bge", "bltu", "bgeu", "beqz", "bnez",
          "blez", "bgez", "bltz", "bgtz"}
JUMP = {"jal", "jalr", "j", "jr", "ret"}
DIV = {"div", "divu", "rem", "remu"}
MULH = {"mulh", "mulhsu", "mulhu"}
MUL = {"mul"}
SYSTEM = {"fence", "fence.i", "fencei", "mret", "uret", "dret", "wfi",
          "ecall", "ebreak", "c.ebreak"}

LINE_RE = re.compile(
    r"^\s*(\d+)(?:ns)?\s+(\d+)\s+([0-9a-fA-F]{8})\s+([0-9a-fA-F]{4,8})\s+(\S+)(.*)$")


def is_csr_insn(hexval):
    """(es_csr, es_write, addr) decodificado del hex crudo."""
    op = hexval & 0x7F
    f3 = (hexval >> 12) & 0x7
    if op != 0x73 or f3 in (0, 4):
        return False, False, None
    addr = (hexval >> 20) & 0xFFF
    rs1_or_imm = (hexval >> 15) & 0x1F
    rd = (hexval >> 7) & 0x1F
    # csrrw/csrrwi siempre escriben; csrrs/c con rs1!=x0 tambien
    write = f3 in (1, 5) or (f3 in (2, 3, 6, 7) and rs1_or_imm != 0)
    read = not (f3 in (1, 5) and rd == 0) or True
    return True, write, addr


def parse_trace(path):
    rows = []
    with open(path) as f:
        for line in f:
            m = LINE_RE.match(line)
            if not m:
                continue
            cyc = int(m.group(2))
            pc = int(m.group(3), 16)
            ihex = int(m.group(4), 16)
            mnem = m.group(5).lower()
            rows.append((cyc, pc, ihex, mnem))
    return rows


def find_window(rows):
    resets = 0
    start = end = None
    for i, (_, _, ihex, _) in enumerate(rows):
        is_csr, write, addr = is_csr_insn(ihex)
        if not is_csr or addr is None:
            continue
        if 0xBC0 <= addr <= 0xBCF:
            if write:
                resets += 1
                if resets == 16:
                    start = i + 1
            elif start is not None and end is None:
                end = i
                break
    if start is None or end is None:
        sys.exit("ERROR: no se encontro la ventana medida en el trace "
                 f"(resets vistos: {resets})")
    return start, end


def classify(rows, start, end):
    cnt = dict(alu=0, mul=0, mulh=0, div=0, mem=0, ctrl=0, float=0,
               csr=0, system=0, unknown=0)
    div_cycle_est = 0
    window = rows[start:end]
    for k, (cyc, pc, ihex, raw_mnem) in enumerate(window):
        mnem = raw_mnem[2:] if raw_mnem.startswith("c.") else raw_mnem
        is_csr, _, _ = is_csr_insn(ihex)
        if is_csr or mnem.startswith("csr"):
            cnt["csr"] += 1
            continue
        if mnem in SYSTEM:
            cnt["system"] += 1
            continue
        if mnem in MEM:
            cnt["mem"] += 1
        elif mnem in BRANCH:
            # tomado si el siguiente PC retirado no es el fall-through
            if k + 1 < len(window):
                nxt = window[k + 1][1]
                fall = (pc + 2, pc + 4)
                if nxt in fall:
                    cnt["alu"] += 1      # no tomado -> ALU simple
                else:
                    cnt["ctrl"] += 1     # tomado -> CTRL
            else:
                cnt["unknown"] += 1
        elif mnem in JUMP:
            cnt["ctrl"] += 1
        elif mnem in DIV:
            cnt["div"] += 1
            if k + 1 < len(window):
                div_cycle_est += window[k + 1][0] - cyc
        elif mnem in MULH:
            cnt["mulh"] += 1
        elif mnem in MUL:
            cnt["mul"] += 1
        elif mnem.startswith("f") and mnem not in ("fence", "fence.i"):
            cnt["float"] += 1
        else:
            cnt["alu"] += 1
    return cnt, div_cycle_est, len(window)


def parse_dut(simlog):
    with open(simlog) as f:
        for line in f:
            m = re.search(r"CLASIF alu=(\d+) mul=(\d+) mulh=(\d+) div=(\d+) "
                          r"mem=(\d+) ctrl=(\d+) float=(\d+) divcyc=(\d+)", line)
            if m:
                keys = ["alu", "mul", "mulh", "div", "mem", "ctrl", "float",
                        "divcyc"]
                return dict(zip(keys, map(int, m.groups())))
    sys.exit("ERROR: el log de simulacion no contiene la linea CLASIF")


def main():
    if len(sys.argv) != 3:
        sys.exit(f"uso: {sys.argv[0]} <trace_core*.log|glob> <sim.log>")
    traces = sorted(glob.glob(sys.argv[1]))
    if not traces:
        sys.exit(f"ERROR: no existe trace {sys.argv[1]}")
    rows = parse_trace(traces[0])
    if not rows:
        sys.exit("ERROR: trace vacio o formato no reconocido")
    start, end = find_window(rows)
    golden, divcyc_est, n_window = classify(rows, start, end)
    dut = parse_dut(sys.argv[2])

    print(f"[golden] ventana: {n_window} instrucciones retiradas "
          f"(trace lineas {start}..{end})")
    print(f"[golden] {golden}")
    print(f"[dut]    {dut}")

    ok = True
    for k in ("alu", "mul", "mulh", "div", "mem", "ctrl", "float"):
        if golden[k] != dut[k]:
            print(f"FAIL {k}: golden={golden[k]} dut={dut[k]}")
            ok = False
    if golden["unknown"]:
        print(f"WARN: {golden['unknown']} instrucciones sin clasificar")

    # DIV_CYC: rango sano + comparacion informativa con estimado del trace
    n_div = golden["div"]
    if n_div:
        lo, hi = 2 * n_div, 40 * n_div
        if not (lo <= dut["divcyc"] <= hi):
            print(f"FAIL divcyc: {dut['divcyc']} fuera de [{lo},{hi}]")
            ok = False
        print(f"[info] divcyc dut={dut['divcyc']} estimado-del-trace={divcyc_est} "
              f"(promedio {dut['divcyc']/n_div:.1f} ciclos/div)")

    # Invariante: ventana completa = categorias + filtradas
    total = sum(golden[k] for k in
                ("alu", "mul", "mulh", "div", "mem", "ctrl", "float",
                 "csr", "system", "unknown"))
    if total != n_window:
        print(f"WARN invariante: clasificadas {total} != retiradas {n_window}")

    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
