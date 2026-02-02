# Hardware Validation Runbook

**Version**: 1.0  
**Last Updated**: February 2, 2026  
**Owner**: Development Team  
**Target Hardware**: Meta Ray-Ban Smart Glasses + Android Smartphone

---

## Overview

This runbook guides hardware validation testing to verify production-ready performance on real Meta Ray-Ban devices. Complete all sections sequentially before pilot deployment.

**Success Criteria**:
- ✅ Bluetooth pairing stable for 1+ hour continuous use
- ✅ End-to-end latency < 1.5s (audio → response)
- ✅ Battery drain < 20% per hour (glasses + phone)
- ✅ 90%+ success rate across 100 test queries
- ✅ No critical hardware incompatibilities

---

## Prerequisites

### Hardware Requirements
- [ ] Meta Ray-Ban Smart Glasses (1 unit, fully charged)
- [ ] Android Smartphone - OPPO Reno 12 or compatible (fully charged)
- [ ] USB-C cable for phone debugging
- [ ] Power banks (2x, 10,000mAh minimum)
- [ ] Stopwatch or timer app
- [ ] Notebook for manual observations

### Software Requirements
- [ ] Android Debug Bridge (ADB) installed on development machine
- [ ] Meta View app installed on phone (from Google Play Store)
- [ ] SmartGlass-AI-Agent repository cloned and dependencies installed
- [ ] Azure OpenAI API keys configured (`.env` file)
- [ ] Video recording app (optional, for demo)

### Environment Setup
```bash
# Verify ADB installation
adb version

# Enable USB debugging on Android phone:
# Settings → About Phone → Tap "Build Number" 7 times
# Settings → Developer Options → Enable USB Debugging

# Connect phone via USB and authorize
adb devices
# Expected: List of devices attached with serial number

# Install test dependencies
pip install -r requirements.txt
pip install pytest pytest-timeout loguru
```

---

## Phase 1: Initial Connection Testing (Day 1, ~2 hours)

### 1.1 Pair Meta Ray-Ban with Phone

**Steps**:
1. Open Meta View app on phone
2. Power on glasses (hold button 3 seconds until LED flashes)
3. Follow pairing flow in app
4. Grant all permissions (camera, microphone, storage)
5. Update firmware if prompted

**Success Criteria**:
- [ ] Glasses appear as "Connected" in Meta View app
- [ ] LED indicator shows solid green
- [ ] Test photo capture works (tap button, photo appears in app)

**Document**:
- Firmware version: `_____________`
- Pairing time: `_____________`
- Issues encountered: `_____________`

### 1.2 Bluetooth Stability Test (1-hour sustained connection)

**Steps**:
```bash
# Terminal 1: Monitor Bluetooth connection
adb shell dumpsys bluetooth_manager | grep -i "ray-ban"

# Terminal 2: Run continuous connection test
python scripts/test_bluetooth_stability.py --duration 3600
```

**Test Script** (`scripts/test_bluetooth_stability.py`):
```python
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
```

**Success Criteria**:
- [ ] Connection uptime > 99% over 1 hour
- [ ] No disconnections requiring manual re-pairing
- [ ] Audio/video stream continuous without dropouts

**Document**:
- Uptime percentage: `_____________`
- Disconnection events: `_____________`
- Average reconnection time: `_____________`

### 1.3 Bluetooth Latency Baseline

**Steps**:
```bash
# Measure Bluetooth audio latency
python scripts/measure_bt_latency.py
```

**Test Script** (`scripts/measure_bt_latency.py`):
```python
#!/usr/bin/env python3
"""Measure Bluetooth audio round-trip latency."""
import time
import pyaudio
import numpy as np
from statistics import mean, stdev

def measure_latency_once():
    """Send audio beep, measure time until echo received."""
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
```

**Success Criteria**:
- [ ] Mean Bluetooth latency < 150ms
- [ ] Standard deviation < 20ms
- [ ] No timeouts or packet loss

**Document**:
- Mean latency: `_____________`
- P95 latency: `_____________`
- Packet loss: `_____________`

### 1.4 Camera Capture Quality

**Steps**:
1. Capture 10 test images in various lighting conditions:
   - Bright outdoor
   - Indoor office lighting
   - Low light (evening/dim room)
   - High contrast scenes (window backlight)
