#!/usr/bin/env bash

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENOCD_CFG="${PULP_OPENOCD_CFG:-/home/jjsotoch/pulp/tfg-pulpissimo/pulpissimo/target/fpga/pulpissimo-zcu104/openocd-zcu104.cfg}"
OPENOCD_BIN="${OPENOCD_BIN:-openocd}"
GDB_BIN="${GDB_BIN:-/usr/bin/gdb-multiarch}"

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 m00_mix.elf [m01_mix.elf ...]" >&2
  exit 1
fi

cleanup() {
  jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT INT TERM

"$OPENOCD_BIN" -f "$OPENOCD_CFG" >/tmp/linear_regression_openocd.log 2>&1 &
sleep 3

for elf in "$@"; do
  if [[ ! -f "$HERE/$elf" ]]; then
    echo "No existe: $HERE/$elf" >&2
    exit 1
  fi

  echo "============================================================"
  echo "Cargando $elf"
  echo "Cuando termine y caiga en ebreak, mide P_avg y lee resultados."
  echo "============================================================"

  "$GDB_BIN" "$HERE/$elf" <<'GDB'
set pagination off
target remote localhost:3333
monitor reset halt
load
continue
x/18xw &results
GDB

  echo
  echo "Finalizado $elf."
  echo "Anota la potencia promedio y pega la salida de:"
  echo "  x/18xw &results"
  echo "Pulsa Enter para continuar con el siguiente."
  read -r
done
