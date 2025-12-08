# Meta DAT Implementation Plan

Concrete implementation plan for integrating Meta Wearables Device Access Toolkit with SmartGlass-AI-Agent.

## 📋 Executive Summary

This document outlines the step-by-step plan to integrate Meta's Device Access Toolkit (DAT) with the SmartGlass-AI-Agent project, enabling AI-powered experiences on Ray-Ban Meta and Ray-Ban Display glasses.

**Timeline**: 4-6 weeks  
**Platforms**: Android (primary), iOS (secondary)  
**Backend**: Python (existing SmartGlassAgent stack)

---

## 🎯 Goals

1. **Enable Hardware Access**: Connect to Ray-Ban Meta glasses via Meta DAT SDK
2. **Stream Multimodal Data**: Camera frames + microphone audio to backend
3. **Process with AI**: Run SmartGlassAgent pipeline (Whisper, CLIP, SNN/LLM)
4. **Return Actions**: Structured responses with actionable commands
5. **Maintain Privacy**: Comply with Meta terms and user privacy expectations

---

## 🏗️ Architecture Decision

### Mobile App = "Edge Sensor Hub"

The mobile app acts as a bridge between glasses and AI backend:

```
┌──────────────────────────────────────────────────────────┐
│  Ray-Ban Meta Glasses                                    │
│  - Camera: 720x960 @ 30fps                              │
│  - Microphone: 16kHz mono                               │
│  - Controls: Button, wake-word                          │
└────────────┬─────────────────────────────────────────────┘
             │ BLE/WiFi (via Meta DAT SDK)
             │
┌────────────▼─────────────────────────────────────────────┐
│  Mobile App (iOS/Android)                                │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Meta DAT SDK Layer                                 │  │
│  │ - Connection management                            │  │
│  │ - Frame streaming                                  │  │
│  │ - Audio streaming                                  │  │
│  │ - Photo capture                                    │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Processing Layer                                   │  │
│  │ - Downsample: 30fps → 5fps (every 6th frame)     │  │
│  │ - Compress: RGB888 → JPEG (85% quality)          │  │
│  │ - Batch: Audio chunks (400 samples @ 16kHz)      │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Communication Layer                                │  │
│  │ - SmartGlassEdgeClient (existing)                 │  │
│  │ - WebSocket for streaming                         │  │
│  │ - HTTP/REST for request-response                  │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │ UI Layer                                           │  │
│  │ - Connection status                               │  │
│  │ - Response display                                │  │
│  │ - Action execution (TTS, navigation)              │  │
│  └────────────────────────────────────────────────────┘  │
└────────────┬─────────────────────────────────────────────┘
             │ HTTP/WebSocket
             │
┌────────────▼─────────────────────────────────────────────┐
│  SmartGlass AI Backend (Python)                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Edge Runtime Server                                │  │
│  │ - FastAPI endpoints                               │  │
│  │ - Session management                              │  │
│  │ - Privacy controls                                │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │ SmartGlassAgent Pipeline                           │  │
│  │ - Whisper (audio → text)                          │  │
│  │ - CLIP/DeepSeek-Vision (image → embeddings)       │  │
│  │ - AUREUS/Do-Attention (reasoning)                 │  │
│  │ - SNNLLMBackend (text generation)                 │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Action Generation                                  │  │
│  │ - Structured action schema                        │  │
│  │ - RaySkillKit mapping                             │  │
│  │ - Response formatting                             │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## 📅 Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal**: Get basic connectivity working with Mock Device

#### Tasks:

1. **Developer Account Setup** (Day 1-2)
   - [ ] Create Meta Managed Account
   - [ ] Create Organization
   - [ ] Create Project for SmartGlass-AI-Agent
   - [ ] Apply for Developer Preview access
   - [ ] Register app bundle IDs

2. **Android Sample App** (Day 3-5)
   - [ ] Clone `facebook/meta-wearables-dat-android`
   - [ ] Set up GitHub Maven authentication
   - [ ] Build and run `samples/CameraAccess`
   - [ ] Test with Mock Device
   - [ ] Document authentication steps

3. **Backend Verification** (Day 5-7)
   - [ ] Verify existing SmartGlassAgent works
   - [ ] Test edge runtime server
   - [ ] Confirm SmartGlassEdgeClient integration
   - [ ] Test dummy agent mode
   - [ ] Document backend endpoints

4. **Initial Integration** (Day 7-10)
   - [ ] Add SmartGlassEdgeClient to Android sample
   - [ ] Implement basic frame callback
   - [ ] Send single frame to backend
   - [ ] Receive and display response
   - [ ] Test end-to-end with Mock Device

**Deliverables**:
- ✅ Working Android app with Mock Device
- ✅ Frame sent to backend
- ✅ AI response received and displayed
- ✅ Documentation of setup process

---

### Phase 2: Core Streaming (Week 2-3)

**Goal**: Implement continuous streaming and optimize data flow

#### Tasks:

1. **Frame Streaming** (Day 11-13)
   - [ ] Implement frame downsampling (30fps → 5fps)
   - [ ] Add JPEG compression (target: <50KB per frame)
   - [ ] Implement frame buffering/queue
   - [ ] Handle backpressure (slow network)
   - [ ] Add frame metadata (timestamp, sequence)

2. **Audio Streaming** (Day 14-16)
   - [ ] Capture microphone stream from glasses
   - [ ] Chunk audio (400 samples @ 16kHz)
   - [ ] Send audio to backend
   - [ ] Verify Whisper transcription
   - [ ] Sync audio with video timestamps

3. **Multimodal Fusion** (Day 17-19)
   - [ ] Send audio + video in same session
   - [ ] Backend: fuse transcripts with vision
   - [ ] Test multimodal queries
   - [ ] Optimize latency (target: <2s end-to-end)
   - [ ] Add performance metrics

4. **Error Handling** (Day 19-21)
   - [ ] Handle connection drops
   - [ ] Implement retry logic
   - [ ] Add battery level monitoring
   - [ ] Handle permission denials
   - [ ] Add user-friendly error messages

**Deliverables**:
- ✅ Continuous frame streaming (5fps)
- ✅ Audio streaming with transcription
- ✅ Multimodal query processing
- ✅ Robust error handling

---

### Phase 3: Actions & UX (Week 3-4)

**Goal**: Implement structured actions and polish user experience

#### Tasks:

1. **Action Execution** (Day 22-24)
   - [ ] Parse action responses from backend
   - [ ] Implement NAVIGATE action (Google Maps)
   - [ ] Implement SHOW_TEXT action (notification)
   - [ ] Add TTS for audio responses
   - [ ] Test RaySkillKit integration

2. **UI/UX Polish** (Day 25-27)
   - [ ] Design connection flow UI
   - [ ] Add loading states
   - [ ] Implement settings screen
   - [ ] Add privacy controls toggle
   - [ ] Design response display

3. **Privacy Controls** (Day 27-28)
   - [ ] Implement data retention toggles
   - [ ] Add consent dialogs
   - [ ] Integrate Meta analytics opt-out
   - [ ] Document privacy features
   - [ ] Test privacy compliance

4. **Testing & Optimization** (Day 29-30)
   - [ ] End-to-end testing with Mock Device
   - [ ] Performance profiling
   - [ ] Battery usage testing
   - [ ] Network usage optimization
   - [ ] Memory leak checks

**Deliverables**:
- ✅ Actionable responses (navigation, notifications)
- ✅ Polished user interface
- ✅ Privacy-compliant implementation
- ✅ Performance benchmarks

---

### Phase 4: Hardware & iOS (Week 4-6)

**Goal**: Test with real hardware and expand to iOS

#### Tasks:

1. **Hardware Testing** (Day 31-35)
   - [ ] Obtain Ray-Ban Meta glasses (if available)
   - [ ] Test BLE connection (not mock)
   - [ ] Verify camera quality and frame rate
   - [ ] Test microphone quality
   - [ ] Measure real-world latency
   - [ ] Document hardware quirks

2. **iOS Implementation** (Day 36-40)
   - [ ] Clone `facebook/meta-wearables-dat-ios`
   - [ ] Build and run iOS sample
   - [ ] Port Android integration to Swift
   - [ ] Implement frame streaming
   - [ ] Test with Mock Device (iOS)
   - [ ] Test with real hardware (if available)

3. **Cross-Platform Polish** (Day 41-42)
   - [ ] Ensure API parity between platforms
   - [ ] Sync feature sets
   - [ ] Harmonize UI/UX
   - [ ] Document platform differences
   - [ ] Create comparison matrix

4. **Documentation & Launch** (Day 43-45)
   - [ ] Complete integration guide
   - [ ] Write troubleshooting guide
   - [ ] Create video tutorials
   - [ ] Prepare demo for stakeholders
   - [ ] Submit for preview review (if applicable)

**Deliverables**:
- ✅ Hardware-tested Android app
- ✅ Working iOS app
- ✅ Comprehensive documentation
- ✅ Demo-ready implementation

---

## 🔧 Technical Implementation Details

### Frame Downsampling Strategy

**Problem**: 30fps is too much data for real-time AI processing

**Solution**: Sample every Nth frame

```kotlin
// Android
var frameCount = 0
fun onFrameReceived(frame: CameraFrame) {
    frameCount++
    if (frameCount % 6 == 0) {  // Every 6th frame = ~5fps
        sendToBackend(frame)
    }
}
```

**Rationale**: 5fps is sufficient for most AI use cases while reducing:
- Network bandwidth: 6x reduction
- Backend processing: 6x reduction
- Battery usage: Significant savings

### JPEG Compression

**Problem**: Raw RGB888 frames are large (720x960x3 = 2MB)

**Solution**: Compress to JPEG

```kotlin
// Android
val stream = ByteArrayOutputStream()
frame.compress(Bitmap.CompressFormat.JPEG, 85, stream)
val jpegBytes = stream.toByteArray()  // Typically <50KB
```

**Quality Settings**:
- 85%: Good balance (30-50KB)
- 90%: Higher quality (50-80KB)
- 80%: Lower quality (20-40KB)

### Audio Chunking

**Problem**: Continuous audio stream needs to be batched

**Solution**: Send 400-sample chunks

```kotlin
// Android
// 400 samples @ 16kHz = 25ms of audio
val chunkSize = 400
val audioBuffer = FloatArray(chunkSize)
```

**Rationale**:
- 25ms chunks minimize latency
- Small enough for real-time processing
- Large enough to avoid overhead

### Session Management

**State Machine**:
```
[Disconnected] 
    → connect() 
    → [Connecting] 
    → onConnected()
    → [Connected]
    → createSession()
    → [Streaming]
    → disconnect()
    → [Disconnected]
