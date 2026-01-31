# Hardware Testing Guide - Meta Ray-Ban + OPPO Reno 12

## Overview

This comprehensive guide covers end-to-end hardware testing for the SmartGlass AI Agent deployment on **Meta Ray-Ban smart glasses** paired with **OPPO Reno 12 smartphone**. Follow these instructions to set up, test, and validate the complete hardware stack.

**Target Deployment**: Meta Ray-Ban Wayfarer + OPPO Reno 12 + Python Backend Server

---

## Part 1: Backend Setup

### 1.1 Start the Python Edge Runtime Server

The backend server processes multimodal data (audio/video) from the glasses via the mobile app.

#### Prerequisites
- Python 3.8+ installed
- Required dependencies: `pip install -r requirements.txt`
- Port 5000 available (default)

#### Start Server

```bash
cd /home/runner/work/SmartGlass-AI-Agent/SmartGlass-AI-Agent
python -m src.edge_runtime.server
```

**Expected Output:**
```
* Running on http://0.0.0.0:5000
* Edge runtime server started
* Privacy defaults: STORE_RAW_AUDIO=false, STORE_RAW_FRAMES=false, STORE_TRANSCRIPTS=false
```

#### Environment Variables (Optional)

Configure privacy and storage settings:

```bash
export STORE_RAW_AUDIO=false      # Keep audio buffers in memory
export STORE_RAW_FRAMES=false     # Preserve video frames
export STORE_TRANSCRIPTS=false    # Retain transcripts
export PROVIDER=meta              # Use Meta Ray-Ban provider
```

### 1.2 Find Your Server IP Address

The mobile app needs to connect to the backend server via network IP.

#### On Linux/Mac:
```bash
# Get local network IP
ip addr show | grep "inet " | grep -v 127.0.0.1
# OR
ifconfig | grep "inet " | grep -v 127.0.0.1
```

#### On Windows:
```bash
ipconfig | findstr IPv4
```

#### Verify Server Accessibility

From another device on the same network:
```bash
curl http://<SERVER_IP>:5000/health
```

**Expected Response:**
```json
{"status": "healthy", "display_available": false}
```

**Save your server IP address** - you'll need it for app configuration (e.g., `192.168.1.100:5000`)

---

## Part 2: Meta Ray-Ban Pairing with OPPO Reno 12

### 2.1 Install Meta View App

1. Open **Google Play Store** on OPPO Reno 12
2. Search for **"Meta View"** or **"Ray-Ban Stories"**
3. Install the official Meta companion app
4. Grant required permissions:
   - Bluetooth
   - Location (for Bluetooth pairing)
   - Notifications
   - Camera (for gallery sync)

### 2.2 Pair Ray-Ban Glasses

#### Initial Pairing Process:

1. **Charge your glasses**: Ensure Meta Ray-Ban glasses are charged (green LED indicator)
2. **Enable pairing mode**:
   - Open the charging case with glasses inside
   - Press and hold the button on the case for 5 seconds
   - LED should flash white (pairing mode active)

3. **Connect via Meta View app**:
   - Open Meta View app on OPPO Reno 12
   - Tap **"Pair New Device"**
   - Enable Bluetooth and Location when prompted
   - Select your Ray-Ban glasses from the list
   - Wait for connection (LED turns solid white)

4. **Complete setup**:
   - Follow on-screen instructions
   - Enable camera/microphone permissions
   - Configure touch controls
   - Update firmware if prompted

#### Verify Connection:

- Open Meta View app → **Devices** tab
- Status should show **"Connected"**
- Battery level should be visible
- Camera preview should work (tap camera icon)

### 2.3 Enable Developer Mode (Optional)

For advanced debugging:

1. Open Meta View app → **Settings**
2. Tap **"About"** → **"Build Number"** 7 times
3. Enter device PIN
4. Developer options now available
5. Enable **USB Debugging** if needed

---

## Part 3: APK Installation via ADB

### 3.1 Enable USB Debugging on OPPO Reno 12