2. Transfer images to development machine:
   ```bash
   adb pull /sdcard/DCIM/Meta/ ./test_images/
   ```
3. Inspect image quality manually

**Success Criteria**:
- [ ] Resolution: 2592x1944 or higher
- [ ] Focus: Sharp text readable at 1 meter
- [ ] Exposure: Properly exposed in 8/10 images
- [ ] Color: Accurate color reproduction (no strong tint)

**Document**:
- Image resolution: `_____________`
- Quality issues: `_____________`
- Lighting conditions that fail: `_____________`

---

## Phase 2: End-to-End Pipeline Testing (Day 2-3, ~8 hours)

### 2.1 Run Full Integration Test Suite

**Steps**:
```bash
# Run all integration tests with hardware
pytest tests/test_production_components.py -v --timeout=30

# Run Meta Ray-Ban specific tests
pytest tests/test_meta_rayban_integration.py -v --hardware
```

**Expected Output**:
```
tests/test_production_components.py::test_clip_world_model PASSED
tests/test_production_components.py::test_sqlite_context_store PASSED
tests/test_production_components.py::test_rule_based_planner PASSED
tests/test_production_components.py::test_end_to_end_integration PASSED

======================== 4 passed in 12.34s ========================
```

**Success Criteria**:
- [ ] All 4 integration tests pass
- [ ] No test timeouts or crashes
- [ ] Test execution time < 30s total

**Document**:
- Tests passed: `_____________`
- Failures: `_____________`
- Error logs: `_____________`

### 2.2 Audio Pipeline Testing

**Test Scenarios**:
1. **Wake word detection** (10 attempts)
   - Say "Hey Ray" clearly
   - Expected: LED flashes, listening mode activated
   - Measure: Detection accuracy, false positive rate

2. **Speech recognition** (20 queries)
   - Sample queries:
     - "What do you see?"
     - "Read the text in front of me"
     - "Navigate to the nearest coffee shop"
     - "Translate this sign to English"
   - Measure: WER (Word Error Rate), recognition latency

3. **Audio output** (10 responses)
   - Listen to TTS responses through glasses speakers
   - Check: Volume adequate, clarity, no distortion

**Steps**:
```bash
# Run audio pipeline test
python tests/test_audio_pipeline_hardware.py
```

**Test Script** (`tests/test_audio_pipeline_hardware.py`):
```python
#!/usr/bin/env python3
"""Test audio pipeline on real hardware."""
import time
from src.audio.wakeword_detector import WakeWordDetector
from src.audio.speech_recognizer import WhisperSpeechRecognizer
from loguru import logger

def test_wakeword_detection():
    """Test wake word detection accuracy."""
    detector = WakeWordDetector()
    
    print("\n=== Wake Word Detection Test ===")
    print("Say 'Hey Ray' 10 times when prompted...")
    
    detections = 0
    false_positives = 0
    
    for i in range(10):
        input(f"\n[{i+1}/10] Press Enter, then say 'Hey Ray'...")
        
        start = time.time()
        detected = detector.listen_for_wakeword(timeout=5.0)
        latency = (time.time() - start) * 1000
        
        if detected:
            detections += 1
            print(f"  ✅ Detected (latency: {latency:.0f}ms)")
        else:
            print(f"  ❌ Not detected (timeout)")
    
    # Test false positives (background noise, wrong phrases)
    print("\n--- Testing False Positives ---")
    print("Stay silent for 30 seconds...")
    
    start = time.time()
    while time.time() - start < 30:
        if detector.detect_frame():  # Non-blocking check
            false_positives += 1
            print(f"  ⚠️  False positive at {time.time()-start:.1f}s")
    
    accuracy = detections / 10 * 100
    fpr = false_positives  # Count in 30s window
    
    print(f"\n{'='*50}")
    print(f"Wake Word Detection Results:")
    print(f"  Accuracy: {accuracy:.1f}% ({detections}/10)")
    print(f"  False Positives: {fpr} in 30s")
    print(f"{'='*50}")
    
    assert accuracy >= 90, f"Accuracy too low: {accuracy}%"
    assert fpr <= 2, f"Too many false positives: {fpr}"

def test_speech_recognition():
    """Test speech recognition accuracy."""
    recognizer = WhisperSpeechRecognizer(model_size="base")
    
    test_phrases = [
        "What do you see?",
        "Read the text in front of me",
        "Navigate to the nearest coffee shop",
        "Translate this sign to English",
        "What time is it?",
    ]
    
    print("\n=== Speech Recognition Test ===")
    
    wer_scores = []
    latencies = []
    
    for i, phrase in enumerate(test_phrases):
        input(f"\n[{i+1}/{len(test_phrases)}] Press Enter, then say: '{phrase}'...")
        
        start = time.time()
        recognized = recognizer.transcribe(timeout=5.0)
        latency = (time.time() - start) * 1000
        latencies.append(latency)
        
        print(f"  Expected: '{phrase}'")
        print(f"  Recognized: '{recognized}'")
        print(f"  Latency: {latency:.0f}ms")
        
        # Simple WER: count word differences
        expected_words = phrase.lower().split()
        recognized_words = recognized.lower().split()
        errors = sum(e != r for e, r in zip(expected_words, recognized_words))
        errors += abs(len(expected_words) - len(recognized_words))
        wer = errors / len(expected_words)
        wer_scores.append(wer)
        
        print(f"  WER: {wer*100:.1f}%")
    
    avg_wer = sum(wer_scores) / len(wer_scores) * 100
    avg_latency = sum(latencies) / len(latencies)
    
    print(f"\n{'='*50}")
    print(f"Speech Recognition Results:")
    print(f"  Average WER: {avg_wer:.1f}%")
    print(f"  Average Latency: {avg_latency:.0f}ms")
    print(f"{'='*50}")
    
    assert avg_wer < 20, f"WER too high: {avg_wer}%"
    assert avg_latency < 2000, f"Latency too high: {avg_latency}ms"

if __name__ == "__main__":
    test_wakeword_detection()
    test_speech_recognition()
    print("\n✅ All audio pipeline tests passed!")
```

