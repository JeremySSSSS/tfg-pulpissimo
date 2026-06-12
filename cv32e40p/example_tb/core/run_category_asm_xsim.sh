#!/usr/bin/env bash
set -euo pipefail

VIVADO_SETTINGS=${VIVADO_SETTINGS:-/home/jjsotoch/Documents/viv/Vivado/2022.1/settings64.sh}
RISCV=${RISCV:-/home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18}
CORE_ROOT=${CORE_ROOT:-/home/jjsotoch/pulp/tfg-power/cv32e40p_direct}
DESIGN_RTL_DIR=${DESIGN_RTL_DIR:-${CORE_ROOT}/rtl}
LOG_DIR=${LOG_DIR:-xsim_category_asm_logs}
FIRMWARE_HEX=${FIRMWARE_HEX:-custom/category_counter_asm.hex}
PASS_MARKER=${PASS_MARKER:-}

source "${VIVADO_SETTINGS}"

mkdir -p "${LOG_DIR}"

echo "==> Building firmware image"
make "${FIRMWARE_HEX}" RISCV="${RISCV}"

echo "==> Preparing XSim file list"
sed '/^+incdir/d; s#${DESIGN_RTL_DIR}#'"${DESIGN_RTL_DIR}"'#g' \
  "${CORE_ROOT}/cv32e40p_manifest.flist" > /tmp/cv32e40p_xsim_asm.flist

sed 's/\.PULP_XPULP[[:space:]]*(PULP_XPULP)/.COREV_PULP      (PULP_XPULP)/; s/\.PULP_CLUSTER[[:space:]]*(PULP_CLUSTER)/.COREV_CLUSTER   (PULP_CLUSTER)/' \
  cv32e40p_tb_subsystem.sv > /tmp/cv32e40p_tb_subsystem_asm_xsim.sv

echo "==> Compiling RTL and testbench"
rm -rf xsim.dir xvlog.log xelab.log xsim.log webtalk*.jou webtalk*.log

xvlog -sv -log "${LOG_DIR}/xvlog.log" \
  -i "${DESIGN_RTL_DIR}/include" \
  -i "${CORE_ROOT}/bhv" \
  -i "${CORE_ROOT}/bhv/include" \
  -i "${CORE_ROOT}/sva" \
  -f /tmp/cv32e40p_xsim_asm.flist \
  include/perturbation_pkg.sv \
  amo_shim.sv \
  cv32e40p_random_interrupt_generator.sv \
  /tmp/cv32e40p_tb_subsystem_asm_xsim.sv \
  dp_ram.sv \
  mm_ram.sv \
  riscv_gnt_stall.sv \
  riscv_rvalid_stall.sv \
  tb_top.sv

xelab tb_top -debug typical -s tb_top_asm_behav -log "${LOG_DIR}/xelab.log"

RUN_LOG="${LOG_DIR}/category_asm.log"

echo "==> Running ${FIRMWARE_HEX}"
xsim tb_top_asm_behav -R -log "${RUN_LOG}" \
  --testplusarg firmware="${FIRMWARE_HEX}" \
  --testplusarg maxcycles=300000

if ! grep -q "EXIT SUCCESS" "${RUN_LOG}"; then
  echo "FAIL: EXIT SUCCESS not found. See ${RUN_LOG}"
  exit 1
fi

if grep -Eq "EXIT FAILURE|ASM CATEGORY TEST FAIL" "${RUN_LOG}"; then
  echo "FAIL: failure marker found. See ${RUN_LOG}"
  exit 1
fi

if [ -n "${PASS_MARKER}" ] && ! grep -q "${PASS_MARKER}" "${RUN_LOG}"; then
  echo "FAIL: pass marker '${PASS_MARKER}' not found. See ${RUN_LOG}"
  exit 1
fi

echo "PASS: assembly category-counter check completed"
echo "Log: ${RUN_LOG}"
