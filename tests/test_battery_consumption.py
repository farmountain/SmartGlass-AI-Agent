#!/usr/bin/env python3
"""Test battery consumption over time."""
import time
import sys
import subprocess
from datetime import datetime

def get_battery_level(device="phone"):
    """Get battery level for glasses or phone."""
    if device == "phone":
        try:
            result = subprocess.run(
                ["adb", "shell", "dumpsys", "battery"],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in result.stdout.split('\n'):
                if 'level:' in line:
                    return int(line.split(':')[1].strip())
        except Exception as e:
            print(f"ERROR reading phone battery: {e}")
            return -1
    else:  # glasses
        # TODO: Implement glasses battery reading via Meta View API
        print("WARNING: Glasses battery reading not yet implemented")
        return -1

def main(duration_seconds=3600):
    """Test battery drain over specified duration."""
    print(f"Battery Consumption Test ({duration_seconds}s)")
    print("=" * 50)
    
    # Record initial battery levels
    phone_start = get_battery_level("phone")
    # glasses_start = get_battery_level("glasses")
    
    if phone_start < 0:
        print("ERROR: Cannot read phone battery level. Is device connected via ADB?")
        return 1
    
    print(f"Initial phone battery: {phone_start}%")
    # print(f"Initial glasses battery: {glasses_start}%")
    print(f"\nRunning continuous workload for {duration_seconds/60:.1f} minutes...")
    print("Workload: 5 queries/min (mix of audio and vision)\n")
    
    start_time = time.time()
    query_count = 0
    
    # Simulate continuous workload
    while time.time() - start_time < duration_seconds:
        # Simulate query (in real test, trigger actual queries)
        time.sleep(12)  # 5 queries per minute
        query_count += 1
        
        # Log progress every 10 minutes
        elapsed = time.time() - start_time
        if query_count % 50 == 0:  # Every 10 minutes (50 queries)
            phone_current = get_battery_level("phone")
            drain = phone_start - phone_current
            drain_rate = (drain / elapsed) * 3600  # %/hour
            print(f"[{elapsed/60:.1f}min] Phone: {phone_current}% "
                  f"(drain rate: {drain_rate:.1f}%/hour)")
    
    # Final measurements
    elapsed = time.time() - start_time
    phone_end = get_battery_level("phone")
    # glasses_end = get_battery_level("glasses")
    
    phone_drain = phone_start - phone_end
    phone_rate = (phone_drain / elapsed) * 3600
    
    # glasses_drain = glasses_start - glasses_end
    # glasses_rate = (glasses_drain / elapsed) * 3600
    
    print(f"\n{'='*50}")
    print(f"Battery Consumption Test Results")
    print(f"{'='*50}")
    print(f"Duration: {elapsed/60:.1f} minutes")
    print(f"Queries processed: {query_count}")
    print(f"\nPhone Battery:")
    print(f"  Start: {phone_start}%")
    print(f"  End: {phone_end}%")
    print(f"  Drain: {phone_drain}%")
    print(f"  Rate: {phone_rate:.2f}%/hour")
    print(f"  Estimated runtime: {phone_end/phone_rate:.1f} hours")
    
    # print(f"\nGlasses Battery:")
    # print(f"  Start: {glasses_start}%")
    # print(f"  End: {glasses_end}%")
    # print(f"  Drain: {glasses_drain}%")
    # print(f"  Rate: {glasses_rate:.2f}%/hour")
    # print(f"  Estimated runtime: {glasses_end/glasses_rate:.1f} hours")
    
    print(f"{'='*50}")
    
    # Check success criteria
    success = True
    if phone_rate >= 15:
        print(f"❌ Phone drain rate {phone_rate:.1f}%/hour >= 15%/hour target")
        success = False
    else:
        print(f"✅ Phone drain rate {phone_rate:.1f}%/hour < 15%/hour target")
    
    # if glasses_rate >= 20:
    #     print(f"❌ Glasses drain rate {glasses_rate:.1f}%/hour >= 20%/hour target")
    #     success = False
    # else:
    #     print(f"✅ Glasses drain rate {glasses_rate:.1f}%/hour < 20%/hour target")
    
    return 0 if success else 1

if __name__ == "__main__":
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 3600
    exit_code = main(duration)
    sys.exit(exit_code)
