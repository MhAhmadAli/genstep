import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sensors.camera import AIObjectDetector


class _Vec(list):
    def tolist(self):
        return list(self)


class _FakeBox:
    def __init__(self, class_id, conf, bbox):
        self.cls = [class_id]
        self.conf = [conf]
        self.xyxy = [_Vec(bbox)]


class _FakeResult:
    def __init__(self, names, boxes):
        self.names = names
        self.boxes = boxes


class _FakeModel:
    def __init__(self, names, boxes):
        self._result = _FakeResult(names=names, boxes=boxes)

    def predict(self, source, conf, verbose=False, imgsz=None):
        return [self._result]


class _FakeCapture:
    def __init__(self, frame="frame"):
        self._frame = frame
        self._released = False

    def isOpened(self):
        return True

    def read(self):
        return True, self._frame

    def release(self):
        self._released = True


class TestCameraPipeline(unittest.TestCase):
    def test_analyze_frame_merges_stairs_and_general_detections(self):
        capture = _FakeCapture()
        model_factory = lambda _: _FakeModel(names={}, boxes=[])
        detector = AIObjectDetector(
            enabled=True,
            stairs_conf=0.5,
            general_conf=0.4,
            hazard_classes={"person"},
            frame_interval_seconds=0.05,
            synchronous=True,
            model_factory=model_factory,
            capture=capture,
        )
        detector.stairs_model = _FakeModel(
            names={0: "stairs"},
            boxes=[_FakeBox(0, 0.92, [10, 20, 30, 40])],
        )
        detector.general_model = _FakeModel(
            names={0: "person"},
            boxes=[_FakeBox(0, 0.88, [1, 2, 3, 4])],
        )
        detector.enabled = True

        detections = detector.analyze_frame()
        hazards = detector.summarize_hazards(detections)

        self.assertEqual(len(detections), 2)
        self.assertEqual(detections[0]["source"], "stairs_model")
        self.assertEqual(detections[1]["source"], "general_model")
        self.assertTrue(hazards["stairs_detected"])
        self.assertTrue(hazards["general_hazard_detected"])
        self.assertIn("person", hazards["labels"])

        detector.close()
        self.assertTrue(capture._released)

    def test_general_inference_gating_skips_general_model(self):
        capture = _FakeCapture()
        detector = AIObjectDetector(
            enabled=True,
            hazard_classes={"person"},
            frame_interval_seconds=0.05,
            synchronous=True,
            model_factory=lambda _: _FakeModel(names={}, boxes=[]),
            capture=capture,
        )
        detector.stairs_model = _FakeModel(
            names={0: "stairs"},
            boxes=[_FakeBox(0, 0.92, [10, 20, 30, 40])],
        )
        detector.general_model = _FakeModel(
            names={0: "person"},
            boxes=[_FakeBox(0, 0.88, [1, 2, 3, 4])],
        )
        detector.enabled = True

        detector.set_general_inference_enabled(False)
        gated = detector.analyze_frame()
        self.assertEqual([d["source"] for d in gated], ["stairs_model"])

        detector.set_general_inference_enabled(True)
        ungated = detector.analyze_frame()
        self.assertEqual(
            sorted(d["source"] for d in ungated),
            ["general_model", "stairs_model"],
        )
        detector.close()

    def test_async_worker_caches_detections(self):
        capture = _FakeCapture()
        detector = AIObjectDetector(
            enabled=True,
            hazard_classes={"person"},
            frame_interval_seconds=0.05,
            synchronous=False,
            model_factory=lambda _: _FakeModel(names={}, boxes=[]),
            capture=capture,
        )
        detector.stairs_model = _FakeModel(
            names={0: "stairs"},
            boxes=[_FakeBox(0, 0.92, [10, 20, 30, 40])],
        )
        detector.general_model = _FakeModel(
            names={0: "person"},
            boxes=[_FakeBox(0, 0.88, [1, 2, 3, 4])],
        )
        detector.enabled = True

        self.assertEqual(detector.analyze_frame(), [])  # nothing produced yet

        detector.start()
        deadline = time.monotonic() + 2.0
        detections = []
        while time.monotonic() < deadline:
            detections = detector.analyze_frame()
            if detections:
                break
            time.sleep(0.02)

        self.assertEqual(len(detections), 2)
        self.assertEqual(
            sorted(d["source"] for d in detections),
            ["general_model", "stairs_model"],
        )
        detector.close()
        self.assertTrue(capture._released)

    def test_stale_detections_capped_after_slow_tick(self):
        detector = AIObjectDetector(
            enabled=True,
            frame_interval_seconds=0.05,
            max_detection_age_seconds=1.0,
            synchronous=False,
            model_factory=lambda _: _FakeModel(names={}, boxes=[]),
            capture=_FakeCapture(),
        )

        cached = [{"source": "stairs_model", "label": "stairs", "confidence": 0.9, "bbox": [0, 0, 1, 1]}]
        # Simulate a single very slow tick: the uncapped adaptive limit would be
        # 2*0.05 + 2*5.0 = 10.1s, but the absolute cap (1.0s) must win.
        detector._last_tick_duration = 5.0
        detector._latest_detections = cached

        # 2s old: older than the cap -> must be discarded, not returned.
        detector._latest_ts = time.monotonic() - 2.0
        self.assertEqual(detector.analyze_frame(), [])

        # 0.1s old: within the cap -> returned.
        detector._latest_ts = time.monotonic() - 0.1
        self.assertEqual(detector.analyze_frame(), cached)

        detector.close()

    def test_summarize_hazards_without_matches(self):
        detector = AIObjectDetector(
            enabled=False,
            hazard_classes={"person"},
            capture=_FakeCapture(),
        )
        hazards = detector.summarize_hazards(
            [
                {"source": "general_model", "label": "chair", "confidence": 0.8, "bbox": [0, 0, 1, 1]},
            ]
        )
        self.assertFalse(hazards["stairs_detected"])
        self.assertFalse(hazards["general_hazard_detected"])
        self.assertEqual(hazards["labels"], ["chair"])


if __name__ == "__main__":
    unittest.main()
