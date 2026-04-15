"""
Manual GSM AT command console for real hardware testing.

Usage:
    .venv/bin/python tests/test_gsm_at_console.py
"""

import os
import select
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import serial
import config
from comms.software_serial import SoftwareSerial
from config import BAUD_RATE, GSM_PORT, GSM_RX_PIN, GSM_TX_PIN, USE_SOFTWARE_SERIAL

SERIAL_TIMEOUT_SECONDS = getattr(config, "GSM_SERIAL_TIMEOUT_SECONDS", 1)


def _open_transport():
    if USE_SOFTWARE_SERIAL:
        return SoftwareSerial(
            rx_pin=GSM_RX_PIN,
            tx_pin=GSM_TX_PIN,
            baud_rate=BAUD_RATE,
            timeout=SERIAL_TIMEOUT_SECONDS,
        )
    return serial.Serial(GSM_PORT, BAUD_RATE, timeout=SERIAL_TIMEOUT_SECONDS)


def _decode_escaped(payload_text):
    # Allows inputs like: raw AT+CMGS="123"\r\nhello\x1a
    return payload_text.encode("utf-8").decode("unicode_escape").encode("latin1", errors="ignore")


def main():
    print("Opening GSM console...")
    if USE_SOFTWARE_SERIAL:
        print(f"Mode: software serial RX{GSM_RX_PIN}/TX{GSM_TX_PIN} @ {BAUD_RATE}")
    else:
        print(f"Mode: hardware serial {GSM_PORT} @ {BAUD_RATE}")
    print("Type AT commands and press Enter (example: AT, AT+CSQ, AT+CREG?)")
    print("Use 'raw <bytes>' for literal payload with escapes (e.g. \\r\\n, \\x1a).")
    print("Type 'exit' to quit.\n")

    transport = _open_transport()
    stop_reader = threading.Event()

    def reader_loop():
        while not stop_reader.is_set():
            try:
                data = transport.read_all()
                if data:
                    print(f"\n< {data.decode('ascii', errors='ignore').rstrip()}\n> ", end="", flush=True)
                else:
                    time.sleep(0.05)
            except Exception as exc:
                print(f"\n[reader error] {exc}")
                break

    reader_thread = threading.Thread(target=reader_loop, daemon=True)
    reader_thread.start()

    try:
        while True:
            print("> ", end="", flush=True)
            if not sys.stdin.isatty():
                ready, _, _ = select.select([sys.stdin], [], [], 0.1)
                if not ready:
                    continue
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()

            if not line:
                continue
            if line.lower() in {"exit", "quit"}:
                break

            if line.lower().startswith("raw "):
                payload = _decode_escaped(line[4:])
            else:
                payload = (line + "\r\n").encode("ascii", errors="ignore")

            transport.write(payload)
    except KeyboardInterrupt:
        pass
    finally:
        stop_reader.set()
        time.sleep(0.1)
        transport.close()
        print("\nClosed GSM console.")


if __name__ == "__main__":
    main()
