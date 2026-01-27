# SWARM ROBOT - MIGRATION GUIDE
**Przewodnik wdrożenia poprawek krok po kroku**

---

## 🎯 CEL

Zaktualizuj system SWARM z wersji 2.0 do 2.1 z następującymi ulepszeniami:
- ✅ Aktywny Online Learning (OL)
- ✅ Automatyczny feedback dla BLL
- ✅ Zmniejszony i conditional chaos
- ✅ Enhanced anti-oscillation
- ✅ Ulepszona komunikacja WiFi/Serial

---

## ⏱️ CZAS POTRZEBNY

- **Quick Update** (tylko Core): ~15 minut
- **Full Update** (Core + Main + Loader): ~45 minut
- **Testing & Validation**: ~30 minut
- **TOTAL**: ~1.5 godziny

---

## 📦 CO OTRZYMAŁEŚ

### Dokumentacja:
1. `PODSUMOWANIE_NAPRAW.md` - Executive summary
2. `SWARM_ANALIZA_PROBLEMOW.md` - Szczegółowa analiza techniczna
3. `QUICK_REFERENCE.md` - Szybkie odniesienie
4. `KOMUNIKACJA_GUIDE.md` - WiFi & Serial guide
5. `MIGRATION_GUIDE.md` - Ten plik

### Kod:
1. `swarm_core_FIXED.py` - Naprawiony core (v2.1)
2. `swarm_main_AUTO_FEEDBACK_PATCH.py` - Patch dla main
3. `loader_ENHANCED.py` - Ulepsz

ony loader (v3.1)

---

## 🔄 MIGRATION STRATEGY

### OPCJA A: QUICK (15 min) ⚡
**Dla:** Szybkie testowanie, development
**Zmienia:** Tylko swarm_core.py

### OPCJA B: RECOMMENDED (45 min) ⭐
**Dla:** Production use, pełna funkcjonalność
**Zmienia:** Core + Main + Loader

### OPCJA C: GRADUAL (rozłożone w czasie)
**Dla:** Ostrożne wdrożenie, minimalizacja ryzyka
**Zmienia:** Po kolei z testami

---

## 🚀 OPCJA A: QUICK UPDATE

### Krok 1: Backup
```bash
# Stwórz backup folder
mkdir swarm_backup_$(date +%Y%m%d)
cd swarm_backup_$(date +%Y%m%d)

# Backup obecnych plików
cp ../swarm_core.py .
cp ../swarm_main.py .
cp ../loader.py .

echo "✅ Backup created in: $(pwd)"
cd ..
```

### Krok 2: Zastąp Core
```bash
# Zamień swarm_core.py
cp swarm_core_FIXED.py swarm_core.py

echo "✅ Core updated to v2.1"
```

### Krok 3: Test
```bash
# Test importu
python -c "from swarm_core import SwarmCore; c = SwarmCore(); print('✅ Import OK')"

# Test podstawowy
python swarm_core.py
```

**Jeśli działa:**
```
✅ SwarmCore v2.1 initialized [FIXED]
   NPZ: 1247 concepts
   BLL: 0 categories
   OL: 0 learned concepts
   Chaos: 0.15 (min_dist=120mm)
```

### Krok 4: Run Simulator
```bash
# Test z simulatorem
python swarm_simulator.py

# Obserwuj:
# - OL vectors powinny rosnąć
# - BLL weights powinny się aktualizować
# - Chaos powinien być mniejszy (0.15 vs 0.5)
```

### Krok 5: Sprawdź rezultaty
```bash
# Po 5 minutach symulacji
ls -lh logs/

# Powinno być:
# - bll_weights.json (aktualizowany)
# - ol_vectors.json (nowy plik z vectors!)
```

**GOTOWE!** Core v2.1 działa.

⚠️ **Uwaga:** Bez patcha main, feedback będzie tylko z simulatora.

---

## ⭐ OPCJA B: RECOMMENDED FULL UPDATE

### CZĘŚĆ 1: Core (jak w Opcji A)
```bash
# Backup
mkdir swarm_backup_$(date +%Y%m%d)
cp swarm_core.py swarm_backup_*/
cp swarm_main.py swarm_backup_*/
cp loader.py swarm_backup_*/

# Update Core
cp swarm_core_FIXED.py swarm_core.py

# Test
python -c "from swarm_core import SwarmCore; print('✅ Core OK')"
```

