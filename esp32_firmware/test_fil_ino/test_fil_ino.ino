/**
 * SWARM ESP32 Tricycle Robot Firmware - WiFi Version
 * ESP32 DevKit V1
 *
 * WYMAGANE BIBLIOTEKI (Arduino IDE):
 * - ArduinoJson (by Benoit Blanchon) - wersja 6.x lub 7.x
 * - WebSockets (by Markus Sattler) - wersja 2.x
 */

#include <WiFi.h>
#include <WiFiClient.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>
#include <Preferences.h>

// ============================================
// WIFI CONFIGURATION - Twoje sieci
// ============================================

#define MAX_NETWORKS 5
struct WiFiNetwork {
  char ssid[32];
  char password[64];
};

// DOMYSLNE SIECI - zmien na swoje!
WiFiNetwork savedNetworks[MAX_NETWORKS] = {
  {"OPPO", "11111111"},           // Slot 0
  {"Redmi", "11111111"},          // Slot 1
  {"SWARM_HOTSPOT", "swarm2026"}, // Slot 2
  {"", ""},                       // Slot 3
  {"", ""}                        // Slot 4
};

// FTP Configuration
#define FTP_USER "esprobot"
#define FTP_PASS "kamil90@"
#define FTP_PORT 2222
char ftpServerIP[16] = "";
bool ftpAvailable = false;

// WebSocket server na porcie 81
WebSocketsServer webSocket = WebSocketsServer(81);
Preferences preferences;

// ============================================
// PIN DEFINITIONS
// ============================================

// Ultrasonic Sensors HC-SR04
#define TRIG_LEFT 12
#define ECHO_LEFT 14
#define TRIG_RIGHT 27
#define ECHO_RIGHT 26

// Stepper Motor LEFT (28BYJ-48 + ULN2003)
#define STEP_L_IN1 19
#define STEP_L_IN2 21
#define STEP_L_IN3 22
#define STEP_L_IN4 23

// Stepper Motor RIGHT (28BYJ-48 + ULN2003)
#define STEP_R_IN1 16
#define STEP_R_IN2 17
#define STEP_R_IN3 5
#define STEP_R_IN4 18

// Battery ADC
#define BATTERY_ADC 34

// ============================================
// ROBOT SPECS
// ============================================

#define WHEEL_DIAMETER_MM 65.0
#define WHEEL_WIDTH_MM 26.0
#define WHEEL_CIRCUMFERENCE_MM (WHEEL_DIAMETER_MM * PI)
#define WHEEL_BASE_MM 120.0

// Stepper (28BYJ-48: 2048 krokow na obrot z przekladnia 64:1)
#define STEPS_PER_REV 2048
#define STEPS_PER_MM (STEPS_PER_REV / WHEEL_CIRCUMFERENCE_MM)
#define STEP_DELAY_US 2000

// Sensory
#define MAX_DISTANCE_CM 400
#define SOUND_SPEED 0.0343

// Skan
#define SCAN_ANGLE_DEG 30
#define SCAN_SAMPLES 15

// Bateria 2S Li-ion
#define BATT_FULL_V 8.4
#define BATT_NOMINAL_V 7.4
#define BATT_LOW_V 6.8
#define BATT_CRITICAL_V 6.4
#define ADC_DIVIDER_RATIO 2.0
#define ADC_REF_VOLTAGE 3.6
#define ADC_RESOLUTION 4095.0

// ============================================
// STEPPER HALF-STEP SEQUENCE
// ============================================

const int STEP_SEQ[8][4] = {
  {1, 0, 0, 0},
  {1, 1, 0, 0},
  {0, 1, 0, 0},
  {0, 1, 1, 0},
  {0, 0, 1, 0},
  {0, 0, 1, 1},
  {0, 0, 0, 1},
  {1, 0, 0, 1}
};

// ============================================
// GLOBALS
// ============================================

unsigned long lastSensorRead = 0;
unsigned long lastFtpUpload = 0;
float distLeft = 0, distRight = 0;
float batteryVoltage = 0;
int batteryPercent = 0;

