import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from feedback.announcer import AudioAnnouncer


class _RecordingEngine:
    """Stub TTS engine that records spoken phrases instead of making sound."""

    def __init__(self):
        self.spoken = []
        self.properties = {}
        self.stopped = False

    def setProperty(self, name, value):
        self.properties[name] = value

    def say(self, phrase):
        self.spoken.append(phrase)

    def runAndWait(self):
        pass

    def stop(self):
        self.stopped = True


def _make_announcer(engine, cooldown_seconds=5.0, enabled=True):
    return AudioAnnouncer(
        enabled=enabled,
        cooldown_seconds=cooldown_seconds,
        rate=150,
        volume=1.0,
        engine_factory=lambda: engine,
    )


def _wait_for(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


class TestAudioAnnouncer(unittest.TestCase):
    def test_announces_each_label_once_within_cooldown(self):
        engine = _RecordingEngine()
        announcer = _make_announcer(engine, cooldown_seconds=60.0)

        announcer.announce_labels(["person", "car"])
        announcer.announce_labels(["person", "car"])  # within cooldown -> ignored

        self.assertTrue(_wait_for(lambda: len(engine.spoken) >= 2))
        time.sleep(0.1)
        announcer.close()

        self.assertEqual(sorted(engine.spoken), ["car ahead", "person ahead"])
        self.assertTrue(engine.stopped)

    def test_dedupes_within_a_single_batch(self):
        engine = _RecordingEngine()
        announcer = _make_announcer(engine, cooldown_seconds=60.0)

        announcer.announce_labels(["person", "person", "person"])

        self.assertTrue(_wait_for(lambda: len(engine.spoken) >= 1))
        time.sleep(0.1)
        announcer.close()

        self.assertEqual(engine.spoken, ["person ahead"])

    def test_repeats_after_cooldown_elapses(self):
        engine = _RecordingEngine()
        announcer = _make_announcer(engine, cooldown_seconds=0.1)

        announcer.announce_labels(["stairs"])
        self.assertTrue(_wait_for(lambda: len(engine.spoken) == 1))
        time.sleep(0.15)
        announcer.announce_labels(["stairs"])
        self.assertTrue(_wait_for(lambda: len(engine.spoken) == 2))
        announcer.close()

        self.assertEqual(engine.spoken, ["stairs ahead", "stairs ahead"])

    def test_disabled_announcer_is_noop(self):
        engine = _RecordingEngine()
        announcer = _make_announcer(engine, enabled=False)

        announcer.announce_labels(["person"])
        time.sleep(0.1)
        announcer.close()

        self.assertEqual(engine.spoken, [])
        self.assertFalse(announcer.enabled)

    def test_engine_init_failure_disables_announcer(self):
        def _boom():
            raise RuntimeError("no audio device")

        announcer = AudioAnnouncer(enabled=True, engine_factory=_boom)
        announcer.announce_labels(["person"])
        announcer.close()

        self.assertFalse(announcer.enabled)
        self.assertIsNotNone(announcer.last_error)


if __name__ == "__main__":
    unittest.main()
