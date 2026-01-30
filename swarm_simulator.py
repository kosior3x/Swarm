#!/usr/bin/env python3
"""
SWARM SIMULATOR - 2-Sensor Robot Simulation
Symuluje robota trojkolowego z 2 czujnikami HC-SR04 (±15 deg)
Generuje dane syntetyczne dla treningu NPZ
"""

import pygame
import math
import random
import time
import csv
from collections import deque
from datetime import datetime
import os
import numpy as np

# IMPORT SWARM CORE (NEW ARCHITECTURE)
try:
    # Try new architecture first
    from swarm_main import SwarmCoreController, DataSource, SwarmConfig
    CORE_AVAILABLE = True
    print("[OK] Imported from swarm_main (new architecture)")
except ImportError:
    try:
        # Fallback to legacy
        from swarm_unified_core import SwarmCoreController, DataSource, SwarmConfig
        CORE_AVAILABLE = True
        print("[OK] Imported from swarm_unified_core (legacy)")
    except ImportError:
        CORE_AVAILABLE = False
        print("[ERROR] Could not import SwarmCore!")

print(f"pygame version: {pygame.version.ver}")
print("=" * 60)
print("SWARM SIMULATOR - FIXED VERSION")
print("=" * 60)
print("Poprawki:")
print("1. THROTTLING decyzji (300ms między decyzjami)")
print("2. ACTION DURATION (każda akcja ma czas na wykonanie)")
print("3. POPRAWIONE KIERUNKI: lewa ściana → skręt w prawo")
print("4. ULTRA CRITICAL safety (30mm = natychmiastowa reakcja)")
print("=" * 60)

# ==============================
# KONFIGURACJA
# ==============================

class Config:
    def __init__(self):
        # Okno
        self.WIDTH = 1050
        self.HEIGHT = 1850
        self.FPS = 60

        # Robot - parametry fizyczne wg specyfikacji
        # Wymiary: 22cm x 20cm (skala 1:3 dla wizualizacji)
        self.ROBOT_WIDTH = 73           # 220mm / 3
        self.ROBOT_LENGTH = 67          # 200mm / 3
        self.ROBOT_SIZE = 40            # Średnica kolizyjna

        # Koła 65x22mm + Silnik 28BYJ-48 12V
        self.WHEEL_DIAMETER = 65        # mm (rzeczywiste)
        self.WHEEL_CIRCUMFERENCE = 204  # π * 65mm
        self.MOTOR_STEPS_PER_REV = 4096 # 28BYJ-48 z przekładnią 1:64
        self.MOTOR_MAX_RPM = 15.0       # Max przy 12V
        self.MAX_SPEED_MMS = 51.0       # mm/s (15 RPM * 204mm / 60s)

        # Prędkość symulacji (skalowana)
        # 51 mm/s rzeczywiste / 3 = 17 px/s w symulacji = ~0.28 px/frame przy 60fps
        self.ROBOT_SPEED = 28.0          # px/frame (odpowiada ~40mm/s rzeczywiste)
        self.TURN_SPEED = 20.0           # Stopery skręcają wolno ale precyzyjnie

        # 2 SENSORAMY HC-SR04 (±15 stopni od osi)
        self.SENSOR_RANGE = 400     # Realny zasięg 40cm
        self.SENSOR_ANGLES = [-13, 13]

        # Przeszkody
        self.MIN_OBSTACLES = 29
        self.MAX_OBSTACLES = 32
        self.OBSTACLE_MIN_SIZE = 50
        self.OBSTACLE_MAX_SIZE = 100

        self.WALL_THICKNESS = 20

        # Progi decyzyjne - DOPASOWANE DO NOWYCH USTAWIEN
        self.DANGER_DISTANCE = 80       # 90px = 9cm (odpowiada 60mm w core)
        self.WARNING_DISTANCE = 130     # 150px = 15cm (odpowiada 100mm w core)
        self.SAFE_DISTANCE = 180

        self.SPAWN_X = self.WIDTH // 2
        self.SPAWN_Y = self.HEIGHT // 2
        self.SAFE_ZONE_RADIUS = 200

        # Kolory
        self.COLORS = {
            'bg': (35, 40, 50),
            'robot': (60, 180, 120),
            'robot_front': (255, 200, 60),
            'sensor_left': (255, 100, 100),   # Czerwony - lewy
            'sensor_right': (100, 100, 255),  # Niebieski - prawy
            'sensor_good': (80, 200, 80),
            'sensor_warn': (255, 180, 60),
            'sensor_danger': (255, 80, 80),
            'obstacle': (80, 85, 95),
            'wall': (60, 65, 75),
            'trail': (50, 120, 255),    # Wyrazisty niebieski
            'text': (220, 220, 230),
            'alert': (255, 60, 60),
        }


