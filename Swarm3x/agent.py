#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SWARM CORE AGENT - MAIN ENTRY POINT
"""

import time
import argparse
import sys
import os

# Ensure we can import from local directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from communication import CommunicationController, CommunicationConfig, ConnectionMode, ProtocolType

def main():
    """Main function for Agent"""
    parser = argparse.ArgumentParser(description='Swarm Core Agent')
    parser.add_argument('--host', default='127.0.0.1', help='Server host IP')
    parser.add_argument('--port', type=int, default=8888, help='Server port')
    parser.add_argument('--rate', type=float, default=10.0, help='Update rate (Hz)')

    args = parser.parse_args()

    print("=" * 60)
    print("🤖 SWARM CORE AGENT")
    print("=" * 60)

    # Create configuration
    config = CommunicationConfig(
        mode=ConnectionMode.CLIENT,
        protocol=ProtocolType.JSON_TCP,
        host=args.host,
        port=args.port,
        update_rate_hz=args.rate,
        log_decisions=True,
        log_raw_data=False
    )

    # Set up callbacks
    def on_decision(decision):
        print(f"\r[AGENT] Action: {decision['action']:20} "
              f"L={decision['speed_left']:6.1f} "
              f"R={decision['speed_right']:6.1f} "
              f"Conf: {decision.get('confidence', 0):.2f}   ", end='')

    def on_sensor(sensor):
        pass # Too noisy to print every sensor update

    def on_error(error):
        print(f"\n❌ ERROR: {error}")

    config.on_decision_callback = on_decision
    config.on_sensor_callback = on_sensor
    config.on_error_callback = on_error

    # Create and start controller
    controller = CommunicationController(config)

    try:
        print(f"Connecting to: {args.host}:{args.port}")
        print(f"Update rate: {args.rate} Hz")
        print("Starting agent...")
        print("Press Ctrl+C to stop")
        print()

        controller.start()

        # Keep running
        last_status_time = 0
        while True:
            time.sleep(1)

            # Print status every 5 seconds
            if time.time() - last_status_time > 5.0:
                status = controller.get_status()
                print(f"\n[STATUS] Core: {status['core_version']}, "
                      f"Decisions: {status['core_stats']['decisions_made']}, "
                      f"Connected: {status['connected']}")
                last_status_time = time.time()

    except KeyboardInterrupt:
        print("\n\nStopping agent...")
    finally:
        controller.stop()
        print("Agent stopped.")

if __name__ == "__main__":
    main()
