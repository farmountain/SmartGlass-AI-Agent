package com.smartglass.sdk

import android.content.Context
import android.content.SharedPreferences

/**
 * Privacy preferences for SmartGlass data storage.
 *
 * These preferences control what types of data the backend is allowed to temporarily store
 * during a session. All storage is in-memory and not persisted to disk by default.
 *
 * @property storeRawAudio Allow temporary storage of raw audio buffers for debugging and VAD
 * @property storeRawFrames Allow temporary storage of video frames for multimodal queries
 * @property storeTranscripts Allow storing transcripts for session history
 */
data class PrivacyPreferences(
    val storeRawAudio: Boolean = false,
    val storeRawFrames: Boolean = false,
    val storeTranscripts: Boolean = false,
) {
    companion object {
        private const val PREFS_NAME = "smartglass_privacy"
        private const val KEY_STORE_RAW_AUDIO = "store_raw_audio"
        private const val KEY_STORE_RAW_FRAMES = "store_raw_frames"
        private const val KEY_STORE_TRANSCRIPTS = "store_transcripts"

        /**
         * Load privacy preferences from SharedPreferences.
         *
         * @param context Android context
         * @return PrivacyPreferences with stored values, defaults to all false
         */
        fun load(context: Context): PrivacyPreferences {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            return PrivacyPreferences(
                storeRawAudio = prefs.getBoolean(KEY_STORE_RAW_AUDIO, false),
                storeRawFrames = prefs.getBoolean(KEY_STORE_RAW_FRAMES, false),
                storeTranscripts = prefs.getBoolean(KEY_STORE_TRANSCRIPTS, false),
            )
        }

        /**
         * Save privacy preferences to SharedPreferences.
         *
         * @param context Android context
         * @param preferences PrivacyPreferences to save
         */
        fun save(context: Context, preferences: PrivacyPreferences) {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            prefs.edit().apply {
                putBoolean(KEY_STORE_RAW_AUDIO, preferences.storeRawAudio)
                putBoolean(KEY_STORE_RAW_FRAMES, preferences.storeRawFrames)
                putBoolean(KEY_STORE_TRANSCRIPTS, preferences.storeTranscripts)
                apply()
            }
        }
    }

    /**
     * Convert preferences to a map for inclusion in session metadata.
     *
     * @return Map of privacy flags
     */
    fun toMetadata(): Map<String, Any> {
        return mapOf(
            "privacy_store_raw_audio" to storeRawAudio,
            "privacy_store_raw_frames" to storeRawFrames,
            "privacy_store_transcripts" to storeTranscripts,
        )
    }
}
