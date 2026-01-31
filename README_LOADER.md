# SWARM Universal Loader

Ten folder zawiera kompletny system sterowania robotem SWARM z obsługą AI (ABSR/BLL).

## 🚀 Jak uruchomić?

### Windows:
Uruchom plik **`start_swarm.bat`**.

### Linux / macOS / Android (Pydroid3):
Uruchom plik **`loader.py`** za pomocą Pythona:
```bash
python loader.py
```

## 🛠️ Funkcje Loadera
1. **Automatyczne sprawdzanie zależności** - Wykrywa brakujące biblioteki (numpy, pandas, pygame, pyserial) i oferuje ich instalację.
2. **Setup Środowiska** - Tworzy folder `logs` i sprawdza obecność modelu `BEHAVIORAL_BRAIN.npz`.
3. **Menu Główne**:
   - **Simulator**: Wirtualne środowisko do testów i zbierania danych.
   - **Live Robot**: Połączenie z robotem via WiFi (ESP32).
   - **Train Brain**: Przetwarzanie zebranych logów w nowy model AI.
   - **Diagnostics**: Skanowanie sieci w poszukiwaniu robota.

## 📁 Struktura Systemu
- `loader.py` - Główny program startowy.
- `swarm_main.py` - Pętla sterowania robotem (tryb Live).
- `swarm_simulator.py` - Symulator graficzny (Pygame).
- `swarm_trainer.py` - Trener sieci neuronowej / modelu NPZ.
- `swarm_wifi.py` - Moduł komunikacji (WebSocket/FTP).
- `swarm_unified_core.py` - Silnik decyzji ABSR.

---
*SWARM Project - 2026*
