# Avances TFG — Estimación de consumo por categoría de instrucción (CV32E40P / PULPissimo / Nexys A7)

## 1. Estado general
- **Clasificador de instrucciones en HW** (7 categorías + DIV_CYC, CSR 0xBC0–0xBCF): funcionando, contadores exactos.
- **3 métodos de caracterización** de los coeficientes de energía por categoría, validados.
- **Sensor de temperatura del die (XADC) integrado** y leíble desde firmware.
- **Cadena de medición** depurada (varios bugs encontrados y resueltos).

---

## 2. Coeficientes por categoría — 3 métodos independientes
Potencia dinámica de cada categoría (mW si corriera a IPC=1, @10 MHz):

| categoría | M1 (bucles aislados) | M2 (chopper diferencial) | M3 (regresión EfiMon) |
|---|---|---|---|
| alu | 20.5 | 19.2 | 19.1 |
| mul | 13.2 | 9.0 | 7.6 |
| mulh | 35.5 | 23.9 | 63.0 |
| div | 5.3 | 3.3 | 3.7 |
| mem | 22.3 | 17.6 | 26.4 |
| ctrl | 24.4 | 17.1 | 62.0 |
| float | 26.8 | 20.1 | 30.6 |

**Lectura:** alu/mem/float **coinciden entre los 3 métodos** (coeficientes confiables).
mul/mulh/div/ctrl divergen en M3 por **colinealidad** (en código real vienen siempre
juntos → la regresión no los separa). M1 (aísla cada categoría) y M2 (diferencial)
dan los valores de referencia.

---

## 3. Validación del modelo — held-out (<10% es la hipótesis del TFG)
Verificación de M3 sobre programas **no usados en la calibración** (misma sesión térmica):

| programa | P_med [W] | P_pred [W] | err % | P_din predicho | delta medido | temp |
|---|---|---|---|---|---|---|
| sha256 | 9.1313 | 9.1315 | +0.00 | 18.1 mW | 17.8 mW | 41.3 °C |
| md5 | 9.1306 | 9.1310 | +0.00 | 17.6 mW | 17.1 mW | 41.3 °C |
| floyd | 9.1281 | 9.1310 | +0.03 | 17.6 mW | 14.6 mW | 41.3 °C |
| primes | 9.1213 | 9.1202 | −0.01 | 6.7 mW | 7.8 mW | 41.0 °C |

- **Error total medio < 0.1 %** (vs objetivo de hipótesis < 10 %).
- **Métrica honesta (P_din vs delta medido):** el modelo predice la potencia
  **dinámica** de cada programa dentro de **±1–3 mW** — no es solo el piso.

---

## 4. Sensor de temperatura on-chip (XADC) — integrado y validado
- Mide la **temperatura del die** del FPGA, leíble por firmware (GPIO), **sin circuito externo**.
- Validado contra Vivado SYSMON: **XADC 38.9 °C vs SYSMON 40.5 °C** (dentro de ±4 °C del sensor).
- Permite **demostrar** (no asumir) que la FPGA opera en equilibrio térmico estable
  (~40 °C) → justifica P_idle fijo dentro de una sesión.
- Confirmado: P_idle sube con la temperatura durante el warm-up (leakage).

---

## 5. Hallazgos clave (contribución metodológica)
1. **Potencia sigue al IPC (throughput), no a la energía por instrucción** (corr +0.92).
   Los programas que stallean el pipeline (div) consumen menos → demuestra potencia ≠ energía.
2. **Floor-limited a 10 MHz:** la dinámica es ~0.1 % del piso → la medición diferencial
   (chopper, M2) es la robusta; los métodos absolutos sufren.
3. **Bugs de medición encontrados y resueltos:**
   - JTAG a 1 MHz inflaba el contador de ciclos 10–74× → bajado a 200 kHz + detector de corrida limpia.
   - Un kernel en assembly pisaba un registro del harness → corregido (guardar en memoria).
   - **Junta del shunt floja** (confirmado físicamente: se toca y cambia la lectura) →
     causa la deriva del baseline entre sesiones → **migración al INA228** (shunt integrado).

---

## 6. Próximos pasos
- Migrar el front-end de medición al **INA228** (shunt 15 mΩ integrado, 6× resolución,
  acumulador de energía) → elimina la deriva del shunt y mejora la señal dinámica.
- Re-caracterizar con la cadena limpia y redactar resultados.
