"""
CalibrationManager — handles sampling, computing, persisting, and loading
sensor calibration data for GenStep AI.
"""

import json
import os
import time
from datetime import datetime

from config import (
    CALIBRATION_FILE,
    CALIBRATION_TIME_SECONDS,
    STEP_TOLERANCE,
    STEP_UP_THRESHOLD,
    STEP_DOWN_THRESHOLD,
    GROUND_BASELINE,
)


# ---------------------------------------------------------------------------
# Defaults dict — used when no calibration file exists or data is invalid
# ---------------------------------------------------------------------------
DEFAULTS = {
    "ground_baseline": GROUND_BASELINE,
    "step_up_threshold": STEP_UP_THRESHOLD,
    "step_down_threshold": STEP_DOWN_THRESHOLD,
    "front_clear_min": 2.5,
    "ir1_baseline": True,
    "ir2_baseline": True,
    "calibrated_at": None,
}


class CalibrationManager:
    """Reads, writes, and executes sensor calibration."""

    def __init__(self, filepath=None):
        self.filepath = filepath or CALIBRATION_FILE
        self.data = dict(DEFAULTS)  # start with a copy of defaults

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def load(self):
        """Load calibration from JSON.  Falls back to defaults on any error."""
        if not os.path.exists(self.filepath):
            print(f"[Calibration] No file found at {self.filepath}. Using defaults.")
            return self.data

        try:
            with open(self.filepath, "r") as f:
                stored = json.load(f)

            # Validate the important keys exist and are reasonable
            if not self._validate(stored):
                print("[Calibration] Stored data failed validation. Using defaults.")
                return self.data

            self.data = stored
            print(f"[Calibration] Loaded from {self.filepath} "
                  f"(calibrated at {stored.get('calibrated_at', 'unknown')}).")
        except (json.JSONDecodeError, IOError) as exc:
            print(f"[Calibration] Error reading file: {exc}. Using defaults.")

        return self.data

    def save(self, data=None):
        """Atomically write calibration data to the JSON file."""
        if data is not None:
            self.data = data

        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

        tmp_path = self.filepath + ".tmp"
        try:
            with open(tmp_path, "w") as f:
                json.dump(self.data, f, indent=2)
            os.replace(tmp_path, self.filepath)  # atomic on POSIX
            print(f"[Calibration] Saved to {self.filepath}.")
        except IOError as exc:
            print(f"[Calibration] Failed to save: {exc}")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @staticmethod
    def _validate(data):
        """Return True if the stored calibration looks sane."""
        try:
            baseline = float(data["ground_baseline"])
            # Ground baseline should be between 5 cm and 2 m
            if not (0.05 <= baseline <= 2.0):
                return False
            # Thresholds must be positive
            if float(data["step_up_threshold"]) <= 0:
                return False
            if float(data["step_down_threshold"]) <= 0:
                return False
            return True
        except (KeyError, TypeError, ValueError):
            return False

    # ------------------------------------------------------------------
    # Calibration routine
    # ------------------------------------------------------------------
    def run_calibration(self, sonar, ir, buzzer, duration=None):
        """
        Run the calibration sequence:
        1.  Three short beeps  → "Hold stick steady"
        2.  Sample sensors for `duration` seconds
        3.  Compute baselines & thresholds
        4.  Validate; keep defaults on failure
        5.  Persist to disk
        6.  One long beep      → "Done"

        Returns the calibration dict.
        """
        duration = duration or CALIBRATION_TIME_SECONDS

        # --- Signal: calibration starting (3 short beeps) ---
        for _ in range(3):
            buzzer.buzzer.value = 1.0
            time.sleep(0.15)
            buzzer.buzzer.value = 0.0
            time.sleep(0.15)

        print(f"[Calibration] Sampling for {duration}s — hold the stick steady…")

        ground_readings = []
        front_readings = []
        ir1_readings = []
        ir2_readings = []

        sample_interval = 0.1  # 100 ms
        samples = int(duration / sample_interval)

        for _ in range(samples):
            ground_readings.append(sonar.get_ground_distance())
            front_readings.append(sonar.get_obstacle_distance())
            ir1_readings.append(ir.sensor1.is_active)
            ir2_readings.append(ir.sensor2.is_active)
            time.sleep(sample_interval)

        # --- Compute averages ---
        ground_avg = sum(ground_readings) / len(ground_readings)
        front_avg = sum(front_readings) / len(front_readings)
        ir1_baseline = sum(ir1_readings) / len(ir1_readings) > 0.5  # majority vote
        ir2_baseline = sum(ir2_readings) / len(ir2_readings) > 0.5

        print(f"[Calibration] Ground baseline: {ground_avg:.3f} m")
        print(f"[Calibration] Front clear avg: {front_avg:.3f} m")

        # --- Front sensor occlusion warning ---
        if front_avg < 0.5:
            print("[Calibration] WARNING: Front sensors may be obstructed!")
            # 5 rapid beeps as warning
            for _ in range(5):
                buzzer.buzzer.value = 1.0
                time.sleep(0.08)
                buzzer.buzzer.value = 0.0
                time.sleep(0.08)

        # --- IR check ---
        if not ir1_baseline or not ir2_baseline:
            print("[Calibration] WARNING: IR sensors triggered on flat ground. "
                  "Adjust potentiometers.")
            for _ in range(4):
                buzzer.buzzer.value = 0.6
                time.sleep(0.12)
                buzzer.buzzer.value = 0.0
                time.sleep(0.12)

        # --- Build calibration data ---
        new_data = {
            "ground_baseline": round(ground_avg, 4),
            "step_up_threshold": round(ground_avg - STEP_TOLERANCE, 4),
            "step_down_threshold": round(ground_avg + STEP_TOLERANCE, 4),
            "front_clear_min": round(front_avg, 4),
            "ir1_baseline": ir1_baseline,
            "ir2_baseline": ir2_baseline,
            "calibrated_at": datetime.now().isoformat(),
        }

        # --- Validate before committing ---
        if self._validate(new_data):
            self.data = new_data
            self.save()
            print("[Calibration] Calibration successful.")
        else:
            print("[Calibration] Results invalid — keeping previous / default values.")

        # --- Signal: calibration complete (1 long beep) ---
        buzzer.buzzer.value = 1.0
        time.sleep(0.6)
        buzzer.buzzer.value = 0.0

        return self.data