```

**Session Lifecycle**:
1. User clicks "Connect"
2. App connects to glasses via Meta DAT
3. App creates backend session
4. App starts streaming frames/audio
5. Backend processes and responds
6. User clicks "Disconnect" or error occurs
7. App closes session and disconnects

---

## 🔒 Privacy & Compliance

### Meta Developer Terms Compliance

**Required**:
- User consent before accessing camera/mic
- Clear disclosure of data usage
- Honor user opt-out requests
- Comply with Acceptable Use Policy
- No prohibited use cases (surveillance, etc.)

### SmartGlass Privacy Controls

**Environment Variables**:
```bash
export STORE_RAW_AUDIO=false      # Don't persist audio
export STORE_RAW_FRAMES=false     # Don't persist frames
export STORE_TRANSCRIPTS=false    # Don't persist transcripts
```

**User-Facing Controls**:
- Toggle for data retention
- Clear data button
- Privacy policy link
- Analytics opt-out

### Data Flow

**Minimal Retention Strategy**:
1. Frame captured on glasses
2. Sent to mobile app (transient)
3. Compressed and sent to backend (transient)
4. Processed by AI models (transient)
5. Response generated
6. **No data persisted by default**

**Opt-In Persistence** (for debugging only):
- User explicitly enables retention
- Clear indication when enabled
- Time-limited retention (e.g., 24 hours)
- Easy deletion

---

## 🧪 Testing Strategy

### Unit Tests

**Android**:
```kotlin
@Test
fun testFrameDownsampling() {
    val handler = CameraHandler(downsampleRate = 6)
    // Test that only every 6th frame is processed
}

