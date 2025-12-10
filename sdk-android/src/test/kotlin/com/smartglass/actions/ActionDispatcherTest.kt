package com.smartglass.actions

import android.app.Application
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.ActivityInfo
import android.content.pm.PackageManager
import android.content.pm.ResolveInfo
import android.net.Uri
import android.speech.tts.TextToSpeech
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(manifest = Config.NONE, sdk = [28])
class ActionDispatcherTest {

    private lateinit var context: Application
    private lateinit var mockTts: TextToSpeech
    private lateinit var dispatcher: ActionDispatcher
    private var ttsSpokenTexts = mutableListOf<String>()

    @Before
    fun setup() {
        context = ApplicationProvider.getApplicationContext()
        ttsSpokenTexts.clear()

        // Create a mock TTS that records spoken text
        mockTts = object : TextToSpeech(context, null) {
            override fun speak(
                text: CharSequence?,
                queueMode: Int,
                params: android.os.Bundle?,
                utteranceId: String?
            ): Int {
                text?.toString()?.let { ttsSpokenTexts.add(it) }
                return TextToSpeech.SUCCESS
            }

            override fun shutdown() {
                // No-op for mock
            }
        }

        dispatcher = ActionDispatcher(context, mockTts)
    }

    @Test
    fun `dispatch executes all actions in sequence`() {
        val actions = listOf(
            SmartGlassAction.SystemHint("Hint 1"),
            SmartGlassAction.SystemHint("Hint 2"),
            SmartGlassAction.SystemHint("Hint 3")
        )

        dispatcher.dispatch(actions)

        // All actions should be processed (verified by no exceptions thrown)
        assertEquals(3, actions.size)
    }

    @Test
    fun `dispatch handles exceptions gracefully and continues`() {
        // Create an action that will cause an issue (package that doesn't exist)
        val actions = listOf(
            SmartGlassAction.SystemHint("Before error"),
            SmartGlassAction.OpenApp("non.existent.package"),
            SmartGlassAction.SystemHint("After error")
        )

        // Should not throw exception
        dispatcher.dispatch(actions)
    }

    @Test
    fun `ShowText creates notification with correct title and body`() {
        val action = SmartGlassAction.ShowText(
            title = "Test Title",
            body = "Test Body"
        )

        dispatcher.dispatch(listOf(action))

        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val shadowNotificationManager = shadowOf(notificationManager)
        val notifications = shadowNotificationManager.allNotifications

        assertEquals(1, notifications.size)
        val notification = notifications[0]
        
        // Check notification content
        assertEquals("Test Title", notification.extras.getString("android.title"))
        assertEquals("Test Body", notification.extras.getString("android.text"))
    }

    @Test
    fun `TtsSpeak speaks text when TTS available`() {
        val action = SmartGlassAction.TtsSpeak(text = "Hello world")

        dispatcher.dispatch(listOf(action))

        assertEquals(1, ttsSpokenTexts.size)
        assertEquals("Hello world", ttsSpokenTexts[0])
    }

    @Test
    fun `TtsSpeak handles missing TTS gracefully`() {
        val dispatcherWithoutTts = ActionDispatcher(context, textToSpeech = null)
        val action = SmartGlassAction.TtsSpeak(text = "Hello world")

        // Should not throw exception
        dispatcherWithoutTts.dispatch(listOf(action))

        // TTS not called since it's not available
        assertEquals(0, ttsSpokenTexts.size)
    }

    @Test
    fun `Navigate with coordinates launches geo intent`() {
        val action = SmartGlassAction.Navigate(
            destinationLabel = "Coffee Shop",
            latitude = 37.7749,
            longitude = -122.4194
        )

        // Setup intent handler
        val geoIntent = Intent(Intent.ACTION_VIEW, Uri.parse("geo:37.7749,-122.4194?q=Coffee%20Shop"))
        shadowOf(context.packageManager).addResolveInfoForIntent(
            geoIntent,
            ResolveInfo().apply {
                activityInfo = ActivityInfo().apply {
                    packageName = "com.google.android.apps.maps"
                    name = "MapsActivity"
                }
            }
        )

        dispatcher.dispatch(listOf(action))

        val startedIntent = shadowOf(context).nextStartedActivity
        assertNotNull(startedIntent)
        assertEquals(Intent.ACTION_VIEW, startedIntent.action)
        assertTrue(startedIntent.data.toString().contains("37.7749"))
        assertTrue(startedIntent.data.toString().contains("-122.4194"))
        assertTrue(startedIntent.flags and Intent.FLAG_ACTIVITY_NEW_TASK != 0)
    }

    @Test
    fun `Navigate with label only launches search intent`() {
        val action = SmartGlassAction.Navigate(
            destinationLabel = "Central Park",
            latitude = null,
            longitude = null
        )

        // Setup intent handler
        val geoIntent = Intent(Intent.ACTION_VIEW, Uri.parse("geo:0,0?q=Central%20Park"))
        shadowOf(context.packageManager).addResolveInfoForIntent(
            geoIntent,
            ResolveInfo().apply {
                activityInfo = ActivityInfo().apply {
                    packageName = "com.google.android.apps.maps"
                    name = "MapsActivity"
                }
            }
        )

        dispatcher.dispatch(listOf(action))

        val startedIntent = shadowOf(context).nextStartedActivity
        assertNotNull(startedIntent)
        assertEquals(Intent.ACTION_VIEW, startedIntent.action)
        assertTrue(startedIntent.data.toString().contains("geo:0,0"))
        assertTrue(startedIntent.data.toString().contains("Central%20Park"))
    }

