#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SWARM CORE COMMUNICATION CONTROLLER v1.1
Adapter layer between SwarmCore and external world.
All corrections, adaptations, and protocol conversions happen here.
"""

import json
import time
import socket
import threading
import logging
import math
import struct
import queue
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List, Callable
from enum import Enum

try:
    from .swarm_core import StandardSwarmCore
except ImportError:
    from swarm_core import StandardSwarmCore

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('SwarmCommsCtrl')

class ProtocolType(Enum):
    """Supported protocols"""
    JSON_TCP = "json_tcp"
    JSON_UDP = "json_udp"
    BINARY_TCP = "binary_tcp"
    BINARY_UDP = "binary_udp"
    WEBSOCKET = "websocket"
    MQTT = "mqtt"

class ConnectionMode(Enum):
    """Connection modes"""
    CLIENT = "client"
    SERVER = "server"
    DUPLEX = "duplex"

@dataclass
class CommunicationConfig:
    """Configuration for communication controller"""

    # Core settings
    core_class: Any = StandardSwarmCore  # Immutable core

    # Network settings
    protocol: ProtocolType = ProtocolType.JSON_TCP
    mode: ConnectionMode = ConnectionMode.CLIENT
    host: str = "127.0.0.1"
    port: int = 8888
    buffer_size: int = 4096

    # Timing
    update_rate_hz: float = 10.0
    reconnect_delay: float = 2.0
    heartbeat_interval: float = 5.0

    # Data processing
    enable_filtering: bool = True
    filter_window: int = 5
    enable_smoothing: bool = True
    smoothing_factor: float = 0.3

    # Corrections and overrides
    enable_speed_limits: bool = True
    max_speed: float = 100.0
    min_speed: float = -50.0

    enable_emergency_override: bool = True
    emergency_distance_cm: float = 10.0

    enable_stall_detection: bool = True
    stall_threshold_cm: float = 5.0
    stall_timeout: float = 2.0

    # Logging
    log_decisions: bool = True
    log_raw_data: bool = False
    log_file: str = "swarm_comms.log"

    # Callbacks
    on_decision_callback: Optional[Callable] = None
    on_sensor_callback: Optional[Callable] = None
    on_error_callback: Optional[Callable] = None
    on_status_callback: Optional[Callable] = None

class CommunicationController:
    """
    ADAPTABLE COMMUNICATION CONTROLLER
    Handles all protocol conversions, corrections, and adaptations.
    This is where ALL modifications happen - NOT in SwarmCore.
    """

    def __init__(self, config: CommunicationConfig):
        self.config = config

        # Initialize immutable core
        self.core = config.core_class()
        logger.info(f"Loaded SwarmCore: {self.core.get_version()}")

        # Communication state
        self.running = False
        self.connected = False
        self.socket = None

        # Data buffers
        self.sensor_history = []
        self.decision_history = []
        self.max_history = 100

        # Filters
        self.distance_filter = MovingAverageFilter(window_size=config.filter_window)

        # State tracking
        self.last_sensor_data = None
        self.last_decision = None
        self.stall_start_time = None
        self.bytes_sent = 0
        self.bytes_received = 0

        # Threads and queues
        self.receive_thread = None
        self.process_thread = None
        self.sensor_queue = queue.Queue(maxsize=100)
        self.command_queue = queue.Queue(maxsize=100)

        # Protocol handlers
        self.protocol_handlers = {
            ProtocolType.JSON_TCP: JSONTCPHandler(),
            ProtocolType.JSON_UDP: JSONUDPHandler(),
            ProtocolType.BINARY_TCP: BinaryTCPHandler(),
            ProtocolType.BINARY_UDP: BinaryUDPHandler(),
        }

        logger.info("CommunicationController initialized")

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def start(self):
        """Start the communication controller"""
        if self.running:
            logger.warning("Controller already running")
            return

        self.running = True

        # Start threads based on mode
        if self.config.mode in [ConnectionMode.CLIENT, ConnectionMode.DUPLEX]:
            self._start_client()

        if self.config.mode in [ConnectionMode.SERVER, ConnectionMode.DUPLEX]:
            self._start_server()

        logger.info(f"CommunicationController started in {self.config.mode.value} mode")

    def stop(self):
        """Stop the communication controller"""
        self.running = False
        self._disconnect()

        # Wait for threads
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2.0)
        if self.process_thread and self.process_thread.is_alive():
            self.process_thread.join(timeout=2.0)

        logger.info("CommunicationController stopped")

    def send_manual_command(self, left_speed: float, right_speed: float,
                           action: str = "MANUAL"):
        """Send manual command (override SwarmCore)"""
        command = {
            'action': action,
            'speed_left': left_speed,
            'speed_right': right_speed,
            'zone': 'MANUAL_OVERRIDE',
            'confidence': 1.0,
            'timestamp': time.time(),
            'source': 'MANUAL'
        }

        self._apply_corrections(command)
        self._send_command(command)

    def get_status(self) -> Dict[str, Any]:
        """Get controller status"""
        return {
            'running': self.running,
            'connected': self.connected,
            'core_version': self.core.get_version(),
            'core_stats': self.core.get_stats(),
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'queue_sizes': {
                'sensor': self.sensor_queue.qsize(),
                'command': self.command_queue.qsize()
            },
            'last_decision': self.last_decision
        }

    def update_config(self, **kwargs):
        """Update configuration dynamically"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"Config updated: {key} = {value}")

    # =========================================================================
    # CORE COMMUNICATION METHODS
    # =========================================================================

    def _start_client(self):
        """Start client communication"""
        self.receive_thread = threading.Thread(
            target=self._client_receive_loop,
            name="ClientReceive",
            daemon=True
        )
        self.receive_thread.start()

        self.process_thread = threading.Thread(
            target=self._process_loop,
            name="ProcessLoop",
            daemon=True
        )
        self.process_thread.start()

    def _start_server(self):
        """Start server communication"""
        server_thread = threading.Thread(
            target=self._server_loop,
            name="ServerLoop",
            daemon=True
        )
        server_thread.start()

    def _client_receive_loop(self):
        """Receive data from server"""
        logger.info("Client receive loop started")

        while self.running:
            try:
                if not self.connected:
                    if not self._connect():
                        time.sleep(self.config.reconnect_delay)
                        continue

                # Receive data
                data = self._receive_data()
                if data:
                    self._process_incoming_data(data)

                time.sleep(0.001)

            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
                self._disconnect()
                time.sleep(1.0)

        logger.info("Client receive loop stopped")

    def _process_loop(self):
        """Process sensor data and make decisions"""
        logger.info("Process loop started")

        last_decision_time = 0
        decision_interval = 1.0 / self.config.update_rate_hz

        while self.running:
            try:
                current_time = time.time()

                # Check decision interval
                if current_time - last_decision_time < decision_interval:
                    time.sleep(0.001)
                    continue

                # Get sensor data from queue
                sensor_data = None
                try:
                    sensor_data = self.sensor_queue.get_nowait()
                except queue.Empty:
                    time.sleep(0.001)
                    continue

                # Process through SwarmCore
                decision = self._process_sensor_data(sensor_data)

                # Send decision
                if decision:
                    self._send_decision(decision)

                last_decision_time = current_time

            except Exception as e:
                logger.error(f"Error in process loop: {e}")
                time.sleep(0.1)

        logger.info("Process loop stopped")

    def _server_loop(self):
        """Server communication loop"""
        logger.info(f"Server loop started on port {self.config.port}")

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', self.config.port))
        server_socket.listen(5)
        server_socket.settimeout(1.0)

        while self.running:
            try:
                client_socket, addr = server_socket.accept()
                logger.info(f"Client connected: {addr}")

                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, addr),
                    daemon=True
                )
                client_thread.start()

            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Server error: {e}")

        server_socket.close()
        logger.info("Server loop stopped")

    def _handle_client(self, client_socket, addr):
        """Handle client connection"""
        logger.info(f"Handling client {addr}")

        try:
            while self.running:
                # Receive data
                data = client_socket.recv(self.config.buffer_size)
                if not data:
                    break

                # Process incoming data
                sensor_data = self._decode_data(data)
                if sensor_data:
                    # Put in queue for processing
                    self.sensor_queue.put(sensor_data)

                    # Send decision if available
                    if self.last_decision:
                        response = self._encode_decision(self.last_decision)
                        client_socket.send(response)

        except Exception as e:
            logger.error(f"Client {addr} error: {e}")
        finally:
            client_socket.close()
            logger.info(f"Client {addr} disconnected")

    # =========================================================================
    # DATA PROCESSING METHODS (WHERE CORRECTIONS HAPPEN)
    # =========================================================================

    def _process_sensor_data(self, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process sensor data through SwarmCore with corrections.
        Here we adapt the 2-sensor input to the 3-sensor SwarmCore requirement.
        """
        try:
            # 1. Extract and ADAPT sensors
            # The simulator sends 'dist_left' (-15 deg) and 'dist_right' (+15 deg)
            # SwarmCore expects 'dist_front', 'dist_left', 'dist_right'

            raw_left = sensor_data.get('dist_left', 400.0)
            raw_right = sensor_data.get('dist_right', 400.0)

            # ADAPTER LOGIC:
            # Since sensors are narrow (+/- 15 deg), they both cover the "front" area.
            # We map Front to the minimum of both to be safe (if either sees an obs, front is blocked).
            # We map Left/Right to their respective sides.

            dist_front = min(raw_left, raw_right)
            dist_left = raw_left
            dist_right = raw_right

            # 2. Apply filtering if enabled
            if self.config.enable_filtering:
                dist_front = self.distance_filter.update('front', dist_front)
                dist_left = self.distance_filter.update('left', dist_left)
                dist_right = self.distance_filter.update('right', dist_right)

            # 3. Apply emergency override if enabled
            if (self.config.enable_emergency_override and
                (dist_front < self.config.emergency_distance_cm or
                 dist_left < self.config.emergency_distance_cm or
                 dist_right < self.config.emergency_distance_cm)):

                logger.warning(f"EMERGENCY OVERRIDE: F={dist_front:.1f}, L={dist_left:.1f}, R={dist_right:.1f}")
                emergency_decision = {
                    'action': 'EMERGENCY_OVERRIDE',
                    'speed_left': 0,
                    'speed_right': 0,
                    'zone': 'EMERGENCY',
                    'confidence': 1.0,
                    'timestamp': time.time(),
                    'source': 'CONTROLLER_OVERRIDE'
                }
                self.last_decision = emergency_decision
                return emergency_decision

            # 4. Apply stall detection if enabled
            # Note: We could use encoder data here if available in sensor_data
            if self.config.enable_stall_detection:
                if self._check_stall_condition(dist_front, dist_left, dist_right):
                    logger.warning("STALL DETECTED - applying correction")
                    # Apply correction - slight reverse and turn
                    stall_decision = {
                        'action': 'STALL_RECOVERY',
                        'speed_left': -20,
                        'speed_right': 30,
                        'zone': 'STALL',
                        'confidence': 0.9,
                        'timestamp': time.time(),
                        'source': 'CONTROLLER_CORRECTION'
                    }
                    self.last_decision = stall_decision
                    return stall_decision

            # 5. Get decision from IMMUTABLE SwarmCore
            # We pass our adapted values
            core_decision = self.core.decide(dist_front, dist_left, dist_right)

            # 6. Apply corrections to core decision
            corrected_decision = self._apply_corrections(core_decision)

            # 7. Apply smoothing if enabled
            if self.config.enable_smoothing and self.last_decision:
                corrected_decision = self._apply_smoothing(corrected_decision)

            # 8. Store decision
            self.last_decision = corrected_decision
            self.decision_history.append(corrected_decision)
            if len(self.decision_history) > self.max_history:
                self.decision_history.pop(0)

            # 9. Call callback if set
            if self.config.on_decision_callback:
                self.config.on_decision_callback(corrected_decision)

            # 10. Log if enabled
            if self.config.log_decisions:
                logger.debug(f"Decision: {corrected_decision['action']} "
                           f"L={corrected_decision['speed_left']:.1f} "
                           f"R={corrected_decision['speed_right']:.1f}")

            return corrected_decision

        except Exception as e:
            logger.error(f"Error processing sensor data: {e}")

            # Return safe decision on error
            safe_decision = {
                'action': 'ERROR_RECOVERY',
                'speed_left': 0,
                'speed_right': 0,
                'zone': 'ERROR',
                'confidence': 0.0,
                'timestamp': time.time(),
                'source': 'CONTROLLER_ERROR'
            }
            self.last_decision = safe_decision
            return safe_decision

    def _apply_corrections(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply all corrections to SwarmCore decision.
        This is where you add your custom logic.
        """
        corrected = decision.copy()

        # 1. Apply speed limits
        if self.config.enable_speed_limits:
            corrected['speed_left'] = max(
                self.config.min_speed,
                min(self.config.max_speed, corrected['speed_left'])
            )
            corrected['speed_right'] = max(
                self.config.min_speed,
                min(self.config.max_speed, corrected['speed_right'])
            )

        # 2. Apply symmetry correction (prevent spinning in place)
        if (abs(corrected['speed_left'] + corrected['speed_right']) < 10 and
            abs(corrected['speed_left'] - corrected['speed_right']) > 50):

            logger.info("Symmetry correction applied")
            # Add small forward component
            corrected['speed_left'] += 10
            corrected['speed_right'] += 10
            corrected['action'] += "_SYMMETRY_CORRECTED"

        # 3. Add timestamp and source
        corrected['corrected_timestamp'] = time.time()
        corrected['source'] = 'CORRECTED'

        return corrected

    def _apply_smoothing(self, new_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Apply smoothing between decisions"""
        if not self.last_decision:
            return new_decision

        smoothed = new_decision.copy()
        alpha = self.config.smoothing_factor

        smoothed['speed_left'] = (
            self.last_decision['speed_left'] * (1 - alpha) +
            new_decision['speed_left'] * alpha
        )
        smoothed['speed_right'] = (
            self.last_decision['speed_right'] * (1 - alpha) +
            new_decision['speed_right'] * alpha
        )

        smoothed['action'] = f"SMOOTHED_{new_decision['action']}"

        return smoothed

    def _check_stall_condition(self, front: float, left: float, right: float) -> bool:
        """Check if robot is stalled"""
        if front < self.config.stall_threshold_cm and self.stall_start_time is None:
            self.stall_start_time = time.time()

        if self.stall_start_time and time.time() - self.stall_start_time > self.config.stall_timeout:
            self.stall_start_time = None
            return True

        if front >= self.config.stall_threshold_cm:
            self.stall_start_time = None

        return False

    # =========================================================================
    # PROTOCOL HANDLING METHODS
    # =========================================================================

    def _connect(self) -> bool:
        """Connect to remote host"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.config.host, self.config.port))
            self.socket.settimeout(0.1)
            self.connected = True
            logger.info(f"Connected to {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def _disconnect(self):
        """Disconnect from remote host"""
        if self.socket:
            self.socket.close()
            self.socket = None
        self.connected = False

    def _receive_data(self) -> Optional[bytes]:
        """Receive data based on protocol"""
        try:
            if self.config.protocol in [ProtocolType.JSON_TCP, ProtocolType.BINARY_TCP]:
                return self._receive_tcp()
            elif self.config.protocol in [ProtocolType.JSON_UDP, ProtocolType.BINARY_UDP]:
                return self._receive_udp()
        except Exception as e:
            logger.error(f"Receive error: {e}")
        return None

    def _receive_tcp(self) -> Optional[bytes]:
        """Receive TCP data"""
        if not self.socket:
            return None

        try:
            data = self.socket.recv(self.config.buffer_size)
            if data:
                self.bytes_received += len(data)
                return data
        except socket.timeout:
            pass
        except Exception as e:
            logger.error(f"TCP receive error: {e}")
            self._disconnect()

        return None

    def _receive_udp(self) -> Optional[bytes]:
        """Receive UDP data"""
        # UDP would use a different socket setup
        # Simplified for example
        return None

    def _send_data(self, data: bytes) -> bool:
        """Send data based on protocol"""
        try:
            if self.config.protocol in [ProtocolType.JSON_TCP, ProtocolType.BINARY_TCP]:
                return self._send_tcp(data)
            elif self.config.protocol in [ProtocolType.JSON_UDP, ProtocolType.BINARY_UDP]:
                return self._send_udp(data)
        except Exception as e:
            logger.error(f"Send error: {e}")
        return False

    def _send_tcp(self, data: bytes) -> bool:
        """Send TCP data"""
        if not self.socket or not self.connected:
            return False

        try:
            self.socket.sendall(data)
            self.bytes_sent += len(data)
            return True
        except Exception as e:
            logger.error(f"TCP send error: {e}")
            self._disconnect()
            return False

    def _send_udp(self, data: bytes) -> bool:
        """Send UDP data"""
        # UDP implementation would go here
        return False

    def _send_command(self, command: Dict[str, Any]):
        """Send command (renamed from internal _send_decision for generic use)"""
        encoded = self._encode_decision(command)
        if encoded:
            self._send_data(encoded)
            # Put in command queue for monitoring
            self.command_queue.put(command)

    def _decode_data(self, raw_data: bytes) -> Optional[Dict[str, Any]]:
        """Decode raw data based on protocol"""
        handler = self.protocol_handlers.get(self.config.protocol)
        if handler:
            return handler.decode(raw_data)
        return None

    def _encode_decision(self, decision: Dict[str, Any]) -> bytes:
        """Encode decision based on protocol"""
        handler = self.protocol_handlers.get(self.config.protocol)
        if handler:
            return handler.encode(decision)
        return b''

    def _process_incoming_data(self, raw_data: bytes):
        """Process incoming raw data"""
        try:
            # Decode data
            sensor_data = self._decode_data(raw_data)
            if not sensor_data:
                return

            # Call sensor callback if set
            if self.config.on_sensor_callback:
                self.config.on_sensor_callback(sensor_data)

            # Log raw data if enabled
            if self.config.log_raw_data:
                logger.debug(f"Raw sensor: {sensor_data}")

            # Put in queue for processing
            self.sensor_queue.put(sensor_data)

        except Exception as e:
            logger.error(f"Error processing incoming data: {e}")

    def _send_decision(self, decision: Dict[str, Any]):
        """Send decision to remote"""
        self._send_command(decision)

# =============================================================================
# PROTOCOL HANDLERS
# =============================================================================

class ProtocolHandler:
    """Base protocol handler"""

    def encode(self, data: Dict[str, Any]) -> bytes:
        raise NotImplementedError

    def decode(self, raw_data: bytes) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

class JSONTCPHandler(ProtocolHandler):
    """JSON over TCP handler"""

    def encode(self, data: Dict[str, Any]) -> bytes:
        return json.dumps(data).encode('utf-8') + b'\n'

    def decode(self, raw_data: bytes) -> Optional[Dict[str, Any]]:
        try:
            data_str = raw_data.decode('utf-8').strip()
            # Handle multiple JSON objects in buffer (take the last complete one or split)
            # For simplicity, we assume one message per packet or clean newlines
            lines = data_str.split('\n')
            if not lines:
                return None

            # Process the last valid line
            valid_data = None
            for line in reversed(lines):
                if line.strip():
                    try:
                        data = json.loads(line)
                        valid_data = data
                        break
                    except:
                        continue

            if not valid_data:
                return None

            data = valid_data

            # Convert to standard format
            # Support both old (front/left/right) and new (left/right) formats
            return {
                'dist_front': data.get('dist_front', 400.0), # Fallback for new sensors handled in process_sensor_data
                'dist_left': data.get('dist_left', 400.0),
                'dist_right': data.get('dist_right', 400.0),
                'enc_left': data.get('enc_left', 0.0),
                'enc_right': data.get('enc_right', 0.0),
                'timestamp': data.get('timestamp', time.time()),
                'raw': data
            }
        except Exception as e:
            logger.error(f"JSON decode error: {e}")
            return None

class JSONUDPHandler(JSONTCPHandler):
    """JSON over UDP handler"""
    pass  # Same as TCP for JSON

class BinaryTCPHandler(ProtocolHandler):
    """Binary protocol over TCP handler"""

    def encode(self, data: Dict[str, Any]) -> bytes:
        # Simple binary format: action(1B) + left(4B) + right(4B)
        action_map = {
            'FORWARD': 1,
            'TURN_LEFT': 2,
            'TURN_RIGHT': 3,
            'EMERGENCY_STOP': 4
        }

        action_byte = action_map.get(data.get('action', 'FORWARD'), 1)
        left_bytes = struct.pack('f', data.get('speed_left', 0))
        right_bytes = struct.pack('f', data.get('speed_right', 0))

        return bytes([action_byte]) + left_bytes + right_bytes

    def decode(self, raw_data: bytes) -> Optional[Dict[str, Any]]:
        # Binary format: front(4B) + left(4B) + right(4B)
        if len(raw_data) >= 12:
            front = struct.unpack('f', raw_data[0:4])[0]
            left = struct.unpack('f', raw_data[4:8])[0]
            right = struct.unpack('f', raw_data[8:12])[0]

            return {
                'dist_front': front,
                'dist_left': left,
                'dist_right': right,
                'timestamp': time.time(),
                'binary': True
            }
        return None

class BinaryUDPHandler(BinaryTCPHandler):
    """Binary protocol over UDP handler"""
    pass

# =============================================================================
# UTILITY CLASSES
# =============================================================================

class MovingAverageFilter:
    """Moving average filter for sensor data"""

    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.buffers = {}

    def update(self, sensor_name: str, value: float) -> float:
        """Update filter and return filtered value"""
        if sensor_name not in self.buffers:
            self.buffers[sensor_name] = []

        buffer = self.buffers[sensor_name]
        buffer.append(value)

        if len(buffer) > self.window_size:
            buffer.pop(0)

        return sum(buffer) / len(buffer)