int stepPosL = 0, stepPosR = 0;
String currentAction = "STOP";

// Scan data
#define SCAN_MAP_SIZE 61
float scanMapL[SCAN_MAP_SIZE];
float scanMapR[SCAN_MAP_SIZE];
bool scanActive = false;

// Log buffer
#define LOG_BUFFER_SIZE 50
String logBuffer[LOG_BUFFER_SIZE];
int logIdx = 0;

// Connection status
bool wifiConnected = false;
bool wsConnected = false;
uint8_t wsClientNum = 0;

// ============================================
// SETUP
// ============================================

void setup() {
  Serial.begin(115200);
  delay(100);

  Serial.println("\n=============================");
  Serial.println("SWARM ESP32 WiFi Robot v2.0");
  Serial.println("=============================");

  // Zaladuj zapisane sieci
  loadSettings();

  // Inicjalizacja pinow
  initPins();

  // Stop silnikow
  stopMotors();
  readBattery();

  // Polacz WiFi
  connectWiFi();

  // Start WebSocket
  webSocket.begin();
  webSocket.onEvent(onWebSocketEvent);

  // Szukaj FTP
  if (wifiConnected) {
    scanForFTP();
  }

  // Inicjalizuj mape skanowania
  for (int i = 0; i < SCAN_MAP_SIZE; i++) {
    scanMapL[i] = MAX_DISTANCE_CM;
    scanMapR[i] = MAX_DISTANCE_CM;
  }

  Serial.println("=============================");
  Serial.println("READY - Oczekuje na polaczenie");
  Serial.println("=============================");
  sendStatus();
}

void initPins() {
  // Piny ultradzwiekowe
  pinMode(TRIG_LEFT, OUTPUT);
  pinMode(ECHO_LEFT, INPUT);
  pinMode(TRIG_RIGHT, OUTPUT);
  pinMode(ECHO_RIGHT, INPUT);

  // Piny stepperow L
  pinMode(STEP_L_IN1, OUTPUT);
  pinMode(STEP_L_IN2, OUTPUT);
  pinMode(STEP_L_IN3, OUTPUT);
  pinMode(STEP_L_IN4, OUTPUT);

  // Piny stepperow R
  pinMode(STEP_R_IN1, OUTPUT);
  pinMode(STEP_R_IN2, OUTPUT);
  pinMode(STEP_R_IN3, OUTPUT);
  pinMode(STEP_R_IN4, OUTPUT);

  // ADC baterii
  pinMode(BATTERY_ADC, INPUT);
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
}

// ============================================
// WIFI FUNCTIONS
// ============================================

void loadSettings() {
  preferences.begin("swarm", true);

  for (int i = 0; i < MAX_NETWORKS; i++) {
    String ssidKey = "ssid" + String(i);
    String passKey = "pass" + String(i);

    String ssid = preferences.getString(ssidKey.c_str(), "");
    String pass = preferences.getString(passKey.c_str(), "");

    if (ssid.length() > 0) {
      ssid.toCharArray(savedNetworks[i].ssid, 32);
      pass.toCharArray(savedNetworks[i].password, 64);
      Serial.printf("Zaladowano siec [%d]: %s\n", i, savedNetworks[i].ssid);
    }
  }

  preferences.end();
}

void saveNetwork(const char* ssid, const char* password, int slot) {
  if (slot < 0 || slot >= MAX_NETWORKS) return;

  preferences.begin("swarm", false);
  preferences.putString(("ssid" + String(slot)).c_str(), ssid);
  preferences.putString(("pass" + String(slot)).c_str(), password);
  preferences.end();

  strncpy(savedNetworks[slot].ssid, ssid, 31);
  strncpy(savedNetworks[slot].password, password, 63);

  Serial.printf("Zapisano siec [%d]: %s\n", slot, ssid);
}

