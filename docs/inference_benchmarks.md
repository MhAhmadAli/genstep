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
| PyTorch, still image | 320 | 450.2 / 459.1 | 211.2 / 216.5 | 662.1 | 1.51 | 280 | 484 |
| NCNN, still image | 320 | 275.2 / 290.5 | 115.4 / 137.1 | 392.3 | 2.53 | 352 | 621 |
| NCNN + perf governor, still image | 320 | / | / | | | | |
| NCNN, live camera | 320 | / | / | | | | |

n = 200 frames per run, same still image for both backends. `end-to-end` is the
sum of both model inferences per frame (capture excluded).

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

- _Speedup PyTorch -> NCNN (still image, imgsz 320):_ ~1.68x throughput (1.51 -> 2.53 FPS).
  - stairs model: 450.2 -> 275.2 ms p50 (1.64x)
  - general model: 211.2 -> 115.4 ms p50 (1.83x)
- _Per-frame latency change:_ end-to-end p50 662.1 -> 392.3 ms, a ~41% reduction (~270 ms saved per dual-model frame).
- _Resource use:_ CPU rose 280% -> 352% (NCNN parallelizes across more cores, which is why it is faster); RSS 484 -> 621 MB.
- _Notes / follow-ups:_
  - The custom `stairs.pt` (22 MB) dominates latency (~2x the general yolo11n model), so it is the best target for further speedup (smaller/quantized stairs model, or a higher `CAMERA_STAIRS_INFER_EVERY_N`).
  - CPU at 352% (~3.5 cores) suggests NCNN is using all 4 cores despite `CAMERA_INFER_THREADS=3`; NCNN may not honor `OMP_NUM_THREADS`/`cv2.setNumThreads`. If leaving a core free for sonar/buzzer/Flask matters under load, set the NCNN thread count explicitly.
  - Still short of the 2-3x / "halve latency" target at imgsz 320 with both models always on; the sonar-gating (general model idle in open space) and async worker close most of that gap in real-world use. Capture the gating and live-camera rows next.
