import serial


class GPSModule:
    """Reads and parses NMEA location data from a GPS module."""

    def __init__(self, port, baud_rate=9600, timeout=1, read_retries=10):
        self.serial = None
        self.last_error = None
        self.read_retries = max(1, int(read_retries))
        try:
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

    def _parse_gprmc(self, sentence):
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
            "source": "GPRMC",
            "raw": sentence,
        }

    def _parse_gpgga(self, sentence):
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
            "source": "GPGGA",
            "raw": sentence,
        }

    def _parse_sentence(self, sentence):
        if sentence.startswith("$GPRMC"):
            return self._parse_gprmc(sentence)
        if sentence.startswith("$GPGGA"):
            return self._parse_gpgga(sentence)
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
