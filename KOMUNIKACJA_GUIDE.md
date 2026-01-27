# SWARM ROBOT - GUIDE KOMUNIKACJI
**Kompletny przewodnik po WiFi i Serial/USB**

---

## 📡 PRZEGLĄD TRYBÓW KOMUNIKACJI

System SWARM obsługuje **3 tryby** komunikacji:

1. **🎮 SIMULATOR** - Wirtualne środowisko (Pygame)
2. **📶 WiFi MODE** - WebSocket @ ESP32 (bezprzewodowo)
3. **🔌 SERIAL MODE** - USB RX/TX (przewodowo)

---

## 📶 WiFi MODE - KOMUNIKACJA BEZPRZEWODOWA

### Jak to działa?

```
┌─────────────┐                        ┌─────────────┐
│   KOMPUTER  │◄─────── WiFi ─────────►│    ESP32    │
│  (Python)   │                        │  (Robot)    │
│             │    WebSocket @ IP:81   │             │
│ swarm_main  │◄─────────────────────►│ WebSocket   │
│   .py       │    JSON messages       │  Server     │
└─────────────┘                        └─────────────┘
```

### Protokół komunikacji:

#### Python → ESP32 (komendy):
```json
{
  "type": "command",
  "action": "FORWARD",
  "speed_left": 100,
  "speed_right": 100
}
```

#### ESP32 → Python (sensory):
```json
{
  "type": "sensors",
  "dist_front": 245.5,
  "dist_left": 312.8,
  "dist_right": 189.3,
  "battery_v": 7.8,
  "battery_pct": 85,
  "steps_l": 1234,
  "steps_r": 1267
}
```

#### ESP32 → Python (alerty):
```json
{
  "type": "alert",
  "level": "WARNING",
  "message": "Battery low: 6.9V"
}
```

---

### KONFIGURACJA WiFi MODE

#### Krok 1: ESP32 Network Setup
```cpp
// Na ESP32 (Arduino/ESP-IDF):
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

WiFi.begin(ssid, password);
while (WiFi.status() != WL_CONNECTED) {
  delay(500);
  Serial.print(".");
}

Serial.println("");
Serial.print("CONNECTED! IP: ");
Serial.println(WiFi.localIP());  // ZAPAMIĘTAJ TEN IP!
```

#### Krok 2: Python Detection
```bash
# Uruchom loader
python loader_ENHANCED.py

# Wybierz opcję 5 (Diagnostics)
# System automatycznie znajdzie ESP32 IP
```

**Przykładowy output:**
```
[*] Scanning WiFi network for ESP32...
  Local IP: 192.168.1.150
  Scanning subnet: 192.168.1.0/24 on port 81...
  [FOUND] ESP32 at 10.135.120.105

✅ ESP32 FOUND at 10.135.120.105:81
  Testing WebSocket connection... [OK]
```

#### Krok 3: Połącz się
```bash
# Opcja A: Auto-detect (przez loader)
python loader_ENHANCED.py
# Wybierz: 2. WiFi Mode
# System automatycznie znajdzie IP

# Opcja B: Manual (bezpośrednio)
python swarm_main.py --mode wifi --ip 10.135.120.105
```

---

### TROUBLESHOOTING WiFi

#### Problem: ESP32 nie jest wykrywany
```
❌ ESP32: NOT FOUND

Rozwiązania:
1. Sprawdź Serial Monitor ESP32:
   - Czy pokazuje "CONNECTED! IP: X.X.X.X"?
   - Zapisz ten IP!

2. Sprawdź sieć WiFi:
   - PC i ESP32 w tej samej sieci?
   - ping 10.135.120.105

3. Sprawdź firewall:
   - Zezwól na port 81
   - Windows: Firewall → Reguły przychodzące → Nowa reguła → Port 81

4. Sprawdź router:
   - AP Isolation wyłączony?
   - ESP32 w DHCP lease list?
```