# ==============================
# CSV LOGGER
# ==============================

class CSVLogger:
    def __init__(self, log_dir="logs"):
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.filename = os.path.join(log_dir, f'train_sim_{timestamp}.csv')

        self.file = open(self.filename, 'w', newline='', encoding='utf-8')
        self.writer = csv.writer(self.file)
        self.writer.writerow([
            'timestamp', 'source', 'dist_front', 'dist_left', 'dist_right',
            'speed_left', 'speed_right', 'action', 'confidence',
            'decision_source', 'cycle', 'robot_x', 'robot_y', 'robot_angle', 'notes'
        ])
        self.file.flush()
        self.row_count = 0
        print(f"Logger: {self.filename}")

    def log(self, dist_L, dist_R, speed_L, speed_R, action, confidence,
            decision_source, cycle, robot_x, robot_y, robot_angle, notes=""):
        dist_front = (dist_L + dist_R) / 2
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        # SANITIZE NOTES - usuń przecinki i ogranicz długość
        clean_notes = str(notes).replace(',', ';').replace('\n', ' ')[:50]

        self.writer.writerow([
            timestamp, 'SIM', f'{dist_front:.1f}', f'{dist_L:.1f}', f'{dist_R:.1f}',
            f'{speed_L:.0f}', f'{speed_R:.0f}', action, f'{confidence:.3f}',
            decision_source, cycle, f'{robot_x:.1f}', f'{robot_y:.1f}',
            f'{robot_angle:.1f}', clean_notes
        ])
        self.row_count += 1
        if self.row_count % 50 == 0:
            self.file.flush()

    def close(self):
        self.file.flush()
        self.file.close()
        print(f"Saved {self.row_count} rows to {self.filename}")


# ==============================
# ROBOT
# ==============================