### CZĘŚĆ 2: Main Patch
```bash
# Otwórz swarm_main.py w edytorze
nano swarm_main.py
# LUB
code swarm_main.py
# LUB
vim swarm_main.py
```

#### 2.1: Dodaj evaluate_action_success()
**Lokalizacja:** Po importach, przed klasami (około linia 60)

```python
# Skopiuj całą funkcję z swarm_main_AUTO_FEEDBACK_PATCH.py
# Linie 20-82:

def evaluate_action_success(
    old_sensors: Dict[str, float],
    new_sensors: Dict[str, float],
    action: str,
    min_improvement: float = 10.0
) -> bool:
    """
    Evaluate if last action was successful
    ... (cała funkcja)
    """
```

#### 2.2: Replace run_control_loop()
**Lokalizacja:** Klasa SwarmCoreController (około linia 600-700)

Znajdź metodę:
```python
def run_control_loop(self, max_cycles: int = None):
    """Main control loop"""
```

Zamień całą metodę na wersję z AUTO_FEEDBACK_PATCH.py (linie 99-170)

**Kluczowe zmiany:**
```python
# DODANE:
last_sensors = None
last_decision = None
success_count = 0
failure_count = 0

# W pętli DODANE:
if last_sensors and last_decision:
    success = evaluate_action_success(...)
    self.core.feedback(success=success)

    if success:
        success_count += 1
    else:
        failure_count += 1
```

#### 2.3: Test patched main
```bash
# Test importu
python -c "from swarm_main import *; print('✅ Main OK')"

# Jeśli błąd:
# - Sprawdź wcięcia (indentation)
# - Sprawdź czy Dict jest zaimportowane (from typing import Dict)
```

### CZĘŚĆ 3: Loader Update (opcjonalne, ale zalecane)
```bash
# Zamień loader
cp loader_ENHANCED.py loader.py

# LUB zachowaj oba:
cp loader.py loader_OLD.py
cp loader_ENHANCED.py loader.py
```

**Test loadera:**
```bash
python loader.py

# Powinno pokazać:
# "SWARM ROBOT SYSTEM - UNIVERSAL LOADER v3.1"
# "[Communication Master Edition]"
```

### CZĘŚĆ 4: Full System Test

#### Test 1: Simulator
```bash
python loader.py
# Wybierz: 1. Run Simulator

# Obserwuj logi:
# "✅ Action FORWARD successful"
# "❌ Action TURN_LEFT failed"
# "📊 Success rate: 87.3% (43/50)"
```

#### Test 2: Diagnostics
```bash
python loader.py
# Wybierz: 5. Run Diagnostics

# Sprawdź:
# - swarm_core v2.1 (FIXED) detected ✅
# - Network status
# - ESP32 detection (WiFi)
# - Serial ports scan
```

#### Test 3: Live Robot (jeśli masz ESP32)

**WiFi Mode:**
```bash
python loader.py
# Wybierz: 2. WiFi Mode
# System auto-detect ESP32 IP
# LUB wpisz manualnie: 10.135.120.105
```

**Serial Mode:**
```bash
python loader.py
# Wybierz: 3. Serial Mode
# System auto-detect port (COM3 / /dev/ttyUSB0)
```

#### Test 4: Learning Verification
```bash
# Uruchom simulator na 10 minut
python swarm_simulator.py

# Po zatrzymaniu (Ctrl+C), sprawdź:
cat logs/ol_vectors.json

# Powinno pokazać nowe concepts:
{
  "AVOID_FRONT_LEFT": [0.234, 0.567, ...],
  "CLEAR_PATH": [0.891, 0.123, ...],
  ...
}

cat logs/bll_weights.json

# Powinno pokazać updated weights:
{
  "navigation": 1.15,
  "avoidance": 0.92,
  ...
}
```

**GOTOWE!** Pełny system v2.1 działa.

---

## 🐢 OPCJA C: GRADUAL UPDATE

### Tydzień 1: Core Only
```bash
1. Backup wszystkiego
2. Update swarm_core.py → swarm_core_FIXED.py
3. Test przez tydzień z simulatorem
4. Monitor logs/ol_vectors.json
5. Sprawdź czy OL się uczy
```

### Tydzień 2: Main Patch
```bash
1. Backup swarm_main.py
2. Dodaj evaluate_action_success()
3. Test z simulatorem
4. Sprawdź success rate logs
```

### Tydzień 3: Full Integration
```bash
1. Patch run_control_loop()
2. Test full auto-feedback
3. Monitor przez tydzień
4. Verify success rate > 80%
```

