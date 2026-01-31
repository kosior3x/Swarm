#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SWARM CORE - Abstract AI Decision Engine
================================================================================

Version: 2.1
Date: 2026-01-30

PHILOSOPHY:
-----------
This module is a PURE AI decision engine. It:
- Does NOT know where sensor data comes from (ESP32/Pydroid/Simulation)
- Does NOT know where decisions go (Serial/WebSocket/UI)
- Does NOT have hardware dependencies (no serial, no GPIO, no platform-specific code)
- Is FULLY testable with mock data
- Is PORTABLE across all platforms

USAGE:
------
    from swarm_core import SwarmCore

    core = SwarmCore()
    decision = core.decide(dist_front=200, dist_left=150, dist_right=150)
    print(decision['action'])  # 'FORWARD', 'TURN_LEFT', etc.

ARCHITECTURE:
-------------
    SwarmCore (main interface)
        ├── SwarmConfig (configuration)
        ├── NPZEngine (vector matching)
        └── ABSRBidecision (BLL + OL + Lorenz chaos)

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

    # ABSR settings
    lorenz_sigma: float = 10.0
    lorenz_rho: float = 28.0
    lorenz_beta: float = 8.0 / 3.0
    chaos_level: float = 0.5

    # BLL/OL Learning
    learning_rate: float = 0.1
    memory_size: int = 1000

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
                logger.info(f"NPZ loaded: {len(self.words)} concepts")
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

        DIRECTION CONVENTION:
        - TURN_LEFT: Left wheel SLOWER, Right wheel FASTER = turn LEFT
        - TURN_RIGHT: Left wheel FASTER, Right wheel SLOWER = turn RIGHT
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
# ABSR BIDECISION ENGINE (BLL + OL + Lorenz Chaos)
# =============================================================================

