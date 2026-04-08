from gpiozero import PWMOutputDevice
import time
import threading

class BuzzerAlerter:
    """Manages the buzzer for various levels of tactile/audio feedback."""

    def __init__(self, pin):
        # Using PWM to allow control over intensity (for vibration simulation)
        # Even if it's a standard active buzzer, PWM can simulate "lower volume" or vibration force.
        self.buzzer = PWMOutputDevice(pin)
        self.stop_event = threading.Event()
        self.alert_thread = None

    def _play_pattern(self, on_time, off_time, intensity, continuous=False):
        """Internal method to run a beeping pattern on a separate thread."""
        while not self.stop_event.is_set():
            self.buzzer.value = intensity
            time.sleep(on_time)
            self.buzzer.value = 0.0
            time.sleep(off_time)
            if not continuous:
                break

    def stop(self):
        """Stop any currently playing alert pattern."""
        self.stop_event.set()
        if self.alert_thread is not None:
            self.alert_thread.join()
        self.buzzer.value = 0.0
        self.stop_event.clear()

    def light_alert(self):
        """Barrier at 3m: Light beeping."""
        self.stop()
        self.alert_thread = threading.Thread(target=self._play_pattern, args=(0.1, 0.9, 0.3, True))
        self.alert_thread.start()

    def moderate_alert(self):
        """Barrier at >1m, <1.5m: Moderate beeping."""
        self.stop()
        self.alert_thread = threading.Thread(target=self._play_pattern, args=(0.2, 0.4, 0.6, True))
        self.alert_thread.start()

    def intense_alert(self):
        """Barrier at <1m: Intense beeping."""
        self.stop()
        self.alert_thread = threading.Thread(target=self._play_pattern, args=(0.1, 0.1, 1.0, True))
        self.alert_thread.start()

    def close(self):
        self.stop()
        self.buzzer.close()
