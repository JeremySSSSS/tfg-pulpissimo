#!/usr/bin/env bash
# Pipeline de potencia por simulacion para UNA categoria (etapa 1, FPU=0):
#   1) compila loop_<cat> con ITERS grande (bucle corre mas que la ventana SAIF)
#   2) XSim reusa el snapshot, captura core.saif sobre la ventana en regimen
#   3) Vivado aplica el SAIF al core sintetizado y reporta potencia dinamica
# Uso:  ./run_power.sh alu        (o mul/mulh/div/mem/ctrl)
set -euo pipefail
cd "$(dirname "$0")"

CAT="${1:?Uso: ./run_power.sh <alu|mul|mulh|div|mem|ctrl>}"
ITERS="${ITERS:-5000}"
TBDIR="$(cd .. && pwd)"          # example_tb/core (donde vive el snapshot xsim.dir)
RISCV="${RISCV:-/home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18}"
VIVADO_SETTINGS="${VIVADO_SETTINGS:-/home/jjsotoch/Documents/viv/Vivado/2022.1/settings64.sh}"
source "${VIVADO_SETTINGS}"
GCC="$(ls "${RISCV}"/bin/riscv32-*-gcc | head -1)"
PREFIX="${GCC%gcc}"

UC="$(echo "$CAT" | tr '[:lower:]' '[:upper:]')"
ELF="${TBDIR}/clasif_v2/pwr_${CAT}.elf"
HEX="${TBDIR}/clasif_v2/pwr_${CAT}.hex"

echo "== [1/3] compilando loop_${CAT} (ITERS=${ITERS}) =="
"${GCC}" -march=rv32imc -DLOOP_${UC} -DITERS=${ITERS}u -o "${ELF}" -w -Os -g -nostdlib \
  -T "${TBDIR}/custom/link.ld" -static \
  "${TBDIR}/custom/crt0.S" "${TBDIR}/clasif_v2/loop_main.c" "${TBDIR}/clasif_v2/loop_${CAT}.S" \
  "${TBDIR}/custom/syscalls.c" "${TBDIR}/custom/vectors.S" \
  -I "${RISCV}"/riscv32-*-elf/include -L "${RISCV}"/riscv32-*-elf/lib -lc -lm -lgcc
"${PREFIX}objcopy" -O verilog "${ELF}" "${HEX}"

echo "== [2/3] XSim: capturando SAIF (reusa snapshot) =="
cd "${TBDIR}"
rm -f power_sim/core.saif
xsim tb_top_clasif -tclbatch power_sim/saif_capture.tcl \
  --testplusarg firmware="${HEX}" \
  --testplusarg maxcycles=400000 > power_sim/xsim_pwr_${CAT}.log 2>&1
mv -f core.saif "power_sim/core_${CAT}.saif" 2>/dev/null || \
  { echo "ERROR: no se genero core.saif"; tail -20 power_sim/xsim_pwr_${CAT}.log; exit 1; }

echo "== [3/3] Vivado: report_power =="
cd power_sim
vivado -mode batch -nojournal -log power_${CAT}.vivado.log \
  -source power_report.tcl -tclargs "core_${CAT}.saif" "power_${CAT}.rpt" \
  > /dev/null 2>&1

echo "== Resultado ${CAT} =="
grep -iE 'Dynamic \(|Total On-Chip|Signals|Logic|Clocks' "power_${CAT}.rpt" | head
