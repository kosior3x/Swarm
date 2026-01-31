#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SWARM NPZ TRAINER - Train behavioral model from logs
Processes CSV logs and creates BEHAVIORAL_BRAIN.npz
"""

import numpy as np
import pandas as pd
import os
import glob
import json
from datetime import datetime
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('Trainer')

# ============================================================================
# CONFIG
# ============================================================================

class TrainerConfig:
    log_dir = "logs"
    output_npz = "BEHAVIORAL_BRAIN.npz"
    vector_dim = 38
    max_sensor_range = 400.0
    min_samples_per_concept = 10
    max_concepts = 100


# ============================================================================
# VECTOR CREATION
# ============================================================================

def create_sensor_vector(d_F, d_L, d_R, speed_L=100, speed_R=100, max_r=400.0, dim=38):
    """Create 38D sensor vector"""
    vec = np.zeros(dim, dtype=np.float32)

    # Normalize
    d_f = min(d_F / max_r, 1.0)
    d_l = min(d_L / max_r, 1.0)
    d_r = min(d_R / max_r, 1.0)

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

    # Speed
    spd_l = min(speed_L / 150.0, 1.0)
    spd_r = min(speed_R / 150.0, 1.0)
    vec[10] = spd_l
    vec[11] = spd_r
    vec[12] = (spd_l + spd_r) / 2.0
    vec[13] = abs(spd_l - spd_r)
    vec[14] = 1.0 if speed_L > 0 and speed_R > 0 else 0.0

    # Situations
    vec[20] = 1.0 if d_f < 0.3 else 0.0
    vec[21] = 1.0 if d_l < 0.2 and d_r > 0.5 else 0.0
    vec[22] = 1.0 if d_r < 0.2 and d_l > 0.5 else 0.0
    vec[23] = 1.0 if d_f < 0.2 and d_l < 0.2 and d_r < 0.2 else 0.0
    vec[24] = 1.0 if d_l > 0.8 and d_r > 0.8 and d_f > 0.5 else 0.0
    vec[25] = 1.0 if d_l < 0.4 and d_r < 0.4 and d_f > 0.5 else 0.0

    # Derived
    vec[30] = np.tanh(d_f * 2 - 1)
    vec[31] = np.tanh((d_l - d_r) * 2)
    vec[32] = 1.0 / (1.0 + np.exp(-5 * (d_f - 0.3)))

    # Normalize
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm

    return vec


def classify_situation(d_F, d_L, d_R, action):
    """Classify situation based on sensors and action"""
    max_r = 400.0
    d_f = d_F / max_r
    d_l = d_L / max_r
    d_r = d_R / max_r

    action_upper = str(action).upper()

    # CHAOS
    if 'CHAOS' in action_upper:
        if 'SLOW' in action_upper:
            return "CHAOS_SLOW_MANEUVER"
        if 'FAST' in action_upper:
            return "CHAOS_FAST_MANEUVER"
        if 'DRIFT' in action_upper:
            return "CHAOS_DRIFT_MANEUVER"
        return "CHAOS_HYBRID"

    # DISCOVERED
    if 'DISCOVERED' in action_upper:
        return "OL_DISCOVERED_CONCEPT"

    # EMERGENCY
    if d_f < 0.15 and d_l < 0.2 and d_r < 0.2:
        return "TRAPPED_ALL_BLOCKED"

    if d_f < 0.15:
        if d_l > d_r + 0.1:
            return "FRONT_BLOCKED_SPACE_LEFT"
        elif d_r > d_l + 0.1:
            return "FRONT_BLOCKED_SPACE_RIGHT"
        else:
            return "FRONT_BLOCKED_EQUAL"

    # AVOIDANCE
    if d_l < 0.15 and d_r > 0.4:
        return "LEFT_WALL_SPACE_RIGHT"

    if d_r < 0.15 and d_l > 0.4:
        return "RIGHT_WALL_SPACE_LEFT"

    if d_f < 0.25:
        if d_l > d_r * 1.2:
            return "WARNING_FRONT_FAVOR_LEFT"
        elif d_r > d_l * 1.2:
            return "WARNING_FRONT_FAVOR_RIGHT"
        else:
            return "WARNING_FRONT_NARROW"

    # SPACE SEEKING
    if abs(d_l - d_r) > 0.15:
        if d_l > d_r:
            return "SPACE_SEEKING_LEFT_OPEN"
        else:
            return "SPACE_SEEKING_RIGHT_OPEN"

    # CORRIDOR
    if d_l < 0.35 and d_r < 0.35 and d_f > 0.4:
        if abs(d_l - d_r) < 0.05:
            return "CORRIDOR_CENTERED"
        elif d_l > d_r:
            return "CORRIDOR_DRIFT_LEFT"
        else:
            return "CORRIDOR_DRIFT_RIGHT"

    # CLEAR
    if d_f > 0.6 and d_l > 0.4 and d_r > 0.4:
        return "CLEAR_SPACE_ALL_SIDES"

    if d_f > 0.5:
        if d_l > 0.5 and d_r > 0.5:
            return "OPEN_AREA_EXPLORE"
        elif d_l > d_r:
            return "FORWARD_FAVOR_LEFT_SPACE"
        else:
            return "FORWARD_FAVOR_RIGHT_SPACE"

    # TIGHT
    total = d_l + d_r
    if total < 0.4:
        return "TIGHT_PASSAGE_CRITICAL"
    elif total < 0.6:
        return "TIGHT_PASSAGE_SLOW"

    return "NORMAL_NAVIGATION"


# ============================================================================
# LOAD LOGS
# ============================================================================

def load_all_logs(log_dir="logs"):
    """Load all CSV logs"""
    all_data = []

    # Define patterns for all log types
    patterns = [
        "train_sim_*.csv",
        "train_live_*.csv",
        "train_esp32_*.csv",
        "train_wifi_*.csv",
        "train_main_*.csv",
        "train_legacy_*.csv"
    ]

    all_files = []
    for p in patterns:
        all_files.extend(glob.glob(os.path.join(log_dir, p)))

    # Deduplicate files
    all_files = sorted(list(set(all_files)))

    if not all_files:
        logger.warning(f"No log files found matching patterns: {patterns}")
        return pd.DataFrame()

    for filepath in all_files:
        try:
            # Use on_bad_lines='skip' to handle malformed rows
            df = pd.read_csv(filepath, on_bad_lines='skip')

            # Map columns to internal format
            if 'dist_front' in df.columns:
                df['dist_F'] = df['dist_front']
            if 'dist_left' in df.columns:
                df['dist_L'] = df['dist_left']
            if 'dist_right' in df.columns:
                df['dist_R'] = df['dist_right']
            if 'speed_left' in df.columns:
                df['speed_L'] = df['speed_left']
            if 'speed_right' in df.columns:
                df['speed_R'] = df['speed_right']

            # Add source file column for tracking
            df['source_file'] = os.path.basename(filepath)

            all_data.append(df)
            logger.info(f"Loaded: {filepath} ({len(df)} rows)")
        except Exception as e:
            logger.warning(f"Failed: {filepath}: {e}")

    if not all_data:
        logger.warning("No valid data loaded from log files!")
        return pd.DataFrame()

    combined = pd.concat(all_data, ignore_index=True)
    logger.info(f"Total: {len(combined)} rows from {len(all_files)} files")

    return combined


# ============================================================================
# CLUSTERING
# ============================================================================

def cluster_by_situation(df, config):
    """Cluster data by situation"""
    clusters = defaultdict(list)

    for _, row in df.iterrows():
        try:
            d_F = float(row.get('dist_F', row.get('dist_front', 200)))
            d_L = float(row.get('dist_L', row.get('dist_left', d_F)))
            d_R = float(row.get('dist_R', row.get('dist_right', d_F)))
            speed_L = float(row.get('speed_L', row.get('speed_left', 100)))
            speed_R = float(row.get('speed_R', row.get('speed_right', 100)))
            action = str(row.get('action', 'FORWARD'))
            notes = str(row.get('notes', '')).strip()

            # 1. Trust 'OL_' concepts from logs (Online Learning / Fuses)
            if notes.startswith('OL_') or notes.startswith('RULE_') or ('MANEUVER' in notes):
                situation = notes
            # 2. Trust existing known concepts if logged clearly
            elif notes and notes.isupper() and " " not in notes and len(notes) > 3:
                situation = notes
            # 3. Otherwise classify based on sensors
            else:
                situation = classify_situation(d_F, d_L, d_R, action)

            vec = create_sensor_vector(d_F, d_L, d_R, speed_L, speed_R,
                                      config.max_sensor_range, config.vector_dim)

            clusters[situation].append(vec)
        except:
            continue

    logger.info(f"Found {len(clusters)} unique situations")
    return dict(clusters)


def aggregate_clusters(clusters, config):
    """Aggregate clusters to concepts"""
    words = []
    vectors = []
    categories = []

    sorted_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)

    for situation, vecs in sorted_clusters:
        if len(vecs) < config.min_samples_per_concept:
            continue

        if len(words) >= config.max_concepts:
            break

        mean_vec = np.mean(vecs, axis=0).astype(np.float32)

        norm = np.linalg.norm(mean_vec)
        if norm > 0:
            mean_vec = mean_vec / norm

        if 'FORWARD' in situation:
            category = 'navigation'
        elif 'LEFT' in situation or 'RIGHT' in situation:
            category = 'avoidance'
        elif 'ESCAPE' in situation or 'STOP' in situation or 'BLOCKED' in situation:
            category = 'emergency'
        else:
            category = 'exploration'

        words.append(situation)
        vectors.append(mean_vec)
        categories.append(category)

        logger.info(f"  {situation:40s} [{category}] ({len(vecs)} samples)")

    return words, np.array(vectors, dtype=np.float32), categories


# ============================================================================
# SAVE NPZ
# ============================================================================

def save_npz(words, vectors, categories, output_path, metadata=None):
    """Save NPZ model"""
    if metadata is None:
        metadata = {}

    metadata['created'] = datetime.now().isoformat()
    metadata['vector_dim'] = vectors.shape[1] if len(vectors) > 0 else 38
    metadata['num_concepts'] = len(words)
    metadata['version'] = '2.0'

    np.savez(
        output_path,
        words=np.array(words, dtype=object),
        vectors=vectors,
        categories=np.array(categories, dtype=object),
        metadata=json.dumps(metadata)
    )

    logger.info(f"✅ Saved: {output_path}")
    logger.info(f"  Concepts: {len(words)}")
    logger.info(f"  Vector dim: {vectors.shape[1] if len(vectors) > 0 else 0}")


# ============================================================================
# BASIC CONCEPTS
# ============================================================================

def create_basic_concepts(output_path, config):
    """Create basic concept set"""
    logger.info("Creating basic concept set...")

    basic_situations = [
        # (name, d_F, d_L, d_R, sp_L, sp_R, category)
        ("CLEAR_SPACE_ALL_SIDES", 350, 300, 300, 120, 120, "navigation"),
        ("OPEN_AREA_EXPLORE", 300, 250, 250, 110, 110, "exploration"),
        ("SPACE_SEEKING_LEFT_OPEN", 200, 350, 100, 70, 120, "space_seeking"),
        ("SPACE_SEEKING_RIGHT_OPEN", 200, 100, 350, 120, 70, "space_seeking"),
        ("FORWARD_FAVOR_LEFT_SPACE", 250, 300, 150, 90, 110, "navigation"),
        ("FORWARD_FAVOR_RIGHT_SPACE", 250, 150, 300, 110, 90, "navigation"),
        ("LEFT_WALL_SPACE_RIGHT", 200, 50, 300, 110, 80, "avoidance"),
        ("RIGHT_WALL_SPACE_LEFT", 200, 300, 50, 80, 110, "avoidance"),
        ("FRONT_BLOCKED_SPACE_LEFT", 60, 250, 100, 40, 120, "avoidance"),
        ("FRONT_BLOCKED_SPACE_RIGHT", 60, 100, 250, 120, 40, "avoidance"),
        ("FRONT_BLOCKED_EQUAL", 60, 150, 150, 50, 50, "emergency"),
        ("WARNING_FRONT_FAVOR_LEFT", 100, 250, 120, 60, 100, "avoidance"),
        ("WARNING_FRONT_FAVOR_RIGHT", 100, 120, 250, 100, 60, "avoidance"),
        ("WARNING_FRONT_NARROW", 100, 100, 100, 50, 50, "emergency"),
        ("CORRIDOR_CENTERED", 250, 80, 80, 90, 90, "navigation"),
        ("CORRIDOR_DRIFT_LEFT", 250, 100, 60, 85, 95, "navigation"),
        ("CORRIDOR_DRIFT_RIGHT", 250, 60, 100, 95, 85, "navigation"),
        ("TIGHT_PASSAGE_CRITICAL", 200, 60, 60, 40, 40, "navigation"),
        ("TIGHT_PASSAGE_SLOW", 200, 90, 90, 60, 60, "navigation"),
        ("CRITICAL_RIGHT_ESCAPE_LEFT", 100, 200, 30, 30, 120, "emergency"),
        ("CRITICAL_LEFT_ESCAPE_RIGHT", 100, 30, 200, 120, 30, "emergency"),
        ("TRAPPED_ALL_BLOCKED", 40, 40, 40, -60, 60, "emergency"),
        ("DANGER_SEEK_LEFT", 80, 250, 100, 40, 100, "avoidance"),
        ("DANGER_SEEK_RIGHT", 80, 100, 250, 100, 40, "avoidance"),
        ("DRIFT_AWAY_FROM_LEFT", 250, 60, 200, 100, 80, "navigation"),
        ("DRIFT_AWAY_FROM_RIGHT", 250, 200, 60, 80, 100, "navigation"),
        ("ACTIVE_SEEK_LEFT_SPACE", 200, 320, 150, 80, 130, "exploration"),
        ("ACTIVE_SEEK_RIGHT_SPACE", 200, 150, 320, 130, 80, "exploration"),
        ("NORMAL_NAVIGATION", 200, 150, 150, 100, 100, "navigation"),
        ("DEFAULT_CAUTIOUS", 150, 120, 120, 90, 90, "navigation"),
        ("CHAOS_SLOW_MANEUVER", 120, 120, 120, 50, 70, "chaos"),
        ("CHAOS_DRIFT_MANEUVER", 180, 200, 120, 90, 110, "chaos"),
    ]

    words = []
    vectors = []
    categories = []

    for name, d_F, d_L, d_R, sp_L, sp_R, cat in basic_situations:
        vec = create_sensor_vector(d_F, d_L, d_R, sp_L, sp_R,
                                   config.max_sensor_range, config.vector_dim)
        words.append(name)
        vectors.append(vec)
        categories.append(cat)
        logger.info(f"  + {name:40s} [{cat}]")

    vectors = np.array(vectors, dtype=np.float32)
    metadata = {'type': 'space_aware_concepts', 'version': '2.0', 'generated': True}
    save_npz(words, vectors, categories, output_path, metadata)

    return True


# ============================================================================
# MAIN TRAINER
# ============================================================================

def train_from_logs(log_dir="logs", output_path="BEHAVIORAL_BRAIN.npz", config=None):
    """Main training function"""
    if config is None:
        config = TrainerConfig()

    logger.info("="*60)
    logger.info("SWARM NPZ TRAINER")
    logger.info("="*60)

    # Load logs
    logger.info("\n[1] Loading logs...")
    df = load_all_logs(log_dir)

    if df.empty:
        logger.warning("No data - creating basic concepts")
        return create_basic_concepts(output_path, config)

    # Cluster
    logger.info("\n[2] Clustering by situation...")
    clusters = cluster_by_situation(df, config)

    # Merge with old brain if exists
    if os.path.exists(output_path):
        try:
            old_data = np.load(output_path, allow_pickle=True)
            old_words = list(old_data['words'])
            old_vecs = old_data['vectors']
            for i, word in enumerate(old_words):
                for _ in range(config.min_samples_per_concept + 1):
                    clusters[word].append(old_vecs[i])
            logger.info(f"Merged {len(old_words)} concepts from existing brain")
        except Exception as e:
            logger.warning(f"Could not merge: {e}")

    # Aggregate
    logger.info("\n[3] Aggregating concepts...")
    words, vectors, categories = aggregate_clusters(clusters, config)

    if len(words) == 0:
        logger.warning("No concepts - creating basic set")
        return create_basic_concepts(output_path, config)

    # Save
    logger.info("\n[4] Saving NPZ...")

    # Check old timestamp
    old_mtime = 0
    if os.path.exists(output_path):
        old_mtime = os.path.getmtime(output_path)

    metadata = {
        'source_files': len(df['source_file'].unique()) if 'source_file' in df.columns else 0,
        'total_samples': len(df),
        'training_date': datetime.now().isoformat()
    }
    save_npz(words, vectors, categories, output_path, metadata)

    # Verify update
    if os.path.exists(output_path):
        new_mtime = os.path.getmtime(output_path)
        if new_mtime > old_mtime:
            logger.info("✅ File successfully updated on disk.")
        else:
            logger.warning("⚠️ File timestamp did not change!")

    logger.info("\n" + "="*60)
    logger.info("TRAINING COMPLETE")
    logger.info("="*60)

    return True


def main():
    """Entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="SWARM NPZ Trainer")
    parser.add_argument('--log-dir', default='logs', help='Log directory')
    parser.add_argument('--output', default='BEHAVIORAL_BRAIN.npz', help='Output NPZ')
    parser.add_argument('--min-samples', type=int, default=10, help='Min samples')
    parser.add_argument('--max-concepts', type=int, default=100, help='Max concepts')

    args = parser.parse_args()

    config = TrainerConfig()
    config.log_dir = args.log_dir
    config.output_npz = args.output
    config.min_samples_per_concept = args.min_samples
    config.max_concepts = args.max_concepts

    success = train_from_logs(args.log_dir, args.output, config)

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
