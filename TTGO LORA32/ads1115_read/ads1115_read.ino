// TTGO LoRa32 V2.1 + ADS1115 + INA240A1
// GPIO19 receives the 3.3 V measurement-window signal from FPGA H4/JD1.
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

constexpr uint8_t OLED_ADDR = 0x3C;
constexpr uint8_t ADS_ADDR = 0x48;
constexpr uint8_t ADS_REG_CONVERSION = 0x00;
constexpr uint8_t ADS_REG_CONFIG = 0x01;
constexpr uint8_t SYNC_PIN = 19;
constexpr uint8_t LORA_CS_PIN = 18;
constexpr uint8_t LORA_RESET_PIN = 23;

// AIN0 to GND, continuous conversion, +/-2.048 V, 860 samples/s.
// This doubles the voltage resolution, but the INA240 output must stay below
// the full-scale limit with a little headroom.
constexpr uint16_t ADS_CONFIG = 0xC4E3;
constexpr float ADS_LSB_VOLTS = 0.0000625f;

constexpr float SHUNT_OHMS = 0.1f;
constexpr float INA_GAIN = 20.0f;
constexpr float LOAD_VOLTS = 5.0f;

Adafruit_SSD1306 display(128, 64, &Wire, -1);

enum class CaptureState {
  WAIT_FOR_LOW,
  ARMED,
  MEASURING,
};

CaptureState captureState = CaptureState::WAIT_FOR_LOW;
double powerSum = 0.0;
uint32_t sampleCount = 0;
uint32_t measurementStartMs = 0;

void writeRegister(uint8_t reg, uint16_t value) {
  Wire.beginTransmission(ADS_ADDR);
  Wire.write(reg);
  Wire.write(value >> 8);
  Wire.write(value & 0xFF);
  Wire.endTransmission();
}

bool adsPresent() {
  Wire.beginTransmission(ADS_ADDR);
  return Wire.endTransmission() == 0;
}

int16_t readConversion() {
  Wire.beginTransmission(ADS_ADDR);
  Wire.write(ADS_REG_CONVERSION);
  Wire.endTransmission(false);
  Wire.requestFrom(ADS_ADDR, static_cast<uint8_t>(2));

  if (Wire.available() != 2) {
    return 0;
  }

  uint16_t raw = (static_cast<uint16_t>(Wire.read()) << 8) | Wire.read();
  return static_cast<int16_t>(raw);
}

void showError(const char* message) {
  Serial.println(message);
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println(message);
  display.display();
}

void showStatus(const char* status) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(28, 26);
  display.println(status);
  display.display();
}

void showAverage(double averagePower) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(32, 8);
  display.println("PROMEDIO");
  display.setTextSize(2);
  display.setCursor(16, 30);
  display.printf("%.3f W", averagePower);
  display.display();
}

void setup() {
  Serial.begin(115200);
  delay(300);

  pinMode(LORA_CS_PIN, OUTPUT);
  digitalWrite(LORA_CS_PIN, HIGH);
  pinMode(LORA_RESET_PIN, OUTPUT);
  digitalWrite(LORA_RESET_PIN, LOW);
  pinMode(SYNC_PIN, INPUT);
  Wire.begin(21, 22);
  Wire.setClock(400000);

  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("ERROR: OLED no responde");
  }

  if (!adsPresent()) {
    showError("ERROR: ADS1115 no responde en 0x48");
    while (true) {
      delay(1000);
    }
  }

  writeRegister(ADS_REG_CONFIG, ADS_CONFIG);
  delay(10);

  showStatus("ESPERANDO");
  Serial.println("Esperando GPIO19 bajo para armar la medicion");
}

void loop() {
  bool syncHigh = digitalRead(SYNC_PIN) == HIGH;

  if (captureState == CaptureState::WAIT_FOR_LOW) {
    if (!syncHigh) {
      captureState = CaptureState::ARMED;
      Serial.println("Medicion armada; esperando flanco ascendente");
    }
    return;
  }

  if (captureState == CaptureState::ARMED) {
    if (syncHigh) {
      powerSum = 0.0;
      sampleCount = 0;
      measurementStartMs = millis();
      captureState = CaptureState::MEASURING;
      showStatus("MIDIENDO");
      Serial.println("Inicio de medicion");
    }
    return;
  }

  if (!syncHigh) {
    uint32_t durationMs = millis() - measurementStartMs;
    if (sampleCount > 0) {
      double averagePower = powerSum / sampleCount;
      showAverage(averagePower);
      Serial.printf("Promedio: %.6f W, muestras: %lu, duracion: %lu ms\n",
                    averagePower, sampleCount, durationMs);
    } else {
      showError("ERROR: sin muestras");
    }
    captureState = CaptureState::ARMED;
    return;
  }

  int16_t raw = readConversion();
  float vout = raw * ADS_LSB_VOLTS;
  float current = vout / (INA_GAIN * SHUNT_OHMS);
  powerSum += LOAD_VOLTS * current;
  sampleCount++;

  delayMicroseconds(1163);
}