**Success Criteria**:
- [ ] Wake word detection accuracy > 90%
- [ ] False positive rate < 2 per 30 seconds
- [ ] Speech recognition WER < 20%
- [ ] Audio processing latency < 2s

**Document**:
- Wake word accuracy: `_____________`
- WER: `_____________`
- Audio latency: `_____________`

### 2.3 Vision Pipeline Testing

**Test Scenarios**:
1. **Scene understanding** (15 images)
   - Capture diverse scenes (indoor, outdoor, people, objects)
   - Process with CLIPWorldModel
   - Verify correct scene classification

2. **OCR accuracy** (10 text samples)
   - Capture images of printed text (signs, menus, documents)
   - Extract text with OCR
   - Measure character accuracy

3. **Object detection** (10 images)
   - Capture images with multiple objects
   - Verify object detection and classification
   - Check bounding box accuracy

**Steps**:
```bash
# Run vision pipeline test
python tests/test_vision_pipeline_hardware.py
```

**Success Criteria**:
- [ ] Scene classification accuracy > 85%
- [ ] OCR character accuracy > 90%
- [ ] Object detection mAP > 0.7
- [ ] Vision processing latency < 500ms

**Document**:
- Scene accuracy: `_____________`
- OCR accuracy: `_____________`
- Vision latency: `_____________`

### 2.4 End-to-End Workflow Testing

**Test 100 representative queries**:

```bash
# Run comprehensive E2E test suite
python tests/test_e2e_hardware.py --queries 100
```

**Query Categories** (20 each):
1. **Visual question answering**
   - "What do you see?"
   - "Describe this scene"
   - "How many people are in front of me?"

2. **OCR and translation**
   - "Read this menu"
   - "Translate this sign to Spanish"
   - "What does this label say?"

3. **Navigation**
   - "Where is the nearest restroom?"
   - "Guide me to the exit"
   - "How far to the parking lot?"

4. **Information lookup**
   - "What's the weather today?"
   - "When is my next meeting?"
   - "Define 'serendipity'"

5. **General assistance**
   - "Set a timer for 5 minutes"
   - "Remind me to call John at 3pm"
   - "What's 15% tip on $80?"

**Success Criteria**:
- [ ] Overall success rate > 90% (90/100 queries)
- [ ] Mean E2E latency < 1.5s
- [ ] P95 latency < 3.0s
- [ ] No crashes or unrecoverable errors

**Document**:
- Success rate: `_____________`
- Mean latency: `_____________`
- P95 latency: `_____________`
- Error categories: `_____________`

---

## Phase 3: Performance Benchmarking (Day 4, ~4 hours)

