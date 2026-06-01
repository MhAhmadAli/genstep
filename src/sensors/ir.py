from gpiozero import LineSensor

class IRArray:
    """Manages the 2 IR sensors typically used for drop-off/stairs detection."""
    
    def __init__(self, ir1_pin, ir2_pin, active_low=True):
        self.sensor1 = LineSensor(ir1_pin)
        self.sensor2 = LineSensor(ir2_pin)
        # Many TCRT5000-style boards are active-low, but some are active-high.
        # Keep this configurable so field wiring/sensor variants can be flipped
        # in config without editing logic again.
        self.active_low = bool(active_low)

    def detect_dropoff(self):
        """Returns True if any sensor detects a drop-off (or obstacle depending on IR type).
        Typically, for a LineSensor, 'is_active' depends on reflection.
        """
        if self.active_low:
            return (not self.sensor1.is_active) or (not self.sensor2.is_active)
        return self.sensor1.is_active or self.sensor2.is_active

    def close(self):
        self.sensor1.close()
        self.sensor2.close()
