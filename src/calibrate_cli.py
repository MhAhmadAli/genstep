#!/usr/bin/env python3
"""
calibrate_cli.py — Standalone CLI tool for calibrating GenStep AI sensors.

Usage:
    python3 src/calibrate_cli.py              # Run calibration (default 5 s)
    python3 src/calibrate_cli.py --time 10    # Run calibration for 10 s
    python3 src/calibrate_cli.py --show       # Print current stored calibration
"""

import argparse
import json
import sys

from config import (
    SONAR_1_PINS, SONAR_2_PINS, SONAR_3_PINS,
    IR_1_PIN, IR_2_PIN, BUZZER_PIN,
    CALIBRATION_TIME_SECONDS,
)
from calibration import CalibrationManager
from sensors.ultrasonic import UltrasonicArray
from sensors.ir import IRArray
from feedback.alerter import BuzzerAlerter


def show_calibration():
    """Print stored calibration data without initializing hardware."""
    mgr = CalibrationManager()
    data = mgr.load()
    print("\n--- Stored Calibration Data ---")
    print(json.dumps(data, indent=2))
    print("-------------------------------\n")


def run_calibration(duration):
    """Initialize hardware, run the calibration routine, then exit."""
    print("Initializing hardware for calibration...")
    sonar = UltrasonicArray(SONAR_1_PINS, SONAR_2_PINS, SONAR_3_PINS)
    ir = IRArray(IR_1_PIN, IR_2_PIN)
    buzzer = BuzzerAlerter(BUZZER_PIN)

    mgr = CalibrationManager()
    # Load existing data first so we can fall back to last valid calibration
    mgr.load()

    try:
        result = mgr.run_calibration(sonar, ir, buzzer, duration=duration)
        print("\n--- Calibration Result ---")
        print(json.dumps(result, indent=2))
        print("--------------------------\n")
    finally:
        sonar.close()
        ir.close()
        buzzer.close()


def main():
    parser = argparse.ArgumentParser(description="GenStep AI Sensor Calibration Tool")
    parser.add_argument(
        "--time", type=float, default=CALIBRATION_TIME_SECONDS,
        help=f"Calibration sampling duration in seconds (default: {CALIBRATION_TIME_SECONDS})"
    )
    parser.add_argument(
        "--show", action="store_true",
        help="Print current stored calibration data and exit"
    )

    args = parser.parse_args()

    if args.show:
        show_calibration()
    else:
        run_calibration(args.time)


if __name__ == "__main__":
    main()
