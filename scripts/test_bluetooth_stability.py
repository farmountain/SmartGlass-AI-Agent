#!/usr/bin/env python3
"""Test Bluetooth connection stability over time."""
import time
import subprocess
import sys
from datetime import datetime

def check_bluetooth_connected(device_name="Ray-Ban"):
    """Check if device is connected via ADB."""
    try:
        result = subprocess.run(
            ["adb", "shell", "dumpsys", "bluetooth_manager"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return device_name.lower() in result.stdout.lower()
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main(duration_seconds=3600):
    """Run stability test for specified duration."""
    start = time.time()
    checks = 0
    failures = 0
    
    print(f"Starting Bluetooth stability test for {duration_seconds}s...")
    print(f"Start time: {datetime.now()}")
    
    while time.time() - start < duration_seconds:
        connected = check_bluetooth_connected()
        checks += 1
        
        if not connected:
            failures += 1
            print(f"[{checks}] DISCONNECTED at {datetime.now()}")
        else:
            if checks % 60 == 0:  # Log every 60 checks (~1 min)
                print(f"[{checks}] Connected OK ({failures} failures so far)")
        
        time.sleep(1)
    
    elapsed = time.time() - start
    uptime_pct = 100 * (1 - failures / checks) if checks > 0 else 0
    
    print(f"\n{'='*50}")
    print(f"Test complete!")
    print(f"Duration: {elapsed:.1f}s")
    print(f"Checks: {checks}")
    print(f"Failures: {failures}")
    print(f"Uptime: {uptime_pct:.2f}%")
    print(f"{'='*50}")
    
    return failures == 0

if __name__ == "__main__":
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 3600
    success = main(duration)
    sys.exit(0 if success else 1)
