# Diseño del clasificador de instrucciones v2 — categorías por unidad activa

**Estado:** especificación acordada (2026-06-11), pendiente de implementación.
**Sustituye a:** clasificador v1 (6 categorías semánticas: Arithmetic/Logic/Memory/Branch/Jump/Float, CSR 0xBC0–0xBCB), que es el del bitstream actual.
**Referencias de código:** árbol `cv32e40p/` de este repositorio (base `pulp-platform/cv32e40p @ 7a49867`).

---

## 1. Motivación

El modelo de estimación `E = Σ eᵢ·nᵢ` es tanto más preciso cuanto más homogéneo
es el costo energético dentro de cada categoría. La energía de una instrucción
la determina **qué unidad física conmuta y cuánta actividad genera en ella**
(`α·C_eff` de la ecuación de potencia dinámica), no su semántica. El esquema v2
traza las fronteras de categoría donde el RTL del CV32E40P las traza: una
categoría por unidad funcional, separando los casos en que la misma unidad
genera actividad muy distinta (mul vs mulh; branch tomado vs no tomado).

Debilidades del v1 que el v2 corrige:
- La frontera Arithmetic/Logic no la decide el RTL (misma ALU, mismo ciclo) —
  era una división sin base microarquitectónica.
- `mul`, `mulh` y `div` quedaban mezcladas en Arithmetic pese a usar unidades
  y latencias distintas (MAC 1 ciclo, MAC-FSM ~4 ciclos, divisor serial 4–32
  ciclos data-dependent).
- Branch y Jump estaban separadas pese a compartir el mecanismo de costo
  (flush/refetch), y un branch no tomado (solo un compare) se contaba igual
  que uno tomado (que paga el flush).
- `mret/uret/dret/wfi/fence/fence.i` se cuentan como Arithmetic por el default
  del decoder (`alu_en=1`, `ALU_SLTU`, `cv32e40p_decoder.sv:195-196`).

## 2. Categorías

7 contadores de 64 bits. Criterio: **categoría = unidad activa × nivel de
actividad**.

| # | Categoría | Instrucciones (RV32IMFC) | Unidades que conmutan |
|---|-----------|--------------------------|------------------------|
| 1 | ALU_SIMPLE | add/addi/sub, and/or/xor(i), shifts, slt(i)(u), lui/auipc, **branches no tomados** | ALU (sumador/shifter/comparador), 1 ciclo |
| 2 | MUL | mul | Multiplicador MAC32 (`cv32e40p_mult.sv`) → DSP48 en Artix-7. No usa la ALU |
| 3 | MULH | mulh, mulhsu, mulhu | El mismo MAC con FSM de ~4 ciclos (4 multiplicaciones parciales) |
| 4 | DIV | div, divu, rem, remu | Divisor serial (`cv32e40p_alu_div.sv`, dentro de la ALU), 4–32 ciclos **dependiente de operandos**; reutiliza el shifter de la ALU por iteración (`cv32e40p_alu.sv:213`) |
| 5 | MEM | lw/lh(u)/lb(u), sw/sh/sb, flw, fsw | ALU (dirección) + LSU + OBI datos + **TCDM/SRAM del SoC** (mayor consumidor fuera del core) |
| 6 | CTRL | jal, jalr, **branches tomados** | ALU (destino/comparación) + flush de pipeline + refetch (OBI instrucciones + SRAM de programa) |
| 7 | FLOAT | fadd.s/fmul.s/fdiv.s/… | Interfaz APU + FPU (fpnew) + regfile FP |

**No contadas** (no suman a ningún contador):
- `csrr/csrw/csrs/csrc` — filtro por `csr_access_ex` (ya existe en v1).
- `ecall`, `ebreak` — el hardware ya las excluye de `minstret`
  (`cv32e40p_id_stage.sv:1613`).
- `mret/uret/dret/wfi/fence/fence.i` — filtro nuevo por evento `system`.

**Invariante verificable en simulación:**
`Σ nᵢ + n_csr + n_system = minstret`.

**Cascada de prioridad** (una instrucción puede encender varias señales; gana
la unidad dominante en energía):

```
MEM → CTRL/branch → FLOAT → DIV → MULH → MUL → ALU_SIMPLE
```

Ejemplos que la requieren: `lw` también enciende la ALU (dirección con
ALU_ADD); `jal` también usa la ALU; `flw` enciende APU-path y data_req (va a
MEM, no a FLOAT).

