#!/usr/bin/env python3
"""Export the GenStep YOLO models to NCNN for fast ARM/NEON CPU inference.

Run this on the Raspberry Pi (or any box with `ultralytics` + `ncnn` installed),
then commit the generated directories so deploys never have to re-export.

Outputs:
    yolo11n_ncnn_model/        (from yolo11n.pt)
    models/stairs_ncnn_model/  (from models/stairs.pt)

Ultralytics' `YOLO()` loads these directories natively at runtime, so the camera
pipeline's `predict(...)` calls are unchanged.
"""

import os
import sys

REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# Match the imgsz the runtime uses so the exported graph is sized correctly.
EXPORT_IMGSZ = 320

MODELS = [
    ("yolo11n.pt", "general"),
    (os.path.join("models", "stairs.pt"), "stairs"),
]


def main():
    try:
        from ultralytics import YOLO
    except ImportError:
        raise SystemExit(
            "ultralytics is not installed. Run `pip install ultralytics` "
            "(it will pull the `ncnn` exporter on first use)."
        )

    os.chdir(REPO_ROOT)
    for model_path, label in MODELS:
        if not os.path.exists(model_path):
            raise SystemExit(f"Missing {label} model weights: {model_path}")
        print(f"[export] {label}: {model_path} -> NCNN (imgsz={EXPORT_IMGSZ})")
        YOLO(model_path).export(format="ncnn", imgsz=EXPORT_IMGSZ)

    print(
        "\nDone. Generated:\n"
        "  yolo11n_ncnn_model/\n"
        "  models/stairs_ncnn_model/\n"
        "Commit these directories so deploys don't need to re-export."
    )


if __name__ == "__main__":
    main()
