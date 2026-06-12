# Suite de verificación del clasificador v2

Verificación auto-verificable del clasificador por unidad activa
(`DISENO_CLASIFICADOR_V2.md`) con **modelo dorado**: el tracer del core
(`bhv/cv32e40p_tracer.sv`, define `CV32E40P_TRACE_EXECUTION`) registra cada
instrucción retirada; `golden_clasif.py` clasifica ese trace en software con
las reglas del esquema y compara contra los CSR que el test imprime.

## Uso

```bash
./run_clasif_v2_xsim.sh                  # batch: simula + careo con el golden, PASS/FAIL
GUI=1 ./run_clasif_v2_xsim.sh            # abre el GUI de XSim para inspeccionar ondas
TEST=clasif_v2/otro ./run_clasif_v2_xsim.sh   # correr otro test
```

En modo GUI, `waves_clasif.tcl` hace todo solo: agrega las señales del
clasificador al waveform y **detiene la simulación al final de la región
medida** (condición `div=6 && mem=8 && ctrl=5` sobre registros), imprimiendo
los 8 contadores en la consola TCL. Ahí los valores deben ser
`alu=12 mul=5 mulh=7 div=6 mem=8 ctrl=5 float=0 divcyc=150`. Si seguís con
`run all`, los contadores crecen sin control (volcado de resultados + printf)
— es normal; los valores válidos son los del punto de parada. El careo con el
modelo dorado solo corre en modo batch.

Notas de `add_condition` en XSim 2022.1 (aprendidas a golpes): los literales
de las condiciones se interpretan en BINARIO (escribir 6 como `110`), no
acepta `-label` ni literales estilo Verilog (`2'b00`), las señales
combinacionales producen disparos falsos por glitches (usar registros), y en
t=0 las X disparan cualquier condición (armar después de `run 100 ns`).

Requiere Vivado 2022.1 (XSim + UVM para el tracer) y la toolchain RISC-V
PULP. PASS/FAIL por código de salida.

## Tests

| Test | Cubre |
|------|-------|
| `clasif_smoke.c` | Las 7 categorías con conteos conocidos, branches tomados (3, con instrucción anulada que no debe contarse) y no tomados (2), filtros csr (2 csrr mcycle) y system (2 fence), DIV_CYC con operandos variados |

Resultado de referencia (2026-06-11, primer PASS):
`alu=12 mul=5 mulh=7 div=6 mem=8 ctrl=5 float=0 divcyc=150` — golden
idéntico; DIV_CYC coincidió ciclo-exacto con el estimado por deltas del
trace (promedio 25.0 ciclos/div).

## Cómo decide el golden la ventana medida

Decodifica el hex crudo: la ventana va desde después del 16.º csr-write a
0xBC0–0xBCF (reset) hasta el primer csr-read de 0xBC0 (lectura). Dentro,
clasifica por mnemónico; un branch es tomado si el siguiente PC retirado no
es el fall-through (pc+2/pc+4).

## Pendientes de la suite

- Test de instrucciones de sistema privilegiadas (mret/wfi requieren setup
  de trap handler).
- Test FLOAT (la elaboración del tb usa FPU=0; la FPU está confirmada en
  hardware — riesgo conocido fpnew+XSim).
- Cargas mixtas largas y secuencias aleatorias para regresión.
- Test de overflow LO→HI (escribir 0xFFFFFFFF en LO y verificar carry).
