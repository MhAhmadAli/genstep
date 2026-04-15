import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from comms.gps import GPSModule


class TestGPSModule(unittest.TestCase):
    def test_get_location_returns_parsed_coordinates_from_gprmc(self):
        fake_serial = MagicMock()
        fake_serial.readline.side_effect = [
            b"$GPRMC,123519,A,4807.038,N,01131.000,E,0.0,0.0,230394,,,A*00\r\n",
        ]

        with patch("comms.gps.serial.Serial", return_value=fake_serial):
            gps = GPSModule("/dev/mock", 9600, timeout=1, read_retries=1)
            location = gps.get_location()

        self.assertIsNotNone(location)
        self.assertAlmostEqual(location["latitude"], 48.1173, places=4)
        self.assertAlmostEqual(location["longitude"], 11.516667, places=4)
        self.assertEqual(location["source"], "GPRMC")
        self.assertEqual(location["utc"], "123519")

    def test_get_location_returns_none_when_no_valid_fix(self):
        fake_serial = MagicMock()
        fake_serial.readline.side_effect = [
            b"$GPRMC,123519,V,4807.038,N,01131.000,E,0.0,0.0,230394,,,N*00\r\n",
            b"$GPGGA,123519,,,,,0,00,99.99,,,,,,*00\r\n",
        ]

        with patch("comms.gps.serial.Serial", return_value=fake_serial):
            gps = GPSModule("/dev/mock", 9600, timeout=1, read_retries=2)
            location = gps.get_location()

        self.assertIsNone(location)
        self.assertEqual(gps.last_error, "No valid GPS fix found.")


if __name__ == "__main__":
    unittest.main()
