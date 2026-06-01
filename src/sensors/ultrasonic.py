from gpiozero import DistanceSensor
from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero.exc import DistanceSensorNoEcho
import warnings

class UltrasonicArray:
    """Manages the 3 ultrasonic sensors"""
    
    def __init__(self, s1_pins, s2_pins, s3_pins, max_distance=4.0):
        self.max_distance = float(max_distance)
        # We use pigpio factory for more precise timing if available,
        # but fallback to default if not configured. It's often required for reliable sonar on Pi.
        try:
            self.factory = PiGPIOFactory()
        except:
            self.factory = None

        # No-echo is expected when nothing is detected in range; avoid log spam.
        warnings.filterwarnings("ignore", category=DistanceSensorNoEcho)

        kwargs = {"max_distance": self.max_distance}
        if self.factory:
            kwargs["pin_factory"] = self.factory

        self.sensor1 = DistanceSensor(trigger=s1_pins[0], echo=s1_pins[1], **kwargs)
        self.sensor2 = DistanceSensor(trigger=s2_pins[0], echo=s2_pins[1], **kwargs)
        self.sensor3 = DistanceSensor(trigger=s3_pins[0], echo=s3_pins[1], **kwargs)

    def _to_meters(self, sensor):
        """
        gpiozero DistanceSensor.distance is normalized (0.0..1.0).
        Convert it back to meters using max_distance.
        """
        ratio = float(sensor.distance)
        distance_m = ratio * self.max_distance
        if distance_m < 0:
            return 0.0
        return distance_m

    def get_obstacle_distance(self):
        """Returns the minimum distance amongst the 2 front-facing sensors in meters."""
        dist2 = self._to_meters(self.sensor2)
        dist3 = self._to_meters(self.sensor3)
        return min(dist2, dist3)

    def get_ground_distance(self):
        """Returns the distance of the downward-facing sensor in meters."""
        ratio = float(self.sensor1.distance)
        # For downward sensing, near-max ratio usually indicates no echo (unknown),
        # which should not be interpreted as a dangerous step.
        if ratio >= 0.98:
            return None
        return ratio * self.max_distance

    def close(self):
        self.sensor1.close()
        self.sensor2.close()
        self.sensor3.close()
