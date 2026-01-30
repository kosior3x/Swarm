# -*- coding: utf-8 -*-
"""
================================================================================
SWARM MAIN - System Integrator
================================================================================

Version: 2.0
Date: 2026-01-26

PURPOSE:
--------
This module is the SYSTEM INTEGRATOR. It:
- Imports the abstract SwarmCore
- Connects to data sources (ESP32, Simulation, WiFi)
- Sends decisions to actuators
- Manages logging and UI

ARCHITECTURE:
-------------
    [ESP32/Simulator/Pydroid] → [DataAdapter] → [SwarmCore] → [ActuatorAdapter] → [ESP32/Motors]
                                                     ↓
                                              [Logger/UI]

USAGE:
------
    # ESP32 mode
    python swarm_main.py --mode esp32 --port COM3

    # Simulation mode (with swarm_simulator.py)
    from swarm_main import SwarmSystem
    system = SwarmSystem(mode='simulation')

    # WiFi mode
    python swarm_main.py --mode wifi --ip 192.168.1.100

================================================================================
"""

import argparse
import time
import json
import csv
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
from collections import deque

# Import the ABSTRACT Core (no hardware dependencies)
from swarm_core import SwarmCore, SwarmConfig, ActionType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('SwarmMain')


# =============================================================================
# DATA SOURCE ADAPTERS (Abstract Interface)
# =============================================================================