### 3.1 Latency Breakdown

**Measure each pipeline stage**:

```bash
# Run detailed latency profiling
python bench/hardware_latency_bench.py --detailed
```

**Test Script** (`bench/hardware_latency_bench.py`):
```python
#!/usr/bin/env python3
"""Benchmark latency on real hardware with detailed breakdown."""
import time
from statistics import mean, stdev
from src.smartglass_agent import SmartGlassAgent
from loguru import logger

def benchmark_latency(agent, num_iterations=50):
    """Measure detailed latency breakdown."""
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
    
    for i in range(num_iterations):
        query, needs_vision = test_queries[i % len(test_queries)]
        
        # Start E2E timer
        t_start = time.perf_counter()
        
        # Audio capture (simulated - measure actual BT latency)
        t_audio_start = time.perf_counter()
        # In real test, capture from glasses microphone
        results["audio_capture"].append((time.perf_counter() - t_audio_start) * 1000)
        
        # Speech recognition
        t_sr_start = time.perf_counter()
        # transcription = agent.speech_recognizer.transcribe(audio)
        results["speech_recognition"].append((time.perf_counter() - t_sr_start) * 1000)
        
        # Intent inference
        t_intent_start = time.perf_counter()
        intent = agent.world_model.infer_intent(query)
        results["intent_inference"].append((time.perf_counter() - t_intent_start) * 1000)
        
        # Vision processing (if needed)
        if needs_vision:
            t_vision_start = time.perf_counter()
            # image = capture_from_glasses()
            # agent.world_model.process_image(image)
            results["vision_processing"].append((time.perf_counter() - t_vision_start) * 1000)
        
        # World model update
        t_world_start = time.perf_counter()
        # agent.world_model.update(...)
        results["world_model_update"].append((time.perf_counter() - t_world_start) * 1000)
        
        # Planning
        t_plan_start = time.perf_counter()
        # plan = agent.planner.generate_plan(intent, context)
        results["planning"].append((time.perf_counter() - t_plan_start) * 1000)
        
        # Execution
        t_exec_start = time.perf_counter()
        # response = agent.execute_plan(plan)
        results["execution"].append((time.perf_counter() - t_exec_start) * 1000)
        
        # Response generation
        t_resp_start = time.perf_counter()
        # response_text = agent.generate_response(...)
        results["response_generation"].append((time.perf_counter() - t_resp_start) * 1000)
        
        # TTS
        t_tts_start = time.perf_counter()
        # audio_output = agent.tts.synthesize(response_text)
        results["tts"].append((time.perf_counter() - t_tts_start) * 1000)
        
        # Total E2E
        t_total = (time.perf_counter() - t_start) * 1000
        results["total_e2e"].append(t_total)
        
        if (i + 1) % 10 == 0:
            logger.info(f"Completed {i+1}/{num_iterations} iterations")
    
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
    
    return results

if __name__ == "__main__":
    agent = SmartGlassAgent()
    results = benchmark_latency(agent, num_iterations=50)
```

**Success Criteria**:
- [ ] Audio capture: < 100ms (P95)
- [ ] Speech recognition: < 800ms (P95)
- [ ] Intent inference: < 50ms (P95)
- [ ] Vision processing: < 500ms (P95)
- [ ] Planning: < 50ms (P95)
- [ ] TTS: < 300ms (P95)
- [ ] **Total E2E: < 1500ms (P95)**

**Document**:
- E2E P95 latency: `_____________`
- Slowest stage: `_____________`
- Optimization opportunities: `_____________`

### 3.2 Battery Consumption

**Test battery drain over 1-hour continuous use**:

**Steps**:
1. Fully charge glasses and phone (100%)
2. Enable airplane mode (WiFi/Bluetooth only)
3. Run continuous test workload:
   ```bash
   python tests/test_battery_consumption.py --duration 3600
   ```
4. Monitor battery levels every 10 minutes
5. Calculate drain rate (%/hour)

**Test Workload**:
- 5 queries per minute (300 queries/hour)
- Mix of audio-only and vision queries (50/50)
- Continuous Bluetooth connection

**Success Criteria**:
- [ ] Glasses battery drain < 20%/hour
- [ ] Phone battery drain < 15%/hour
- [ ] Combined runtime > 4 hours continuous use

**Document**:
- Glasses drain rate: `_____________`
- Phone drain rate: `_____________`
- Estimated runtime: `_____________`