## 3. Mapa de señales (verificado en el RTL, 2026-06-11)

### Modelo de timing

Los eventos `mhpmevent_*` se generan en ID y se flopean un ciclo
(`cv32e40p_id_stage.sv:1633-1640`): pulsan en el ciclo en que la instrucción
está en EX, **alineados** con los registros de pipeline `*_ex` (`alu_en_ex`,
`alu_operator_ex`, `mult_en_ex`, `mult_operator_ex`, `apu_en_ex`,
`csr_access_ex`). `mhpmevent_minstret` pulsa **una vez por instrucción**
aunque esta pase varios ciclos en EX (mulh, div) → se cuentan instrucciones,
no ciclos.

Excepción: `mhpmevent_branch_taken` pulsa **un ciclo después** del evento
branch (`id_stage:1640`: `branch_o && branch_decision_i`, la decisión sale de
EX). Ya viene calificado por `minstret` aguas arriba: se suma con su propio
pulso, **sin** re-gatear con `retire_i`.

### Condiciones de detección

| Categoría | Condición exacta | Fuente |
|---|---|---|
| MEM | `load_i \|\| store_i` | `mhpmevent_load/store` (`id_stage:1634-1635`); flw/fsw activan `data_req` (`decoder:1930+`, con FPU=1) |
| CTRL | `jump_i \|\| branch_taken_i` | `mhpmevent_jump` (`id_stage:1636`), `mhpmevent_branch_taken` (`id_stage:1640`) |
| FLOAT | `apu_en_i` | `apu_en_ex` (`core:205`, ya cableada en v1) |
| DIV | `alu_en_i && alu_operator_i ∈ {ALU_DIV, ALU_DIVU, ALU_REM, ALU_REMU}` | operadores en `pkg:157-160` |
| MULH | `mult_en_i && mult_operator_i == MUL_H` | `decoder:1137-1154` (las tres mulh* → MUL_H) |
| MUL | `mult_en_i && mult_operator_i == MUL_MAC32` | `decoder:1128-1129` |
| ALU_SIMPLE | `alu_en_i` && no-div && ninguna categoría anterior, **+ not-taken** | ver derivación abajo |
| (filtro) | `!csr_access_i && !system_i` en las ramas gateadas por retire | `csr_access_ex` + evento `system` nuevo |

**Derivación de branch no tomado** (dentro del clasificador):

```systemverilog
// branch_i pulsa en EX; branch_taken_i pulsa un ciclo después si fue tomado
branch_q1     <= branch_i;                    // flop interno
not_taken     =  branch_q1 && !branch_taken_i; // pulso alineado con taken
```

`not_taken` suma a ALU_SIMPLE; `branch_taken_i` suma a CTRL. El conteo total
es exacto; solo el instante del incremento se corre un ciclo (irrelevante: los
CSR se leen muchos ciclos después).

## 4. Mapa de CSR

14 CSR en 0xBC0–0xBCD (custom RW de modo máquina: bits [9:8]=11, [11:10]=10).

| Par | LO | HI | Contador | Cuenta |
|-----|----|----|----------|--------|
| 1 | 0xBC0 | 0xBC1 | ALU_SIMPLE | instrucciones |
| 2 | 0xBC2 | 0xBC3 | MUL | instrucciones |
| 3 | 0xBC4 | 0xBC5 | MULH | instrucciones |
| 4 | 0xBC6 | 0xBC7 | DIV | instrucciones |
| 5 | 0xBC8 | 0xBC9 | MEM | instrucciones |
| 6 | 0xBCA | 0xBCB | CTRL | instrucciones |
| 7 | 0xBCC | 0xBCD | FLOAT | instrucciones |
| 8 | 0xBCE | 0xBCF | DIV_CYC | **ciclos** de ocupación del divisor |

El rango 0xBC0–0xBCF queda completo: 8 contadores de 64 bits, 16 CSR.

Lectura: `(HI << 32) | LO`. Escritura de 0 en ambos resetea el contador.
Semántica de acceso idéntica al v1 (lectura por multiplexor en el core,
escritura directa; csrrs/csrrc con rs1≠x0 sobre estos CSR no soportado, igual
que v1).

## 4b. Manejo de instrucciones multiciclo

