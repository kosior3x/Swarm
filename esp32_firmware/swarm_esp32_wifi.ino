/**
 * SWARM ESP32 Tricycle Robot - ADVANCED FIRMWARE v3.0
 *
 * Features:
 * - Hybrid Communication (WiFi WebSocket + USB Serial)
 * - Hardware Steps Memory (Odometry) & Atomic Maneuvers
 * - On-board Reflexes (Emergency Braking & Oscillation Prevention)
 * - Sonar Noise Filtering
 * - AUTO-AP FALLBACK: Switches to AP "robots" / "11111111" if no signal for 15s
 * - COMMAND-ACK PROTOCOL: Sends "executed" confirmation for every command
 * - LIVE HEARTBEAT: Continuous status reporting
 */

#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>

// ======================================================================================
// CONFIGURATION
// ======================================================================================

// Pins (Based on HARDWARE_CONFIG.py)
const int LEFT_MOTOR_PINS[] = {25, 26, 27, 14};
const int RIGHT_MOTOR_PINS[] = {32, 33, 12, 13};
const int TRIG_LEFT = 4;
const int ECHO_LEFT = 5;
const int TRIG_RIGHT = 18;
const int ECHO_RIGHT = 19;
const int LED_PIN = 2;

// Safety & Logic
const unsigned long COMM_TIMEOUT_MS = 15000; // 15s watchdog
const char* AP_SSID = "robots";
const char* AP_PASS = "11111111";
const char* DEF_SSID = "SWARM_NET";
const char* DEF_PASS = "swarm_password";

const int WS_PORT = 81;
const int EMERGENCY_BACK_STEPS = 1000; // ~5cm
const int MIN_SAFE_DIST = 60; // mm

// ======================================================================================
// GLOBALS
// ======================================================================================

WebSocketsServer webSocket(WS_PORT);
bool wifiActive = false;
bool clientConnected = false;
bool isApMode = false;
unsigned long lastPacketTime = 0; // Watchdog timer

// Motor State
struct Motor {
  const int* pins;
  long absoluteStep;
  int speed;
  long targetStep;
  bool positioning;
  long lastStepTime;
  int stepIndex;
  unsigned long stepDelay;
};

// 28BYJ-48 Half-step sequence
const int stepSequence[8][4] = {
  {1, 0, 0, 0}, {1, 1, 0, 0}, {0, 1, 0, 0}, {0, 1, 1, 0},
  {0, 0, 1, 0}, {0, 0, 1, 1}, {0, 0, 0, 1}, {1, 0, 0, 1}
};

Motor mLeft = {LEFT_MOTOR_PINS, 0, 0, 0, false, 0, 0, 0};
Motor mRight = {RIGHT_MOTOR_PINS, 0, 0, 0, false, 0, 0, 0};

// Sensor & Logic State
float distLeft = 0;
float distRight = 0;
unsigned long lastSensorRead = 0;
String lastTurnDir = "NONE";
unsigned long lastTurnTime = 0;
String systemStatus = "OK"; // OK, NOK, BUSY

// ======================================================================================
// LOW LEVEL CONTROL
// ======================================================================================

void setSpeed(Motor &m, int speedPct) {
    m.speed = constrain(speedPct, -100, 100);
    m.positioning = false;
    if (m.speed == 0) m.stepDelay = 0;
    else m.stepDelay = 100000 / abs(m.speed);
}

void setTargetSteps(Motor &m, int relativeSteps, int speedPct) {
    m.targetStep = m.absoluteStep + relativeSteps;
    int spd = abs(speedPct);
    m.speed = (relativeSteps > 0) ? spd : -spd;
    m.stepDelay = 100000 / abs(m.speed);
    m.positioning = true;
}