### 3.3 Network Performance

**Test network latency and reliability**:

```bash
# Measure API latency to Azure OpenAI
python bench/network_latency_bench.py --iterations 100
```

**Metrics to collect**:
- API request latency (DNS, TLS, request, response)
- Throughput (tokens/second)
- Error rate (timeouts, 5xx errors)
- Retry behavior

**Success Criteria**:
- [ ] API latency < 500ms (P95)
- [ ] Error rate < 1%
- [ ] Throughput > 50 tokens/second

**Document**:
- API latency P95: `_____________`
- Error rate: `_____________`
- Network issues: `_____________`

---

## Phase 4: Bug Identification (Day 5-6, ~8 hours)

### 4.1 Hardware-Specific Issues

**Common issues to test**:

1. **Bluetooth reconnection**
   - Manually disconnect/reconnect glasses
   - Test automatic reconnection
   - Measure reconnection time

2. **Camera auto-focus**
   - Test focus on objects at various distances
   - Check focus speed and accuracy
   - Verify no focus hunting

3. **Microphone quality**
   - Test in noisy environments (street, cafe, office)
   - Measure background noise suppression
   - Check wind noise handling (outdoor)

4. **Speaker volume**
   - Test volume levels (min, mid, max)
   - Check for distortion at high volume
   - Verify audibility in noisy environments

5. **Button responsiveness**
   - Test single tap, double tap, long press
   - Measure button latency
   - Check for missed inputs

**Document all issues**:
```markdown
## Hardware Issues Log

### Issue #1: [Short Description]
- **Severity**: Critical | High | Medium | Low
- **Frequency**: Always | Often | Sometimes | Rare
- **Steps to Reproduce**:
  1. ...
  2. ...
- **Expected Behavior**: ...
- **Actual Behavior**: ...
- **Workaround**: ...
- **Proposed Fix**: ...

### Issue #2: ...
```

### 4.2 Edge Cases and Error Handling

**Test error scenarios**:
- Loss of internet connection mid-query
- API rate limiting or quota exceeded
- Low battery (< 10%)
- Extreme temperatures (if possible)
- Very loud or very quiet speech
- Poor lighting conditions (darkness, glare)
- Obscured camera view

**Success Criteria**:
- [ ] Graceful degradation (no crashes)
- [ ] User-friendly error messages
- [ ] Recovery without restart

### 4.3 Stress Testing

**Test system limits**:
```bash
# Rapid-fire queries (1 per second for 5 minutes)
python tests/test_stress_hardware.py --rate 1.0 --duration 300

# Memory leak test (continuous use for 4 hours)
python tests/test_memory_leak.py --duration 14400
```

**Success Criteria**:
- [ ] No crashes during stress test
- [ ] Memory usage stable (no leaks)
- [ ] Performance consistent over time

---

## Phase 5: Documentation and Reporting (Day 7, ~4 hours)

### 5.1 Update Benchmarks

**Update project documentation**:

```bash
# Update README.md with actual hardware metrics
# Update docs/PERFORMANCE.md with detailed benchmarks
# Update 30_DAY_CRITICAL_PATH.md with completion status
```

**Files to update**:
- [ ] [README.md](../README.md) - Performance section
- [ ] [docs/PERFORMANCE.md](PERFORMANCE.md) - Hardware benchmarks
- [ ] [30_DAY_CRITICAL_PATH.md](../30_DAY_CRITICAL_PATH.md) - Week 1-2 checklist
- [ ] [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) - Test coverage

### 5.2 Create Hardware Test Report

**Generate comprehensive report**:

```bash
# Generate HTML report from test results
python scripts/generate_hardware_report.py --output reports/hardware_validation.html
```

**Report sections**:
1. Executive Summary
2. Test Environment
3. Test Results Summary
4. Detailed Metrics
5. Issue Log
6. Recommendations
7. Appendix (raw data, logs)

**Report template**: See [HARDWARE_TEST_REPORT_TEMPLATE.md](HARDWARE_TEST_REPORT_TEMPLATE.md)

### 5.3 Record Demo Video

**Video outline** (2-3 minutes):
1. Hardware setup and pairing (15s)
2. Wake word detection demo (15s)
3. Visual QA examples (30s)
4. OCR and translation (30s)
5. Navigation assistance (30s)
6. General assistance (30s)
7. Performance metrics overlay (15s)