void connectWiFi() {
  Serial.println("Skanuje sieci WiFi...");

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);

  int numNetworks = WiFi.scanNetworks();
  Serial.printf("Znaleziono %d sieci\n", numNetworks);

  // Probuj kazda zapisana siec
  for (int slot = 0; slot < MAX_NETWORKS; slot++) {
    if (strlen(savedNetworks[slot].ssid) == 0) continue;

    for (int i = 0; i < numNetworks; i++) {
      if (WiFi.SSID(i) == savedNetworks[slot].ssid) {
        Serial.printf("Laczenie z: %s (RSSI: %d dBm)\n",
                     savedNetworks[slot].ssid, WiFi.RSSI(i));

        WiFi.begin(savedNetworks[slot].ssid, savedNetworks[slot].password);

        int timeout = 30;
        while (WiFi.status() != WL_CONNECTED && timeout > 0) {
          delay(500);
          Serial.print(".");
          timeout--;
        }

        if (WiFi.status() == WL_CONNECTED) {
          wifiConnected = true;
          Serial.printf("\n*** POLACZONO! IP: %s ***\n",
                       WiFi.localIP().toString().c_str());
          return;
        } else {
          Serial.println("\nNie udalo sie polaczyc");
        }
      }
    }
  }

  Serial.println("Brak polaczenia WiFi - uzywam Serial");
  wifiConnected = false;
}

void scanForFTP() {
  Serial.println("Szukam serwera FTP...");
  ftpAvailable = false;

  if (!wifiConnected) return;

  IPAddress localIP = WiFi.localIP();

  // Sprawdź typowe adresy w sieci
  for (int addr = 1; addr <= 255; addr++) {
    if (addr == localIP[3]) continue; // Pomiń własny adres

    IPAddress testIP(localIP[0], localIP[1], localIP[2], addr);

    WiFiClient testClient;
    testClient.setTimeout(200);

    if (testClient.connect(testIP, FTP_PORT)) {
      delay(50);

      if (testClient.available()) {
        String resp = testClient.readStringUntil('\n');
        if (resp.startsWith("220")) {
          sprintf(ftpServerIP, "%d.%d.%d.%d", testIP[0], testIP[1], testIP[2], testIP[3]);
          ftpAvailable = true;
          Serial.printf("✓ FTP znaleziony: %s:%d\n", ftpServerIP, FTP_PORT);
          testClient.stop();
          return;
        }
      }
      testClient.stop();
    }

    if (addr % 20 == 0) {
      Serial.print(".");
      webSocket.loop(); // Utrzymaj WebSocket
    }
  }

  Serial.println("\n✗ Brak serwera FTP");
  ftpAvailable = false;
}

// ============================================
// WEBSOCKET HANDLER
// ============================================

void onWebSocketEvent(uint8_t num, WStype_t type, uint8_t *payload, size_t length) {
  switch (type) {
    case WStype_DISCONNECTED:
      Serial.printf("[WS] Klient %u rozlaczony\n", num);
      if (num == wsClientNum) {
        wsConnected = false;
      }
      break;

    case WStype_CONNECTED:
      {
        IPAddress ip = webSocket.remoteIP(num);
        Serial.printf("[WS] Klient %u polaczony z %s\n", num, ip.toString().c_str());
        wsConnected = true;
        wsClientNum = num;
        sendStatus();
      }
      break;

    case WStype_TEXT:
      {
        String msg = String((char*)payload);
        Serial.printf("[WS] Otrzymano: %s\n", msg.c_str());
        processCommand(msg);
      }
      break;

    default:
      break;
  }
}

// ============================================
// SENSOR FUNCTIONS
// ============================================

float readDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 30000);
  if (duration == 0) return MAX_DISTANCE_CM;

  float distance = duration * SOUND_SPEED / 2.0;
  return min(distance, (float)MAX_DISTANCE_CM);
}

void readAllSensors() {
  distLeft = readDistance(TRIG_LEFT, ECHO_LEFT);
  distRight = readDistance(TRIG_RIGHT, ECHO_RIGHT);
}

