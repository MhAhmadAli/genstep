"""
Unit tests for CalibrationManager.
Uses unittest.mock to simulate sensor hardware.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

# Add src to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from calibration import CalibrationManager, DEFAULTS


class TestCalibrationLoad(unittest.TestCase):
    """Tests for CalibrationManager.load()"""

    def test_load_returns_defaults_when_file_missing(self):
        """When no file exists, load() should return defaults."""
        mgr = CalibrationManager(filepath="/tmp/nonexistent_calibration.json")
        data = mgr.load()
        self.assertEqual(data["ground_baseline"], DEFAULTS["ground_baseline"])
        self.assertEqual(data["step_up_threshold"], DEFAULTS["step_up_threshold"])
        self.assertEqual(data["step_down_threshold"], DEFAULTS["step_down_threshold"])

    def test_load_returns_defaults_on_corrupt_json(self):
        """When the file contains invalid JSON, load() should return defaults."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {{{")
            path = f.name

        try:
            mgr = CalibrationManager(filepath=path)
            data = mgr.load()
            self.assertEqual(data["ground_baseline"], DEFAULTS["ground_baseline"])
        finally:
            os.unlink(path)

    def test_load_returns_defaults_on_invalid_values(self):
        """When stored values fail validation, load() should return defaults."""
        bad_data = {
            "ground_baseline": 999.0,  # way too large
            "step_up_threshold": 0.15,
            "step_down_threshold": 0.45,
            "front_clear_min": 2.5,
            "ir1_baseline": True,
            "ir2_baseline": True,
            "calibrated_at": "2026-01-01T00:00:00",
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(bad_data, f)
            path = f.name

        try:
            mgr = CalibrationManager(filepath=path)
            data = mgr.load()
            # Should fall back to defaults because 999m is unreasonable
            self.assertEqual(data["ground_baseline"], DEFAULTS["ground_baseline"])
        finally:
            os.unlink(path)

    def test_load_reads_valid_file(self):
        """When a valid JSON file exists, load() should return its contents."""
        valid_data = {
            "ground_baseline": 0.28,
            "step_up_threshold": 0.13,
            "step_down_threshold": 0.43,
            "front_clear_min": 3.1,
            "ir1_baseline": True,
            "ir2_baseline": True,
            "calibrated_at": "2026-04-01T12:00:00",
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(valid_data, f)
            path = f.name

        try:
            mgr = CalibrationManager(filepath=path)
            data = mgr.load()
            self.assertAlmostEqual(data["ground_baseline"], 0.28)
            self.assertAlmostEqual(data["step_up_threshold"], 0.13)
            self.assertAlmostEqual(data["step_down_threshold"], 0.43)
        finally:
            os.unlink(path)


class TestCalibrationSave(unittest.TestCase):
    """Tests for CalibrationManager.save()"""

    def test_save_creates_file(self):
        """save() should create the JSON file with correct data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "calibration.json")
            mgr = CalibrationManager(filepath=path)
            mgr.data = {
                "ground_baseline": 0.30,
                "step_up_threshold": 0.15,
                "step_down_threshold": 0.45,
                "front_clear_min": 2.5,
                "ir1_baseline": True,
                "ir2_baseline": True,
                "calibrated_at": "2026-04-01T12:00:00",
            }
            mgr.save()

            self.assertTrue(os.path.exists(path))
            with open(path, "r") as f:
                saved = json.load(f)
            self.assertAlmostEqual(saved["ground_baseline"], 0.30)

    def test_save_overwrites_existing(self):
        """Re-calibration should overwrite the old file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "calibration.json")
            mgr = CalibrationManager(filepath=path)

            mgr.data = {"ground_baseline": 0.25, "step_up_threshold": 0.10,
                         "step_down_threshold": 0.40, "front_clear_min": 2.0,
                         "ir1_baseline": True, "ir2_baseline": True,
                         "calibrated_at": "2026-01-01T00:00:00"}
            mgr.save()

            mgr.data["ground_baseline"] = 0.35
            mgr.save()

            with open(path, "r") as f:
                saved = json.load(f)
            self.assertAlmostEqual(saved["ground_baseline"], 0.35)


class TestCalibrationValidation(unittest.TestCase):
    """Tests for CalibrationManager._validate()"""

    def test_valid_data_passes(self):
        valid = {"ground_baseline": 0.30, "step_up_threshold": 0.15,
                 "step_down_threshold": 0.45}
        self.assertTrue(CalibrationManager._validate(valid))

    def test_baseline_too_high_fails(self):
        bad = {"ground_baseline": 5.0, "step_up_threshold": 0.15,
               "step_down_threshold": 0.45}
        self.assertFalse(CalibrationManager._validate(bad))

    def test_baseline_too_low_fails(self):
        bad = {"ground_baseline": 0.01, "step_up_threshold": 0.15,
               "step_down_threshold": 0.45}
        self.assertFalse(CalibrationManager._validate(bad))

    def test_negative_threshold_fails(self):
        bad = {"ground_baseline": 0.30, "step_up_threshold": -0.1,
               "step_down_threshold": 0.45}
        self.assertFalse(CalibrationManager._validate(bad))

    def test_missing_key_fails(self):
        bad = {"ground_baseline": 0.30}
        self.assertFalse(CalibrationManager._validate(bad))


class TestCalibrationRun(unittest.TestCase):
    """Tests for CalibrationManager.run_calibration() with mocked hardware."""

    def _make_mocks(self, ground_val=0.30, front_val=2.5, ir1=True, ir2=True):
        """Create mock sonar, ir, and buzzer objects."""
        sonar = MagicMock()
        sonar.get_ground_distance.return_value = ground_val
        sonar.get_obstacle_distance.return_value = front_val

        ir = MagicMock()
        ir.sensor1.is_active = ir1
        ir.sensor2.is_active = ir2

        buzzer = MagicMock()
        buzzer.buzzer = MagicMock()
        buzzer.buzzer.value = 0.0

        return sonar, ir, buzzer

    def test_successful_calibration_saves_file(self):
        """A normal calibration should save valid data to the file."""
        sonar, ir, buzzer = self._make_mocks(ground_val=0.28, front_val=3.0)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "calibration.json")
            mgr = CalibrationManager(filepath=path)
            result = mgr.run_calibration(sonar, ir, buzzer, duration=0.5)

            self.assertTrue(os.path.exists(path))
            self.assertAlmostEqual(result["ground_baseline"], 0.28, places=2)
            self.assertIsNotNone(result["calibrated_at"])

    def test_invalid_readings_keep_defaults(self):
        """If ground reads 4m (pointed at sky), should keep defaults."""
        sonar, ir, buzzer = self._make_mocks(ground_val=4.0)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "calibration.json")
            mgr = CalibrationManager(filepath=path)
            result = mgr.run_calibration(sonar, ir, buzzer, duration=0.5)

            # Should NOT have saved the bad data — file should not exist
            self.assertFalse(os.path.exists(path))
            # Should still hold defaults
            self.assertEqual(result["ground_baseline"], DEFAULTS["ground_baseline"])

    def test_front_occlusion_warning(self):
        """If front sensors read < 0.5m during calibration, buzzer should warn."""
        sonar, ir, buzzer = self._make_mocks(ground_val=0.30, front_val=0.3)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "calibration.json")
            mgr = CalibrationManager(filepath=path)
            mgr.run_calibration(sonar, ir, buzzer, duration=0.5)

            # Buzzer should have been activated for warning beeps
            # (3 start beeps + 5 warning beeps + 1 end beep = multiple calls)
            self.assertTrue(buzzer.buzzer.value is not None)

    def test_recalibration_overwrites_old_data(self):
        """Running calibration twice should overwrite the first result."""
        sonar1, ir1, buzzer1 = self._make_mocks(ground_val=0.25)
        sonar2, ir2, buzzer2 = self._make_mocks(ground_val=0.35)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "calibration.json")

            mgr = CalibrationManager(filepath=path)
            mgr.run_calibration(sonar1, ir1, buzzer1, duration=0.5)

            mgr2 = CalibrationManager(filepath=path)
            result = mgr2.run_calibration(sonar2, ir2, buzzer2, duration=0.5)

            self.assertAlmostEqual(result["ground_baseline"], 0.35, places=2)


if __name__ == "__main__":
    unittest.main()