**Mecánica de conteo:** `mhpmevent_minstret` pulsa una sola vez por
instrucción (cuando ID la valida); durante una EX multiciclo el pipeline está
stalleado y nada más retira. Una `div` de 32 ciclos = un incremento en DIV.
No requiere lógica adicional.

**Semántica del modelo:** la energía de los ciclos extra queda dentro del
coeficiente: `eᵢ = P̄·T/nᵢ` y `T` contiene todos los ciclos del bucle de
caracterización (p. ej. `e_mulh ≈ 4·e_mul` sale solo de la medición). El
problema real es la **varianza de ciclos dentro de la categoría**:

| Categoría | Ciclos | Varianza intra-categoría |
|---|---|---|
| MULH | ~4 fijos | Ninguna |
| MEM | 1 (TCDM) | Ninguna |
| CTRL | flush fijo | Ninguna |
| DIV | 4–32 según operandos | Alta → tratamiento abajo |
| FLOAT | heterogénea por op (fadd corta, fdiv/fsqrt largas) | Media → tratamiento abajo |

Tratamiento (**modelo híbrido, decisión 2026-06-11**): *latencia constante →
contar instrucciones; latencia variable por datos → contar ciclos de
ocupación de la unidad.*

1. **DIV — contador de ciclos dedicado (DIV_CYC):** además del contador de
   instrucciones, un 8.º contador acumula 1 **cada ciclo** en que EX está
   ocupado por una división (`alu_en_i && alu_operator_i ∈ {DIV,DIVU,REM,REMU}`,
   sin gatear por retire). Funciona sin señales nuevas porque los registros
   ID/EX retienen el operador durante todo el stall multiciclo
   (`id_stage:1472-1573`: solo cargan con `ex_ready`). El modelo pasa a:

   `E = Σ eᵢ·nᵢ (6 categorías de latencia fija) + p_div·c_div`

   donde `p_div` = energía por ciclo de división (casi constante: cada
   iteración del divisor serial hace el mismo shift+resta) y `c_div` el valor
   de DIV_CYC. La caracterización `p_div = P̄·T/c_div` es más robusta que la
   versión por instrucción (independiente de los operandos del bucle de
   calibración). `n_div` se sigue contando: sirve para el invariante, y
   `c_div/n_div` reporta la latencia promedio observada.
   La caracterización con operandos de latencia mín/máx/aleatoria se mantiene
   como **validación de que p_div es constante** (los tres deben dar el mismo
   p_div dentro del ruido).

   Uso en el modelo: `n_div` no lleva coeficiente (sirve para el invariante y
   para reportar `c_div/n_div` = latencia promedio observada). En el método de
   regresión (M2), la columna de división de la matriz de conteos lleva
   **c_div en vez de n_div**; las incógnitas son los 6 eᵢ por instrucción +
   p_div. Para comparar con la literatura por instrucción (Tiwari/Fang):
   `e_div_efectivo = p_div·(c_div/n_div)`, aclarando que depende de la carga.
   Ventaja de caracterización: en el bucle dominado de división la dominancia
   **en ciclos** supera el 99 % (cada div ≈ 25 ciclos vs 1 de las auxiliares),
   mejor que la dominancia por instrucciones de las demás categorías.

   Nota de implementación: las burbujas del pipeline cargan los regs ID/EX
   con `alu_en=1, ALU_SLTU` (`id_stage:1593-1597`) — no contaminan DIV_CYC
   (SLTU ∉ ops de división) ni los contadores de instrucciones (las burbujas
   no retiran). Esto descarta de paso generalizar el conteo por ciclos a las
   demás categorías sin un calificador de validez adicional.
2. **FLOAT:** caracterizar con mezcla representativa de operaciones y
   documentar que el coeficiente refleja esa mezcla.
3. **Stalls entre instrucciones** (load-use, jr-stall): su energía cae en
   `P̄·T` y se reparte en los coeficientes de la ventana; en bucles dominados
   los stalls propios de la categoría quedan dentro de su `eᵢ`. Los efectos
   cruzados en cargas mixtas son el supuesto de independencia de contexto ya
   declarado en el marco teórico (§2.2.1).
