# ESP32 ARDUINO - INSTALLATION & SETUP GUIDE
**Przewodnik instalacji kodu Arduino dla SWARM Robot**

---

## 📦 CO POTRZEBUJESZ

### Hardware:
- ✅ ESP32-WROOM-32 (lub kompatybilny)
- ✅ 2x stepper motor 28BYJ-48 z ULN2003 driver
- ✅ 3x HC-SR04 ultrasonic sensor
- ✅ Battery monitor (voltage divider)
- ✅ Kabel USB (data + power!)

### Software:
- ✅ Arduino IDE 2.x (lub 1.8.19+)
- ✅ ESP32 board support
- ✅ Biblioteki: ArduinoJson, WebSockets

---

## 🔧 INSTALACJA ARDUINO IDE

### Krok 1: Pobierz Arduino IDE
```
Windows/macOS/Linux:
https://www.arduino.cc/en/software

Wybierz wersję 2.x (recommended) lub 1.8.19+
```

### Krok 2: Instaluj ESP32 Board Support

**Arduino IDE 2.x:**
```
1. Otwórz Arduino IDE
2. File → Preferences
3. W "Additional Boards Manager URLs" dodaj:
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
4. OK
5. Tools → Board → Boards Manager
6. Szukaj: "esp32"
7. Zainstaluj: "esp32 by Espressif Systems" (najnowsza wersja)
8. Poczekaj na instalację (może zająć 5-10 min)
```

**Arduino IDE 1.8.x:**
```
1. File → Preferences
2. Additional Boards Manager URLs:
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
3. Tools → Board → Boards Manager
4. Szukaj: "esp32"
5. Install: "esp32 by Espressif Systems"
```

### Krok 3: Instaluj Biblioteki

**Metoda A: Library Manager (polecana)**
```
1. Tools → Manage Libraries (lub Ctrl+Shift+I)
2. Szukaj: "ArduinoJson"
   - Zainstaluj: ArduinoJson by Benoit Blanchon (wersja 6.x)
3. Szukaj: "WebSockets"
   - Zainstaluj: WebSockets by Markus Sattler
4. Gotowe!
```

**Metoda B: Manual (jeśli A nie działa)**
```
1. Pobierz:
   - https://github.com/bblanchon/ArduinoJson/releases
   - https://github.com/Links2004/arduinoWebSockets/releases

2. Sketch → Include Library → Add .ZIP Library
3. Wybierz pobrane pliki .zip
```

---

## 📝 KONFIGURACJA KODU

### Krok 1: Otwórz plik ESP32_SWARM_ROBOT.ino

### Krok 2: Skonfiguruj WiFi

**ZNAJDŹ LINIE 53-54:**
```cpp
const char* WIFI_SSID = "YOUR_WIFI_SSID";        // ZMIEŃ!
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"; // ZMIEŃ!
```

**ZAMIEŃ NA SWOJE:**
```cpp
const char* WIFI_SSID = "MojaSkoczkaSiec";      // Twoja nazwa WiFi
const char* WIFI_PASSWORD = "TajneHaslo123";     // Twoje hasło
```

⚠️ **WAŻNE:**
- Wielkość liter ma znaczenie!
- WiFi musi być 2.4 GHz (ESP32 nie obsługuje 5 GHz)
- Router nie może mieć AP Isolation

### Krok 3: Sprawdź piny (opcjonalne)

Jeśli używasz innych pinów, zmień:

**Silniki (linie 65-66):**
```cpp
const int MOTOR_LEFT_PINS[4] = {25, 26, 27, 14};   // IN1-IN4
const int MOTOR_RIGHT_PINS[4] = {32, 33, 12, 13};  // IN1-IN4
```

**Sensory (linie 69-73):**
```cpp
const int SENSOR_LEFT_TRIG = 4;
const int SENSOR_LEFT_ECHO = 5;
const int SENSOR_FRONT_TRIG = 16;
const int SENSOR_FRONT_ECHO = 17;
const int SENSOR_RIGHT_TRIG = 18;
const int SENSOR_RIGHT_ECHO = 19;
```

**Bateria (linia 76):**
```cpp
const int BATTERY_PIN = 34;  // ADC pin
```

### Krok 4: Dostosuj voltage divider (opcjonalne)

Jeśli używasz innego dzielnika napięcia:

**Linia 77:**
```cpp
const float VOLTAGE_DIVIDER_RATIO = 2.0;  // Zmień jeśli potrzeba
```

**Przykład:**
- Jeśli R1=10kΩ, R2=10kΩ → ratio = 2.0
- Jeśli R1=20kΩ, R2=10kΩ → ratio = 3.0

---

## ⬆️ UPLOAD DO ESP32

### Krok 1: Podłącz ESP32

```
ESP32 → USB → Komputer

Powinien się pojawić nowy port:
- Windows: COM3, COM4, COM5...
- Linux: /dev/ttyUSB0, /dev/ttyACM0
- macOS: /dev/cu.usbserial-*
```

