import serial

class GPSModule:
    """Reads NMEA sentences from the GPS module."""

    def __init__(self, port, baud_rate=9600):
        try:
            self.serial = serial.Serial(port, baud_rate, timeout=1)
        except Exception as e:
            print(f"Failed to initialize GPS: {e}")
            self.serial = None

    def get_location(self):
        """Reads serial data and extracts basic location.
        A full implementation would parse $GPGGA or $GPRMC sentences.
        """
        if not self.serial:
            return None

        # Flush input to get the most recent reading
        self.serial.reset_input_buffer()
        
        for _ in range(10): # Try to read a few lines
            line = self.serial.readline().decode('ascii', errors='ignore').strip()
            if line.startswith('$GPRMC') or line.startswith('$GPGGA'):
                # For brevity, returning the raw sentence. 
                # Better implementation would use 'pynmea2' library to parse lat/lon.
                return line
        return None

    def close(self):
        if self.serial:
            self.serial.close()
