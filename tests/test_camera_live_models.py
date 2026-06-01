import os
import sys
import time

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import (
    CAMERA_GENERAL_INFER_EVERY_N,
    CAMERA_USE_PICAMERA2,
    CAMERA_IMAGE_SIZE,
    CAMERA_INDEX,
    CAMERA_RESOLUTION,
    CAMERA_STAIRS_INFER_EVERY_N,
    GENERAL_CONFIDENCE_THRESHOLD,
    GENERAL_MODEL_PATH,
    STAIRS_CONFIDENCE_THRESHOLD,
    STAIRS_MODEL_PATH,
)


def _parse_detections(result, source_name):
    detections = []
    boxes = getattr(result, "boxes", None)
    names = getattr(result, "names", {})
    if not boxes:
        return detections

    for box in boxes:
        class_id = int(box.cls[0]) if box.cls is not None else -1
        label = str(names.get(class_id, class_id)).lower()
        conf = float(box.conf[0]) if box.conf is not None else 0.0
        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
        detections.append(
            {
                "source": source_name,
                "label": label,
                "confidence": conf,
                "bbox": (x1, y1, x2, y2),
            }
        )
    return detections


def _draw_detections(frame, detections):
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        source = det["source"]
        color = (0, 0, 255) if source == "stairs_model" else (0, 255, 255)
        text = f'{det["label"]} {det["confidence"]:.2f} ({source})'
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame,
            text,
            (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
        )


def _open_camera():
    if CAMERA_USE_PICAMERA2:
        try:
            try:
                from picamera2 import Picamera2
            except ImportError:
                import sys

                dist_packages = "/usr/lib/python3/dist-packages"
                if dist_packages not in sys.path:
                    sys.path.append(dist_packages)
                from picamera2 import Picamera2

            picam2 = Picamera2()
            config = picam2.create_preview_configuration(
                main={"size": CAMERA_RESOLUTION, "format": "RGB888"}
            )
            picam2.configure(config)
            picam2.start()
            time.sleep(1.0)
            print("Using Picamera2 backend.")
            return "picamera2", picam2
        except Exception as exc:
            print(f"Picamera2 unavailable, falling back to OpenCV: {exc}")

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if cap.isOpened():
        print("Using OpenCV backend.")
        return "opencv", cap
    return None, None


def _read_frame(backend, camera):
    if backend == "picamera2":
        rgb = camera.capture_array("main")
        if rgb is None:
            return False, None
        return True, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return camera.read()


def main():
    try:
        from ultralytics import YOLO
    except Exception as exc:
        print(f"Failed to import ultralytics: {exc}")
        print("Install dependency with: .venv/bin/pip install ultralytics")
        return

    print("Loading models...")
    print(f"  stairs model:  {STAIRS_MODEL_PATH}")
    print(f"  general model: {GENERAL_MODEL_PATH}")
    stairs_model = YOLO(STAIRS_MODEL_PATH)
    general_model = YOLO(GENERAL_MODEL_PATH)

    print(f"Opening camera index {CAMERA_INDEX}...")
    backend, camera = _open_camera()
    if not camera:
        print("Error: Could not open camera.")
        return

    gui_enabled = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if gui_enabled:
        print("GUI preview enabled. Press 'q' in preview window to quit.")
    else:
        print("Headless session detected: running without GUI preview.")
        print("Press Ctrl+C to stop.")

    print("Running live inference. Press 'q' to quit.")
    last_log = 0.0
    last_warn = 0.0
    frame_count = 0
    fps_t0 = time.monotonic()
    consecutive_read_failures = 0
    max_read_failures = 50
    frame_idx = 0
    cached_stairs = []
    cached_general = []

    try:
        while True:
            ok, frame = _read_frame(backend, camera)
            if not ok:
                consecutive_read_failures += 1
                now = time.monotonic()
                if now - last_warn >= 1.0:
                    print(
                        f"Warning: Failed to read frame "
                        f"({consecutive_read_failures} consecutive failures)."
                    )
                    last_warn = now
                if consecutive_read_failures >= max_read_failures:
                    print(
                        "Error: Camera feed is not returning frames. "
                        "Check camera connection/index and try again."
                    )
                    break
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                time.sleep(0.02)
                continue
            consecutive_read_failures = 0
            frame_idx += 1

            if frame_idx % max(1, CAMERA_STAIRS_INFER_EVERY_N) == 0:
                stairs_result = stairs_model.predict(
                    source=frame,
                    conf=STAIRS_CONFIDENCE_THRESHOLD,
                    imgsz=CAMERA_IMAGE_SIZE,
                    verbose=False,
                )[0]
                cached_stairs = _parse_detections(stairs_result, "stairs_model")
            if frame_idx % max(1, CAMERA_GENERAL_INFER_EVERY_N) == 0:
                general_result = general_model.predict(
                    source=frame,
                    conf=GENERAL_CONFIDENCE_THRESHOLD,
                    imgsz=CAMERA_IMAGE_SIZE,
                    verbose=False,
                )[0]
                cached_general = _parse_detections(general_result, "general_model")

            detections = cached_stairs + cached_general
            _draw_detections(frame, detections)

            frame_count += 1
            elapsed = max(0.001, time.monotonic() - fps_t0)
            fps = frame_count / elapsed
            cv2.putText(
                frame,
                f"FPS: {fps:.1f} | detections: {len(detections)}",
                (10, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )

            if gui_enabled:
                cv2.imshow("GenStep Dual-Model Camera Test", frame)
            now = time.monotonic()
            if now - last_log >= 1.0:
                labels = [f'{d["label"]}:{d["confidence"]:.2f}' for d in detections]
                print(f"[frame] fps={fps:.1f} detections={len(detections)} {labels}")
                last_log = now

            if gui_enabled and cv2.waitKey(1) & 0xFF == ord("q"):
                break
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        if backend == "picamera2":
            try:
                camera.stop()
            except Exception:
                pass
        elif camera:
            camera.release()
        if gui_enabled:
            cv2.destroyAllWindows()
        print("Camera test stopped.")


if __name__ == "__main__":
    main()