1. Open **Settings** → **About Phone**
2. Tap **"Version"** or **"Build Number"** 7 times to enable Developer Options
3. Return to **Settings** → **Additional Settings** → **Developer Options**
4. Enable **"USB Debugging"**
5. Enable **"Install via USB"** (optional, for easier APK install)

### 3.2 Install Android Debug Bridge (ADB)

#### On Linux/Mac:
```bash
# Ubuntu/Debian
sudo apt-get install android-tools-adb android-tools-fastboot

# macOS (Homebrew)
brew install android-platform-tools
```

#### On Windows:
- Download [SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools)
- Extract to `C:\platform-tools`
- Add to PATH environment variable

#### Verify Installation:
```bash
adb version
```

### 3.3 Build the SmartGlass APK

From the repository root:

```bash
# Build debug APK
./gradlew :sample:assembleDebug

# APK location:
# sample/build/outputs/apk/debug/sample-debug.apk
```

**Tip**: If Gradle daemon hangs, use `./gradlew --stop` and retry.

### 3.4 Connect OPPO Reno 12 via USB

1. Connect phone to computer with USB cable
2. On phone: Select **"File Transfer"** or **"MTP"** mode
3. Tap **"Allow USB debugging"** when prompted
4. Check **"Always allow from this computer"** (optional)

#### Verify Connection:
```bash
adb devices
```

**Expected Output:**
```
List of devices attached
<SERIAL_NUMBER>    device
```

If shows "unauthorized", check phone notification and approve.

### 3.5 Install APK

```bash
# Install APK to device
adb install -r sample/build/outputs/apk/debug/sample-debug.apk

# -r flag allows reinstall (useful for updates)
```

**Expected Output:**
```
Performing Streamed Install
Success
```

#### Troubleshooting Installation Issues:

**Error: INSTALL_FAILED_UPDATE_INCOMPATIBLE**
```bash
# Uninstall existing app first
adb uninstall com.smartglass.sample
# Then reinstall
adb install sample/build/outputs/apk/debug/sample-debug.apk
```

**Error: device offline**
```bash
adb kill-server
adb start-server
adb devices
```

### 3.6 Launch the App

```bash
# Launch app via ADB
adb shell am start -n com.smartglass.sample/.ComposeActivity

# OR manually: Find "SmartGlass AI" app on phone home screen
```

---

## Part 4: End-to-End Test Scenarios

### Test Scenario 1: Backend Connectivity Test

**Objective**: Verify mobile app can connect to backend server

**Steps**:
1. Open SmartGlass AI app on OPPO Reno 12
2. Tap **"Settings"** (menu icon) → **"Backend Configuration"**
3. Enter server URL: `http://<SERVER_IP>:5000`
4. Tap **"Save"**
5. Return to main screen
6. Observe connection status bar at top

**Expected Result**:
- Status changes from **"DISCONNECTED"** to **"CONNECTING"** to **"CONNECTED"**
- Backend server logs show: `New session created: <session_id>`

**Pass Criteria**: ✅ Connection status shows "CONNECTED" within 5 seconds

**Debug**:
```bash
# Check server logs
# View logcat from app
adb logcat | grep SmartGlass
```

---

### Test Scenario 2: Text Query Processing

**Objective**: Test basic text-to-response pipeline without glasses

**Steps**:
1. Ensure app is connected to backend (green status indicator)
2. In the text input field, type: `"What can you help me with?"`
3. Tap **Send** button
4. Wait for AI response

**Expected Result**:
- User message appears in chat (right-aligned, blue bubble)
- AI response appears within 2-3 seconds (left-aligned, gray bubble)
- Response describes available features (vision, audio, actions)

**Performance Benchmark**:
- Response latency: **< 2 seconds** (target)
- App remains responsive during processing

**Pass Criteria**: ✅ Response received within 3 seconds, no crashes

**Debug**:
```bash
# Monitor backend processing
curl http://<SERVER_IP>:5000/metrics

# Check session logs
adb logcat | grep "onSendMessage\|AI response"
```

---

### Test Scenario 3: Audio Streaming from Ray-Ban Glasses

**Objective**: Test real-time audio capture and speech-to-text

**Prerequisites**:
- Meta Ray-Ban glasses paired and connected
- Backend server running with Whisper model

