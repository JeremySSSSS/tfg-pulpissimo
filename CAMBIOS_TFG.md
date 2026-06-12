# Cambios del TFG — Clasificador de instrucciones para estimación de consumo

Resumen de las modificaciones realizadas sobre los proyectos base para integrar
un módulo hardware de clasificación de instrucciones en el CV32E40P y exponer sus
contadores por CSR, junto con los ajustes de plataforma en PULPissimo para la
medición sobre la Nexys A7-100T.

Los cambios se reparten en **dos repositorios** (el core es una dependencia que
PULPissimo consume vía Bender):

| Repositorio | Rol | Base |
|---|---|---|
| `JeremySSSSS/tfg-power-clean` | Core CV32E40P + clasificador + firmware | fork de `pulp-platform/cv32e40p` @ `7a49867` |
| `JeremySSSSS/pulpissimo` | SoC, top-level FPGA, constraints, bitstream | fork de `pulp-platform/pulpissimo` |

---

## 1. CV32E40P (`tfg-power-clean`, rama `tfg-clasificador`)

Diff sobre la base upstream `7a49867` (*Bump FPU to pulp-v0.1.3*): **8 archivos**.

### Módulo nuevo — `rtl/cv32e40p_insn_classifier.sv`
- Clasifica cada instrucción **retirada** en 6 categorías: Arithmetic, Logic,
  Memory, Branch, Jump, Floating point.
- **6 contadores de 64 bits**, leídos como **12 CSR** en pares LO/HI.
- Detección por las señales del pipeline en EX: `alu_en` / `alu_operator`
  (arith vs logic), `mult_en`, `data_req` (load/store → memory), `branch`,
  `jump`, `apu_en` (floating point).
- **Filtro de accesos CSR**: el conteo solo ocurre con
  `if (retire_i && !csr_access_i)`, de modo que las propias instrucciones
  `csrr/csrw` de lectura/reset de contadores **no contaminan** la categoría
  Arithmetic (el decoder deja `alu_en=1`, `alu_operator=SLTU` para los CSR).

### Mapeo de CSR — `rtl/include/cv32e40p_pkg.sv`
Rango **custom 0xBC0–0xBCB** (User custom RW del spec RISC-V):

| CSR | Campo | | CSR | Campo |
|------|-----------|---|------|-----------|
| 0xBC0 | ARITH_LO  | | 0xBC6 | BRANCH_LO |
| 0xBC1 | ARITH_HI  | | 0xBC7 | BRANCH_HI |
| 0xBC2 | LOGIC_LO  | | 0xBC8 | JUMP_LO   |
| 0xBC3 | LOGIC_HI  | | 0xBC9 | JUMP_HI   |
| 0xBC4 | MEMORY_LO | | 0xBCA | FLOAT_LO  |
| 0xBC5 | MEMORY_HI | | 0xBCB | FLOAT_HI  |

Cada contador de 64 bits se reconstruye como `(HI << 32) | LO`.

### Integración en el core — `rtl/cv32e40p_core.sv`
- Instancia `insn_classifier_i` con las conexiones a las señales del pipeline
  (`retire`, `load`/`store`, `jump`/`branch`, `alu_en`/`alu_operator`,
  `mult_en`, `apu_en`, `csr_access`).
- Multiplexor de lectura: `csr_rdata = cat_csr_hit ? cat_csr_rdata : csr_rdata_cs`.

### Decoder — `rtl/cv32e40p_decoder.sv`
- Acepta los 12 CSR del clasificador como accesos válidos (sin lanzar
  *illegal instruction*).

### Manifiestos
- `Bender.yml`, `cv32e40p_manifest.flist`, `src_files.yml`: registran el nuevo
  archivo `cv32e40p_insn_classifier.sv` en el orden de compilación
  (decoder → classifier → core).

### Firmware de caracterización — `firmware/dominated_loops/`
- Bucles dominados por categoría (`arith.S`, `logic.S`, `memory.S`, `branch.S`,
  `jump.S`, `float.S`): 64 instrucciones objetivo + 2 de control (`addi`,`bnez`)
  por iteración → ~97 % de dominancia (branch ~100 %).
- Ventana de medición delimitada por flanco de **GPIO8 → GPIO26 (ESP32)**;
  termina en `ebreak`.
- `frequency_probe.S`: confirma la frecuencia real del core (parpadeo de `led1_o`
  → 10 MHz con el bitstream actual).