void readBattery() {
  int adcRaw = analogRead(BATTERY_ADC);
  float adcV = (adcRaw / ADC_RESOLUTION) * ADC_REF_VOLTAGE;
  batteryVoltage = adcV * ADC_DIVIDER_RATIO;

  // Ogranicz zakres
  batteryVoltage = constrain(batteryVoltage, BATT_CRITICAL_V, BATT_FULL_V);

  // Oblicz procent
  batteryPercent = map((int)(batteryVoltage * 100),
                       (int)(BATT_CRITICAL_V * 100),
                       (int)(BATT_FULL_V * 100),
                       0, 100);
  batteryPercent = constrain(batteryPercent, 0, 100);
}

// ============================================
// JSON COMMUNICATION
// ============================================

void sendJSON(JsonDocument& doc) {
  String json;
  serializeJson(doc, json);

  if (wsConnected) {
    webSocket.sendTXT(wsClientNum, json);
  }
  Serial.println(json);
}

void sendSensorData() {
  StaticJsonDocument<300> doc;
  doc["type"] = "sensors";
  doc["dist_left"] = round(distLeft * 10) / 10.0;
  doc["dist_right"] = round(distRight * 10) / 10.0;
  doc["dist_front"] = round((distLeft + distRight) / 2.0 * 10) / 10.0;
  doc["battery_v"] = round(batteryVoltage * 100) / 100.0;
  doc["battery_pct"] = batteryPercent;
  doc["action"] = currentAction;
  doc["wifi"] = wifiConnected;
  doc["ws"] = wsConnected;
  doc["ftp"] = ftpAvailable;
  sendJSON(doc);
}

void sendStatus() {
  StaticJsonDocument<300> doc;
  doc["type"] = "status";
  doc["ip"] = wifiConnected ? WiFi.localIP().toString() : "offline";
  doc["wifi"] = wifiConnected;
  doc["ftp"] = ftpAvailable;
  if (ftpAvailable) {
    doc["ftp_ip"] = ftpServerIP;
  }
  doc["battery_v"] = round(batteryVoltage * 100) / 100.0;
  doc["battery_pct"] = batteryPercent;
  doc["wheel_mm"] = WHEEL_DIAMETER_MM;
  doc["wheel_base"] = WHEEL_BASE_MM;
  doc["uptime"] = millis() / 1000;
  sendJSON(doc);
}

void sendAck(String action) {
  StaticJsonDocument<200> doc;
  doc["type"] = "ack";
  doc["action"] = action;
  doc["battery_v"] = round(batteryVoltage * 100) / 100.0;
  doc["timestamp"] = millis();
  sendJSON(doc);
}

void sendAlert(const char* message) {
  StaticJsonDocument<200> doc;
  doc["type"] = "alert";
  doc["message"] = message;
  doc["battery_v"] = round(batteryVoltage * 100) / 100.0;
  sendJSON(doc);
}

// ============================================
// STEPPER MOTOR FUNCTIONS
// ============================================

void setStepperL(int step) {
  step = ((step % 8) + 8) % 8;
  digitalWrite(STEP_L_IN1, STEP_SEQ[step][0]);
  digitalWrite(STEP_L_IN2, STEP_SEQ[step][1]);
  digitalWrite(STEP_L_IN3, STEP_SEQ[step][2]);
  digitalWrite(STEP_L_IN4, STEP_SEQ[step][3]);
}

void setStepperR(int step) {
  step = ((step % 8) + 8) % 8;
  digitalWrite(STEP_R_IN1, STEP_SEQ[step][0]);
  digitalWrite(STEP_R_IN2, STEP_SEQ[step][1]);
  digitalWrite(STEP_R_IN3, STEP_SEQ[step][2]);
  digitalWrite(STEP_R_IN4, STEP_SEQ[step][3]);
}

