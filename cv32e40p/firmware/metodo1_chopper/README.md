# Método 1 — caracterización por CHOPEO (medición diferencial)

Mide la **potencia dinámica por categoría de instrucción** del CV32E40P, en
físico, sobre la placa real, sin modificarla. Es el Método 1 definitivo del TFG.

## Estructura
```
fuentes/      # un .S auto-contenido por categoría (referencia wfi) + Makefile -> ../elf
elf/          # los .elf de categoría (salida del build)
benchmarks/   # kernels C reales (sha256/primes/conv) + harness.S + Makefile, para validar
scripts/      # pipeline de medición y modelo, TODO data-driven (lee CSVs, nada hardcodeado)
esp/          # firmware ESP32: chopper_read/ (caracterizar) y ads1115_read/ (validar)
```

### Datos (en `scripts/`, todos trazables a su fuente)
| CSV | qué tiene | fuente |
|-----|-----------|--------|
| `chopper_results.csv` | delta_i [W] y P_idle por corrida (caracterización vigente, wfi) | `run_chopper.py` |
| `chopper_historico.csv` | crudo NOP + wfi | justifica el cambio de referencia |
| `cpi_categorias.csv` | CPI_i = ciclos/instr de los bucles dominados | `../../metodo1/runs_m1.csv` |
| `sim_potencia.csv` | potencia dinámica del core aislado @10 MHz | `power_sim/power_*.rpt` |
| **`coeficientes.csv`** | **e_dyn_i / p_div / P_idle del modelo** | **`run_chopper.py` (vía `modelo.py`)** |
| `validacion.csv` | P_med vs P_pred de los benchmarks | `validar_chopper.py --run` |

`modelo.py` calcula los coeficientes (`e_dyn_i = delta_i·CPI_i/f`, `p_div = delta_div/f`) — lo comparten
`run_chopper.py` (los genera al caracterizar) y `validar_chopper.py` (predice). `recuperar_datos.py`
regenera `cpi_categorias.csv`, `sim_potencia.csv` y separa el histórico desde sus fuentes.

## Cómo se usa
```bash
# 1. compilar
cd fuentes && make            # -> ../elf/*.elf
cd ../benchmarks && make      # -> sha256/primes/conv.elf

# 2. caracterizar (ESP32 con chopper_read.ino, OpenOCD en :3333)
cd ../scripts
python3 run_chopper.py --repeats 2 alu mul mulh div mem ctrl float   # -> chopper_results.csv

# 3. validar el modelo con programas reales (ESP32 con ads1115_read.ino)
python3 validar_chopper.py --run sha256 primes conv                  # -> validacion.csv
python3 validar_chopper.py                                           # coeficientes + tablas
```

---

# Justificación del método (los 6 pilares)

### 1. El problema
A 10 MHz la potencia **dinámica** por categoría (~10 mW) está enterrada bajo la
potencia total de la placa (~5 W, mayormente estática) y bajo la **deriva
térmica** (~10–15 mW en minutos). La medición absoluta (bucles dominados, restar
P_cat − P_idle medidos con minutos de diferencia) no la resuelve: la deriva
arruina la resta.

### 2. Principio del chopper (lock-in)
Se alterna **rápido** (~0.3 s) entre la categoría (GPIO alto) y una referencia
(GPIO bajo), CHOP_PAIRS=500 veces. El ESP32 bina la potencia por estado del GPIO:
```
delta = promedio_alto − promedio_bajo = dinámica de la categoría
```
Como las fases adyacentes están a <1 s, la deriva (lenta) se cancela en la resta.
El ruido por par baja como 1/√N pares → señal de ~10 mW resoluble.

### 3. Evolución de la referencia: NOP → wfi
- **Referencia NOP** (bucle de NOPs, IPC~1): todo el pipeline conmuta cada ciclo,
  así que las categorías que **stallean** (div IPC~0.04, mulh multi-ciclo) conmutan
  MENOS que la referencia → **delta negativo** (ver `chopper_historico.csv`).
- **Referencia wfi** (core dormido, clock-gated): conmutación ~0 = estática real.
  Arma el FC timer (evento 10) para ~0.3 s y ejecuta `wfi`; el timer (dominio de
  periférico) despierta al core. `mie[10]=1`, `mstatus.MIE=0` → despierta sin tomar
  trap. Con esto div/mulh pasan a **positivos** y todo queda contra el mismo cero.

### 4. Validación cruzada con simulación
El orden y la magnitud por categoría coinciden con la simulación de potencia del
core aislado (OOC synth + SAIF + `report_power` @10 MHz) → confirmación
independiente (físico + digital). `validar_chopper.py` imprime la tabla.
El chopper sale por encima de la sim porque mide TODA la placa (core + memoria +
interconexión), no solo el core; la brecha crece con el IPC.

### 5. Validación end-to-end
Los coeficientes del chopper, en el modelo `E = P_idle·T + Σ e_dyn_i·n_i + p_div·c_div`,
predicen la **potencia total** de programas reales held-out (sha256, primes, conv)
con error <0.1%, medidos en la misma sesión. (El modelo estima el TOTAL; usa el
P_idle de la caracterización. El término de tiempo lo hace robusto al IPC.)

### 6. Limitación honesta
La cadena INA240 (alimentado a 3.3 V) satura su salida a ~1.55 A; la categoría de
más corriente (alu) puede quedar subestimada (piso). Se resuelve con el INA228
(mide el shunt directo, sin amplificador). El dinámico por categoría a 10 MHz es
chico (~10 mW): el modelo predice bien el total porque la estática domina, y el
reparto dinámico tiene su límite de precisión.

> Referencia NOP (reproducir el pilar 3): reemplazar la fase idle por
> `li s1, 3000 ; 1: .rept 1000 ; nop ; .endr ; addi s1,s1,-1 ; bnez s1,1b`.
