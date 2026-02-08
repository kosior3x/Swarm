#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SWARM CORE SIMULATOR - PYGAME VISUALIZATION
"""

import pygame
import sys
import math
import socket
import threading
import json
import time
import random
import argparse
import csv
import os

# =============================================================================
# CONFIGURATION
# =============================================================================

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)
CYAN = (0, 255, 255)

# Robot settings
ROBOT_RADIUS = 30  # 30 pixels (approx 30cm)
SENSOR_RANGE = 390  # 3.9m = 390px (if 1px = 1cm)
SENSOR_ANGLE = 30  # Cone angle in degrees

class SwarmProtocol:
    """Protocol helper"""
    @staticmethod
    def encode_sensor_data(dist_left, dist_right, enc_left, enc_right, x, y, angle):
        data = {
            'type': 'SENSOR',
            'timestamp': time.time(),
            'dist_left': dist_left,   # -15 deg
            'dist_right': dist_right, # +15 deg
            'enc_left': enc_left,     # accumulated steps
            'enc_right': enc_right,   # accumulated steps
            'pos_x': x,
            'pos_y': y,
            'angle': angle
        }
        return json.dumps(data) + '\n'

    @staticmethod
    def decode_command(data_str):
        """Decode command handling multiple JSON objects"""
        try:
            lines = data_str.strip().split('\n')
            for line in reversed(lines):
                if line.strip():
                    try:
                        return json.loads(line)
                    except:
                        continue
            return None
        except:
            return None

class Robot(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((ROBOT_RADIUS*2, ROBOT_RADIUS*2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, BLUE, (ROBOT_RADIUS, ROBOT_RADIUS), ROBOT_RADIUS)
        # Direction indicator
        pygame.draw.line(self.image, WHITE, (ROBOT_RADIUS, ROBOT_RADIUS), (ROBOT_RADIUS*2, ROBOT_RADIUS), 3)

        self.original_image = self.image
        self.rect = self.image.get_rect(center=(x, y))

        self.pos = pygame.math.Vector2(x, y)
        self.angle = 0  # Degrees, 0 is right
        self.speed_left = 0
        self.speed_right = 0

        # Encoders (steps)
        self.enc_left = 0.0
        self.enc_right = 0.0

        # Sensors [angle_offset, current_dist]
        # Two sensors: Left (-15 deg), Right (+15 deg)
        self.sensors = {
            'left': [-15, SENSOR_RANGE],
            'right': [15, SENSOR_RANGE]
        }

    def update(self, dt, obstacles):
        # Differential drive kinematics
        wheel_sep = ROBOT_RADIUS * 2.0

        # Convert PWM/Speed (0-100) to pixels/sec
        v_left = self.speed_left * 2.0
        v_right = self.speed_right * 2.0

        # Update encoders (simulate steps)
        # Assuming 1 step per pixel roughly for simulation purposes
        self.enc_left += v_left * dt
        self.enc_right += v_right * dt

        v = (v_left + v_right) / 2.0
        omega = (v_right - v_left) / wheel_sep  # rad/s

        # Update angle
        self.angle += math.degrees(omega * dt)
        self.angle %= 360

        # Update position
        rad_angle = math.radians(self.angle)
        dx = v * math.cos(rad_angle) * dt
        dy = v * math.sin(rad_angle) * dt

        self.pos.x += dx
        self.pos.y += dy

        # Screen bounds
        self.pos.x = max(ROBOT_RADIUS, min(SCREEN_WIDTH - ROBOT_RADIUS, self.pos.x))
        self.pos.y = max(ROBOT_RADIUS, min(SCREEN_HEIGHT - ROBOT_RADIUS, self.pos.y))

        self.rect.center = self.pos

        # Rotate image
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        self.rect = self.image.get_rect(center=self.rect.center)

        # Update sensors
        self._update_sensors(obstacles)

    def _update_sensors(self, obstacles):
        for name, sensor in self.sensors.items():
            angle_offset = sensor[0]
            cast_angle = self.angle + angle_offset

            # Raycast
            min_dist = SENSOR_RANGE

            rad = math.radians(cast_angle)
            dir_x = math.cos(rad)
            dir_y = math.sin(rad)

            start_pos = self.pos

            # Check collisions with screen edges
            if dir_x > 0:
                d = (SCREEN_WIDTH - start_pos.x) / dir_x
                if 0 < d < min_dist: min_dist = d
            elif dir_x < 0:
                d = (0 - start_pos.x) / dir_x
                if 0 < d < min_dist: min_dist = d

            if dir_y > 0:
                d = (SCREEN_HEIGHT - start_pos.y) / dir_y
                if 0 < d < min_dist: min_dist = d
            elif dir_y < 0:
                d = (0 - start_pos.y) / dir_y
                if 0 < d < min_dist: min_dist = d

            # Check obstacles (optimized vector projection)
            for obs in obstacles:
                v_obs = obs.pos - start_pos
                v_ray = pygame.math.Vector2(dir_x, dir_y)

                t = v_obs.dot(v_ray)

                if 0 < t < min_dist:
                    closest_point = start_pos + v_ray * t
                    dist_to_ray = closest_point.distance_to(obs.pos)

                    if dist_to_ray < obs.radius:
                        x_sq = obs.radius**2 - dist_to_ray**2
                        if x_sq >= 0:
                            x = math.sqrt(x_sq)
                            d = t - x
                            if 0 < d < min_dist:
                                min_dist = d

            sensor[1] = min_dist

    def draw(self, surface):
        surface.blit(self.image, self.rect)

        # Draw sensor cones
        for name, sensor in self.sensors.items():
            angle_offset = sensor[0]
            dist = sensor[1]

            start_angle = math.radians(self.angle + angle_offset - SENSOR_ANGLE/2)
            end_angle = math.radians(self.angle + angle_offset + SENSOR_ANGLE/2)

            points = [self.pos]
            steps = 5
            for i in range(steps + 1):
                a = start_angle + (end_angle - start_angle) * i / steps
                p = self.pos + pygame.math.Vector2(math.cos(a), math.sin(a)) * dist
                points.append(p)

            color = (0, 255, 0, 50)
            if dist < 50:
                color = (255, 0, 0, 50)

            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(s, color, points)
            surface.blit(s, (0,0))

            ray_end = self.pos + pygame.math.Vector2(math.cos(math.radians(self.angle + angle_offset)), math.sin(math.radians(self.angle + angle_offset))) * dist
            pygame.draw.line(surface, RED, self.pos, ray_end, 1)

class Obstacle:
    def __init__(self, x, y, radius):
        self.pos = pygame.math.Vector2(x, y)
        self.radius = radius

    def draw(self, surface):
        pygame.draw.circle(surface, GRAY, (int(self.pos.x), int(self.pos.y)), self.radius)

class GameSimulator:
    def __init__(self, host, port, record=False):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Swarm3x Simulator - Receiver")
        self.clock = pygame.time.Clock()

        self.robot = Robot(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)
        self.obstacles = [
            Obstacle(200, 200, 40),
            Obstacle(600, 400, 50),
            Obstacle(300, 500, 30),
            Obstacle(500, 200, 40)
        ]

        self.host = host
        self.port = port
        self.record = record
        self.running = True
        self.server_socket = None
        self.client_socket = None
        self.client_address = None
        self.last_command = {}

        # Logging
        if self.record:
            self.log_file = open(f"swarm_log_{int(time.time())}.csv", 'w', newline='')
            self.writer = csv.writer(self.log_file)
            self.writer.writerow(['timestamp', 'dist_left', 'dist_right', 'enc_left', 'enc_right', 'cmd_left', 'cmd_right', 'action'])

        # Threading
        self.lock = threading.Lock()
        self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
        self.server_thread.start()

    def _server_loop(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            print(f"Server listening on {self.host}:{self.port}")

            while self.running:
                try:
                    self.server_socket.settimeout(1.0)
                    client, addr = self.server_socket.accept()
                    print(f"Client connected: {addr}")

                    with self.lock:
                        self.client_socket = client
                        self.client_address = addr

                    self._handle_client(client)

                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Server loop error: {e}")

        except Exception as e:
            print(f"Server init error: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()

    def _handle_client(self, client):
        client.settimeout(0.1)
        while self.running:
            try:
                # Receive command
                try:
                    data = client.recv(4096)
                    if not data:
                        break

                    decoded = SwarmProtocol.decode_command(data.decode('utf-8'))
                    if decoded:
                        with self.lock:
                            self.robot.speed_left = decoded.get('speed_left', 0)
                            self.robot.speed_right = decoded.get('speed_right', 0)
                            self.last_command = decoded
                except socket.timeout:
                    pass

                # Send sensor data
                with self.lock:
                    msg = SwarmProtocol.encode_sensor_data(
                        self.robot.sensors['left'][1],
                        self.robot.sensors['right'][1],
                        self.robot.enc_left,
                        self.robot.enc_right,
                        self.robot.pos.x,
                        self.robot.pos.y,
                        self.robot.angle
                    )

                    # Log data
                    if self.record:
                        self.writer.writerow([
                            time.time(),
                            self.robot.sensors['left'][1],
                            self.robot.sensors['right'][1],
                            self.robot.enc_left,
                            self.robot.enc_right,
                            self.robot.speed_left,
                            self.robot.speed_right,
                            self.last_command.get('action', '')
                        ])

                # Simulate latency/jitter if needed (optional)
                # time.sleep(random.uniform(0.001, 0.01))

                client.sendall(msg.encode('utf-8'))
                time.sleep(0.05) # ~20Hz

            except Exception as e:
                print(f"Client handler error: {e}")
                break

        with self.lock:
            self.client_socket = None
        print("Client disconnected")
        client.close()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            # Update
            self.robot.update(dt, self.obstacles)

            # Draw
            self.screen.fill(BLACK)
            for obs in self.obstacles:
                obs.draw(self.screen)
            self.robot.draw(self.screen)

            # UI Info
            font = pygame.font.Font(None, 24)
            status_text = f"Connected: {self.client_address if self.client_socket else 'No'}"
            text_surf = font.render(status_text, True, WHITE)
            self.screen.blit(text_surf, (10, 10))

            sensor_text = f"L: {int(self.robot.sensors['left'][1])} R: {int(self.robot.sensors['right'][1])}"
            sens_surf = font.render(sensor_text, True, WHITE)
            self.screen.blit(sens_surf, (10, 40))

            enc_text = f"Enc: {int(self.robot.enc_left)} / {int(self.robot.enc_right)}"
            enc_surf = font.render(enc_text, True, WHITE)
            self.screen.blit(enc_surf, (10, 70))

            if self.last_command:
                conf_text = f"Action: {self.last_command.get('action', '')} ({self.last_command.get('confidence', 0):.2f})"
                conf_surf = font.render(conf_text, True, CYAN)
                self.screen.blit(conf_surf, (10, 100))

            pygame.display.flip()

        if self.record:
            self.log_file.close()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Swarm3x Simulator')
    parser.add_argument('--host', default='0.0.0.0', help='Server host')
    parser.add_argument('--port', type=int, default=8888, help='Server port')
    parser.add_argument('--record', action='store_true', help='Record simulation data to CSV')
    args = parser.parse_args()

    sim = GameSimulator(args.host, args.port, args.record)
    sim.run()
