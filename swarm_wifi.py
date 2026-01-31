#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SWARM WIFI INTERFACE - UNIFIED VERSION 2.1
Compatible with SwarmMain Handshake Protocol
"""

import json
import socket
import threading
import time
import logging
from typing import Optional, Dict
from collections import deque

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('SwarmWiFi')

class SimpleWebSocket:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False

    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(3.0)
            self.socket.connect((self.host, self.port))

            handshake = (
                f"GET / HTTP/1.1\r\n"
                f"Host: {self.host}:{self.port}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Version: 13\r\n\r\n"
            )
            self.socket.send(handshake.encode())
            response = self.socket.recv(1024).decode('utf-8', errors='ignore')

            if "101" in response or "Upgrade" in response:
                self.connected = True
                self.socket.setblocking(False)
                return True
            return False
        except Exception as e:
            logger.error(f"Connect error: {e}")
            return False

    def send(self, message: str) -> bool:
        if not self.connected: return False
        try:
            self.socket.send((message + "\n").encode())
            return True
        except:
            self.connected = False
            return False

    def recv(self) -> Optional[str]:
        if not self.connected: return None
        try:
            data = self.socket.recv(4096)
            return data.decode('utf-8', errors='ignore').strip() if data else None
        except BlockingIOError:
            return None
        except:
            return None

class SwarmWiFiController:
    def __init__(self, esp32_ip: str = "10.135.120.105"):
        self.esp32_ip = esp32_ip
        self.ws = SimpleWebSocket(self.esp32_ip, 81)
        self.connected = False
        self.sensor_data = {}
        self.running = False

    def start(self) -> bool:
        if self.ws.connect():
            self.connected = True
            self.running = True
            threading.Thread(target=self._listen, daemon=True).start()
            logger.info(f"✅ Connected to ESP32 at {self.esp32_ip}")
            return True
        return False

    def _listen(self):
        while self.running:
            msg = self.ws.recv()
            if msg:
                try:
                    for line in msg.split('\n'):
                        data = json.loads(line)
                        if data.get('type') == 'sensors':
                            self.sensor_data = data
                except: pass
            time.sleep(0.01)

    def send_action(self, action: str, speed_l: float, speed_r: float) -> bool:
        payload = json.dumps({
            'type': 'command',
            'action': action,
            'speed_left': int(speed_l),
            'speed_right': int(speed_r)
        })
        return self.ws.send(payload)

    def stop(self):
        self.running = False
        self.connected = False
        if self.ws.socket: self.ws.socket.close()
