# comun — módulos compartidos del banco

- `jtag.py` — carga y ejecución de ELF en el CV32E40P vía OpenOCD (FT232H):
  arranca el programa, espera el retiro, lee los CSR del clasificador (0xBC0–0xBCF)
  y calcula la duración esperada de la ventana de medición para la guarda de
  apareamiento con el ESP32.
- `sheet.py` — I/O con la hoja de cálculo a través del Web App de Apps Script.
  `Inbox.get_pavg()` espera la ventana de potencia que sube el ESP32 y descarta
  filas viejas cuya duración no calza con la esperada (evita desalinear la tanda).
- `modelo.py` — el modelo de estimación: `E = P_estatica·T + Σ e_i·n_i`, lectura
  y escritura de `coeficientes.csv`.
- `pulp_temp.h` — lectura de la temperatura del die (XADC) desde el firmware.

## Configuración local (obligatoria)

`config_local.py` contiene la URL real del Web App y **no se versiona**. Para
configurar el banco en una máquina nueva:

```
cp config_local.py.example config_local.py
# editar SCRIPT_URL con la URL /exec del deployment propio de Apps Script
```