class ABSRBidecision:
    """
    ABSR Bidirectional Decision Engine
    Combines NPZ matching with Behavioral Like Learning (BLL)
    and Online Learning (OL)
    """

    def __init__(self, config: SwarmConfig, npz_engine: NPZEngine):
        self.config = config
        self.npz = npz_engine

        # BLL memory
        self.bll_weights = {}
        self.bll_history = deque(maxlen=config.memory_size)

        # OL additions
        self.ol_vectors = {}

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

        # Direction memory
        self.direction_memory = deque(maxlen=20)
        self.last_turn_direction = None
        self.turn_streak = 0
        self.preferred_escape_direction = None

        self._load_learning_data()

        # State Machine Memory
        self.current_maneuver = None
        self.last_maneuver_turn = None
        self.last_maneuver_time = 0
        self.last_sensor_vec = None

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
        """Blend action with Lorenz chaos dynamics"""
        cx, cy, cz = chaos_vec
        speed_l, speed_r = base_speeds

        intensity = abs(cz) * self.config.chaos_level * 0.5
        direction_blend = cx * 20 * intensity
        speed_modifier = 1.0 + (cy * 0.2 * intensity)

        new_speed_l = max(0, min(150, speed_l * speed_modifier + direction_blend))
        new_speed_r = max(0, min(150, speed_r * speed_modifier - direction_blend))

        return (base_action, new_speed_l, new_speed_r)

    def _update_direction_memory(self, action_concept: str, action_type: str = None):
        """Update direction memory"""
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

            if self.last_turn_direction == direction:
                self.turn_streak += 1
                if self.turn_streak >= 3:
                    self.preferred_escape_direction = direction
            else:
                self.turn_streak = 1
                self.last_turn_direction = direction

    def _load_learning_data(self):
        """Load BLL/OL data from disk"""
        bll_path = os.path.join(self.config.learning_dir, 'bll_weights.json')
        ol_path = os.path.join(self.config.learning_dir, 'ol_vectors.json')

        try:
            if os.path.exists(bll_path):
                with open(bll_path, 'r') as f:
                    self.bll_weights = json.load(f)
                logger.info(f"Loaded BLL weights: {len(self.bll_weights)} categories")
        except Exception as e:
            logger.warning(f"Failed to load BLL: {e}")

        try:
            if os.path.exists(ol_path):
                with open(ol_path, 'r') as f:
                    data = json.load(f)
                self.ol_vectors = {k: np.array(v) for k, v in data.items()}
                logger.info(f"Loaded OL vectors: {len(self.ol_vectors)} words")
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
        except Exception as e:
            logger.error(f"Failed to save learning data: {e}")

    def _rule_based_decision(self,
                              dist_front: float,
                              dist_left: float,
                              dist_right: float) -> Tuple[str, float, float, str]:
        """
        Rule-based fallback decision

        DIRECTION CONVENTION:
        - TURN_LEFT: Left wheel SLOWER, Right wheel FASTER
        - TURN_RIGHT: Left wheel FASTER, Right wheel SLOWER
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
        # This must be first to prevent getting stuck in oscillations
        if (d_l < SIDE_CRITICAL and d_r < SIDE_CRITICAL) or \
           (d_f < 0.15 and d_l < 0.25 and d_r < 0.25):
            return (ActionType.ESCAPE.value, -100.0, 100.0, "TRAPPED_ESCAPE")

        # 2. Side collision - Escape from the closer wall
        # Right side too close → TURN LEFT (escape left)
        if d_r < SIDE_CRITICAL:
            # If left is also somewhat close but we have space, turn sharper
            return (ActionType.TURN_LEFT.value, 40.0, 140.0, "SIDE_COLLISION_RIGHT")

        # Left side too close → TURN RIGHT (escape right)
        if d_l < SIDE_CRITICAL:
            return (ActionType.TURN_RIGHT.value, 140.0, 40.0, "SIDE_COLLISION_LEFT")

        # Front very close
        if d_f < 0.25:
            if d_l > d_r:
                return (ActionType.TURN_LEFT.value, 30.0, 130.0, "EMERGENCY_BRAKE_LEFT")
            else:
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
        Make decision based on sensors with State Machine for maneuvers
        """
        current_time = time.time()
        self.decision_count += 1

        # 1. MANEUVER EXECUTION (High Priority)
        # If we are in a multi-step maneuver, execute next step
        if hasattr(self, 'current_maneuver') and self.current_maneuver:
            return self._execute_maneuver(dist_front, dist_left, dist_right)

        # 2. EMERGENCY TRIGGER (Safety First)
        # Check if we need to start an Emergency Maneuver
        if self._check_emergency_condition(dist_front, dist_left, dist_right):
            return self._start_emergency_maneuver(dist_left, dist_right)

        # 3. AVOIDANCE TRIGGER (Proactive)
        # Check if we need to start an Avoidance Maneuver (< 200mm)
        if self._check_avoidance_condition(dist_front, dist_left, dist_right):
            return self._start_avoidance_maneuver(dist_left, dist_right)

        # Create sensor vector (needed for learning)
        sensor_vec = self.npz.create_sensor_vector(
            dist_front, dist_left, dist_right, speed_left, speed_right
        )
        self.last_sensor_vec = sensor_vec

        # 4. SAFETY FUSE / RULE CHECK
        # Before asking AI, check if specific rule applies (e.g. tight passage, corridor)
        # This acts as the "Fuse" that we want the AI to learn.
        rule_action, rule_sl, rule_sr, rule_concept = self._rule_based_decision(
            dist_front, dist_left, dist_right
        )

        # 5. STANDARD DECISION (NPZ + Chaos)
        # Lorenz chaos
        chaos_vec = self._lorenz_step()

        # NPZ matching
        concept, similarity, category = self.npz.find_best_match(sensor_vec)

        # BLL boost
        bll_boost = self.bll_weights.get(category, 1.0)
        adjusted_sim = similarity * bll_boost

        # DECISION SELECTION
        # If Rule is critical/specific (not just default), it overrides weak AI
        # Or if AI is confident, it takes over (Learning Goal)

        use_rule = False
        if "DEFAULT" not in rule_concept:
            # If AI is weak (< 0.7) and Rule is specific -> Use Rule (Fuse active)
            if adjusted_sim < 0.7:
                use_rule = True

        if use_rule:
            action, spd_l, spd_r = rule_action, rule_sl, rule_sr
            source = 'RULE_FUSE'
            concept = rule_concept
            # Rule actions are usually precise, so we might reduce chaos
            chaos_vec = (0, 0, 0)
        elif adjusted_sim > 0.5:
            action, spd_l, spd_r = self.npz.concept_to_action(concept)
            source = 'NPZ'
        else:
            # Fallback to simple forward if confused
            action = ActionType.FORWARD.value
            spd_l, spd_r = 80.0, 80.0
            source = 'VAGUE'
            concept = 'FORWARD_UNCERTAIN'

        # Apply chaos (only if not a strict rule/fuse)
        if source != 'RULE_FUSE':
            blended_action, blended_spd_l, blended_spd_r = self._chaos_blend_action(
                action, (spd_l, spd_r), chaos_vec
            )
        else:
            blended_action, blended_spd_l, blended_spd_r = action, spd_l, spd_r

        decision = {
            'action': blended_action,
            'speed_left': blended_spd_l,
            'speed_right': blended_spd_r,
            'confidence': adjusted_sim,
            'concept': concept,
            'source': source,
            'cycle': self.decision_count
        }

        self.last_decision = decision
        return decision

    # =========================================================================
    # STATE MACHINE & LOGIC METHODS
    # =========================================================================

    def _check_emergency_condition(self, df, dl, dr) -> bool:
        """Active if VERY close or trapped"""
        CRITICAL = 60.0 # mm
        # Front too close OR both sides too close
        if df < CRITICAL: return True
        if dl < CRITICAL and dr < CRITICAL: return True
        # One side extremely close
        if dl < CRITICAL/2 or dr < CRITICAL/2: return True
        return False

    def _start_emergency_maneuver(self, dl, dr):
        """Start 'Back up and Align' maneuver"""
        # Determine best turn direction (towards open space)
        turn_dir = ActionType.TURN_RIGHT.value if dl < dr else ActionType.TURN_LEFT.value

        self.current_maneuver = {
            'type': 'EMERGENCY_ESCAPE',
            'phase': 'REVERSE',
            'step_count': 0,
            'target_steps': 20,  # Increased to 20 cycles (1 sec) for meaningful reverse
            'turn_dir': turn_dir
        }
        logger.warning("TRIGGERED: Emergency Escape Maneuver")
        return self._execute_maneuver_step(ActionType.REVERSE.value, -100, -100, "EMERGENCY_START")

    def _check_avoidance_condition(self, df, dl, dr) -> bool:
        """Active if approaching obstacle (< 200mm)"""
        AVOID_THRESH = 200.0

        # Only trigger if one side is clearly blocked and other is free(er)
        if dl < AVOID_THRESH or dr < AVOID_THRESH:
            # Prevent triggering if we are essentially in open space or symmetric corridor
            if abs(dl - dr) > 20: # Hysteresis
                return True
        return False

    def _start_avoidance_maneuver(self, dl, dr):
        """Start 'Turn to Free' maneuver with hysteresis"""

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

        # Check oscillation (filtering)
        if hasattr(self, 'last_maneuver_turn'):
            # If we recently turned RIGHT, don't suddenly turn LEFT unless critical
            if self.last_maneuver_turn != action and time.time() - self.last_maneuver_time < 2.0:
                 # Oscillation detected, prefer Forward or strict safety
                 logger.info("Oscillation prevented. Forcing Forward.")
                 return {
                    'action': ActionType.FORWARD.value,
                    'speed_left': 60, 'speed_right': 60,
                    'source': 'ANTI_OSCILLATION',
                    'confidence': 1.0
                 }

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

        # ----------------------------------------------------
        # TYPE 1: EMERGENCY ESCAPE (Reverse 5 -> Turn until Safe)
        # ----------------------------------------------------
        if m['type'] == 'EMERGENCY_ESCAPE':

            # Phase 1: REVERSE
            if m['phase'] == 'REVERSE':
                m['step_count'] += 1
                if m['step_count'] >= m['target_steps']:
                    m['phase'] = 'ALIGN_TURN'
                    logger.info("Emergency: Switching to ALIGN_TURN")

                return self._execute_maneuver_step(ActionType.REVERSE.value, -100, -100, f"REVERSING_{m['step_count']}")

            # Phase 2: ALIGN TURN
            elif m['phase'] == 'ALIGN_TURN':
                # Exit condition: Both sensors > 100
                if dl > 100.0 and dr > 100.0:
                    self.current_maneuver = None # Done
                    return self._execute_maneuver_step(ActionType.STOP.value, 0, 0, "SAFE_REACHED")

                # Continue turning
                action = m['turn_dir']
                spd_l, spd_r = (40, 120) if action == ActionType.TURN_RIGHT.value else (120, 40)
                return self._execute_maneuver_step(action, spd_l, spd_r, "ALIGNING_TO_SAFE")

        # ----------------------------------------------------
        # TYPE 2: AVOIDANCE TURN (Turn until better)
        # ----------------------------------------------------
        elif m['type'] == 'AVOIDANCE_TURN':
            # "Turn towards free until [Target] increases by 20"
            # NOTE: We monitor the 'blocked' side to assume it clears,
            # OR we monitor the 'free' side as requested by user?
            # User guideline: "do momentu zwiekszenia prawego [free side] o 20"

            action = m['action']

            # Determine success metric
            # If turning Right, we watch Right sensor (free space)?
            # Or assume we watch the sensor we are turning TOWARDS.

            current_target_val = dr if action == ActionType.TURN_RIGHT.value else dl
            improvement = current_target_val - m['start_target_val']

            # Exit condition 1: Improved by 20
            # Exit condition 2: Path is clear (> 300)
            # Exit condition 3: Stuck too long (timeout) -> Handled by manual manual timeout if needed, but let's assume sensor change

            if improvement >= 20.0 or current_target_val > 300.0:
                self.last_maneuver_turn = action
                self.last_maneuver_time = time.time()
                self.current_maneuver = None # Done
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
        """Provide feedback for BLL and OL learning"""
        if not self.last_decision:
            return

        if category is None:
            category = self.last_decision.get('category', 'unknown')

        # 1. BLL Update (Weights)
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

        # 2. Online Learning (OL) - Learn from Fuses/Maneuvers
        # If the action was successful and came from a Fuse/Maneuver, memorize it
        source = self.last_decision.get('source', '')
        if success and self.last_sensor_vec is not None:
            if source in ['RULE_FUSE', 'MANEUVER', 'ANTI_OSCILLATION']:
                # Generate a concept name
                concept_name = self.last_decision.get('concept', f"OL_{source}_{int(time.time())}")

                # Add/Update vector in OL memory
                # If concept exists, average it (Simple Moving Average)
                if concept_name in self.ol_vectors:
                    self.ol_vectors[concept_name] = (self.ol_vectors[concept_name] * 0.9) + (self.last_sensor_vec * 0.1)
                else:
                    self.ol_vectors[concept_name] = self.last_sensor_vec

                logger.info(f"OL: Learned {concept_name} from {source}")

        # Save periodically
        if len(self.bll_history) % 20 == 0 or not success:
            self.save_learning_data()


