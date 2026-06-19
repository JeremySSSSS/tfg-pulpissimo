# Firmware ESP32 (medición de potencia)

El ESP32 lee la corriente de la placa (shunt 50 mΩ → INA240 G=20 → ADS1115,
PGA ±2.048 V) y sube el resultado a un Google Sheet por WiFi. Dos sketches según
la etapa:

| sketch | cuándo | qué hace |
|--------|--------|----------|
| `chopper_read/` | **caracterización** (`run_chopper.py`) | bina la potencia por estado del GPIO19 y sube `delta = P(alto) − P(bajo)` |
| `ads1115_read/` | **validación** (`validar_chopper.py --run`) | sube el `P_avg` absoluto de la ventana de medición |

## Flashear
```bash
arduino-cli compile --fqbn esp32:esp32:esp32 --upload -p /dev/ttyACM0 esp/chopper_read
arduino-cli compile --fqbn esp32:esp32:esp32 --upload -p /dev/ttyACM0 esp/ads1115_read
```
Puerto `/dev/ttyACM0`, 115200 baud. **Acordate de flashear el correcto antes de
cada etapa** (chopper_read para caracterizar, ads1115_read para validar).
