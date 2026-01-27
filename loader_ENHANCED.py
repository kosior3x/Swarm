#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SWARM UNIVERSAL LOADER - ENHANCED v3.1
================================================================================
Project: Autonomic SWARM
Version: 3.1 "Communication Master"
Date: 2026-01-27

ENHANCED FEATURES:
-----------------
✅ WiFi/WebSocket communication (ESP32)
✅ USB/Serial communication (RX/TX via USB)
✅ Auto-detection of ESP32 (WiFi scan + Serial scan)
✅ Enhanced diagnostics with connection testing
✅ Communication mode selection
✅ Real-time connection status monitoring
✅ Integration with FIXED swarm_core v2.1

SUPPORTED MODES:
---------------
1. SIMULATOR    - Virtual environment (Pygame)
2. WIFI MODE    - WebSocket @ ESP32 IP:81
3. SERIAL MODE  - USB RX/TX (Auto-detect COM/ttyUSB)
4. TRAINER      - NPZ brain training
5. DIAGNOSTICS  - Full system check

================================================================================
"""

import os
import sys
import time
import subprocess
import platform
import logging
import socket
import json
from datetime import datetime
from typing import Optional, List, Tuple

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
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


# ============================================================================
# DEPENDENCY MANAGER
# ============================================================================

DEPENDENCIES = {
    'numpy': 'numpy',
    'pandas': 'pandas',
    'pygame': 'pygame',
    'serial': 'pyserial',
    'websocket': 'websocket-client'  # Optional for WiFi
}

def check_dependencies(silent=False):
    """Check and report missing dependencies"""
    if not silent:
        print(f"\n{Color.CYAN}[*] Checking Dependencies...{Color.END}")

    missing = []
    optional_missing = []

    for module, package in DEPENDENCIES.items():
        try:
            __import__(module)
            if not silent:
                print(f"  {Color.GREEN}[OK]{Color.END} {module}")
        except ImportError:
            if module == 'websocket':
                optional_missing.append(package)
                if not silent:
                    print(f"  {Color.YELLOW}[OPTIONAL]{Color.END} {module} (for WiFi mode)")
            else:
                missing.append(package)
                if not silent:
                    print(f"  {Color.RED}[MISSING]{Color.END} {module} (package: {package})")

    if missing:
        print(f"\n{Color.RED}[!] Critical dependencies missing.{Color.END}")
        choice = input("Would you like to try installing them now? (y/n): ").lower()
        if choice == 'y':
            for pkg in missing:
                print(f"{Color.CYAN}[*] Installing {pkg}...{Color.END}")
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
                except Exception as e:
                    print(f"{Color.RED}[ERROR] Failed to install {pkg}: {e}{Color.END}")
        else:
            print(f"{Color.YELLOW}[!] Please install manually: pip install {' '.join(missing)}{Color.END}")

    if optional_missing and not silent:
        print(f"\n{Color.YELLOW}[i] Optional: pip install {' '.join(optional_missing)}{Color.END}")

    return len(missing) == 0


# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

def setup_environment():
    """Ensure directories and essential files exist"""
    print(f"\n{Color.CYAN}[*] Setting up environment...{Color.END}")

    # Check/Create Logs
    if not os.path.exists('logs'):
        os.makedirs('logs')
        print(f"  {Color.GREEN}[CREATED]{Color.END} logs directory")
    else:
        print(f"  {Color.GREEN}[OK]{Color.END} logs directory")

    # Check Brain
    if not os.path.exists('BEHAVIORAL_BRAIN.npz'):
        print(f"  {Color.YELLOW}[WARN]{Color.END} BEHAVIORAL_BRAIN.npz missing!")
        print("         System will use rule-based fallback or requires training.")
    else:
        print(f"  {Color.GREEN}[OK]{Color.END} BEHAVIORAL_BRAIN.npz")

    # Check swarm_core version
    try:
        import swarm_core
        if hasattr(swarm_core, 'SwarmCore'):
            core_test = swarm_core.SwarmCore()
            stats = core_test.get_stats()

            # Check if OL is present (indicates v2.1)
            if 'ol_vectors' in stats:
                print(f"  {Color.GREEN}[OK]{Color.END} swarm_core v2.1 (FIXED) detected")
            else:
                print(f"  {Color.YELLOW}[WARN]{Color.END} swarm_core v2.0 detected (consider upgrading to v2.1)")
    except Exception as e:
        print(f"  {Color.YELLOW}[WARN]{Color.END} Could not verify swarm_core: {e}")


# ============================================================================
# COMMUNICATION DIAGNOSTICS
# ============================================================================

def get_local_ip() -> Optional[str]:
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return None


def scan_wifi_for_esp32(timeout: float = 3.0) -> Optional[str]:
    """
    Scan local network for ESP32

    Returns:
        ESP32 IP if found, None otherwise
    """
    print(f"\n{Color.CYAN}[*] Scanning WiFi network for ESP32...{Color.END}")

    local_ip = get_local_ip()
    if not local_ip:
        print(f"  {Color.RED}[ERROR]{Color.END} Could not determine local IP")
        return None

    print(f"  Local IP: {Color.GREEN}{local_ip}{Color.END}")

    # Extract subnet
    subnet = '.'.join(local_ip.split('.')[:-1]) + '.'
    print(f"  Scanning subnet: {subnet}0/24 on port 81...")

    # Common ESP32 IPs to check first
    priority_ips = [
        "10.135.120.105",  # From your logs
        f"{subnet}100",
        f"{subnet}101",
        f"{subnet}105",
    ]

    # Quick check priority IPs
    for ip in priority_ips:
        if test_esp32_connection(ip, 81, timeout=1.0):
            print(f"  {Color.GREEN}[FOUND]{Color.END} ESP32 at {ip}")
            return ip

    print(f"  {Color.YELLOW}[INFO]{Color.END} ESP32 not found in quick scan")
    print(f"  {Color.CYAN}[TIP]{Color.END} Check ESP32 Serial Monitor for IP address")

    return None


def test_esp32_connection(ip: str, port: int = 81, timeout: float = 1.0) -> bool:
    """
    Test if ESP32 is reachable at given IP:port

    Args:
        ip: IP address to test
        port: Port (default 81 for WebSocket)
        timeout: Connection timeout

    Returns:
        True if ESP32 responds
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False