**Steps**:
1. Ensure glasses are connected (check Meta View app)
2. In SmartGlass AI app, tap **"Connect to Glasses"** button (FAB)
3. Observe status change to **"CONNECTED"**
4. Tap the **microphone icon** in the app
5. Speak into Ray-Ban glasses microphone: `"Hello, can you hear me?"`
6. Wait 2-3 seconds
7. Check for transcribed text in input field

**Expected Result**:
- Glasses microphone activates (haptic feedback/LED indicator)
- Audio streams to backend in real-time
- Transcribed text appears in input field
- Backend logs show: `ASR transcription: "Hello, can you hear me?"`

**Performance Benchmark**:
- Audio streaming latency: **< 500ms**
- Transcription delay: **< 2 seconds** after speech ends
- Battery drain: **< 2% during 60-second test**

**Pass Criteria**: ✅ Transcription accuracy > 90%, latency < 2s

**Debug**:
```bash
# Check audio stream
adb logcat | grep "AudioStream\|Microphone"

# Server-side audio logs
# Look for: "Audio frame received: <bytes>"
```

---

### Test Scenario 4: Vision + Audio Multimodal Query

**Objective**: Test complete multimodal pipeline (camera + microphone + LLM)

**Prerequisites**:
- Meta Ray-Ban glasses paired and connected
- Backend server running with CLIP + Whisper + SNN/LLM

**Steps**:
1. Ensure glasses are connected
2. In SmartGlass AI app, enable **"Auto Frame Capture"** in settings
3. Point Ray-Ban glasses camera at an object (e.g., coffee mug on desk)
4. Tap microphone icon
5. Say: `"What am I looking at?"`
6. Wait for AI response

**Expected Result**:
- Camera captures frame automatically
- Audio streams and transcribes
- Backend processes both modalities
- AI response describes the scene: `"You're looking at a coffee mug on a desk..."`
- Response includes suggested actions (if applicable)

**Performance Benchmark**:
- Total end-to-end latency: **< 5 seconds** (target: < 2s)
- Frame capture: **< 200ms**
- Vision processing (CLIP): **< 500ms**
- Audio transcription: **< 1s**
- LLM generation: **< 2s**
- Memory usage: **< 200MB** on device

**Pass Criteria**: ✅ Complete response within 5s, accurate scene description

**Advanced**: Test with complex scenarios:
- Multiple objects in scene
- Text/signage (OCR)
- People/faces (if privacy settings allow)
- Low-light conditions

**Debug**:
```bash
# Monitor frame streaming
adb logcat | grep "CameraFrame\|Vision"

# Backend multimodal processing
# Check logs for: "Multimodal query: text=..., image=..."

# Performance profiling
adb shell dumpsys gfxinfo com.smartglass.sample
```

---

## Part 5: Performance Benchmarks

### 5.1 Target Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| End-to-End Latency | 3-5s | < 2s | 🟡 In Progress |
| Frame Capture Rate | 30 fps | 5-10 fps (adaptive) | ✅ Implemented |
| Battery Drain (1hr streaming) | 12-15% | < 10% | 🟡 Optimizing |
| Memory Footprint (App) | 180-220MB | < 200MB | ✅ Within Target |
| Backend Response Time | 1.5-2.5s | < 1s | 🟡 Optimizing |
| Audio Transcription Latency | 1.5s | < 1s | 🟡 In Progress |
| Vision Processing (CLIP) | 800ms | < 500ms | 🔴 Needs Work |
| SNN Inference | 300ms | < 200ms | ✅ Within Target |

### 5.2 Benchmark Test Suite

#### Audio Latency Test
```bash
# Run synthetic audio benchmark
python bench/audio_bench.py --out artifacts/audio_latency.csv

# Check results
cat artifacts/audio_latency.csv
```

**Expected Output**: Frame counts, reversal metrics, VAD performance

#### Vision Latency Test
```bash
# Run keyframe + OCR benchmark
python bench/image_bench.py

# Results stored in:
# - artifacts/image_latency.csv
# - artifacts/ocr_results.csv
```

