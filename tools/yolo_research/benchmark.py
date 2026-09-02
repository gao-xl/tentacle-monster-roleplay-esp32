"""
Latency, FPS & Jitter Benchmark Suite for YOLO-Pose 26
Measures real inference throughput on AMD DirectML / CUDA / CPU.
"""

import time
import numpy as np
import onnxruntime as ort
import argparse

def run_benchmark(onnx_path: str, rounds: int = 200, imgsz: int = 640):
    print(f"⏱️ Benchmarking ONNX Inference Engine: {onnx_path}")

    # Prioritize DirectML on Windows, then CUDA, then CPU
    providers = ['DmlExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']
    available = [p for p in providers if p in ort.get_available_providers()]
    print(f"Active Hardware Providers: {available}")

    session = ort.InferenceSession(onnx_path, providers=available)
    input_name = session.get_inputs()[0].name
    input_shape = [1, 3, imgsz, imgsz]
    dummy_input = np.random.randn(*input_shape).astype(np.float16 if "fp16" in onnx_path.lower() else np.float32)

    # Warmup
    for _ in range(20):
        _ = session.run(None, {input_name: dummy_input})

    # Benchmark Loop
    latencies = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        _ = session.run(None, {input_name: dummy_input})
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000)

    avg_latency = np.mean(latencies)
    p95_latency = np.percentile(latencies, 95)
    fps = 1000.0 / avg_latency

    print("==================================================")
    print(f"🔥 Benchmark Results ({rounds} frames):")
    print(f"  • Average Latency: {avg_latency:.2f} ms")
    print(f"  • 95th Percentile: {p95_latency:.2f} ms")
    print(f"  • Throughput:       {fps:.1f} FPS")
    print("==================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="models/yolo11n-pose26.onnx")
    args = parser.parse_args()

    run_benchmark(args.model)