class SimRobot:
    def __init__(self, x, y, config, logger, brain=None):
        self.config = config
        self.logger = logger
        self.x = x
        self.y = y
        self.angle = random.uniform(0, 360)
        self.size = config.ROBOT_SIZE
        self.radius = self.size // 2

        # Podłączamy UNIFIED CORE jako mózg
        if brain:
            self.brain = brain
        else:
            if CORE_AVAILABLE:
                self.brain = SwarmCoreController(source=DataSource.SIMULATION)
            else:
                print("!!! CRITICAL: swarm_unified_core.py not found!")
                import sys
                sys.exit(1)

        # 2 Sensory (±15 deg)
        self.dist_L = config.SENSOR_RANGE
        self.dist_R = config.SENSOR_RANGE

        # Ruch
        self.vx = 0
        self.vy = 0
        self.angular_vel = 0
        self.speed_L = 0
        self.speed_R = 0

        # THROTTLING DECYZJI
        self.last_decision_time = 0
        self.decision_interval = 0.3  # 300ms między decyzjami
        self.current_action = None
        self.action_start_time = 0
        self.action_completed = True
        self.action_duration = 0.6  # 400ms na wykonanie akcji

        # Fizyczne cele (do płynnej interpolacji)
        self.target_speed_L = 0
        self.target_speed_R = 0
        self.current_target_speed_L = 0
        self.current_target_speed_R = 0

        # Statystyki
        self.cycles = 0
        self.collisions = 0
        self.positive = 0
        self.negative = 0
        self.distance_traveled = 0

        # Ślad całej trasy (bez limitu długości)
        self.trail = []
        self.last_decision = None

        # Emergency monitoring
        self.last_emergency_check = 0
        self.emergency_check_interval = 0.05  # 50ms

    def update_sensors(self, obstacles, walls):
        """Aktualizacja 2 sensorow - SYMULACJA SZEROKIEJ WIĄZKI"""
        all_obs = walls + obstacles

        # HC-SR04 ma wiązkę około 15-30 stopni.
        # Symulujemy to rzucając 5 promieni na każdy sensor w zakresie +/- 12 stopni
        beam_offsets = [-12, -6, 0, 6, 12]

        results = []
        for i, angle_center in enumerate(self.config.SENSOR_ANGLES):
            min_sensor_dist = self.config.SENSOR_RANGE

            for b_off in beam_offsets:
                total_angle = self.angle + angle_center + b_off
                angle_rad = math.radians(total_angle)
                dir_x = math.cos(angle_rad)
                dir_y = math.sin(angle_rad)

                # Raycast dla pojedynczego promienia wiązki
                for obs in all_obs:
                    obs_x, obs_y, obs_w, obs_h = obs
                    t_min, t_max = 0.0, self.config.SENSOR_RANGE

                    if abs(dir_x) > 1e-10:
                        t1, t2 = (obs_x - self.x) / dir_x, (obs_x + obs_w - self.x) / dir_x
                        t_min, t_max = max(t_min, min(t1, t2)), min(t_max, max(t1, t2))
                    elif self.x < obs_x or self.x > obs_x + obs_w: continue

                    if abs(dir_y) > 1e-10:
                        t1, t2 = (obs_y - self.y) / dir_y, (obs_y + obs_h - self.y) / dir_y
                        t_min, t_max = max(t_min, min(t1, t2)), min(t_max, max(t1, t2))
                    elif self.y < obs_y or self.y > obs_y + obs_h: continue

                    if t_min <= t_max and 0 <= t_min < min_sensor_dist:
                        min_sensor_dist = t_min

            # Na koniec odejmij promień robota
            results.append(max(0, min_sensor_dist - self.radius*0.65))

        self.dist_L, self.dist_R = results

    def _check_emergency(self):
        """Sprawdź czy sytuacja jest awaryjna (ULTRA CRITICAL)"""
        current_time = time.time()
        if current_time - self.last_emergency_check < self.emergency_check_interval:
            return False

        self.last_emergency_check = current_time

        # ULTRA CRITICAL w symulacji (30px = ~30mm)
        ULTRA_CRITICAL = 35

        if self.dist_L < ULTRA_CRITICAL or self.dist_R < ULTRA_CRITICAL:
            # Emergency! Przerywamy obecną akcję
            self.action_completed = True
            print(f"[EMERGENCY!] L:{self.dist_L:.0f} R:{self.dist_R:.0f}")
            return True

        return False

    def update(self, dt, obstacles, walls):
        """Aktualizacja robota z THROTTLINGIEM"""
        self.cycles += 1
        current_time = time.time()

        # 1. ZAWSZE aktualizuj sensory
        self.update_sensors(obstacles, walls)

        # 2. SPRAWDŹ EMERGENCY (działa niezależnie od wszystkiego)
        emergency_detected = self._check_emergency()

        # 3. SPRAWDŹ CZY AKCJA SIĘ ZAKOŃCZYŁA
        if not self.action_completed:
            if current_time - self.action_start_time >= self.action_duration:
                self.action_completed = True
                # DEBUG
                if self.current_action:
                    print(f"[ACTION COMPLETED] {self.current_action.get('concept', '')}")

        # 4. PODEJMIJ NOWĄ DECYZJĘ tylko jeśli:
        #    - minął wymagany interval (300ms)
        #    - ORAZ akcja jest zakończona
        #    - LUB wykryto emergency
        can_make_decision = (
            (current_time - self.last_decision_time >= self.decision_interval) and
            (self.action_completed or emergency_detected)
        )

        if can_make_decision or emergency_detected:
            self.last_decision_time = current_time

            # Podejmij decyzję
            dist_F = (self.dist_L + self.dist_R) / 2
            decision = self.brain.process_sensors(
                dist_front=dist_F,
                dist_left=self.dist_L,
                dist_right=self.dist_R,
                current_speed_l=self.speed_L,
                current_speed_r=self.speed_R,
                robot_x=self.x,
                robot_y=self.y,
                robot_angle=self.angle
            )

            self.last_decision = decision

            # Rozpocznij nową akcję jeśli to nowa decyzja
            if (not self.current_action or
                decision['concept'] != self.current_action.get('concept', '') or
                emergency_detected):

                self.current_action = decision
                self.action_start_time = current_time
                self.action_completed = False

                # Ustaw cele
                self.target_speed_L = decision['speed_left']
                self.target_speed_R = decision['speed_right']

                # DEBUG - pokaż tylko nowe decyzje, nie powtórzenia
                if emergency_detected:
                    print(f"[EMERGENCY DECISION] {decision['concept']} | "
                          f"L:{self.dist_L:.0f} R:{self.dist_R:.0f} | "
                          f"Speeds: {self.target_speed_L:.0f}/{self.target_speed_R:.0f}")
                else:
                    print(f"[NEW DECISION] {decision['concept']} | "
                          f"L:{self.dist_L:.0f} R:{self.dist_R:.0f} | "
                          f"Speeds: {self.target_speed_L:.0f}/{self.target_speed_R:.0f}")

        # 5. WYKONAJ AKCJĘ (płynna interpolacja do celów)
        if not self.action_completed:
            # Interpoluj do target speeds
            ACCEL_RATE = 3.0  # Jak szybko zmieniać prędkość

            self.current_target_speed_L += (self.target_speed_L - self.current_target_speed_L) * ACCEL_RATE * dt
            self.current_target_speed_R += (self.target_speed_R - self.current_target_speed_R) * ACCEL_RATE * dt

            # Clamp
            self.current_target_speed_L = max(0, min(150, self.current_target_speed_L))
            self.current_target_speed_R = max(0, min(150, self.current_target_speed_R))

            # Ustaw rzeczywiste prędkości
            self.speed_L = self.current_target_speed_L
            self.speed_R = self.current_target_speed_R

            # Wykonaj ruch na podstawie bieżących prędkości
            self._execute_current()

        # 6. RUCH FIZYCZNY
        old_x, old_y = self.x, self.y
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle = (self.angle + self.angular_vel * dt) % 360

        # 7. KOLIZJE
        collision = False
        all_obs = walls + obstacles

        for obs in all_obs:
            ox, oy, ow, oh = obs
            closest_x = max(ox, min(self.x, ox + ow))
            closest_y = max(oy, min(self.y, oy + oh))
            dx = self.x - closest_x
            dy = self.y - closest_y
            if dx*dx + dy*dy < self.radius * self.radius:
                collision = True
                break

        # 8. BEHAWIORYSTYKA
        if collision:
            self.x, self.y = old_x, old_y
            self.collisions += 1
            self.negative += 1
            # Behawioralna kara
            if hasattr(self.brain, 'absr'):
                self.brain.absr.feedback(False)
            behavior_note = "CRASH"

            # Przerywamy akcję po kolizji
            self.action_completed = True
        else:
            # Dystans tylko przy braku kolizji
            dist_step = math.sqrt((self.x - old_x)**2 + (self.y - old_y)**2)
            self.distance_traveled += dist_step

            # Ocena sukcesu
            min_dist = min(self.dist_L, self.dist_R)
            reward = (self.config.ROBOT_SPEED / 10.0)
            behavior_note = "SMOOTH"

            if min_dist < self.config.WARNING_DISTANCE and min_dist > self.config.DANGER_DISTANCE:
                reward += 5.0
                behavior_note = "PRO_AVOIDANCE"
                self.positive += 1

        # 9. BRAIN FEEDBACK (tylko jeśli akcja zakończona i bez kolizji)
        if self.action_completed and not collision and hasattr(self.brain, 'absr'):
            self.brain.absr.feedback(True)

        # 10. LOG (zawsze loguj, nawet jeśli to ta sama decyzja)
        if self.last_decision:
            self.logger.log(
                self.dist_L, self.dist_R,
                self.speed_L, self.speed_R,
                self.last_decision['action'], self.last_decision.get('confidence', 1.0),
                self.last_decision.get('source', 'UNIFIED'), self.cycles,
                self.x, self.y, self.angle,
                notes=self.last_decision.get('concept', '')
            )

        # 11. ŚLAD
        self.trail.append((self.x, self.y))

    def _execute_current(self):
        """Wykonaj aktualną akcję na podstawie bieżących prędkości"""
        norm_L = self.speed_L / 150.0
        norm_R = self.speed_R / 150.0
        avg_norm = (norm_L + norm_R) / 2
        turn_rate = (norm_R - norm_L) * 2.0

        angle_rad = math.radians(self.angle)
        base_speed = self.config.ROBOT_SPEED

        # Obsługa specjalnych akcji
        if self.current_action and 'ESCAPE' in self.current_action.get('action', ''):
            # Ruch do tyłu
            self.vx = -base_speed * 0.8 * math.cos(angle_rad)
            self.vy = -base_speed * 0.8 * math.sin(angle_rad)
            self.angular_vel = turn_rate * self.config.TURN_SPEED * 2
        elif self.current_action and ('EMERGENCY' in self.current_action.get('concept', '') or
                                     'ULTRA' in self.current_action.get('concept', '')):
            # Emergency - agresywny manewr
            self.vx = base_speed * 0.7 * avg_norm * math.cos(angle_rad)
            self.vy = base_speed * 0.7 * avg_norm * math.sin(angle_rad)
            self.angular_vel = turn_rate * self.config.TURN_SPEED * 3
        elif self.current_action and 'TURN' in self.current_action.get('action', ''):
            # Skręt
            self.vx = base_speed * 0.5 * avg_norm * math.cos(angle_rad)
            self.vy = base_speed * 0.5 * avg_norm * math.sin(angle_rad)
            self.angular_vel = turn_rate * self.config.TURN_SPEED * 2.5
        else:
            # Normalny ruch
            self.vx = base_speed * avg_norm * math.cos(angle_rad)
            self.vy = base_speed * avg_norm * math.sin(angle_rad)
            self.angular_vel = turn_rate * self.config.TURN_SPEED

    def draw(self, screen, font):
        """Rysowanie"""
        # Ślad (Cienka, niebieska linia ciągła)
        if len(self.trail) > 1:
            pygame.draw.lines(screen, self.config.COLORS['trail'], False, self.trail, 1)

        # Robot
        pygame.draw.circle(screen, self.config.COLORS['robot'],
                          (int(self.x), int(self.y)), self.radius)

        # Kierunek
        dir_x = self.x + self.radius * 1.2 * math.cos(math.radians(self.angle))
        dir_y = self.y + self.radius * 1.2 * math.sin(math.radians(self.angle))
        pygame.draw.circle(screen, self.config.COLORS['robot_front'],
                          (int(dir_x), int(dir_y)), 6)

        # 2 Sensory
        for i, (dist, angle_offset) in enumerate([(self.dist_L, -15), (self.dist_R, 15)]):
            total_angle = math.radians(self.angle + angle_offset)
            end_x = self.x + dist * math.cos(total_angle)
            end_y = self.y + dist * math.sin(total_angle)

            # Kolor
            if dist < self.config.DANGER_DISTANCE:
                color = self.config.COLORS['sensor_danger']
            elif dist < self.config.WARNING_DISTANCE:
                color = self.config.COLORS['sensor_warn']
            else:
                color = self.config.COLORS['sensor_good']

            # Linia sensora
            base_color = self.config.COLORS['sensor_left'] if i == 0 else self.config.COLORS['sensor_right']
            pygame.draw.line(screen, base_color, (self.x, self.y), (end_x, end_y), 2)
            pygame.draw.circle(screen, color, (int(end_x), int(end_y)), 5)

        # Panel info
        if self.last_decision:
            y = 10

            # Kolor tekstu - czerwony dla emergency
            text_color = self.config.COLORS['text']
            if (self.last_decision.get('source') == 'SAFETY_OVERRIDE' or
                'ULTRA' in self.last_decision.get('concept', '') or
                'EMERGENCY' in self.last_decision.get('concept', '')):
                text_color = self.config.COLORS['alert']

            info = [
                f"Action: {self.last_decision['action']}",
                f"Concept: {self.last_decision['concept']}",
                f"Source: {self.last_decision['source']}",
                f"Conf: {self.last_decision['confidence']:.0%}",
                f"L: {self.dist_L:.0f}  R: {self.dist_R:.0f}",
                f"Speed: {self.speed_L:.0f}/{self.speed_R:.0f}",
                f"Action: {'COMPLETE' if self.action_completed else 'RUNNING'}",
            ]
            for text in info:
                surf = font.render(text, True, text_color)
                screen.blit(surf, (10, y))
                y += 32

    def close(self):
        # Nie zamykaj loggera tutaj, aby pozwolić na reset (klawisz R)
        pass


