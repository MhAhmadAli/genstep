from gpiozero import DistanceSensor
from gpiozero.pins.pigpio import PiGPIOFactory

class UltrasonicArray:
    """Manages the 3 ultrasonic sensors"""
    
    def __init__(self, s1_pins, s2_pins, s3_pins, max_distance=4.0):
        # We use pigpio factory for more precise timing if available,
        # but fallback to default if not configured. It's often required for reliable sonar on Pi.
        try:
            self.factory = PiGPIOFactory()
        except:
            self.factory = None
            
        kwargs = {"max_distance": max_distance}
        if self.factory:
            kwargs["pin_factory"] = self.factory

        self.sensor1 = DistanceSensor(trigger=s1_pins[0], echo=s1_pins[1], **kwargs)
        self.sensor2 = DistanceSensor(trigger=s2_pins[0], echo=s2_pins[1], **kwargs)
        self.sensor3 = DistanceSensor(trigger=s3_pins[0], echo=s3_pins[1], **kwargs)

    def get_obstacle_distance(self):
        """Returns the minimum distance amongst the 2 front-facing sensors in meters."""
        dist2 = self.sensor2.distance
        dist3 = self.sensor3.distance
        return min(dist2, dist3)

    def get_ground_distance(self):
        """Returns the distance of the downward-facing sensor in meters."""
        return self.sensor1.distance

    def close(self):
        self.sensor1.close()
        self.sensor2.close()
        self.sensor3.close()
