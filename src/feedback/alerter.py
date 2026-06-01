from gpiozero import PWMOutputDevice
import time
import threading


class BuzzerAlerter:
    """Manages the buzzer for various levels of tactile/audio feedback."""

    def __init__(self, pin, cooldown_seconds=10):
        # Using PWM to allow control over intensity (for vibration simulation)
        # Even if it's a standard active buzzer, PWM can simulate "lower volume" or vibration force.
        self.buzzer = PWMOutputDevice(pin)
        self.stop_event = threading.Event()
        self.alert_thread = None
        self.cooldown_seconds = float(cooldown_seconds)
        self._next_allowed_start = 0.0
        self._cooldown_lock = threading.Lock()

    def _can_start_buzz(self):
        now = time.monotonic()
        with self._cooldown_lock:
            if now < self._next_allowed_start:
                return False
            self._next_allowed_start = now + self.cooldown_seconds
            return True

    def cooldown_remaining_seconds(self):
        now = time.monotonic()
        with self._cooldown_lock:
            return max(0.0, self._next_allowed_start - now)

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
        if not self._can_start_buzz():
            return False
        self.stop()
        self.alert_thread = threading.Thread(target=self._play_pattern, args=(0.1, 0.9, 0.3, True))
        self.alert_thread.start()
        return True

    def moderate_alert(self):
        """Barrier at >1m, <1.5m: Moderate beeping."""
        if not self._can_start_buzz():
            return False
        self.stop()
        self.alert_thread = threading.Thread(target=self._play_pattern, args=(0.2, 0.4, 0.6, True))
        self.alert_thread.start()
        return True

    def intense_alert(self):
        """Barrier at <1m: Intense beeping."""
        if not self._can_start_buzz():
            return False
        self.stop()
        self.alert_thread = threading.Thread(target=self._play_pattern, args=(0.1, 0.1, 1.0, True))
        self.alert_thread.start()
        return True

    def play_sound(self, duration=0.2, intensity=1.0):
        """Play one short predefined beep."""
        if not self._can_start_buzz():
            return False
        self.stop()
        self.buzzer.value = intensity
        time.sleep(duration)
        self.buzzer.value = 0.0
        return True

    def find_stick_pattern(self):
        """Play a finite 'find me' pattern sequence."""
        if not self._can_start_buzz():
            return False
        self.stop()

        def _run():
            for _ in range(8):
                if self.stop_event.is_set():
                    break
                self.buzzer.value = 1.0
                time.sleep(0.12)
                self.buzzer.value = 0.0
                time.sleep(0.12)
            self.buzzer.value = 0.0

        self.alert_thread = threading.Thread(target=_run, daemon=True)
        self.alert_thread.start()
        return True

    def close(self):
        self.stop()
        self.buzzer.close()
