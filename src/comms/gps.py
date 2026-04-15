import serial
from comms.software_serial import SoftwareSerial


class GPSModule:
    """Reads and parses NMEA location data from a GPS module."""

    def __init__(
        self,
        port=None,
        baud_rate=9600,
        timeout=1,
        read_retries=10,
        rx_pin=None,
        tx_pin=None,
    ):
        self.serial = None
        self.last_error = None
        self.read_retries = max(1, int(read_retries))
        try:
            if rx_pin is not None and tx_pin is not None:
                self.serial = SoftwareSerial(rx_pin, tx_pin, baud_rate=baud_rate, timeout=timeout)
            else:
                if not port:
                    raise ValueError("A serial port is required when rx_pin/tx_pin are not provided.")
                self.serial = serial.Serial(port, baud_rate, timeout=timeout)
        except Exception as exc:
            self.last_error = f"Failed to initialize GPS: {exc}"
            print(self.last_error)

    def _parse_coordinate(self, value, direction, degree_digits):
        if not value or not direction:
            return None
        try:
            degrees = int(value[:degree_digits])
            minutes = float(value[degree_digits:])
        except ValueError:
            return None

        decimal = degrees + (minutes / 60.0)
        if direction in ("S", "W"):
            decimal = -decimal
        return decimal

    def _parse_rmc(self, sentence):
        parts = sentence.split(",")
        if len(parts) < 10:
            return None
        if parts[2] != "A":  # A = valid fix, V = void
            return None

        lat = self._parse_coordinate(parts[3], parts[4], 2)
        lon = self._parse_coordinate(parts[5], parts[6], 3)
        if lat is None or lon is None:
            return None

        return {
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "utc": parts[1] or None,
            "source": sentence[1:6],
            "raw": sentence,
        }

    def _parse_gga(self, sentence):
        parts = sentence.split(",")
        if len(parts) < 7:
            return None
        fix_quality = parts[6]
        if fix_quality in ("", "0"):
            return None

        lat = self._parse_coordinate(parts[2], parts[3], 2)
        lon = self._parse_coordinate(parts[4], parts[5], 3)
        if lat is None or lon is None:
            return None

        return {
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "utc": parts[1] or None,
            "source": sentence[1:6],
            "raw": sentence,
        }

    def _parse_sentence(self, sentence):
        if len(sentence) >= 6 and sentence.startswith("$"):
            sentence_type = sentence[3:6]
            if sentence_type == "RMC":
                return self._parse_rmc(sentence)
            if sentence_type == "GGA":
                return self._parse_gga(sentence)
        return None

    def get_location(self):
        """Return parsed GPS coordinates or None when no valid fix exists."""
        if not self.serial:
            return None

        self.last_error = None
        try:
            self.serial.reset_input_buffer()
            for _ in range(self.read_retries):
                line = self.serial.readline().decode("ascii", errors="ignore").strip()
                if not line:
                    continue
                location = self._parse_sentence(line)
                if location:
                    return location
            self.last_error = "No valid GPS fix found."
            return None
        except Exception as exc:
            self.last_error = f"GPS read failed: {exc}"
            print(self.last_error)
            return None

    def close(self):
        if self.serial:
            self.serial.close()
