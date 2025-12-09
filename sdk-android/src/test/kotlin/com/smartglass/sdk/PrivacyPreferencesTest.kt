package com.smartglass.sdk

import android.content.Context
import android.content.SharedPreferences
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.mockito.Mock
import org.mockito.Mockito.*
import org.mockito.junit.MockitoJUnitRunner

/**
 * Unit tests for PrivacyPreferences.
 */
@RunWith(MockitoJUnitRunner::class)
class PrivacyPreferencesTest {

    @Mock
    private lateinit var mockContext: Context

    @Mock
    private lateinit var mockSharedPrefs: SharedPreferences

    @Mock
    private lateinit var mockEditor: SharedPreferences.Editor

    @Before
    fun setup() {
        `when`(mockContext.getSharedPreferences("smartglass_privacy", Context.MODE_PRIVATE))
            .thenReturn(mockSharedPrefs)
        `when`(mockSharedPrefs.edit()).thenReturn(mockEditor)
        `when`(mockEditor.putBoolean(anyString(), anyBoolean())).thenReturn(mockEditor)
    }

    @Test
    fun testDefaultValues() {
        // Given default preferences (all false)
        `when`(mockSharedPrefs.getBoolean(anyString(), anyBoolean())).thenReturn(false)

        // When loading preferences
        val prefs = PrivacyPreferences.load(mockContext)

        // Then all values should be false
        assertFalse(prefs.storeRawAudio)
        assertFalse(prefs.storeRawFrames)
        assertFalse(prefs.storeTranscripts)
    }

    @Test
    fun testLoadWithCustomValues() {
        // Given custom preferences
        `when`(mockSharedPrefs.getBoolean("store_raw_audio", false)).thenReturn(true)
        `when`(mockSharedPrefs.getBoolean("store_raw_frames", false)).thenReturn(false)
        `when`(mockSharedPrefs.getBoolean("store_transcripts", false)).thenReturn(true)

        // When loading preferences
        val prefs = PrivacyPreferences.load(mockContext)

        // Then values should match stored preferences
        assertTrue(prefs.storeRawAudio)
        assertFalse(prefs.storeRawFrames)
        assertTrue(prefs.storeTranscripts)
    }

    @Test
    fun testSavePreferences() {
        // Given privacy preferences
        val prefs = PrivacyPreferences(
            storeRawAudio = true,
            storeRawFrames = false,
            storeTranscripts = true
        )

        // When saving preferences
        PrivacyPreferences.save(mockContext, prefs)

        // Then editor should be called with correct values
        verify(mockEditor).putBoolean("store_raw_audio", true)
        verify(mockEditor).putBoolean("store_raw_frames", false)
        verify(mockEditor).putBoolean("store_transcripts", true)
        verify(mockEditor).apply()
    }

    @Test
    fun testToMetadata() {
        // Given privacy preferences
        val prefs = PrivacyPreferences(
            storeRawAudio = true,
            storeRawFrames = false,
            storeTranscripts = true
        )

        // When converting to metadata
        val metadata = prefs.toMetadata()

        // Then metadata should contain correct keys and values
        assertEquals(3, metadata.size)
        assertEquals(true, metadata["privacy_store_raw_audio"])
        assertEquals(false, metadata["privacy_store_raw_frames"])
        assertEquals(true, metadata["privacy_store_transcripts"])
    }
}