### Krok 2: Wybierz Board

**Arduino IDE:**
```
Tools → Board → ESP32 Arduino → ESP32 Dev Module

LUB jeśli masz inny model:
- DOIT ESP32 DEVKIT V1
- ESP32-WROOM-DA Module
- itd.
```

### Krok 3: Wybierz Port

```
Tools → Port → wybierz odpowiedni port
- Windows: COM3 (przykład)
- Linux: /dev/ttyUSB0 (przykład)
- macOS: /dev/cu.usbserial-* (przykład)
```

### Krok 4: Konfiguruj ustawienia

**Polecane ustawienia:**
```
Tools →
  Board: "ESP32 Dev Module"
  Upload Speed: "921600"
  CPU Frequency: "240MHz"
  Flash Frequency: "80MHz"
  Flash Mode: "QIO"
  Flash Size: "4MB (32Mb)"
  Partition Scheme: "Default 4MB..."
  Core Debug Level: "None" (lub "Info" do debug)
  PSRAM: "Disabled"
  Port: [twój port]
```

### Krok 5: Kompiluj i Upload

```
1. Kliknij: Verify/Compile (✓) - sprawdź błędy
2. Jeśli OK, kliknij: Upload (→)
3. Poczekaj na kompilację...
4. Podczas uploadu może pojawić się:
   "Connecting........_____...."

5. Jeśli stuck na "Connecting...":
   - Przytrzymaj BOOT button na ESP32
   - Puść gdy zacznie się upload
```

**Upload successful:**
```
Hard resetting via RTS pin...
Done uploading.
```

---

## 🔍 TEST I DIAGNOSTYKA

### Test 1: Serial Monitor

```
1. Tools → Serial Monitor
2. Baud rate: 115200
3. Resetuj ESP32 (przycisk RST)
4. Powinno pokazać:

================================
SWARM ROBOT ESP32 v2.1
================================

Initializing motors... OK
Initializing sensors... OK
Connecting to WiFi: MojaSkoczkaSiec
.......

✅ WiFi CONNECTED!
IP Address: 10.135.120.105    ← ZAPAMIĘTAJ!
Signal: -45 dBm
WebSocket server started on port 81

✅ SWARM Robot ready!
Waiting for commands...
```

### Test 2: Ping IP

**Windows:**
```cmd
ping 10.135.120.105

Odpowiedź z 10.135.120.105: ...
```

**Linux/macOS:**
```bash
ping -c 4 10.135.120.105

4 packets transmitted, 4 received, 0% packet loss
```

### Test 3: WebSocket Test

**Otwórz drugi terminal:**
```bash
telnet 10.135.120.105 81

# Powinno połączyć bez błędów
# Ctrl+C aby wyjść
```

### Test 4: Python Connection

```bash
# Uruchom loader
python loader_ENHANCED.py

# Wybierz: 2. WiFi Mode
# Wpisz IP: 10.135.120.105

# LUB auto-detect:
# Wybierz: 5. Run Diagnostics
# System automatycznie znajdzie ESP32
```

---

## 🐛 TROUBLESHOOTING

### Problem: "Board ... not available"
```
Rozwiązanie:
1. Sprawdź czy ESP32 board support jest zainstalowany
2. Restart Arduino IDE
3. Tools → Board → Boards Manager → przeinstaluj ESP32
```

### Problem: "Port not found"
```
Rozwiązanie Windows:
1. Device Manager → Ports (COM & LPT)
2. Sprawdź czy ESP32 jest widoczny
3. Jeśli nie: zainstaluj driver CP210x lub CH340

Rozwiązanie Linux:
sudo usermod -a -G dialout $USER
# Logout & Login
ls -l /dev/ttyUSB*

Rozwiązanie macOS:
1. Sprawdź czy driver zainstalowany
2. ls /dev/cu.*
```

### Problem: "Compilation error"
```
error: 'WebSocketsServer' was not declared

Rozwiązanie:
1. Tools → Manage Libraries
2. Reinstall: WebSockets by Markus Sattler
3. Restart Arduino IDE

error: 'ArduinoJson.h' no such file

Rozwiązanie:
1. Tools → Manage Libraries
2. Install: ArduinoJson by Benoit Blanchon (wersja 6.x!)
```

### Problem: "Upload failed / Timeout"
```
A fatal error occurred: Failed to connect

Rozwiązanie:
1. Przytrzymaj przycisk BOOT podczas uploadu
2. Spróbuj niższej Upload Speed (460800 lub 115200)
3. Sprawdź kabel USB (musi być DATA cable!)
4. Spróbuj innego portu USB
```

### Problem: WiFi connection failed
```
⚠️  WiFi connection FAILED!

Rozwiązanie:
1. Sprawdź SSID i hasło (wielkość liter!)
2. WiFi musi być 2.4 GHz (nie 5 GHz)
3. Sprawdź czy router nie ma MAC filtering
4. Sprawdź czy router nie ma AP Isolation
5. Spróbuj bliżej routera
```

