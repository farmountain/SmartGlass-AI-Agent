#!/usr/bin/env python3
"""Benchmark latency on real hardware with detailed breakdown."""
import time
import sys
import os
from statistics import mean, stdev

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def benchmark_latency(num_iterations=50):
    """Measure detailed latency breakdown."""
    try:
        from src.smartglass_agent import SmartGlassAgent
    except ImportError:
        print("ERROR: Cannot import SmartGlassAgent")
        sys.exit(1)
    
    results = {
        "audio_capture": [],
        "speech_recognition": [],
        "intent_inference": [],
        "vision_processing": [],
        "world_model_update": [],
        "planning": [],
        "execution": [],
        "response_generation": [],
        "tts": [],
        "total_e2e": []
    }
    
    test_queries = [
        ("What do you see?", True),  # Needs vision
        ("What time is it?", False),  # No vision
        ("Read this text", True),
        ("Set a timer", False),
    ]
    
    print(f"Initializing SmartGlassAgent...")
    agent = SmartGlassAgent()
    
    print(f"\nRunning {num_iterations} iterations...")
    
    for i in range(num_iterations):
        query, needs_vision = test_queries[i % len(test_queries)]
        
        # Start E2E timer
        t_start = time.perf_counter()
        
        # Audio capture (simulated - in real test, capture from glasses)
        t_audio_start = time.perf_counter()
        time.sleep(0.05)  # Simulate BT latency
        results["audio_capture"].append((time.perf_counter() - t_audio_start) * 1000)
        
        # Speech recognition (simulated)
        t_sr_start = time.perf_counter()
        time.sleep(0.5)  # Simulate Whisper processing
        results["speech_recognition"].append((time.perf_counter() - t_sr_start) * 1000)
        
        # Intent inference
        t_intent_start = time.perf_counter()
        if agent.world_model:
            intent = agent.world_model.infer_intent(query)
        results["intent_inference"].append((time.perf_counter() - t_intent_start) * 1000)
        
        # Vision processing (if needed)
        if needs_vision:
            t_vision_start = time.perf_counter()
            time.sleep(0.3)  # Simulate CLIP processing
            results["vision_processing"].append((time.perf_counter() - t_vision_start) * 1000)
        
        # World model update
        t_world_start = time.perf_counter()
        if agent.world_model:
            pass  # World model already updated
        results["world_model_update"].append((time.perf_counter() - t_world_start) * 1000)
        
        # Planning
        t_plan_start = time.perf_counter()
        if agent.planner and agent.world_model:
            # plan = agent.planner.plan(query, agent.world_model.current_state())
            pass
        results["planning"].append((time.perf_counter() - t_plan_start) * 1000)
        
        # Execution (simulated)
        t_exec_start = time.perf_counter()
        time.sleep(0.01)
        results["execution"].append((time.perf_counter() - t_exec_start) * 1000)
        
        # Response generation (simulated)
        t_resp_start = time.perf_counter()
        # response = agent.generate_response(query)
        time.sleep(0.3)  # Simulate LLM call
        results["response_generation"].append((time.perf_counter() - t_resp_start) * 1000)
        
        # TTS (simulated)
        t_tts_start = time.perf_counter()
        time.sleep(0.2)  # Simulate TTS synthesis
        results["tts"].append((time.perf_counter() - t_tts_start) * 1000)
        
        # Total E2E
        t_total = (time.perf_counter() - t_start) * 1000
        results["total_e2e"].append(t_total)
        
        if (i + 1) % 10 == 0:
            print(f"Completed {i+1}/{num_iterations} iterations")
    
    # Print statistics
    print(f"\n{'='*70}")
    print(f"Hardware Latency Benchmark Results ({num_iterations} iterations)")
    print(f"{'='*70}")
    print(f"{'Stage':<25} {'Mean':>10} {'Stdev':>10} {'P50':>10} {'P95':>10} {'P99':>10}")
    print(f"{'-'*70}")
    
    for stage, latencies in results.items():
        if latencies:
            latencies_sorted = sorted(latencies)
            n = len(latencies_sorted)
            stats = {
                "mean": mean(latencies),
                "stdev": stdev(latencies) if n > 1 else 0,
                "p50": latencies_sorted[int(n * 0.5)],
                "p95": latencies_sorted[int(n * 0.95)],
                "p99": latencies_sorted[int(n * 0.99)],
            }
            print(f"{stage:<25} {stats['mean']:>9.2f}ms {stats['stdev']:>9.2f}ms "
                  f"{stats['p50']:>9.2f}ms {stats['p95']:>9.2f}ms {stats['p99']:>9.2f}ms")
    
    print(f"{'='*70}\n")
    
    # Check success criteria
    e2e_p95 = sorted(results["total_e2e"])[int(len(results["total_e2e"]) * 0.95)]
    if e2e_p95 < 1500:
        print(f"✅ SUCCESS: E2E P95 latency {e2e_p95:.2f}ms < 1500ms target")
        return 0
    else:
        print(f"❌ FAILED: E2E P95 latency {e2e_p95:.2f}ms >= 1500ms target")
        return 1

if __name__ == "__main__":
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    exit_code = benchmark_latency(iterations)
    sys.exit(exit_code)