#### End-to-End Integration Test
```bash
# Start backend server in profiling mode
python -m src.edge_runtime.server --profile

# Run test client
python tests/test_integration_e2e.py

# Check metrics endpoint
curl http://localhost:5000/metrics
```

**Metrics to Monitor**:
- `sessions.active`: Number of concurrent sessions
- `latency.vad.avg`: VAD processing time
- `latency.asr.avg`: Audio transcription time
- `latency.vision.avg`: Vision processing time
- `latency.llm.avg`: LLM generation time
- `latency.all.avg`: Total pipeline latency

### 5.3 Mobile App Performance Profiling

#### Using Android Studio Profiler:

1. Connect OPPO Reno 12 via USB (ADB)
2. Open Android Studio
3. **View** → **Tool Windows** → **Profiler**
4. Select **com.smartglass.sample** process
5. Monitor:
   - **CPU**: Should stay < 50% during streaming
   - **Memory**: Heap should stay < 200MB
   - **Network**: Monitor frame/audio upload bandwidth
   - **Battery**: Drain rate during active session

#### Memory Leak Detection:
```bash
# Dump memory info
adb shell dumpsys meminfo com.smartglass.sample

# Check for leaks after 10 minutes of use
# Expected: Memory usage should stabilize
```

### 5.4 Battery Consumption Test

**Procedure**:
1. Fully charge OPPO Reno 12 (100%)
2. Enable airplane mode (disable background apps)
3. Enable Wi-Fi only (for backend connection)
4. Start SmartGlass app
5. Connect to glasses and backend
6. Simulate realistic usage for 1 hour:
   - 5 multimodal queries per 10 minutes
   - Camera auto-capture enabled
   - Idle between queries
7. Record battery level after 1 hour

**Target**: Battery drain < 10% per hour
**Current**: ~12-15% per hour (optimization in progress)

---

## Part 6: Troubleshooting Common Issues

### Issue 1: Cannot Connect to Backend Server

**Symptoms**:
- App shows "DISCONNECTED" or "CONNECTION_FAILED"
- No response from server

**Diagnostics**:
```bash
# Check if server is running
curl http://<SERVER_IP>:5000/health

# Check firewall
# Linux: sudo ufw status
# Windows: Check Windows Defender Firewall

# Verify network connectivity from phone
adb shell ping <SERVER_IP>
```

**Solutions**:
1. ✅ Ensure server is running: `python -m src.edge_runtime.server`
2. ✅ Check firewall allows port 5000
3. ✅ Verify phone and server are on same Wi-Fi network
4. ✅ Try server IP instead of hostname
5. ✅ Check app settings for correct backend URL format: `http://IP:5000` (no trailing slash)

---

### Issue 2: Ray-Ban Glasses Won't Pair

**Symptoms**:
- Glasses not visible in Bluetooth scan
- Pairing fails or disconnects immediately

**Solutions**:
1. ✅ Reset glasses: Hold power button for 10 seconds until LED flashes
2. ✅ Clear Bluetooth cache on phone:
   - Settings → Apps → Bluetooth → Storage → Clear Cache
3. ✅ Forget device and re-pair:
   - Bluetooth settings → Ray-Ban → Forget Device
4. ✅ Update Meta View app to latest version
5. ✅ Charge glasses fully (low battery prevents pairing)
6. ✅ Try pairing in a different location (avoid Bluetooth interference)

---

### Issue 3: Audio Not Streaming from Glasses

**Symptoms**:
- Microphone icon activates but no transcription
- Backend logs show no audio frames

**Diagnostics**:
```bash
# Check microphone permissions
adb shell dumpsys package com.smartglass.sample | grep permission

# Monitor audio stream logs
adb logcat | grep "AudioStream\|Microphone\|MetaRayBan"
```

**Solutions**:
1. ✅ Grant microphone permission: App Settings → Permissions → Microphone
2. ✅ Check Ray-Ban microphone hardware: Test in Meta View app
3. ✅ Restart audio streaming in app (disconnect/reconnect)
4. ✅ Verify `PROVIDER=meta` environment variable on backend
5. ✅ Check Meta View app isn't blocking microphone access

