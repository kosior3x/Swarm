# SWARM Tricycle Robot - Hardware & WiFi Documentation

## 1. ROBOT SPECIFICATIONS

```
        [HC-SR04 L]     [HC-SR04 R]
              \   -15 deg  +15 deg   /
               \       |      /
                \     (o)    /     <- Front swivel caster
                 \     |    /
    +-------------+---------+--------------+
    |                                       |
    |            ESP32 DevKit V1            |
    |               (WiFi)                  |
    |                                       |
    +=====[28BYJ-48]=====+=====[ 28BYJ-48]==+
              |                    |
         LEFT WHEEL          RIGHT WHEEL
         65mm x 26mm         65mm x 26mm
```

### Wheel Dimensions
- **Diameter:** 65 mm
- **Width:** 26 mm
- **Circumference:** 204.2 mm (pi * 65)
- **Steps per mm:** 10.03 (2048 / 204.2)

### Robot Dimensions
- **Wheel base:** ~120 mm (adjust in code)
- **Total width:** ~170 mm
- **Total length:** ~150 mm

---

## 2. COMPONENTS LIST

| Component | Qty | Model | Specs |
|-----------|-----|-------|-------|
| ESP32 | 1 | DevKit V1 | WiFi 802.11 b/g/n |
| Ultrasonic | 2 | HC-SR04 | 2-400cm, mounted at +/-15 deg |
| Stepper Motor | 2 | 28BYJ-48 | 5V, 0.1A, 2048 steps/rev |
| Motor Driver | 2 | ULN2003 | 7-channel Darlington |
| Battery | 2 | 18650 | 3.7V, 2600mAh (series = 7.4V) |
| Caster | 1 | Swivel | ~30mm diameter |

---

## 3. PIN MAPPING

### Ultrasonic Sensors

| Sensor | Pin | ESP32 GPIO |
|--------|-----|------------|
| LEFT TRIG | - | GPIO 12 |
| LEFT ECHO | - | GPIO 14 |
| RIGHT TRIG | - | GPIO 27 |
| RIGHT ECHO | - | GPIO 26 |

### Stepper Motors

| Motor | ULN2003 | ESP32 GPIO |
|-------|---------|------------|
| LEFT IN1 | Pin 1 | GPIO 19 |
| LEFT IN2 | Pin 2 | GPIO 21 |
| LEFT IN3 | Pin 3 | GPIO 22 |
| LEFT IN4 | Pin 4 | GPIO 23 |
| RIGHT IN1 | Pin 1 | GPIO 16 |
| RIGHT IN2 | Pin 2 | GPIO 17 |
| RIGHT IN3 | Pin 3 | GPIO 5 |
| RIGHT IN4 | Pin 4 | GPIO 18 |

### Battery ADC

| Function | ESP32 GPIO | Notes |
|----------|------------|-------|
| Voltage | GPIO 34 | Via 10k/10k divider |

---

## 4. WIRING DIAGRAM

```
                    +-------+
                    | 18650 |
                    | 3.7V  |
                    +---+---+
                        |
                    +---+---+
                    | 18650 |
                    | 3.7V  |
                    +---+---+
                        |
         +--------------+---------------+
         |              |               |
        GND          7.4V            +---+
         |              |            |10k|
         |         +----+----+       +---+
         |         |  5V     |         |
         |      [ULN2003] [ULN2003]  GPIO34
         |         (L)       (R)       |
         |                           +---+
         |    [28BYJ-48] [28BYJ-48]  |10k|
         |                           +---+
         +-------+-------------------+--+
                 |                      |
                GND                    GND

              +-----------+
              |   ESP32   |
              |  DevKit   |
              |   WiFi    |
              +-----------+
              |           |
         +----+           +----+
         |                     |
    [HC-SR04 L]           [HC-SR04 R]
      -15 deg               +15 deg
```

---

## 5. WIFI CONFIGURATION

### ESP32 Access
- **WebSocket Port:** 81
- **Protocol:** JSON over WebSocket

### Saved Networks (configurable)
```
Slot 0: SWARM_HOTSPOT / swarm2026
Slot 1: [your network]
Slot 2: [your network]
```

### FTP Server (PC/Phone side)
- **Port:** 2222
- **Login:** esprobot
- **Password:** kamil90@
- **Purpose:** Receive CSV logs from ESP32

---

## 6. COMMUNICATION PROTOCOL

### ESP32 -> Python (WebSocket)

```json
// Sensor data (every 50ms)
{
  "type": "sensors",
  "dist_left": 120.5,
  "dist_right": 89.2,
  "dist_front": 104.8,
  "battery_v": 7.4,
  "battery_pct": 50,
  "wifi": true,
  "ftp": true
}

// Scan complete
{
  "type": "scan_result",
  "min_left": 45.2,
  "min_left_angle": -20,
  "min_front": 78.5,
  "min_right": 123.0,
  "min_right_angle": 15,
  "recommendation": "TURN_LEFT"
}

// Alert
{
  "type": "alert",
  "message": "BATTERY_CRITICAL",
  "battery_v": 6.3
}

// Status
{
  "type": "status",
  "ip": "192.168.1.105",
  "wifi": true,
  "ftp_server": "192.168.1.100",
  "ftp_available": true,
  "wheel_diameter_mm": 65.0,
  "wheel_width_mm": 26.0
}
```

