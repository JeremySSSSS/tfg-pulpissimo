# LilyGo TTGO LoRa32 V2.1 (T3 v1.6) — Notas de hardware y flasheo

Documentación de la placa del proyecto, con la configuración verificada el 2026-06-09.

## Identificación

| Dato | Valor |
|---|---|
| Placa | LilyGo TTGO LoRa32 V2.1 (T3 v1.6), 433/868/915 MHz |
| MCU | ESP32-PICO-D4 rev 1.1, 2 cores |
| Flash | 4 MB |
| PSRAM | ninguna |
| USB-serial | CH9102 (`1a86:55d4`) → `/dev/ttyACM0` |
| Pantalla | OLED SSD1306 0.96", 128×64, monocromo, I²C |

> El usuario está en el grupo `dialout`, así que flashea sin `sudo`.

## Pinout del OLED (SSD1306)

| Señal | GPIO |
|---|---|
| Dirección I²C | `0x3C` |
| SDA | **21** |
| SCL | **22** |
| Reset | **ninguno** → pasar `-1` en el constructor |

## ⚠️ Pines PROHIBIDOS: GPIO16 y GPIO17

En el **ESP32-PICO-D4** los pines **GPIO16 y GPIO17 están cableados a la flash
embebida** del encapsulado. Configurarlos con `pinMode()` **reinicia el chip**
(boot loop con `rst:0x8 TG1WDT_SYS_RESET`). NO usarlos para nada.

Por esto el pinout "clásico" de la TTGO T-Display (que usa DC=16) NO sirve aquí:
esta placa **no es una T-Display** y su pantalla es OLED I²C, no ST7789 SPI.

## Flasheo con arduino-cli

```bash
export PATH=$HOME/bin:$PATH          # arduino-cli vive en ~/bin
FQBN=esp32:esp32:esp32
SKETCH=~/pulp/esp32_hola

arduino-cli compile --fqbn $FQBN $SKETCH
arduino-cli upload  --fqbn $FQBN -p /dev/ttyACM0 $SKETCH
```

- Core: `esp32:esp32` 3.3.10
- Librerías de pantalla: **Adafruit SSD1306** + **Adafruit GFX**

## Leer el serial de forma fiable

El `arduino-cli monitor` resultó errático. Usar pyserial forzando el reset por DTR/RTS:

```python
import serial, time
s = serial.Serial("/dev/ttyACM0", 115200, timeout=0.2)
s.setDTR(False); s.setRTS(True); time.sleep(0.2); s.setRTS(False)  # reset EN
t0 = time.time(); buf = b""
while time.time() - t0 < 8:
    buf += s.read(256)
print(buf.decode("utf-8", "replace"))
s.close()
```

## Sketch mínimo "Hola" (referencia)

Ver `hola_oled.ino` en este directorio. Resumen:

```cpp
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

Adafruit_SSD1306 display(128, 64, &Wire, -1);   // -1 = sin reset

void setup() {
  Wire.begin(21, 22);                           // SDA, SCL
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(2);
  display.setCursor(30, 12);
  display.println("Hola!");
  display.display();
}
void loop() {}
```

## WiFi -> Google Sheets (funcionando)

Sketch en `~/pulp/esp32_sheets/`. La placa se conecta al WiFi y hace HTTPS GET a un
Google Apps Script (Web App) que agrega una fila a una hoja.

Claves que costaron:
- Usar `WiFiClientSecure` con `client.setInsecure()` (no validar cert).
- `https.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS)` porque Google redirige.
- **Subir el timeout**: Apps Script tarda 5-10 s; con el default (5 s) da "read Timeout".
  Usar `client.setTimeout(20000)`, `https.setConnectTimeout(15000)`, `https.setTimeout(20000)`.
- El WiFi debe ser 2.4 GHz.

Apps Script (doGet) usado: `appendRow([new Date(), e.parameter.valor])`, desplegado
como App web con acceso "Cualquier usuario".

## Pendiente

- Enviar mediciones reales de forma periodica (loop con delay), no un valor random.
- Mapear pines de la radio LoRa SX127x (para datalogger LoRa).
- Pinout de la ranura microSD (SPI) para guardar mediciones en CSV.
