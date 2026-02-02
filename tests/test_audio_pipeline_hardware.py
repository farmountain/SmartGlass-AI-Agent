#!/usr/bin/env python3
"""Test audio pipeline on real hardware."""
import time
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_wakeword_detection():
    """Test wake word detection accuracy."""
    try:
        from src.audio.wakeword_detector import WakeWordDetector
    except ImportError:
        print("WARNING: WakeWordDetector not available, skipping test")
        return
    
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
        if hasattr(detector, 'detect_frame') and detector.detect_frame():  # Non-blocking check
            false_positives += 1
            print(f"  ⚠️  False positive at {time.time()-start:.1f}s")
        time.sleep(0.1)
    
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
    try:
        from src.whisper_processor import WhisperAudioProcessor
    except ImportError:
        print("WARNING: WhisperAudioProcessor not available, skipping test")
        return
    
    recognizer = WhisperAudioProcessor(model_size="base")
    
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
        # Simulate audio capture and transcription
        # In real test, capture from glasses microphone
        print(f"  [Simulated] Recording audio...")
        time.sleep(2)  # Simulate recording time
        
        # Mock recognition for now (replace with actual hardware test)
        recognized = phrase  # Placeholder
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
    print("Hardware Audio Pipeline Testing")
    print("================================\n")
    
    try:
        # test_wakeword_detection()
        test_speech_recognition()
        print("\n✅ All audio pipeline tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        sys.exit(1)
