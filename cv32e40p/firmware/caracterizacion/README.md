# Banco de caracterización y validación energética

Software del banco de medición del TFG: carga programas bare-metal en el CV32E40P
por JTAG, lee los CSR del clasificador, recibe la potencia promedio medida por el
ESP32+INA228 y produce los coeficientes energéticos `e_i` y su validación.

## Punto de entrada

```
python3 gui.py            # interfaz web en http://localhost:8237
python3 gui.py --lan      # accesible desde la red local (teléfono, etc.)
```

La GUI encola trabajos (campañas de caracterización y tandas de validación) y los
ejecuta en serie mostrando la salida en vivo. Todo lo que hace la GUI también se
puede correr por consola con los scripts de abajo.

## Scripts

| Script | Función |
|---|---|
| `caracterizar.py` | Corre una campaña completa de un método y ajusta los coeficientes: `caracterizar.py bucles` (M1) o `caracterizar.py regresion --modelo efimon` (M2; efimon es el modelo oficial del TFG, hay que pedirlo explícito porque el default de la CLI es `clasico`). Cada campaña respalda sus coeficientes en `<metodo>/campanas/coeficientes_<timestamp>.csv`. |
| `verificar.py` | Valida los coeficientes contra las cargas de `benchmarks/`: `verificar.py --metodo 1\|2 <programas...>`. `--pidle archivo` (default) usa la potencia estática de la calibración; `--pidle medir` la mide en el momento (recomendado si la temperatura ambiente cambió). `--repeats N` promedia N tandas. Cada tanda queda en `validaciones/`. |
| `reproducibilidad.py` | Estadística entre campañas: coeficientes por campaña, CV por categoría y estabilidad de la validación. |
| `sweep_termico.py` | Barrido de potencia estática contra temperatura del die (ventilación forzada) — evidencia de la dependencia térmica documentada en el TFG. |
| `pares.py` | Pares diferenciales: mide el costo de una categoría por diferencia entre dos programas casi idénticos, para arbitrar entre M1 y M2. |
| `test_float.py`, `test_xadc/` | Pruebas puntuales de la FPU y del sensor de temperatura. |

## Datos

- `bucles/` (M1) y `regresion/` (M2): fuentes de calibración, ELF, `datos.csv` y
  `coeficientes.csv` oficiales de cada método, con respaldos por campaña en `campanas/`.
- `benchmarks/`: cargas de validación, nunca usadas para calibrar.
- `validaciones/`: una tanda de validación por archivo.
- `verificacion.csv`: historial acumulado de validaciones.
- `pidle_temp.csv`, `pidle_fit.csv`: barrido térmico y su ajuste lineal.
- `archivo/`: datos de corridas antiguas, conservados fuera del flujo activo.

## Requisitos

OpenOCD con el FT232H conectado a la Nexys A7 (config en
`pulpissimo/target/fpga/pulpissimo-nexys/openocd-ft232h.cfg`), el ESP32 midiendo
(ver `esp32_ina228/README.md`) y `comun/config_local.py` con la URL del Apps
Script (ver `comun/README.md`).
