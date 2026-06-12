#!/usr/bin/env bash
set -euo pipefail

VIVADO_SETTINGS=${VIVADO_SETTINGS:-/home/jjsotoch/Documents/viv/Vivado/2022.1/settings64.sh}
RISCV=${RISCV:-/home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18}
CORE_ROOT=${CORE_ROOT:-/home/jjsotoch/pulp/tfg-power/cv32e40p_direct}
DESIGN_RTL_DIR=${DESIGN_RTL_DIR:-${CORE_ROOT}/rtl}
LOG_DIR=${LOG_DIR:-xsim_category_freeze_logs}
FIRMWARE_HEX=${FIRMWARE_HEX:-custom/category_counter_freeze.hex}

source "${VIVADO_SETTINGS}"

mkdir -p "${LOG_DIR}"

echo "==> Building firmware image"
make "${FIRMWARE_HEX}" RISCV="${RISCV}"

echo "==> Preparing XSim file list"
sed '/^+incdir/d; s#${DESIGN_RTL_DIR}#'"${DESIGN_RTL_DIR}"'#g' \
  "${CORE_ROOT}/cv32e40p_manifest.flist" > /tmp/cv32e40p_xsim_freeze.flist

sed 's/\.PULP_XPULP[[:space:]]*(PULP_XPULP)/.COREV_PULP      (PULP_XPULP)/; s/\.PULP_CLUSTER[[:space:]]*(PULP_CLUSTER)/.COREV_CLUSTER   (PULP_CLUSTER)/' \
  cv32e40p_tb_subsystem.sv > /tmp/cv32e40p_tb_subsystem_freeze_xsim.sv

echo "==> Compiling RTL and testbench"
rm -rf xsim.dir xvlog.log xelab.log xsim.log webtalk*.jou webtalk*.log

xvlog -sv -log "${LOG_DIR}/xvlog.log" \
  -i "${DESIGN_RTL_DIR}/include" \
  -i "${CORE_ROOT}/bhv" \
  -i "${CORE_ROOT}/bhv/include" \
  -i "${CORE_ROOT}/sva" \
  -f /tmp/cv32e40p_xsim_freeze.flist \
  include/perturbation_pkg.sv \
  amo_shim.sv \
  cv32e40p_random_interrupt_generator.sv \
  /tmp/cv32e40p_tb_subsystem_freeze_xsim.sv \
  dp_ram.sv \
  mm_ram.sv \
  riscv_gnt_stall.sv \
  riscv_rvalid_stall.sv \
  tb_top.sv

xelab tb_top -debug typical -s tb_top_freeze_behav -log "${LOG_DIR}/xelab.log"

cat > /tmp/category_freeze_read.tcl <<'TCL'
restart
run 20 us
puts T20_ARITH=[get_value /tb_top/wrapper_i/top_i/core_i/insn_classifier_i/arithmetic_q]
puts T20_LOGIC=[get_value /tb_top/wrapper_i/top_i/core_i/insn_classifier_i/logic_q]
puts T20_MEMORY=[get_value /tb_top/wrapper_i/top_i/core_i/insn_classifier_i/memory_q]
puts T20_BRANCH=[get_value /tb_top/wrapper_i/top_i/core_i/insn_classifier_i/branch_q]
puts T20_JUMP=[get_value /tb_top/wrapper_i/top_i/core_i/insn_classifier_i/jump_q]
puts T20_FLOAT=[get_value /tb_top/wrapper_i/top_i/core_i/insn_classifier_i/floating_q]
run 20 us
puts T40_ARITH=[get_value /tb_top/wrapper_i/top_i/core_i/insn_classifier_i/arithmetic_q]
puts T40_LOGIC=[get_value /tb_top/wrapper_i/top_i/core_i/insn_classifier_i/logic_q]
puts T40_MEMORY=[get_value /tb_top/wrapper_i/top_i/core_i/insn_classifier_i/memory_q]
puts T40_BRANCH=[get_value /tb_top/wrapper_i/top_i/core_i/insn_classifier_i/branch_q]
puts T40_JUMP=[get_value /tb_top/wrapper_i/top_i/core_i/insn_classifier_i/jump_q]
puts T40_FLOAT=[get_value /tb_top/wrapper_i/top_i/core_i/insn_classifier_i/floating_q]
exit
TCL

RUN_LOG="${LOG_DIR}/category_freeze.log"

echo "==> Running ${FIRMWARE_HEX}"
xsim tb_top_freeze_behav -tclbatch /tmp/category_freeze_read.tcl -log "${RUN_LOG}" \
  --testplusarg firmware="${FIRMWARE_HEX}" \
  --testplusarg maxcycles=300000

sed -n '/T20_/p;/T40_/p' "${RUN_LOG}"

if ! diff -q <(sed -n 's/^T20_//p' "${RUN_LOG}") <(sed -n 's/^T40_//p' "${RUN_LOG}") >/dev/null; then
  echo "FAIL: counters changed between 20us and 40us. See ${RUN_LOG}"
  exit 1
fi

echo "PASS: counters are frozen after program body"
echo "Log: ${RUN_LOG}"
