#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SWARM UNIVERSAL LOADER - NAPRAWIONY
================================================================================
Project: Autonomic SWARM
Version: 3.1 "Universal Fixed"
Date: 2026-01-25

Funkcjonalny loader zarządzający ekosystemem SWARM.
================================================================================
"""

import os
import sys
import time
import subprocess
import platform
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('SwarmLoader')

# ============================================================================
# COLORS & AESTHETICS (ANSI)
# ============================================================================

class Color:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

# ============================================================================
# DEPENDENCY MANAGER
# ============================================================================

DEPENDENCIES = {
    'numpy': 'numpy',
    'pygame': 'pygame',
    'pandas': 'pandas',
}

def check_dependencies():
    """Check and report missing dependencies"""
    print(f"\n{Color.CYAN}[*] Sprawdzanie zależności...{Color.END}")
    missing = []
    for module, package in DEPENDENCIES.items():
        try:
            __import__(module)
            print(f"  {Color.GREEN}[OK]{Color.END} {module}")
        except ImportError:
            print(f"  {Color.RED}[BRAK]{Color.END} {module} (pakiet: {package})")
            missing.append(package)

    if missing:
        print(f"\n{Color.YELLOW}[!] Brakujące zależności.{Color.END}")
        choice = input("Czy chcesz spróbować je zainstalować teraz? (y/n): ").lower()
        if choice == 'y':
            for pkg in missing:
                print(f"{Color.CYAN}[*] Instalowanie {pkg}...{Color.END}")
                try:
                    # Sprawdź czy pip jest dostępny
                    import pip
                    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
                    print(f"  {Color.GREEN}[OK]{Color.END} {pkg} zainstalowany")
                except Exception as e:
                    print(f"{Color.RED}[BŁĄD] Nie udało się zainstalować {pkg}: {e}{Color.END}")
        else:
            print(f"{Color.YELLOW}[!] Zainstaluj ręcznie: pip install {' '.join(missing)}{Color.END}")
    return len(missing) == 0

# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

def setup_environment():
    """Ensure directories and essential files exist"""
    print(f"\n{Color.CYAN}[*] Przygotowywanie środowiska...{Color.END}")

    directories = ['logs', 'brain_data', 'saved_models']

    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"  {Color.GREEN}[UTWORZONO]{Color.END} {directory}/")
        else:
            print(f"  {Color.GREEN}[OK]{Color.END} {directory}/")

    # Sprawdź istotne pliki
    essential_files = {
        'behavioral_model.csv': 'Model behawioralny',
        'BEHAVIORAL_BRAIN.npz': 'Mózg ABSR',
    }

    for file, description in essential_files.items():
        if os.path.exists(file):
            print(f"  {Color.GREEN}[OK]{Color.END} {file} ({description})")
        else:
            print(f"  {Color.YELLOW}[BRAK]{Color.END} {file} ({description})")

    return True

# ============================================================================
# FILE CHECKERS
# ============================================================================

def check_required_files():
    """Sprawdza czy wymagane pliki istnieją"""
    required = ['swarm_simulator.py', 'swarm_main.py', 'robot_with_intuition.py']
    missing = []

    for file in required:
        if os.path.exists(file):
            print(f"  {Color.GREEN}[OK]{Color.END} {file}")
        else:
            print(f"  {Color.RED}[BRAK]{Color.END} {file}")
            missing.append(file)

    if missing:
        print(f"\n{Color.RED}[!] Brakujące pliki główne:{Color.END}")
        for file in missing:
            print(f"  - {file}")
        return False
    return True

# ============================================================================
# MENU ACTIONS - POPRAWIONE
# ============================================================================

def run_simulator():
    """Launch the Pygame simulator"""
    print(f"\n{Color.BLUE}>>> URUCHAMIANIE SYMULATORA SWARM <<<{Color.END}")

    # Sprawdź czy plik istnieje
    if not os.path.exists("swarm_simulator.py"):
        print(f"{Color.RED}[BŁĄD] Brak pliku swarm_simulator.py{Color.END}")
        print("Tworzę podstawowy symulator...")
        create_basic_simulator()

    try:
        # Uruchom symulator
        print(f"{Color.CYAN}[*] Uruchamianie...{Color.END}")
        subprocess.run([sys.executable, "swarm_simulator.py"])
    except KeyboardInterrupt:
        print(f"\n{Color.YELLOW}[!] Symulator zatrzymany przez użytkownika{Color.END}")
    except Exception as e:
        print(f"{Color.RED}[BŁĄD] Nie można uruchomić symulatora: {e}{Color.END}")
        print(f"{Color.YELLOW}[!] Sprawdź czy pygame jest zainstalowany{Color.END}")

    input("\nNaciśnij Enter aby kontynuować...")

def run_live():
    """Launch the main robot loop"""
    print(f"\n{Color.BLUE}>>> URUCHAMIANIE ŻYWEGO ROBOTA <<<{Color.END}")

    if not os.path.exists("swarm_main.py"):
        print(f"{Color.RED}[BŁĄD] Brak pliku swarm_main.py{Color.END}")
        print("Tworzę podstawowy główny skrypt...")
        create_basic_main()

    try:
        print(f"{Color.CYAN}[*] Uruchamianie głównej pętli robota...{Color.END}")
        subprocess.run([sys.executable, "swarm_main.py"])
    except KeyboardInterrupt:
        print(f"\n{Color.YELLOW}[!] Robot zatrzymany przez użytkownika{Color.END}")
    except Exception as e:
        print(f"{Color.RED}[BŁĄD] Nie można uruchomić robota: {e}{Color.END}")

    input("\nNaciśnij Enter aby kontynuować...")

def run_trainer():
    """Launch the NPZ trainer"""
    print(f"\n{Color.BLUE}>>> URUCHAMIANIE TRENERA MÓZGU <<<{Color.END}")

    # Sprawdź dostępne opcje treningu
    trainers = [
        ('absr_brain_incremental.py', 'ABSR Brain (inkrementalny)'),
        ('swarm_trainer.py', 'Podstawowy trainer'),
    ]

    available_trainers = []
    for file, description in trainers:
        if os.path.exists(file):
            available_trainers.append((file, description))

    if not available_trainers:
        print(f"{Color.RED}[BŁĄD] Brak dostępnych trenerów{Color.END}")
        print("Tworzę podstawowy trainer...")
        create_basic_trainer()
        available_trainers.append(('swarm_trainer.py', 'Podstawowy trainer'))

    print(f"\n{Color.CYAN}Dostępne trenery:{Color.END}")
    for i, (file, desc) in enumerate(available_trainers, 1):
        print(f"  {Color.CYAN}{i}.{Color.END} {desc} ({file})")
    print(f"  {Color.CYAN}0.{Color.END} Powrót")

    choice = input(f"\n{Color.BOLD}Wybierz trener [0-{len(available_trainers)}]: {Color.END}").strip()

    if choice == '0':
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(available_trainers):
            file, desc = available_trainers[idx]
            print(f"\n{Color.GREEN}[*] Uruchamianie {desc}...{Color.END}")
            subprocess.run([sys.executable, file])
        else:
            print(f"{Color.RED}[!] Nieprawidłowy wybór{Color.END}")
    except ValueError:
        print(f"{Color.RED}[!] Wprowadź numer{Color.END}")

    input("\nNaciśnij Enter aby kontynuować...")

def run_diagnostics():
    """Check system status"""
    print(f"\n{Color.CYAN}--- DIAGNOSTYKA SYSTEMU ---{Color.END}")

    # 1. Informacje o systemie
    print(f"\n{Color.BOLD}1. SYSTEM:{Color.END}")
    print(f"   Platforma: {platform.system()} {platform.release()}")
    print(f"   Procesor: {platform.processor()}")
    print(f"   Python: {sys.version.split()[0]}")

    # 2. Stan dysku
    print(f"\n{Color.BOLD}2. DYSK:{Color.END}")
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        print(f"   Wolne: {free // (2**30)} GB")
        print(f"   Użyte: {used // (2**30)} GB")
        print(f"   Całkowite: {total // (2**30)} GB")
    except:
        print("   Nie można sprawdzić przestrzeni dyskowej")

    # 3. Zależności
    print(f"\n{Color.BOLD}3. ZALEŻNOŚCI:{Color.END}")
    for module, package in DEPENDENCIES.items():
        try:
            __import__(module)
            print(f"   {Color.GREEN}✓{Color.END} {module}")
        except:
            print(f"   {Color.RED}✗{Color.END} {module}")

    # 4. Pliki
    print(f"\n{Color.BOLD}4. PLIKI:{Color.END}")
    check_required_files()

    # 5. ESP32/WiFi (opcjonalnie)
    print(f"\n{Color.BOLD}5. SIECI/WIFI:{Color.END}")
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        print(f"   Local IP: {Color.GREEN}{local_ip}{Color.END}")
    except:
        print("   Nie można sprawdzić IP")

    # 6. Brain status
    print(f"\n{Color.BOLD}6. MÓZG:{Color.END}")
    if os.path.exists('BEHAVIORAL_BRAIN.npz'):
        try:
            import numpy as np
            data = np.load('BEHAVIORAL_BRAIN.npz', allow_pickle=True)
            words = data['words'].tolist() if 'words' in data else []
            vectors = data['vectors'] if 'vectors' in data else []
            print(f"   Słowa: {len(words)}")
            print(f"   Wektory: {vectors.shape if len(vectors) > 0 else 'brak'}")
        except:
            print("   Plik mózgu uszkodzony")
    else:
        print(f"   {Color.YELLOW}Mózg nie znaleziony{Color.END}")

    print(f"\n{Color.CYAN}--- KONIEC DIAGNOSTYKI ---{Color.END}")
    input("\nNaciśnij Enter aby kontynuować...")

def run_intuition_test():
    """Run ABSR intuition test"""
    print(f"\n{Color.BLUE}>>> TEST INTUICJI ABSR <<<{Color.END}")

    if not os.path.exists('robot_with_intuition.py'):
        print(f"{Color.RED}[BŁĄD] Brak pliku robot_with_intuition.py{Color.END}")
        return

    try:
        # Zaimportuj i uruchom test
        import robot_with_intuition
        print(f"{Color.GREEN}[*] Test intuicji uruchomiony{Color.END}")

        # Tu możesz dodać konkretny test
        print("Testowanie decyzji ABSR...")

    except Exception as e:
        print(f"{Color.RED}[BŁĄD] Nie można uruchomić testu: {e}{Color.END}")

    input("\nNaciśnij Enter aby kontynuować...")

# ============================================================================
# FILE CREATORS (fallback)
# ============================================================================

def create_basic_simulator():
    """Create basic simulator if missing"""
    content = '''#!/usr/bin/env python3
"""
Podstawowy symulator SWARM
"""
import pygame
import sys

def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("SWARM Simulator")

    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        screen.fill((0, 0, 30))

        # Prostokąt robota
        pygame.draw.rect(screen, (0, 255, 0), (350, 250, 100, 100))

        # Tekst
        font = pygame.font.Font(None, 36)
        text = font.render("SWARM SIMULATOR - BASIC", True, (255, 255, 255))
        screen.blit(text, (200, 50))

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
'''

    with open("swarm_simulator.py", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"{Color.GREEN}[OK] Utworzono podstawowy symulator{Color.END}")

def create_basic_main():
    """Create basic main robot script"""
    content = '''#!/usr/bin/env python3
"""
Podstawowy główny skrypt robota
"""
import time

print("=== SWARM ROBOT - BASIC ===")
print("Ten skrypt wymaga implementacji.")
print("1. Połączenie z hardware")
print("2. Odczyt sensorów")
print("3. Sterowanie silnikami")
print("===========================")

for i in range(5, 0, -1):
    print(f"Zamykanie za {i}...")
    time.sleep(1)

print("Zakończono.")
'''

    with open("swarm_main.py", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"{Color.GREEN}[OK] Utworzono podstawowy skrypt główny{Color.END}")

def create_basic_trainer():
    """Create basic trainer"""
    content = '''#!/usr/bin/env python3
"""
Podstawowy trainer SWARM
"""
print("=== SWARM TRAINER - BASIC ===")
print("Ten trainer wymaga implementacji.")
print("Możliwości:")
print("1. Tworzenie modelu behawioralnego")
print("2. Generowanie NPZ brain")
print("3. Trening ABSR")
print("==============================")

input("Naciśnij Enter aby kontynuować...")
'''

    with open("swarm_trainer.py", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"{Color.GREEN}[OK] Utworzono podstawowy trainer{Color.END}")

# ============================================================================
# MAIN INTERFACE
# ============================================================================

def print_header():
    """Print beautiful header"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{Color.BOLD}{Color.BLUE}" + "="*60)
    print("      🚀 SWARM ROBOT SYSTEM - UNIVERSAL LOADER v3.1")
    print("="*60 + Color.END)
    print(f" Platforma: {platform.system()} {platform.release()}")
    print(f" Python:   {sys.version.split()[0]}")
    print(f" Czas:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Color.BLUE}" + "="*60 + Color.END)