void disableSteppers() {
  digitalWrite(STEP_L_IN1, LOW);
  digitalWrite(STEP_L_IN2, LOW);
  digitalWrite(STEP_L_IN3, LOW);
  digitalWrite(STEP_L_IN4, LOW);
  digitalWrite(STEP_R_IN1, LOW);
  digitalWrite(STEP_R_IN2, LOW);
  digitalWrite(STEP_R_IN3, LOW);
  digitalWrite(STEP_R_IN4, LOW);
}

void stopMotors() {
  disableSteppers();
  currentAction = "STOP";
}

void moveSteps(int stepsL, int stepsR) {
  if (stepsL == 0 && stepsR == 0) return;

  int dirL = (stepsL > 0) ? 1 : -1;
  int dirR = (stepsR > 0) ? 1 : -1;

  stepsL = abs(stepsL);
  stepsR = abs(stepsR);

  int maxSteps = max(stepsL, stepsR);
  float incL = (float)stepsL / maxSteps;
  float incR = (float)stepsR / maxSteps;

  float accumL = 0, accumR = 0;

  for (int i = 0; i < maxSteps; i++) {
    accumL += incL;
    accumR += incR;

    if (accumL >= 1.0) {
      stepPosL += dirL;
      setStepperL(stepPosL);
      accumL -= 1.0;
    }

    if (accumR >= 1.0) {
      stepPosR -= dirR;  // Right motor reversed
      setStepperR(stepPosR);
      accumR -= 1.0;
    }

    delayMicroseconds(STEP_DELAY_US);

    // Check sensors every 50 steps
    if (i % 50 == 0) {
      webSocket.loop();
      readAllSensors();

      if (distLeft < 10.0 || distRight < 10.0) {
        stopMotors();
        sendAlert("OBSTACLE_DETECTED");
        return;
      }
    }
  }
}

void moveForward(int mm) {
  int steps = mm * STEPS_PER_MM;
  currentAction = "FORWARD";
  moveSteps(steps, steps);
  stopMotors();
}

void moveBackward(int mm) {
  int steps = mm * STEPS_PER_MM;
  currentAction = "BACKWARD";
  moveSteps(-steps, -steps);
  stopMotors();
}

void rotateDegrees(float degrees) {
  float arcMM = WHEEL_BASE_MM * abs(degrees) * PI / 360.0;
  int steps = arcMM * STEPS_PER_MM;

  currentAction = (degrees > 0) ? "ROTATE_RIGHT" : "ROTATE_LEFT";

  if (degrees > 0) {
    moveSteps(steps, -steps);
  } else {
    moveSteps(-steps, steps);
  }

  stopMotors();
}

// ============================================
// SCAN MODE (SIMULATED - bez faktycznego obracania)
// ============================================

void performFullScan() {
  if (scanActive) return;

  scanActive = true;

  // Informuj o rozpoczęciu skanowania
  {
    StaticJsonDocument<100> doc;
    doc["type"] = "scan";
    doc["status"] = "started";
    sendJSON(doc);
  }

  // Symuluj skanowanie
  int center = SCAN_MAP_SIZE / 2;

  // Generuj losowe dane dla skanu
  for (int i = 0; i < SCAN_MAP_SIZE; i++) {
    float baseDist = random(30, 150);
    float variation = random(-20, 20);

    scanMapL[i] = constrain(baseDist + variation, 20.0, 200.0);
    scanMapR[i] = constrain(baseDist + random(-20, 20), 20.0, 200.0);
  }

  // Oblicz min/max
  float minL = 200.0, minF = 200.0, minR = 200.0;

  for (int i = 0; i < center - 10; i++) {
    float d = min(scanMapL[i], scanMapR[i]);
    if (d < minL) minL = d;
  }

  for (int i = center - 10; i <= center + 10; i++) {
    float d = min(scanMapL[i], scanMapR[i]);
    if (d < minF) minF = d;
  }

  for (int i = center + 10; i < SCAN_MAP_SIZE; i++) {
    float d = min(scanMapL[i], scanMapR[i]);
    if (d < minR) minR = d;
  }

  // Wyślij wyniki
  {
    StaticJsonDocument<300> doc;
    doc["type"] = "scan_result";
    doc["min_left"] = round(minL * 10) / 10.0;
    doc["min_front"] = round(minF * 10) / 10.0;
    doc["min_right"] = round(minR * 10) / 10.0;

    // Rekomendacja
    if (minF < 30.0 && minL < 30.0 && minR < 30.0) {
      doc["recommendation"] = "ESCAPE";
    } else if (minF < 50.0) {
      doc["recommendation"] = (minL > minR) ? "TURN_LEFT" : "TURN_RIGHT";
    } else {
      doc["recommendation"] = "FORWARD";
    }

    sendJSON(doc);
  }

  scanActive = false;

  // Informuj o zakończeniu
  {
    StaticJsonDocument<100> doc;
    doc["type"] = "scan";
    doc["status"] = "completed";
    sendJSON(doc);
  }
}