### Tydzień 4: Loader & Communication
```bash
1. Update loader.py
2. Test WiFi mode
3. Test Serial mode
4. Production deployment
```

---

## ✅ VALIDATION CHECKLIST

Po migracji, sprawdź:

### Core Verification:
- [ ] `python swarm_core.py` działa bez błędów
- [ ] Version pokazuje "v2.1 [FIXED]"
- [ ] OL vectors inicjalizowane (może być 0 na start)
- [ ] Chaos level = 0.15
- [ ] Test scenarios przechodzą

### Main Verification:
- [ ] `python swarm_main.py --mode simulation` działa
- [ ] Logi pokazują "✅ Action X successful" / "❌ Action X failed"
- [ ] Co 50 cykli: "📊 Success rate: X%"
- [ ] Na exit: "FINAL STATISTICS" pokazuje się

### Learning Verification:
- [ ] Po 100 cyklach: `logs/ol_vectors.json` istnieje
- [ ] OL vectors > 0 (powinno być 5-15 concepts)
- [ ] `logs/bll_weights.json` aktualizowany
- [ ] Success rate > 75%

### Communication Verification (jeśli masz ESP32):
- [ ] WiFi mode: łączy się z ESP32 IP:81
- [ ] Serial mode: wykrywa COM port
- [ ] Sensor data jest odbierana
- [ ] Commands są wysyłane
- [ ] Brak packet loss / timeout

---

## 🐛 TROUBLESHOOTING MIGRATION

### Problem: ImportError po update
```
ImportError: cannot import name 'SwarmCore'

Rozwiązanie:
1. Sprawdź czy swarm_core_FIXED.py został skopiowany jako swarm_core.py
2. Usuń cache:
   rm -rf __pycache__
   rm *.pyc
3. Test ponownie:
   python -c "from swarm_core import SwarmCore"
```

### Problem: IndentationError w main patch
```
IndentationError: unexpected indent

Rozwiązanie:
1. Python wymaga spacji (nie tabulatorów)
2. Upewnij się że cała metoda ma spójne wcięcia
3. Użyj edytora z Python support (VS Code, PyCharm)
4. Sprawdź czy skopiowałeś całą funkcję (nie tylko fragment)
```

### Problem: OL nie się nie uczy
```
Po 200 cyklach: ol_vectors.json = {}

Możliwe przyczyny:
1. Brak auto-feedback:
   - Sprawdź czy run_control_loop() został patched
   - Logi powinny pokazywać "✅ Action X successful"

2. OL disabled:
   - W swarm_core.py sprawdź:
     ol_enabled: bool = True  # Powinno być True

3. Threshold za wysoki:
   - Zmniejsz ol_similarity_threshold z 0.6 na 0.5
```

### Problem: Success rate za niski (<60%)
```
📊 Success rate: 45.2% (22/50)

Rozwiązanie:
1. Zwiększ tolerancję w evaluate_action_success():
   return new_f >= (old_f - 30)  # Zamiast -20

2. Sprawdź czy robot nie jest w pętli:
   - Logi: "⚠️ Oscillation detected"
   - To normalne w wąskich korytarzach

3. Chaos może przeszkadzać:
   - Zmniejsz chaos_level do 0.10 (z 0.15)
```

### Problem: ESP32 nie łączy się (WiFi)
```
[ERROR] WebSocket connection failed

Rozwiązanie - sprawdź diagnostykę:
python loader.py → 5. Run Diagnostics

Zobacz KOMUNIKACJA_GUIDE.md sekcja "TROUBLESHOOTING WiFi"
```

### Problem: Serial port busy
```
[ERROR] Serial port already in use

Rozwiązanie:
1. Zamknij Arduino Serial Monitor
2. Zamknij inne PuTTY/screen sessions
3. Restart port (Linux):
   sudo fuser -k /dev/ttyUSB0
```

---

## 📊 POST-MIGRATION MONITORING

### Pierwsze 24h po wdrożeniu:

#### Sprawdź co godzinę:
```bash
# OL growth
cat logs/ol_vectors.json | python -m json.tool | grep -c "AVOID"

# BLL updates
cat logs/bll_weights.json | python -m json.tool

# Success rate trend
grep "Success rate" logs/*.log | tail -20
```

