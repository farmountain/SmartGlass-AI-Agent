#!/usr/bin/env python3
"""Measure API network latency to Azure OpenAI."""
import time
import sys
import os
from statistics import mean, stdev

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def measure_api_latency(iterations=100):
    """Measure Azure OpenAI API request latency."""
    try:
        from openai import AzureOpenAI
    except ImportError:
        print("ERROR: openai package not installed. Install with: pip install openai")
        return 1
    
    # Get credentials from environment
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")
    
    if not api_key or not endpoint:
        print("ERROR: Azure OpenAI credentials not configured")
        print("Set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT environment variables")
        return 1
    
    client = AzureOpenAI(
        api_key=api_key,
        api_version="2024-02-01",
        azure_endpoint=endpoint
    )
    
    latencies = []
    errors = 0
    total_tokens = 0
    
    print(f"Measuring API latency to Azure OpenAI ({iterations} requests)...")
    print(f"Endpoint: {endpoint}")
    print(f"Deployment: {deployment}\n")
    
    for i in range(iterations):
        try:
            start = time.perf_counter()
            response = client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say hello"}
                ],
                max_tokens=10,
                temperature=0
            )
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
            
            if response.usage:
                total_tokens += response.usage.total_tokens
            
            if (i + 1) % 10 == 0:
                print(f"[{i+1}/{iterations}] Latency: {latency:.0f}ms")
        
        except Exception as e:
            errors += 1
            print(f"[{i+1}/{iterations}] ERROR: {e}")
            if errors > 10:
                print(f"\nToo many errors ({errors}), aborting test")
                return 1
    
    if not latencies:
        print("ERROR: No successful API requests")
        return 1
    
    # Calculate statistics
    latencies_sorted = sorted(latencies)
    n = len(latencies_sorted)
    
    stats = {
        "mean": mean(latencies),
        "stdev": stdev(latencies) if n > 1 else 0,
        "min": min(latencies),
        "max": max(latencies),
        "p50": latencies_sorted[int(n * 0.5)],
        "p95": latencies_sorted[int(n * 0.95)],
        "p99": latencies_sorted[int(n * 0.99)],
    }
    
    error_rate = (errors / iterations) * 100
    avg_tokens = total_tokens / len(latencies)
    throughput = (total_tokens / sum(latencies)) * 1000  # tokens/second
    
    print(f"\n{'='*60}")
    print(f"Network Latency Benchmark Results")
    print(f"{'='*60}")
    print(f"Requests: {len(latencies)}/{iterations} successful")
    print(f"Errors: {errors} ({error_rate:.2f}%)")
    print(f"\nLatency Statistics:")
    print(f"  Mean: {stats['mean']:.2f}ms")
    print(f"  Stdev: {stats['stdev']:.2f}ms")
    print(f"  Min: {stats['min']:.2f}ms")
    print(f"  Max: {stats['max']:.2f}ms")
    print(f"  P50: {stats['p50']:.2f}ms")
    print(f"  P95: {stats['p95']:.2f}ms")
    print(f"  P99: {stats['p99']:.2f}ms")
    print(f"\nThroughput:")
    print(f"  Total tokens: {total_tokens}")
    print(f"  Avg tokens/request: {avg_tokens:.1f}")
    print(f"  Throughput: {throughput:.1f} tokens/s")
    print(f"{'='*60}")
    
    # Check success criteria
    success = True
    if stats['p95'] >= 500:
        print(f"❌ P95 latency {stats['p95']:.2f}ms >= 500ms target")
        success = False
    else:
        print(f"✅ P95 latency {stats['p95']:.2f}ms < 500ms target")
    
    if error_rate >= 1:
        print(f"❌ Error rate {error_rate:.2f}% >= 1% target")
        success = False
    else:
        print(f"✅ Error rate {error_rate:.2f}% < 1% target")
    
    return 0 if success else 1

if __name__ == "__main__":
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    exit_code = measure_api_latency(iterations)
    sys.exit(exit_code)