### Problem: No sensor data
```
Sensors: L=400.0 F=400.0 R=400.0

Rozwiązanie:
1. Sprawdź połączenia HC-SR04:
   - VCC → 5V
   - GND → GND
   - TRIG → GPIO (sprawdź pin)
   - ECHO → GPIO przez voltage divider lub level shifter!

2. HC-SR04 używa 5V logic, ESP32 używa 3.3V
   - ECHO pin MUSI mieć voltage divider (R1=1kΩ, R2=2kΩ)
   - LUB użyj level shifter 5V→3.3V

3. Test pojedynczego sensora:
   - Odłącz 2 sensory
   - Test z jednym
```

### Problem: Motors not moving
```
Rozwiązanie:
1. Sprawdź połączenia ULN2003:
   - IN1-IN4 → GPIO pins
   - VCC → 5V lub 12V (zależy od modelu)
   - GND → common ground z ESP32

2. Sprawdź zasilanie:
   - 28BYJ-48 12V wymaga 12V!
   - Nie zasilaj z USB (za mało prądu)
   - Użyj external power supply

3. Test ręczny w Serial Monitor:
   {"type":"command","action":"FORWARD","speed_left":80,"speed_right":80}
```

---

## 📊 MONITORING

### Serial Monitor output:

**Normalny:**
```json
{"type":"sensors","dist_front":245.3,"dist_left":312.8,"dist_right":189.6,"battery_v":7.82,"battery_pct":85,"steps_l":1234,"steps_r":1267,"action":"FORWARD","emergency":false}
```

**Alert - Battery low:**
```json
{"type":"alert","level":"WARNING","message":"Battery low: 6.78V","timestamp":12345}
```

**Alert - Timeout:**
```json
{"type":"alert","level":"TIMEOUT","message":"No command received for 2s - Emergency stop","timestamp":67890}
```

### LED indicators:

**ESP32 onboard LED:**
- Miganie podczas boot
- Stały gdy connected do WiFi
- Gaśnie gdy disconnected

**ULN2003 LEDs:**
- Mrugają podczas ruchu silników
- Wszystkie zgaszone gdy STOP

---

## 🔧 KALIBRACJA

### Motor Speed Tuning

**Jeśli silniki są za wolne:**
```cpp
// Linia 82 - zmniejsz delay
const int STEP_DELAY_US = 800;  // było 1000
```

**Jeśli silniki są za szybkie:**
```cpp
const int STEP_DELAY_US = 1500;  // było 1000
```

### Sensor Calibration

**Jeśli sensory pokazują błędne wartości:**
```cpp
// W funkcji readUltrasonic(), linia ~440
// Adjust speed of sound (zależy od temperatury)
float distance = (duration * 0.0343) / 2.0;  // 343 m/s @ 20°C

// Zimno (0°C): 0.0331
// Ciepło (30°C): 0.0349
```

### Battery Calibration

**Zmierz rzeczywiste napięcie baterii:**
```cpp
// Linia 77 - dostosuj ratio
// Przykład: ESP32 pokazuje 3.9V, multimetr pokazuje 7.8V
// Ratio = 7.8 / 3.9 = 2.0 ✅
```

---

## 📝 CHECKLIST PRZED UŻYCIEM

- [ ] Arduino IDE zainstalowane
- [ ] ESP32 board support zainstalowany
- [ ] Biblioteki: ArduinoJson + WebSockets
- [ ] WiFi SSID i password skonfigurowane
- [ ] Piny sprawdzone (motory, sensory, battery)
- [ ] Kod skompilowany bez błędów
- [ ] Upload successful
- [ ] Serial Monitor pokazuje IP address
- [ ] Ping do ESP32 działa
- [ ] Python może połączyć się przez WiFi
- [ ] Sensory pokazują dane (nie 400.0)
- [ ] Motory reagują na komendy
- [ ] Battery voltage jest poprawne

---

## 🚀 QUICK START SUMMARY

```bash
# 1. Install
- Arduino IDE 2.x
- ESP32 board support
- ArduinoJson + WebSockets libraries

# 2. Configure
- WiFi SSID & password (linie 53-54)
- Pins (jeśli inne niż default)
- Voltage divider ratio (jeśli trzeba)

# 3. Upload
- Board: ESP32 Dev Module
- Port: COM3 (lub /dev/ttyUSB0)
- Upload Speed: 921600
- Click Upload button
- (Hold BOOT if stuck)

# 4. Test
- Serial Monitor @ 115200
- Check IP address
- Ping IP
- Python: loader_ENHANCED.py → WiFi Mode

# 5. Run!
- python swarm_simulator.py (test)
- python loader_ENHANCED.py → 2 (live WiFi)
- python loader_ENHANCED.py → 3 (live Serial)
```

---

**GOTOWE!** ESP32 jest skonfigurowane i gotowe do komunikacji z Python! 🎉

---

**Wersja:** 2.1
**Data:** 2026-01-27
**Dla:** ESP32-WROOM-32 + SWARM Robot
