# TFG — Módulo hardware de clasificación de instrucciones para estimación de consumo energético en RISC-V

**Estudiante:** Jeremy Jesús Soto Chacón · Ingeniería Electrónica, Instituto Tecnológico de Costa Rica
**Plataforma:** CV32E40P (RV32IMFC) sobre PULPissimo, FPGA Digilent Nexys A7-100T (Artix-7)

## Descripción

Este repositorio contiene el RTL, la plataforma FPGA, el firmware y el software de
caracterización del Trabajo Final de Graduación: un **módulo hardware de clasificación
de instrucciones** integrado en el pipeline del core CV32E40P. El módulo cuenta, en
tiempo real y sin instrumentar el software, cuántas instrucciones retiradas pertenecen
a cada una de **7 categorías definidas por unidad funcional activa** (`alu`, `mul`,
`mulh`, `div`, `mem`, `ctrl`, `float`), más un contador de ciclos de ocupación del
divisor, y expone los conteos mediante **16 CSR custom (0xBC0–0xBCF)**.

Con esos conteos `n_i` y coeficientes energéticos `e_i` (nJ por instrucción) obtenidos
por caracterización eléctrica directa, se estima la energía de una aplicación bare-metal:

```
E_est = P_estatica·T + Σ e_i·n_i
```

La caracterización se hace midiendo la corriente del riel de la FPGA con un **INA228**
leído por un **ESP32**, que sube las ventanas de potencia promedio a una hoja de
cálculo vía Apps Script. Dos métodos independientes producen los coeficientes:

- **M1 (bucles dominados):** microbenchmarks donde una categoría domina el retiro;
  el coeficiente se despeja directamente.
- **M2 (regresión):** 15 programas de calibración a tres intensidades (duty 100/60/30 %)
  y ajuste por mínimos cuadrados no negativos con intercepto (estilo EfiMon).

**Resultado:** validando contra 14 cargas no vistas durante la calibración, el error
relativo medio absoluto es **0,15 % (M1)** y **0,22 % (M2)**, con máximos < 0,7 % —
muy por debajo de la meta de 10 % de la hipótesis.

## Estructura

| Directorio | Contenido |
|---|---|
| `cv32e40p/` | Core con el clasificador integrado (ver `cv32e40p/README_TFG.md`) |
| `cv32e40p/rtl/cv32e40p_insn_classifier.sv` | El módulo clasificador (v2) |
| `cv32e40p/firmware/caracterizacion/` | Banco de caracterización y validación completo |
| `pulpissimo/` | Plataforma SoC con las modificaciones para la Nexys A7 (ver `pulpissimo/README_TFG.md`) |
| `Anteproyecto/`, `Documento TFG/` | Documentos académicos (LaTeX) |
| `Circuito de Potencia/` | PCB del sensado de corriente |

## Reproducir

1. Bitstream: `pulpissimo/bitstream/xilinx_pulpissimo_xadc.bit` (o regenerar con
   `pulpissimo/target/fpga/pulpissimo-nexys/run_batch.tcl`).
2. Configurar credenciales locales: ver `cv32e40p/firmware/caracterizacion/comun/README.md`
   y `esp32_ina228/README.md` (plantillas `.example`, no versionadas las reales).
3. Correr el banco: `python3 cv32e40p/firmware/caracterizacion/gui.py` y abrir
   `http://localhost:8237`, o usar los scripts por consola (`caracterizar.py`,
   `verificar.py`).

Base upstream: `pulp-platform/pulpissimo @ bfc3d9a` + `pulp-platform/cv32e40p @ 7a49867`.