class DataSourceAdapter(ABC):
    """Abstract interface for sensor data sources"""

    @abstractmethod
    def connect(self) -> bool:
        """Connect to data source"""
        pass

    @abstractmethod
    def read_sensors(self) -> Optional[Dict[str, float]]:
        """
        Read sensor data

        Returns:
            Dict with 'dist_front', 'dist_left', 'dist_right' or None if error
        """
        pass

    @abstractmethod
    def disconnect(self):
        """Disconnect from data source"""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected"""
        pass


class ActuatorAdapter(ABC):
    """Abstract interface for motor/actuator control"""

    @abstractmethod
    def execute(self, action: str, speed_left: float, speed_right: float) -> bool:
        """
        Execute action on hardware

        Args:
            action: Action type (FORWARD, TURN_LEFT, etc.)
            speed_left: Left motor speed
            speed_right: Right motor speed

        Returns:
            True if successful
        """
        pass


# =============================================================================
# ESP32 SERIAL ADAPTER
# =============================================================================

class ESP32SerialAdapter(DataSourceAdapter, ActuatorAdapter):
    """
    ESP32 adapter via Serial/USB connection

    Protocol (JSON):
    ESP32 -> Python: {"type":"sensors","dist_front":123,"dist_left":89,"dist_right":156}
    Python -> ESP32: {"type":"command","action":"FORWARD","speed_left":100,"speed_right":100}
    """

    def __init__(self, port: str = None, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self._connected = False

        # State tracking
        self.battery_voltage = 0.0
        self.battery_percent = 0
        self.alerts = []
        self.read_buffer = deque(maxlen=100)

    def connect(self) -> bool:
        """Connect to ESP32 via Serial"""
        try:
            import serial

            if not self.port:
                self.port = self._auto_detect_port()
                if not self.port:
                    logger.error("No ESP32 port found. Specify with --port")
                    return False

            self.serial = serial.Serial(
                self.port,
                baudrate=self.baudrate,
                timeout=1.0
            )
            self._connected = True
            logger.info(f"Connected to ESP32 on {self.port}")
            return True

        except ImportError:
            logger.error("pyserial not installed. Run: pip install pyserial")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to ESP32: {e}")
            return False

    def _auto_detect_port(self) -> Optional[str]:
        """Try to auto-detect ESP32 port"""
        import sys

        if sys.platform == "win32":
            ports = ["COM3", "COM4", "COM5", "COM6", "COM7", "COM8"]
        else:
            ports = ["/dev/ttyUSB0", "/dev/ttyACM0", "/dev/ttyUSB1"]

        import serial
        for port in ports:
            try:
                s = serial.Serial(port, self.baudrate, timeout=0.5)
                s.close()
                logger.info(f"Found port: {port}")
                return port
            except:
                pass

        return None

    def read_sensors(self) -> Optional[Dict[str, float]]:
        """Read sensor data from ESP32"""
        if not self._connected:
            return None

        try:
            line = self.serial.readline().decode('utf-8').strip()
            if not line:
                return None

            data = json.loads(line)
            msg_type = data.get('type', '')

            if msg_type == 'sensors':
                # Update battery status if present
                if 'battery_v' in data:
                    self.battery_voltage = data['battery_v']
                    self.battery_percent = data.get('battery_pct', 0)

                return {
                    'dist_front': data.get('dist_front', 400),
                    'dist_left': data.get('dist_left', 400),
                    'dist_right': data.get('dist_right', 400),
                    'steps_l': data.get('steps_l', 0),
                    'steps_r': data.get('steps_r', 0)
                }

            elif msg_type == 'alert':
                self.alerts.append(data)
                logger.warning(f"ESP32 Alert: {data.get('message', 'unknown')}")

            return None

        except json.JSONDecodeError:
            return None
        except Exception as e:
            logger.error(f"Read error: {e}")
            return None

    def execute(self, action: str, speed_left: float, speed_right: float) -> bool:
        """Send command to ESP32"""
        if not self._connected:
            return False

        try:
            command = {
                'type': 'command',
                'action': action,
                'speed_left': int(speed_left),
                'speed_right': int(speed_right)
            }

            self.serial.write((json.dumps(command) + '\n').encode('utf-8'))
            return True

        except Exception as e:
            logger.error(f"Send error: {e}")
            return False

    def disconnect(self):
        """Disconnect from ESP32"""
        if self.serial:
            self.serial.close()
        self._connected = False
        logger.info("Disconnected from ESP32")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def get_battery_status(self) -> Dict:
        """Get battery status"""
        return {
            'voltage': self.battery_voltage,
            'percent': self.battery_percent,
            'low': self.battery_voltage < 6.8,
            'critical': self.battery_voltage < 6.4
        }

    def get_alerts(self) -> List:
        """Get and clear alerts"""
        alerts = self.alerts.copy()
        self.alerts.clear()
        return alerts


# =============================================================================
# WIFI/WEBSOCKET ADAPTER
# =============================================================================

class WiFiAdapter(DataSourceAdapter, ActuatorAdapter):
    """
    WiFi adapter using WebSocket connection to ESP32
    """

    def __init__(self, host: str = "192.168.1.100", port: int = 81):
        self.host = host
        self.port = port
        self.ws = None
        self._connected = False
        self.last_sensors = None

    def connect(self) -> bool:
        """Connect via WebSocket"""
        try:
            # Try to import from swarm_wifi if available
            try:
                from swarm_wifi import WebSocketClient
                self.ws = WebSocketClient(self.host, self.port)
            except ImportError:
                # Fallback to websocket-client
                import websocket
                self.ws = websocket.create_connection(
                    f"ws://{self.host}:{self.port}",
                    timeout=5
                )

            if hasattr(self.ws, 'connect'):
                self.ws.connect()

            # Perform Handshake (Ping) to verify protocol and reset Watchdog
            if self._handshake():
                self._connected = True
                logger.info(f"✅ Connected & Handshaked with ESP32 at {self.host}:{self.port}")
                return True
            else:
                logger.error("Handshake failed (No PONG received)")
                self.ws.close()
                return False

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False

    def _handshake(self) -> bool:
        """Send Ping and wait for Ack to verify connection"""
        try:
            ping_cmd = json.dumps({'type': 'ping'})
            if hasattr(self.ws, 'send'):
                self.ws.send(ping_cmd)

            # Wait for response (short timeout)
            self.ws.settimeout(2.0)
            if hasattr(self.ws, 'recv'):
                resp = self.ws.recv()
                if resp:
                    data = json.loads(resp)
                    # Expecting {"type": "ack", "action": "ping", ...}
                    if data.get('type') == 'ack' and data.get('action') == 'ping':
                        return True
            return False
        except Exception as e:
            logger.warning(f"Handshake error: {e}")
            return False

    def read_sensors(self) -> Optional[Dict[str, float]]:
        """Read sensor data via WebSocket"""
        if not self._connected:
            return None

        try:
            if hasattr(self.ws, 'recv'):
                # Non-blocking read or short timeout
                self.ws.settimeout(0.1)
                try:
                    msg = self.ws.recv()
                except:
                    return self.last_sensors # Return last known state on timeout
            else:
                return None

            if msg:
                data = json.loads(msg)
                if data.get('type') == 'sensors':
                    self.last_sensors = {
                        'dist_front': data.get('dist_front', 400),
                        'dist_left': data.get('dist_left', 400),
                        'dist_right': data.get('dist_right', 400),
                        'steps_l': data.get('steps_l', 0),
                        'steps_r': data.get('steps_r', 0)
                    }
                    return self.last_sensors

            return None

        except Exception as e:
            logger.error(f"WebSocket read error: {e}")
            return None

    def execute(self, action: str, speed_left: float, speed_right: float) -> bool:
        """Send command via WebSocket"""
        if not self._connected:
            return False

        try:
            command = json.dumps({
                'type': 'command',
                'action': action,
                'speed_left': int(speed_left),
                'speed_right': int(speed_right)
            })

            if hasattr(self.ws, 'send'):
                self.ws.send(command)

            return True

        except Exception as e:
            logger.error(f"WebSocket send error: {e}")
            return False

    def disconnect(self):
        """Disconnect WebSocket"""
        if self.ws and hasattr(self.ws, 'close'):
            self.ws.close()
        self._connected = False
        logger.info("WebSocket disconnected")

    @property
    def is_connected(self) -> bool:
        return self._connected


# =============================================================================
# SIMULATION ADAPTER (for swarm_simulator.py)
# =============================================================================

class SimulationAdapter(DataSourceAdapter, ActuatorAdapter):
    """
    Adapter for simulator - used by swarm_simulator.py
    This is a pass-through adapter since simulator manages its own state
    """

    def __init__(self):
        self._connected = True
        self.last_sensors = None
        self.last_command = None

    def connect(self) -> bool:
        self._connected = True
        return True

    def read_sensors(self) -> Optional[Dict[str, float]]:
        # Simulator calls core directly, this is for compatibility
        return self.last_sensors

    def set_sensors(self, dist_front: float, dist_left: float, dist_right: float):
        """Called by simulator to set current sensor values"""
        self.last_sensors = {
            'dist_front': dist_front,
            'dist_left': dist_left,
            'dist_right': dist_right
        }

    def execute(self, action: str, speed_left: float, speed_right: float) -> bool:
        self.last_command = {
            'action': action,
            'speed_left': speed_left,
            'speed_right': speed_right
        }
        return True

    def get_last_command(self) -> Optional[Dict]:
        return self.last_command

    def disconnect(self):
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected


# =============================================================================
# DATA LOGGER
# =============================================================================

class DataLogger:
    """
    Unified data logger for all modes
    Creates CSV files with sensor data and decisions
    """

    COLUMNS = [
        'timestamp', 'source', 'dist_front', 'dist_left', 'dist_right',
        'speed_left', 'speed_right', 'action', 'confidence',
        'decision_source', 'cycle', 'steps_l', 'steps_r', 'notes'
    ]

    def __init__(self, log_dir: str = "logs", source: str = "MAIN"):
        self.log_dir = log_dir
        self.source = source
        self.file = None
        self.writer = None
        self.row_count = 0

        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        self._open_file()

    def _open_file(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(self.log_dir, f'train_{self.source.lower()}_{timestamp}.csv')

        self.file = open(filename, 'w', newline='', encoding='utf-8')
        self.writer = csv.writer(self.file)
        self.writer.writerow(self.COLUMNS)
        self.file.flush()

        logger.info(f"Logging to: {filename}")

    def log(self, sensors: Dict, decision: Dict, notes: str = ""):
        """Log sensor data and decision"""
        row = [
            datetime.now().isoformat(),
            self.source,
            f"{sensors.get('dist_front', 0):.1f}",
            f"{sensors.get('dist_left', 0):.1f}",
            f"{sensors.get('dist_right', 0):.1f}",
            f"{decision.get('speed_left', 0):.0f}",
            f"{decision.get('speed_right', 0):.0f}",
            decision.get('action', 'UNKNOWN'),
            f"{decision.get('confidence', 0):.3f}",
            decision.get('source', 'UNKNOWN'),
            decision.get('cycle', 0),
            sensors.get('steps_l', 0),
            sensors.get('steps_r', 0),
            notes.replace(',', ';').replace('\n', ' ')[:100]
        ]

        self.writer.writerow(row)
        self.row_count += 1

        if self.row_count % 50 == 0:
            self.file.flush()

    def close(self):
        if self.file:
            self.file.flush()
            self.file.close()
            logger.info(f"Logger closed: {self.row_count} rows saved")


# =============================================================================
# SWARM SYSTEM - MAIN INTEGRATOR
# =============================================================================

class SwarmSystem:
    """
    Main SWARM System integrator.

    Connects:
    - Abstract SwarmCore (AI brain)
    - Data source (ESP32/WiFi/Simulator)
    - Actuator (ESP32/WiFi/Simulator)
    - Logger (CSV)

    Usage:
        system = SwarmSystem(mode='esp32', port='COM3')
        system.start()

        # Or single cycle
        decision = system.run_cycle(sensors)
    """

    def __init__(self,
                 mode: str = 'simulation',
                 port: str = None,
                 host: str = None,
                 config: SwarmConfig = None):
        """
        Initialize SWARM System

        Args:
            mode: 'esp32', 'wifi', or 'simulation'
            port: Serial port for ESP32 mode
            host: IP address for WiFi mode
            config: SwarmConfig (uses default if None)
        """
        self.mode = mode
        self.config = config or SwarmConfig()

        # Initialize ABSTRACT Core (no hardware knowledge)
        self.core = SwarmCore(self.config)

        # Initialize adapters based on mode
        if mode == 'esp32':
            self.adapter = ESP32SerialAdapter(port=port)
            source_name = "ESP32"
        elif mode == 'wifi':
            self.adapter = WiFiAdapter(host=host or "192.168.1.100")
            source_name = "WIFI"
        else:
            self.adapter = SimulationAdapter()
            source_name = "SIM"

        # Data logger
        self.logger = DataLogger(source=source_name)

        # State
        self.running = False
        self.cycle_count = 0
        self.last_decision = None

        logger.info(f"SwarmSystem initialized: mode={mode}")

    def connect(self) -> bool:
        """Connect to data source/actuator"""
        return self.adapter.connect()

    def run_cycle(self, sensors: Dict = None) -> Optional[Dict]:
        """
        Run single decision cycle

        Args:
            sensors: Sensor data dict (if None, reads from adapter)

        Returns:
            Decision dict or None if no sensors available
        """
        # Get sensor data
        if sensors is None:
            sensors = self.adapter.read_sensors()

        if sensors is None:
            return None

        # Core decision (Core does NOT know about hardware!)
        decision = self.core.decide(
            dist_front=sensors['dist_front'],
            dist_left=sensors['dist_left'],
            dist_right=sensors['dist_right']
        )

        # Execute on hardware
        self.adapter.execute(
            decision['action'],
            decision['speed_left'],
            decision['speed_right']
        )

        # Log
        self.logger.log(sensors, decision, notes=decision.get('concept', ''))

        self.cycle_count += 1
        self.last_decision = decision

        return decision

    def provide_feedback(self, success: bool):
        """Provide learning feedback to core"""
        self.core.feedback(success)

    def start(self, duration: float = None):
        """
        Start continuous operation

        Args:
            duration: Run duration in seconds (None = forever)
        """
        if not self.adapter.is_connected:
            if not self.connect():
                logger.error("Failed to connect. Aborting.")
                return

        self.running = True
        start_time = time.time()

        last_action_time = time.time()

        logger.info("Starting SWARM system...")

        try:
            while self.running:
                # Check duration
                if duration and (time.time() - start_time) >= duration:
                    break

                # Run cycle
                decision = self.run_cycle()

                if decision:
                    # Display status
                    if self.cycle_count % 30 == 0:
                        print(f"[{self.cycle_count}] {decision['action']} | "
                              f"Conf: {decision['confidence']:.0%} | "
                              f"Src: {decision['source']}")
                    last_action_time = time.time()
                else:
                    # Idle / No Sensors - Send Heartbeat if needed
                    if time.time() - last_action_time > 2.0:
                         if self.mode == 'wifi':
                             self.adapter.execute("ping", 0, 0) # Keep-alive
                             last_action_time = time.time()

                # Rate limit
                time.sleep(0.05)  # 20 Hz

        except KeyboardInterrupt:
            logger.info("Interrupted by user")

        self.stop()

    def stop(self):
        """Stop system and cleanup"""
        self.running = False
        self.adapter.disconnect()
        self.core.save()
        self.logger.close()
        logger.info(f"System stopped after {self.cycle_count} cycles")

    def get_stats(self) -> Dict:
        """Get system statistics"""
        return {
            'mode': self.mode,
            'cycle_count': self.cycle_count,
            'connected': self.adapter.is_connected,
            'core_stats': self.core.get_stats()
        }


# =============================================================================
# LEGACY COMPATIBILITY - SwarmCoreController
# =============================================================================

class SwarmCoreController:
    """
    Legacy compatibility wrapper.

    For backwards compatibility with swarm_simulator.py and other modules
    that use the old SwarmCoreController interface.
    """

    def __init__(self, source=None, config: SwarmConfig = None):
        self.config = config or SwarmConfig()
        self.core = SwarmCore(self.config)
        self.npz = self.core.npz
        self.absr = self.core.absr
        self.logger = DataLogger(source=source.value if source else "LEGACY")

        self.cycle_count = 0
        self.last_action = None

    def process_sensors(self,
                       dist_front: float,
                       dist_left: float,
                       dist_right: float,
                       current_speed_l: float = 100.0,
                       current_speed_r: float = 100.0,
                       robot_x: float = 0.0,
                       robot_y: float = 0.0,
                       robot_angle: float = 0.0) -> Dict:
        """Legacy interface - wraps SwarmCore.decide()"""
        self.cycle_count += 1

        decision = self.core.decide(
            dist_front=dist_front,
            dist_left=dist_left,
            dist_right=dist_right,
            speed_left=current_speed_l,
            speed_right=current_speed_r
        )

        # Log
        sensors = {
            'dist_front': dist_front,
            'dist_left': dist_left,
            'dist_right': dist_right
        }
        self.logger.log(sensors, decision, notes=f"x:{robot_x:.0f},y:{robot_y:.0f}")

        self.last_action = decision
        return decision

    def feedback(self, success: bool):
        """Legacy feedback interface"""
        self.core.feedback(success)

    def close(self):
        """Cleanup"""
        self.core.save()
        self.logger.close()


# For backwards compatibility with swarm_simulator.py
# which imports: from swarm_unified_core import SwarmCoreController, DataSource, SwarmConfig
from enum import Enum
class DataSource(Enum):
    """Legacy enum for backwards compatibility"""
    SIMULATION = "SIM"
    ESP32_LIVE = "ESP32"
    UNKNOWN = "UNK"


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='SWARM System')
    parser.add_argument('--mode', choices=['esp32', 'wifi', 'simulation'],
                        default='simulation', help='Operation mode')
    parser.add_argument('--port', type=str, help='Serial port for ESP32')
    parser.add_argument('--host', type=str, help='IP address for WiFi mode')
    parser.add_argument('--duration', type=float, help='Run duration in seconds')
    parser.add_argument('--test', action='store_true', help='Run test scenarios')

    args = parser.parse_args()

    print("=" * 60)
    print("SWARM SYSTEM v2.0 - Integrated Robot Control")
    print("=" * 60)

    if args.test:
        # Test mode - run scenarios without hardware
        print("\nRunning test scenarios...")

        system = SwarmSystem(mode='simulation')

        test_scenarios = [
            ({'dist_front': 200, 'dist_left': 150, 'dist_right': 150}, "Clear path"),
            ({'dist_front': 50, 'dist_left': 150, 'dist_right': 150}, "Front obstacle"),
            ({'dist_front': 150, 'dist_left': 30, 'dist_right': 200}, "Left wall"),
            ({'dist_front': 150, 'dist_left': 200, 'dist_right': 30}, "Right wall"),
            ({'dist_front': 40, 'dist_left': 40, 'dist_right': 40}, "Trapped"),
        ]

        for sensors, scenario in test_scenarios:
            decision = system.run_cycle(sensors)
            print(f"\n[{scenario}]")
            print(f"  Sensors: F={sensors['dist_front']}, L={sensors['dist_left']}, R={sensors['dist_right']}")
            print(f"  Decision: {decision['action']}")
            print(f"  Speeds: L={decision['speed_left']:.0f}, R={decision['speed_right']:.0f}")
            print(f"  Source: {decision['source']}")

        system.stop()

    else:
        # Normal operation
        system = SwarmSystem(
            mode=args.mode,
            port=args.port,
            host=args.host
        )

        system.start(duration=args.duration)

    print("\n" + "=" * 60)
    print("System stopped.")


if __name__ == "__main__":
    main()