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

# Robot settings
ROBOT_RADIUS = 30  # 30 pixels (approx 30cm in simulation scale 1px=1cm)
SENSOR_RANGE = 390  # 3.9m = 390px (if 1px = 1cm)
SENSOR_ANGLE = 30  # Cone angle in degrees

class SwarmProtocol:
    """Protocol helper"""
    @staticmethod
    def encode_sensor_data(dist_front, dist_left, dist_right, x, y, angle):
        data = {
            'type': 'SENSOR',
            'timestamp': time.time(),
            'dist_front': dist_front,
            'dist_left': dist_left,
            'dist_right': dist_right,
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

        # Sensors [angle_offset, current_dist]
        self.sensors = {
            'front': [0, SENSOR_RANGE],
            'left': [-45, SENSOR_RANGE], # -45 degrees
            'right': [45, SENSOR_RANGE]  # +45 degrees
        }

    def update(self, dt, obstacles):
        # Differential drive kinematics
        # Wheel separation approx ROBOT_RADIUS * 2
        wheel_sep = ROBOT_RADIUS * 2.0

        # Convert PWM/Speed (0-100) to pixels/sec
        # Max speed 100 -> 100 px/s (approx 1m/s)
        v_left = self.speed_left * 2.0
        v_right = self.speed_right * 2.0

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

            # Check walls (simple box)
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

            # Check obstacles
            for obs in obstacles:
                # Simplified collision: check points along the ray
                # Optimized: Vector projection
                v_obs = obs.pos - start_pos
                v_ray = pygame.math.Vector2(dir_x, dir_y)

                # Project v_obs onto v_ray
                t = v_obs.dot(v_ray)

                if 0 < t < min_dist:
                    closest_point = start_pos + v_ray * t
                    dist_to_ray = closest_point.distance_to(obs.pos)

                    if dist_to_ray < obs.radius:
                        # Intersection found, calculate precise distance
                        # Triangle: obs.radius^2 = dist_to_ray^2 + x^2
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

            # Draw cone (approximate with polygon)
            points = [self.pos]
            steps = 5
            for i in range(steps + 1):
                a = start_angle + (end_angle - start_angle) * i / steps
                p = self.pos + pygame.math.Vector2(math.cos(a), math.sin(a)) * dist
                points.append(p)

            color = (0, 255, 0, 50) # Transparent green
            if dist < 50:
                color = (255, 0, 0, 50)

            # Pygame doesn't support alpha on polygons directly nicely without surface
            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(s, color, points)
            surface.blit(s, (0,0))

            # Draw ray line
            ray_end = self.pos + pygame.math.Vector2(math.cos(math.radians(self.angle + angle_offset)), math.sin(math.radians(self.angle + angle_offset))) * dist
            pygame.draw.line(surface, RED, self.pos, ray_end, 1)

class Obstacle:
    def __init__(self, x, y, radius):
        self.pos = pygame.math.Vector2(x, y)
        self.radius = radius

    def draw(self, surface):
        pygame.draw.circle(surface, GRAY, (int(self.pos.x), int(self.pos.y)), self.radius)

class GameSimulator:
    def __init__(self, host, port):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Swarm3x Simulator")
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
        self.running = True
        self.server_socket = None
        self.client_socket = None
        self.client_address = None

        # Threading for server
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

                    # Process potentially multiple JSONs
                    decoded = SwarmProtocol.decode_command(data.decode('utf-8'))
                    if decoded:
                        with self.lock:
                            # Update robot speeds
                            self.robot.speed_left = decoded.get('speed_left', 0)
                            self.robot.speed_right = decoded.get('speed_right', 0)
                except socket.timeout:
                    pass

                # Send sensor data
                with self.lock:
                    msg = SwarmProtocol.encode_sensor_data(
                        self.robot.sensors['front'][1],
                        self.robot.sensors['left'][1],
                        self.robot.sensors['right'][1],
                        self.robot.pos.x,
                        self.robot.pos.y,
                        self.robot.angle
                    )

                client.sendall(msg.encode('utf-8'))
                time.sleep(0.05) # Send at ~20Hz

            except Exception as e:
                print(f"Client handler error: {e}")
                break

        with self.lock:
            self.client_socket = None
        print("Client disconnected")
        client.close()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  # Seconds

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

            sensor_text = f"F: {int(self.robot.sensors['front'][1])} L: {int(self.robot.sensors['left'][1])} R: {int(self.robot.sensors['right'][1])}"
            sens_surf = font.render(sensor_text, True, WHITE)
            self.screen.blit(sens_surf, (10, 40))

            pygame.display.flip()

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Swarm3x Simulator')
    parser.add_argument('--host', default='0.0.0.0', help='Server host')
    parser.add_argument('--port', type=int, default=8888, help='Server port')
    args = parser.parse_args()

    sim = GameSimulator(args.host, args.port)
    sim.run()