4. **Alternativa descartada — ciclos para TODAS las categorías:** cambia la
   clase de modelo respecto a Tiwari/Fang, duplica el hardware y además las
   burbujas (alu_en=1/SLTU) exigirían calificadores de validez por categoría.
   El híbrido (ciclos solo donde la latencia es variable) captura casi todo
   el beneficio a una fracción del costo. Si FLOAT resulta relevante en la
   caracterización (FPU presente y fdiv/fsqrt frecuentes), se evalúa un
   contador FPU_CYC análogo con el handshake del APU — decisión diferida.

## 5. Cambios de RTL requeridos

| Archivo | Cambio |
|---|---|
| `rtl/cv32e40p_id_stage.sv` | Nuevo evento flopeado junto a los demás: `mhpmevent_system_o <= minstret && (mret_insn_dec \|\| uret_insn_dec \|\| dret_insn_dec \|\| wfi_insn_dec \|\| fencei_insn_dec)`. Las señales `*_dec` ya existen (l.964-977). +1 puerto |
| `rtl/cv32e40p_core.sv` | Cablear al clasificador: `mult_operator_ex` (l.183), `mhpmevent_branch_taken` (l.336), `mhpmevent_system` (nuevo). Actualizar instancia (l.1040+) |
| `rtl/cv32e40p_insn_classifier.sv` | Reescritura: 7 contadores de instrucciones + DIV_CYC (suma cada ciclo con operador DIV, sin retire), condiciones de §3, flop `branch_q1`, filtro `!csr_access_i && !system_i`, mux de lectura de 16 CSR |
| `rtl/include/cv32e40p_pkg.sv` | 16 direcciones CSR (0xBC0–0xBCF) en `csr_num_e` |
| `rtl/cv32e40p_decoder.sv` | Aceptar los 4 CSR nuevos (0xBCC–0xBCF) como accesos válidos |

**No se tocan:** ALU, multiplicador, divisor, LSU, cs_registers.
`fence` y `fence.i` comparten `fencei_insn_o` (`decoder:2601-2611`) — una sola
señal cubre ambas.

## 6. Riesgos y verificaciones previas

1. **FPU**: confirmar `FPU=1` en la build de pulp_soc antes de implementar.
   Si la build no instancia FPU, `apu_en_ex` es 0 estructural y FLOAT siempre
   cuenta 0 (decidir: reportar "no aplicable" o retirar la categoría).
2. **MUL_MAC32 compartido**: `p.mac/p.msu` de Xpulp usan el mismo operador que
   `mul`. Compilando bare-metal RV32IMC el compilador no las emite; documentar
   como supuesto del flujo.
3. **Latencia de div dependiente de datos**: `e_div` es un promedio sobre la
   distribución de operandos del bucle de caracterización → caracterizar con
   operandos variados y documentar como limitación del modelo por instrucción
   (contar ciclos por categoría queda como trabajo futuro).

## 7. Plan de verificación (suite v2, posterior a la implementación)

Suite auto-verificable basada en **modelo dorado**:
1. El testbench corre un programa y al final vuelca los 14 CSR.
2. Un script parsea el trace de instrucciones retiradas del CV32E40P
   (tracer en `bhv/`), clasifica cada instrucción en software con las reglas
   de §2/§3 y calcula los conteos esperados.
3. PASS si CSR == golden para los 7 contadores de instrucciones y se cumple
   el invariante `Σ nᵢ + n_csr + n_system = minstret`.
4. **DIV_CYC**: validación con divisiones dirigidas de operandos conocidos
   (la latencia del divisor es función de los operandos) → `c_div` esperado
   exacto por test; sanity general: `lat_min·n_div ≤ c_div ≤ lat_max·n_div`.

Casos a cubrir: bucles dominados por cada categoría (7), branches
tomados/no-tomados mezclados, div con operandos extremos (latencia mín/máx),
mulh aislada, accesos CSR intercalados (filtro), instrucciones de sistema
(mret/wfi/fence), cargas mixtas y secuencias aleatorias.

## 8. Impacto en el resto del proyecto

- **Firmware**: 7 bucles dominados (los nuevos: mul, mulh, div — cadenas de la
  misma instrucción; en div, variar operandos). Actualizar `csr_test` y
  `COMANDOS_JTAG.md` al mapeo de 14 CSR.
- **Caracterización**: 7 coeficientes iniciales. Pliegues posibles según
  evidencia (si `e_mul ≈ e_alu` o `e_mulh` despreciable, el modelo final
  reporta 6 o 5 categorías; el pliegue se reporta como resultado medido).
