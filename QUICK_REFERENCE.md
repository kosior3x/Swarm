# SWARM ROBOT - QUICK REFERENCE GUIDE
**Szybkie odniesienie dla logiki kierunków i decyzji**

---

## 🧭 KONWENCJA KIERUNKÓW

### Fizyczne zachowanie silników:
```
TURN_LEFT:
  - Left motor:  SLOWER  (przykład: 40)
  - Right motor: FASTER  (przykład: 120)
  - Rezultat:    Robot obraca się W LEWO ⟲

TURN_RIGHT:
  - Left motor:  FASTER  (przykład: 120)
  - Right motor: SLOWER  (przykład: 40)
  - Rezultat:    Robot obraca się W PRAWO ⟳

FORWARD:
  - Left motor:  RÓWNO   (przykład: 100)
  - Right motor: RÓWNO   (przykład: 100)
  - Rezultat:    Robot jedzie prosto ↑

REVERSE:
  - Left motor:  UJEMNE  (przykład: -100)
  - Right motor: UJEMNE  (przykład: -100)
  - Rezultat:    Robot cofa się ↓
```

---

## 🚧 LOGIKA UNIKANIA PRZESZKÓD

### Reguła podstawowa:
**Skręcaj W STRONĘ wolnej przestrzeni, UNIKAJ blokady**

### Przykłady:

#### Przypadek 1: LEFT_WALL
```
Sensor readings:
  dist_left:  50mm  ← BLOKADA!
  dist_right: 300mm ← Wolna przestrzeń

Logika:
  LEFT jest zablokowany → Uciekaj W PRAWO

Decision:
  Action: TURN_RIGHT
  Speeds: (140, 40)  ← Left FASTER = turn RIGHT
```

#### Przypadek 2: RIGHT_WALL
```
Sensor readings:
  dist_left:  300mm ← Wolna przestrzeń
  dist_right: 50mm  ← BLOKADA!

Logika:
  RIGHT jest zablokowany → Uciekaj W LEWO

Decision:
  Action: TURN_LEFT
  Speeds: (40, 140)  ← Right FASTER = turn LEFT
```

#### Przypadek 3: FRONT obstacle, more space LEFT
```
Sensor readings:
  dist_front: 80mm  ← PRZESZKODA!
  dist_left:  250mm ← Więcej miejsca
  dist_right: 120mm

Logika:
  Front blocked, dist_left > dist_right
  → Więcej miejsca po LEWEJ → Skręć W LEWO

Decision:
  Action: TURN_LEFT
  Speeds: (40, 140)
```

#### Przypadek 4: TRAPPED (wszystko blisko)
```
Sensor readings:
  dist_front: 45mm  ← BLOKADA!
  dist_left:  40mm  ← BLOKADA!
  dist_right: 38mm  ← BLOKADA!

Logika:
  Wszystko zablokowane → EMERGENCY ESCAPE

Decision:
  Action: ESCAPE (rotate in place)
  Speeds: (-100, 100)  ← Left REVERSE, Right FORWARD
```

---

## 📊 PROGI DYSTANSÓW

```
EMERGENCY:  < 60mm   → Natychmiastowa reakcja
DANGER:     < 100mm  → Aktywny unik
WARNING:    < 150mm  → Zwolnij i koryguj
SAFE:       > 200mm  → Normalny ruch
```

### Decyzje based on thresholds:

```python
if min(dist_front, dist_left, dist_right) < 60:
    → EMERGENCY (ESCAPE lub STOP)

elif dist_front < 100:
    → DANGER (Sharp turn w stronę wolnej przestrzeni)

elif dist_front < 150:
    → WARNING (Gentle turn, reduce speed)

else:
    → SAFE (Forward, full speed)
```

---

## 🎯 MANEWRY AWARYJNE

### Emergency Escape Sequence:
```
1. REVERSE (20 cycles, ~1 sekunda)
   - Cofnij się od przeszkody
   - Speeds: (-100, -100)

2. ALIGN_TURN (until safe)
   - Obróć się w stronę wolnej przestrzeni
   - Direction: Towards LARGER sensor value
   - Exit: When both sensors > 100mm

3. FORWARD
   - Wznów normalny ruch
```

### Avoidance Turn:
```
1. Detect: One side < 200mm, asymmetric (|left-right| > 20mm)

2. Turn towards FREE side:
   - if dist_left < dist_right: TURN_RIGHT
   - if dist_right < dist_left: TURN_LEFT

3. Continue until improvement ≥ 20mm OR target > 300mm

4. Exit: Resume FORWARD
```

---

## 🧠 AI DECISION FLOW

