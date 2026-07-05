// TTGO LoRa32 + ADS1115 + INA240A1 -- modo CHOPPER (medicion diferencial).
// GPIO19 recibe el GPIO8 del FPGA, que ahora ALTERNA: alto = fase categoria,
// bajo = fase idle. Este firmware muestrea la potencia continuamente y la bina
// por estado del GPIO: acumula suma/cuenta de la fase ALTA y de la BAJA por
// separado. Cuando el experimento termina (GPIO bajo continuo > 1.5 s), calcula
//   delta = promedio_alto - promedio_bajo
// = potencia dinamica de la categoria sobre el idle, y la sube al Sheet.
// La deriva termica (lenta) se cancela porque las fases adyacentes estan a <1 s.
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

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
#define RUN_LABEL "chopper"
#endif

// AIN0-GND, continuo, +/-4.096 V, 860 SPS. SHUNT_OHMS calibrado por POTENCIA
// (idle real ~5.05 W): el paralelo dejo el shunt efectivo en ~91mohm, NO 50. Con
// 91mohm + G=20 a 1A da V_out~1.82V; +/-4.096V clipea a 2.25A (margen ok),
// +/-2.048V clipearia a 1.125A (riesgo en los picos de alu). Resolucion 125 uV/LSB.
constexpr uint16_t ADS_CONFIG = 0xC2E3;
constexpr float ADS_LSB_VOLTS = 0.000125f;
constexpr float SHUNT_OHMS = 0.091f;
constexpr float INA_GAIN = 20.0f;
constexpr float LOAD_VOLTS = 5.0f;

constexpr uint32_t END_GAP_MS = 1500;   // bajo continuo > esto => fin del experimento
constexpr uint8_t  SKIP_AFTER_EDGE = 2; // descarta muestras tras un cambio de fase (transitorio)

Adafruit_SSD1306 display(128, 64, &Wire, -1);

double sumHigh = 0, sumLow = 0;
uint32_t cntHigh = 0, cntLow = 0;
uint32_t lastHighMs = 0;
bool running = false;
bool prevHigh = false;
bool sawLow = false;        // vimos un bajo -> el firmware ya hizo gpio_init
uint8_t skip = 0;
bool wifiReady = false;

// OLED: refresco de baja frecuencia (la I2C del OLED frena el muestreo) + ultimo resultado.
uint32_t lastDispMs = 0;
double lastDelta = 0, lastAvgH = 0, lastAvgL = 0;
bool haveResult = false;

void writeRegister(uint8_t reg, uint16_t value) {
  Wire.beginTransmission(ADS_ADDR);
  Wire.write(reg); Wire.write(value >> 8); Wire.write(value & 0xFF);
  Wire.endTransmission();
}
bool adsPresent() { Wire.beginTransmission(ADS_ADDR); return Wire.endTransmission() == 0; }
int16_t readConversion() {
  Wire.beginTransmission(ADS_ADDR);
  Wire.write(ADS_REG_CONVERSION);
  Wire.endTransmission(false);
  Wire.requestFrom(ADS_ADDR, static_cast<uint8_t>(2));
  if (Wire.available() != 2) return 0;
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

// Reposo: estado de WiFi + ultimo delta medido (si hay).
void screenIdle() {
  header("CHOPPER");
  char b[26];
  if (wifiReady) { snprintf(b, sizeof(b), "WiFi %lddBm", (long)WiFi.RSSI()); line(0, b); }
  else           line(0, "WiFi: ...");
  line(1, "esperando GPIO");
  if (haveResult) { snprintf(b, sizeof(b), "ult: %.3f mW", lastDelta * 1e3); line(2, b); }
  display.display();
}

// En medicion: potencia en vivo, fase actual y conteo de muestras.
void screenRun(float P, bool high) {
  header("MIDIENDO");
  char b[26];
  snprintf(b, sizeof(b), "P: %.4f W", P);                                      line(0, b);
  line(1, high ? "fase: ALTO  ^" : "fase: bajo  _");
  snprintf(b, sizeof(b), "nH:%lu", (unsigned long)cntHigh);                    line(2, b);
  snprintf(b, sizeof(b), "nL:%lu", (unsigned long)cntLow);                     line(3, b);
  display.display();
}

// Resultado: delta grande (mW) + promedios y conteos.
void screenResult() {
  header("LISTO");
  char b[26];
  display.setTextSize(2);
  snprintf(b, sizeof(b), "%.2f", lastDelta * 1e3);
  display.setCursor(0, 16); display.print(b);
  display.setTextSize(1); display.print(" mW");
  snprintf(b, sizeof(b), "H%.4f L%.4f", lastAvgH, lastAvgL);                   line(2, b);
  snprintf(b, sizeof(b), "n %lu/%lu", (unsigned long)cntHigh, (unsigned long)cntLow); line(3, b);
  display.display();
}
void connectWifi() {
  WiFi.mode(WIFI_STA); WiFi.begin(WIFI_SSID, WIFI_PASS);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 20000) delay(300);
  wifiReady = (WiFi.status() == WL_CONNECTED);
}

