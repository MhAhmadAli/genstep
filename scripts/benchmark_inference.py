#!/usr/bin/env python3
"""Benchmark dual-model YOLO inference for the GenStep camera pipeline.

Run this on the Raspberry Pi with the real models so the numbers reflect
production. It reuses the same `AIObjectDetector` load/predict path the live
system uses, so PyTorch vs NCNN comparisons are apples-to-apples.

Examples
--------
PyTorch baseline against a real still image (repeatable):
    python3 scripts/benchmark_inference.py --backend pytorch --no-camera \
        --image samples/scene.jpg --imgsz 320 --frames 200

NCNN end-to-end against the live Picamera2 feed:
    python3 scripts/benchmark_inference.py --backend ncnn --with-camera \
        --imgsz 320 --frames 200
"""

import argparse
import os
import statistics
import sys
import time

import cv2

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, SRC_DIR)

import config  # noqa: E402
from sensors.camera import AIObjectDetector  # noqa: E402

try:
    import psutil
except ImportError:  # pragma: no cover - psutil is a hard dependency for this script
    psutil = None


class _StillCapture:
    """Feeds a single real image through the detector's capture seam.

    Used for `--no-camera` runs so latency is measured against an identical
    frame every iteration (removes capture jitter from the numbers).
    """

    def __init__(self, image):
        self._image = image

    def isOpened(self):
        return True

    def read(self):
        return True, self._image

    def release(self):
        pass


def _percentile(samples, pct):
    if not samples:
        return 0.0
    ordered = sorted(samples)
    rank = max(0, min(len(ordered) - 1, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[rank]


def _summarize(name, samples_ms):
    if not samples_ms:
        print(f"  {name}: no samples")
        return
    print(
        f"  {name}: "
        f"p50={_percentile(samples_ms, 50):.1f}ms  "
        f"p95={_percentile(samples_ms, 95):.1f}ms  "
        f"mean={statistics.fmean(samples_ms):.1f}ms  "
        f"n={len(samples_ms)}"
    )


def _build_detector(args):
    capture = None
    if args.no_camera:
        if not args.image:
            raise SystemExit("--no-camera requires --image pointing to a real photo")
        image = cv2.imread(args.image)
        if image is None:
            raise SystemExit(f"Could not read image: {args.image}")
        capture = _StillCapture(image)

    return AIObjectDetector(
        camera_index=config.CAMERA_INDEX,
        enabled=True,
        backend=args.backend,
        stairs_model_path=config.STAIRS_MODEL_PATH,
        general_model_path=config.GENERAL_MODEL_PATH,
        stairs_model_ncnn_path=config.STAIRS_MODEL_NCNN_PATH,
        general_model_ncnn_path=config.GENERAL_MODEL_NCNN_PATH,
        stairs_conf=config.STAIRS_CONFIDENCE_THRESHOLD,
        general_conf=config.GENERAL_CONFIDENCE_THRESHOLD,
        hazard_classes=config.GENERAL_HAZARD_CLASSES,
        use_picamera2=config.CAMERA_USE_PICAMERA2 and args.with_camera,
        camera_resolution=config.CAMERA_RESOLUTION,
        frame_interval_seconds=0.0,
        image_size=args.imgsz,
        infer_threads=config.CAMERA_INFER_THREADS,
        synchronous=True,
        capture=capture,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=["pytorch", "ncnn"], default="pytorch")
    parser.add_argument("--imgsz", type=int, default=320)
    parser.add_argument("--frames", type=int, default=200)
    parser.add_argument("--image", default=None, help="Real image path for --no-camera runs")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--no-camera", action="store_true", help="Run on a fixed still image")
    source.add_argument("--with-camera", action="store_true", help="Run on the live camera feed")
    args = parser.parse_args()

    if not args.no_camera and not args.with_camera:
        args.with_camera = True

    detector = _build_detector(args)
    if not detector.enabled:
        raise SystemExit(f"Detector failed to initialize: {detector.last_error}")

    proc = psutil.Process() if psutil else None
    if proc:
        proc.cpu_percent(None)  # prime the CPU% sampler

    stairs_ms = []
    general_ms = []
    end_to_end_ms = []

    print(
        f"Benchmark: backend={args.backend} imgsz={args.imgsz} frames={args.frames} "
        f"source={'still-image' if args.no_camera else 'live-camera'}"
    )
    print("Warming up (5 frames)...")
    for _ in range(5):
        detector.analyze_frame()

    for i in range(args.frames):
        ret, frame = detector._read_frame()
        if not ret:
            print(f"[warn] frame {i} capture failed; skipping")
            continue

        t0 = time.perf_counter()
        detector._predict(detector.stairs_model, frame, detector.stairs_conf, "stairs_model")
        t1 = time.perf_counter()
        detector._predict(detector.general_model, frame, detector.general_conf, "general_model")
        t2 = time.perf_counter()

        stairs_ms.append((t1 - t0) * 1000.0)
        general_ms.append((t2 - t1) * 1000.0)
        end_to_end_ms.append((t2 - t0) * 1000.0)

    total_s = sum(end_to_end_ms) / 1000.0
    fps = (len(end_to_end_ms) / total_s) if total_s > 0 else 0.0

    print("\nResults")
    _summarize("stairs model", stairs_ms)
    _summarize("general model", general_ms)
    _summarize("end-to-end (both)", end_to_end_ms)
    print(f"  throughput: {fps:.2f} FPS (both models per frame)")
    if proc:
        print(f"  CPU: {proc.cpu_percent(None):.0f}%  RSS: {proc.memory_info().rss / 1e6:.0f} MB")

    detector.close()


if __name__ == "__main__":
    main()
