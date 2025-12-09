# Privacy Settings UI Implementation

## Overview

This document describes the privacy settings UI implementation for the SmartGlass Android SDK and sample app.

## Implementation Details

### 1. PrivacyPreferences Data Class

Location: `sdk-android/src/main/kotlin/com/smartglass/sdk/PrivacyPreferences.kt`

A data class that manages user privacy preferences with three boolean flags:
- `storeRawAudio`: Allow temporary storage of raw audio buffers
- `storeRawFrames`: Allow temporary storage of video frames
- `storeTranscripts`: Allow storing transcripts for session history

Features:
- Persists settings using SharedPreferences
- Provides `load()` and `save()` static methods
- Converts preferences to metadata map for session initialization

### 2. PrivacySettingsFragment

Location: `sdk-android/src/main/kotlin/com/smartglass/sdk/ui/PrivacySettingsFragment.kt`

A reusable Fragment that displays privacy controls:
- Three toggle switches for each privacy setting
- User-friendly explanations for each toggle
- Automatic persistence on toggle change
- Loads current preferences on creation

### 3. Layout Design

Location: `sdk-android/src/main/res/layout/fragment_privacy_settings.xml`

The layout uses a ScrollView with:
- Header with title and description
- Three sections, each containing:
  - A label and Switch in a horizontal layout
  - A description text explaining the setting
- Footer text with additional information

### 4. String Resources

Location: `sdk-android/src/main/res/values/privacy_strings.xml`

User-facing strings that explain:
- What each toggle does
- That the glasses use Meta's Wearables Device Access Toolkit
- That users can stop streaming at any time
- That all storage is in-memory only and temporary

### 5. Sample App Integration

Location: `sample/src/main/java/com/smartglass/sample/`

Changes:
- Added `PrivacySettingsActivity` to host the fragment
- Added a "Privacy Settings" button to the main activity
- Updated `SampleActivity` to load privacy preferences and pass them to `SmartGlassClient`
- Updated AndroidManifest.xml to register the new activity

### 6. Backend Integration

Location: `src/edge_runtime/server.py`

Changes:
- `/sessions` endpoint reads privacy headers (X-Privacy-Store-Raw-Audio, etc.)
- `/dat/session` endpoint extracts privacy flags from metadata
- Privacy flags are logged for future per-session configuration

## UI Flow

1. User opens the sample app
2. User taps "Privacy Settings" button
3. PrivacySettingsActivity opens with PrivacySettingsFragment
4. User sees three toggles with descriptions:
   - "Store Audio Temporarily"
   - "Store Video Frames Temporarily"
   - "Store Conversation History"
5. User adjusts toggles as desired
6. Settings are automatically saved
7. User navigates back to main screen
8. When starting a session, preferences are loaded and sent to backend

## Privacy Settings Screen Layout

```
┌─────────────────────────────────────┐
│ ← Privacy Settings                  │
├─────────────────────────────────────┤
│                                     │
│  Privacy & Data Controls            │
│  ───────────────────────            │
│  Control what data is temporarily   │
│  stored during your session. These  │
│  settings use Meta's Wearables      │
│  Device Access Toolkit for camera   │
│  and audio streaming. You can stop  │
│  streaming at any time.             │
│                                     │
│  Store Audio Temporarily      [ ○ ] │
│  When enabled, raw audio from your  │
│  glasses microphone is kept in      │
│  memory for processing and          │
│  debugging. Audio is never saved to │
│  disk and is cleared when you end   │
│  the session.                       │
│                                     │
│  Store Video Frames Temporarily     │
│                              [ ● ]  │
│  When enabled, video frames from    │
│  your glasses camera are kept in    │
│  memory for multimodal queries.     │
│  Frames are never saved to disk and │
│  are cleared when you end the       │
│  session.                           │
│                                     │
│  Store Conversation History  [ ○ ]  │
│  When enabled, text transcripts of  │
│  your conversations are kept for    │
│  session history. This helps        │
│  provide context for follow-up      │
│  questions. Transcripts are cleared │
│  when you end the session.          │
│                                     │
│  All data storage is in-memory only │
│  and automatically cleared when the │
│  session ends. No data is written   │
│  to disk or transmitted outside     │
│  your control.                      │
│                                     │
└─────────────────────────────────────┘
```

## Data Flow

### Session Initialization with Privacy Preferences

```
Android App
    │
    ├─ Load PrivacyPreferences from SharedPreferences
    │
    ├─ Create SmartGlassClient
    │
    ├─ Call startSession(privacyPreferences)
    │
    └─ SmartGlassClient adds privacy headers:
        │
        ├─ X-Privacy-Store-Raw-Audio: true/false
        ├─ X-Privacy-Store-Raw-Frames: true/false
        └─ X-Privacy-Store-Transcripts: true/false
            │
            └─ POST /sessions → Backend Server
                │
                └─ Server extracts headers and logs preferences
```

### DAT Session Initialization

```
Android App
    │
    ├─ Load PrivacyPreferences
    │
    └─ Create SessionInitRequest with metadata:
        {
          "device_id": "...",
          "client_version": "1.0.0",
          "metadata": {
            "privacy_store_raw_audio": true,
            "privacy_store_raw_frames": false,
            "privacy_store_transcripts": true
          }
        }
        │
        └─ POST /dat/session → Backend Server
            │
            └─ Server extracts metadata and applies privacy flags
```

## Testing

A unit test suite has been created at:
`sdk-android/src/test/kotlin/com/smartglass/sdk/PrivacyPreferencesTest.kt`

Tests cover:
- Default values (all false)
- Loading custom values
- Saving preferences
- Converting to metadata format

## Future Enhancements

1. **Per-Session Privacy Control**: Currently, privacy flags are logged but not applied at the session level. Future work should modify `SessionManager.create_session()` to accept and apply privacy flags per session.

2. **Privacy Dashboard**: Add a settings screen showing:
   - Current privacy settings
   - Session history (if enabled)
   - Data usage statistics

3. **Privacy Onboarding**: Show privacy settings on first launch to ensure users understand the controls.

4. **Privacy Policy Link**: Add a link to the full privacy policy for more details.

## Security Considerations

- All privacy preferences are stored locally on the device
- Preferences are sent with each session initialization
- Backend receives and logs privacy flags (future: enforce them)
- No privacy data is transmitted to third parties
- All storage is in-memory only (not written to disk)
- Session data is cleared when the session ends

## Compliance

This implementation aligns with:
- PRIVACY.md documentation
- Meta's Wearables Device Access Toolkit preview requirements
- User consent and control best practices
- Transparent data handling principles
