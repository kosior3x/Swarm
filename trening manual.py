#!/usr/bin/env python3
"""
SWARM MANUAL TRAINER - Android Touch Interface v2
Przyciski POZA mapą, bez kolizji przy starcie
"""

import pygame
import math
import random
import time
import csv
from datetime import datetime
import os

# ==============================
# KONFIGURACJA ANDROID
# ==============================

class AndroidConfig:
    def __init__(self):
        # Ekran dla Androida (pionowy) - większy na przyciski
        self.WIDTH = 900
        self.HEIGHT = 1600

        # Rozmiary obszarów
        self.MAP_HEIGHT = int(self.HEIGHT * 0.7)  # 70% na mapę
        self.CONTROLS_HEIGHT = self.HEIGHT - self.MAP_HEIGHT  # 30% na kontrolki

        # Robot
        self.ROBOT_SIZE = 40
        self.ROBOT_SPEED = 18.0
        self.TURN_SPEED = 15.0

        # Sensory
        self.SENSOR_RANGE = 400
        self.SENSOR_ANGLES = [-15, 15]

        # Przeszkody
        self.MIN_OBSTACLES = 15
        self.MAX_OBSTACLES = 25
        self.OBSTACLE_SIZE_RANGE = (40, 120)

        # Ściany
        self.WALL_THICKNESS = 20

        # Kolory dla Androida
        self.COLORS = {
            'bg': (240, 245, 250),
            'map_bg': (220, 230, 240),
            'robot': (0, 150, 255),
            'robot_front': (255, 100, 0),
            'sensor_left': (255, 80, 80),
            'sensor_right': (80, 80, 255),
            'obstacle': (180, 180, 190),
            'wall': (200, 200, 210),
            'trail': (0, 120, 200),
            'button_idle': (100, 180, 100),
            'button_pressed': (60, 140, 60),
            'button_special_idle': (180, 100, 100),
            'button_special_pressed': (140, 60, 60),
            'text': (30, 30, 30),
            'warning': (255, 100, 0),
            'danger': (255, 50, 50),
            'controls_bg': (50, 60, 70),
        }

        # Przyciski dotykowe
        self.BUTTON_SIZE = 100
        self.BUTTON_MARGIN = 20

# ==============================
# PRZYCISKI DOTYKOWE
# ==============================