def main_menu():
    """Main menu loop"""
    while True:
        print_header()

        # Quick status
        brain_exists = os.path.exists('BEHAVIORAL_BRAIN.npz')
        brain_status = f"{Color.GREEN}✓ MÓZG{Color.END}" if brain_exists else f"{Color.YELLOW}✗ BRAK MÓZGU{Color.END}"

        print(f"\n{Color.BOLD}STATUS: {brain_status}{Color.END}")

        print(f"\n{Color.BOLD}MENU GŁÓWNE:{Color.END}")
        print(f"  {Color.CYAN}1.{Color.END} URUCHOM SYMULATOR        {Color.YELLOW}(Środowisko wirtualne){Color.END}")
        print(f"  {Color.CYAN}2.{Color.END} URUCHOM ŻYWEGO ROBOTA    {Color.GREEN}(Hardware/WiFi){Color.END}")
        print(f"  {Color.CYAN}3.{Color.END} TRENUJ MÓZG (NPZ)       {Color.CYAN}(Przetwarzanie logów){Color.END}")
        print(f"  {Color.CYAN}4.{Color.END} DIAGNOSTYKA SYSTEMU     {Color.BLUE}(Sprawdzenie stanu){Color.END}")
        print(f"  {Color.CYAN}5.{Color.END} TEST INTUICJI ABSR      {Color.MAGENTA}(Eksperymentalne){Color.END}")
        print(f"  {Color.CYAN}6.{Color.END} SPRAWDŹ ZALEŻNOŚCI")
        print(f"  {Color.RED}0. WYJŚCIE{Color.END}")

        try:
            choice = input(f"\n{Color.BOLD}Wybierz opcję [0-6]: {Color.END}").strip()

            if choice == '1':
                run_simulator()
            elif choice == '2':
                run_live()
            elif choice == '3':
                run_trainer()
            elif choice == '4':
                run_diagnostics()
            elif choice == '5':
                run_intuition_test()
            elif choice == '6':
                check_dependencies()
                input("\nNaciśnij Enter aby kontynuować...")
            elif choice == '0':
                print(f"\n{Color.GREEN}Do widzenia! 🚀{Color.END}")
                break
            else:
                print(f"{Color.RED}[!] Nieprawidłowy wybór{Color.END}")
                time.sleep(1)

        except KeyboardInterrupt:
            print(f"\n{Color.YELLOW}[!] Przerwano przez użytkownika{Color.END}")
            break
        except Exception as e:
            print(f"{Color.RED}[!] Błąd: {e}{Color.END}")
            time.sleep(2)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    try:
        # Initial setup
        print_header()
        print(f"{Color.CYAN}[*] Inicjalizacja systemu SWARM...{Color.END}")

        # Setup environment
        setup_environment()

        # Check essential files
        if not check_required_files():
            print(f"\n{Color.YELLOW}[!] Brakuje podstawowych plików{Color.END}")
            print("Czy chcesz utworzyć podstawowe pliki? (y/n): ", end="")
            if input().lower() == 'y':
                create_basic_simulator()
                create_basic_main()
                create_basic_trainer()

        # Start main menu
        main_menu()

    except KeyboardInterrupt:
        print(f"\n{Color.YELLOW}[!] Przerwano podczas inicjalizacji{Color.END}")
    except Exception as e:
        print(f"\n{Color.RED}[!] Błąd krytyczny: {e}{Color.END}")
        import traceback
        traceback.print_exc()
        input("\nNaciśnij Enter aby zakończyć...")
        sys.exit(1)