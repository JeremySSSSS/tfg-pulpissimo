// LILYGO TTGO LoRa32 V2.1 (T3 v1.6) - OLED SSD1306 0.96"
// OLED: I2C addr 0x3C, SDA=21, SCL=22, SIN reset por GPIO (-1)
// OJO: en el ESP32-PICO-D4, GPIO16 y GPIO17 estan reservados por la flash: NO usar.
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define OLED_SDA   21
#define OLED_SCL   22
#define SCREEN_W   128
#define SCREEN_H   64
#define OLED_ADDR  0x3C

Adafruit_SSD1306 display(SCREEN_W, SCREEN_H, &Wire, -1);   // -1 = sin pin de reset

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== TTGO LoRa32: OLED ===");

  Wire.begin(OLED_SDA, OLED_SCL);

  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("ERROR: OLED no responde");
    return;
  }
  Serial.println("OLED OK, dibujando Hola");

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  display.setTextSize(2);
  display.setCursor(30, 12);
  display.println("Hola!");

  display.setTextSize(1);
  display.setCursor(6, 44);
  display.println("TTGO LoRa32 V2.1");

  display.display();
}

void loop() {
}