class TouchButton:
    def __init__(self, x, y, size, label, key_char=None, is_special=False):
        self.rect = pygame.Rect(x - size//2, y - size//2, size, size)
        self.label = label
        self.key_char = key_char
        self.is_special = is_special
        self.pressed = False
        self.size = size

    def draw(self, screen, colors, font):
        if self.is_special:
            color = colors['button_special_pressed'] if self.pressed else colors['button_special_idle']
        else:
            color = colors['button_pressed'] if self.pressed else colors['button_idle']

        pygame.draw.rect(screen, color, self.rect, border_radius=15)

        # Obramowanie
        border_color = (30, 30, 30) if self.pressed else (70, 70, 70)
        pygame.draw.rect(screen, border_color, self.rect, 3, border_radius=15)

        # Tekst
        text_surf = font.render(self.label, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

        # Klawisz (jeśli przypisany)
        if self.key_char:
            key_surf = pygame.font.Font(None, 28).render(f"({self.key_char})", True, (255, 255, 200))
            key_rect = key_surf.get_rect(center=(self.rect.centerx, self.rect.centery + 25))
            screen.blit(key_surf, key_rect)

    def check_touch(self, pos):
        return self.rect.collidepoint(pos)

    def set_pressed(self, pressed):
        self.pressed = pressed

# ==============================
# SYSTEM PRZYCISKÓW (POZA MAPĄ)
# ==============================

class TouchControlSystem:
    def __init__(self, config):
        self.config = config
        self.buttons = {}
        self.setup_buttons()

    def setup_buttons(self):
        w, controls_top = self.config.WIDTH, self.config.MAP_HEIGHT
        size = self.config.BUTTON_SIZE
        margin = self.config.BUTTON_MARGIN

        # Centrum kontroli (na dole ekranu)
        center_x, center_y = w // 2, controls_top + (self.config.CONTROLS_HEIGHT // 2)

        # D-PAD (główna kontrola)
        self.buttons['UP'] = TouchButton(center_x, center_y - size - margin, size, "↑", "W")
        self.buttons['LEFT'] = TouchButton(center_x - size - margin, center_y, size, "←", "A")
        self.buttons['RIGHT'] = TouchButton(center_x + size + margin, center_y, size, "→", "D")
        self.buttons['DOWN'] = TouchButton(center_x, center_y + size + margin, size, "↓", "S")
        self.buttons['STOP'] = TouchButton(center_x, center_y, size, "STOP", "SPACE")

        # Przyciski specjalne (po bokach)
        self.buttons['ESCAPE_LEFT'] = TouchButton(100, center_y, size, "↰", "Q", is_special=True)
        self.buttons['ESCAPE_RIGHT'] = TouchButton(w - 100, center_y, size, "↱", "E", is_special=True)

        # Przyciski funkcyjne (u góry kontroli)
        func_y = controls_top + 60
        self.buttons['RECORD'] = TouchButton(w - 100, func_y, size//1.5, "REC", "R", is_special=True)
        self.buttons['RESET'] = TouchButton(100, func_y, size//1.5, "RST", "T", is_special=True)
        self.buttons['CHANGE'] = TouchButton(w // 2, func_y, size//1.5, "SCEN", "C", is_special=True)

    def draw(self, screen, colors, font):
        # Tło dla kontrolek
        controls_rect = pygame.Rect(0, self.config.MAP_HEIGHT, self.config.WIDTH, self.config.CONTROLS_HEIGHT)
        pygame.draw.rect(screen, colors['controls_bg'], controls_rect)

        # Separator linia
        pygame.draw.line(screen, (100, 100, 100),
                        (0, self.config.MAP_HEIGHT),
                        (self.config.WIDTH, self.config.MAP_HEIGHT), 3)

        # Przyciski
        for button in self.buttons.values():
            button.draw(screen, colors, font)

        # Etykieta
        label_font = pygame.font.Font(None, 36)
        label = label_font.render("CONTROLS", True, (200, 200, 200))
        screen.blit(label, (self.config.WIDTH//2 - 50, self.config.MAP_HEIGHT + 10))

    def handle_touch(self, pos, pressed):
        """Obsłuż dotyk - tylko w obszarze kontrolek"""
        x, y = pos
        if y < self.config.MAP_HEIGHT:
            return None  # Ignoruj dotyk na mapie

        for name, button in self.buttons.items():
            if button.check_touch(pos):
                button.set_pressed(pressed)
                return name
        return None

    def get_controls_state(self):
        """Zwraca stan wszystkich przycisków jako dict"""
        key_mapping = {
            'UP': {'action': 'FORWARD', 'speed_L': 150, 'speed_R': 150},
            'DOWN': {'action': 'BACKWARD', 'speed_L': -100, 'speed_R': -100},
            'LEFT': {'action': 'TURN_LEFT', 'speed_L': 60, 'speed_R': 120},
            'RIGHT': {'action': 'TURN_RIGHT', 'speed_L': 120, 'speed_R': 60},
            'ESCAPE_LEFT': {'action': 'ESCAPE_LEFT', 'speed_L': -100, 'speed_R': 180},
            'ESCAPE_RIGHT': {'action': 'ESCAPE_RIGHT', 'speed_L': 180, 'speed_R': -100},
            'STOP': {'action': 'STOP', 'speed_L': 0, 'speed_R': 0},
        }

        for name, button in self.buttons.items():
            if button.pressed and name in key_mapping:
                state = key_mapping[name].copy()
                state['source'] = 'MANUAL_TOUCH'
                state['confidence'] = 1.0
                state['concept'] = f"MANUAL_{name}"
                return state

        return None

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
        print(f"📝 Logger: {self.filename}")

    def log(self, dist_L, dist_R, speed_L, speed_R, action, confidence,
            decision_source, cycle, robot_x, robot_y, robot_angle, notes=""):
        dist_front = (dist_L + dist_R) / 2
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        self.writer.writerow([
            timestamp, 'MANUAL_TRAINER', f'{dist_front:.1f}', f'{dist_L:.1f}', f'{dist_R:.1f}',
            f'{speed_L:.0f}', f'{speed_R:.0f}', action, f'{confidence:.3f}',
            decision_source, cycle, f'{robot_x:.1f}', f'{robot_y:.1f}',
            f'{robot_angle:.1f}', notes[:100]
        ])
        self.row_count += 1

        if self.row_count % 100 == 0:
            self.file.flush()

    def close(self):
        self.file.close()
        print(f"💾 Saved {self.row_count} rows to {self.filename}")

# ==============================
# MANUAL ROBOT (bez kolizji przy starcie)
# ==============================

class ManualTrainingRobot:
    def __init__(self, x, y, config, logger):
        self.config = config
        self.logger = logger

        self.x = x
        self.y = y
        self.angle = random.uniform(0, 360)
        self.size = config.ROBOT_SIZE
        self.radius = self.size // 2

        # Sensory
        self.dist_L = config.SENSOR_RANGE
        self.dist_R = config.SENSOR_RANGE

        # Ruch
        self.vx = 0
        self.vy = 0
        self.angular_vel = 0
        self.speed_L = 0
        self.speed_R = 0

        # Kontrola manualna
        self.last_manual_action = None

        # Ślad
        self.trail = []

        # Statystyki
        self.cycles = 0
        self.collisions = 0
        self.distance_traveled = 0

        # Nagrywanie
        self.recording = True

        print("🤖 MANUAL TRAINING ROBOT READY")
        print("Controls in bottom 30% of screen")
        print("Recording: ON")

    def is_position_safe(self, x, y, obstacles, walls, padding=50):
        """Sprawdź czy pozycja jest wolna od przeszkód"""
        all_obs = walls + obstacles

        for obs in all_obs:
            ox, oy, ow, oh = obs
            # Zwiększony obszar kolizji dla bezpieczeństwa
            if (x > ox - padding and x < ox + ow + padding and
                y > oy - padding and y < oy + oh + padding):
                return False
        return True

    def find_safe_spawn_position(self, obstacles, walls):
        """Znajdź bezpieczną pozycję startową"""
        max_attempts = 100
        wt = self.config.WALL_THICKNESS

        for _ in range(max_attempts):
            x = random.randint(wt + 100, self.config.WIDTH - wt - 100)
            y = random.randint(wt + 100, self.config.MAP_HEIGHT - wt - 100)

            if self.is_position_safe(x, y, obstacles, walls, padding=80):
                return x, y

        # Fallback: środek mapy
        return self.config.WIDTH // 2, self.config.MAP_HEIGHT // 2

    def update_sensors(self, obstacles, walls):
        """Aktualizuj sensory"""
        all_obs = walls + obstacles

        results = []
        for angle_center in self.config.SENSOR_ANGLES:
            min_dist = self.config.SENSOR_RANGE
            total_angle = self.angle + angle_center
            angle_rad = math.radians(total_angle)
            dir_x = math.cos(angle_rad)
            dir_y = math.sin(angle_rad)

            for obs in all_obs:
                ox, oy, ow, oh = obs
                t_min, t_max = 0.0, self.config.SENSOR_RANGE

                if abs(dir_x) > 1e-10:
                    t1, t2 = (ox - self.x) / dir_x, (ox + ow - self.x) / dir_x
                    t_min, t_max = max(t_min, min(t1, t2)), min(t_max, max(t1, t2))

                if abs(dir_y) > 1e-10:
                    t1, t2 = (oy - self.y) / dir_y, (oy + oh - self.y) / dir_y
                    t_min, t_max = max(t_min, min(t1, t2)), min(t_max, max(t1, t2))

                if t_min <= t_max and 0 <= t_min < min_dist:
                    min_dist = t_min

            results.append(max(0, min_dist - self.radius))

        self.dist_L, self.dist_R = results

    def apply_manual_control(self, control_state):
        """Zastosuj kontrolę manualną"""
        if not control_state:
            # Brak kontroli - stop
            self.speed_L = 0
            self.speed_R = 0
            self.last_manual_action = None
            return

        # Zapisz akcję do logowania
        self.last_manual_action = control_state

        # Ustaw prędkości
        self.speed_L = control_state['speed_L']
        self.speed_R = control_state['speed_R']

        # Wykonaj ruch
        norm_L = self.speed_L / 150.0
        norm_R = self.speed_R / 150.0
        avg_norm = (norm_L + norm_R) / 2
        turn_rate = (norm_R - norm_L) * 2.0

        angle_rad = math.radians(self.angle)
        base_speed = self.config.ROBOT_SPEED

        # Ruch do przodu/tyłu
        if 'BACKWARD' in control_state['action']:
            self.vx = -base_speed * 0.7 * math.cos(angle_rad)
            self.vy = -base_speed * 0.7 * math.sin(angle_rad)
        else:
            self.vx = base_speed * avg_norm * math.cos(angle_rad)
            self.vy = base_speed * avg_norm * math.sin(angle_rad)

        # Skręt
        self.angular_vel = turn_rate * self.config.TURN_SPEED

    def update(self, dt, obstacles, walls, control_state=None):
        """Aktualizuj robota"""
        self.cycles += 1

        # 1. Aktualizuj sensory
        self.update_sensors(obstacles, walls)

        # 2. Zastosuj kontrolę manualną
        self.apply_manual_control(control_state)

        # 3. Zapisz starą pozycję dla kolizji
        old_x, old_y = self.x, self.y

        # 4. Zaktualizuj pozycję
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle = (self.angle + self.angular_vel * dt) % 360

        # 5. Sprawdź czy nie wyszedł poza mapę
        wt = self.config.WALL_THICKNESS
        self.x = max(wt + self.radius, min(self.config.WIDTH - wt - self.radius, self.x))
        self.y = max(wt + self.radius, min(self.config.MAP_HEIGHT - wt - self.radius, self.y))

        # 6. Sprawdź kolizje z przeszkodami
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

        if collision:
            # Cofnij ruch przy kolizji
            self.x, self.y = old_x, old_y
            self.collisions += 1
            self.speed_L = 0
            self.speed_R = 0
            self.vx = 0
            self.vy = 0
            self.angular_vel = 0

            # Komunikat tylko co 5 kolizji żeby nie spamować
            if self.collisions % 5 == 0:
                print(f"💥 Collisions: {self.collisions}")
        else:
            # Oblicz przebyty dystans
            dist_step = math.sqrt((self.x - old_x)**2 + (self.y - old_y)**2)
            self.distance_traveled += dist_step

        # 7. Loguj (jeśli nagrywanie włączone)
        if self.recording and self.last_manual_action:
            self.logger.log(
                self.dist_L, self.dist_R,
                self.speed_L, self.speed_R,
                self.last_manual_action['action'],
                1.0,
                'MANUAL_TOUCH',
                self.cycles,
                self.x, self.y, self.angle,
                notes=f"Manual: {self.last_manual_action['concept']}"
            )

        # 8. Dodaj do śladu
        self.trail.append((self.x, self.y))

        # Ogranicz długość śladu
        if len(self.trail) > 500:
            self.trail = self.trail[-500:]

    def draw(self, screen, colors, font):
        """Narysuj robota"""
        # Ślad
        if len(self.trail) > 1:
            pygame.draw.lines(screen, colors['trail'], False, self.trail, 2)

        # Robot
        pygame.draw.circle(screen, colors['robot'],
                          (int(self.x), int(self.y)), self.radius)

        # Kierunek
        dir_x = self.x + self.radius * 1.2 * math.cos(math.radians(self.angle))
        dir_y = self.y + self.radius * 1.2 * math.sin(math.radians(self.angle))
        pygame.draw.circle(screen, colors['robot_front'],
                          (int(dir_x), int(dir_y)), 8)

        # Sensory
        for i, (dist, angle_offset) in enumerate([(self.dist_L, -15), (self.dist_R, 15)]):
            total_angle = math.radians(self.angle + angle_offset)
            end_x = self.x + dist * math.cos(total_angle)
            end_y = self.y + dist * math.sin(total_angle)

            # Kolor sensora
            color = colors['sensor_left'] if i == 0 else colors['sensor_right']
            pygame.draw.line(screen, color, (self.x, self.y), (end_x, end_y), 3)

            # Punkt końcowy z gradientem
            if dist < 50:
                point_color = colors['danger']
            elif dist < 100:
                point_color = colors['warning']
            else:
                point_color = color
            pygame.draw.circle(screen, point_color, (int(end_x), int(end_y)), 6)

        # Info panel (u góry mapy)
        info_y = 10
        info = [
            f"MANUAL TRAINING",
            f"Recording: {'ON' if self.recording else 'OFF'}",
            f"Collisions: {self.collisions}",
            f"Distance: {self.distance_traveled:.0f}px",
        ]

        for text in info:
            surf = font.render(text, True, colors['text'])
            screen.blit(surf, (10, info_y))
            info_y += 35

# ==============================
# GENEROWANIE SCENARIUSZY (bez przeszkód przy starcie)
# ==============================

def generate_training_scenario(scenario_type, config, safe_zone_center, safe_zone_radius=150):
    """Generuj scenariusz z bezpieczną strefą startową"""
    wt = config.WALL_THICKNESS
    obstacles = []
    safe_x, safe_y = safe_zone_center

    if scenario_type == "narrow_corridor":
        # Wąski korytarz - zaczyna się dalej od środka
        corridor_width = 140
        center_x = config.WIDTH // 2

        # Lewa ściana (dalej od środka jeśli potrzeba)
        wall1_x = center_x - corridor_width//2 - 60
        if abs(wall1_x - safe_x) < safe_zone_radius:
            wall1_x = safe_x - safe_zone_radius - 100
        obstacles.append((wall1_x, 200, 40, config.MAP_HEIGHT - 400))

        # Prawa ściana
        wall2_x = center_x + corridor_width//2 + 20
        if abs(wall2_x - safe_x) < safe_zone_radius:
            wall2_x = safe_x + safe_zone_radius + 100
        obstacles.append((wall2_x, 200, 40, config.MAP_HEIGHT - 400))

        # Dodatkowe przeszkody (omijają bezpieczną strefę)
        for _ in range(10):
            x = random.randint(wt + 50, config.WIDTH - wt - 50)
            y = random.randint(250, config.MAP_HEIGHT - 250)

            # Sprawdź odległość od bezpiecznej strefy
            dist_to_safe = math.sqrt((x - safe_x)**2 + (y - safe_y)**2)
            if dist_to_safe > safe_zone_radius + 80:
                w = random.randint(30, 80)
                h = random.randint(30, 80)
                obstacles.append((x, y, w, h))

    elif scenario_type == "maze":
        # Labirynt z dziurą na start
        cell_size = 100
        for row in range(6):
            for col in range(5):
                x = 120 + col * cell_size
                y = 150 + row * cell_size

                # Zostaw dziurę w środku dla startu
                dist_to_safe = math.sqrt((x - safe_x)**2 + (y - safe_y)**2)
                if dist_to_safe > safe_zone_radius + 50 and random.random() > 0.3:
                    w = cell_size - 20
                    h = 30
                    obstacles.append((x, y, w, h))

    elif scenario_type == "spiral":
        # Spirala zaczynająca się dalej od środka
        center_x, center_y = config.WIDTH // 2, config.MAP_HEIGHT // 2
        radius = 180  # Zacznij dalej

        for i in range(12):
            angle = i * 30
            rad = math.radians(angle)
            x = center_x + radius * math.cos(rad) - 30
            y = center_y + radius * math.sin(rad) - 30

            # Sprawdź odległość od bezpiecznej strefy
            dist_to_safe = math.sqrt((x - safe_x)**2 + (y - safe_y)**2)
            if dist_to_safe > safe_zone_radius + 50:
                obstacles.append((x, y, 60, 60))
            radius += 35

    else:  # random
        # Losowe przeszkody omijające bezpieczną strefę
        for _ in range(random.randint(config.MIN_OBSTACLES, config.MAX_OBSTACLES)):
            w = random.randint(*config.OBSTACLE_SIZE_RANGE)
            h = random.randint(*config.OBSTACLE_SIZE_RANGE)
            x = random.randint(wt + 50, config.WIDTH - w - wt - 50)
            y = random.randint(wt + 50, config.MAP_HEIGHT - h - wt - 50)

            # Sprawdź odległość od bezpiecznej strefy
            dist_to_safe = math.sqrt((x - safe_x)**2 + (y - safe_y)**2)
            if dist_to_safe > safe_zone_radius + 80:
                obstacles.append((x, y, w, h))

    return obstacles

# ==============================
# MAIN TRAINER
# ==============================

def main():
    print("=" * 60)
    print("🤖 SWARM MANUAL TRAINER v2 - Separate Controls Area")
    print("=" * 60)

    # Inicjalizacja
    pygame.init()
    config = AndroidConfig()

    screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT))
    pygame.display.set_caption("SWARM Manual Trainer - Controls Below Map")

    font = pygame.font.Font(None, 42)
    small_font = pygame.font.Font(None, 32)
    clock = pygame.time.Clock()

    # Logger
    logger = CSVLogger()

    # System dotykowy (przyciski na dole)
    touch_system = TouchControlSystem(config)

    # Ściany (tylko w obszarze mapy)
    wt = config.WALL_THICKNESS
    walls = [
        (0, 0, wt, config.MAP_HEIGHT),
        (config.WIDTH - wt, 0, wt, config.MAP_HEIGHT),
        (0, 0, config.WIDTH, wt),
        (0, config.MAP_HEIGHT - wt, config.WIDTH, wt),
    ]

    # Bezpieczna strefa startowa (nie na środku, żeby było ciekawiej)
    safe_zone_x = config.WIDTH // 3
    safe_zone_y = config.MAP_HEIGHT // 3

    # Scenariusze
    scenarios = ["narrow_corridor", "maze", "spiral", "random"]
    current_scenario = 0

    # Generuj przeszkody (omijając bezpieczną strefę)
    obstacles = generate_training_scenario(
        scenarios[current_scenario],
        config,
        (safe_zone_x, safe_zone_y),
        safe_zone_radius=120
    )

    # Robot - zaczyna w bezpiecznej strefie
    robot = ManualTrainingRobot(safe_zone_x, safe_zone_y, config, logger)

    # Główna pętla
    running = True
    control_state = None

    print("\n📱 CONTROLS (bottom 30% of screen):")
    print("  Touch the buttons BELOW the map")
    print("  W/↑ - Forward  |  S/↓ - Backward")
    print("  A/← - Turn Left | D/→ - Turn Right")
    print("  Q - Escape Left | E - Escape Right")
    print("  SPACE - Stop")
    print("  R - Record toggle | T - Reset")
    print("  C - Change scenario")
    print("=" * 60)

    while running:
        dt = 1.0 / 60.0  # Stały krok czasowy

        # Obsługa zdarzeń
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                key_mapping = {
                    pygame.K_w: 'UP',
                    pygame.K_UP: 'UP',
                    pygame.K_s: 'DOWN',
                    pygame.K_DOWN: 'DOWN',
                    pygame.K_a: 'LEFT',
                    pygame.K_LEFT: 'LEFT',
                    pygame.K_d: 'RIGHT',
                    pygame.K_RIGHT: 'RIGHT',
                    pygame.K_q: 'ESCAPE_LEFT',
                    pygame.K_e: 'ESCAPE_RIGHT',
                    pygame.K_SPACE: 'STOP',
                    pygame.K_r: 'RECORD',
                    pygame.K_t: 'RESET',
                    pygame.K_c: 'CHANGE',
                }

                if event.key in key_mapping:
                    btn_name = key_mapping[event.key]

                    if btn_name == 'RECORD':
                        robot.recording = not robot.recording
                        status = "ON" if robot.recording else "OFF"
                        print(f"📼 Recording: {status}")

                    elif btn_name == 'RESET':
                        # Reset z nową bezpieczną pozycją
                        safe_x, safe_y = robot.find_safe_spawn_position(obstacles, walls)
                        robot = ManualTrainingRobot(safe_x, safe_y, config, logger)
                        print(f"🔄 Reset at safe position ({safe_x:.0f}, {safe_y:.0f})")

                    elif btn_name == 'CHANGE':
                        current_scenario = (current_scenario + 1) % len(scenarios)
                        safe_x, safe_y = robot.find_safe_spawn_position([], walls)  # Nowa bezpieczna pozycja
                        obstacles = generate_training_scenario(
                            scenarios[current_scenario],
                            config,
                            (safe_x, safe_y),
                            safe_zone_radius=120
                        )
                        robot = ManualTrainingRobot(safe_x, safe_y, config, logger)
                        print(f"🔄 Scenario: {scenarios[current_scenario]}")

                    else:
                        # Symuluj naciśnięcie przycisku
                        for btn in touch_system.buttons.values():
                            btn.set_pressed(False)
                        if btn_name in touch_system.buttons:
                            touch_system.buttons[btn_name].set_pressed(True)
                        control_state = touch_system.get_controls_state()

            elif event.type == pygame.KEYUP:
                # Zwolnienie klawisza
                for btn in touch_system.buttons.values():
                    btn.set_pressed(False)
                control_state = None

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Dotyk tylko w obszarze kontrolek
                btn_name = touch_system.handle_touch(event.pos, True)
                if btn_name:
                    control_state = touch_system.get_controls_state()

            elif event.type == pygame.MOUSEBUTTONUP:
                # Koniec dotyku
                touch_system.handle_touch(event.pos, False)
                control_state = None

        # Aktualizuj robota
        robot.update(dt, obstacles, walls, control_state)

        # Rysowanie
        # Tło mapy
        map_rect = pygame.Rect(0, 0, config.WIDTH, config.MAP_HEIGHT)
        pygame.draw.rect(screen, config.COLORS['map_bg'], map_rect)

        # Ściany
        for wall in walls:
            pygame.draw.rect(screen, config.COLORS['wall'], wall)

        # Przeszkody
        for obs in obstacles:
            pygame.draw.rect(screen, config.COLORS['obstacle'], obs)

        # Robot
        robot.draw(screen, config.COLORS, font)

        # Kontrolki (na dole)
        touch_system.draw(screen, config.COLORS, small_font)

        # Informacje o scenariuszu
        scenario_text = font.render(f"Scenario: {scenarios[current_scenario]}",
                                   True, config.COLORS['text'])
        screen.blit(scenario_text, (config.WIDTH // 2 - 120, config.MAP_HEIGHT - 50))

        # Aktualna akcja (jeśli jest)
        if control_state:
            action_text = font.render(f"Action: {control_state['action']}",
                                     True, config.COLORS['robot'])
            screen.blit(action_text, (10, config.MAP_HEIGHT - 100))

        pygame.display.flip()
        clock.tick(60)

    # Zakończenie
    logger.close()
    pygame.quit()

    print(f"\n🎯 TRAINING SESSION SUMMARY:")
    print(f"   Total cycles: {robot.cycles}")
    print(f"   Collisions: {robot.collisions}")
    print(f"   Distance: {robot.distance_traveled:.0f}px")
    print(f"   Log file: {logger.filename}")
    print("=" * 60)

if __name__ == "__main__":
    main()