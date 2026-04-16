import os
import sys
import time

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import (
    CAMERA_IMAGE_SIZE,
    CAMERA_INDEX,
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
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    print("Running live inference. Press 'q' to quit.")
    last_log = 0.0
    frame_count = 0
    fps_t0 = time.monotonic()

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Warning: Failed to read frame.")
                continue

            stairs_result = stairs_model.predict(
                source=frame,
                conf=STAIRS_CONFIDENCE_THRESHOLD,
                imgsz=CAMERA_IMAGE_SIZE,
                verbose=False,
            )[0]
            general_result = general_model.predict(
                source=frame,
                conf=GENERAL_CONFIDENCE_THRESHOLD,
                imgsz=CAMERA_IMAGE_SIZE,
                verbose=False,
            )[0]

            detections = []
            detections.extend(_parse_detections(stairs_result, "stairs_model"))
            detections.extend(_parse_detections(general_result, "general_model"))
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

            cv2.imshow("GenStep Dual-Model Camera Test", frame)
            now = time.monotonic()
            if now - last_log >= 1.0:
                labels = [f'{d["label"]}:{d["confidence"]:.2f}' for d in detections]
                print(f"[frame] detections={len(detections)} {labels}")
                last_log = now

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Camera test stopped.")


if __name__ == "__main__":
    main()
