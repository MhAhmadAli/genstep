import cv2
import os
import sys
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
        use_picamera2=True,
        camera_resolution=(1280, 720),
        frame_interval_seconds=0.2,
        image_size=640,
        stairs_infer_every_n=1,
        general_infer_every_n=1,
        model_factory=None,
        capture=None,
    ):
        self.enabled = bool(enabled)
        self.stairs_model_path = stairs_model_path
        self.general_model_path = general_model_path
        self.stairs_conf = float(stairs_conf)
        self.general_conf = float(general_conf)
        self.hazard_classes = set(hazard_classes or set())
        self.use_picamera2 = bool(use_picamera2)
        self.camera_resolution = tuple(camera_resolution) if camera_resolution else (1280, 720)
        self.frame_interval_seconds = max(0.05, float(frame_interval_seconds))
        self.image_size = int(image_size) if image_size else None
        self.stairs_infer_every_n = max(1, int(stairs_infer_every_n))
        self.general_infer_every_n = max(1, int(general_infer_every_n))
        self.last_error = None
        self.last_detections = []
        self._last_frame_ts = 0.0
        self._frame_counter = 0
        self._stairs_detections = []
        self._general_detections = []
        self._camera_backend = "none"
        self.picam2 = None

        self.cap = capture if capture is not None else None
        if capture is not None:
            self._camera_backend = "injected"
        elif self.enabled:
            self._initialize_camera(camera_index)

        self._model_factory = model_factory
        self.stairs_model = None
        self.general_model = None
        self._load_models()

    def _import_picamera2(self):
        try:
            from picamera2 import Picamera2

            return Picamera2
        except ImportError:
            dist_packages = "/usr/lib/python3/dist-packages"
            if os.path.isdir(dist_packages) and dist_packages not in sys.path:
                sys.path.append(dist_packages)
            from picamera2 import Picamera2

            return Picamera2

    def _initialize_camera(self, camera_index):
        if self.use_picamera2:
            try:
                Picamera2 = self._import_picamera2()
                self.picam2 = Picamera2()
                config = self.picam2.create_preview_configuration(
                    main={"size": self.camera_resolution, "format": "RGB888"}
                )
                self.picam2.configure(config)
                self.picam2.start()
                time.sleep(1.0)
                self._camera_backend = "picamera2"
                print("[Camera] Using Picamera2 backend.")
                return
            except Exception as exc:
                print(f"[Camera] Picamera2 unavailable, falling back to OpenCV: {exc}")
                self.picam2 = None

        self.cap = cv2.VideoCapture(camera_index)
        if self.cap and getattr(self.cap, "isOpened", None) and self.cap.isOpened():
            time.sleep(1.0)
            self._camera_backend = "opencv"
            print("[Camera] Using OpenCV backend.")
            return

        self.last_error = "Camera is not available."
        print(f"[Camera] {self.last_error}")
        self.enabled = False

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

    def _read_frame(self):
        if self._camera_backend == "picamera2" and self.picam2:
            try:
                rgb = self.picam2.capture_array("main")
                if rgb is None:
                    return False, None
                # Convert to BGR for OpenCV and Ultralytics consistency.
                return True, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            except Exception:
                return False, None
        if self.cap:
            return self.cap.read()
        return False, None

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
        if not self.enabled or (self.picam2 is None and self.cap is None):
            return []

        now = time.monotonic()
        if now - self._last_frame_ts < self.frame_interval_seconds:
            return self.last_detections
        self._last_frame_ts = now

        ret, frame = self._read_frame()
        if not ret:
            self.last_error = "Failed to capture frame from camera."
            return []

        try:
            self._frame_counter += 1
            if self._frame_counter % self.stairs_infer_every_n == 0:
                self._stairs_detections = self._predict(
                    self.stairs_model,
                    frame,
                    self.stairs_conf,
                    source="stairs_model",
                )
            if self._frame_counter % self.general_infer_every_n == 0:
                self._general_detections = self._predict(
                    self.general_model,
                    frame,
                    self.general_conf,
                    source="general_model",
                )
            detections = self._stairs_detections + self._general_detections
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
        if self.picam2:
            try:
                self.picam2.stop()
            except Exception:
                pass
            self.picam2 = None
        if self.cap:
            self.cap.release()