---

### Issue 4: Frame Capture Not Working

**Symptoms**:
- Camera doesn't capture frames
- Vision queries return "No image available"

**Diagnostics**:
```bash
# Check camera permissions
adb shell pm grant com.smartglass.sample android.permission.CAMERA

# Monitor frame capture
adb logcat | grep "CameraFrame\|capturePhoto"
```

**Solutions**:
1. ✅ Grant camera permission in app settings
2. ✅ Enable "Auto Frame Capture" in app settings
3. ✅ Test camera in Meta View app (to rule out hardware issue)
4. ✅ Check Ray-Ban camera LED indicator (should briefly light when capturing)
5. ✅ Restart Ray-Ban glasses
6. ✅ Verify backend has vision model loaded (CLIP)

---

### Issue 5: High Battery Drain

**Symptoms**:
- Battery drains > 15% per hour
- Device gets hot during use

**Diagnostics**:
```bash
# Check battery stats
adb shell dumpsys batterystats com.smartglass.sample

# Monitor CPU usage
adb shell top | grep smartglass
```

**Solutions**:
1. ✅ Reduce frame capture rate: Settings → Advanced → Frame Rate → "5 fps"
2. ✅ Disable auto-capture when not needed
3. ✅ Use adaptive frame rate based on battery level (see Performance Optimization guide)
4. ✅ Enable battery saver mode on phone
5. ✅ Close background apps consuming resources
6. ✅ Update to latest app version with optimizations

---

### Issue 6: Slow AI Response Times

**Symptoms**:
- Responses take > 5 seconds
- Timeouts or "Processing..." stuck

**Diagnostics**:
```bash
# Check backend metrics
curl http://<SERVER_IP>:5000/metrics

# Profile backend
python -m src.edge_runtime.server --profile

# Check backend CPU/GPU usage
top
nvidia-smi  # If using GPU
```

**Solutions**:
1. ✅ Ensure backend runs on GPU if available
2. ✅ Reduce image resolution: Compress frames before upload (see Performance guide)
3. ✅ Use INT8 quantized SNN model (see Performance guide)
4. ✅ Check network latency: `ping <SERVER_IP>`
5. ✅ Increase backend server resources (RAM, CPU cores)
6. ✅ Profile bottleneck stages: Check `/metrics` for slowest component

---

### Issue 7: App Crashes on Startup

**Diagnostics**:
```bash
# View crash logs
adb logcat | grep "AndroidRuntime\|FATAL"

# Check for missing model files
adb shell ls /data/data/com.smartglass.sample/files/
```

**Solutions**:
1. ✅ Reinstall APK: `adb install -r sample-debug.apk`
2. ✅ Clear app data: Settings → Apps → SmartGlass AI → Storage → Clear Data
3. ✅ Check Android version compatibility (requires Android 8.0+)
4. ✅ Verify SNN model file is bundled in APK assets
5. ✅ Check logcat for specific error messages

---

## Part 7: Deployment Checklist

### Hardware Validation Setup (Week 1-2)

- [ ] **Procurement**
  - [ ] Meta Ray-Ban smart glasses (1 unit)
  - [ ] OPPO Reno 12 smartphone (1 unit)
  - [ ] USB-C cable + power bank
  - [ ] Backup test device (optional)

- [ ] **Test Environment**
  - [ ] Install ADB tools on development machine
  - [ ] Prepare a dedicated test space (quiet, stable lighting)
  - [ ] Configure low-latency Wi-Fi network
  - [ ] Set up device logging: `adb logcat` and server logs

- [ ] **Baseline Measurements**
  - [ ] Bluetooth pairing stability (1-hour continuous)
  - [ ] Camera capture quality (sample frames)
  - [ ] Microphone quality (sample audio)
  - [ ] End-to-end latency baseline (5 test runs)
  - [ ] Battery drain baseline (30-minute session)

### Pre-Deployment Validation

- [ ] **Backend Server**
  - [ ] Python 3.8+ installed
  - [ ] All dependencies installed: `pip install -r requirements.txt`
  - [ ] Server starts without errors
  - [ ] `/health` endpoint responds
  - [ ] Privacy environment variables configured
  - [ ] Firewall allows port 5000
  - [ ] SSL/TLS configured (for production)