// ============================================
// SIMPLE FTP CLIENT
// ============================================

bool uploadLogsToFTP() {
  if (!ftpAvailable || strlen(ftpServerIP) == 0 || logIdx == 0) {
    return false;
  }

  Serial.printf("[FTP] Próba połączenia z %s:%d\n", ftpServerIP, FTP_PORT);

  WiFiClient client;
  if (!client.connect(ftpServerIP, FTP_PORT)) {
    Serial.println("[FTP] Połączenie nieudane");
    ftpAvailable = false;
    return false;
  }

  delay(100);

  // Czekaj na powitanie
  unsigned long timeout = millis();
  while (!client.available() && millis() - timeout < 3000) {
    delay(10);
  }

  if (client.available()) {
    String response = client.readStringUntil('\n');
    Serial.println("[FTP] " + response);

    if (response.startsWith("220")) {
      // Logowanie
      client.println("USER " + String(FTP_USER));
      delay(100);
      response = client.readStringUntil('\n');
      Serial.println("[FTP] " + response);

      if (response.startsWith("331")) {
        client.println("PASS " + String(FTP_PASS));
        delay(100);
        response = client.readStringUntil('\n');
        Serial.println("[FTP] " + response);

        if (response.startsWith("230")) {
          // Utwórz plik
          String filename = "swarm_log_" + String(millis()) + ".csv";
          client.println("STOR " + filename);
          delay(100);
          response = client.readStringUntil('\n');

          if (response.startsWith("150")) {
            // Wyślij dane
            for (int i = 0; i < logIdx; i++) {
              client.println(logBuffer[i]);
            }

            client.stop();
            logIdx = 0;
            Serial.println("[FTP] Logi wysłane");
            return true;
          }
        }
      }
    }
  }

  client.stop();
  Serial.println("[FTP] Upload failed");
  return false;
}

void addLogEntry() {
  if (logIdx >= LOG_BUFFER_SIZE) {
    // Przesuń bufor (FIFO)
    for (int i = 1; i < LOG_BUFFER_SIZE; i++) {
      logBuffer[i-1] = logBuffer[i];
    }
    logIdx = LOG_BUFFER_SIZE - 1;
  }

  String entry = String(millis()) + "," +
                 WiFi.localIP().toString() + "," +
                 String(distLeft, 1) + "," +
                 String(distRight, 1) + "," +
                 String(batteryVoltage, 2) + "," +
                 String(batteryPercent) + "," +
                 currentAction;

  logBuffer[logIdx++] = entry;
}

// ============================================
// COMMAND PROCESSING
// ============================================

