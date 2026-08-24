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
# PCP -> GitHub Worker / task for Copilot

Goal: move process-heavy PCP compilation away from SEOHOST. SEOHOST stays control plane only.

Targets to preserve in first migration:
- UNO R3: arduino:avr:uno / arduino:avr@1.8.8
- ESP32: esp32:esp32:esp32 / esp32:esp32@3.3.11
- ESP32-S3: esp32:esp32:esp32s3 / esp32:esp32@3.3.11
- ESP8266: esp8266:esp8266:nodemcuv2 / esp8266:esp8266@3.1.2
- RP2040 Pico: rp2040:rp2040:rpipico / rp2040:rp2040@6.0.0
- Pico 2: rp2040:rp2040:rpipico2 / rp2040:rp2040@6.0.0

Phase 1:
1. Commit .github/workflows/pcp-build.yml and scripts/github/pcp_build_worker.sh.
2. Map existing golden sketches to stable repo-relative paths.
3. Run workflow_dispatch for all six targets.
4. Artifact must contain build.log, result.json, bin/.
5. Do not change PCP runtime/API yet.
6. Do not start any compiler/toolchain on SEOHOST.
7. Do not add a daemon/cron just for GitHub polling.

Phase 2:
Replace local compile execution in PCP with an in-process GitHub adapter exposing submit_build(), get_build_status(), list_build_artifacts(). The supplied Python bridge is a bootstrap/reference implementation. Prefer in-process HTTP over spawning shell/Python per poll.

Dynamic user source: do not encode arbitrary source into workflow inputs. Use ephemeral Git branch/commit or object storage bundle later.

Security: token outside webroot and repo; fine-grained PAT bootstrap restricted to one repo with Actions read/write and Contents read; later prefer GitHub App installation tokens.

Do not touch VSA/VISSOL/DRDAMSON/Gateway/supervisors or local USB Device Bridge.

Return exact diff, files changed, test results per target, artifact names, and every remaining local compiler invocation in PCP.
# PCP GitHub offload bootstrap

This bundle prepares Phase 1: GitHub Actions executes Arduino builds, SEOHOST only dispatches/status-checks.

Repository files:
- .github/workflows/pcp-build.yml
- scripts/github/pcp_build_worker.sh
- COPILOT_TASK.md

Server-side bootstrap/reference:
- scripts/server/pcp_github_bridge.py
- scripts/server/bootstrap_github_bridge.sh
- config/pcp_github.env.example

Token config must live outside public_html, recommended: $HOME/.config/pcp/github.env with chmod 600.

No local Termux exit/logout is required by this bundle.
