"""
Manual GPS serial console for real hardware testing.

Usage:
    .venv/bin/python tests/test_gps_raw_console.py

Features:
    - Live raw GPS output (NMEA lines)
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import serial
import config
from comms.software_serial import SoftwareSerial
from config import BAUD_RATE, GPS_PORT, GPS_RX_PIN, GPS_TX_PIN, USE_SOFTWARE_SERIAL

GPS_TIMEOUT_SECONDS = getattr(config, "GPS_SERIAL_TIMEOUT_SECONDS", 1)


def _open_gps_transport():
    if USE_SOFTWARE_SERIAL:
        return SoftwareSerial(
            rx_pin=GPS_RX_PIN,
            tx_pin=GPS_TX_PIN,
            baud_rate=BAUD_RATE,
            timeout=GPS_TIMEOUT_SECONDS,
        )
    return serial.Serial(GPS_PORT, BAUD_RATE, timeout=GPS_TIMEOUT_SECONDS)


def main():
    print("Opening GPS raw console...")
    if USE_SOFTWARE_SERIAL:
        print(f"Mode: software serial | GPS RX{GPS_RX_PIN}/TX{GPS_TX_PIN} @ {BAUD_RATE}")
    else:
        print(f"Mode: hardware serial | GPS {GPS_PORT} @ {BAUD_RATE}")

    try:
        gps_transport = _open_gps_transport()
        print("[GPS] Connected.")
    except Exception as exc:
        print(f"[GPS] Failed to open: {exc}")
        return

    print("Streaming raw GPS NMEA output. Press Ctrl+C to stop.\n")

    try:
        while True:
            try:
                line = gps_transport.readline().decode("ascii", errors="ignore").strip()
                if line:
                    print(f"[GPS] {line}")
            except Exception as exc:
                print(f"[GPS] Read error: {exc}")
                time.sleep(0.1)
                continue
    except KeyboardInterrupt:
        pass
    finally:
        gps_transport.close()
        print("\nClosed GPS raw console.")


if __name__ == "__main__":
    main()
