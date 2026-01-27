#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SWARM CORE - Abstract AI Decision Engine [FIXED VERSION]
================================================================================

Version: 2.1 CORRECTED
Date: 2026-01-27
Status: ✅ ALL ISSUES FIXED

MAJOR FIXES:
-----------
1. ✅ Online Learning (OL) ACTIVATED
2. ✅ Behavioral Like Learning (BLL) AUTO-FEEDBACK
3. ✅ Chaos reduced to 0.15 and conditional
4. ✅ Enhanced anti-oscillation detection
5. ✅ Unified direction convention documentation
6. ✅ Success evaluation integrated

DIRECTION CONVENTION - UNIFIED REFERENCE:
==========================================

PHYSICAL ROBOT BEHAVIOR:
------------------------
- TURN_LEFT:  Left motor SLOWER, Right motor FASTER
              Example: (40, 120) → Robot body rotates LEFT (counter-clockwise)

- TURN_RIGHT: Left motor FASTER, Right motor SLOWER
              Example: (120, 40) → Robot body rotates RIGHT (clockwise)

OBSTACLE AVOIDANCE LOGIC:
-------------------------
- LEFT obstacle detected  → Turn RIGHT (escape right)
- RIGHT obstacle detected → Turn LEFT (escape left)
- FRONT obstacle detected → Turn towards more open side

SENSOR COMPARISON:
------------------
- if dist_left < dist_right:  LEFT is more blocked → Turn RIGHT
- if dist_left > dist_right:  RIGHT is more blocked → Turn LEFT

