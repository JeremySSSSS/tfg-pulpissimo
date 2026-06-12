#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

constexpr uint8_t SYNC_PIN = 19;
constexpr uint8_t LORA_CS_PIN = 18;
constexpr uint8_t LORA_RESET_PIN = 23;

Adafruit_SSD1306 display(128, 64, &Wire, -1);

void setup() {
  Serial.begin(115200);

  pinMode(LORA_CS_PIN, OUTPUT);
  digitalWrite(LORA_CS_PIN, HIGH);
  pinMode(LORA_RESET_PIN, OUTPUT);
  digitalWrite(LORA_RESET_PIN, LOW);
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
  display.println("GPIO19");
  display.setTextSize(2);
  display.setCursor(38, 30);
  display.println(high ? "HIGH" : "LOW");
  display.display();

  delay(50);
}
