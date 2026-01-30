# SWARM WiFi Robot System

## 📁 Struktura plików

```
wifi_SWARM/
├── swarm_main.py           # Główna pętla robota (uruchom to!)
├── swarm_wifi.py           # Komunikacja WiFi/WebSocket/FTP
├── swarm_unified_core.py   # Silnik decyzyjny ABSR
├── swarm_simulator.py      # Symulator pygame (2 sensory)
├── swarm_trainer.py        # Trening NPZ z logów
├── BEHAVIORAL_BRAIN.npz    # Wytrenowany model (43 koncepty)
├── README.md               # Ten plik
└── esp32_firmware/
    ├── swarm_esp32_wifi.ino  # Firmware ESP32
    └── HARDWARE.md           # Dokumentacja połączeń
```

---

## 🚀 Szybki start

### 1. ESP32 - Wgraj firmware

1. Otwórz `esp32_firmware/swarm_esp32_wifi.ino` w Arduino IDE
2. Zainstaluj biblioteki:
   - `ArduinoJson` (by Benoit Blanchon)
   - `WebSockets` (by Markus Sattler)
3. Wybierz płytkę: ESP32 Dev Module
4. Wgraj

### 2. Python - Uruchom system

```bash
# Tryb z WiFi (ESP32)
python swarm_main.py

# Symulacja (bez ESP32)
python swarm_simulator.py

# Trening modelu
python swarm_trainer.py
```

---

## 📶 Komunikacja WiFi

### Architektura

```
+----------------+     WiFi      +----------------+
|     PC/Phone   |<------------>|     ESP32      |
|    (Python)    |  WebSocket   |   Tricycle Bot |
+----------------+   port 81    +----------------+
       |                              |
       | FTP:2222                     | Sensors
       | esprobot                     | HC-SR04 x2
       | kamil90@                     |
       |                              | Motors
       +<---- CSV Logs ---------------+ 28BYJ-48 x2
```

### Sieci WiFi w ESP32
- Slot 0: `OPPO` / `11111111`
- Slot 1: `Redmi` / `11111111`
- Slot 2: `SWARM_HOTSPOT` / `swarm2026`

---

## 🔌 Połączenia hardware

### Sensory HC-SR04
| Sensor | TRIG | ECHO |
|--------|------|------|
| LEWY (-15°) | GPIO 12 | GPIO 14 |
| PRAWY (+15°) | GPIO 27 | GPIO 26 |

### Silniki 28BYJ-48
| Silnik | IN1 | IN2 | IN3 | IN4 |
|--------|-----|-----|-----|-----|
| LEWY | GPIO 19 | GPIO 21 | GPIO 22 | GPIO 23 |
| PRAWY | GPIO 16 | GPIO 17 | GPIO 5 | GPIO 18 |

### Bateria
- ADC: GPIO 34 (przez dzielnik 10k/10k)

---

## 🧠 Model NPZ

**BEHAVIORAL_BRAIN.npz** zawiera 43 wytrenowanych konceptów:

| Kategoria | Koncepty |
|-----------|----------|
| navigation | FORWARD, CORRIDOR, ASYMMETRIC, CLEAR_PATH |
| avoidance | TURN_LEFT, TURN_RIGHT, DRIFT, WALL_AVOID |
| emergency | ESCAPE, STOP, TRAPPED |
| exploration | EXPLORE_LEFT, EXPLORE_RIGHT |

### Ponowny trening

1. Uruchom symulator i zbieraj dane
2. Uruchom `python swarm_trainer.py`
3. Nowy model zostanie zapisany

---

## 🎮 Sterowanie

### Symulator (swarm_simulator.py)
- `SPACE` - pauza
- `R` - reset
- `ESC` - wyjście

### Główny program (swarm_main.py)
```
1. Start autonomous mode  - Robot jedzie sam
2. Manual control         - WASD sterowanie
3. Request scan           - Skan 360°
4. Check status           - Stan czujników
5. Configure WiFi         - Ustaw sieć
0. Exit
```

---

## 📊 Logi

Logi zapisywane w `logs/`:
- `train_sim_*.csv` - dane z symulacji
- `train_live_*.csv` - dane z ESP32

Format:
```csv
timestamp,source,dist_front,dist_left,dist_right,speed_left,speed_right,action,confidence
```

---

## ⚡ Rozwiązywanie problemów

### ESP32 nie łączy się z WiFi
- Sprawdź hasło w Serial Monitor
- Spróbuj innej sieci

### Python nie znajduje ESP32
- Sprawdź czy są na tej samej sieci
- Podaj IP ręcznie: `SwarmWiFiController(esp32_ip="192.168.x.x")`

### Sensory pokazują 400
- Nie podłączone lub złe piny
- Sprawdź połączenia wg HARDWARE.md

---

*SWARM Project - Behavioral AI Robot*
*v2.0 - WiFi Edition*