#### Problem: Connection timeout
```
[ERROR] WebSocket connection failed

Rozwiązania:
1. ESP32 WebSocket server działa?
   - Serial Monitor: "WebSocket server started on port 81"

2. Test manualny:
   telnet 10.135.120.105 81
   # Powinno się połączyć

3. Restart ESP32:
   - Power cycle
   - Sprawdź czy ESP32 ponownie łączy się z WiFi
```

#### Problem: Data loss / packet drops
```
⚠️ Sensors: No data received

Rozwiązania:
1. Jakość WiFi:
   - Zbyt daleko od routera?
   - Interferencja (mikrofala, Bluetooth)?
   - Przejdź bliżej routera

2. ESP32 busy?
   - Za dużo komunikatów na sekundę?
   - Zwiększ delay między send()

3. Buffer overflow:
   - ESP32: zwiększ WebSocket buffer size
```

---

## 🔌 SERIAL MODE - KOMUNIKACJA PRZEWODOWA

### Jak to działa?

```
┌─────────────┐      USB Cable       ┌─────────────┐
│   KOMPUTER  │◄────────────────────►│    ESP32    │
│  (Python)   │                      │  (Robot)    │
│             │   RX ◄──────────► TX │             │
│ pyserial    │   TX ◄──────────► RX │   UART      │
│ 115200 baud │   GND ◄─────────► GND│             │
└─────────────┘                      └─────────────┘
```

### Protokół komunikacji:

**IDENTYCZNY JAK WiFi!** - te same JSON messages

Różnica: zamiast WebSocket, używamy **Serial UART @ 115200 baud**

---

### KONFIGURACJA SERIAL MODE

#### Krok 1: Fizyczne połączenie

**Windows:**
```
ESP32 USB → Komputer
Driver: CP210x lub CH340 (auto-install w Win10/11)
Port: COM3, COM4, COM5... (sprawdź Device Manager)
```

**Linux:**
```
ESP32 USB → Komputer
Port: /dev/ttyUSB0, /dev/ttyACM0
Permissions: sudo usermod -a -G dialout $USER
              (logout/login required)
```

**macOS:**
```
ESP32 USB → Komputer
Driver: może wymagać instalacji CP210x
Port: /dev/cu.usbserial-*
```

#### Krok 2: Instalacja pyserial
```bash
pip install pyserial
```

#### Krok 3: Auto-detection
```bash
python loader_ENHANCED.py

# Wybierz: 5. Run Diagnostics
# System automatycznie zeskanuje porty
```

**Przykładowy output:**
```
[*] Scanning Serial/USB ports...
  [FOUND] COM3 - Silicon Labs CP210x USB to UART Bridge
  [FOUND] COM4 - USB Serial Port

  Testing ports for ESP32...
  Testing COM3... [OK] ESP32 detected!

✅ ESP32 FOUND on COM3
```

#### Krok 4: Połącz się
```bash
# Opcja A: Auto-detect (przez loader)
python loader_ENHANCED.py
# Wybierz: 3. Serial Mode
# System automatycznie znajdzie port

# Opcja B: Manual
python swarm_main.py --mode serial --port COM3

# Linux:
python swarm_main.py --mode serial --port /dev/ttyUSB0
```

---

### TROUBLESHOOTING SERIAL

#### Problem: Port not found
```
[ERROR] No serial ports detected

Rozwiązania:
1. Windows - Device Manager:
   - Ports (COM & LPT) → czy widać ESP32?
   - Jeśli nie: zainstaluj driver CP210x/CH340

2. Linux - Permissions:
   sudo usermod -a -G dialout $USER
   # Logout & login

   ls -l /dev/ttyUSB*
   # Powinno pokazać port

3. Kabel USB:
   - Użyj kabla DATA (nie tylko POWER!)
   - Sprawdź czy kabel działa z innym urządzeniem

4. ESP32:
   - Naciśnij przycisk RESET
   - Sprawdź czy LED power świeci
```

