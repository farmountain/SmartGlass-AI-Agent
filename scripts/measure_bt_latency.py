#!/usr/bin/env python3
"""Measure Bluetooth audio round-trip latency."""
import time
import sys
from statistics import mean, stdev

try:
    import pyaudio
    import numpy as np
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("WARNING: pyaudio not installed. Install with: pip install pyaudio")

def measure_latency_once():
    """Send audio beep, measure time until echo received."""
    if not PYAUDIO_AVAILABLE:
        print("ERROR: pyaudio required for latency measurement")
        return -1
    
    p = pyaudio.PyAudio()
    
    # Generate 1kHz beep (50ms)
    sample_rate = 16000
    duration = 0.05
    frequency = 1000
    samples = np.sin(2 * np.pi * frequency * np.linspace(0, duration, int(sample_rate * duration)))
    
    # Open stream
    stream = p.open(
        format=pyaudio.paFloat32,
        channels=1,
        rate=sample_rate,
        input=True,
        output=True,
        frames_per_buffer=1024
    )
    
    # Send beep and measure echo
    start = time.perf_counter()
    stream.write(samples.astype(np.float32).tobytes())
    
    # Listen for echo (simple threshold detection)
    while True:
        audio = stream.read(1024, exception_on_overflow=False)
        audio_np = np.frombuffer(audio, dtype=np.float32)
        if np.max(np.abs(audio_np)) > 0.1:  # Echo detected
            latency = (time.perf_counter() - start) * 1000  # ms
            break
        if time.perf_counter() - start > 1.0:  # Timeout
            latency = -1
            break
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    return latency

def main(iterations=10):
    """Run multiple latency measurements."""
    print("Measuring Bluetooth audio latency...")
    latencies = []
    
    for i in range(iterations):
        latency = measure_latency_once()
        if latency > 0:
            latencies.append(latency)
            print(f"[{i+1}/{iterations}] Latency: {latency:.2f}ms")
        else:
            print(f"[{i+1}/{iterations}] TIMEOUT")
        time.sleep(0.5)
    
    if latencies:
        print(f"\n{'='*50}")
        print(f"Bluetooth Latency Statistics:")
        print(f"  Mean: {mean(latencies):.2f}ms")
        print(f"  Stdev: {stdev(latencies):.2f}ms")
        print(f"  Min: {min(latencies):.2f}ms")
        print(f"  Max: {max(latencies):.2f}ms")
        print(f"{'='*50}")
    else:
        print("ERROR: No successful measurements")

if __name__ == "__main__":
    main()
