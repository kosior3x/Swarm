#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SWARM ROBOT - PRODUKCYJNA KONFIGURACJA SPRZĘTOWA
================================================================================

⚠️  UWAGA: TEN PLIK ZAWIERA STAŁE PARAMETRY SPRZĘTOWE!
⚠️  NIE MODYFIKOWAĆ BEZ KONSULTACJI Z ZESPOŁEM HARDWARE!
⚠️  Zmiana tych wartości może spowodować uszkodzenie robota!

Data utworzenia: 2026-01-25
Wersja: 1.0.0 PRODUCTION
================================================================================
"""

from dataclasses import dataclass
from typing import Final

# ============================================================================
# ZABEZPIECZENIE PRZED PRZYPADKOWĄ MODYFIKACJĄ
# ============================================================================
_HARDWARE_LOCK = True  # Ustaw na False tylko podczas kalibracji!

if _HARDWARE_LOCK:
    class FrozenClass:
        """Klasa bazowa blokująca modyfikację atrybutów"""
        def __setattr__(self, key, value):
            if hasattr(self, key):
                raise AttributeError(f"⛔ BŁĄD: Próba modyfikacji stałej sprzętowej '{key}'! "
                                   f"Odblokuj _HARDWARE_LOCK aby zmodyfikować.")
            super().__setattr__(key, value)
else:
    FrozenClass = object


# ============================================================================
# SILNIKI - 28BYJ-48 12V z ULN2003
# ============================================================================
@dataclass(frozen=True)
class MotorConfig:
    """Konfiguracja silnika krokowego 28BYJ-48"""

    # Nazwa i model
    MODEL: Final[str] = "28BYJ-48"
    DRIVER: Final[str] = "ULN2003"
    VOLTAGE: Final[float] = 12.0  # V

    # Parametry silnika
    STEPS_INTERNAL: Final[int] = 64      # Kroki wewnętrzne na obrót
    GEAR_RATIO: Final[int] = 64          # Przekładnia 1:64
    STEPS_PER_REV: Final[int] = 4096     # 64 * 64 = całkowite kroki na obrót

    # Wydajność
    MAX_RPM: Final[float] = 15.0         # Maksymalna prędkość obrotowa
    TORQUE_MNM: Final[float] = 34.0      # Moment obrotowy (mN·m)

    # Sekwencja sterowania (half-step dla płynności)
    STEP_SEQUENCE: Final[tuple] = (
        (1, 0, 0, 0),
        (1, 1, 0, 0),
        (0, 1, 0, 0),
        (0, 1, 1, 0),
        (0, 0, 1, 0),
        (0, 0, 1, 1),
        (0, 0, 0, 1),
        (1, 0, 0, 1),
    )

    # Piny ESP32 (GPIO)
    LEFT_MOTOR_PINS: Final[tuple] = (25, 26, 27, 14)   # IN1, IN2, IN3, IN4
    RIGHT_MOTOR_PINS: Final[tuple] = (32, 33, 12, 13)  # IN1, IN2, IN3, IN4


MOTOR = MotorConfig()


# ============================================================================
# KOŁA - 65x22mm
# ============================================================================
@dataclass(frozen=True)
class WheelConfig:
    """Konfiguracja kół"""

    DIAMETER_MM: Final[float] = 65.0     # Średnica (mm)
    WIDTH_MM: Final[float] = 22.0        # Szerokość (mm)
    CIRCUMFERENCE_MM: Final[float] = 204.2  # π * 65 = obwód (mm)

    # Prędkość liniowa
    MAX_SPEED_MMS: Final[float] = 51.0   # mm/s przy 15 RPM
    MAX_SPEED_CMS: Final[float] = 5.1    # cm/s


WHEEL = WheelConfig()


# ============================================================================
# ROBOT - WYMIARY FIZYCZNE
# ============================================================================
@dataclass(frozen=True)
class RobotDimensions:
    """Rzeczywiste wymiary robota"""

    # Wymiary zewnętrzne
    WIDTH_MM: Final[float] = 220.0       # Szerokość całkowita (22cm)
    LENGTH_MM: Final[float] = 200.0      # Długość całkowita (20cm)
    HEIGHT_MM: Final[float] = 120.0      # Wysokość (szacowana)

    # Rozstaw osi
    WHEEL_BASE_MM: Final[float] = 180.0  # Odległość między kołami
    AXLE_TO_FRONT_MM: Final[float] = 100.0  # Oś do przodu
    AXLE_TO_REAR_MM: Final[float] = 100.0   # Oś do tyłu

    # Promień skrętu (minimalny)
    MIN_TURN_RADIUS_MM: Final[float] = 110.0  # Połowa szerokości

    # Marginesy bezpieczeństwa
    CLEARANCE_MM: Final[float] = 50.0    # Margines z każdej strony
    MIN_PASSAGE_MM: Final[float] = 320.0 # Minimalne przejście (robot + 2*margines)


DIMENSIONS = RobotDimensions()


# ============================================================================
# SENSORY - HC-SR04
# ============================================================================
@dataclass(frozen=True)
class SensorConfig:
    """Konfiguracja sensorów ultradźwiękowych"""

    MODEL: Final[str] = "HC-SR04"
    VOLTAGE: Final[float] = 5.0          # V (wymaga konwertera poziomów!)

    # Zasięg
    MIN_RANGE_MM: Final[float] = 20.0    # Minimalny zasięg
    MAX_RANGE_MM: Final[float] = 4000.0  # Maksymalny zasięg (40cm praktyczny)
    PRACTICAL_RANGE_MM: Final[float] = 400.0  # Praktyczny zasięg

    # Montaż (kąty od osi robota)
    LEFT_ANGLE_DEG: Final[float] = -15.0   # Lewy sensor
    RIGHT_ANGLE_DEG: Final[float] = 15.0   # Prawy sensor

    # Piny ESP32 (GPIO)
    LEFT_TRIG: Final[int] = 4
    LEFT_ECHO: Final[int] = 5
    RIGHT_TRIG: Final[int] = 18
    RIGHT_ECHO: Final[int] = 19


SENSOR = SensorConfig()


# ============================================================================
# ESP32 - MIKROKONTROLER
# ============================================================================
@dataclass(frozen=True)
class ESP32Config:
    """Konfiguracja ESP32"""

    MODEL: Final[str] = "ESP32-WROOM-32"
    CLOCK_MHZ: Final[int] = 240

    # Komunikacja
    WIFI_ENABLED: Final[bool] = True
    WEBSOCKET_PORT: Final[int] = 81

    # UART (do debugowania)
    UART_BAUDRATE: Final[int] = 115200

    # Zasilanie
    VOLTAGE: Final[float] = 3.3          # V


ESP32 = ESP32Config()


# ============================================================================
# BATERIA
# ============================================================================
@dataclass(frozen=True)
class BatteryConfig:
    """Konfiguracja baterii"""

    TYPE: Final[str] = "Li-Ion 2S"       # 2 ogniwa szeregowo
    NOMINAL_VOLTAGE: Final[float] = 7.4  # V
    MAX_VOLTAGE: Final[float] = 8.4      # V (pełne naładowanie)
    MIN_VOLTAGE: Final[float] = 6.0      # V (odcięcie ochronne)

    # Progi ostrzegawcze
    WARNING_VOLTAGE: Final[float] = 6.8  # V - ostrzeżenie
    CRITICAL_VOLTAGE: Final[float] = 6.4 # V - zatrzymaj robota


BATTERY = BatteryConfig()


# ============================================================================
# PROGI BEZPIECZEŃSTWA (PRODUKCYJNE)
# ============================================================================
@dataclass(frozen=True)
class SafetyThresholds:
    """Progi bezpieczeństwa dla nawigacji"""

    # Dystanse (mm)
    EMERGENCY_DISTANCE_MM: Final[float] = 60.0   # Natychmiastowy unik
    DANGER_DISTANCE_MM: Final[float] = 150.0     # Aktywny unik
    WARNING_DISTANCE_MM: Final[float] = 250.0    # Zwolnij i koryguj
    SAFE_DISTANCE_MM: Final[float] = 350.0       # Normalny ruch

    # Prędkości (% maksymalnej)
    SPEED_EMERGENCY: Final[float] = 0.2          # 20% przy emergencji
    SPEED_DANGER: Final[float] = 0.4             # 40% przy niebezpieczeństwie
    SPEED_WARNING: Final[float] = 0.6            # 60% przy ostrzeżeniu
    SPEED_NORMAL: Final[float] = 1.0             # 100% normalnie


SAFETY = SafetyThresholds()


# ============================================================================
# WERYFIKACJA KONFIGURACJI
# ============================================================================
def verify_hardware_config() -> bool:
    """Weryfikuje spójność konfiguracji sprzętowej"""
    errors = []

    # Sprawdź zgodność silnika z kołem
    expected_speed = MOTOR.MAX_RPM * WHEEL.CIRCUMFERENCE_MM / 60.0
    if abs(expected_speed - WHEEL.MAX_SPEED_MMS) > 1.0:
        errors.append(f"Niezgodność prędkości: obliczona {expected_speed:.1f} vs zapisana {WHEEL.MAX_SPEED_MMS}")

    # Sprawdź wymiary
    if DIMENSIONS.MIN_PASSAGE_MM < DIMENSIONS.WIDTH_MM + 2 * DIMENSIONS.CLEARANCE_MM:
        errors.append("Minimalne przejście mniejsze niż robot + marginesy!")

    # Sprawdź napięcie baterii
    if BATTERY.MIN_VOLTAGE >= BATTERY.WARNING_VOLTAGE:
        errors.append("Próg ostrzegawczy baterii niższy niż minimum!")

    if errors:
        print("[!] BLEDY KONFIGURACJI SPRZETOWEJ:")
        for e in errors:
            print(f"   [X] {e}")
        return False

    print("[OK] Konfiguracja sprzetowa zweryfikowana pomyslnie")
    return True


# ============================================================================
# EKSPORT STAŁYCH
# ============================================================================
PRODUCTION_CONFIG = {
    'motor': MOTOR,
    'wheel': WHEEL,
    'dimensions': DIMENSIONS,
    'sensor': SENSOR,
    'esp32': ESP32,
    'battery': BATTERY,
    'safety': SAFETY,
}


if __name__ == "__main__":
    print("=" * 60)
    print("SWARM ROBOT - KONFIGURACJA PRODUKCYJNA")
    print("=" * 60)
    print(f"\nSilnik: {MOTOR.MODEL} @ {MOTOR.VOLTAGE}V")
    print(f"Koła: {WHEEL.DIAMETER_MM}x{WHEEL.WIDTH_MM}mm")
    print(f"Robot: {DIMENSIONS.WIDTH_MM}x{DIMENSIONS.LENGTH_MM}mm")
    print(f"Max prędkość: {WHEEL.MAX_SPEED_MMS} mm/s")
    print(f"Sensory: {SENSOR.MODEL} @ ±{abs(SENSOR.LEFT_ANGLE_DEG)}°")
    print()
    verify_hardware_config()
