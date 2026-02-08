#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SWARM CORE - STANDARD IMMUTABLE LOGIC
"""

import time
import logging
from typing import Dict, Any

# Configure logging if not already configured
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('SwarmCore')

class StandardSwarmCore:
    """
    STANDARDIZED SWARM CORE - DO NOT MODIFY!
    This is the immutable decision-making engine.
    """

    VERSION = "3.7-STANDARD"

    def __init__(self):
        self.cycle_count = 0
        self.stats = {
            'decisions_made': 0,
            'emergency_stops': 0,
            'average_confidence': 0.0
        }

        # Standard configuration - DO NOT CHANGE
        self.config = {
            'max_distance_cm': 400.0,
            'min_distance_cm': 5.0,
            'emergency_threshold': 15.0,
            'avoid_threshold': 50.0,
            'normal_speed': 80.0,
            'turn_speed': 60.0
        }

        logger.info(f"StandardSwarmCore v{self.VERSION} initialized")

    def decide(self, dist_front: float, dist_left: float, dist_right: float) -> Dict[str, Any]:
        """
        STANDARD DECISION FUNCTION - DO NOT MODIFY!
        Input: distances in cm
        Output: standardized decision dictionary
        """
        self.cycle_count += 1

        # Emergency check - IMMUTABLE LOGIC
        if (dist_front < self.config['emergency_threshold'] or
            dist_left < self.config['emergency_threshold'] or
            dist_right < self.config['emergency_threshold']):

            self.stats['emergency_stops'] += 1
            return self._create_decision('EMERGENCY_STOP', 0, 0, 'EMERGENCY', 1.0)

        # Avoid logic - IMMUTABLE
        if dist_front < self.config['avoid_threshold']:
            if dist_left > dist_right:
                return self._create_decision('TURN_LEFT',
                    -self.config['turn_speed'], self.config['turn_speed'], 'AVOID', 0.8)
            else:
                return self._create_decision('TURN_RIGHT',
                    self.config['turn_speed'], -self.config['turn_speed'], 'AVOID', 0.8)

        # Navigation logic - IMMUTABLE
        if dist_left < self.config['avoid_threshold']:
            return self._create_decision('ADJUST_RIGHT',
                self.config['normal_speed'], self.config['normal_speed'] * 0.6, 'NAVIGATE', 0.7)

        if dist_right < self.config['avoid_threshold']:
            return self._create_decision('ADJUST_LEFT',
                self.config['normal_speed'] * 0.6, self.config['normal_speed'], 'NAVIGATE', 0.7)

        # Default forward - IMMUTABLE
        return self._create_decision('FORWARD',
            self.config['normal_speed'], self.config['normal_speed'], 'CLEAR', 0.9)

    def _create_decision(self, action: str, left: float, right: float,
                        zone: str, confidence: float) -> Dict[str, Any]:
        """Create standardized decision dictionary"""
        decision = {
            'action': action,
            'speed_left': left,
            'speed_right': right,
            'zone': zone,
            'confidence': confidence,
            'cycle': self.cycle_count,
            'timestamp': time.time(),
            'core_version': self.VERSION
        }

        # Update statistics
        self.stats['decisions_made'] += 1
        self.stats['average_confidence'] = (
            self.stats['average_confidence'] * (self.stats['decisions_made'] - 1) +
            confidence
        ) / self.stats['decisions_made']

        return decision

    def get_stats(self) -> Dict[str, Any]:
        """Get core statistics"""
        return self.stats.copy()

    def get_version(self) -> str:
        """Get core version"""
        return self.VERSION
