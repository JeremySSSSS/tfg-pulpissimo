# esp32_ina228 — firmware del medidor de potencia

Firmware Arduino para el ESP32 que lee el INA228 (tensión de shunt y de bus sobre
el riel de la FPGA), integra la potencia en ventanas y sube cada ventana
(`p_avg`, `duration_ms`, energía) a la pestaña `inbox` de la hoja de cálculo vía
el Web App de Apps Script. El banco (`comun/sheet.py`) aparea cada ventana con la
corrida que la generó usando la duración como guarda.

## Configuración (obligatoria antes de compilar)

Las credenciales viven en `secrets.h`, que **no se versiona**:

```
cp secrets.h.example secrets.h
# editar WIFI_SSID, WIFI_PASS y SCRIPT_URL (misma URL que comun/config_local.py)
```

## Compilar y flashear

```
arduino-cli compile --fqbn esp32:esp32:esp32 .
arduino-cli upload --fqbn esp32:esp32:esp32 -p /dev/ttyUSB0 .
```
