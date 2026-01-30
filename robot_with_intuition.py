#!/usr/bin/env python3
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
        print("
Testowanie decyzji:")
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
