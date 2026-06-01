# Inference Benchmarks

Throughput and latency numbers for the GenStep dual-model camera pipeline on the
Raspberry Pi 4 (CPU only). These are produced by
[`scripts/benchmark_inference.py`](../scripts/benchmark_inference.py) and must be
captured on the actual Pi with the real `yolo11n.pt` and `models/stairs.pt`
models. Do not estimate these values; run the script and paste the output.

## How to capture

```bash
# Baseline (PyTorch), repeatable still image:
python3 scripts/benchmark_inference.py --backend pytorch --no-camera \
    --image samples/scene.jpg --imgsz 320 --frames 200

# NCNN, same image:
python3 scripts/benchmark_inference.py --backend ncnn --no-camera \
    --image samples/scene.jpg --imgsz 320 --frames 200

# End-to-end with the live camera:
python3 scripts/benchmark_inference.py --backend ncnn --with-camera \
    --imgsz 320 --frames 200
```

Use the same `--image` for PyTorch vs NCNN so the comparison is apples-to-apples.

## Results (fill in on the Pi)

Hardware: Raspberry Pi 4 (___ GB), Raspberry Pi OS ___, governor: ___ (default / performance)

| Config | imgsz | stairs p50 / p95 (ms) | general p50 / p95 (ms) | end-to-end p50 (ms) | FPS | CPU % | RSS (MB) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PyTorch, still image | 320 | / | / | | | | |
| NCNN, still image | 320 | / | / | | | | |
| NCNN + perf governor, still image | 320 | / | / | | | | |
| NCNN, live camera | 320 | / | / | | | | |

### Sonar gating (general model idle in open space)

Measured separately because gating only changes runtime cost when no obstacle is
within `CAMERA_GENERAL_GATE_DISTANCE_M`. Record observed loop cadence / CPU with
the general model gated OFF vs ON during a live walk.

| Scenario | general model | observed FPS | CPU % | notes |
| --- | --- | --- | --- | --- |
| Open space (no obstacle < gate) | gated OFF | | | stairs only |
| Obstacle within gate | gated ON | | | both models |

### Async worker (main-loop responsiveness)

Confirms the main loop iterates at ~10 Hz (0.1s sleep) regardless of inference
cost once capture+inference run on the background thread.

| Build | main-loop iterations/sec | inference FPS (worker) | notes |
| --- | --- | --- | --- |
| Synchronous (pre-async) | | | inference blocks loop |
| Async worker | | | loop decoupled |

## Observations

- _Speedup PyTorch -> NCNN:_ ___x
- _Per-frame latency change:_ ___
- _Notes:_ ___
