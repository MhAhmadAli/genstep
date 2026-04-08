from gpiozero import LineSensor

class IRArray:
    """Manages the 2 IR sensors typically used for drop-off/stairs detection."""
    
    def __init__(self, ir1_pin, ir2_pin):
        self.sensor1 = LineSensor(ir1_pin)
        self.sensor2 = LineSensor(ir2_pin)

    def detect_dropoff(self):
        """Returns True if any sensor detects a drop-off (or obstacle depending on IR type).
        Typically, for a LineSensor, 'is_active' depends on reflection.
        """
        # Note: behavior of is_active depends on whether the IR sensor is active high or low.
        return not self.sensor1.is_active or not self.sensor2.is_active

    def close(self):
        self.sensor1.close()
        self.sensor2.close()
