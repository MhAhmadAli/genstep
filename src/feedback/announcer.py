import queue
import threading
import time


class AudioAnnouncer:
    """Speaks detected object labels through the Pi's 3.5mm headphone jack.

    Uses offline pyttsx3 (espeak-ng on the Pi). Speaking happens on a daemon
    worker thread so the safety loop never blocks on `runAndWait()`. Each label
    is announced at most once per `cooldown_seconds` so a persistent object does
    not get repeated every frame.
    """

    def __init__(
        self,
        enabled=True,
        cooldown_seconds=5.0,
        rate=150,
        volume=1.0,
        engine_factory=None,
    ):
        self.enabled = bool(enabled)
        self.cooldown_seconds = float(cooldown_seconds)
        self.rate = int(rate)
        self.volume = float(volume)
        self.last_error = None

        self._engine = None
        self._queue = queue.Queue()
        self._last_spoken = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread = None

        if self.enabled:
            self._engine = self._create_engine(engine_factory)
            if self._engine is not None:
                self._start_worker()
            else:
                self.enabled = False

    def _create_engine(self, engine_factory):
        try:
            if engine_factory is None:
                import pyttsx3

                engine_factory = pyttsx3.init
            engine = engine_factory()
            try:
                engine.setProperty("rate", self.rate)
                engine.setProperty("volume", self.volume)
            except Exception:
                pass
            return engine
        except Exception as exc:
            self.last_error = f"Audio announcer init failed: {exc}"
            print(f"[Audio] {self.last_error}")
            return None

    def _start_worker(self):
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def _worker_loop(self):
        while self._running:
            try:
                phrase = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if phrase is None:
                break
            try:
                self._engine.say(phrase)
                self._engine.runAndWait()
            except Exception as exc:
                self.last_error = f"Audio announcer speak failed: {exc}"
                print(f"[Audio] {self.last_error}")

    def announce_labels(self, labels):
        """Queue spoken announcements for labels past their cooldown."""
        if not self.enabled or not labels:
            return
        now = time.monotonic()
        spoken_this_batch = set()
        with self._lock:
            for label in labels:
                if not label or label in spoken_this_batch:
                    continue
                last = self._last_spoken.get(label)
                if last is not None and now - last < self.cooldown_seconds:
                    continue
                self._last_spoken[label] = now
                spoken_this_batch.add(label)
        for label in spoken_this_batch:
            self._queue.put(self._phrase_for(label))

    def _phrase_for(self, label):
        return f"{label} ahead"

    def close(self):
        self._running = False
        if self._thread is not None:
            self._queue.put(None)
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._engine is not None:
            try:
                self._engine.stop()
            except Exception:
                pass
            self._engine = None