#### Problem: Permission denied (Linux)
```
[ERROR] Permission denied: '/dev/ttyUSB0'

Rozwiązanie:
sudo chmod 666 /dev/ttyUSB0
# LUB (trwałe):
sudo usermod -a -G dialout $USER
# Logout & Login
```

#### Problem: Port busy
```
[ERROR] Serial port already in use

Rozwiązania:
1. Zamknij inne programy:
   - Arduino IDE Serial Monitor
   - PuTTY / screen / minicom
   - Inne instancje swarm_main.py

2. Reset port (Linux):
   sudo fuser -k /dev/ttyUSB0

3. Unplug & replug USB
```

#### Problem: Garbage data / wrong baud
```
[ERROR] JSONDecodeError: Expecting value

Rozwiązania:
1. Sprawdź baud rate:
   - ESP32: Serial.begin(115200)
   - Python: baudrate=115200
   - MUSZĄ SIĘ ZGADZAĆ!

2. Serial Monitor test:
   - Otwórz Arduino Serial Monitor @ 115200
   - Czy widzisz poprawne JSON?
   - Jeśli nie → problem w ESP32 kodzie
```

---

## 🔀 PORÓWNANIE: WiFi vs Serial

| Aspekt | WiFi MODE | SERIAL MODE |
|--------|-----------|-------------|
| **Prędkość** | ~10-50ms latency | ~5-10ms latency ✅ |
| **Zasięg** | Do ~50m (zależy od WiFi) ✅ | ~3m (długość kabla) |
| **Niezawodność** | Może gubić pakiety ⚠️ | Bardzo stabilne ✅ |
| **Setup** | Wymaga WiFi config | Plug & play ✅ |
| **Mobilność** | Pełna wolność ✅ | Ograniczona kablem |
| **Debugging** | Trudniejszy | Łatwiejszy ✅ |
| **Power** | Wymaga baterii | Może zasilać z USB ✅ |

### Kiedy używać WiFi?
- ✅ Robot jeździ swobodnie
- ✅ Duży zasięg ruchu
- ✅ Bateria już zainstalowana
- ✅ Demo/prezentacja

### Kiedy używać Serial?
- ✅ Development/debugging
- ✅ Trenowanie w miejscu
- ✅ Stabilne testy
- ✅ Brak WiFi network
- ✅ Niski latency critical

---

## 🔧 KONFIGURACJA ZAAWANSOWANA

### Zmiana portu WebSocket
```python
# swarm_wifi.py
class SimpleWebSocket:
    def __init__(self, host: str, port: int = 8080):  # Zmień z 81
```

```cpp
// ESP32
WebSocketsServer webSocket = WebSocketsServer(8080);  // Zmień z 81
```

### Zmiana baud rate Serial
```python
# swarm_main.py
ESP32SerialAdapter(port=None, baudrate=230400)  # Zwiększ z 115200
```

```cpp
// ESP32
Serial.begin(230400);  // Zwiększ z 115200
```

### Buffer sizes
```cpp
// ESP32 - zwiększ dla szybszej komunikacji
#define WEBSOCKET_MAX_DATA_SIZE 8192
#define SERIAL_RX_BUFFER_SIZE 2048
```

---

## 📊 MONITORING KOMUNIKACJI

### Real-time logs
```bash
# Włącz debug logging
export SWARM_DEBUG=1
python swarm_main.py --mode wifi --ip 10.135.120.105

# Output:
# [DEBUG] Sent: {"type":"command","action":"FORWARD"...}
# [DEBUG] Recv: {"type":"sensors","dist_front":245.5...}
```

### Packet counter
```python
# W swarm_main.py dodaj:
class WiFiAdapter:
    def __init__(self):
        self.packets_sent = 0
        self.packets_received = 0

    def execute(self, ...):
        self.packets_sent += 1
        # ...

    def read_sensors(self):
        # ...
        self.packets_received += 1
```