void updateMotor(Motor &m) {
    if (m.speed == 0) return;

    // Check target reach
    if (m.positioning) {
        if ((m.speed > 0 && m.absoluteStep >= m.targetStep) ||
            (m.speed < 0 && m.absoluteStep <= m.targetStep)) {
            m.speed = 0;
            m.positioning = false;
            return;
        }
    }

    unsigned long now = micros();
    if (now - m.lastStepTime >= m.stepDelay) {
        m.lastStepTime = now;
        if (m.speed > 0) { m.stepIndex++; m.absoluteStep++; }
        else { m.stepIndex--; m.absoluteStep--; }
        m.stepIndex &= 7;
        for (int i = 0; i < 4; i++) digitalWrite(m.pins[i], stepSequence[m.stepIndex][i]);
    }
}

// ======================================================================================
// SENSORS & FILTERING
// ======================================================================================

float readSonarFiltered(int trig, int echo) {
    float reads[3];
    for(int i=0; i<3; i++) {
        digitalWrite(trig, LOW); delayMicroseconds(2);
        digitalWrite(trig, HIGH); delayMicroseconds(10);
        digitalWrite(trig, LOW);
        long dur = pulseIn(echo, HIGH, 15000);
        reads[i] = (dur == 0) ? 400.0 : (dur * 0.034 / 2);
        delay(2);
    }
    // Median
    if (reads[0] > reads[1]) { float t=reads[0]; reads[0]=reads[1]; reads[1]=t; }
    if (reads[1] > reads[2]) { float t=reads[1]; reads[1]=reads[2]; reads[2]=t; }
    if (reads[0] > reads[1]) { float t=reads[0]; reads[0]=reads[1]; reads[1]=t; }
    return reads[1];
}

// ======================================================================================
// LOGIC & COMMS
// ======================================================================================

void sendPacket(String json) {
    if(wifiActive && clientConnected) webSocket.broadcastTXT(json);
    Serial.println(json);
}

void sendAck(String action, String status) {
    StaticJsonDocument<200> doc;
    doc["type"] = "ack";
    doc["action"] = action;
    doc["status"] = status; // "wykonane"
    doc["id"] = millis(); // timestamp ID
    String out;
    serializeJson(doc, out);
    sendPacket(out);
}

void switchToAP() {
    if (isApMode) return;
    Serial.println("Watchdog Timeout! Switching to AP Mode...");
    WiFi.disconnect();
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASS);
    IPAddress myIP = WiFi.softAPIP();
    Serial.print("AP IP: "); Serial.println(myIP);
    isApMode = true;
    wifiActive = true;
    systemStatus = "AP_FALLBACK";

    // Blink LED fast to indicate AP mode
    for(int i=0; i<10; i++) {
        digitalWrite(LED_PIN, !digitalRead(LED_PIN));
        delay(100);
    }
    digitalWrite(LED_PIN, HIGH);
}

void executeReflex(String type) {
    if (type == "EMERGENCY_BACK") {
        setTargetSteps(mLeft, -EMERGENCY_BACK_STEPS, 100);
        setTargetSteps(mRight, -EMERGENCY_BACK_STEPS, 100);
        systemStatus = "REFLEX_BUSY";
    }
}

void processJsonCommand(String json) {
    lastPacketTime = millis(); // Reset Watchdog

    StaticJsonDocument<512> doc;
    DeserializationError err = deserializeJson(doc, json);
    if (err) return;

    String type = doc["type"];

    if (type == "command") {
        String action = doc["action"];

        // Oscillation protection
        if ((action == "TURN_LEFT" && lastTurnDir == "RIGHT") ||
            (action == "TURN_RIGHT" && lastTurnDir == "LEFT")) {
            if (millis() - lastTurnTime < 2000) action = "STOP";
        }

        if (action.startsWith("TURN")) {
             lastTurnDir = (action == "TURN_LEFT") ? "LEFT" : "RIGHT";
             lastTurnTime = millis();
        }

        int sl = doc["speed_left"];
        int sr = doc["speed_right"];
        setSpeed(mLeft, sl);
        setSpeed(mRight, sr);

        if (action == "ESCAPE") executeReflex("EMERGENCY_BACK");

        sendAck(action, "wykonane");
    }
    else if (type == "move_atomic") {
        int stepsL = doc["steps_left"];
        int stepsR = doc["steps_right"];
        int spd = doc["speed"] | 100;
        setTargetSteps(mLeft, stepsL, spd);
        setTargetSteps(mRight, stepsR, spd);
        sendAck("move_atomic", "wykonane");
    }
    else if (type == "ping") {
        // Keep-alive packet
        sendAck("ping", "pong");
    }
}