bool uploadDelta(double delta, double avgH, double avgL, uint32_t nH, uint32_t nL) {
  if (!wifiReady) connectWifi();
  if (!wifiReady) { Serial.println("WiFi: no conectado"); return false; }
  // delta va en p_avg (lo lee fetch_sheet); avgH en valor; cuentas en samples/duration.
  String url = String(SCRIPT_URL) +
               "?profile=" + RUN_LABEL +
               "&valor=" + String(avgH, 6) +
               "&p_avg=" + String(delta, 6) +
               "&samples=" + String(nH) +
               "&duration_ms=" + String(nL);
  WiFiClientSecure client; client.setInsecure(); client.setTimeout(20000);
  HTTPClient https; https.begin(client, url);
  https.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
  https.setConnectTimeout(15000); https.setTimeout(20000);
  int code = https.GET(); String resp = https.getString(); https.end();
  Serial.printf("Sheets HTTP=%d resp=%s\n", code, resp.c_str());
  return code > 0 && code < 400;
}

void setup() {
  Serial.begin(115200); delay(300);
  pinMode(LORA_CS_PIN, OUTPUT); digitalWrite(LORA_CS_PIN, HIGH);
  pinMode(LORA_RESET_PIN, OUTPUT); digitalWrite(LORA_RESET_PIN, LOW);
  pinMode(SYNC_PIN, INPUT);
  Wire.begin(21, 22); Wire.setClock(400000);
  connectWifi();
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) Serial.println("OLED no responde");
  if (!adsPresent()) { header("ERROR"); line(0, "ADS1115 no resp"); display.display(); while (true) delay(1000); }
  writeRegister(ADS_REG_CONFIG, ADS_CONFIG); delay(10);
  screenIdle();
  Serial.println("Modo CHOPPER: esperando alternancia de GPIO19...");
}

void loop() {
  static uint32_t lastDebugMs = 0;
  bool high = digitalRead(SYNC_PIN) == HIGH;
  int16_t raw = readConversion();
  float vout = raw * ADS_LSB_VOLTS;
  float current = vout / (INA_GAIN * SHUNT_OHMS);
  float P = LOAD_VOLTS * current;
  uint32_t now = millis();

  if (running && (now - lastDebugMs > 1000)) {
    lastDebugMs = now;
    Serial.printf("RAW=%d Vout=%.6f V I=%.6f A P=%.6f W phase=%s\n",
                  raw, vout, current, P, high ? "HIGH" : "LOW");
  }

  // descarta unas muestras tras cada cambio de fase (transitorio del ADC)
  if (!high) sawLow = true;   // ya vimos un bajo => el firmware ejecuto gpio_init

  // Arranca el experimento en el primer flanco BAJO->ALTO (tras haber visto un
  // bajo). Asi se IGNORA el alto inicial con que arranca la FPGA / la carga por
  // JTAG: ese alto no tiene un bajo antes, asi que no dispara el inicio. Si no,
  // se contaria como muestras altas a potencia idle e inflaria nH (y diluiria
  // avgHigh -> delta erroneo).
  if (high && !prevHigh && sawLow && !running) {
    running = true; sumHigh = sumLow = 0; cntHigh = cntLow = 0;
  }

  if (high != prevHigh) { skip = SKIP_AFTER_EDGE; prevHigh = high; }

  if (running && skip == 0) {
    if (high) { sumHigh += P; cntHigh++; }
    else      { sumLow  += P; cntLow++;  }
  }
  if (high) lastHighMs = now;
  if (skip > 0) skip--;

  // fin del experimento: bajo continuo > END_GAP_MS tras haber corrido
  if (running && cntHigh > 0 && cntLow > 0 && (now - lastHighMs) > END_GAP_MS) {
    double avgH = sumHigh / cntHigh;
    double avgL = sumLow / cntLow;
    double delta = avgH - avgL;
    Serial.printf("DELTA=%.6f W  (alto=%.6f baja=%.6f, nH=%lu nL=%lu)\n",
                  delta, avgH, avgL, cntHigh, cntLow);
    lastDelta = delta; lastAvgH = avgH; lastAvgL = avgL; haveResult = true;
    screenResult();
    uploadDelta(delta, avgH, avgL, cntHigh, cntLow);
    running = false;
    sawLow = false;   // exige un nuevo bajo antes de re-armar el proximo experimento
    lastDispMs = millis();  // deja la pantalla de resultado un rato antes del reposo
  }

  // Refresca el OLED a ~1 Hz: la I2C del OLED (~23 ms) frena el muestreo, asi que
  // NO se actualiza cada vuelta. ~2% de muestras perdidas, al azar -> sin sesgo.
  if (now - lastDispMs > 1000) {
    lastDispMs = now;
    if (running) screenRun(P, high);
    else         screenIdle();
  }

  delayMicroseconds(1163);  // ~860 muestras/s
}
