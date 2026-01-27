#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SWARM MAIN - AUTO-FEEDBACK ADDITIONS [PATCH FILE]
================================================================================

Add these functions to swarm_main.py to enable automatic feedback loop

Version: 2.1
Date: 2026-01-27
================================================================================
"""

from typing import Dict

def evaluate_action_success(
    old_sensors: Dict[str, float],
    new_sensors: Dict[str, float],
    action: str,
    min_improvement: float = 10.0
) -> bool:
    """
    Evaluate if last action was successful

    Success criteria:
    - FORWARD: Front distance didn't decrease significantly
    - TURN_LEFT/RIGHT: Turned towards more open space
    - ESCAPE: Got away from danger zone
    - STOP: Stayed safe

    Args:
        old_sensors: Sensor state before action
        new_sensors: Sensor state after action
        action: Action that was executed
        min_improvement: Minimum distance improvement (mm)

    Returns:
        True if action was successful
    """
    old_f = old_sensors.get('dist_front', 400)
    old_l = old_sensors.get('dist_left', 400)
    old_r = old_sensors.get('dist_right', 400)

    new_f = new_sensors.get('dist_front', 400)
    new_l = new_sensors.get('dist_left', 400)
    new_r = new_sensors.get('dist_right', 400)

    # Check for collision
    if new_f < 40 or new_l < 40 or new_r < 40:
        return False  # Too close = failure

    # Action-specific evaluation
    if action == "FORWARD":
        # Success if maintained or improved front clearance
        return new_f >= (old_f - 20)  # Allow small decrease

    elif action == "TURN_LEFT":
        # Success if left space improved or maintained
        improvement = new_l - old_l
        return improvement >= -10  # Allow small decrease

    elif action == "TURN_RIGHT":
        # Success if right space improved or maintained
        improvement = new_r - old_r
        return improvement >= -10

    elif action == "ESCAPE" or action == "REVERSE":
        # Success if got away from immediate danger
        min_old = min(old_f, old_l, old_r)
        min_new = min(new_f, new_l, new_r)
        return min_new > min_old  # Any improvement is good

    elif action == "STOP":
        # Success if maintained safe distance
        return min(new_f, new_l, new_r) > 60

    # Default: check if robot is in better state
    old_min = min(old_f, old_l, old_r)
    new_min = min(new_f, new_l, new_r)
    return new_min >= old_min


# =============================================================================
# MODIFIED SwarmCoreController.run_control_loop()
# =============================================================================

"""
Replace the existing run_control_loop() method in SwarmCoreController class
with this version that includes automatic feedback:
"""

def run_control_loop_WITH_FEEDBACK(self, max_cycles: int = None):
    """
    Main control loop with AUTOMATIC FEEDBACK

    This version evaluates each action's success and provides
    feedback to the core for BLL and OL learning.
    """
    import time
    import logging

    logger = logging.getLogger('SwarmMain')

    cycle = 0
    last_sensors = None
    last_decision = None
    success_count = 0
    failure_count = 0

    try:
        logger.info("🚀 Starting control loop with AUTO-FEEDBACK")

        while self.running:
            if max_cycles and cycle >= max_cycles:
                break

            # 1. Read sensors
            sensor_data = self.data_source.read_sensors()
            if not sensor_data:
                time.sleep(0.1)
                continue

            # 2. ✅ Provide feedback for last decision
            if last_sensors and last_decision:
                success = evaluate_action_success(
                    old_sensors=last_sensors,
                    new_sensors=sensor_data,
                    action=last_decision['action']
                )

                # Send feedback to core
                self.core.feedback(success=success)

                # Log result
                if success:
                    success_count += 1
                    logger.debug(f"✅ Action {last_decision['action']} successful")
                else:
                    failure_count += 1
                    logger.warning(f"❌ Action {last_decision['action']} failed")

                # Periodic stats
                if (success_count + failure_count) % 50 == 0:
                    total = success_count + failure_count
                    success_rate = (success_count / total) * 100 if total > 0 else 0
                    logger.info(f"📊 Success rate: {success_rate:.1f}% ({success_count}/{total})")

            # 3. Make new decision
            decision = self.core.decide(**sensor_data)

            # 4. Execute
            if self.actuator:
                self.actuator.execute(
                    decision['action'],
                    decision['speed_left'],
                    decision['speed_right']
                )

            # 5. Log
            if self.logger:
                self.logger.log_decision(sensor_data, decision)

            # 6. Remember for next cycle
            last_sensors = sensor_data.copy()
            last_decision = decision

            cycle += 1
            time.sleep(0.05)  # 20 Hz control loop

    except KeyboardInterrupt:
        logger.info("\n⏸️  Stopped by user")
    finally:
        # Final statistics
        total = success_count + failure_count
        if total > 0:
            success_rate = (success_count / total) * 100
            logger.info(f"\n{'='*60}")
            logger.info(f"FINAL STATISTICS:")
            logger.info(f"  Total decisions: {total}")
            logger.info(f"  Successful: {success_count} ({success_rate:.1f}%)")
            logger.info(f"  Failed: {failure_count}")
            logger.info(f"{'='*60}")

        # Save learning data
        logger.info("💾 Saving learning data...")
        self.core.save()
        logger.info("✅ Done!")


# =============================================================================
# USAGE INSTRUCTIONS
# =============================================================================

"""
TO APPLY THIS PATCH:
===================

1. Open swarm_main.py

2. Add the evaluate_action_success() function at the top (after imports)

3. Replace the run_control_loop() method in SwarmCoreController class
   with run_control_loop_WITH_FEEDBACK()

4. Test with simulator first:
   python swarm_simulator.py

5. Monitor logs for success/failure messages

6. Check that logs/bll_weights.json and logs/ol_vectors.json are updated

7. Verify OL usage in core stats:
   core.get_stats()['ol_usage_count']

EXPECTED BEHAVIOR:
==================
- You should see "✅ Action X successful" or "❌ Action X failed" in logs
- Every 50 decisions, you'll see success rate statistics
- BLL weights will adjust based on success/failure
- OL will learn new vectors for successful situations
- On exit, final statistics are displayed
"""

if __name__ == "__main__":
    print(__doc__)
