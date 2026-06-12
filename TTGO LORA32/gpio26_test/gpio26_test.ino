#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

constexpr uint8_t SYNC_PIN = 26;
Adafruit_SSD1306 display(128, 64, &Wire, -1);

void setup() {
  Serial.begin(115200);
  pinMode(SYNC_PIN, INPUT);
  Wire.begin(21, 22);
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
}

void loop() {
  bool high = digitalRead(SYNC_PIN) == HIGH;

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(28, 8);
  display.println("GPIO26");
  display.setTextSize(2);
  display.setCursor(38, 30);
  display.println(high ? "HIGH" : "LOW");
  display.display();

  delay(50);
}