# =============================================================================
# SWARM CORE - MAIN INTERFACE
# =============================================================================

class SwarmCore:
    """
    Main SWARM Core interface - PURE AI ENGINE

    This class is the ONLY thing external modules need to import.
    It provides a clean interface for AI decisions without any
    knowledge of hardware, communication protocols, or UI.

    Usage:
        core = SwarmCore()
        decision = core.decide(dist_front=200, dist_left=150, dist_right=150)
        core.feedback(success=True)
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

        logger.info(f"SwarmCore v2.0 initialized (abstract mode)")
        logger.info(f"NPZ loaded: {self.npz.loaded}, {len(self.npz.words)} concepts")

    def decide(self,
               dist_front: float,
               dist_left: float,
               dist_right: float,
               speed_left: float = 100.0,
               speed_right: float = 100.0,
               **kwargs) -> Dict[str, Any]:
        """
        Make decision based on sensor data.

        This method does NOT know where the data comes from.
        It simply processes input and returns output.

        Args:
            dist_front: Front distance sensor (mm)
            dist_left: Left distance sensor (mm)
            dist_right: Right distance sensor (mm)
            speed_left: Current left speed (optional)
            speed_right: Current right speed (optional)
            **kwargs: Additional context (ignored by core)

        Returns:
            Dict with:
                - action: str (FORWARD, TURN_LEFT, TURN_RIGHT, STOP, ESCAPE)
                - speed_left: float (motor speed 0-150)
                - speed_right: float (motor speed 0-150)
                - confidence: float (0.0-1.0)
                - concept: str (detected concept)
                - source: str (NPZ, RULES, SAFETY)
                - cycle: int (decision cycle number)
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
        logger.info("Learning data saved")

    def get_stats(self) -> Dict:
        """Get core statistics"""
        return {
            'cycle_count': self.cycle_count,
            'npz_loaded': self.npz.loaded,
            'concepts_count': len(self.npz.words),
            'bll_categories': len(self.absr.bll_weights),
            'ol_vectors': len(self.absr.ol_vectors),
            'direction_memory': list(self.absr.direction_memory)[-5:],
            'preferred_direction': self.absr.preferred_escape_direction
        }


# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SWARM CORE v2.0 - Abstract AI Engine")
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

    print("\n" + "=" * 60)
    print("Core stats:", core.get_stats())
    print("=" * 60)