### Latency measurement
```python
import time

start = time.time()
actuator.execute("FORWARD", 100, 100)
sensor_data = data_source.read_sensors()
latency = (time.time() - start) * 1000  # ms

logger.info(f"Latency: {latency:.1f}ms")
```

---

## 🎯 QUICK START GUIDE

### Pierwszy raz z WiFi:
```bash
1. Podłącz ESP32 do USB
2. Otwórz Arduino Serial Monitor @ 115200
3. Sprawdź czy ESP32 pokazuje: "CONNECTED! IP: X.X.X.X"
4. Zapisz ten IP
5. python loader_ENHANCED.py
6. Wybierz: 2. WiFi Mode
7. Wpisz IP (lub auto-detect)
8. ✅ Gotowe!
```

### Pierwszy raz z Serial:
```bash
1. Podłącz ESP32 do USB
2. python loader_ENHANCED.py
3. Wybierz: 3. Serial Mode
4. System automatycznie znajdzie port
5. ✅ Gotowe!
```

---

## 🛠️ DIAGNOSTYKA - CHECKLIST

Przed zgłoszeniem problemu, sprawdź:

### WiFi Mode:
- [ ] ESP32 połączony z WiFi? (Serial Monitor)
- [ ] PC i ESP32 w tej samej sieci?
- [ ] Można ping-nąć ESP32 IP?
- [ ] Port 81 otwarty? (telnet IP 81)
- [ ] Firewall zezwala?
- [ ] WebSocket server działa na ESP32?

### Serial Mode:
- [ ] Kabel USB DATA (nie tylko power)?
- [ ] Driver zainstalowany? (Device Manager)
- [ ] Port widoczny? (COM3 / /dev/ttyUSB0)
- [ ] Permissions OK? (Linux: dialout group)
- [ ] Baud rate = 115200 (obie strony)?
- [ ] Nic innego nie używa portu?

---

## 📚 DODATKOWE ZASOBY

### Komendy testowe:

```bash
# Test WiFi connection
python -c "from swarm_wifi import SwarmWiFiController; c = SwarmWiFiController('10.135.120.105'); c.start()"

# Test Serial connection
python -c "import serial; s = serial.Serial('COM3', 115200); print(s.readline())"

# Port listing
python -m serial.tools.list_ports

# Network scan
nmap -p 81 192.168.1.0/24  # Znajdź ESP32
```

### ESP32 Arduino przykład:

```cpp
#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>

const char* ssid = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";

WebSocketsServer webSocket = WebSocketsServer(81);

void setup() {
  Serial.begin(115200);

  // Connect WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.print("CONNECTED! IP: ");
  Serial.println(WiFi.localIP());

  // Start WebSocket
  webSocket.begin();
  webSocket.onEvent(webSocketEvent);

  Serial.println("WebSocket server started on port 81");
}

void loop() {
  webSocket.loop();

  // Send sensors every 50ms
  static unsigned long lastSend = 0;
  if (millis() - lastSend > 50) {
    sendSensors();
    lastSend = millis();
  }
}

void sendSensors() {
  StaticJsonDocument<256> doc;
  doc["type"] = "sensors";
  doc["dist_front"] = readFrontSensor();
  doc["dist_left"] = readLeftSensor();
  doc["dist_right"] = readRightSensor();
  doc["battery_v"] = readBattery();

  String output;
  serializeJson(doc, output);
  webSocket.broadcastTXT(output);
  Serial.println(output);  // Dla debugowania
}

void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
  if (type == WStype_TEXT) {
    StaticJsonDocument<256> doc;
    deserializeJson(doc, payload);

    String action = doc["action"];
    int speed_l = doc["speed_left"];
    int speed_r = doc["speed_right"];

    executeCommand(action, speed_l, speed_r);
  }
}
```

---

**Wersja:** 3.1
**Data:** 2026-01-27
**Komunikacja:** WiFi + Serial + Auto-detection
