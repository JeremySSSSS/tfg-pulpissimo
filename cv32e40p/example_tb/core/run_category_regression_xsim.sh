#!/usr/bin/env bash
set -euo pipefail

VIVADO_SETTINGS=${VIVADO_SETTINGS:-/home/jjsotoch/Documents/viv/Vivado/2022.1/settings64.sh}
RISCV=${RISCV:-/home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18}
CORE_ROOT=${CORE_ROOT:-/home/jjsotoch/pulp/tfg-power/cv32e40p_direct}
DESIGN_RTL_DIR=${DESIGN_RTL_DIR:-${CORE_ROOT}/rtl}
LOG_DIR=${LOG_DIR:-xsim_category_regression_logs}

source "${VIVADO_SETTINGS}"

mkdir -p "${LOG_DIR}"

echo "==> Building firmware images"
make custom/hello_world.hex RISCV="${RISCV}"
make custom/category_counter_test.hex RISCV="${RISCV}"
make custom/category_counter_regression.hex RISCV="${RISCV}"

echo "==> Preparing XSim file list"
sed '/^+incdir/d; s#${DESIGN_RTL_DIR}#'"${DESIGN_RTL_DIR}"'#g' \
  "${CORE_ROOT}/cv32e40p_manifest.flist" > /tmp/cv32e40p_xsim.flist

sed 's/\.PULP_XPULP[[:space:]]*(PULP_XPULP)/.COREV_PULP      (PULP_XPULP)/; s/\.PULP_CLUSTER[[:space:]]*(PULP_CLUSTER)/.COREV_CLUSTER   (PULP_CLUSTER)/' \
  cv32e40p_tb_subsystem.sv > /tmp/cv32e40p_tb_subsystem_xsim.sv

echo "==> Compiling RTL and testbench"
rm -rf xsim.dir xvlog.log xelab.log xsim.log webtalk*.jou webtalk*.log

xvlog -sv -log "${LOG_DIR}/xvlog.log" \
  -i "${DESIGN_RTL_DIR}/include" \
  -i "${CORE_ROOT}/bhv" \
  -i "${CORE_ROOT}/bhv/include" \
  -i "${CORE_ROOT}/sva" \
  -f /tmp/cv32e40p_xsim.flist \
  include/perturbation_pkg.sv \
  amo_shim.sv \
  cv32e40p_random_interrupt_generator.sv \
  /tmp/cv32e40p_tb_subsystem_xsim.sv \
  dp_ram.sv \
  mm_ram.sv \
  riscv_gnt_stall.sv \
  riscv_rvalid_stall.sv \
  tb_top.sv

xelab tb_top -debug typical -s tb_top_behav -log "${LOG_DIR}/xelab.log"

run_firmware() {
  local name=$1
  local hex=$2
  local required_marker=$3
  local log="${LOG_DIR}/${name}.log"

  echo "==> Running ${name}: ${hex}"
  xsim tb_top_behav -R -log "${log}" \
    --testplusarg firmware="${hex}" \
    --testplusarg maxcycles=300000

  if ! grep -q "EXIT SUCCESS" "${log}"; then
    echo "FAIL ${name}: EXIT SUCCESS not found. See ${log}"
    return 1
  fi

  if grep -Eq "EXIT FAILURE|CATEGORY REGRESSION FAIL|FAIL " "${log}"; then
    echo "FAIL ${name}: failure marker found. See ${log}"
    return 1
  fi

  if [[ -n "${required_marker}" ]] && ! grep -q "${required_marker}" "${log}"; then
    echo "FAIL ${name}: required marker '${required_marker}' not found. See ${log}"
    return 1
  fi

  echo "PASS ${name}"
}

echo "==> Running regression"
run_firmware "hello_world" "custom/hello_world.hex" "hello world!"
run_firmware "category_smoke" "custom/category_counter_test.hex" "category counters"
run_firmware "category_deep" "custom/category_counter_regression.hex" "CATEGORY REGRESSION PASS"

echo "==> All category regression tests passed"
echo "Logs: ${LOG_DIR}"
