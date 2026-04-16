import cv2
import time


class AIObjectDetector:
    """Runs dual-model object detection on camera frames."""

    def __init__(
        self,
        camera_index=0,
        enabled=True,
        stairs_model_path="models/stairs.pt",
        general_model_path="yolo11n.pt",
        stairs_conf=0.45,
        general_conf=0.35,
        hazard_classes=None,
        frame_interval_seconds=0.2,
        image_size=640,
        model_factory=None,
        capture=None,
    ):
        self.enabled = bool(enabled)
        self.stairs_model_path = stairs_model_path
        self.general_model_path = general_model_path
        self.stairs_conf = float(stairs_conf)
        self.general_conf = float(general_conf)
        self.hazard_classes = set(hazard_classes or set())
        self.frame_interval_seconds = max(0.05, float(frame_interval_seconds))
        self.image_size = int(image_size) if image_size else None
        self.last_error = None
        self.last_detections = []
        self._last_frame_ts = 0.0

        self.cap = capture if capture is not None else cv2.VideoCapture(camera_index)
        if self.cap and getattr(self.cap, "isOpened", None):
            if self.cap.isOpened():
                time.sleep(1.0)
            elif self.enabled:
                self.last_error = "Camera is not available."
                print(f"[Camera] {self.last_error}")
                self.enabled = False
        else:
            self.last_error = "Camera device failed to initialize."
            print(f"[Camera] {self.last_error}")
            self.enabled = False

        self._model_factory = model_factory
        self.stairs_model = None
        self.general_model = None
        self._load_models()

    def _load_models(self):
        if not self.enabled:
            return
        try:
            if self._model_factory is None:
                from ultralytics import YOLO

                self._model_factory = YOLO

            self.stairs_model = self._model_factory(self.stairs_model_path)
            self.general_model = self._model_factory(self.general_model_path)
            self.last_error = None
            print(
                f"[Camera] Models loaded (stairs='{self.stairs_model_path}', "
                f"general='{self.general_model_path}')."
            )
        except Exception as exc:
            self.last_error = f"Camera model initialization failed: {exc}"
            print(f"[Camera] {self.last_error}")
            self.enabled = False

    def _predict(self, model, frame, conf_threshold, source):
        detections = []
        if not model:
            return detections

        results = model.predict(
            source=frame,
            conf=conf_threshold,
            verbose=False,
            imgsz=self.image_size,
        )
        if not results:
            return detections

        result = results[0]
        boxes = getattr(result, "boxes", None)
        names = getattr(result, "names", {})
        if not boxes:
            return detections

        for box in boxes:
            class_id = int(box.cls[0]) if box.cls is not None else -1
            label = names.get(class_id, str(class_id))
            confidence = float(box.conf[0]) if box.conf is not None else 0.0
            xyxy = box.xyxy[0].tolist() if box.xyxy is not None else [0, 0, 0, 0]
            detections.append(
                {
                    "source": source,
                    "label": str(label).lower(),
                    "confidence": round(confidence, 4),
                    "bbox": [round(float(v), 2) for v in xyxy],
                }
            )
        return detections

    def analyze_frame(self):
        """Capture one frame and return normalized detections."""
        if not self.enabled or not self.cap:
            return []

        now = time.monotonic()
        if now - self._last_frame_ts < self.frame_interval_seconds:
            return self.last_detections
        self._last_frame_ts = now

        ret, frame = self.cap.read()
        if not ret:
            self.last_error = "Failed to capture frame from camera."
            return []

        try:
            detections = []
            detections.extend(
                self._predict(
                    self.stairs_model,
                    frame,
                    self.stairs_conf,
                    source="stairs_model",
                )
            )
            detections.extend(
                self._predict(
                    self.general_model,
                    frame,
                    self.general_conf,
                    source="general_model",
                )
            )
            self.last_detections = detections
            self.last_error = None
        except Exception as exc:
            self.last_error = f"Camera inference failed: {exc}"
            print(f"[Camera] {self.last_error}")
            return []

        return detections

    def summarize_hazards(self, detections):
        labels = {item.get("label") for item in detections}
        stairs_detected = any(item.get("source") == "stairs_model" for item in detections)
        general_hazard_detected = any(label in self.hazard_classes for label in labels)
        return {
            "stairs_detected": stairs_detected,
            "general_hazard_detected": general_hazard_detected,
            "labels": sorted(label for label in labels if label),
        }

    def close(self):
        if self.cap:
            self.cap.release()