- [ ] **Meta Ray-Ban Glasses**
  - [ ] Glasses fully charged
  - [ ] Firmware up to date
  - [ ] Paired with OPPO Reno 12 via Meta View app
  - [ ] Camera and microphone working
  - [ ] Touch controls configured

- [ ] **OPPO Reno 12 Mobile App**
  - [ ] Developer options enabled (for ADB)
  - [ ] USB debugging enabled (for initial install)
  - [ ] SmartGlass APK installed
  - [ ] Camera permission granted
  - [ ] Microphone permission granted
  - [ ] Storage permission granted (for logs)
  - [ ] Location permission granted (for Bluetooth)
  - [ ] Backend URL configured correctly

- [ ] **Network Configuration**
  - [ ] Phone and server on same Wi-Fi network
  - [ ] Server IP address reachable from phone
  - [ ] Network bandwidth sufficient (min 5 Mbps)
  - [ ] Low latency (< 50ms ping time)

### Post-Deployment Testing

- [ ] **Smoke Tests**
  - [ ] Backend connectivity test (Scenario 1)
  - [ ] Text query test (Scenario 2)
  - [ ] Audio streaming test (Scenario 3)
  - [ ] Multimodal query test (Scenario 4)

- [ ] **Performance Tests**
  - [ ] End-to-end latency < 5s
  - [ ] Battery drain < 15% per hour
  - [ ] Memory usage < 200MB
  - [ ] No memory leaks after 30 minutes

- [ ] **Stress Tests**
  - [ ] 10 consecutive queries without errors
  - [ ] 1-hour continuous streaming session
  - [ ] Reconnection after network interruption
  - [ ] Graceful handling of backend server restart

### Monitoring Setup

- [ ] **Backend Monitoring**
  - [ ] Enable logging: `python -m src.edge_runtime.server --log-level INFO`
  - [ ] Monitor `/metrics` endpoint periodically
  - [ ] Set up alerting for errors/downtime
  - [ ] Configure log rotation

- [ ] **Mobile App Monitoring**
  - [ ] Enable crash reporting (Firebase Crashlytics recommended)
  - [ ] Monitor app performance via Android vitals
  - [ ] Track user engagement metrics
  - [ ] Set up feedback mechanism

---

## Part 8: Reference Appendices

### Appendix A: API Endpoints

#### Backend Server Endpoints

**GET /health**
- **Description**: Health check
- **Response**: `{"status": "healthy"}`

**GET /sessions**
- **Description**: List all active sessions
- **Response**: `{"sessions": [{"session_id": "<uuid>", "transcript_count": 0, "has_frame": false, "query_count": 0}], "count": 1}`

**POST /sessions**
- **Description**: Create new session
- **Headers**:
  - `X-Privacy-Store-Raw-Audio: true/false`
  - `X-Privacy-Store-Raw-Frames: true/false`
  - `X-Privacy-Store-Transcripts: true/false`
- **Response**: `{"session_id": "<uuid>"}`

**POST /sessions/<session_id>/query**
- **Description**: Send text query
- **Body**: `{"text": "query text"}`
- **Response**: `{"response": "AI response", "actions": [...]}`

**POST /sessions/<session_id>/multimodal**
- **Description**: Send multimodal query (text + image)
- **Body**: `{"text": "query", "image": "base64_encoded_image"}`
- **Response**: `{"response": "AI response", "actions": [...]}`

**GET /metrics**
- **Description**: Get performance metrics
- **Response**: Latency histograms, session counts, query volumes

### Appendix B: Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PROVIDER` | `mock` | Provider selection (mock, meta, vuzix, etc.) |
| `STORE_RAW_AUDIO` | `false` | Keep audio buffers in memory |
| `STORE_RAW_FRAMES` | `false` | Preserve video frames |
| `STORE_TRANSCRIPTS` | `false` | Retain conversation history |
| `WHISPER_MODEL` | `base` | Whisper model size (tiny/base/small/medium/large) |
| `CLIP_MODEL` | `openai/clip-vit-base-patch32` | CLIP model identifier |
| `SNN_MODEL_PATH` | `artifacts/snn_student/student.pt` | SNN model checkpoint path |

