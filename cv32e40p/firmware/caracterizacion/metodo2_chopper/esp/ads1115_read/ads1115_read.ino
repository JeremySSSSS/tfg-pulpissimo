// TTGO LoRa32 V2.1 + ADS1115 + INA240A1
// GPIO19 receives the 3.3 V measurement-window signal from FPGA H4/JD1.
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// WiFi -> Google Sheets (Apps Script Web App)
// Replace SCRIPT_URL with your deployed web app URL.
const char* WIFI_SSID = "SOLIS AP 7";
const char* WIFI_PASS = "SolisAP7*";
const char* SCRIPT_URL = "https://script.google.com/macros/s/REDACTED/exec";

constexpr uint8_t ADS_ADDR = 0x48;
constexpr uint8_t OLED_ADDR = 0x3C;
constexpr uint8_t ADS_REG_CONVERSION = 0x00;
constexpr uint8_t ADS_REG_CONFIG = 0x01;
constexpr uint8_t SYNC_PIN = 19;
constexpr uint8_t LORA_CS_PIN = 18;
constexpr uint8_t LORA_RESET_PIN = 23;

#ifndef RUN_LABEL
#define RUN_LABEL "unset"
#endif

// AIN0 to GND, continuous conversion, +/-2.048 V, 860 samples/s.
// SHUNT_OHMS = 50mohm. Resolucion 62.5 uV/LSB.
constexpr uint16_t ADS_CONFIG = 0xC4E3;
constexpr float ADS_LSB_VOLTS = 0.0000625f;

constexpr float SHUNT_OHMS = 0.05f;
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
double rawSum = 0.0;
double voutSum = 0.0;
uint32_t sampleCount = 0;
uint32_t measurementStartMs = 0;

bool wifiReady = false;

// OLED: refresco de baja frecuencia (la I2C del OLED frena el muestreo) + ultimo resultado.
uint32_t lastDispMs = 0;
double lastAvg = 0;
bool haveResult = false;

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

// Encabezado: titulo en barra invertida + contenido en lineas de abajo.
void header(const char* title) {
  display.clearDisplay();
  display.fillRect(0, 0, 128, 11, SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK);
  display.setTextSize(1);
  display.setCursor(3, 2); display.print(title);
  display.setTextColor(SSD1306_WHITE);
}
void line(int row, const char* s) {            // row 0..3, bajo el encabezado
  display.setCursor(0, 15 + row * 12); display.print(s);
}

void showError(const char* message) {
  Serial.println(message);
  header("ERROR");
  line(0, message);
  display.display();
}

// Reposo: estado de WiFi + ultimo promedio medido (si hay).
void screenIdle() {
  header("MEDIDOR");
  char b[26];
  if (wifiReady) { snprintf(b, sizeof(b), "WiFi %lddBm", (long)WiFi.RSSI()); line(0, b); }
  else           line(0, "WiFi: ...");
  line(1, "esperando GPIO");
  if (haveResult) { snprintf(b, sizeof(b), "ult: %.4f W", lastAvg); line(2, b); }
  display.display();
}

// En medicion: estado fijo, sin mostrar promedio parcial.
void screenMeasuring(double avg, uint32_t elapsedMs) {
  header("MIDIENDO");
  char b[26];
  snprintf(b, sizeof(b), "P: %.4f W", avg);                                   line(0, b);
  snprintf(b, sizeof(b), "n: %lu", (unsigned long)sampleCount);               line(1, b);
  snprintf(b, sizeof(b), "t: %lu.%lu s", (unsigned long)(elapsedMs/1000), (unsigned long)((elapsedMs/100)%10)); line(2, b);
  display.display();
}

// Resultado: promedio grande (W) + muestras y duracion.
void screenResult(double avg, uint32_t durMs) {
  header("PROMEDIO");
  char b[26];
  display.setTextSize(2);
  snprintf(b, sizeof(b), "%.4f", avg);
  display.setCursor(0, 16); display.print(b);
  display.setTextSize(1); display.print(" W");
  snprintf(b, sizeof(b), "n %lu", (unsigned long)sampleCount);                line(2, b);
  snprintf(b, sizeof(b), "t %lu ms", (unsigned long)durMs);                   line(3, b);
  display.display();
}

void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 20000) {
    delay(300);
  }
  wifiReady = (WiFi.status() == WL_CONNECTED);
}

bool uploadAverage(double averagePower, uint32_t durationMs, uint32_t samples) {
  if (!wifiReady) {
    connectWifi();
  }
  if (!wifiReady) {
    Serial.println("WiFi: no conectado, no se sube a Sheets");
    return false;
  }

  String url = String(SCRIPT_URL) +
               "?profile=" + RUN_LABEL +
               "&valor=" + String(averagePower, 6) +
               "&p_avg=" + String(averagePower, 6) +
               "&samples=" + String(samples) +
               "&duration_ms=" + String(durationMs);

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(20000);

  HTTPClient https;
  https.begin(client, url);
  https.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
  https.setConnectTimeout(15000);
  https.setTimeout(20000);

  int code = https.GET();
  String resp = https.getString();
  https.end();

  Serial.printf("Sheets HTTP=%d resp=%s\n", code, resp.c_str());
  return code > 0 && code < 400;
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
  connectWifi();

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

  screenIdle();
  Serial.println("Esperando GPIO19 bajo para armar la medicion");
}

void loop() {
  bool syncHigh = digitalRead(SYNC_PIN) == HIGH;

  if (captureState == CaptureState::WAIT_FOR_LOW) {
    if (!syncHigh) {
      captureState = CaptureState::ARMED;
      Serial.println("Medicion armada; esperando flanco ascendente");
    }
    if (millis() - lastDispMs > 1000) { lastDispMs = millis(); screenIdle(); }
    return;
  }

  if (captureState == CaptureState::ARMED) {
    if (syncHigh) {
      powerSum = 0.0;
      rawSum = 0.0;
      voutSum = 0.0;
      sampleCount = 0;
      measurementStartMs = millis();
      captureState = CaptureState::MEASURING;
      Serial.println("Inicio de medicion");
    }
    if (millis() - lastDispMs > 1000) { lastDispMs = millis(); screenIdle(); }
    return;
  }

  if (!syncHigh) {
    uint32_t durationMs = millis() - measurementStartMs;
    if (sampleCount > 0) {
      double averagePower = powerSum / sampleCount;
      double averageRaw = rawSum / sampleCount;
      double averageVout = voutSum / sampleCount;
      lastAvg = averagePower; haveResult = true;
      screenResult(averagePower, durationMs);
      Serial.printf("Promedio: %.6f W, RAW_avg: %.2f, Vout_avg: %.6f V, muestras: %lu, duracion: %lu ms\n",
                    averagePower, averageRaw, averageVout, sampleCount, durationMs);
      uploadAverage(averagePower, durationMs, sampleCount);
      lastDispMs = millis();   // deja el resultado un rato antes del reposo
    } else {
      showError("sin muestras");
    }
    captureState = CaptureState::ARMED;
    return;
  }

  int16_t raw = readConversion();
  float vout = raw * ADS_LSB_VOLTS;
  float current = vout / (INA_GAIN * SHUNT_OHMS);
  rawSum += raw;
  voutSum += vout;
  powerSum += LOAD_VOLTS * current;
  sampleCount++;

  if (millis() - lastDispMs > 1000) {
    lastDispMs = millis();
    screenMeasuring(powerSum / sampleCount, millis() - measurementStartMs);
  }

  delayMicroseconds(1163);
}