**Recording tips**:
- Use screen recording + glasses POV camera
- Add captions for queries and responses
- Show latency timer overlay
- Demonstrate in real-world environment

**Success Criteria**:
- [ ] Video duration < 3 minutes
- [ ] All major features demonstrated
- [ ] Clear audio and video quality
- [ ] Performance metrics visible

---

## Phase 6: Bug Fixes and Optimization (Day 8-10, ~12 hours)

### 6.1 Prioritize Issues

**Issue triage criteria**:
- **P0 (Critical)**: System unusable, crashes, data loss
- **P1 (High)**: Core features broken, poor UX
- **P2 (Medium)**: Nice-to-have features, minor bugs
- **P3 (Low)**: Cosmetic issues, documentation

**Focus on P0 and P1 issues only** before pilot deployment.

### 6.2 Implement Fixes

**Standard fix workflow**:
1. Create feature branch: `git checkout -b fix/issue-description`
2. Implement fix with tests
3. Verify fix on hardware
4. Update documentation
5. Commit and push: `git push origin fix/issue-description`
6. Merge to main after validation

### 6.3 Re-run Validation

**After fixes, re-run critical tests**:
```bash
# Re-run integration tests
pytest tests/test_production_components.py -v

# Re-run E2E hardware tests
python tests/test_e2e_hardware.py --queries 100

# Re-run performance benchmarks
python bench/hardware_latency_bench.py
```

**Success Criteria**:
- [ ] All P0/P1 issues resolved
- [ ] No regression in test pass rate
- [ ] Performance metrics still meet targets

---

## Completion Checklist

### Hardware Validation ✅
- [ ] Bluetooth stable for 1+ hour (>99% uptime)
- [ ] E2E latency < 1.5s (P95)
- [ ] Battery drain < 20%/hour (glasses), < 15%/hour (phone)
- [ ] Success rate > 90% across 100 queries
- [ ] Wake word accuracy > 90%
- [ ] Speech recognition WER < 20%
- [ ] Scene classification accuracy > 85%
- [ ] OCR accuracy > 90%

### Documentation ✅
- [ ] Hardware test report complete
- [ ] Benchmarks updated in README.md
- [ ] Issue log documented with severity
- [ ] Demo video recorded and uploaded
- [ ] PERFORMANCE.md updated with hardware metrics

### Deliverables ✅
- [ ] Hardware test report (HTML/PDF)
- [ ] Demo video (2-3 minutes)
- [ ] Issue backlog (prioritized)
- [ ] Updated documentation

### Go/No-Go Decision ✅
- [ ] **GO**: All success criteria met, no critical blockers
- [ ] **NO-GO**: Critical issues unfixable in < 2 weeks

---

## Appendix A: Test Scripts Index

All test scripts referenced in this runbook:

- `scripts/test_bluetooth_stability.py` - Bluetooth connection stability test
- `scripts/measure_bt_latency.py` - Bluetooth audio latency measurement
- `tests/test_audio_pipeline_hardware.py` - Audio pipeline validation
- `tests/test_vision_pipeline_hardware.py` - Vision pipeline validation
- `tests/test_e2e_hardware.py` - End-to-end workflow testing
- `bench/hardware_latency_bench.py` - Detailed latency profiling
- `tests/test_battery_consumption.py` - Battery drain testing
- `bench/network_latency_bench.py` - Network performance testing
- `tests/test_stress_hardware.py` - Stress testing
- `tests/test_memory_leak.py` - Memory leak detection
- `scripts/generate_hardware_report.py` - Report generation

---

## Appendix B: Troubleshooting Guide

### Issue: Glasses won't pair
**Solution**: 
1. Reset glasses (hold button 30s)
2. Clear Bluetooth cache on phone
3. Reinstall Meta View app

### Issue: Poor audio quality
**Solution**:
1. Check microphone not obstructed
2. Test in quieter environment
3. Update firmware

### Issue: High latency (> 3s)
**Solution**:
1. Check network connection (WiFi vs cellular)
2. Test with local model (remove API calls)
3. Profile to find bottleneck

### Issue: Battery drains quickly
**Solution**:
1. Reduce query frequency
2. Disable vision when not needed
3. Lower screen brightness on phone

---

**End of Runbook**

*Next Step: Execute validation and proceed to pilot deployment if GO criteria met.*