```
┌─────────────────────────────────┐
│   Read Sensors                  │
│   (dist_front, dist_left, right)│
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ Check MANEUVER active?          │
│ (Emergency/Avoidance)           │
└─Yes───┬──────────────No─────────┘
        │                    │
        ▼                    ▼
┌──────────────┐   ┌────────────────────┐
│Execute       │   │ Check EMERGENCY?   │
│Maneuver Step │   │ (< 60mm)           │
└──────────────┘   └─Yes──┬────No───────┘
                          │       │
                          ▼       ▼
                   ┌──────────┐ ┌────────────┐
                   │ Start    │ │Check AVOID?│
                   │Emergency │ │(< 200mm)   │
                   └──────────┘ └─Yes─┬─No───┘
                                      │   │
                                      ▼   ▼
                               ┌──────────┐ ┌──────────────┐
                               │Start     │ │AI Decision:  │
                               │Avoidance │ │1.Create vec  │
                               └──────────┘ │2.NPZ match   │
                                            │3.OL match    │
                                            │4.Choose best │
                                            │5.BLL boost   │
                                            │6.Add chaos   │
                                            └──────┬───────┘
                                                   │
                                                   ▼
                                            ┌──────────────┐
                                            │Execute Action│
                                            │Send to motors│
                                            └──────┬───────┘
                                                   │
                                                   ▼
                                            ┌──────────────┐
                                            │Evaluate      │
                                            │Success       │
                                            │→ Feedback    │
                                            └──────────────┘
```

---

## 🔧 PARAMETRY KONFIGURACYJNE

### SwarmConfig (swarm_core.py):
```python
# Chaos
chaos_level = 0.15              # Wpływ chaosu (0.0-1.0)
chaos_min_safe_distance = 120.0 # Wyłącz chaos gdy < 120mm

# Learning
learning_rate = 0.1             # BLL update rate
ol_learning_rate = 0.15         # OL update rate
ol_similarity_threshold = 0.6   # Min similarity dla OL

# Thresholds
danger_dist = 60.0              # Emergency threshold
warning_dist = 100.0            # Warning threshold

# Robot dimensions
robot_width = 220.0             # Width (mm)
robot_clearance = 30.0          # Safety margin
```

---

## 📈 MONITORING

### Key metrics to watch:

```python
# Get statistics
stats = core.get_stats()

print(f"Cycles: {stats['cycle_count']}")
print(f"NPZ loaded: {stats['npz_loaded']}")
print(f"BLL categories: {stats['bll_categories']}")
print(f"OL vectors: {stats['ol_vectors']}")        # Should grow!
print(f"OL usage: {stats['ol_usage_count']}")      # Should increase!
print(f"Direction: {stats['preferred_direction']}") # LEFT/RIGHT/None
```

### Success rate tracking:
```
Every 50 decisions:
  📊 Success rate: 87.3% (43/50)

Final report:
  FINAL STATISTICS:
    Total decisions: 523
    Successful: 467 (89.3%)
    Failed: 56
```

---

## 🐛 DEBUGGING

### Problemy z kierunkami?
```python
# Enable debug logging
import logging
logging.getLogger('SwarmCore').setLevel(logging.DEBUG)

# You'll see:
# "🧠 Using OL: AVOID_LEFT (sim=0.83)"
# "✅ Action FORWARD successful"
# "⚠️ Oscillation detected: Alternating L-R pattern"
```

### Test direction mapping:
```python
from swarm_core import SwarmCore

core = SwarmCore()

# Test scenario: Left wall
decision = core.decide(
    dist_front=200,
    dist_left=50,   # LEFT blocked
    dist_right=300  # RIGHT free
)

print(f"Action: {decision['action']}")  # Should be TURN_RIGHT
print(f"Speeds: L={decision['speed_left']}, R={decision['speed_right']}")
# Should be L > R (example: 140, 40)
```

---

## ✅ CHECKLIST PRZED UŻYCIEM

### Pre-flight check:
- [ ] `BEHAVIORAL_BRAIN.npz` exists
- [ ] `logs/` directory exists
- [ ] swarm_core_FIXED.py installed
- [ ] Auto-feedback added to swarm_main.py
- [ ] Test imports: `from swarm_core import SwarmCore`
- [ ] Run basic test: `python swarm_core.py`

### During operation watch for:
- [ ] Success rate > 75%
- [ ] OL vectors growing
- [ ] No oscillation warnings
- [ ] Smooth navigation
- [ ] No collisions

---

## 🆘 QUICK FIXES

### OL not learning?
```python
# Lower threshold
config.ol_similarity_threshold = 0.5  # Instead of 0.6
```

### Too many oscillations?
```python
# Increase hysteresis
# In _start_avoidance_maneuver():
if ... time.time() - self.last_maneuver_time < 3.0:  # Instead of 2.0
```

### Success rate too low?
```python
# In evaluate_action_success():
return new_f >= (old_f - 30)  # More tolerant (was -20)
```

### Chaos too random?
```python
config.chaos_level = 0.10  # Reduce further (was 0.15)
```

---

## 📚 WIĘCEJ INFO

- **Pełna analiza:** `SWARM_ANALIZA_PROBLEMOW.md`
- **Podsumowanie:** `PODSUMOWANIE_NAPRAW.md`
- **Fixed code:** `swarm_core_FIXED.py`
- **Patch:** `swarm_main_AUTO_FEEDBACK_PATCH.py`

---

**Wersja:** 2.1
**Data:** 2026-01-27
**Quick reference for:** SWARM Robot Navigation System
