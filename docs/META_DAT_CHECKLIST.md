# Meta DAT Integration Checklist

A practical checklist for integrating Meta Wearables Device Access Toolkit with SmartGlass-AI-Agent.

## 📋 Pre-Development Setup

### Meta Developer Account
- [ ] Create Meta Managed Account at [developers.meta.com/wearables](https://developers.meta.com/wearables)
- [ ] Create Organization for your company/project
- [ ] Add team members to organization
- [ ] Create Project named "SmartGlass-AI-Agent" (or your app name)
- [ ] Apply for Developer Preview access via interest form
- [ ] Wait for approval (may take several days)
- [ ] Register iOS app bundle ID: `com.yourcompany.smartglass`
- [ ] Register Android package name: `com.yourcompany.smartglass`

### Development Tools
- [ ] Install Android Studio (latest stable)
- [ ] Install Xcode 15+ (macOS only, for iOS development)
- [ ] Install Python 3.9+ on development machine
- [ ] Install Git command line tools
- [ ] Create GitHub Personal Access Token (for Maven access)
- [ ] Set `GITHUB_TOKEN` environment variable

### Repository Setup
- [ ] Clone SmartGlass-AI-Agent: `git clone https://github.com/farmountain/SmartGlass-AI-Agent.git`
- [ ] Clone Meta DAT Android SDK (optional): `git clone https://github.com/facebook/meta-wearables-dat-android.git`
- [ ] Clone Meta DAT iOS SDK (optional): `git clone https://github.com/facebook/meta-wearables-dat-ios.git`
- [ ] Review all three documentation files (Integration Guide, Quickstart, Implementation Plan)

---

## 🐍 Backend Setup

### Python Environment
- [ ] Navigate to SmartGlass-AI-Agent directory
- [ ] Create virtual environment: `python -m venv venv`
- [ ] Activate virtual environment
  - macOS/Linux: `source venv/bin/activate`
  - Windows: `venv\Scripts\activate`
- [ ] Upgrade pip: `pip install --upgrade pip`
- [ ] Install requirements: `pip install -r requirements.txt`

### Backend Testing
- [ ] Set provider: `export PROVIDER=meta`
- [ ] Enable dummy agent: `export SDK_PYTHON_DUMMY_AGENT=1`
- [ ] Start server: `python -m sdk_python.server --host 0.0.0.0 --port 8000`
- [ ] Test health endpoint: `curl http://localhost:8000/health`
- [ ] Expected response: `{"status":"healthy"}`
- [ ] Note your computer's IP address for mobile app
  - macOS/Linux: `ifconfig | grep inet`
  - Windows: `ipconfig`

---

## 📱 Android Development

### Project Setup
- [ ] Open Android Studio
- [ ] Create New Project → Empty Activity
- [ ] Set name: "HelloSmartGlass" (or your app name)
- [ ] Set package: `com.yourcompany.smartglass`
- [ ] Choose Kotlin language
- [ ] Set Minimum SDK: API 24

### Dependencies Configuration
- [ ] Add GitHub Maven repository to `settings.gradle.kts`
- [ ] Add Meta DAT dependencies to `app/build.gradle.kts`
  - `com.meta.wearable:mwdat-core:0.2.1`
  - `com.meta.wearable:mwdat-camera:0.2.1`
  - `com.meta.wearable:mwdat-mockdevice:0.2.1`
- [ ] Add SmartGlass SDK dependency: `implementation(project(":sdk-android"))`
- [ ] Add coroutines: `org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3`
- [ ] Sync Gradle dependencies

### Permissions & Manifest
- [ ] Add `android.permission.INTERNET` to AndroidManifest.xml
- [ ] Add `android.permission.BLUETOOTH` to AndroidManifest.xml
- [ ] Add `android.permission.BLUETOOTH_CONNECT` to AndroidManifest.xml
- [ ] Add analytics opt-out meta-data (optional)
- [ ] Review and accept required permissions

### Implementation
- [ ] Copy MainActivity.kt from [Quickstart guide](hello_smartglass_quickstart.md)
- [ ] Copy activity_main.xml layout from guide
- [ ] Update backend URL to your computer's IP
  - Emulator: `http://10.0.2.2:8000`
  - Physical device: `http://YOUR_IP:8000`
- [ ] Build project (should succeed)

### Testing
- [ ] Run app on emulator or device
- [ ] Click "Connect" button
- [ ] Verify Mock Device connection succeeds
- [ ] Click "Capture & Analyze" button
- [ ] Verify image displayed and AI response received
- [ ] Test error handling (disconnect backend, retry)
- [ ] Check Logcat for any errors

---

## 🍎 iOS Development

### Project Setup
- [ ] Open Xcode
- [ ] File → New → Project
- [ ] Choose iOS → App
- [ ] Set Product Name: "HelloSmartGlass"
- [ ] Set Bundle Identifier: `com.yourcompany.smartglass`
- [ ] Choose SwiftUI interface
- [ ] Choose Swift language

### Dependencies Configuration
- [ ] File → Add Package Dependencies
- [ ] Add: `https://github.com/facebook/meta-wearables-dat-ios`
- [ ] Select latest version
- [ ] Add to HelloSmartGlass target
- [ ] Wait for package resolution

### Info.plist Configuration
- [ ] Open Info.plist
- [ ] Add MWDAT → Analytics → OptOut → YES (optional)
- [ ] Add network usage descriptions (if prompted)

### Implementation
- [ ] Copy ContentView.swift from [Quickstart guide](hello_smartglass_quickstart.md)
- [ ] Copy SmartGlassViewModel.swift from guide
- [ ] Update backend URL to your computer's IP
  - Example: `http://192.168.1.100:8000`
- [ ] Build project (Cmd+B, should succeed)

### Testing
- [ ] Run app on simulator or device (Cmd+R)
- [ ] Tap "Connect" button
- [ ] Verify Mock Device connection succeeds
- [ ] Tap "Capture & Analyze" button
- [ ] Verify image displayed and AI response received
- [ ] Test error handling
- [ ] Check Console for any errors

---

## 🧪 Testing Checklist

### Basic Functionality
- [ ] App launches without crashes
- [ ] Connect button changes state correctly
- [ ] Mock Device connection succeeds
- [ ] Capture button becomes enabled after connect
- [ ] Image displays after capture
- [ ] AI response appears within 3 seconds
- [ ] Disconnect works properly
- [ ] UI updates reflect current state

### Error Scenarios
- [ ] Test with backend offline (should show error)
- [ ] Test with invalid backend URL (should show error)
- [ ] Test network disconnect during streaming
- [ ] Test repeated connect/disconnect cycles
- [ ] Test capture without connecting first
- [ ] Verify error messages are user-friendly

### Performance
- [ ] Measure end-to-end latency (capture → response)
- [ ] Target: <2 seconds
- [ ] Check memory usage (should be <200MB Android, <150MB iOS)
- [ ] Monitor battery drain (should be <10% per hour)
- [ ] Test with multiple captures in succession
- [ ] Verify no memory leaks after 10+ captures

---

## 🔒 Privacy & Compliance

### Meta Compliance
- [ ] Review Meta Wearables Developer Terms
- [ ] Review Acceptable Use Policy
- [ ] Implement user consent before camera/mic access
- [ ] Add clear disclosure of data usage
- [ ] Implement opt-out for analytics
- [ ] Test privacy controls

### SmartGlass Privacy
- [ ] Set `STORE_RAW_AUDIO=false` (default)
- [ ] Set `STORE_RAW_FRAMES=false` (default)
- [ ] Set `STORE_TRANSCRIPTS=false` (default)
- [ ] Implement "Clear Data" button in settings
- [ ] Add privacy policy link
- [ ] Test data retention controls

### Data Handling
- [ ] Verify frames not persisted by default
- [ ] Verify audio not persisted by default
- [ ] Verify transcripts not persisted by default
- [ ] Test that opt-in persistence works if needed
- [ ] Verify secure transmission (HTTPS for production)
- [ ] Document data retention policy

---

## 🚀 Production Readiness

### Real Hardware Testing
- [ ] Obtain Ray-Ban Meta glasses (when available)
- [ ] Update transport from "mock" to "ble"
- [ ] Test Bluetooth connection
- [ ] Verify camera quality and frame rate
- [ ] Test microphone quality
- [ ] Measure real-world latency
- [ ] Test battery impact on glasses
- [ ] Document any hardware-specific issues

### Performance Optimization
- [ ] Profile app with Android Profiler / Instruments
- [ ] Optimize memory usage
- [ ] Reduce network bandwidth if needed
- [ ] Implement frame skipping if performance poor
- [ ] Add adaptive quality based on network speed
- [ ] Test with poor network conditions

### User Experience
- [ ] Design onboarding flow
- [ ] Add loading states and progress indicators
- [ ] Implement helpful error messages
- [ ] Add settings screen
- [ ] Create about/help section
- [ ] Add offline mode (if applicable)
- [ ] Test with real users

### Documentation
- [ ] Write user-facing documentation
- [ ] Create video tutorial (optional)
- [ ] Document known issues
- [ ] Write troubleshooting guide for users
- [ ] Create FAQ section
- [ ] Prepare support materials

---

## 📦 Deployment

### Pre-Launch
- [ ] Complete testing on both platforms
- [ ] Verify privacy compliance
- [ ] Review app store guidelines
- [ ] Prepare marketing materials
- [ ] Create demo video
- [ ] Set up analytics (if using)

### iOS App Store
- [ ] Create App Store Connect listing
- [ ] Prepare app screenshots
- [ ] Write app description
- [ ] Set pricing/availability
- [ ] Submit for review
- [ ] Respond to review feedback

### Google Play Store
- [ ] Create Play Console listing
- [ ] Prepare app screenshots
- [ ] Write app description
- [ ] Set pricing/availability
- [ ] Submit for review
- [ ] Respond to review feedback

### Post-Launch
- [ ] Monitor crash reports
- [ ] Monitor user feedback
- [ ] Track key metrics (latency, errors, usage)
- [ ] Plan feature updates
- [ ] Maintain documentation

---

## 🎯 Success Metrics

### Technical Metrics
- [ ] End-to-end latency <2 seconds (95th percentile)
- [ ] Connection success rate >95%
- [ ] Crash-free rate >99%
- [ ] API response time <500ms (backend)
- [ ] Memory usage within targets

### User Metrics
- [ ] User satisfaction score >4.0/5.0
- [ ] Retention rate (Day 1, Day 7, Day 30)
- [ ] Feature usage statistics
- [ ] Support ticket volume
- [ ] App store rating >4.0/5.0

### Business Metrics
- [ ] Number of active users
- [ ] Usage frequency
- [ ] Feature adoption rates
- [ ] Revenue (if applicable)
- [ ] User acquisition cost

---

## 📞 Getting Help

### Documentation
- [ ] Review [Meta DAT Integration Guide](meta_dat_integration.md)
- [ ] Check [Hello SmartGlass Quickstart](hello_smartglass_quickstart.md)
- [ ] Consult [Implementation Plan](meta_dat_implementation_plan.md)
- [ ] Read [Android SDK Guide](../ANDROID_SDK.md)

### Support Channels
- [ ] Check existing GitHub issues
- [ ] Review Meta Developer Portal documentation
- [ ] Join community discussions (if available)
- [ ] Contact farmountain@gmail.com for commercial support

### Troubleshooting
- [ ] Review troubleshooting section in docs
- [ ] Check common issues in Quickstart
- [ ] Enable debug logging
- [ ] Collect device logs (Logcat/Console)
- [ ] Test with Mock Device first

---

## ✅ Final Checklist

Before considering the integration complete:

- [ ] All tests passing (unit, integration, E2E)
- [ ] Documentation complete and accurate
- [ ] Privacy controls implemented and tested
- [ ] Performance meets targets
- [ ] Error handling robust
- [ ] User experience polished
- [ ] Both platforms working (if doing both)
- [ ] Hardware tested (if available)
- [ ] Team trained on maintenance
- [ ] Monitoring/analytics in place
- [ ] Support plan ready
- [ ] Ready for production deployment

---

**Track Your Progress**: Mark items as complete using `- [x]` in markdown

**Estimated Time**: 
- MVP (Mock Device only): 1-2 weeks
- Full production (with hardware): 4-6 weeks

**Built with ❤️ for AI-powered wearables**
