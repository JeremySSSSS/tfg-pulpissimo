# TFG — Módulo hardware de clasificación de instrucciones para estimación de consumo energético en RISC-V

**Estudiante:** Jeremy Jesús Soto Chacón · Ingeniería Electrónica, Instituto Tecnológico de Costa Rica
**Plataforma:** CV32E40P (RV32IMC) sobre PULPissimo, FPGA Digilent Nexys A7-100T (Artix-7)

## Descripción

Este repositorio contiene el trabajo de RTL, plataforma FPGA y firmware del Trabajo
Final de Graduación: un **módulo hardware de clasificación de instrucciones** integrado
en el pipeline del core CV32E40P. El módulo cuenta, en tiempo real y sin instrumentar el
software, cuántas instrucciones retiradas pertenecen a cada una de 6 categorías
(Arithmetic, Logic, Memory, Branch, Jump, Floating point) y expone los conteos mediante
**registros CSR custom**.

Con esos conteos `n_i` y coeficientes energéticos `e_i` obtenidos por caracterización
eléctrica directa (sensado de corriente INA240 + ADS1115 + ESP32 sobre la Nexys A7),
se estima el consumo de una aplicación bare-metal como:

```
E_est = Σ e_i · n_i        P_est = E_est / T
```

La hipótesis del TFG es que esta estimación alcanza un error relativo medio inferior al
10 % respecto a la medición eléctrica directa.

## Estructura del repositorio

| Directorio | Contenido | Base upstream |
|---|---|---|
| `pulpissimo/` | SoC PULPissimo: top-level FPGA, constraints, flujo de síntesis, bitstreams | `pulp-platform/pulpissimo @ bfc3d9a` |
| `cv32e40p/` | Core CV32E40P con el clasificador integrado + firmware de caracterización | `pulp-platform/cv32e40p @ 7a49867` |
| `Anteproyecto/` | Anteproyecto aprobado (fuentes LaTeX, figuras y PDF compilado: `main.pdf`) | — |
| `Documento TFG/` | Informe final (tesis) en desarrollo: plantilla con capítulos de implementación, resultados y conclusiones en esqueleto | — |
| `DOCS/` | Material de referencia: datasheets, papers, esquemáticos/PCB del medidor y figuras usadas por el documento | — |
| `Circuito de Potencia/` | Circuito de medición INA240A1 + ADS1115 (esquemáticos, PCB, firmware de adquisición) — en preparación | — |
| `TTGO LORA32/` | Documentación y sketches de la LilyGO TTGO LoRa32 (ESP32): guía de programación, OLED, lectura ADS1115 y pruebas de GPIO | — |

La historia de git separa la base de los cambios propios: el **commit inicial** es el
árbol upstream sin modificar de ambos proyectos, y cada commit posterior agrupa un
cambio del TFG. `git log --oneline` muestra exactamente qué se modificó y
`git diff <commit-base> HEAD` da el diff completo del trabajo propio.

## Cambios sobre la base

### 1. Clasificador de instrucciones (`cv32e40p/`)

**Módulo nuevo — `rtl/cv32e40p_insn_classifier.sv`** (v2, categorías por unidad
activa; especificación completa en [`DISENO_CLASIFICADOR_V2.md`](DISENO_CLASIFICADOR_V2.md))
- Clasifica cada instrucción **retirada** según la unidad funcional que activa,
  con **7 contadores de instrucciones + 1 contador de ciclos** (todos de
  64 bits, leídos como **16 CSR en pares LO/HI**).
- Branches: no tomado → ALU_SIMPLE (solo un compare); tomado → CTRL (paga el
  flush/refetch, mismo mecanismo que jal/jalr).
- **Modelo híbrido**: la división (latencia variable 4–32 ciclos según
  operandos) se modela por ciclos de ocupación (DIV_CYC), el resto por
  instrucción: `E = Σ eᵢ·nᵢ + p_div·c_div`.
- **Filtros**: los accesos CSR (`csr_access`) y las instrucciones de sistema
  (`mret/uret/dret/wfi/fence`, evento nuevo en `id_stage`) no se cuentan.

**Mapeo de CSR — `rtl/include/cv32e40p_pkg.sv`** (rango custom RW de modo máquina 0xBC0–0xBCF):