#### Metryki do śledzenia:
- **OL Vectors Count:** Powinno rosnąć przez pierwsze 6-12h, potem stabilizować
- **Success Rate:** Powinno być >75% i rosnąć do >85% w ciągu tygodnia
- **Oscillation Warnings:** Powinno być <5% wszystkich decyzji
- **Chaos Disabled Events:** Powinno być ~30-40% (gdy blisko obstacles)

### Po tygodniu:

```python
# Uruchom w Python:
from swarm_core import SwarmCore

core = SwarmCore()
stats = core.get_stats()

print(f"OL Vectors: {stats['ol_vectors']}")  # Oczekiwane: 30-60
print(f"BLL Categories: {stats['bll_categories']}")  # Oczekiwane: 10-20
print(f"OL Usage: {stats['ol_usage_count']}")  # Powinno rosnąć
print(f"Preferred Direction: {stats['preferred_direction']}")  # LEFT lub RIGHT
```

**Zdrowy system po tygodniu:**
```
OL Vectors: 45
BLL Categories: 15
OL Usage: 2847
Preferred Direction: RIGHT
Success Rate: 89.3%
```

---

## 🔄 ROLLBACK PROCEDURE

Jeśli coś pójdzie nie tak:

### Rollback Core:
```bash
cd swarm_backup_YYYYMMDD
cp swarm_core.py ../
cd ..
python -c "from swarm_core import SwarmCore; print('Rollback OK')"
```

### Rollback Main:
```bash
cd swarm_backup_YYYYMMDD
cp swarm_main.py ../
cd ..
python swarm_main.py --mode simulation --cycles 10
```

### Rollback Loader:
```bash
cd swarm_backup_YYYYMMDD
cp loader.py ../
cd ..
python loader.py
```

### Rollback ALL:
```bash
cd swarm_backup_YYYYMMDD
cp *.py ../
cd ..
echo "✅ Full rollback completed"
```

---

## 📞 SUPPORT & HELP

### Jeśli masz problemy:

1. **Sprawdź QUICK_REFERENCE.md** - podstawy kierunków i logiki
2. **Sprawdź KOMUNIKACJA_GUIDE.md** - WiFi/Serial troubleshooting
3. **Sprawdź SWARM_ANALIZA_PROBLEMOW.md** - szczegółowa analiza
4. **Uruchom diagnostykę:** `python loader.py → 5`

### Debug checklist:
- [ ] Backup exists?
- [ ] All files replaced correctly?
- [ ] No syntax errors in patches?
- [ ] Dependencies installed?
- [ ] Logs directory exists?
- [ ] BEHAVIORAL_BRAIN.npz present?

### Common errors quick fix:
```bash
# ImportError
rm -rf __pycache__; python -c "from swarm_core import SwarmCore"

# IndentationError
# Use proper editor (VS Code, PyCharm)

# PermissionError (Serial)
sudo chmod 666 /dev/ttyUSB0  # Linux

# ConnectionError (WiFi)
ping <ESP32_IP>; telnet <ESP32_IP> 81
```

---

## 🎉 SUCCESS CRITERIA

Migration jest udana gdy:

✅ **Core v2.1:**
- Import działa bez błędów
- Version = v2.1 [FIXED]
- OL vectors inicjalizowane
- Chaos = 0.15

✅ **Auto-Feedback:**
- Logi pokazują success/failure
- Success rate > 75%
- Statistics na exit

✅ **Learning:**
- ol_vectors.json rośnie
- bll_weights.json aktualizowany
- Success rate poprawia się w czasie

✅ **Communication (opcjonalne):**
- WiFi lub Serial działa
- Sensor data odbierana
- Commands wysyłane
- Stabilne połączenie

---

## 📈 EXPECTED IMPROVEMENTS

Po migracji oczekuj:

### Immediate (pierwsze uruchomienie):
- ✅ Mniej losowych skrętów (chaos 0.15 vs 0.5)
- ✅ Smooth navigation w clear paths
- ✅ Logi z success/failure feedback

### Po 100 cyklach:
- ✅ OL: 5-15 learned concepts
- ✅ Success rate: 75-85%
- ✅ Zmniejszone oscylacje

### Po tygodniu:
- ✅ OL: 30-60 concepts (stabilizacja)
- ✅ Success rate: 85-92%
- ✅ Robot "personality" (preferred directions)
- ✅ Lepsze unikanie pułapek

---

**POWODZENIA!** 🚀

---

**Wersja:** 1.0
**Data:** 2026-01-27
**Dla:** SWARM Robot v2.0 → v2.1 Migration
