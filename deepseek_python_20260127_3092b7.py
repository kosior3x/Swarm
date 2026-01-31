#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SWARM ANDROID LOADER - dla Pydroid3
================================================================================
Specjalna wersja loader dla Android/Pydroid3 bez użycia input() w problematycznych miejscach.
================================================================================
"""

import os
import sys
import time
import subprocess
import platform
import logging
from datetime import datetime

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('SwarmLoaderAndroid')

# ============================================================================
# KOLORY (dla terminala Pydroid3)
# ============================================================================

class Color:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

# ============================================================================
# FUNKCJE POMOCNICZE DLA ANDROID
# ============================================================================

def android_input(prompt, default="n"):
    """
    Bezpieczna funkcja input dla Androida
    W przypadku błędu zwraca wartość domyślną
    """
    try:
        return input(prompt)
    except EOFError:
        print(f"{Color.YELLOW}[ANDROID] Używam wartości domyślnej: {default}{Color.END}")
        return default
    except Exception as e:
        print(f"{Color.YELLOW}[ANDROID] Błąd input: {e}, używam: {default}{Color.END}")
        return default

def wait_for_enter():
    """Czekaj na Enter z obsługą Androida"""
    try:
        android_input("\nNaciśnij Enter aby kontynuować...", "")
    except:
        time.sleep(2)  # Fallback: poczekaj 2 sekundy

def clear_screen():
    """Wyczyść ekran - bezpieczna wersja dla Androida"""
    try:
        os.system('clear')
    except:
        print("\n" * 50)  # Fallback: wypisz wiele nowych linii

# ============================================================================
# SPRAWDZANIE ZALEŻNOŚCI
# ============================================================================

DEPENDENCIES = {
    'numpy': 'numpy',
    'pygame': 'pygame',
    'pandas': 'pandas',
}

def check_dependencies():
    """Sprawdź czy wymagane biblioteki są zainstalowane"""
    print(f"\n{Color.CYAN}[*] Sprawdzanie zależności...{Color.END}")
    missing = []

    for module, package in DEPENDENCIES.items():
        try:
            __import__(module)
            print(f"  {Color.GREEN}✓{Color.END} {module}")
        except ImportError:
            print(f"  {Color.RED}✗{Color.END} {module}")
            missing.append(package)

    if missing:
        print(f"\n{Color.YELLOW}[!] Brakuje: {', '.join(missing)}{Color.END}")
        print(f"    Zainstaluj: pip install {' '.join(missing)}")

    return len(missing) == 0

# ============================================================================
# PRZYGOTOWANIE ŚRODOWISKA
# ============================================================================

def setup_environment():
    """Przygotuj środowisko - utwórz potrzebne katalogi"""
    print(f"\n{Color.CYAN}[*] Przygotowywanie środowiska...{Color.END}")

    directories = ['logs', 'brain_data', 'saved_models', 'training_data']

    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"  {Color.GREEN}[+] {directory}/{Color.END}")
        else:
            print(f"  {Color.GREEN}[✓] {directory}/{Color.END}")

    return True

def check_essential_files():
    """Sprawdź istnienie kluczowych plików"""
    print(f"\n{Color.CYAN}[*] Sprawdzanie plików...{Color.END}")

    files_to_check = [
        ('swarm_simulator.py', 'Symulator'),
        ('swarm_main.py', 'Główny robot'),
        ('BEHAVIORAL_BRAIN.npz', 'Mózg ABSR'),
        ('behavioral_model.csv', 'Model behawioralny'),
    ]

    all_exist = True
    for filename, description in files_to_check:
        if os.path.exists(filename):
            print(f"  {Color.GREEN}✓{Color.END} {filename} ({description})")
        else:
            print(f"  {Color.YELLOW}✗{Color.END} {filename} ({description})")
            all_exist = False

    return all_exist

# ============================================================================
# AUTOMATYCZNE TWORZENIE BRAKUJĄCYCH PLIKÓW
# ============================================================================

def create_robot_with_intuition():
    """Utwórz podstawowy plik robot_with_intuition.py"""
    content = '''#!/usr/bin/env python3
"""
Robot z intuicyjnym mózgiem ABSR - podstawowa wersja dla Android
"""
import numpy as np
import time

class IntuitionRobot:
    def __init__(self):
        self.sensor_left = 0
        self.sensor_right = 0
        self.brain_file = "BEHAVIORAL_BRAIN.npz"

    def load_brain(self):
        """Ładuj mózg ABSR"""
        try:
            data = np.load(self.brain_file, allow_pickle=True)
            print(f"✓ Mózg załadowany: {len(data['words'])} słów")
            return True
        except:
            print("✗ Nie można załadować mózgu")
            return False

    def feel_and_decide(self, dist_left, dist_right):
        """Prosta decyzja intuicyjna"""
        if dist_left < 50 and dist_right < 50:
            return {"action": "ESCAPE_LEFT", "speed_L": -100, "speed_R": 150}
        elif dist_left < 100:
            return {"action": "TURN_RIGHT", "speed_L": 120, "speed_R": 60}
        elif dist_right < 100:
            return {"action": "TURN_LEFT", "speed_L": 60, "speed_R": 120}
        else:
            return {"action": "FORWARD", "speed_L": 120, "speed_R": 120}

def main():
    print("🤖 ROBOT Z INTUICJĄ ABSR")
    print("="*40)

    robot = IntuitionRobot()

    if robot.load_brain():
        print("\nTestowanie decyzji:")
        test_cases = [
            ("Wolna przestrzeń", 300, 280),
            ("Przeszkoda z lewej", 80, 250),
            ("Przeszkoda z prawej", 250, 80),
            ("Kolizja", 40, 45),
        ]

        for name, left, right in test_cases:
            decision = robot.feel_and_decide(left, right)
            print(f"{name}: L={left}, R={right}")
            print(f"  → {decision['action']} ({decision['speed_L']}, {decision['speed_R']})")

if __name__ == "__main__":
    main()
'''

    with open("robot_with_intuition.py", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"{Color.GREEN}[✓] Utworzono robot_with_intuition.py{Color.END}")

# ============================================================================
# FUNKCJE URUCHAMIANIA
# ============================================================================

def run_simulator():
    """Uruchom symulator"""
    print(f"\n{Color.BLUE}>>> URUCHAMIANIE SYMULATORA <<<{Color.END}")

    if not os.path.exists("swarm_simulator.py"):
        print(f"{Color.RED}✗ Brak symulatora!{Color.END}")
        return False

    try:
        print(f"{Color.CYAN}[*] Uruchamianie...{Color.END}")
        # W Pydroid3 subprocess może nie działać idealnie, używamy import
        import swarm_simulator
        return True
    except Exception as e:
        print(f"{Color.RED}✗ Błąd: {e}{Color.END}")
        return False

def run_live_robot():
    """Uruchom głównego robota"""
    print(f"\n{Color.BLUE}>>> URUCHAMIANIE ROBOTA <<<{Color.END}")

    if not os.path.exists("swarm_main.py"):
        print(f"{Color.RED}✗ Brak głównego skryptu!{Color.END}")
        return False

    try:
        print(f"{Color.CYAN}[*] Uruchamianie...{Color.END}")
        import swarm_main
        return True
    except Exception as e:
        print(f"{Color.RED}✗ Błąd: {e}{Color.END}")
        return False

def run_absr_trainer():
    """Uruchom trenera ABSR"""
    print(f"\n{Color.BLUE}>>> TRENOWANIE MÓZGU ABSR <<<{Color.END}")

    trainers = [
        ('absr_brain_incremental.py', 'ABSR Brain Inkrementalny'),
        ('swarm_trainer.py', 'Podstawowy Trainer'),
        ('workflow_universal.py', 'Pełny Workflow'),
    ]

    available = []
    for file, name in trainers:
        if os.path.exists(file):
            available.append((file, name))

    if not available:
        print(f"{Color.YELLOW}✗ Brak dostępnych trenerów{Color.END}")
        return False

    print(f"\n{Color.CYAN}Dostępne trenery:{Color.END}")
    for i, (file, name) in enumerate(available, 1):
        print(f"  {i}. {name}")

    try:
        choice = android_input(f"\nWybierz [1-{len(available)}]: ", "1")
        idx = int(choice) - 1

        if 0 <= idx < len(available):
            file, name = available[idx]
            print(f"{Color.GREEN}[*] Uruchamianie {name}...{Color.END}")

            # W Pydroid3 lepiej importować niż subprocess
            if file == 'absr_brain_incremental.py':
                import absr_brain_incremental
            elif file == 'swarm_trainer.py':
                import swarm_trainer
            elif file == 'workflow_universal.py':
                import workflow_universal

            return True
        else:
            print(f"{Color.RED}✗ Nieprawidłowy wybór{Color.END}")
            return False
    except Exception as e:
        print(f"{Color.RED}✗ Błąd: {e}{Color.END}")
        return False

def show_diagnostics():
    """Pokaż diagnostykę systemu"""
    print(f"\n{Color.CYAN}=== DIAGNOSTYKA ANDROID ==={Color.END}")

    # Informacje o systemie
    print(f"\n{Color.BOLD}📱 SYSTEM:{Color.END}")
    print(f"  Platforma: {platform.system()} {platform.release()}")
    print(f"  Procesor: {platform.machine()}")
    print(f"  Python: {sys.version.split()[0]}")

    # Sprawdź brain
    print(f"\n{Color.BOLD}🧠 MÓZG:{Color.END}")
    if os.path.exists('BEHAVIORAL_BRAIN.npz'):
        try:
            import numpy as np
            data = np.load('BEHAVIORAL_BRAIN.npz', allow_pickle=True)
            words = len(data['words']) if 'words' in data else 0
            print(f"  ✓ BEHAVIORAL_BRAIN.npz ({words} słów)")
        except:
            print(f"  ✗ Mózg uszkodzony")
    else:
        print(f"  ✗ Brak mózgu")

    # Pliki
    print(f"\n{Color.BOLD}📁 PLIKI:{Color.END}")
    files = ['swarm_simulator.py', 'swarm_main.py', 'behavioral_model.csv']
    for f in files:
        status = "✓" if os.path.exists(f) else "✗"
        color = Color.GREEN if os.path.exists(f) else Color.RED
        print(f"  {color}{status}{Color.END} {f}")

    # Dysk
    print(f"\n{Color.BOLD}💾 DYSK:{Color.END}")
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        print(f"  Wolne: {free // (2**20):,} MB")
        print(f"  Użyte: {used // (2**20):,} MB")
    except:
        print("  Nie można sprawdzić dysku")

    print(f"\n{Color.CYAN}=== KONIEC DIAGNOSTYKI ==={Color.END}")
    return True

# ============================================================================
# MENU GŁÓWNE DLA ANDROID
# ============================================================================

def show_menu():
    """Pokaż menu główne"""
    clear_screen()

    # Nagłówek
    print(f"{Color.BOLD}{Color.BLUE}" + "="*50)
    print("     🤖 SWARM ANDROID LOADER")
    print("="*50 + Color.END)
    print(f"  Platforma: Android (Pydroid3)")
    print(f"  Czas: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{Color.BLUE}" + "="*50 + Color.END)

    # Status mózgu
    brain_exists = os.path.exists('BEHAVIORAL_BRAIN.npz')
    brain_status = f"{Color.GREEN}✓ MÓZG OK{Color.END}" if brain_exists else f"{Color.RED}✗ BRAK MÓZGU{Color.END}"
    print(f"\n  STATUS: {brain_status}")

    # Opcje menu
    print(f"\n{Color.BOLD}🏁 MENU GŁÓWNE:{Color.END}")
    print(f"  1️⃣  {Color.CYAN}Uruchom Symulator{Color.END}")
    print(f"  2️⃣  {Color.CYAN}Uruchom Robota{Color.END}")
    print(f"  3️⃣  {Color.CYAN}Trenuj Mózg ABSR{Color.END}")
    print(f"  4️⃣  {Color.CYAN}Diagnostyka Systemu{Color.END}")
    print(f"  5️⃣  {Color.CYAN}Sprawdź Zależności{Color.END}")
    print(f"  6️⃣  {Color.CYAN}Utwórz Brakujące Pliki{Color.END}")
    print(f"  0️⃣  {Color.RED}Wyjście{Color.END}")

    return android_input(f"\n{Color.BOLD}Wybierz opcję [0-6]: {Color.END}", "0")

def handle_menu_choice(choice):
    """Obsłuż wybór z menu"""
    if choice == '1':
        run_simulator()
        wait_for_enter()
        return True
    elif choice == '2':
        run_live_robot()
        wait_for_enter()
        return True
    elif choice == '3':
        run_absr_trainer()
        wait_for_enter()
        return True
    elif choice == '4':
        show_diagnostics()
        wait_for_enter()
        return True
    elif choice == '5':
        check_dependencies()
        wait_for_enter()
        return True
    elif choice == '6':
        print(f"\n{Color.CYAN}[*] Tworzenie brakujących plików...{Color.END}")
        if not os.path.exists("robot_with_intuition.py"):
            create_robot_with_intuition()
        print(f"{Color.GREEN}[✓] Gotowe!{Color.END}")
        wait_for_enter()
        return True
    elif choice == '0':
        print(f"\n{Color.GREEN}👋 Do widzenia!{Color.END}")
        return False
    else:
        print(f"{Color.RED}✗ Nieprawidłowy wybór{Color.END}")
        time.sleep(1)
        return True

# ============================================================================
# INICJALIZACJA SYSTEMU
# ============================================================================

def initialize_system():
    """Inicjalizuj system SWARM dla Androida"""
    print(f"{Color.CYAN}[*] Inicjalizacja SWARM dla Android...{Color.END}")

    # 1. Przygotuj środowisko
    setup_environment()

    # 2. Sprawdź pliki
    files_ok = check_essential_files()

    # 3. Sprawdź zależności (tylko informacyjnie)
    check_dependencies()

    # 4. Jeśli brakuje kluczowych plików, zapytaj (bez input problematycznego)
    if not os.path.exists("robot_with_intuition.py"):
        print(f"\n{Color.YELLOW}[!] Brak robot_with_intuition.py{Color.END}")
        print(f"{Color.CYAN}[*] Automatycznie tworzę podstawową wersję...{Color.END}")
        create_robot_with_intuition()
        time.sleep(1)

    print(f"\n{Color.GREEN}[✓] System gotowy!{Color.END}")
    time.sleep(1)

    return True

# ============================================================================
# GŁÓWNA PĘTLA
# ============================================================================

def main():
    """Główna funkcja programu"""
    try:
        # Inicjalizacja
        initialize_system()

        # Pętla menu
        running = True
        while running:
            choice = show_menu()
            running = handle_menu_choice(choice)

    except KeyboardInterrupt:
        print(f"\n{Color.YELLOW}[!] Przerwano przez użytkownika{Color.END}")
    except Exception as e:
        print(f"\n{Color.RED}[!] Błąd krytyczny: {e}{Color.END}")
        print(f"{Color.YELLOW}[*] Restartuję za 5 sekund...{Color.END}")
        time.sleep(5)

        # Spróbuj ponownie
        try:
            main()
        except:
            print(f"{Color.RED}[!] Nie można uruchomić{Color.END}")

# ============================================================================
# URUCHOMIENIE
# ============================================================================

if __name__ == "__main__":
    # Specjalna flaga dla Androida
    print(f"{Color.BOLD}{Color.CYAN}🤖 SWARM ANDROID EDITION 🤖{Color.END}")
    print(f"{Color.CYAN}Optymalizowany dla Pydroid3{Color.END}")

    # Uruchom główną pętlę
    main()