### Python -> ESP32 (WebSocket)

```json
// Movement command
{
  "type": "command",
  "action": "FORWARD",
  "speed_left": 100,
  "speed_right": 100
}

// Actions: FORWARD, TURN_LEFT, TURN_RIGHT, STOP, ESCAPE, SCAN

// Configure WiFi
{
  "type": "config",
  "ssid": "MyNetwork",
  "password": "mypassword",
  "slot": 1
}

// Trigger FTP scan
{
  "type": "ftp_scan"
}
```

---

## 7. CONNECTION FLOW

```
1. ESP32 boots
   |
2. Scan saved WiFi networks
   |
3. Connect to first available
   |
4. Start WebSocket server (port 81)
   |
5. Scan network for FTP server (port 2222)
   |
6. If FTP found: enable log upload
   |
7. Wait for WebSocket client
   |
8. Send sensor data every 50ms
   |
9. Process commands
   |
10. Upload logs to FTP every 5 minutes
```

---

## 8. SCAN MODE OPERATION

```
1. Receive SCAN command
2. STOP robot
3. Read center position (0 deg)
4. Rotate RIGHT 30 deg (continuous scan)
   - 15 samples at 2 deg intervals
5. Return to CENTER
6. Rotate LEFT 30 deg (continuous scan)
   - 15 samples at 2 deg intervals
7. Return to CENTER
8. Calculate obstacle map
9. Send scan_result with recommendation
```

---

## 9. BATTERY MONITORING

### Voltage Levels (2S Li-ion)

| State | Voltage | Percent | Action |
|-------|---------|---------|--------|
| Full | 8.4V | 100% | Normal |
| Nominal | 7.4V | 50% | Normal |
| Low | 6.8V | 20% | Warning |
| Critical | 6.4V | 0% | Emergency stop |

### ADC Calculation

```
V_battery = ADC_voltage x 2.0 (10k/10k divider)
ADC_voltage = (ADC_raw / 4095) x 3.6V
```

---

## 10. STEPPER MOTOR CALCULATIONS

### 28BYJ-48 Specs
- Steps per revolution: 2048 (with 64:1 gear)
- Step angle: 0.176 deg

### Movement Formulas

```python
# Wheel circumference
circumference = 65 * 3.14159 = 204.2 mm

# Steps per mm
steps_per_mm = 2048 / 204.2 = 10.03 steps/mm

# To move 100mm forward:
steps = 100 * 10.03 = 1003 steps

# To rotate robot 90 degrees:
# Arc = wheel_base * angle * pi / 180
arc_mm = 120 * 90 * 3.14159 / 180 = 188.5 mm
steps = 188.5 * 10.03 = 1891 steps per wheel
```

---

## 11. LOG FILE FORMAT

### Filename Pattern
- Simulation: `train_sim_YYYYMMDD_HHMMSS.csv`
- ESP32 Live: `train_live_XXXXXXX.csv` (timestamp in ms)

### CSV Columns
```
timestamp,dist_left,dist_right,speed_left,speed_right,action,battery
```

### Example
```csv
timestamp,dist_left,dist_right,speed_left,speed_right,action,battery
123456789,120.5,89.2,100,100,FORWARD,7.42
123456839,115.3,92.1,100,100,FORWARD,7.41
123456889,45.2,95.8,60,120,TURN_LEFT,7.41
```

---

## 12. PYDROID3 SETUP

### Required Files
1. `swarm_wifi.py` - WiFi controller
2. `swarm_unified_core.py` - Decision engine

### Usage on Android
```python
from swarm_wifi import SwarmWiFiController
from swarm_unified_core import SwarmCoreController, DataSource

# Start WiFi controller
wifi = SwarmWiFiController()
wifi.start()

# Start decision engine
core = SwarmCoreController(source=DataSource.ESP32_LIVE)

# Main loop
while True:
    sensors = wifi.get_sensors()
    if sensors:
        decision = core.process_sensors(
            dist_front=sensors.get('dist_front', 200),
            dist_left=sensors.get('dist_left', 200),
            dist_right=sensors.get('dist_right', 200)
        )
        wifi.send_action(
            decision['action'],
            decision['speed_left'],
            decision['speed_right']
        )
    time.sleep(0.05)
```

---

## 13. TROUBLESHOOTING

### ESP32 not found
1. Check if ESP32 and PC/phone are on same network
2. Verify WiFi credentials in ESP32 (Serial monitor)
3. Try manual IP: `controller = SwarmWiFiController(esp32_ip="192.168.x.x")`

### FTP upload fails
1. Check FTP server is running on PC/phone
2. Verify port 2222 is open
3. Check credentials: esprobot / kamil90@

### Motors not moving
1. Check ULN2003 power (5V)
2. Verify GPIO connections
3. Test with Serial commands

### Battery issues
1. Verify voltage divider (should read ~half of battery voltage)
2. Check low battery threshold (6.8V)

---

*SWARM Project - Behavioral AI Robot*
