#!/usr/bin/env python3
"""Comprehensive E2E test suite for hardware validation."""
import time
import sys
import os
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Test query categories
VISUAL_QA_QUERIES = [
    "What do you see?",
    "Describe this scene",
    "How many people are in front of me?",
    "What colors are visible?",
    "Is this indoors or outdoors?",
]

OCR_TRANSLATION_QUERIES = [
    "Read this menu",
    "Translate this sign to Spanish",
    "What does this label say?",
    "Read the text on this document",
    "Translate this to French",
]

NAVIGATION_QUERIES = [
    "Where is the nearest restroom?",
    "Guide me to the exit",
    "How far to the parking lot?",
    "Find the nearest coffee shop",
    "Navigate to the entrance",
]

INFO_LOOKUP_QUERIES = [
    "What's the weather today?",
    "When is my next meeting?",
    "Define serendipity",
    "What's the capital of France?",
    "Convert 50 USD to EUR",
]

GENERAL_ASSISTANCE_QUERIES = [
    "Set a timer for 5 minutes",
    "Remind me to call John at 3pm",
    "What's 15% tip on $80?",
    "Add milk to my shopping list",
    "What day is it today?",
]

ALL_QUERIES = (
    VISUAL_QA_QUERIES +
    OCR_TRANSLATION_QUERIES +
    NAVIGATION_QUERIES +
    INFO_LOOKUP_QUERIES +
    GENERAL_ASSISTANCE_QUERIES
)

def run_e2e_test(agent, query: str, needs_vision: bool = False) -> Dict[str, Any]:
    """Run single E2E test query."""
    start = time.perf_counter()
    
    try:
        # Simulate multimodal query processing
        result = agent.process_multimodal_query(
            text_query=query,
            image_input=None if not needs_vision else "mock_image.jpg",
        )
        
        latency = (time.perf_counter() - start) * 1000
        
        return {
            "query": query,
            "success": True,
            "latency_ms": latency,
            "response": result.get("response", ""),
            "actions": result.get("actions", []),
        }
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return {
            "query": query,
            "success": False,
            "latency_ms": latency,
            "error": str(e),
        }

def main(num_queries=100):
    """Run comprehensive E2E test suite."""
    try:
        from src.smartglass_agent import SmartGlassAgent
    except ImportError:
        print("ERROR: Cannot import SmartGlassAgent")
        return 1
    
    print(f"Initializing SmartGlassAgent...")
    agent = SmartGlassAgent()
    
    print(f"\nRunning {num_queries} E2E test queries...")
    print("=" * 60)
    
    results: List[Dict[str, Any]] = []
    successes = 0
    failures = 0
    latencies = []
    
    # Run test queries
    for i in range(num_queries):
        query = ALL_QUERIES[i % len(ALL_QUERIES)]
        needs_vision = query in VISUAL_QA_QUERIES or query in OCR_TRANSLATION_QUERIES
        
        result = run_e2e_test(agent, query, needs_vision)
        results.append(result)
        
        if result["success"]:
            successes += 1
            latencies.append(result["latency_ms"])
            status = "✅"
        else:
            failures += 1
            status = "❌"
        
        if (i + 1) % 10 == 0:
            print(f"[{i+1}/{num_queries}] {status} Query: '{query[:40]}...'")
    
    # Calculate statistics
    success_rate = (successes / num_queries) * 100
    
    if latencies:
        latencies_sorted = sorted(latencies)
        n = len(latencies_sorted)
        mean_latency = sum(latencies) / len(latencies)
        p95_latency = latencies_sorted[int(n * 0.95)]
        p99_latency = latencies_sorted[int(n * 0.99)]
    else:
        mean_latency = p95_latency = p99_latency = 0
    
    # Print results
    print(f"\n{'='*60}")
    print(f"E2E Hardware Test Results")
    print(f"{'='*60}")
    print(f"Total queries: {num_queries}")
    print(f"Successes: {successes}")
    print(f"Failures: {failures}")
    print(f"Success rate: {success_rate:.1f}%")
    print(f"\nLatency Statistics:")
    print(f"  Mean: {mean_latency:.2f}ms")
    print(f"  P95: {p95_latency:.2f}ms")
    print(f"  P99: {p99_latency:.2f}ms")
    print(f"{'='*60}")
    
    # Check success criteria
    all_pass = True
    
    if success_rate < 90:
        print(f"❌ Success rate {success_rate:.1f}% < 90% target")
        all_pass = False
    else:
        print(f"✅ Success rate {success_rate:.1f}% >= 90% target")
    
    if mean_latency >= 1500:
        print(f"❌ Mean latency {mean_latency:.2f}ms >= 1500ms target")
        all_pass = False
    else:
        print(f"✅ Mean latency {mean_latency:.2f}ms < 1500ms target")
    
    if p95_latency >= 3000:
        print(f"❌ P95 latency {p95_latency:.2f}ms >= 3000ms target")
        all_pass = False
    else:
        print(f"✅ P95 latency {p95_latency:.2f}ms < 3000ms target")
    
    return 0 if all_pass else 1

if __name__ == "__main__":
    num_queries = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    exit_code = main(num_queries)
    sys.exit(exit_code)
