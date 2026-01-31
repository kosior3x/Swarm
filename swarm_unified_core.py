#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SWARM UNIFIED CORE - LEGACY WRAPPER
================================================================================

Version: 2.0 (Wrapper)
Date: 2026-01-26

NOTE:
-----
This is a COMPATIBILITY WRAPPER.
The actual core logic has been moved to:
- swarm_core.py (Abstract AI Engine)
- swarm_main.py (System Integrator)

Do NOT modify this file directly. Modify swarm_core.py instead.
================================================================================
"""

import logging

# Re-export classes from new architecture
from swarm_core import SwarmCore, SwarmConfig, ActionType, NPZEngine, ABSRBidecision
from swarm_main import SwarmCoreController, DataSource, SwarmSystem, DataLogger

# Configure logging to match old behavior
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger('SwarmCore')
logger.warning("Using LEGACY wrapper swarm_unified_core.py - Please migrate to swarm_core.py")

# Compatibility check
if __name__ == "__main__":
    print("="*60)
    print("THIS IS A LEGACY WRAPPER")
    print("Please run 'swarm_main.py' or 'loader.py' instead.")
    print("="*60)

    # Run simulation test from new main if executed directly
    from swarm_main import main
    main()