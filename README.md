# SWARM Robot System v2.1 🚀

**Project:** Autonomous Behavioral Swarm Robot
**Version:** System 2.1 | Core 2.1 | Loader 3.1
**Date:** 2026-01-31

---

## 📦 File Structure

```
SWARM_ROOT/
├── loader.py               # 🚀 UNIVERSAL LAUNCHER (Run this!)
├── reset_environment.py    # 🧹 Reset utility (Archives logs, clears memory)
├── swarm_core.py           # 🧠 AI Decision Engine (NPZ + BLL + OL + Chaos)
├── swarm_main.py           # 🎮 System Integrator (WiFi/Serial/Sim)
├── swarm_trainer.py        # 🎓 Brain Trainer (Incremental Learning)
├── swarm_simulator.py      # 🕹️ 2D Physics Simulator
├── BEHAVIORAL_BRAIN.npz    # 💾 Trained Knowledge Base
├── ESP32_SWARM_ROBOT.ino   # 🤖 Firmware for ESP32
└── logs/                   # 📊 Training Data & Memory
```

---

## 🚀 Quick Start

### 1. Python Environment (PC/Android)

Run the **Universal Loader** to access all tools:

```bash
python loader.py
```

**Menu Options:**
- **[1] Run Simulator**: Train the AI in a virtual environment. Safe & fast.
- **[2] Run Live Robot**: Connect to physical robot via WiFi or Serial.
- **[3] Train Brain**: Learn from collected logs (Sim + Live). Updates `BEHAVIORAL_BRAIN.npz`.
- **[7] Reset Environment**: Archive old logs and clear short-term memory for a fresh start.

### 2. ESP32 Firmware (Robot)

1. Open `ESP32_SWARM_ROBOT.ino` in Arduino IDE.
2. Install libraries: `ArduinoJson`, `WebSockets`.
3. Configure WiFi in the top section:
   ```cpp
   const char* WIFI_SSID = "YOUR_SSID";
   const char* WIFI_PASSWORD = "YOUR_PASS";
   ```
4. Upload to ESP32.

---

## 🧠 AI Architecture (v2.1)

The system uses a **Hybrid ABSR Decision Engine**:

1. **Safety Fuse (Rules):** Immediate reaction to critical threats (e.g. collision imminent).
2. **NPZ Brain (Knowledge):** Matches sensor patterns to known concepts (Vector Similarity).
3. **Online Learning (OL):** "Learns from Fuses". If a Safety Fuse saves the robot, the sensor pattern is memorized and added to the Brain.
4. **Lorenz Chaos:** Adds pseudo-random exploration variability to prevent loops.

**Incremental Learning Loop:**
`Simulate/Drive` → `Log (Note: RULE_...)` → `Train` → `Brain Update` → `Smarter Robot`

---

## 🔧 Hardware Setup

- **Controller:** ESP32 (WROOM-32)
- **Motors:** 2x 28BYJ-48 Steppers + ULN2003 Drivers
- **Sensors:** 3x HC-SR04 (Left -15°, Front 0°, Right +15°)
- **Power:** 2S Li-Ion (7.4V) with voltage divider on GPIO 34.

**Pinout:**
- **Left Motor:** 25, 26, 27, 14
- **Right Motor:** 32, 33, 12, 13
- **Sensors (Trig/Echo):** L(4,5), F(16,17), R(18,19)

---

## 📊 Troubleshooting

**"No module named..."**
- Select **[6] Check Dependencies** in `loader.py` to auto-install requirements.

**ESP32 not connecting**
- Use **[4] Diagnostics** in `loader.py` to scan for the robot.
- Check if PC and Robot are on the same WiFi.

**Brain not learning**
- Ensure you run **[3] Train Brain** after generating logs.
- Check `logs/` folder for `.csv` files.

---

*Ready for Autonomous Operation.*
