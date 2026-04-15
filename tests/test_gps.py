import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from comms.gps import GPSModule
from config import (
    BAUD_RATE,
    GPS_PORT,
    GPS_READ_RETRIES,
    GPS_RX_PIN,
    GPS_SERIAL_TIMEOUT_SECONDS,
    GPS_TX_PIN,
    USE_SOFTWARE_SERIAL,
)


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

    def test_get_location_parses_gn_talker_sentences(self):
        fake_serial = MagicMock()
        fake_serial.readline.side_effect = [
            b"$GNRMC,123519,A,4807.038,N,01131.000,E,0.0,0.0,230394,,,A*00\r\n",
        ]

        with patch("comms.gps.serial.Serial", return_value=fake_serial):
            gps = GPSModule("/dev/mock", 9600, timeout=1, read_retries=1)
            location = gps.get_location()

        self.assertIsNotNone(location)
        self.assertAlmostEqual(location["latitude"], 48.1173, places=4)
        self.assertAlmostEqual(location["longitude"], 11.516667, places=4)
        self.assertEqual(location["source"], "GNRMC")
        self.assertEqual(location["utc"], "123519")

    @unittest.skipUnless(
        os.getenv("RUN_REAL_GPS_TEST") == "1",
        "Set RUN_REAL_GPS_TEST=1 to run real GPS hardware integration test.",
    )
    def test_get_location_from_real_device(self):
        if USE_SOFTWARE_SERIAL:
            gps = GPSModule(
                baud_rate=BAUD_RATE,
                timeout=GPS_SERIAL_TIMEOUT_SECONDS,
                read_retries=GPS_READ_RETRIES,
                rx_pin=GPS_RX_PIN,
                tx_pin=GPS_TX_PIN,
            )
        else:
            gps = GPSModule(
                GPS_PORT,
                BAUD_RATE,
                timeout=GPS_SERIAL_TIMEOUT_SECONDS,
                read_retries=GPS_READ_RETRIES,
            )

        try:
            self.assertIsNotNone(
                gps.serial,
                f"Failed to initialize real GPS device: {gps.last_error}",
            )
            location = gps.get_location()
            self.assertIsNotNone(
                location,
                f"No valid GPS fix received from device. Last error: {gps.last_error}",
            )
            self.assertIn("latitude", location)
            self.assertIn("longitude", location)
            self.assertGreaterEqual(location["latitude"], -90.0)
            self.assertLessEqual(location["latitude"], 90.0)
            self.assertGreaterEqual(location["longitude"], -180.0)
            self.assertLessEqual(location["longitude"], 180.0)
        finally:
            gps.close()


if __name__ == "__main__":
    unittest.main()