- **Documento de tesis**: §"Definición de categorías por firma de energía" de
  `Documento TFG/implementacion.tex` se redacta desde este diseño.
- **Predicción falsable para el análisis**: MEM y CTRL deberían dar los
  coeficientes más altos (su energía sale del core hacia la SRAM del SoC).
- **Bitstream**: el actual (v1) sigue siendo válido para lo ya medido; el v2
  requiere re-síntesis.

## 9. Caracterización en banco: potencia → energía (pendiente de redactar)

> Nota guardada 2026-06-12 para el marco teórico / resultados del Documento TFG.
> Captura la conclusión de la discusión sobre las mediciones físicas del v1.

**La trampa: potencia ≠ energía.** El circuito (INA240→ADS1115→ESP32) mide
**potencia** `P̄` (W = J/s). El modelo necesita **energía por instrucción**
`eᵢ` (J). Comparar potencia cruda entre bucles **engaña**.

**Evidencia empírica (v1, bucles dominados):** el bucle de `arith` midió
**más potencia** que el de `float`. Físicamente parece al revés, pero es
correcto: `float.S` es una cadena de dependencias serial y la FPU tiene
latencia (apu_lat=2 para FP32, `C_LAT_FP32='d1`) → el core stallea ~3 ciclos
por op → IPC≈0.34 vs arith IPC≈0.97. Float retira instrucciones ~3× más lento,
así que mete **menos conmutación por segundo** → **menos potencia**, aunque
cada `fadd` cueste **más energía**.

**La corrección — normalizar por tiempo (CPI/IPC):**

```
        ΔP            ΔP · T
eᵢ = ──────────  =  ──────────       T = ciclos / f_clk = (s2−s1)/f_clk
     IPC · f_clk        N
```

- `ΔP = P̄_loop − P̄_idle` → ESP32
- `T` (ciclos) → `mcycle` (`s1`/`s2` ya capturados en los `.S`)
- `N` → contador de categoría (o LOOP_COUNT×64)

El IPC bajo de float **amplifica** su `eᵢ`: aunque tenga menos potencia, sale
más caro por instrucción. Consistencia que cierra el modelo: al reconstruir
potencia `P̄ = E/T = (Σeᵢnᵢ)/T`, un programa con muchos floats da **energía
alta pero potencia baja** (más energía repartida en más tiempo) — reproduce la
medición. Lo que vacía la batería es la energía, no la potencia: esto justifica
medir con un clasificador de instrucciones y no con un multímetro instantáneo.

**Ambos métodos de caracterización necesitan el tiempo (ciclos):**
- *Bucles dominados (M1):* IPC **explícito**, una categoría por corrida.
- *Regresión (M2):* IPC **implícito** — cada `Eₖ = P̄ₖ·Tₖ` lleva el tiempo
  adentro; se resuelven todos los `eᵢ` (+ `p_div`) de cargas mixtas. Más robusta
  (no depende de dominancia perfecta, admite término de base/leakage). **Error a
  evitar:** regresar contra potencia y conteos directos (`P̄ = Σeᵢnᵢ`) cae en la
  misma trampa; debe ser **energía** (o potencia contra *tasas* `nᵢ/T`).

**Referencias (verificar año/páginas antes de entregar):**
- Tiwari, Malik, Wolfe (1994), *Power Analysis of Embedded Software…*, IEEE
  Trans. VLSI Syst. 2(4):437-445 — modelo `E = Σ eᵢ·nᵢ` (base del clasificador).
- Tiwari et al. (1996), *Instruction Level Power Analysis…*, J. VLSI Sig. Proc.
  13:223-238.
- Hennessy & Patterson, *Computer Architecture: A Quantitative Approach* —
  definiciones `E = P·t`, `t = ciclos/f`, **CPI** (= 1/IPC). La literatura usa
  CPI; conviene redactar en CPI para alinear.
- Isci & Martonosi (2003), *Runtime Power Monitoring in High-End Processors*,
  MICRO-36 — potencia desde contadores de HW (justifica fase 2).
- Contreras & Martonosi (2005), *Power Prediction for Intel XScale… PMU Events*,
  ISLPED — regresión lineal sobre eventos de contador.
- Bircher & John, *Complete System Power Estimation Using Processor Performance
  Events*, IEEE Trans. Computers — modelos de regresión con contadores.