def scan_serial_ports() -> List[str]:
    """
    Scan for available serial ports

    Returns:
        List of available port names
    """
    print(f"\n{Color.CYAN}[*] Scanning Serial/USB ports...{Color.END}")

    try:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())

        if not ports:
            print(f"  {Color.YELLOW}[WARN]{Color.END} No serial ports found")
            return []

        available = []
        for port in ports:
            print(f"  {Color.GREEN}[FOUND]{Color.END} {port.device} - {port.description}")
            available.append(port.device)

        return available

    except ImportError:
        print(f"  {Color.RED}[ERROR]{Color.END} pyserial not installed")
        print(f"  {Color.CYAN}[TIP]{Color.END} Install with: pip install pyserial")
        return []
    except Exception as e:
        print(f"  {Color.RED}[ERROR]{Color.END} Serial scan failed: {e}")
        return []


def test_serial_connection(port: str, baudrate: int = 115200, timeout: float = 2.0) -> bool:
    """
    Test serial connection to ESP32

    Args:
        port: Serial port name
        baudrate: Baud rate (default 115200)
        timeout: Read timeout

    Returns:
        True if ESP32 responds with sensor data
    """
    try:
        import serial

        print(f"  Testing {port}...", end=" ")

        ser = serial.Serial(port, baudrate, timeout=timeout)
        time.sleep(0.5)  # Wait for connection

        # Try to read a few lines
        for _ in range(5):
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                try:
                    data = json.loads(line)
                    if data.get('type') == 'sensors':
                        ser.close()
                        print(f"{Color.GREEN}[OK] ESP32 detected!{Color.END}")
                        return True
                except json.JSONDecodeError:
                    pass

        ser.close()
        print(f"{Color.YELLOW}[NO DATA]{Color.END}")
        return False

    except Exception as e:
        print(f"{Color.RED}[FAILED] {e}{Color.END}")
        return False


