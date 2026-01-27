# SWARM ROBOT - KOMPLEKSOWA ANALIZA PROBLEMÓW
**Data:** 2026-01-27
**Wersja:** 2.0 CRITICAL AUDIT
**Status:** 🔴 WYKRYTO POWAŻNE NIESPÓJNOŚCI

---

## 📋 SPIS TREŚCI
1. [Odwrócone Logiki Kierunków](#1-odwrócone-logiki-kierunków)
2. [Problemy w Manewrach Awaryjnych](#2-problemy-w-manewrach-awaryjnych)
3. [Uśpiony Online Learning (OL)](#3-uśpiony-online-learning-ol)
4. [Uśpiony Behavioral Like Learning (BLL)](#4-uśpiony-behavioral-like-learning-bll)
5. [Chaos Parameter & Lorenz - Problemy](#5-chaos-parameter--lorenz---problemy)
6. [Niespójności w Danych Treningowych](#6-niespójności-w-danych-treningowych)
7. [Propozycje Naprawy](#7-propozycje-naprawy)

---

## 1. ODWRÓCONE LOGIKI KIERUNKÓW

### 🔴 PROBLEM GŁÓWNY: Niespójność w definicji skrętu

#### Lokalizacja 1: `swarm_core.py` - Linie 252-315
**Deklarowana konwencja:**
```python
# DIRECTION CONVENTION:
# - TURN_LEFT: Left wheel SLOWER, Right wheel FASTER = turn LEFT
# - TURN_RIGHT: Left wheel FASTER, Right wheel SLOWER = turn RIGHT
```

**Rzeczywistość w kodzie:**
```python
# LEFT obstacle/wall → turn RIGHT (escape to the right)
if 'LEFT_WALL' in concept_upper or 'LEFT_OBSTACLE' in concept_upper:
    return (ActionType.TURN_RIGHT.value, 140.0, 40.0)
    # ⚠️ Left=140, Right=40 → RIGHT wheel SLOWER = turns RIGHT
    # ✅ ZGODNE z deklaracją

# RIGHT obstacle/wall → turn LEFT (escape to the left)
if 'RIGHT_WALL' in concept_upper or 'RIGHT_OBSTACLE' in concept_upper:
    return (ActionType.TURN_LEFT.value, 40.0, 140.0)
    # ⚠️ Left=40, Right=140 → LEFT wheel SLOWER = turns LEFT
    # ✅ ZGODNE z deklaracją
```

**WNIOSEK:** Konwencja jest POPRAWNA, ale...

---

#### Lokalizacja 2: `swarm_core.py` - Linie 481-574 (rule_based_decision)
**Znalezione problemy:**

```python
# Side collision - RIGHT side too close → TURN LEFT (escape left)
if d_r < SIDE_CRITICAL:
    return (ActionType.TURN_LEFT.value, 40.0, 140.0, "SIDE_COLLISION_RIGHT")
    # ⚠️ PROBLEM: RIGHT blocked → turn LEFT
    # To oznacza: zbliżamy się do PRAWEJ ściany, więc uciekamy w LEWO
    # Speeds: L=40, R=140 → LEFT slower = robot turns LEFT
    # ✅ LOGIKA POPRAWNA

# LEFT side too close → TURN RIGHT (escape right)
if d_l < SIDE_CRITICAL:
    return (ActionType.TURN_RIGHT.value, 140.0, 40.0, "SIDE_COLLISION_LEFT")
    # ⚠️ PROBLEM: LEFT blocked → turn RIGHT
    # Speeds: L=140, R=40 → RIGHT slower = robot turns RIGHT
    # ✅ LOGIKA POPRAWNA
```

**ALE ZOBACZ TO:**
```python
# Front very close - linie 514-518
if d_f < 0.25:
    if d_l > d_r:  # MORE space on LEFT
        return (ActionType.TURN_LEFT.value, 30.0, 130.0, "EMERGENCY_BRAKE_LEFT")
        # ⚠️ MORE space LEFT → turn LEFT
        # To jest POPRAWNE - skręcamy w stronę wolnej przestrzeni

    else:  # MORE space on RIGHT
        return (ActionType.TURN_RIGHT.value, 130.0, 30.0, "EMERGENCY_BRAKE_RIGHT")
        # ⚠️ MORE space RIGHT → turn RIGHT
        # ✅ POPRAWNE
```

**JEDNAK:**
```python
# Danger zone - linie 521-526
if d_f < danger_threshold:
    if d_l > d_r:  # MORE space LEFT
        return (ActionType.TURN_LEFT.value, 40.0, 110.0, "AVOID_FRONT_LEFT")
        # ✅ POPRAWNE

    else:  # MORE space RIGHT
        return (ActionType.TURN_RIGHT.value, 110.0, 40.0, "AVOID_FRONT_RIGHT")
        # ✅ POPRAWNE
```

**PROBLEM - Linie 563-567:**
```python
# Asymmetric - seek space
if abs(d_l - d_r) > 0.15:
    if d_l > d_r:  # MORE space LEFT
        return (ActionType.FORWARD.value, 80.0, 130.0, "SEEK_SPACE_LEFT")
        # ⚠️⚠️⚠️ WAIT! This is FORWARD but with asymmetric speeds
        # Left=80, Right=130 → LEFT slower = turns LEFT while moving forward
        # ✅ POPRAWNE - gentle correction towards open space

    else:  # MORE space RIGHT
        return (ActionType.FORWARD.value, 130.0, 80.0, "SEEK_SPACE_RIGHT")
        # ✅ POPRAWNE
```

---

### 🟡 ZNALEZIONY PROBLEM: Avoidance Maneuver Logic

#### Lokalizacja: `swarm_core.py` - Linie 691-726

```python
def _start_avoidance_maneuver(self, dl, dr):
    """Start 'Turn to Free' maneuver with hysteresis"""

    # Logic: Turn towards the larger value (Free space)
    if dl < dr:
        # Left blocked -> Turn Right
        action = ActionType.TURN_RIGHT.value  # ✅ CORRECT
        target_sensor_start = dr
        blocked_sensor = 'left'
    else:
        # Right blocked -> Turn Left
        action = ActionType.TURN_LEFT.value   # ✅ CORRECT
        target_sensor_start = dl
        blocked_sensor = 'right'
```

**Analiza:**
- `dl < dr` → Left is SMALLER (more blocked) → Turn RIGHT (towards free RIGHT space) ✅
- `dl > dr` → Right is SMALLER (more blocked) → Turn LEFT (towards free LEFT space) ✅

**WNIOSEK:** Logika POPRAWNA!

---

#### 🔴 KRYTYCZNY PROBLEM: Linie 773-788

```python
elif m['type'] == 'AVOIDANCE_TURN':
    action = m['action']

    # Determine success metric
    # If turning Right, we watch Right sensor (free space)?
    # Or assume we watch the sensor we are turning TOWARDS.

    current_target_val = dr if action == ActionType.TURN_RIGHT.value else dl
    # ⚠️⚠️⚠️ PROBLEM!

    # If action == TURN_RIGHT:
    #   - We are turning RIGHT because LEFT was blocked
    #   - We want to escape to the RIGHT
    #   - So we should monitor RIGHT sensor (dr)
    #   - current_target_val = dr ✅ CORRECT

    # If action == TURN_LEFT:
    #   - We are turning LEFT because RIGHT was blocked
    #   - We want to escape to the LEFT
    #   - So we should monitor LEFT sensor (dl)
    #   - current_target_val = dl ✅ CORRECT

    improvement = current_target_val - m['start_target_val']
```

**WNIOSEK:** Ta logika jest POPRAWNA! Monitorujemy sensor w kierunku którego się obracamy.

---

## 2. PROBLEMY W MANEWRACH AWARYJNYCH

### 🔴 PROBLEM: Emergency Escape Direction Selection

#### Lokalizacja: `swarm_core.py` - Linia 668

```python
def _start_emergency_maneuver(self, dl, dr):
    """Start 'Back up and Align' maneuver"""
    # Determine best turn direction (towards open space)
    turn_dir = ActionType.TURN_RIGHT.value if dl < dr else ActionType.TURN_LEFT.value
    # ⚠️⚠️⚠️ ANALIZA:

    # If dl < dr:
    #   - LEFT sensor shows SMALLER distance (more blocked)
    #   - RIGHT sensor shows LARGER distance (more open)
    #   - Decision: turn_dir = TURN_RIGHT
    #   - ✅ CORRECT - turn towards open space

    # If dl > dr:
    #   - LEFT sensor shows LARGER distance (more open)
    #   - RIGHT sensor shows SMALLER distance (more blocked)
    #   - Decision: turn_dir = TURN_LEFT
    #   - ✅ CORRECT - turn towards open space
```

**WNIOSEK:** Logika POPRAWNA!

---

### 🔴 PROBLEM: Execution speeds - Linia 755

```python
# Continue turning
action = m['turn_dir']
spd_l, spd_r = (40, 120) if action == ActionType.TURN_RIGHT.value else (120, 40)
# ⚠️ ANALIZA:

# If action == TURN_RIGHT:
#   spd_l=40, spd_r=120
#   RIGHT wheel FASTER = robot turns RIGHT ✅ CORRECT

# If action == TURN_LEFT:
#   spd_l=120, spd_r=40
#   LEFT wheel FASTER = robot turns LEFT ✅ CORRECT
```

**WNIOSEK:** Speeds POPRAWNE!

---

### 🟡 JEDNAK JEST PROBLEM: Linia 787

```python
# Continue turning
spd_l, spd_r = (40, 120) if action == ActionType.TURN_RIGHT.value else (120, 40)
# ⚠️⚠️⚠️ CZEKAJ! To jest DOKŁADNIE TO SAMO co w linii 755!
# Ale w kontekście AVOIDANCE_TURN używamy zmiennej `action` z maneuveru

# PROBLEM: czy `action` w tym kontekście to:
# - ActionType.TURN_RIGHT.value (string "TURN_RIGHT")
# - czy po prostu string zapisany wcześniej?

# Sprawdzam linię 721-722:
# self.current_maneuver = {
#     'type': 'AVOIDANCE_TURN',
#     'action': action,  # <-- to jest string "TURN_LEFT" lub "TURN_RIGHT"
# }

# ✅ OK, więc porównanie działa poprawnie
```

---

## 3. UŚPIONY ONLINE LEARNING (OL)

### 🔴 KRYTYCZNY PROBLEM: OL NIE JEST UŻYWANY!

#### Dowód 1: Inicjalizacja istnieje
```python
# swarm_core.py linia 338
self.ol_vectors = {}
```

#### Dowód 2: Ładowanie działa
```python
# swarm_core.py linie 447-454
try:
    if os.path.exists(ol_path):
        with open(ol_path, 'r') as f:
            data = json.load(f)
        self.ol_vectors = {k: np.array(v) for k, v in data.items()}
        logger.info(f"Loaded OL vectors: {len(self.ol_vectors)} words")
except Exception as e:
    logger.warning(f"Failed to load OL: {e}")
```

#### Dowód 3: Zapisywanie działa
```python
# swarm_core.py linie 468-470
ol_data = {k: v.tolist() for k, v in self.ol_vectors.items()}
with open(ol_path, 'w') as f:
    json.dump(ol_data, f, indent=2)
```

### ⚠️ ALE NIGDZIE NIE MA:
1. ❌ Dodawania nowych wektorów do `self.ol_vectors`
2. ❌ Używania `self.ol_vectors` w decision logic
3. ❌ Aktualizacji `self.ol_vectors` na podstawie feedbacku
4. ❌ Porównywania sensor_vector z `self.ol_vectors`

### 💡 CO POWINNO BYĆ:

```python
def decide(self, dist_front, dist_left, dist_right, ...):
    # ... existing code ...

    # NPZ matching
    concept, similarity, category = self.npz.find_best_match(sensor_vec)

    # 🆕 OL MATCHING (should be added)
    if self.ol_vectors:
        ol_concept, ol_sim = self._match_ol_vectors(sensor_vec)

        # Combine NPZ + OL
        if ol_sim > similarity:
            concept = ol_concept
            similarity = ol_sim
            source = 'OL'

    # ... rest of code ...
```

```python
def feedback(self, success: bool, context: Dict = None):
    """Provide feedback for learning"""
    # ... existing BLL code ...

    # 🆕 OL UPDATE (should be added)
    if success and self.last_sensor_vec is not None:
        # Add/update vector in OL database
        concept_key = self.last_decision.get('concept', 'unknown')

        if concept_key not in self.ol_vectors:
            self.ol_vectors[concept_key] = self.last_sensor_vec
        else:
            # Update with exponential moving average
            alpha = 0.2
            self.ol_vectors[concept_key] = (
                alpha * self.last_sensor_vec +
                (1 - alpha) * self.ol_vectors[concept_key]
            )
```

---

## 4. UŚPIONY BEHAVIORAL LIKE LEARNING (BLL)

### 🟡 CZĘŚCIOWO DZIAŁA, ALE MA PROBLEMY

#### ✅ Co działa:
```python
# swarm_core.py linie 334-336
self.bll_weights = {}
self.bll_history = deque(maxlen=config.memory_size)

# Linie 618-620 - BLL boost jest używany!
bll_boost = self.bll_weights.get(category, 1.0)
adjusted_sim = similarity * bll_boost
```

#### ⚠️ Co NIE działa:
1. **Feedback nie jest wywoływany automatycznie**
```python
# swarm_core.py linie 804-822
def feedback(self, success: bool, category: str = None):
    # ... kod istnieje ...
    # ❌ ALE NIGDZIE NIE MA AUTOMATYCZNEGO WYWOŁANIA!
```

2. **W swarm_main.py brak feedback loop**
```python
# Szukam w swarm_main.py...
# ❌ BRAK wywołania core.feedback() w głównej pętli!
```

3. **Brak success detection**
```python
# Co oznacza "success"?
# - Robot osiągnął cel?
# - Uniknął kolizji?
# - Poruszył się forward bez problemów?
#
# ❌ BRAK logiki określającej czy akcja była udana!
```

### 💡 CO POWINNO BYĆ:

```python
# W swarm_main.py - główna pętla

while running:
    # Get sensors
    sensor_data = data_source.read_sensors()

    # Make decision
    decision = core.decide(**sensor_data)

    # Execute
    actuator.execute(
        decision['action'],
        decision['speed_left'],
        decision['speed_right']
    )

    # 🆕 WAIT and evaluate success
    time.sleep(0.3)
    new_sensors = data_source.read_sensors()

    # 🆕 SUCCESS DETECTION
    success = evaluate_action_success(
        old_sensors=sensor_data,
        new_sensors=new_sensors,
        action=decision['action']
    )

    # 🆕 FEEDBACK
    core.feedback(success=success)
```

---

## 5. CHAOS PARAMETER & LORENZ - PROBLEMY

### 🟡 DZIAŁA, ALE...

#### ✅ Co działa:
```python
# swarm_core.py linie 370-390
def _lorenz_step(self) -> Tuple[float, float, float]:
    """Full Lorenz attractor step"""
    # ... implementation is CORRECT ...
    # ✅ Matematyka Lorenza jest poprawna

# Linie 392-405
def _chaos_blend_action(self, base_action, base_speeds, chaos_vec):
    # ... blending logic exists ...
    # ✅ Chaos jest mieszany z akcjami
```

#### ⚠️ PROBLEMY:

1. **Chaos Level = 0.5 to DUŻO!**
```python
# HARDWARE_CONFIG.py - brak ustawienia chaos_level
# swarm_core.py linia 89
chaos_level: float = 0.5  # ⚠️ 50% chaos influence!

# Linia 398
intensity = abs(cz) * self.config.chaos_level * 0.5
# Final intensity = abs(cz) * 0.5 * 0.5 = abs(cz) * 0.25
# To wciąż może dawać ±20mm speed variation!
```

2. **Chaos może powodować oscylacje**
```python
# Linia 399
direction_blend = cx * 20 * intensity
# cx ∈ [-1, 1] (normalized Lorenz X)
# intensity ∈ [0, 0.25] (max)
# direction_blend ∈ [-5, +5] (max)

# Linie 402-403
new_speed_l = max(0, min(150, speed_l * speed_modifier + direction_blend))
new_speed_r = max(0, min(150, speed_r * speed_modifier - direction_blend))

# ⚠️ PROBLEM: Znak +/- może wprowadzać przypadkowe skręty!
# Jeśli base action = FORWARD (100, 100):
#   - direction_blend = +5
#   - new_speed_l = 105, new_speed_r = 95
#   - Robot skręca lekko w PRAWO (unexpected!)
```

3. **Chaos w manewrach awaryjnych?**
```python
# swarm_core.py linia 613
chaos_vec = self._lorenz_step()

# Linia 634-636
blended_action, blended_spd_l, blended_spd_r = self._chaos_blend_action(
    action, (spd_l, spd_r), chaos_vec
)

# ⚠️ Chaos jest aplikowany TYLKO w standardowej decyzji (linia 605)
# ✅ DOBRZE - manewry awaryjne (linie 590-601) NIE mają chaosu
```

### 💡 REKOMENDACJE:

```python
# 1. Zmniejsz chaos_level
chaos_level: float = 0.15  # Zamiast 0.5

# 2. Wyłącz chaos gdy robot jest blisko przeszkód
if min(dist_front, dist_left, dist_right) < 150.0:
    chaos_vec = (0.0, 0.0, 0.0)  # Disable chaos in danger

# 3. Aplikuj chaos tylko do forward movement
if action == ActionType.FORWARD.value:
    apply_chaos = True
else:
    chaos_vec = (0.0, 0.0, 0.0)
```

---

## 6. NIESPÓJNOŚCI W DANYCH TRENINGOWYCH

### 📊 Analiza CSV: train_sim_20260127_064742.csv

#### Obserwacje:

1. **Cykle 16-30: Avoidance Turn sequence**
```
Cycle 16: dist_left=233.8, dist_right=200.0 → TURN_LEFT
Cycles 17-29: Continuous TURN_LEFT with (120, 40)
Cycle 30: dist_left=390.0, dist_right=196.3 → FORWARD
```

**Analiza:**
- Left increasing: 233.8 → 390.0 (improvement +156mm)
- Right decreasing: 200.0 → 196.3
- Decision: TURN_LEFT was towards MORE OPEN space (left)
- ✅ LOGIKA POPRAWNA

2. **Powtarzające się wzorce:**
```
Pattern: FORWARD → TURN_LEFT → FORWARD → TURN_LEFT → ...
```

**Problem:**
- Robot seems stuck in left-turning pattern
- Może to oznaczać:
  - Oscylację w wąskim korytarzu
  - Preference dla skrętu w lewo (bias)
  - Brak property diversification w decisions

---

## 7. PROPOZYCJE NAPRAWY

### 🔧 PRIORYTET 1: Ujednolicenie i dokumentacja kierunków

#### Plik: `swarm_core.py`

```python
# ============================================================================
# DIRECTION CONVENTION - UNIFIED REFERENCE
# ============================================================================
#
# PHYSICAL ROBOT BEHAVIOR:
# ------------------------
# - TURN_LEFT:  Left motor SLOWER, Right motor FASTER
#               Example: (40, 120) → Robot body rotates LEFT (counter-clockwise)
#
# - TURN_RIGHT: Left motor FASTER, Right motor SLOWER
#               Example: (120, 40) → Robot body rotates RIGHT (clockwise)
#
# OBSTACLE AVOIDANCE LOGIC:
# -------------------------
# - LEFT obstacle detected  → Turn RIGHT (escape right)
# - RIGHT obstacle detected → Turn LEFT (escape left)
# - FRONT obstacle detected → Turn towards more open side
#
# SENSOR COMPARISON:
# ------------------
# - if dist_left < dist_right:  LEFT is more blocked → Turn RIGHT
# - if dist_left > dist_right:  RIGHT is more blocked → Turn LEFT
#
# ============================================================================
```

---

### 🔧 PRIORYTET 2: Aktywacja Online Learning

#### Plik: `swarm_core.py` - Dodaj metodę:

```python
def _match_ol_vectors(self, sensor_vec: np.ndarray) -> Tuple[str, float]:
    """
    Match sensor vector against OL database

    Returns:
        (concept, similarity)
    """
    if not self.ol_vectors:
        return ("", 0.0)

    best_concept = ""
    best_sim = 0.0

    # Normalize sensor vector
    norm = np.linalg.norm(sensor_vec)
    if norm > 0:
        sensor_vec_norm = sensor_vec / norm
    else:
        return ("", 0.0)

    # Find best match
    for concept, vec in self.ol_vectors.items():
        # Normalize OL vector
        vec_norm = np.linalg.norm(vec)
        if vec_norm > 0:
            vec_normalized = vec / vec_norm
            similarity = np.dot(sensor_vec_norm, vec_normalized)

            if similarity > best_sim:
                best_sim = similarity
                best_concept = concept

    return (best_concept, float(best_sim))
```

#### Modyfikacja `decide()` - Linia 616:

```python
# NPZ matching
npz_concept, npz_similarity, category = self.npz.find_best_match(sensor_vec)

# 🆕 OL matching
ol_concept, ol_similarity = self._match_ol_vectors(sensor_vec)

# Choose best source
if ol_similarity > npz_similarity and ol_similarity > 0.6:
    concept = ol_concept
    similarity = ol_similarity
    source = 'OL'
    logger.debug(f"Using OL: {concept} (sim={similarity:.2f})")
else:
    concept = npz_concept
    similarity = npz_similarity
    source = 'NPZ'

# Rest of existing code...
```

#### Modyfikacja `feedback()` - Linia 804:

```python
def feedback(self, success: bool, category: str = None):
    """Provide feedback for BLL + OL learning"""

    # Existing BLL code...
    if category is None and self.last_decision:
        category = self.last_decision.get('category', 'unknown')

    if category:
        current = self.bll_weights.get(category, 1.0)
        delta = self.config.learning_rate if success else -self.config.learning_rate
        self.bll_weights[category] = max(0.5, min(1.5, current + delta))

        self.bll_history.append({
            'time': datetime.now().isoformat(),
            'category': category,
            'success': success,
            'weight': self.bll_weights[category]
        })

    # 🆕 OL UPDATE
    if self.last_sensor_vec is not None and self.last_decision:
        concept_key = self.last_decision.get('concept', 'unknown')

        if success:
            # Reinforce vector
            if concept_key not in self.ol_vectors:
                # New concept - add it
                self.ol_vectors[concept_key] = self.last_sensor_vec.copy()
                logger.info(f"OL: Added new concept '{concept_key}'")
            else:
                # Update existing with EMA
                alpha = 0.15  # Learning rate for vector update
                self.ol_vectors[concept_key] = (
                    alpha * self.last_sensor_vec +
                    (1 - alpha) * self.ol_vectors[concept_key]
                )
        else:
            # Unsuccessful - decrease confidence or remove if consistently bad
            if concept_key in self.ol_vectors:
                # Decay the vector slightly
                self.ol_vectors[concept_key] *= 0.95

                # Remove if vector becomes too small
                if np.linalg.norm(self.ol_vectors[concept_key]) < 0.1:
                    del self.ol_vectors[concept_key]
                    logger.info(f"OL: Removed unreliable concept '{concept_key}'")

    # Save periodically
    if len(self.bll_history) % 20 == 0 or not success:
        self.save_learning_data()
```

---

### 🔧 PRIORYTET 3: Automatyczny Feedback Loop

#### Plik: `swarm_main.py` - Dodaj funkcję success detection:

```python
def evaluate_action_success(
    old_sensors: Dict[str, float],
    new_sensors: Dict[str, float],
    action: str,
    min_improvement: float = 10.0
) -> bool:
    """
    Evaluate if last action was successful

    Success criteria:
    - FORWARD: Front distance didn't decrease significantly
    - TURN_LEFT/RIGHT: Turned towards more open space
    - ESCAPE: Got away from danger zone
    - STOP: Stayed safe

    Args:
        old_sensors: Sensor state before action
        new_sensors: Sensor state after action
        action: Action that was executed
        min_improvement: Minimum distance improvement (mm)

    Returns:
        True if action was successful
    """
    old_f = old_sensors.get('dist_front', 400)
    old_l = old_sensors.get('dist_left', 400)
    old_r = old_sensors.get('dist_right', 400)

    new_f = new_sensors.get('dist_front', 400)
    new_l = new_sensors.get('dist_left', 400)
    new_r = new_sensors.get('dist_right', 400)

    # Check for collision
    if new_f < 40 or new_l < 40 or new_r < 40:
        return False  # Too close = failure

    # Action-specific evaluation
    if action == "FORWARD":
        # Success if maintained or improved front clearance
        return new_f >= (old_f - 20)  # Allow small decrease

    elif action == "TURN_LEFT":
        # Success if left space improved or maintained
        improvement = new_l - old_l
        return improvement >= -10  # Allow small decrease

    elif action == "TURN_RIGHT":
        # Success if right space improved or maintained
        improvement = new_r - old_r
        return improvement >= -10

    elif action == "ESCAPE" or action == "REVERSE":
        # Success if got away from immediate danger
        min_old = min(old_f, old_l, old_r)
        min_new = min(new_f, new_l, new_r)
        return min_new > min_old  # Any improvement is good

    elif action == "STOP":
        # Success if maintained safe distance
        return min(new_f, new_l, new_r) > 60

    # Default: check if robot is in better state
    old_min = min(old_f, old_l, old_r)
    new_min = min(new_f, new_l, new_r)
    return new_min >= old_min
```

#### Modyfikacja głównej pętli w `SwarmCoreController`:

```python
def run_control_loop(self, max_cycles: int = None):
    """Main control loop with automatic feedback"""

    cycle = 0
    last_sensors = None
    last_decision = None

    try:
        while self.running:
            if max_cycles and cycle >= max_cycles:
                break

            # 1. Read sensors
            sensor_data = self.data_source.read_sensors()
            if not sensor_data:
                time.sleep(0.1)
                continue

            # 2. Provide feedback for last decision
            if last_sensors and last_decision:
                success = evaluate_action_success(
                    old_sensors=last_sensors,
                    new_sensors=sensor_data,
                    action=last_decision['action']
                )

                self.core.feedback(success=success)

                if not success:
                    logger.warning(f"Action {last_decision['action']} was unsuccessful")

            # 3. Make new decision
            decision = self.core.decide(**sensor_data)

            # 4. Execute
            self.actuator.execute(
                decision['action'],
                decision['speed_left'],
                decision['speed_right']
            )

            # 5. Log
            if self.logger:
                self.logger.log_decision(sensor_data, decision)

            # 6. Remember for next cycle
            last_sensors = sensor_data.copy()
            last_decision = decision

            cycle += 1
            time.sleep(0.05)

    except KeyboardInterrupt:
        logger.info("Stopped by user")
    finally:
        # Final save
        self.core.save()
```

---

### 🔧 PRIORYTET 4: Chaos Reduction & Safety

#### Plik: `swarm_core.py` - Modyfikuj `SwarmConfig`:

```python
@dataclass
class SwarmConfig:
    # ... existing fields ...

    # ABSR settings - UPDATED
    lorenz_sigma: float = 10.0
    lorenz_rho: float = 28.0
    lorenz_beta: float = 8.0 / 3.0
    chaos_level: float = 0.15  # 🔧 REDUCED from 0.5 to 0.15
    chaos_enabled: bool = True  # 🆕 Allow disabling chaos
    chaos_min_safe_distance: float = 120.0  # 🆕 Disable chaos when too close
```

#### Modyfikuj `decide()` - chaos application:

```python
def decide(self, ...):
    # ... existing code until line 613 ...

    # Lorenz chaos - CONDITIONAL
    if (self.config.chaos_enabled and
        min(dist_front, dist_left, dist_right) > self.config.chaos_min_safe_distance):
        chaos_vec = self._lorenz_step()
    else:
        chaos_vec = (0.0, 0.0, 0.0)  # Disable chaos in danger

    # ... rest of code ...

    # Apply chaos ONLY to FORWARD actions
    if action == ActionType.FORWARD.value:
        blended_action, blended_spd_l, blended_spd_r = self._chaos_blend_action(
            action, (spd_l, spd_r), chaos_vec
        )
    else:
        # No chaos for turns/stops/escapes
        blended_action = action
        blended_spd_l = spd_l
        blended_spd_r = spd_r
```

---

### 🔧 PRIORYTET 5: Anti-Oscillation Enhancement

#### Plik: `swarm_core.py` - Strengthen oscillation detection:

```python
def __init__(self, config: SwarmConfig, npz_engine: NPZEngine):
    # ... existing code ...

    # 🆕 Enhanced direction memory
    self.direction_memory = deque(maxlen=20)
    self.last_turn_direction = None
    self.turn_streak = 0
    self.preferred_escape_direction = None
    self.oscillation_detected = False  # 🆕
    self.consecutive_direction_changes = 0  # 🆕
```

#### Dodaj metodę wykrywania oscylacji:

```python
def _detect_oscillation(self) -> bool:
    """
    Detect if robot is oscillating between directions

    Returns:
        True if oscillation detected
    """
    if len(self.direction_memory) < 6:
        return False

    # Get last 6 decisions
    recent = list(self.direction_memory)[-6:]

    # Pattern 1: L-R-L-R-L-R
    pattern1 = ['LEFT', 'RIGHT', 'LEFT', 'RIGHT', 'LEFT', 'RIGHT']
    pattern2 = ['RIGHT', 'LEFT', 'RIGHT', 'LEFT', 'RIGHT', 'LEFT']

    if recent == pattern1 or recent == pattern2:
        logger.warning("⚠️ Oscillation detected: Alternating L-R pattern")
        return True

    # Pattern 2: More than 3 direction changes in 6 moves
    changes = sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])
    if changes >= 4:
        logger.warning(f"⚠️ Oscillation detected: {changes} direction changes in 6 moves")
        return True

    return False
```

#### Modyfikuj `_start_avoidance_maneuver`:

```python
def _start_avoidance_maneuver(self, dl, dr):
    """Start 'Turn to Free' maneuver with enhanced anti-oscillation"""

    # 🆕 Check for oscillation
    if self._detect_oscillation():
        self.oscillation_detected = True

        # Force forward movement for a few cycles
        logger.info("🛡️ Anti-oscillation: Forcing FORWARD")
        return {
            'action': ActionType.FORWARD.value,
            'speed_left': 70,
            'speed_right': 70,
            'source': 'ANTI_OSCILLATION',
            'confidence': 1.0,
            'concept': 'FORCE_FORWARD'
        }

    # Logic: Turn towards the larger value (Free space)
    if dl < dr:
        action = ActionType.TURN_RIGHT.value
        target_sensor_start = dr
        blocked_sensor = 'left'
    else:
        action = ActionType.TURN_LEFT.value
        target_sensor_start = dl
        blocked_sensor = 'right'

    # Check recent turn (existing code)
    if hasattr(self, 'last_maneuver_turn'):
        if self.last_maneuver_turn != action and time.time() - self.last_maneuver_time < 2.0:
            logger.info("🛡️ Oscillation prevented: Preferring forward")
            return {
                'action': ActionType.FORWARD.value,
                'speed_left': 60,
                'speed_right': 60,
                'source': 'ANTI_OSCILLATION',
                'confidence': 1.0,
                'concept': 'HYSTERESIS_FORWARD'
            }

    # 🆕 Update direction memory
    self._update_direction_memory(action_concept='', action_type=action)

    # Start maneuver
    self.current_maneuver = {
        'type': 'AVOIDANCE_TURN',
        'action': action,
        'start_target_val': target_sensor_start,
        'blocked_side': blocked_sensor
    }

    return self._execute_maneuver_step(action, 120, 120, "AVOID_START")
```

---

## 🎯 PODSUMOWANIE

### ✅ CO DZIAŁA POPRAWNIE:
1. Konwencja kierunków (Left slower = turn left)
2. Emergency escape logic
3. Avoidance turn direction selection
4. Speed calculations dla skrętów
5. Lorenz chaos mathematics
6. BLL weights storage/loading
7. OL vectors storage/loading

### 🔴 KRYTYCZNE PROBLEMY:
1. **Online Learning (OL) nie jest używany** - mechanizm śpi
2. **BLL feedback nie jest wywoływany** - brak success detection
3. **Chaos level za wysoki** (0.5 → 0.15)
4. **Chaos aplikowany zbyt agresywnie** (także podczas skrętów)
5. **Brak automatycznego feedback loop** w main

### 🟡 PROBLEMY ŚREDNIE:
1. Możliwe oscylacje w wąskich korytarzach
2. Brak dywersyfikacji decyzji (preferuje left turn)
3. Chaos może wprowadzać niepożądane skręty
4. Brak integracji OL z NPZ matching

### 💚 PROPOZYCJE:
1. **Aktywuj OL** - dodaj matching i update logic
2. **Dodaj automatic feedback** - success evaluation w main loop
3. **Zmniejsz chaos** - 0.15 zamiast 0.5
4. **Chaos tylko dla FORWARD** - wyłącz dla turns/escapes
5. **Enhanced anti-oscillation** - wykrywanie wzorców L-R-L-R
6. **Unified documentation** - jedna reference dla kierunków

---

## 📝 NASTĘPNE KROKI

### Faza 1: Dokumentacja (30 min)
- [ ] Dodaj unified direction convention comment
- [ ] Sprawdź wszystkie miejsca z turn logic
- [ ] Ujednolić nazewnictwo (LEFT/RIGHT/blocked/free)

### Faza 2: Aktywacja OL (1-2h)
- [ ] Implement `_match_ol_vectors()`
- [ ] Integrate OL w `decide()`
- [ ] Update `feedback()` z OL logic
- [ ] Test OL learning cycle

### Faza 3: Automatic Feedback (1h)
- [ ] Implement `evaluate_action_success()`
- [ ] Modify `SwarmCoreController.run_control_loop()`
- [ ] Add success logging
- [ ] Test feedback loop

### Faza 4: Chaos Reduction (30 min)
- [ ] Update `SwarmConfig` chaos parameters
- [ ] Add conditional chaos application
- [ ] Test with/without chaos

### Faza 5: Anti-Oscillation (1h)
- [ ] Implement `_detect_oscillation()`
- [ ] Enhanced `_start_avoidance_maneuver()`
- [ ] Test oscillation detection
- [ ] Tune hysteresis parameters

### Faza 6: Testing (2-3h)
- [ ] Unit tests dla direction logic
- [ ] Integration tests z simulator
- [ ] Real robot tests (ESP32)
- [ ] Performance benchmarks

---

**Koniec raportu**
