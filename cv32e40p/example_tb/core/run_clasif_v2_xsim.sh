#!/usr/bin/env bash
# Suite de verificación del clasificador v2 sobre XSim.
# Compila el core de ESTE árbol (cv32e40p/ del monorepo) con el tracer
# habilitado, corre el test y valida contra el modelo dorado.
set -euo pipefail

cd "$(dirname "$0")"

VIVADO_SETTINGS=${VIVADO_SETTINGS:-/home/jjsotoch/Documents/viv/Vivado/2022.1/settings64.sh}
RISCV=${RISCV:-/home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18}
CORE_ROOT="$(cd ../.. && pwd)"
DESIGN_RTL_DIR="${CORE_ROOT}/rtl"
FPNEW_DIR=${FPNEW_DIR:-$(ls -d /home/jjsotoch/pulp/pulpissimo/.bender/git/checkouts/fpnew-*/src 2>/dev/null | head -1)}
CF_MATH=$(find /home/jjsotoch/pulp/pulpissimo/.bender/git/checkouts -name cf_math_pkg.sv 2>/dev/null | head -1)
TEST=${TEST:-clasif_v2/clasif_smoke}
MAXCYCLES=${MAXCYCLES:-400000}

source "${VIVADO_SETTINGS}"

GCC=$(ls "${RISCV}"/bin/riscv32-*-gcc | head -1)
PREFIX="${GCC%gcc}"

echo "== Compilando firmware ${TEST}.c =="
"${GCC}" -march=rv32imc -o "${TEST}.elf" -w -Os -g -nostdlib \
  -T custom/link.ld -static \
  custom/crt0.S "${TEST}.c" custom/syscalls.c custom/vectors.S \
  -I "${RISCV}"/riscv32-*-elf/include \
  -L "${RISCV}"/riscv32-*-elf/lib \
  -lc -lm -lgcc
"${PREFIX}objcopy" -O verilog "${TEST}.elf" "${TEST}.hex"

echo "== Compilando RTL (con tracer) =="
# cv32e40p_fpu_pkg.sv fue eliminado por el commit upstream 7a49867 pero el
# flist upstream quedó sin actualizar; fpnew_pkg (externo) lo sustituye.
sed '/^+incdir/d; /cv32e40p_fpu_pkg/d; s#${DESIGN_RTL_DIR}#'"${DESIGN_RTL_DIR}"'#g' \
  "${CORE_ROOT}/cv32e40p_manifest.flist" > /tmp/clasif_v2_xsim.flist

rm -rf xsim.dir xvlog.log xelab.log xsim.log trace_core_*.log

xvlog -sv -L uvm -d CV32E40P_TRACE_EXECUTION \
  -i "${DESIGN_RTL_DIR}/include" \
  -i "${CORE_ROOT}/bhv" \
  -i "${CORE_ROOT}/bhv/include" \
  ${CF_MATH} \
  "${FPNEW_DIR}/fpnew_pkg.sv" \
  -f /tmp/clasif_v2_xsim.flist \
  "${CORE_ROOT}/bhv/cv32e40p_tracer.sv" \
  "${CORE_ROOT}/bhv/cv32e40p_core_log.sv" \
  include/perturbation_pkg.sv \
  amo_shim.sv \
  cv32e40p_random_interrupt_generator.sv \
  cv32e40p_tb_subsystem.sv \
  dp_ram.sv \
  mm_ram.sv \
  riscv_gnt_stall.sv \
  riscv_rvalid_stall.sv \
  tb_top.sv > xvlog_run.log 2>&1 || { tail -20 xvlog_run.log; exit 1; }

echo "== Elaborando =="
xelab tb_top -L uvm -debug typical -s tb_top_clasif > xelab_run.log 2>&1 \
  || { grep -E "ERROR" xelab_run.log | head -20; exit 1; }

echo "== Simulando =="
xsim tb_top_clasif -R \
  --testplusarg firmware="${TEST}.hex" \
  --testplusarg maxcycles="${MAXCYCLES}" 2>&1 | tee sim_clasif.log

echo "== Modelo dorado =="
python3 clasif_v2/golden_clasif.py 'trace_core_*.log' sim_clasif.log