| Par LO/HI | Contador | Cuenta |
|-----------|----------|--------|
| 0xBC0/0xBC1 | ALU_SIMPLE (+ branch no tomado) | instrucciones |
| 0xBC2/0xBC3 | MUL | instrucciones |
| 0xBC4/0xBC5 | MULH | instrucciones |
| 0xBC6/0xBC7 | DIV | instrucciones |
| 0xBC8/0xBC9 | MEM | instrucciones |
| 0xBCA/0xBCB | CTRL (jal/jalr + branch tomado) | instrucciones |
| 0xBCC/0xBCD | FLOAT | instrucciones |
| 0xBCE/0xBCF | DIV_CYC | ciclos del divisor |

Cada contador se reconstruye como `(HI << 32) | LO`.

**Integración:**
- `rtl/cv32e40p_core.sv`: instancia `insn_classifier_i` conectada al pipeline y
  multiplexor de lectura `csr_rdata = cat_csr_hit ? cat_csr_rdata : csr_rdata_cs`.
- `rtl/cv32e40p_decoder.sv`: acepta los 16 CSR custom sin lanzar *illegal instruction*.
- `rtl/cv32e40p_id_stage.sv`: evento `mhpmevent_system` para el filtro de sistema.
- `Bender.yml`, `cv32e40p_manifest.flist`, `src_files.yml`: registran el módulo nuevo
  en el orden de compilación (decoder → classifier → core).

**Verificación — `example_tb/core/clasif_v2/`**: suite XSim con modelo dorado
(clasifica el trace de instrucciones retiradas en software y compara contra
los CSR). Primer PASS 2026-06-11 con DIV_CYC ciclo-exacto. Ver su README.

### 2. Firmware de caracterización (`cv32e40p/firmware/`)

- `firmware/dominated_loops/`: bucles dominados por categoría con 64
  instrucciones objetivo + 2 de control por iteración (~97 % de dominancia).
  La ventana de medición se delimita con un flanco en GPIO8 → GPIO26 de la
  ESP32 y termina en `ebreak`.
  *Pendiente:* reescribir los bucles al esquema v2 (7 categorías, operandos
  variados para división) y al mapeo de 16 CSR.
- `firmware/dominated_loops/frequency_probe.S`: verificación de la frecuencia real del
  core (10 MHz con el bitstream actual).

### 3. Plataforma FPGA Nexys A7-100T (`pulpissimo/target/fpga/pulpissimo-nexys/`)

- `rtl/xilinx_pulpissimo.v`: puerto nuevo `pad_esp32_sync` (señal interna `io_08`,
  antes `led0_o`) como pulso de sincronización hacia la ESP32; corrección de
  `pad_jtag_tdo` de `input` a `inout` (impedía el enganche de OpenOCD).
- `constraints/nexys4DDR.xdc`: `pad_esp32_sync` → pin H4 (PMOD JD1); JTAG por PMOD JA
  (TMS=C17, TDI=D18, TDO=E18, TCK=G17) para adaptador FT232H externo; constraints de
  temporización JTAG (`create_clock` sobre TCK, grupos de reloj asíncronos,
  `set_max_delay` en los caminos CDC del `dmi_jtag`).
- `openocd-ft232h.cfg`: configuración de OpenOCD para el adaptador FT232H.
- `run_batch.tcl`: síntesis no incremental (evita el error Synth 8-6885 al integrar el
  módulo nuevo), limpieza de pads no usados post-síntesis y `BIN_FILE true`.

### 4. Bitstreams (`pulpissimo/bitstream/`)

| Archivo | Contenido |
|---|---|
| `xilinx_pulpissimo_12csr.bit` | Bitstream grabado actualmente en la FPGA: clasificador **v1** (12 CSR) + fix JTAG TDO |

*Pendiente:* re-síntesis con el clasificador v2 (16 CSR) — el RTL de este
árbol ya es v2 y está verificado en simulación.

## Nota de reproducibilidad (Bender)

Este repositorio es el **artefacto de entrega y lectura** del TFG: contiene la base y
los cambios en una historia limpia. El flujo de síntesis oficial de PULPissimo es
Bender-puro y `pulp_soc` fija `cv32e40p` a un commit exacto del upstream, por lo que un
`bender checkout` limpio no consume automáticamente el core de este árbol: el
clasificador debe aplicarse sobre el checkout de Bender (los archivos de `cv32e40p/rtl/`
de este repo son exactamente los que se sintetizaron en el bitstream incluido).
El detalle completo está en [`CAMBIOS_TFG.md`](CAMBIOS_TFG.md).