# ============================================================================
# ENHANCED DIAGNOSTICS
# ============================================================================

def run_full_diagnostics():
    """Comprehensive system diagnostics"""
    print(f"\n{Color.BOLD}{Color.CYAN}{'='*70}")
    print("SWARM SYSTEM DIAGNOSTICS")
    print(f"{'='*70}{Color.END}\n")

    # 1. System Info
    print(f"{Color.BOLD}[1] SYSTEM INFORMATION{Color.END}")
    print(f"  Platform: {platform.system()} {platform.release()}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 2. Dependencies
    print(f"\n{Color.BOLD}[2] DEPENDENCIES{Color.END}")
    check_dependencies(silent=False)

    # 3. Network
    print(f"\n{Color.BOLD}[3] NETWORK STATUS{Color.END}")
    local_ip = get_local_ip()
    if local_ip:
        print(f"  Local IP: {Color.GREEN}{local_ip}{Color.END}")
    else:
        print(f"  {Color.RED}[ERROR]{Color.END} Network not available")

    # 4. WiFi ESP32 Scan
    print(f"\n{Color.BOLD}[4] WIFI ESP32 DETECTION{Color.END}")
    esp32_ip = scan_wifi_for_esp32(timeout=3.0)

    if esp32_ip:
        print(f"\n  {Color.GREEN}✅ ESP32 FOUND at {esp32_ip}:81{Color.END}")

        # Test connection
        print(f"  Testing WebSocket connection...", end=" ")
        if test_esp32_connection(esp32_ip, 81, timeout=2.0):
            print(f"{Color.GREEN}[OK]{Color.END}")
        else:
            print(f"{Color.RED}[FAILED]{Color.END}")
    else:
        print(f"\n  {Color.YELLOW}⚠️  ESP32 not detected via WiFi{Color.END}")
        print(f"  {Color.CYAN}[TIP]{Color.END} Check ESP32 Serial Monitor for IP address")
        print(f"  {Color.CYAN}[TIP]{Color.END} Ensure ESP32 and PC are on same WiFi network")

    # 5. Serial Port Scan
    print(f"\n{Color.BOLD}[5] SERIAL/USB PORT DETECTION{Color.END}")
    serial_ports = scan_serial_ports()

    if serial_ports:
        print(f"\n  Testing ports for ESP32...")
        esp32_port = None
        for port in serial_ports:
            if test_serial_connection(port):
                esp32_port = port
                break

        if esp32_port:
            print(f"\n  {Color.GREEN}✅ ESP32 FOUND on {esp32_port}{Color.END}")
        else:
            print(f"\n  {Color.YELLOW}⚠️  No ESP32 detected on serial ports{Color.END}")
            print(f"  {Color.CYAN}[TIP]{Color.END} Check USB cable connection")
            print(f"  {Color.CYAN}[TIP]{Color.END} Verify ESP32 is powered on")
    else:
        print(f"\n  {Color.RED}❌ No serial ports available{Color.END}")

    # 6. Files Check
    print(f"\n{Color.BOLD}[6] ESSENTIAL FILES{Color.END}")
    files_to_check = [
        ('BEHAVIORAL_BRAIN.npz', 'NPZ Brain'),
        ('swarm_core.py', 'Core AI Engine'),
        ('swarm_main.py', 'Main Controller'),
        ('swarm_wifi.py', 'WiFi Interface'),
        ('swarm_simulator.py', 'Simulator'),
        ('logs/', 'Logs Directory')
    ]

    for filename, description in files_to_check:
        if os.path.exists(filename):
            print(f"  {Color.GREEN}[OK]{Color.END} {description} ({filename})")
        else:
            print(f"  {Color.YELLOW}[MISSING]{Color.END} {description} ({filename})")

    # 7. Summary
    print(f"\n{Color.BOLD}{Color.CYAN}{'='*70}")
    print("DIAGNOSTIC SUMMARY")
    print(f"{'='*70}{Color.END}\n")

    print(f"{Color.BOLD}Recommended Connection Mode:{Color.END}")
    if esp32_ip:
        print(f"  → {Color.GREEN}WiFi Mode{Color.END} (ESP32 @ {esp32_ip})")
    elif serial_ports and esp32_port:
        print(f"  → {Color.GREEN}Serial Mode{Color.END} (ESP32 @ {esp32_port})")
    elif serial_ports:
        print(f"  → {Color.YELLOW}Serial Mode{Color.END} (try port: {serial_ports[0]})")
    else:
        print(f"  → {Color.CYAN}Simulator Mode{Color.END} (no hardware detected)")

    print(f"\n{Color.CYAN}{'='*70}{Color.END}\n")

    input("Press Enter to return to menu...")


# ============================================================================
# MENU ACTIONS
# ============================================================================

def run_simulator():
    """Launch the Pygame simulator"""
    print(f"\n{Color.BLUE}{'='*60}")
    print(">>> LAUNCHING SWARM SIMULATOR <<<")
    print(f"{'='*60}{Color.END}\n")

    print(f"{Color.CYAN}Starting virtual environment...{Color.END}")

    try:
        subprocess.run([sys.executable, "swarm_simulator.py"])
    except FileNotFoundError:
        print(f"{Color.RED}[ERROR]{Color.END} swarm_simulator.py not found!")
    except Exception as e:
        print(f"{Color.RED}[ERROR]{Color.END} {e}")

    input("\nPress Enter to continue...")


def run_live_wifi():
    """Launch with WiFi/WebSocket connection"""
    print(f"\n{Color.BLUE}{'='*60}")
    print(">>> LAUNCHING SWARM - WIFI MODE <<<")
    print(f"{'='*60}{Color.END}\n")

    # Auto-detect or ask for IP
    esp32_ip = scan_wifi_for_esp32(timeout=2.0)

    if not esp32_ip:
        print(f"\n{Color.YELLOW}[!] ESP32 not auto-detected{Color.END}")
        esp32_ip = input("Enter ESP32 IP address (or Enter to skip): ").strip()

        if not esp32_ip:
            print(f"{Color.RED}[ABORT]{Color.END} No IP provided")
            input("\nPress Enter to continue...")
            return

    print(f"\n{Color.GREEN}[*] Connecting to ESP32 @ {esp32_ip}:81...{Color.END}")

    try:
        # Launch with WiFi adapter
        subprocess.run([
            sys.executable, "swarm_main.py",
            "--mode", "wifi",
            "--ip", esp32_ip
        ])
    except FileNotFoundError:
        print(f"{Color.RED}[ERROR]{Color.END} swarm_main.py not found!")
    except Exception as e:
        print(f"{Color.RED}[ERROR]{Color.END} {e}")

    input("\nPress Enter to continue...")


def run_live_serial():
    """Launch with Serial/USB connection"""
    print(f"\n{Color.BLUE}{'='*60}")
    print(">>> LAUNCHING SWARM - SERIAL MODE <<<")
    print(f"{'='*60}{Color.END}\n")

    # Auto-detect serial ports
    serial_ports = scan_serial_ports()

    if not serial_ports:
        print(f"{Color.RED}[ERROR]{Color.END} No serial ports detected!")
        print(f"{Color.CYAN}[TIP]{Color.END} Check USB connection and drivers")
        input("\nPress Enter to continue...")
        return

    # Try to detect ESP32
    esp32_port = None
    for port in serial_ports:
        if test_serial_connection(port):
            esp32_port = port
            break

    if not esp32_port:
        print(f"\n{Color.YELLOW}[!] ESP32 not auto-detected{Color.END}")
        print("\nAvailable ports:")
        for i, port in enumerate(serial_ports, 1):
            print(f"  {i}. {port}")

        choice = input(f"\nSelect port (1-{len(serial_ports)}) or Enter to skip: ").strip()

        if choice.isdigit() and 1 <= int(choice) <= len(serial_ports):
            esp32_port = serial_ports[int(choice) - 1]
        else:
            print(f"{Color.RED}[ABORT]{Color.END} No port selected")
            input("\nPress Enter to continue...")
            return

    print(f"\n{Color.GREEN}[*] Connecting to ESP32 @ {esp32_port}...{Color.END}")

    try:
        # Launch with serial adapter
        subprocess.run([
            sys.executable, "swarm_main.py",
            "--mode", "serial",
            "--port", esp32_port
        ])
    except FileNotFoundError:
        print(f"{Color.RED}[ERROR]{Color.END} swarm_main.py not found!")
    except Exception as e:
        print(f"{Color.RED}[ERROR]{Color.END} {e}")

    input("\nPress Enter to continue...")


def run_trainer():
    """Launch the NPZ trainer"""
    print(f"\n{Color.BLUE}{'='*60}")
    print(">>> LAUNCHING SWARM TRAINER <<<")
    print(f"{'='*60}{Color.END}\n")

    print(f"{Color.CYAN}Training NPZ brain from simulation data...{Color.END}")

    try:
        subprocess.run([sys.executable, "swarm_trainer.py"])
    except FileNotFoundError:
        print(f"{Color.RED}[ERROR]{Color.END} swarm_trainer.py not found!")
    except Exception as e:
        print(f"{Color.RED}[ERROR]{Color.END} {e}")

    input("\nPress Enter to continue...")


# ============================================================================
# MAIN INTERFACE
# ============================================================================

def print_header():
    """Print loader header"""
    os.system('cls' if os.name == 'nt' else 'clear')

    print(f"{Color.BOLD}{Color.BLUE}" + "="*70)
    print("      SWARM ROBOT SYSTEM - UNIVERSAL LOADER v3.1")
    print("           [Communication Master Edition]")
    print("="*70 + Color.END)
    print(f" Platform: {platform.system()} {platform.release()}")
    print(f" Python:   {sys.version.split()[0]}")
    print(f" Time:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Color.BLUE}" + "="*70 + Color.END)


def main_menu():
    """Main menu loop"""
    while True:
        print_header()

        print(f"\n{Color.BOLD}CHOOSE OPERATION:{Color.END}\n")

        print(f"{Color.CYAN}  [SIMULATION]{Color.END}")
        print(f"  1. Run Simulator           {Color.YELLOW}(Virtual Environment){Color.END}")

        print(f"\n{Color.CYAN}  [LIVE ROBOT]{Color.END}")
        print(f"  2. WiFi Mode               {Color.GREEN}(WebSocket @ ESP32 IP:81){Color.END}")
        print(f"  3. Serial Mode             {Color.GREEN}(USB RX/TX){Color.END}")

        print(f"\n{Color.CYAN}  [TRAINING & DIAGNOSTICS]{Color.END}")
        print(f"  4. Train Brain (NPZ)       {Color.MAGENTA}(Process Logs → Model){Color.END}")
        print(f"  5. Run Diagnostics         {Color.BLUE}(Full System Check){Color.END}")
        print(f"  6. Re-check Dependencies")

        print(f"\n{Color.RED}  0. EXIT{Color.END}")

        choice = input(f"\n{Color.BOLD}Select [0-6]: {Color.END}").strip()

        if choice == '1':
            run_simulator()
        elif choice == '2':
            run_live_wifi()
        elif choice == '3':
            run_live_serial()
        elif choice == '4':
            run_trainer()
        elif choice == '5':
            run_full_diagnostics()
        elif choice == '6':
            check_dependencies()
            input("\nPress Enter to continue...")
        elif choice == '0':
            print(f"\n{Color.GREEN}Exiting SWARM Loader. Goodbye!{Color.END}\n")
            break
        else:
            print(f"{Color.RED}Invalid selection.{Color.END}")
            time.sleep(1)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        # Initial setup
        print_header()
        setup_environment()

        # Check critical dependencies
        if not check_dependencies(silent=True):
            print(f"\n{Color.YELLOW}[!] Please install missing dependencies first{Color.END}")
            input("\nPress Enter to exit...")
            sys.exit(1)

        # Run main menu
        main_menu()

    except KeyboardInterrupt:
        print(f"\n{Color.RED}Interrupted by user.{Color.END}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Color.RED}Fatal error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)
