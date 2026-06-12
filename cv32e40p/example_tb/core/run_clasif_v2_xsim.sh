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
# Modos:
#   ./run_clasif_v2_xsim.sh                  test dirigido (clasif_smoke)
#   LOOP=alu|mul|mulh|div|mem|ctrl|float     bucle dominado de esa categoría
#   DIVOPS=min|max                           operandos de div (default: aleatorios)
#   ITERS=n                                  iteraciones del bucle (default 8)
#   GUI=1                                    ondas (firmware termina en wfi)
#   SKIPRTL=1                                no recompilar el RTL (reusar snapshot)
TEST=${TEST:-clasif_v2/clasif_smoke}
SRCS="${TEST}.c"
MARCH="rv32imc"
ABIFLAGS=""

# En GUI el firmware termina en wfi (core dormido, contadores congelados):
# basta una simulación corta. En batch corre completo (printf + golden).
if [ "${GUI:-0}" = "1" ]; then
  MAXCYCLES=${MAXCYCLES:-20000}
  EXTRA_CFLAGS="-DWAVES_HOLD"
else
  MAXCYCLES=${MAXCYCLES:-400000}
  EXTRA_CFLAGS=""
fi

if [ -n "${LOOP:-}" ]; then
  TEST="clasif_v2/loop_${LOOP}"
  SRCS="clasif_v2/loop_main.c clasif_v2/loop_${LOOP}.S"
  EXTRA_CFLAGS="${EXTRA_CFLAGS} -DLOOP_$(echo "${LOOP}" | tr '[:lower:]' '[:upper:]')"
  [ -n "${ITERS:-}" ] && EXTRA_CFLAGS="${EXTRA_CFLAGS} -DITERS=${ITERS}u"
  case "${DIVOPS:-}" in
    min) EXTRA_CFLAGS="${EXTRA_CFLAGS} -DDIV_MIN" ;;
    max) EXTRA_CFLAGS="${EXTRA_CFLAGS} -DDIV_MAX" ;;
  esac
  if [ "${LOOP}" = "float" ]; then
    MARCH="rv32imfc"
    ABIFLAGS="-mabi=ilp32f"
    echo "AVISO: loop_float requiere el tb elaborado con FPU=1 (pendiente)."
  fi
fi

source "${VIVADO_SETTINGS}"

GCC=$(ls "${RISCV}"/bin/riscv32-*-gcc | head -1)
PREFIX="${GCC%gcc}"

echo "== Compilando firmware: ${SRCS} =="
"${GCC}" -march=${MARCH} ${ABIFLAGS} ${EXTRA_CFLAGS} -o "${TEST}.elf" -w -Os -g -nostdlib \
  -T custom/link.ld -static \
  custom/crt0.S ${SRCS} custom/syscalls.c custom/vectors.S \
  -I "${RISCV}"/riscv32-*-elf/include \
  -L "${RISCV}"/riscv32-*-elf/lib \
  -lc -lm -lgcc
"${PREFIX}objcopy" -O verilog "${TEST}.elf" "${TEST}.hex"

if [ "${SKIPRTL:-0}" = "1" ] && [ -d xsim.dir/tb_top_clasif ]; then
  echo "== RTL: reusando snapshot existente (SKIPRTL=1) =="
else
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
fi

if [ "${GUI:-0}" = "1" ]; then
  echo "== Simulando (GUI) =="
  # GUI normal: agregá las señales de insn_classifier_i al waveform desde el
  # árbol de instancias (tb_top > wrapper_i > wrapper_i > core_i) y dale
  # "run all". El firmware (compilado con WAVES_HOLD) ejecuta wfi tras leer
  # los contadores: el core se duerme y los valores quedan congelados en
  # 12/5/7/6/8/5/0/150 hasta el final — miralos donde sea del tramo final.
  # Si existe una configuración de ondas guardada, cargarla automáticamente
  WCFG=""
  [ -f clasif_v2/tb_top_clasif.wcfg ] && WCFG="--view clasif_v2/tb_top_clasif.wcfg"
  xsim tb_top_clasif -gui ${WCFG} \
    --testplusarg firmware="${TEST}.hex" \
    --testplusarg maxcycles="${MAXCYCLES}"
else
  echo "== Simulando =="
  xsim tb_top_clasif -R \
    --testplusarg firmware="${TEST}.hex" \
    --testplusarg maxcycles="${MAXCYCLES}" 2>&1 | tee sim_clasif.log

  echo "== Modelo dorado =="
  python3 clasif_v2/golden_clasif.py 'trace_core_*.log' sim_clasif.log
fi
