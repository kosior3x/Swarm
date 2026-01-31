#!/usr/bin/env python3
"""
SWARM RESET UTILITY
Creates a fresh, standardized environment for the SWARM Robot.
"""

import os
import shutil
import numpy as np
import json

def reset_environment():
    print("=" * 60)
    print("SWARM ENVIRONMENT RESET")
    print("=" * 60)

    # 1. Directories
    dirs = ['logs', 'brain_data', 'training_data']
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"[CREATED] {d}/")
        else:
            print(f"[OK] {d}/ exists")

    # 2. Archive old logs instead of deleting (Safety)
    log_files = [f for f in os.listdir('logs') if f.endswith('.csv') or f.endswith('.log')]
    if log_files:
        archive_dir = os.path.join('logs', 'archive')
        if not os.path.exists(archive_dir):
            os.makedirs(archive_dir)

        for f in log_files:
            src = os.path.join('logs', f)
            dst = os.path.join(archive_dir, f)
            shutil.move(src, dst)
        print(f"[ARCHIVED] {len(log_files)} logs moved to logs/archive/")

    # 3. Reset Learning Memory (OL/BLL)
    # BLL Weights
    bll_path = 'logs/bll_weights.json'
    bll_default = {}  # Empty start, weights default to 1.0 in code
    with open(bll_path, 'w') as f:
        json.dump(bll_default, f, indent=2)
    print(f"[RESET] {bll_path}")

    # OL Vectors
    ol_path = 'logs/ol_vectors.json'
    ol_default = {}
    with open(ol_path, 'w') as f:
        json.dump(ol_default, f, indent=2)
    print(f"[RESET] {ol_path}")

    # 4. Create Empty/Basic NPZ if missing
    npz_path = 'BEHAVIORAL_BRAIN.npz'
    if not os.path.exists(npz_path):
        print("[INIT] Creating basic BEHAVIORAL_BRAIN.npz...")
        # Use swarm_trainer to generate basic set
        try:
            import swarm_trainer
            config = swarm_trainer.TrainerConfig()
            swarm_trainer.create_basic_concepts(npz_path, config)
            print(f"[CREATED] {npz_path} (Basic Concepts)")
        except ImportError:
            print("[ERROR] Could not import swarm_trainer!")
    else:
        print(f"[OK] {npz_path} exists (retaining existing brain)")

    print("\nEnvironment is ready for incremental learning.")
    print("=" * 60)

if __name__ == "__main__":
    reset_environment()
