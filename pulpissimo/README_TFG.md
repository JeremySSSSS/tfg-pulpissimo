# Modificaciones del TFG sobre PULPissimo

Este árbol parte de `pulp-platform/pulpissimo @ bfc3d9a`. El `README.md` original de
la plataforma se conserva; este archivo documenta solo lo agregado por el proyecto,
todo bajo `target/fpga/pulpissimo-nexys/`.

## Archivos nuevos

- `rtl/xadc_temp.v` — lectura de la temperatura del die vía XADC del Artix-7,
  mapeada a un registro accesible por el firmware. Es la fuente del dato de
  temperatura que acompaña cada medición de potencia del banco.
- `openocd-ft232h.cfg` — configuración de OpenOCD para el adaptador JTAG FT232H
  usado por el banco de caracterización (carga y arranque de ELF sin tocar la placa).
- `run_batch.tcl` — regeneración del bitstream en modo batch (sin GUI de Vivado).

## Archivos modificados

- `rtl/xilinx_pulpissimo.v` — instanciación del bloque XADC en el top de la Nexys.
- `constraints/nexys4DDR.xdc` — restricciones adicionales del proyecto.
- `tcl/run.tcl` — inclusión de las fuentes nuevas en el flujo de síntesis.

## Bitstream

`bitstream/xilinx_pulpissimo_xadc.bit` es el bitstream usado en toda la
caracterización y validación del TFG (core con clasificador v2 + XADC).
Nota: la FPU de este bitstream cuelga con ciertos patrones float+memoria
(limitación documentada en el TFG); las cargas float del banco usan los
patrones que sí operan de forma estable.