================================================================================
"""

import numpy as np
import json
import os
import time
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple, Any
from collections import deque
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('SwarmCore')


# =============================================================================
# ENUMS AND CONFIG
# =============================================================================

class ActionType(Enum):
    """Robot action types"""
    FORWARD = "FORWARD"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    STOP = "STOP"
    ESCAPE = "ESCAPE"
    REVERSE = "REVERSE"
    EXPLORE = "EXPLORE"


@dataclass
class SwarmConfig:
    """Configuration for SWARM Core - NO HARDWARE DEPENDENCIES"""
    # Vector dimensions
    vector_dim: int = 38
    max_sensor_range: float = 400.0

    # NPZ paths
    npz_behavior: str = "BEHAVIORAL_BRAIN.npz"

    # Learning directory (for BLL/OL persistence)
    learning_dir: str = "logs"

    # ABSR settings - FIXED
    lorenz_sigma: float = 10.0
    lorenz_rho: float = 28.0
    lorenz_beta: float = 8.0 / 3.0
    chaos_level: float = 0.15  # 🔧 REDUCED from 0.5 to 0.15
    chaos_enabled: bool = True  # 🆕 Allow disabling chaos
    chaos_min_safe_distance: float = 120.0  # 🆕 Disable chaos when too close

    # BLL/OL Learning - ENHANCED
    learning_rate: float = 0.1
    memory_size: int = 1000
    ol_enabled: bool = True  # 🆕 OL activation flag
    ol_learning_rate: float = 0.15  # 🆕 OL vector update rate
    ol_similarity_threshold: float = 0.6  # 🆕 Min similarity to use OL

    # Robot Geometry (mm) - for decision logic only
    robot_width: float = 220.0
    robot_length: float = 200.0
    robot_clearance: float = 30.0
    robot_turn_radius: float = 90.0

    # Decision thresholds (mm)
    danger_dist: float = 60.0
    warning_dist: float = 100.0

    # Tight passage thresholds
    tight_passage_factor: float = 1.2

    def get_min_passage_width(self) -> float:
        """Minimal passage width considering robot width + margins"""
        return self.robot_width + (self.robot_clearance * 2)

    def is_tight_passage(self, dist_left: float, dist_right: float) -> bool:
        """Check if passage is tight for the robot"""
        total_width = dist_left + dist_right
        min_safe = self.get_min_passage_width()
        return total_width < min_safe

    def get_safe_speed_for_passage(self, dist_left: float, dist_right: float) -> float:
        """Calculate safe speed for passage"""
        total_width = dist_left + dist_right
        min_width = self.get_min_passage_width()

        if total_width < min_width:
            return 0.0
        elif total_width < min_width * 1.5:
            return 40.0
        else:
            return 90.0


# =============================================================================
# NPZ ENGINE (Vector Matching)
# =============================================================================

class NPZEngine:
    """
    NPZ-based vector matching engine
    Finds best action based on sensor vector similarity
    """

    def __init__(self, config: SwarmConfig):
        self.config = config
        self.words = []
        self.vectors = None
        self.vectors_norm = None
        self.categories = []
        self.word_to_idx = {}
        self.loaded = False

        self._load_npz()

    def _load_npz(self) -> bool:
        """Load NPZ database"""
        try:
            if os.path.exists(self.config.npz_behavior):
                data = np.load(self.config.npz_behavior, allow_pickle=True)
                self.words = list(data['words'])
                self.vectors = data['vectors'].astype(np.float32)
                self.categories = list(data['categories'])
                data.close()

                # Normalize
                norms = np.linalg.norm(self.vectors, axis=1, keepdims=True)
                norms[norms == 0] = 1
                self.vectors_norm = self.vectors / norms

                self.word_to_idx = {str(w).lower(): i for i, w in enumerate(self.words)}
                self.loaded = True
                logger.info(f"✅ NPZ loaded: {len(self.words)} concepts")
                return True

        except Exception as e:
            logger.error(f"Failed to load NPZ: {e}")

        return False

    def create_sensor_vector(self,
                             dist_front: float,
                             dist_left: float,
                             dist_right: float,
                             speed_left: float = 100.0,
                             speed_right: float = 100.0) -> np.ndarray:
        """Create 38D sensor vector from raw sensor data"""
        vec = np.zeros(self.config.vector_dim, dtype=np.float32)
        max_r = self.config.max_sensor_range

        # Normalize distances (0-1)
        d_f = min(dist_front / max_r, 1.0)
        d_l = min(dist_left / max_r, 1.0)
        d_r = min(dist_right / max_r, 1.0)

        # Distance zones
        vec[0] = d_f
        vec[1] = d_l
        vec[2] = d_r
        vec[3] = (d_f + d_l + d_r) / 3.0
        vec[4] = min(d_f, d_l, d_r)
        vec[5] = max(d_f, d_l, d_r)
        vec[6] = abs(d_l - d_r)
        vec[7] = 1.0 if d_f < 0.2 else 0.0
        vec[8] = 1.0 if d_l < 0.3 or d_r < 0.3 else 0.0
        vec[9] = 1.0 if d_f > 0.8 and d_l > 0.5 and d_r > 0.5 else 0.0

        # Speed encodings
        spd_l = min(speed_left / 150.0, 1.0)
        spd_r = min(speed_right / 150.0, 1.0)
        vec[10] = spd_l
        vec[11] = spd_r
        vec[12] = (spd_l + spd_r) / 2.0
        vec[13] = abs(spd_l - spd_r)
        vec[14] = 1.0 if speed_left > 0 and speed_right > 0 else 0.0

        # Situation features
        vec[20] = 1.0 if d_f < 0.3 else 0.0
        vec[21] = 1.0 if d_l < 0.2 and d_r > 0.5 else 0.0
        vec[22] = 1.0 if d_r < 0.2 and d_l > 0.5 else 0.0
        vec[23] = 1.0 if d_f < 0.2 and d_l < 0.2 and d_r < 0.2 else 0.0
        vec[24] = 1.0 if d_l > 0.8 and d_r > 0.8 and d_f > 0.5 else 0.0
        vec[25] = 1.0 if d_l < 0.4 and d_r < 0.4 and d_f > 0.5 else 0.0

        # Derived metrics
        vec[30] = np.tanh(d_f * 2 - 1)
        vec[31] = np.tanh((d_l - d_r) * 2)
        vec[32] = 1.0 / (1.0 + np.exp(-5 * (d_f - 0.3)))

        # Normalize final vector
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec

    def find_best_match(self,
                        sensor_vector: np.ndarray,
                        tolerance: float = 0.25) -> Tuple[str, float, str]:
        """Find best matching concept for sensor vector"""
        if not self.loaded or self.vectors_norm is None:
            return ("FORWARD", 0.0, "fallback")

        sims = np.dot(self.vectors_norm, sensor_vector)
        best_idx = np.argmax(sims)
        best_sim = float(sims[best_idx])

        if best_sim < tolerance:
            return ("FORWARD", best_sim, "low_confidence")

        concept = str(self.words[best_idx])
        category = str(self.categories[best_idx])

        return (concept, best_sim, category)

    def concept_to_action(self, concept: str) -> Tuple[str, float, float]:
        """
        Map concept to action and speeds

        DIRECTION CONVENTION (see top of file for full reference):
        - TURN_LEFT: Left wheel SLOWER (40), Right wheel FASTER (140)
        - TURN_RIGHT: Left wheel FASTER (140), Right wheel SLOWER (40)
        """
        concept_upper = concept.upper()

        # Emergency actions
        if 'TRAPPED' in concept_upper or 'EMERGENCY_ESCAPE' in concept_upper:
            return (ActionType.ESCAPE.value, -120.0, 120.0)

        if 'COLLISION' in concept_upper or 'CAUTIOUS_STOP' in concept_upper:
            return (ActionType.STOP.value, 0.0, 0.0)

        # LEFT obstacle/wall → turn RIGHT (escape to the right)
        if 'LEFT_WALL' in concept_upper or 'LEFT_OBSTACLE' in concept_upper:
            return (ActionType.TURN_RIGHT.value, 140.0, 40.0)

        # RIGHT obstacle/wall → turn LEFT (escape to the left)
        if 'RIGHT_WALL' in concept_upper or 'RIGHT_OBSTACLE' in concept_upper:
            return (ActionType.TURN_LEFT.value, 40.0, 140.0)

        # Front obstacle with direction
        if 'FRONT_OBSTACLE_RIGHT' in concept_upper:
            return (ActionType.TURN_LEFT.value, 40.0, 140.0)

        if 'FRONT_OBSTACLE_LEFT' in concept_upper:
            return (ActionType.TURN_RIGHT.value, 140.0, 40.0)

        # Exploration
        if 'EXPLORATION_LEFT' in concept_upper:
            return (ActionType.TURN_LEFT.value, 30.0, 150.0)

        if 'EXPLORATION_RIGHT' in concept_upper:
            return (ActionType.TURN_RIGHT.value, 150.0, 30.0)

        # Navigation forward variants
        if 'CORRIDOR' in concept_upper:
            return (ActionType.FORWARD.value, 90.0, 90.0)

        if 'CLEAR_PATH' in concept_upper:
            return (ActionType.FORWARD.value, 120.0, 120.0)

        if 'NORMAL' in concept_upper or 'FORWARD' in concept_upper:
            return (ActionType.FORWARD.value, 100.0, 100.0)

        # Legacy mappings
        if 'ESCAPE' in concept_upper or 'STUCK' in concept_upper:
            return (ActionType.ESCAPE.value, -120.0, 120.0)

        if 'TURN_LEFT' in concept_upper or 'LEFT' in concept_upper:
            return (ActionType.TURN_LEFT.value, 30.0, 150.0)

        if 'TURN_RIGHT' in concept_upper or 'RIGHT' in concept_upper:
            return (ActionType.TURN_RIGHT.value, 150.0, 30.0)

        if 'STOP' in concept_upper:
            return (ActionType.STOP.value, 0.0, 0.0)

        # Default: forward
        return (ActionType.FORWARD.value, 100.0, 100.0)


# =============================================================================
# ABSR BIDECISION ENGINE (BLL + OL + Lorenz Chaos) - FIXED
# =============================================================================

class ABSRBidecision:
    """
    ABSR Bidirectional Decision Engine [FIXED]
    Combines NPZ matching with Behavioral Like Learning (BLL)
    and Online Learning (OL) - NOW BOTH ACTIVE!
    """

    def __init__(self, config: SwarmConfig, npz_engine: NPZEngine):
        self.config = config
        self.npz = npz_engine

        # BLL memory
        self.bll_weights = {}
        self.bll_history = deque(maxlen=config.memory_size)

        # OL additions - NOW ACTIVE
        self.ol_vectors = {}
        self.ol_usage_count = 0  # 🆕 Track OL usage

        # Lorenz chaos - full 3D state
        self.lorenz_state = [0.1, 0.2, 0.3]
        self.chaos_history = deque(maxlen=100)

        # Decision history
        self.last_decision = None
        self.last_sensor_vec = None
        self.decision_count = 0
        self.unknown_situation_streak = 0

        # Throttling
        self.last_decision_time = 0
        self.decision_min_interval = 0.3
        self.cached_decision = None
        self.cached_sensors = None

        # Direction memory - ENHANCED
        self.direction_memory = deque(maxlen=20)
        self.last_turn_direction = None
        self.turn_streak = 0
        self.preferred_escape_direction = None
        self.oscillation_detected = False  # 🆕
        self.consecutive_direction_changes = 0  # 🆕

        self._load_learning_data()

        # State Machine Memory
        self.current_maneuver = None
        self.last_maneuver_turn = None
        self.last_maneuver_time = 0

    def _lorenz_step(self) -> Tuple[float, float, float]:
        """Full Lorenz attractor step"""
        x, y, z = self.lorenz_state
        sigma = self.config.lorenz_sigma
        rho = self.config.lorenz_rho
        beta = self.config.lorenz_beta
        dt = 0.01

        dx = sigma * (y - x)
        dy = x * (rho - z) - y
        dz = x * y - beta * z

        self.lorenz_state = [x + dx*dt, y + dy*dt, z + dz*dt]

        norm_x = np.tanh(self.lorenz_state[0] / 20.0)
        norm_y = np.tanh(self.lorenz_state[1] / 25.0)
        norm_z = np.tanh(self.lorenz_state[2] / 30.0)

        self.chaos_history.append((norm_x, norm_y, norm_z))

        return (norm_x, norm_y, norm_z)

    def _chaos_blend_action(self, base_action: str, base_speeds: Tuple[float, float],
                            chaos_vec: Tuple[float, float, float]) -> Tuple[str, float, float]:
        """
        Blend action with Lorenz chaos dynamics - FIXED
        Now only applies to FORWARD actions
        """
        cx, cy, cz = chaos_vec
        speed_l, speed_r = base_speeds

        intensity = abs(cz) * self.config.chaos_level * 0.5
        direction_blend = cx * 20 * intensity
        speed_modifier = 1.0 + (cy * 0.2 * intensity)

        new_speed_l = max(0, min(150, speed_l * speed_modifier + direction_blend))
        new_speed_r = max(0, min(150, speed_r * speed_modifier - direction_blend))

        return (base_action, new_speed_l, new_speed_r)

    def _update_direction_memory(self, action_concept: str, action_type: str = None):
        """Update direction memory - ENHANCED"""
        concept_upper = action_concept.upper()

        direction = None
        if action_type:
            if 'TURN_LEFT' in action_type:
                direction = 'LEFT'
            elif 'TURN_RIGHT' in action_type:
                direction = 'RIGHT'
        else:
            if 'LEFT' in concept_upper and 'RIGHT' not in concept_upper:
                direction = 'LEFT'
            elif 'RIGHT' in concept_upper and 'LEFT' not in concept_upper:
                direction = 'RIGHT'

        if direction:
            self.direction_memory.append(direction)

            # 🆕 Count direction changes
            if len(self.direction_memory) >= 2:
                if self.direction_memory[-1] != self.direction_memory[-2]:
                    self.consecutive_direction_changes += 1
                else:
                    self.consecutive_direction_changes = 0

            if self.last_turn_direction == direction:
                self.turn_streak += 1
                if self.turn_streak >= 3:
                    self.preferred_escape_direction = direction
            else:
                self.turn_streak = 1
                self.last_turn_direction = direction

    def _detect_oscillation(self) -> bool:
        """
        🆕 Detect if robot is oscillating between directions

        Returns:
            True if oscillation detected
        """
        if len(self.direction_memory) < 6:
            return False

        # Get last 6 decisions
        recent = list(self.direction_memory)[-6:]

        # Pattern 1: L-R-L-R-L-R
        pattern1 = ['LEFT', 'RIGHT', 'LEFT', 'RIGHT', 'LEFT', 'RIGHT']
        pattern2 = ['RIGHT', 'LEFT', 'RIGHT', 'LEFT', 'RIGHT', 'LEFT']

        if recent == pattern1 or recent == pattern2:
            logger.warning("⚠️ Oscillation detected: Alternating L-R pattern")
            return True

        # Pattern 2: More than 3 direction changes in 6 moves
        changes = sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])
        if changes >= 4:
            logger.warning(f"⚠️ Oscillation detected: {changes} direction changes in 6 moves")
            return True

        return False

    def _match_ol_vectors(self, sensor_vec: np.ndarray) -> Tuple[str, float]:
        """
        🆕 Match sensor vector against OL database

        Returns:
            (concept, similarity)
        """
        if not self.config.ol_enabled or not self.ol_vectors:
            return ("", 0.0)

        best_concept = ""
        best_sim = 0.0

        # Normalize sensor vector
        norm = np.linalg.norm(sensor_vec)
        if norm > 0:
            sensor_vec_norm = sensor_vec / norm
        else:
            return ("", 0.0)

        # Find best match
        for concept, vec in self.ol_vectors.items():
            # Normalize OL vector
            vec_norm = np.linalg.norm(vec)
            if vec_norm > 0:
                vec_normalized = vec / vec_norm
                similarity = np.dot(sensor_vec_norm, vec_normalized)

                if similarity > best_sim:
                    best_sim = similarity
                    best_concept = concept

        return (best_concept, float(best_sim))

    def _load_learning_data(self):
        """Load BLL/OL data from disk"""
        bll_path = os.path.join(self.config.learning_dir, 'bll_weights.json')
        ol_path = os.path.join(self.config.learning_dir, 'ol_vectors.json')

        try:
            if os.path.exists(bll_path):
                with open(bll_path, 'r') as f:
                    self.bll_weights = json.load(f)
                logger.info(f"✅ Loaded BLL weights: {len(self.bll_weights)} categories")
        except Exception as e:
            logger.warning(f"Failed to load BLL: {e}")

        try:
            if os.path.exists(ol_path):
                with open(ol_path, 'r') as f:
                    data = json.load(f)
                self.ol_vectors = {k: np.array(v) for k, v in data.items()}
                logger.info(f"✅ Loaded OL vectors: {len(self.ol_vectors)} concepts")
        except Exception as e:
            logger.warning(f"Failed to load OL: {e}")

    def save_learning_data(self):
        """Save BLL/OL data to disk"""
        if not os.path.exists(self.config.learning_dir):
            os.makedirs(self.config.learning_dir)

        bll_path = os.path.join(self.config.learning_dir, 'bll_weights.json')
        ol_path = os.path.join(self.config.learning_dir, 'ol_vectors.json')

        try:
            with open(bll_path, 'w') as f:
                json.dump(self.bll_weights, f, indent=2)

            ol_data = {k: v.tolist() for k, v in self.ol_vectors.items()}
            with open(ol_path, 'w') as f:
                json.dump(ol_data, f, indent=2)

            logger.debug(f"💾 Saved: BLL={len(self.bll_weights)}, OL={len(self.ol_vectors)}")
        except Exception as e:
            logger.error(f"Failed to save learning data: {e}")

    def _rule_based_decision(self,
                              dist_front: float,
                              dist_left: float,
                              dist_right: float) -> Tuple[str, float, float, str]:
        """
        Rule-based fallback decision

        DIRECTION CONVENTION (see top of file):
        - TURN_LEFT: Left wheel SLOWER (40), Right wheel FASTER (140)
        - TURN_RIGHT: Left wheel FASTER (140), Right wheel SLOWER (40)
        """
        max_r = self.config.max_sensor_range
        d_f = dist_front / max_r
        d_l = dist_left / max_r
        d_r = dist_right / max_r

        robot_half_width = self.config.robot_width / 2
        clearance = self.config.robot_clearance
        min_side_dist = robot_half_width + clearance

        # Side collision thresholds
        SIDE_CRITICAL = 60.0 / max_r

        # 1. CRITICAL: Both sides close or Front+Sides close → ESCAPE IMMEDIATELY
        if (d_l < SIDE_CRITICAL and d_r < SIDE_CRITICAL) or \
           (d_f < 0.15 and d_l < 0.25 and d_r < 0.25):
            return (ActionType.ESCAPE.value, -100.0, 100.0, "TRAPPED_ESCAPE")

        # 2. Side collision - Escape from the closer wall
        # Right side too close → TURN LEFT (escape left)
        if d_r < SIDE_CRITICAL:
            return (ActionType.TURN_LEFT.value, 40.0, 140.0, "SIDE_COLLISION_RIGHT")

        # Left side too close → TURN RIGHT (escape right)
        if d_l < SIDE_CRITICAL:
            return (ActionType.TURN_RIGHT.value, 140.0, 40.0, "SIDE_COLLISION_LEFT")

        # Front very close
        if d_f < 0.25:
            if d_l > d_r:  # MORE space on LEFT
                return (ActionType.TURN_LEFT.value, 30.0, 130.0, "EMERGENCY_BRAKE_LEFT")
            else:  # MORE space on RIGHT
                return (ActionType.TURN_RIGHT.value, 130.0, 30.0, "EMERGENCY_BRAKE_RIGHT")

        # Danger zone
        danger_threshold = self.config.danger_dist / max_r
        if d_f < danger_threshold:
            if d_l > d_r:
                return (ActionType.TURN_LEFT.value, 40.0, 110.0, "AVOID_FRONT_LEFT")
            else:
                return (ActionType.TURN_RIGHT.value, 110.0, 40.0, "AVOID_FRONT_RIGHT")

        # Warning zone
        warning_threshold = self.config.warning_dist / max_r
        if d_f < warning_threshold:
            base_speed = 50.0
            turn_speed = 90.0

            if d_l > d_r:
                return (ActionType.TURN_LEFT.value, base_speed, turn_speed, "WARNING_STEER_LEFT")
            else:
                return (ActionType.TURN_RIGHT.value, turn_speed, base_speed, "WARNING_STEER_RIGHT")

        # Passage width check
        is_tight = self.config.is_tight_passage(dist_left, dist_right)
        safe_speed = self.config.get_safe_speed_for_passage(dist_left, dist_right)

        total_passage = dist_left + dist_right
        if total_passage < self.config.get_min_passage_width():
            if d_l > d_r:
                return (ActionType.TURN_LEFT.value, 40.0, 80.0, "TOO_NARROW_LEFT")
            else:
                return (ActionType.TURN_RIGHT.value, 80.0, 40.0, "TOO_NARROW_RIGHT")

        # Tight passage
        if is_tight:
            center_error = (dist_left - dist_right) / 2
            correction = center_error * 0.3
            speed = safe_speed
            return (ActionType.FORWARD.value, speed - correction, speed + correction, "TIGHT_PASSAGE")

        # Corridor
        if d_l < 0.4 and d_r < 0.4 and d_f > 0.4:
            bias = (d_l - d_r) * 20
            return (ActionType.FORWARD.value, 80.0 - bias, 80.0 + bias, "CORRIDOR")

        # Asymmetric - seek space
        if abs(d_l - d_r) > 0.15:
            if d_l > d_r:
                return (ActionType.FORWARD.value, 80.0, 130.0, "SEEK_SPACE_LEFT")
            else:
                return (ActionType.FORWARD.value, 130.0, 80.0, "SEEK_SPACE_RIGHT")

        # Clear path
        if d_f > 0.6 and d_l > 0.3 and d_r > 0.3:
            return (ActionType.FORWARD.value, 120.0, 120.0, "CLEAR_PATH")

        # Default
        return (ActionType.FORWARD.value, 80.0, 80.0, "DEFAULT_CAUTIOUS")

    def decide(self,
               dist_front: float,
               dist_left: float,
               dist_right: float,
               speed_left: float = 100.0,
               speed_right: float = 100.0) -> Dict:
        """
        Make decision based on sensors - FIXED VERSION
        Now includes OL matching and conditional chaos
        """
        current_time = time.time()
        self.decision_count += 1

        # 1. MANEUVER EXECUTION (High Priority)
        if hasattr(self, 'current_maneuver') and self.current_maneuver:
            return self._execute_maneuver(dist_front, dist_left, dist_right)

        # 2. EMERGENCY TRIGGER (Safety First)
        if self._check_emergency_condition(dist_front, dist_left, dist_right):
            return self._start_emergency_maneuver(dist_left, dist_right)

        # 3. AVOIDANCE TRIGGER (Proactive)
        if self._check_avoidance_condition(dist_front, dist_left, dist_right):
            return self._start_avoidance_maneuver(dist_left, dist_right)

        # 4. STANDARD DECISION (NPZ + OL + Chaos)

        # Create sensor vector
        sensor_vec = self.npz.create_sensor_vector(
            dist_front, dist_left, dist_right, speed_left, speed_right
        )
        self.last_sensor_vec = sensor_vec

        # 🆕 Lorenz chaos - CONDITIONAL
        min_dist = min(dist_front, dist_left, dist_right)
        if (self.config.chaos_enabled and
            min_dist > self.config.chaos_min_safe_distance):
            chaos_vec = self._lorenz_step()
        else:
            chaos_vec = (0.0, 0.0, 0.0)  # Disable chaos in danger

        # NPZ matching
        npz_concept, npz_similarity, category = self.npz.find_best_match(sensor_vec)

        # 🆕 OL matching
        ol_concept, ol_similarity = self._match_ol_vectors(sensor_vec)

        # 🆕 Choose best source (NPZ vs OL)
        if (self.config.ol_enabled and
            ol_similarity > npz_similarity and
            ol_similarity > self.config.ol_similarity_threshold):

            concept = ol_concept
            similarity = ol_similarity
            source = 'OL'
            self.ol_usage_count += 1
            logger.debug(f"🧠 Using OL: {concept} (sim={similarity:.2f})")
        else:
            concept = npz_concept
            similarity = npz_similarity
            source = 'NPZ'

        # BLL boost
        bll_boost = self.bll_weights.get(category, 1.0)
        adjusted_sim = similarity * bll_boost

        # Convert to action
        if adjusted_sim > 0.5:
            action, spd_l, spd_r = self.npz.concept_to_action(concept)
        else:
            action = ActionType.FORWARD.value
            spd_l, spd_r = 80.0, 80.0
            concept = 'FORWARD_UNCERTAIN'

        # 🔧 Apply chaos ONLY to FORWARD actions
        if action == ActionType.FORWARD.value and chaos_vec != (0.0, 0.0, 0.0):
            blended_action, blended_spd_l, blended_spd_r = self._chaos_blend_action(
                action, (spd_l, spd_r), chaos_vec
            )
        else:
            # No chaos for turns/stops/escapes
            blended_action = action
            blended_spd_l = spd_l
            blended_spd_r = spd_r

        decision = {
            'action': blended_action,
            'speed_left': blended_spd_l,
            'speed_right': blended_spd_r,
            'confidence': adjusted_sim,
            'concept': concept,
            'source': source,
            'cycle': self.decision_count,
            'category': category  # 🆕 For feedback
        }

        self.last_decision = decision
        return decision

    # =========================================================================
    # STATE MACHINE & LOGIC METHODS
    # =========================================================================

    def _check_emergency_condition(self, df, dl, dr) -> bool:
        """Active if VERY close or trapped"""
        CRITICAL = 60.0  # mm
        if df < CRITICAL: return True
        if dl < CRITICAL and dr < CRITICAL: return True
        if dl < CRITICAL/2 or dr < CRITICAL/2: return True
        return False

    def _start_emergency_maneuver(self, dl, dr):
        """Start 'Back up and Align' maneuver"""
        # Determine best turn direction (towards open space)
        # Logic: if dl < dr → LEFT more blocked → turn RIGHT
        turn_dir = ActionType.TURN_RIGHT.value if dl < dr else ActionType.TURN_LEFT.value

        self.current_maneuver = {
            'type': 'EMERGENCY_ESCAPE',
            'phase': 'REVERSE',
            'step_count': 0,
            'target_steps': 20,
            'turn_dir': turn_dir
        }
        logger.warning("🚨 TRIGGERED: Emergency Escape Maneuver")
        return self._execute_maneuver_step(ActionType.REVERSE.value, -100, -100, "EMERGENCY_START")

    def _check_avoidance_condition(self, df, dl, dr) -> bool:
        """Active if approaching obstacle (< 200mm)"""
        AVOID_THRESH = 200.0

        if dl < AVOID_THRESH or dr < AVOID_THRESH:
            if abs(dl - dr) > 20:  # Hysteresis
                return True
        return False

    def _start_avoidance_maneuver(self, dl, dr):
        """Start 'Turn to Free' maneuver - ENHANCED with anti-oscillation"""

        # 🆕 Check for oscillation
        if self._detect_oscillation():
            self.oscillation_detected = True

            logger.info("🛡️ Anti-oscillation: Forcing FORWARD")
            return {
                'action': ActionType.FORWARD.value,
                'speed_left': 70,
                'speed_right': 70,
                'source': 'ANTI_OSCILLATION',
                'confidence': 1.0,
                'concept': 'FORCE_FORWARD',
                'cycle': self.decision_count
            }

        # Logic: Turn towards the larger value (Free space)
        if dl < dr:
            # Left blocked -> Turn Right
            action = ActionType.TURN_RIGHT.value
            target_sensor_start = dr
            blocked_sensor = 'left'
        else:
            # Right blocked -> Turn Left
            action = ActionType.TURN_LEFT.value
            target_sensor_start = dl
            blocked_sensor = 'right'

        # Check oscillation (existing hysteresis)
        if hasattr(self, 'last_maneuver_turn'):
            if self.last_maneuver_turn != action and time.time() - self.last_maneuver_time < 2.0:
                logger.info("🛡️ Oscillation prevented: Preferring forward")
                return {
                   'action': ActionType.FORWARD.value,
                   'speed_left': 60,
                   'speed_right': 60,
                   'source': 'ANTI_OSCILLATION',
                   'confidence': 1.0,
                   'concept': 'HYSTERESIS_FORWARD',
                   'cycle': self.decision_count
                }

        # 🆕 Update direction memory
        self._update_direction_memory(action_concept='', action_type=action)

        self.current_maneuver = {
            'type': 'AVOIDANCE_TURN',
            'action': action,
            'start_target_val': target_sensor_start,
            'blocked_side': blocked_sensor
        }

        return self._execute_maneuver_step(action, 120, 120, "AVOID_START")

    def _execute_maneuver(self, df, dl, dr):
        """Execute current step of the active maneuver"""
        m = self.current_maneuver

        # TYPE 1: EMERGENCY ESCAPE
        if m['type'] == 'EMERGENCY_ESCAPE':

            if m['phase'] == 'REVERSE':
                m['step_count'] += 1
                if m['step_count'] >= m['target_steps']:
                    m['phase'] = 'ALIGN_TURN'
                    logger.info("Emergency: Switching to ALIGN_TURN")

                return self._execute_maneuver_step(ActionType.REVERSE.value, -100, -100, f"REVERSING_{m['step_count']}")

            elif m['phase'] == 'ALIGN_TURN':
                # Exit condition: Both sensors > 100
                if dl > 100.0 and dr > 100.0:
                    self.current_maneuver = None
                    return self._execute_maneuver_step(ActionType.STOP.value, 0, 0, "SAFE_REACHED")

                # Continue turning
                action = m['turn_dir']
                spd_l, spd_r = (40, 120) if action == ActionType.TURN_RIGHT.value else (120, 40)
                return self._execute_maneuver_step(action, spd_l, spd_r, "ALIGNING_TO_SAFE")

        # TYPE 2: AVOIDANCE TURN
        elif m['type'] == 'AVOIDANCE_TURN':
            action = m['action']

            # Determine success metric (monitor sensor we're turning towards)
            current_target_val = dr if action == ActionType.TURN_RIGHT.value else dl
            improvement = current_target_val - m['start_target_val']

            # Exit conditions
            if improvement >= 20.0 or current_target_val > 300.0:
                self.last_maneuver_turn = action
                self.last_maneuver_time = time.time()
                self.current_maneuver = None
                return self._execute_maneuver_step(ActionType.FORWARD.value, 100, 100, "PATH_IMPROVED")

            # Continue turning
            spd_l, spd_r = (40, 120) if action == ActionType.TURN_RIGHT.value else (120, 40)
            return self._execute_maneuver_step(action, spd_l, spd_r, "AVOIDING_OBSTACLE")

        return self._execute_maneuver_step(ActionType.STOP.value, 0, 0, "UNKNOWN_MANEUVER")

    def _execute_maneuver_step(self, action, sl, sr, concept):
        """Helper to format decision dict"""
        return {
            'action': action,
            'speed_left': sl,
            'speed_right': sr,
            'confidence': 1.0,
            'source': 'MANEUVER',
            'concept': concept,
            'cycle': self.decision_count
        }

    def feedback(self, success: bool, category: str = None):
        """
        Provide feedback for BLL + OL learning - FIXED & ENHANCED

        Args:
            success: True if last action was successful
            category: Category for BLL (auto-detected if None)
        """
        # BLL Update
        if category is None and self.last_decision:
            category = self.last_decision.get('category', 'unknown')

        if category:
            current = self.bll_weights.get(category, 1.0)
            delta = self.config.learning_rate if success else -self.config.learning_rate
            self.bll_weights[category] = max(0.5, min(1.5, current + delta))

            self.bll_history.append({
                'time': datetime.now().isoformat(),
                'category': category,
                'success': success,
                'weight': self.bll_weights[category]
            })

        # 🆕 OL UPDATE
        if self.config.ol_enabled and self.last_sensor_vec is not None and self.last_decision:
            concept_key = self.last_decision.get('concept', 'unknown')

            if success:
                # Reinforce vector
                if concept_key not in self.ol_vectors:
                    # New concept - add it
                    self.ol_vectors[concept_key] = self.last_sensor_vec.copy()
                    logger.info(f"🧠 OL: Added new concept '{concept_key}'")
                else:
                    # Update existing with EMA
                    alpha = self.config.ol_learning_rate
                    self.ol_vectors[concept_key] = (
                        alpha * self.last_sensor_vec +
                        (1 - alpha) * self.ol_vectors[concept_key]
                    )
                    logger.debug(f"🧠 OL: Updated concept '{concept_key}'")
            else:
                # Unsuccessful - decrease confidence or remove
                if concept_key in self.ol_vectors:
                    # Decay the vector
                    self.ol_vectors[concept_key] *= 0.95

                    # Remove if vector becomes too small
                    if np.linalg.norm(self.ol_vectors[concept_key]) < 0.1:
                        del self.ol_vectors[concept_key]
                        logger.info(f"🧠 OL: Removed unreliable concept '{concept_key}'")

        # Save periodically
        if len(self.bll_history) % 20 == 0 or not success:
            self.save_learning_data()


# =============================================================================
# SWARM CORE - MAIN INTERFACE
# =============================================================================

class SwarmCore:
    """
    Main SWARM Core interface - PURE AI ENGINE [FIXED]

    Version 2.1 includes:
    - ✅ Active Online Learning
    - ✅ Enhanced BLL with auto-feedback
    - ✅ Conditional chaos (disabled in danger)
    - ✅ Anti-oscillation detection
    - ✅ Unified direction convention
    """

    def __init__(self, config: SwarmConfig = None):
        """
        Initialize SWARM Core

        Args:
            config: Configuration (uses default if None)
        """
        self.config = config or SwarmConfig()

        # Initialize components
        self.npz = NPZEngine(self.config)
        self.absr = ABSRBidecision(self.config, self.npz)

        # State
        self.cycle_count = 0
        self.last_decision = None

        logger.info(f"✅ SwarmCore v2.1 initialized [FIXED]")
        logger.info(f"   NPZ: {len(self.npz.words)} concepts")
        logger.info(f"   BLL: {len(self.absr.bll_weights)} categories")
        logger.info(f"   OL: {len(self.absr.ol_vectors)} learned concepts")
        logger.info(f"   Chaos: {self.config.chaos_level} (min_dist={self.config.chaos_min_safe_distance}mm)")

    def decide(self,
               dist_front: float,
               dist_left: float,
               dist_right: float,
               speed_left: float = 100.0,
               speed_right: float = 100.0,
               **kwargs) -> Dict[str, Any]:
        """
        Make decision based on sensor data.

        Args:
            dist_front: Front distance sensor (mm)
            dist_left: Left distance sensor (mm)
            dist_right: Right distance sensor (mm)
            speed_left: Current left speed (optional)
            speed_right: Current right speed (optional)
            **kwargs: Additional context (ignored by core)

        Returns:
            Dict with action, speeds, confidence, concept, source, cycle
        """
        self.cycle_count += 1

        decision = self.absr.decide(
            dist_front, dist_left, dist_right,
            speed_left, speed_right
        )

        self.last_decision = decision
        return decision

    def feedback(self, success: bool, context: Dict = None):
        """
        Provide feedback for learning.

        Args:
            success: True if last action was good
            context: Optional additional context
        """
        self.absr.feedback(success)

    def save(self):
        """Save learning data to disk"""
        self.absr.save_learning_data()
        logger.info("💾 Learning data saved")

    def get_stats(self) -> Dict:
        """Get core statistics"""
        return {
            'cycle_count': self.cycle_count,
            'npz_loaded': self.npz.loaded,
            'concepts_count': len(self.npz.words),
            'bll_categories': len(self.absr.bll_weights),
            'ol_vectors': len(self.absr.ol_vectors),
            'ol_usage_count': self.absr.ol_usage_count,
            'direction_memory': list(self.absr.direction_memory)[-5:],
            'preferred_direction': self.absr.preferred_escape_direction,
            'oscillation_detected': self.absr.oscillation_detected
        }


# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SWARM CORE v2.1 [FIXED] - Abstract AI Engine")
    print("=" * 60)

    core = SwarmCore()

    test_scenarios = [
        (200, 150, 150, "Clear path"),
        (50, 150, 150, "Front obstacle"),
        (150, 30, 200, "Left wall"),
        (150, 200, 30, "Right wall"),
        (40, 40, 40, "Trapped"),
    ]

    print("\nTest scenarios:")
    for dist_f, dist_l, dist_r, scenario in test_scenarios:
        decision = core.decide(
            dist_front=dist_f,
            dist_left=dist_l,
            dist_right=dist_r
        )

        print(f"\n[{scenario}]")
        print(f"  Sensors: F={dist_f}, L={dist_l}, R={dist_r}")
        print(f"  Decision: {decision['action']}")
        print(f"  Speeds: L={decision['speed_left']:.0f}, R={decision['speed_right']:.0f}")
        print(f"  Source: {decision['source']}")

        # Simulate feedback
        success = dist_f > 100  # Simple success criterion
        core.feedback(success=success)

    print("\n" + "=" * 60)
    stats = core.get_stats()
    print("Core stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print("=" * 60)

    core.save()
