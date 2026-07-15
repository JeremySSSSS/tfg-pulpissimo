# Modificaciones del TFG sobre el core CV32E40P

Este árbol parte de `pulp-platform/cv32e40p @ 7a49867`. El `README.md` original del
core se conserva intacto; este archivo documenta solo lo agregado por el proyecto.

## Archivos nuevos

- `rtl/cv32e40p_insn_classifier.sv` — clasificador de instrucciones v2: 7 contadores
  de 64 bits por categoría de unidad activa (`alu`, `mul`, `mulh`, `div`, `mem`,
  `ctrl`, `float`) más `div_cyc` (ciclos de ocupación del divisor), expuestos como
  16 CSR en pares LO/HI (0xBC0–0xBCF). La cascada de prioridad y el invariante
  `Σ nᵢ + n_csr + n_system = minstret` están documentados en el encabezado del
  propio módulo y verificados por el banco de pruebas de `example_tb/core/clasif_v2/`.

## Archivos modificados

- `rtl/cv32e40p_core.sv` — instanciación del clasificador y conexión de los eventos
  de retiro y del multiplexor de lectura CSR.
- `rtl/cv32e40p_decoder.sv` — señales de clasificación adicionales (evento `system`
  para filtrar `mret/wfi/fence`, que el decoder original contaba como ALU).
- `rtl/cv32e40p_id_stage.sv` — flopeo ID→EX de los eventos que consume el clasificador.
- `rtl/include/cv32e40p_pkg.sv` — direcciones de los CSR custom y tipos asociados.

## Firmware

- `firmware/caracterizacion/` — banco completo de caracterización energética y
  validación (tiene su propio README).