void sendTelemetry() {
    StaticJsonDocument<512> doc;
    doc["type"] = "sensors";
    doc["dist_left"] = (int)distLeft;
    doc["dist_right"] = (int)distRight;
    doc["dist_front"] = (int)((distLeft + distRight) / 2);
    doc["steps_l"] = mLeft.absoluteStep;
    doc["steps_r"] = mRight.absoluteStep;
    // Live Heartbeat & Status
    doc["wifi_mode"] = isApMode ? "AP" : "STA";
    doc["status"] = systemStatus;
    doc["connected"] = clientConnected;
    doc["signal"] = WiFi.RSSI();

    String out;
    serializeJson(doc, out);
    sendPacket(out);
}

// ======================================================================================
// MAIN LOOP
// ======================================================================================

void setup() {
    Serial.begin(115200);
    pinMode(LED_PIN, OUTPUT);
    for(int i=0; i<4; i++) {
        pinMode(LEFT_MOTOR_PINS[i], OUTPUT);
        pinMode(RIGHT_MOTOR_PINS[i], OUTPUT);
    }
    pinMode(TRIG_LEFT, OUTPUT); pinMode(ECHO_LEFT, INPUT);
    pinMode(TRIG_RIGHT, OUTPUT); pinMode(ECHO_RIGHT, INPUT);

    // Try Default Network
    Serial.println("Booting...");
    WiFi.begin(DEF_SSID, DEF_PASS);
    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 5000) {
        delay(100); digitalWrite(LED_PIN, !digitalRead(LED_PIN)); // Slow Blink
    }

    if (WiFi.status() == WL_CONNECTED) {
        wifiActive = true;
        isApMode = false;
        digitalWrite(LED_PIN, HIGH);
        Serial.println("Connected to WiFi!");
    } else {
        switchToAP(); // Immediate AP if default unavailable
    }

    webSocket.begin();
    webSocket.onEvent([](uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
        if(type == WStype_CONNECTED) clientConnected = true;
        if(type == WStype_DISCONNECTED) clientConnected = false;
        if(type == WStype_TEXT) processJsonCommand(String((char*)payload));
    });

    lastPacketTime = millis();
}

void loop() {
    if(wifiActive) webSocket.loop();

    if (Serial.available()) {
        String line = Serial.readStringUntil('\n');
        line.trim();
        if (line.startsWith("{")) processJsonCommand(line);
    }

    // Watchdog
    if (millis() - lastPacketTime > COMM_TIMEOUT_MS && !isApMode) {
        switchToAP();
    }

    // Sensors (20Hz)
    if (millis() - lastSensorRead > 50) {
        distLeft = readSonarFiltered(TRIG_LEFT, ECHO_LEFT);
        distRight = readSonarFiltered(TRIG_RIGHT, ECHO_RIGHT);

        // Safety Reflex
        if ((distLeft < MIN_SAFE_DIST || distRight < MIN_SAFE_DIST) && mLeft.speed > 0) {
             executeReflex("EMERGENCY_BACK");
             systemStatus = "NOK_OBSTACLE";
        } else if (systemStatus != "AP_FALLBACK") {
            systemStatus = "OK";
        }

        sendTelemetry();
        lastSensorRead = millis();
    }

    updateMotor(mLeft);
    updateMotor(mRight);
}