void processCommand(String json) {
  StaticJsonDocument<512> doc;
  DeserializationError err = deserializeJson(doc, json);

  if (err) {
    Serial.print("[ERROR] JSON parse failed: ");
    Serial.println(err.c_str());
    return;
  }

  String type = doc["type"].as<String>();

  if (type == "command") {
    String action = doc["action"].as<String>();
    int value = doc["value"] | 0;

    currentAction = action;

    if (action == "STOP") {
      stopMotors();
      sendAck("STOP");

    } else if (action == "FORWARD") {
      moveForward(value > 0 ? value : 100);
      sendAck("FORWARD");

    } else if (action == "BACKWARD") {
      moveBackward(value > 0 ? value : 100);
      sendAck("BACKWARD");

    } else if (action == "LEFT") {
      rotateDegrees(-(value > 0 ? value : 90));
      sendAck("LEFT");

    } else if (action == "RIGHT") {
      rotateDegrees(value > 0 ? value : 90);
      sendAck("RIGHT");

    } else if (action == "SCAN") {
      performFullScan();
      sendAck("SCAN");

    } else {
      sendAlert("UNKNOWN_COMMAND");
    }

  } else if (type == "config") {
    if (doc.containsKey("ssid") && doc.containsKey("password")) {
      String ssid = doc["ssid"].as<String>();
      String password = doc["password"].as<String>();
      int slot = doc["slot"] | 0;

      saveNetwork(ssid.c_str(), password.c_str(), slot);

      StaticJsonDocument<100> resp;
      resp["type"] = "config";
      resp["status"] = "saved";
      resp["slot"] = slot;
      sendJSON(resp);

      // Reconnect if we saved current network
      if (WiFi.SSID() == ssid) {
        Serial.println("Reconnecting WiFi...");
        wifiConnected = false;
        connectWiFi();
      }
    }

  } else if (type == "get_status") {
    sendStatus();

  } else if (type == "scan_wifi") {
    connectWiFi();
    sendStatus();

  } else if (type == "scan_ftp") {
    scanForFTP();
    sendStatus();

  } else if (type == "set_ftp") {
    if (doc.containsKey("ip")) {
      String ip = doc["ip"].as<String>();
      ip.toCharArray(ftpServerIP, 16);
      ftpAvailable = true;
      Serial.printf("Ustawiono FTP: %s\n", ftpServerIP);

      StaticJsonDocument<100> resp;
      resp["type"] = "ftp";
      resp["status"] = "set";
      resp["ip"] = ftpServerIP;
      sendJSON(resp);
    }

  } else if (type == "upload_logs") {
    bool success = uploadLogsToFTP();

    StaticJsonDocument<100> resp;
    resp["type"] = "ftp";
    resp["status"] = success ? "uploaded" : "failed";
    sendJSON(resp);
  }
}

// ============================================
// SAFETY CHECKS
// ============================================

void checkBattery() {
  if (batteryVoltage < BATT_CRITICAL_V) {
    sendAlert("BATTERY_CRITICAL");
    stopMotors();
  } else if (batteryVoltage < BATT_LOW_V) {
    sendAlert("BATTERY_LOW");
  }
}

void checkObstacles() {
  if ((distLeft < 10.0 || distRight < 10.0) &&
      currentAction != "STOP" &&
      currentAction != "ESCAPE") {
    stopMotors();
    sendAlert("OBSTACLE_DETECTED");
  }
}

// ============================================
// MAIN LOOP
// ============================================

void loop() {
  webSocket.loop();

  unsigned long currentMillis = millis();

  // Czytaj sensory co 100ms
  if (currentMillis - lastSensorRead >= 100) {
    readAllSensors();
    lastSensorRead = currentMillis;

    // Dodaj do logów co 10 odczytów
    static int readCount = 0;
    if (++readCount >= 10) {
      addLogEntry();
      readCount = 0;

      // Czytaj baterię co 10 cykli
      readBattery();
      checkBattery();
    }

    // Sprawdź przeszkody
    checkObstacles();

    // Wyślij dane
    if (wsConnected) {
      sendSensorData();
    }
  }

  // Spróbuj wysłać logi co 30 sekund jeśli są
  if (currentMillis - lastFtpUpload >= 30000 && logIdx > 0) {
    if (ftpAvailable) {
      uploadLogsToFTP();
    }
    lastFtpUpload = currentMillis;
  }

  // Obsługa komend z Serial
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) {
      processCommand(line);
    }
  }

  // Utrzymaj stabilność
  delay(1);
}