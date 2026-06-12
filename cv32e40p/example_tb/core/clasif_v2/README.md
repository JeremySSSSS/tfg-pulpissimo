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

En modo GUI el flujo es manual, como siempre: agregar las señales de
`insn_classifier_i` al waveform desde el árbol de instancias
(`tb_top > wrapper_i > wrapper_i > core_i`) y darle `run all`. En GUI el
firmware se compila con `-DWAVES_HOLD`: tras leer los contadores ejecuta
**`wfi`** (el mismo truco del viejo `category_counter_freeze.c`) — el core se
duerme y los contadores quedan **congelados** en sus valores finales hasta el
fin de la simulación. No hay que cazar ningún instante: en cualquier punto
del tramo final del waveform se lee
`alu=12 mul=5 mulh=7 div=6 mem=8 ctrl=5 float=0 divcyc=150`.
(En este modo el programa no llega al printf, por eso el careo con el modelo
dorado solo corre en modo batch, donde WAVES_HOLD no se define.)

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
