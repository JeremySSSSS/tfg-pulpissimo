// Diagnostico: imprime en vivo el estado del INA228 y del pin de ventana (GPIO19)
// SIN bloquear si el INA no aparece. Sirve para ver si el pin cambia cuando el
// harness hace gpio_high/gpio_low. NO mide ni publica: solo prueba el cableado.
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

static const int SDA_PIN  = 21;
static const int SCL_PIN  = 22;
static const int SYNC_PIN = 19;
static const int LORA_CS_PIN    = 18;   // GPIO19 es MISO del LoRa: hay que dejar
static const int LORA_RESET_PIN = 23;   // la radio deseleccionada y en reset para
static const uint8_t OLED_ADDR = 0x3C;  // que no clave la linea de la ventana.

Adafruit_SSD1306 display(128, 64, &Wire, -1);
uint8_t inaAddr = 0;
bool oledOk = false;

uint32_t readReg(uint8_t addr, uint8_t reg, uint8_t bytes) {
  Wire.beginTransmission(addr); Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return 0;
  if (Wire.requestFrom((int)addr, (int)bytes) != bytes) { while (Wire.available()) Wire.read(); return 0; }
  uint32_t v = 0; while (Wire.available()) v = (v << 8) | Wire.read();
  return v;
}

void findIna() {
  for (uint8_t a = 0x40; a <= 0x4F; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() != 0) continue;
    uint16_t man = (uint16_t)readReg(a, 0x3E, 2);
    uint16_t dev = (uint16_t)readReg(a, 0x3F, 2);
    Serial.printf("I2C 0x%02X MAN=0x%04X DEV=0x%04X\n", a, man, dev);
    if (man == 0x5449 && ((dev >> 4) == 0x228)) { inaAddr = a; return; }
  }
}

void setup() {
  Serial.begin(115200); delay(400);
  pinMode(LORA_CS_PIN, OUTPUT);    digitalWrite(LORA_CS_PIN, HIGH);  // LoRa deseleccionado
  pinMode(LORA_RESET_PIN, OUTPUT); digitalWrite(LORA_RESET_PIN, LOW);// LoRa en reset
  pinMode(SYNC_PIN, INPUT);          // sin pull: leemos lo que llega del FPGA tal cual
  Wire.begin(SDA_PIN, SCL_PIN); Wire.setClock(400000);
  oledOk = display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR);
  Serial.println("\nSYNC PROBE (GPIO19)");
  findIna();
  Serial.printf(inaAddr ? "INA228 OK addr=0x%02X\n" : "INA228 NO detectado\n", inaAddr);
}

void loop() {
  int s = digitalRead(SYNC_PIN);
  Serial.printf("INA=%s  SYNC(GPIO19)=%d\n", inaAddr ? "OK" : "--", s);
  if (oledOk) {
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(1); display.setCursor(0, 0);
    display.printf("INA %s  GPIO19", inaAddr ? "OK" : "NO");
    display.setTextSize(4); display.setCursor(40, 24);
    display.print(s);
    display.display();
  }
  delay(200);   // ~5 Hz, suficiente para ver el flanco de una ventana de segundos
}