@Test
fun testJpegCompression() {
    val bitmap = createTestBitmap()
    val compressed = compressToJpeg(bitmap, quality = 85)
    assertTrue(compressed.size < 100_000) // <100KB
}
```

**Backend**:
```python
def test_multimodal_query():
    agent = SmartGlassAgent()
    result = agent.process_multimodal_query(
        text_query="What do you see?",
        image_input=test_image
    )
    assert "response" in result
    assert "actions" in result
```

### Integration Tests

1. **Mock Device Flow**
   - Connect to Mock Device
   - Capture frame
   - Send to backend
   - Verify response

2. **Real Hardware Flow** (if available)
   - Connect via BLE
   - Stream frames
   - Stream audio
   - Verify quality

3. **Error Scenarios**
   - Network disconnect
   - Backend timeout
   - Permission denied
   - Battery low

### Performance Benchmarks

**Metrics to Track**:
- End-to-end latency (capture → response)
- Frame processing time
- Network bandwidth usage
- Battery consumption per hour
- Memory usage

**Targets**:
- Latency: <2 seconds (capture to response)
- Bandwidth: <5 MB/minute (streaming)
- Battery: <10% per hour (continuous use)
- Memory: <200MB (Android), <150MB (iOS)

---

## 📚 Documentation Deliverables

### For Developers

1. **Setup Guide** ✅
   - Account creation
   - SDK installation
   - First app setup

2. **Integration Guide** ✅
   - Architecture overview
   - Code examples
   - Best practices

3. **API Reference**
   - Meta DAT SDK methods
   - SmartGlassEdgeClient API
   - Response schemas

4. **Troubleshooting Guide** ✅
   - Common errors
   - Debug tips
   - FAQ

### For Users

1. **Getting Started**
   - How to connect glasses
   - Basic usage
   - Privacy controls

2. **Use Cases**
   - Example scenarios
   - Feature demonstrations
   - Tips and tricks

### For Stakeholders

1. **Technical Overview**
   - Architecture diagrams
   - Technology stack
   - Performance metrics

2. **Privacy & Compliance**
   - Data handling policies
   - Compliance measures
   - User controls

---

## 🎯 Success Criteria

### Minimum Viable Product (MVP)

- [ ] Android app connects to Ray-Ban Meta (or Mock Device)
- [ ] Streams camera frames (5fps) to backend
- [ ] Backend processes with SmartGlassAgent
- [ ] Responses displayed in mobile app
- [ ] Basic error handling
- [ ] Privacy controls implemented

### Full Launch Criteria

- [ ] Both Android and iOS apps working
- [ ] Tested with real hardware
- [ ] <2 second end-to-end latency
- [ ] Comprehensive documentation
- [ ] Privacy compliance verified
- [ ] Demo video created
- [ ] User testing completed

---

## 🚧 Known Limitations

### Current Constraints

1. **No AR Overlays**: Cannot render custom UI on Ray-Ban Display (yet)
2. **Mobile-Anchored**: All processing requires paired mobile app
3. **Preview Access**: Meta DAT still in developer preview
4. **Platform Support**: Android and iOS only (no web)

### Future Enhancements

1. **On-Device AI**: Run SNN models on mobile for lower latency
2. **Offline Mode**: Cache models and work without network
3. **AR Integration**: Add overlays when Meta enables developer access
4. **Watch App**: Extend to companion watch apps
5. **Multi-Device**: Support multiple glasses per user

---

## 📞 Support & Resources

### Getting Help

- **Meta Developer Portal**: https://developers.meta.com/wearables
- **SmartGlass GitHub**: https://github.com/farmountain/SmartGlass-AI-Agent
- **Issue Tracker**: Open issues on GitHub
- **Email**: farmountain@gmail.com

### Related Documentation

- [Meta DAT Integration Guide](meta_dat_integration.md)
- [Hello SmartGlass Quickstart](hello_smartglass_quickstart.md)
- [Android SDK Guide](../ANDROID_SDK.md)
- [SmartGlassAgent API](API_REFERENCE.md)
- [Privacy Guidelines](../PRIVACY.md)

---

## 📝 Project Tracking Template

Use this template to track your implementation progress:

**Project Status**: [ Planning / In Progress / Testing / Complete ]  
**Current Phase**: [ Phase 1 / Phase 2 / Phase 3 / Phase 4 ]  
**Start Date**: [ Your start date ]  
**Target Completion**: [ Your target date ]  
**Team Size**: [ Number of developers ]

**Built with ❤️ for AI-powered wearables**
