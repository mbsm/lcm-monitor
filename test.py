#!/usr/bin/env python3
"""LCM traffic simulator for testing the network monitor.

Note: This requires LCM message types (gps_t, state_t) to be installed
or available in your Python path. Update the imports below based on
your LCM types package structure.
"""
import lcm
import sys
import random
import time


try:
    from gps_t import gps_t
    from state_t import state_t
except ImportError:
    print("Error: LCM message types not found.")
    print("Please install your LCM types package or update sys.path in this file.")
    sys.exit(1)


class Rate:
    def __init__(self, hz):
        self.period = 1 / hz
        self.next_time = time.time() + self.period

    def sleep(self):
        remaining = self.next_time - time.time()
        if remaining > 0:
            time.sleep(remaining)
        self.next_time += self.period


def main():
    """Entry point for lcm-test command."""
    print("Starting LCM test traffic generator...")
    print("Publishing on channels: gps, state")
    print("Press Ctrl+C to stop")

    lc = lcm.LCM()
    rate = Rate(100)

    try:
        while True:
            gps = gps_t()
            gps.fix = 4
            gps.latitude = 123456
            gps.longitude = 456786
            gps.altitude = 0
            gps.heading = 147
            gps.ground_speed = 2.25 + random.random()

            state = state_t()

            lc.publish("gps", gps.encode())
            lc.publish("state", state.encode())
            rate.sleep()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == '__main__':
    main()