def generate_obstacles(config):
    """Generuje listę przeszkód omijając strefę respawn"""
    wt = config.WALL_THICKNESS
    obstacles = []
    num_to_gen = random.randint(config.MIN_OBSTACLES, config.MAX_OBSTACLES)

    attempts = 0
    while len(obstacles) < num_to_gen and attempts < 200:
        attempts += 1
        # Generuj prostokąty (jeden bok dłuższy)
        w = random.randint(config.OBSTACLE_MIN_SIZE, config.OBSTACLE_MAX_SIZE * 2)
        h = random.randint(config.OBSTACLE_MIN_SIZE, config.OBSTACLE_MAX_SIZE // 2)
        if random.random() > 0.5: w, h = h, w

        x = random.randint(wt + 60, config.WIDTH - w - wt - 60)
        y = random.randint(wt + 60, config.HEIGHT - h - wt - 60)

        # Strefa bezpieczna (respawn) - nie pozwól na przeszkodę w promieniu SAFE_ZONE_RADIUS
        # Sprawdzamy kolizję prostokąta przeszkody z prostokątem bezpiecznym
        safe_margin = config.SAFE_ZONE_RADIUS
        if (x < config.SPAWN_X + safe_margin and x + w > config.SPAWN_X - safe_margin and
            y < config.SPAWN_Y + safe_margin and y + h > config.SPAWN_Y - safe_margin):
            continue

        obstacles.append((x, y, w, h))

    return obstacles


# ==============================
# MAIN
# ==============================

def main():
    print("SWARM 2-Sensor Simulator - THROTTLED DECISION MODE")
    print("=" * 60)

    pygame.init()
    config = Config()

    screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT))
    pygame.display.set_caption("SWARM 2-Sensor Simulator (±15 deg) - THROTTLED")

    font = pygame.font.Font(None, 44)
    clock = pygame.time.Clock()

    # Logger
    logger = CSVLogger()

    # Robot
    robot = SimRobot(config.SPAWN_X, config.SPAWN_Y, config, logger)

    # Sciany
    wt = config.WALL_THICKNESS
    walls = [
        (0, 0, wt, config.HEIGHT),
        (config.WIDTH - wt, 0, wt, config.HEIGHT),
        (0, 0, config.WIDTH, wt),
        (0, config.HEIGHT - wt, config.WIDTH, wt),
    ]

    # Przeszkody
    obstacles = generate_obstacles(config)

    running = True
    paused = False
    start_time = time.time()

    print("Controls: SPACE=pause, R=reset, ESC=quit")
    print("=" * 60)

    while running:
        # STAŁY krok czasowy (niezależny od FPS)
        dt = 1.0 / 60.0  # Stałe 60 FPS

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    # RESET z zachowaniem Braina i Loggera!
                    old_brain = robot.brain
                    robot = SimRobot(config.SPAWN_X, config.SPAWN_Y, config, logger, brain=old_brain)
                    obstacles = generate_obstacles(config)
                    print(f"Reset: Continuity preserved. Brain: {len(old_brain.npz.words)} concepts loaded.")

        if not paused:
            robot.update(dt, obstacles, walls)

        # Rysowanie
        screen.fill(config.COLORS['bg'])

        # Sciany
        for wall in walls:
            pygame.draw.rect(screen, config.COLORS['wall'], wall)

        # Przeszkody - ostre prostokąty
        for obs in obstacles:
            pygame.draw.rect(screen, config.COLORS['obstacle'], obs)

        # Robot
        robot.draw(screen, font)

        # Statystyki
        elapsed = time.time() - start_time
        stats = [
            f"Time: {elapsed:.0f}s",
            f"Cycles: {robot.cycles}",
            f"+{robot.positive} / -{robot.negative}",
            f"Dist: {robot.distance_traveled:.0f}px",
            f"Decisions: {robot.cycles / max(1, elapsed):.1f}/s",
        ]
        y = config.HEIGHT - 110
        for stat in stats:
            surf = font.render(stat, True, config.COLORS['text'])
            screen.blit(surf, (10, y))
            y += 32

        if paused:
            pause_surf = font.render("PAUSED - SPACE to resume", True, (255, 255, 100))
            screen.blit(pause_surf, (config.WIDTH // 2 - 100, config.HEIGHT // 2))

        pygame.display.flip()

        # Ogranicz do 60 FPS (zapobiega przyspieszaniu przy zminimalizowanym oknie)
        clock.tick(60)

    # Zapisz wagi BLL i OL przed wyjściem!
    if hasattr(robot.brain, 'absr'):
        robot.brain.absr._save_learning_data()
    robot.close()
    logger.close()
    pygame.quit()

    print(f"\nSimulation ended: {robot.cycles} cycles")
    print(f"Positive: {robot.positive}, Negative: {robot.negative}")
    print(f"Distance: {robot.distance_traveled:.0f}px")
    print(f"Decision rate: {robot.cycles / max(1, elapsed):.1f} decisions/s")


if __name__ == "__main__":
    main()