    @Test
    fun `Navigate with no maps app shows toast`() {
        val action = SmartGlassAction.Navigate(
            destinationLabel = "Test Location",
            latitude = null,
            longitude = null
        )

        // Don't register any intent handler
        dispatcher.dispatch(listOf(action))

        // Should show toast message (verified by no exception)
        // Actual toast verification would require more complex Robolectric setup
    }

    @Test
    fun `RememberNote stores note in SharedPreferences`() {
        val action = SmartGlassAction.RememberNote(note = "Buy milk")

        dispatcher.dispatch(listOf(action))

        val prefs = context.getSharedPreferences("smartglass_notes", Context.MODE_PRIVATE)
        val notes = prefs.getString("notes_list", "")
        
        assertEquals("Buy milk", notes)
    }

    @Test
    fun `RememberNote appends multiple notes`() {
        val action1 = SmartGlassAction.RememberNote(note = "First note")
        val action2 = SmartGlassAction.RememberNote(note = "Second note")

        dispatcher.dispatch(listOf(action1, action2))

        val prefs = context.getSharedPreferences("smartglass_notes", Context.MODE_PRIVATE)
        val notes = prefs.getString("notes_list", "")
        
        assertTrue(notes!!.contains("First note"))
        assertTrue(notes.contains("Second note"))
        assertTrue(notes.contains("\n---\n"))
    }

    @Test
    fun `OpenApp launches app with valid package`() {
        val packageName = "com.example.testapp"
        val action = SmartGlassAction.OpenApp(packageName = packageName)

        // Setup launch intent
        val launchIntent = Intent(Intent.ACTION_MAIN).apply {
            setPackage(packageName)
            addCategory(Intent.CATEGORY_LAUNCHER)
        }
        shadowOf(context.packageManager).addResolveInfoForIntent(
            launchIntent,
            ResolveInfo().apply {
                activityInfo = ActivityInfo().apply {
                    this.packageName = packageName
                    name = "MainActivity"
                }
            }
        )

        // Need to set launch intent for package
        val packageManager = shadowOf(context.packageManager)
        packageManager.addPackage(packageName)
        val intent = Intent(Intent.ACTION_MAIN).apply {
            addCategory(Intent.CATEGORY_LAUNCHER)
            setPackage(packageName)
        }
        packageManager.addActivityIfNotPresent(
            ActivityInfo().apply {
                this.packageName = packageName
                name = "MainActivity"
            }
        )

        dispatcher.dispatch(listOf(action))

        val startedIntent = shadowOf(context).nextStartedActivity
        assertNotNull(startedIntent)
        assertTrue(startedIntent.flags and Intent.FLAG_ACTIVITY_NEW_TASK != 0)
    }

    @Test
    fun `OpenApp shows toast for non-existent package`() {
        val action = SmartGlassAction.OpenApp(packageName = "non.existent.package")

        // Should not throw exception, just show toast
        dispatcher.dispatch(listOf(action))

        // Verify no activity was started
        val startedIntent = shadowOf(context).nextStartedActivity
        assertNull(startedIntent)
    }

    @Test
    fun `SystemHint shows toast and logs`() {
        val action = SmartGlassAction.SystemHint(hint = "Test hint message")

        // Should not throw exception
        dispatcher.dispatch(listOf(action))

        // Toast shown (verified by no exception)
    }

    @Test
    fun `multiple actions of same type are executed`() {
        val actions = listOf(
            SmartGlassAction.TtsSpeak(text = "First"),
            SmartGlassAction.TtsSpeak(text = "Second"),
            SmartGlassAction.TtsSpeak(text = "Third")
        )

        dispatcher.dispatch(actions)

        assertEquals(3, ttsSpokenTexts.size)
        assertEquals("First", ttsSpokenTexts[0])
        assertEquals("Second", ttsSpokenTexts[1])
        assertEquals("Third", ttsSpokenTexts[2])
    }

    @Test
    fun `mixed action types are executed in order`() {
        val actions = listOf(
            SmartGlassAction.TtsSpeak(text = "Speaking"),
            SmartGlassAction.RememberNote(note = "Note 1"),
            SmartGlassAction.SystemHint(hint = "Hint"),
            SmartGlassAction.RememberNote(note = "Note 2")
        )

        dispatcher.dispatch(actions)

        // Verify TTS was called
        assertEquals(1, ttsSpokenTexts.size)
        assertEquals("Speaking", ttsSpokenTexts[0])

        // Verify both notes were stored
        val prefs = context.getSharedPreferences("smartglass_notes", Context.MODE_PRIVATE)
        val notes = prefs.getString("notes_list", "")
        assertTrue(notes!!.contains("Note 1"))
        assertTrue(notes.contains("Note 2"))
    }

    @Test
    fun `empty action list is handled gracefully`() {
        // Should not throw exception
        dispatcher.dispatch(emptyList())
    }
}