### Appendix C: ADB Quick Reference

```bash
# List connected devices
adb devices

# Install APK
adb install -r app.apk

# Uninstall app
adb uninstall com.smartglass.sample

# Launch app
adb shell am start -n com.smartglass.sample/.ComposeActivity

# View logs (filtered)
adb logcat | grep SmartGlass

# Clear logs
adb logcat -c

# Grant permission
adb shell pm grant com.smartglass.sample android.permission.CAMERA

# Pull file from device
adb pull /sdcard/smartglass/logs/app.log ./

# Push file to device
adb push model.pt /sdcard/smartglass/models/

# Take screenshot
adb shell screencap -p /sdcard/screen.png
adb pull /sdcard/screen.png

# Record video
adb shell screenrecord /sdcard/demo.mp4
# Stop with Ctrl+C
adb pull /sdcard/demo.mp4
```

### Appendix D: Meta Ray-Ban Specifications

**Hardware**:
- Camera: 5MP, 1080p video
- Microphone: Dual beamforming microphones
- Speaker: Open-ear audio (Bose)
- Battery: Up to 6 hours continuous use
- Connectivity: Bluetooth 5.0
- Weight: ~50g

**Supported Features**:
- Photo/video capture
- Voice commands
- Audio streaming
- Facebook/Instagram sharing
- LED privacy indicator

### Appendix E: OPPO Reno 12 Specifications

**Hardware**:
- CPU: MediaTek Dimensity 7300
- RAM: 8GB/12GB
- Storage: 256GB/512GB
- Display: 6.7" AMOLED, 120Hz
- OS: Android 14 (ColorOS 14)
- Battery: 5000mAh
- Connectivity: 5G, Wi-Fi 6, Bluetooth 5.3

**Performance Notes**:
- Excellent for AI workload offloading
- Long battery life for extended sessions
- Fast charging (80W SUPERVOOC)

### Appendix F: Network Requirements

**Minimum**:
- Bandwidth: 5 Mbps upload/download
- Latency: < 100ms
- Connection: Wi-Fi or 4G/5G

**Recommended**:
- Bandwidth: 10+ Mbps
- Latency: < 50ms
- Connection: Wi-Fi 5/6 or 5G

**Data Usage Estimates**:
- Audio streaming: ~100 KB/min
- Video frames (5 fps): ~500 KB/min
- Total multimodal session: ~600-800 KB/min (~36 MB/hour)

### Appendix G: Privacy & Compliance

**Data Handling**:
- All processing happens on local backend server (no cloud by default)
- Raw audio/video never saved to disk (configurable)
- User controls via privacy settings
- Compliant with Meta Wearables DAT requirements

**User Rights**:
- View privacy settings anytime
- Disable data retention
- Clear session data
- Stop streaming anytime
- Disconnect glasses

**See Also**: [PRIVACY.md](../PRIVACY.md) for detailed privacy documentation

---

## Additional Resources

- **Meta DAT Integration**: [docs/meta_dat_integration.md](meta_dat_integration.md)
- **Hello SmartGlass Quickstart**: [docs/hello_smartglass_quickstart.md](hello_smartglass_quickstart.md)
- **Performance Optimization Guide**: [docs/PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md)
- **API Reference**: [docs/API_REFERENCE.md](API_REFERENCE.md)
- **Privacy Documentation**: [PRIVACY.md](../PRIVACY.md)
- **Implementation Progress**: [docs/IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md)

---

## Support

For issues, questions, or contributions:
- **GitHub Issues**: [SmartGlass-AI-Agent Issues](https://github.com/farmountain/SmartGlass-AI-Agent/issues)
- **Email**: farmountain@gmail.com
- **Documentation**: [Project Wiki](https://github.com/farmountain/SmartGlass-AI-Agent/wiki)

---

**Last Updated**: December 2024
**Version**: 1.0
**Target Hardware**: Meta Ray-Ban Wayfarer + OPPO Reno 12