- `csr_test/`: test mínimo de contadores vía JTAG/GDB (`COMANDOS_JTAG.md`).
  > Pendiente: `csr_test.S` aún usa el mapeo antiguo 0xBC0–0xBC5; falta
  > actualizarlo al esquema LO/HI 0xBC0–0xBCB.

---

## 2. PULPissimo (`JeremySSSSS/pulpissimo`)

Ajustes de plataforma para la FPGA Nexys A7-100T (target `pulpissimo-nexys`).

### Top-level FPGA — `target/fpga/pulpissimo-nexys/rtl/xilinx_pulpissimo.v`
- Nuevo puerto `inout wire pad_esp32_sync` (señal interna `io_08`) como **pulso
  de sincronización hacia la ESP32**, mapeado en `.pad_io`.
- `io_08` se redirige desde `led0_o` (LED onboard inaccesible) hacia un pin de
  PMOD; el LED0 onboard pierde su función.

### Constraints — `target/fpga/pulpissimo-nexys/constraints/nexys4DDR.xdc`
- **JTAG en PMOD JA** (LVCMOS33), para FT232H externo:

  | Señal | Pin | PMOD |
  |-------|-----|------|
  | `pad_jtag_tms` | C17 | JA1 |
  | `pad_jtag_tdi` | D18 | JA2 |
  | `pad_jtag_tdo` | E18 | JA3 |
  | `pad_jtag_tck` | G17 | JA4 |

- **Sync ESP32**: `pad_esp32_sync` → **H4 (PMOD JD1)**.
- Restricciones de temporización JTAG: `create_clock` sobre `tck` (100 ns),
  grupos de reloj asíncronos entre TCK / clk SoC / clk periférico, y
  `set_max_delay` sobre los caminos CDC del `dmi_jtag`.

### Dirección del TDO y debug — commit `34be791`
- `pad_jtag_tdo` corregido de `input` a `inout` (fix de dirección que impedía el
  enganche de OpenOCD).
- Añadida la configuración de OpenOCD para el adaptador **FT232H**.

### Flujo de síntesis — `target/fpga/pulpissimo-nexys/run_batch.tcl`
- Síntesis **no incremental** (`AUTO_INCREMENTAL_CHECKPOINT 0`,
  `INCREMENTAL_MODE off`, `FLATTEN_HIERARCHY none`) para evitar el error
  Synth 8-6885 al integrar el módulo nuevo.
- Limpieza de netlist post-síntesis: se eliminan los pads no usados
  (`bootsel`, `hyper`, `jtag_trst`) y se atan sus nets a constante.
- Bitstream con `BIN_FILE true`.

### Bitstream y setup de debug — commits `73090f4`, `720fb5e`, `b8475de`
- Bitstream de la Nexys A7-100T con los 12 CSR y el fix de JTAG TDO,
  versionado junto con el setup de depuración FPGA.

---

## 3. Nota de integración (Bender) y reproducibilidad

El flujo de síntesis FPGA es **Bender-puro**: el `Makefile` ejecuta
`bender script vivado` para generar `tcl/generated/compile.tcl`, que Vivado lee.

- `pulp_soc` fija `cv32e40p` a un **commit exacto** del upstream (`rev: 7a49867`),
  por lo que Bender 0.27.1 no permite hacer *override* de la fuente desde el
  paquete raíz hacia el fork.
- En consecuencia, en el árbol de trabajo actual el clasificador reside en el
  checkout `.bender/.../cv32e40p` **aplicado a mano** sobre la base upstream.
  Un `bender checkout`/`update` limpio re-clona el upstream y **elimina** el
  módulo; habría que reaplicarlo.
- Caminos para cerrar la reproducibilidad (no aplicados por decisión actual):
  (B) forkear `pulp_soc` apuntando `cv32e40p` → `tfg-power-clean` y hacer
  *override* de `pulp_soc` desde PULPissimo (se pide por versión, sí se puede);
  (C) script post-checkout que copie los archivos del clasificador desde
  `tfg-power-clean` al checkout `.bender`.

El repositorio `tfg-power-clean` conserva el RTL del clasificador con la traza de
fork sobre `pulp-platform/cv32e40p @ 7a49867`, de modo que el código fuente queda
versionado y trazable aunque el flujo Bender aún no lo consuma directamente.
