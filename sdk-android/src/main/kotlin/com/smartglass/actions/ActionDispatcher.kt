package com.smartglass.actions

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.speech.tts.TextToSpeech
import android.util.Log
import android.widget.Toast
import androidx.core.app.NotificationCompat
import com.smartglass.data.SmartGlassRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

/**
 * Dispatcher for executing SmartGlassAction instances on Android.
 *
 * This class handles the execution of various action types including showing text,
 * text-to-speech, navigation, note storage, app launching, and system hints.
 *
 * @property context Android context for executing actions
 * @property textToSpeech Optional TextToSpeech instance for TTS actions
 * @property repository Optional repository for persistent storage (notes, etc.)
 */
class ActionDispatcher(
    private val context: Context,
    private val textToSpeech: TextToSpeech? = null,
    private val repository: SmartGlassRepository? = null
) {
    private val coroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    companion object {
        private const val TAG = "ActionDispatcher"
        private const val CHANNEL_ID = "smartglass_actions"
        private const val CHANNEL_NAME = "SmartGlass Actions"
        private const val NOTES_PREFS_NAME = "smartglass_notes"
        private const val NOTES_KEY = "notes_list"
        private const val NOTES_DELIMITER = "\n---\n"
        private const val DEFAULT_DESTINATION_LABEL = "Location"
    }

    init {
        // Ensure notification channel is created on initialization
        createNotificationChannel()
    }

    /**
     * Dispatch a list of SmartGlassAction instances for execution.
     *
     * Each action is executed in sequence. Exceptions are caught and logged
     * to ensure that a failure in one action doesn't prevent subsequent actions
     * from executing.
     *
     * @param actions List of SmartGlassAction instances to execute
     */
    fun dispatch(actions: List<SmartGlassAction>) {
        actions.forEach { action ->
            try {
                when (action) {
                    is SmartGlassAction.ShowText -> handleShowText(action)
                    is SmartGlassAction.TtsSpeak -> handleTtsSpeak(action)
                    is SmartGlassAction.Navigate -> handleNavigate(action)
                    is SmartGlassAction.RememberNote -> handleRememberNote(action)
                    is SmartGlassAction.OpenApp -> handleOpenApp(action)
                    is SmartGlassAction.SystemHint -> handleSystemHint(action)
                }
            } catch (e: Exception) {
                Log.w(TAG, "Failed to execute action: $action", e)
            }
        }
    }

    /**
     * Show a heads-up notification with the text content.
     *
     * Creates a notification with the title and body text, using a small icon
     * and providing tap-to-open app behavior.
     */
    private fun handleShowText(action: SmartGlassAction.ShowText) {
        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        // Create an intent to open the app when notification is tapped
        val intent = context.packageManager.getLaunchIntentForPackage(context.packageName)?.apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        val pendingIntent = intent?.let {
            val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            } else {
                PendingIntent.FLAG_UPDATE_CURRENT
            }
            PendingIntent.getActivity(context, 0, it, flags)
        }

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setContentTitle(action.title)
            .setContentText(action.body)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setAutoCancel(true)
            .apply {
                if (pendingIntent != null) {
                    setContentIntent(pendingIntent)
                }
            }
            .build()

        // Use unique ID based on content to avoid duplicate notifications
        val notificationId = java.util.Objects.hash(action.title, action.body)
        notificationManager.notify(notificationId, notification)

        Log.d(TAG, "ShowText notification displayed: ${action.title}")
    }

    /**
     * Speak text using TextToSpeech if available.
     *
     * Uses queue mode (QUEUE_ADD) to avoid interrupting ongoing speech.
     */
    private fun handleTtsSpeak(action: SmartGlassAction.TtsSpeak) {
        if (textToSpeech == null) {
            Log.w(TAG, "TtsSpeak action requested but TextToSpeech not available")
            return
        }

        val result = textToSpeech.speak(
            action.text,
            TextToSpeech.QUEUE_ADD,
            null,
            action.text.hashCode().toString()
        )

        if (result == TextToSpeech.SUCCESS) {
            Log.d(TAG, "TtsSpeak: ${action.text}")
        } else {
            Log.w(TAG, "TtsSpeak failed with result code: $result")
        }
    }

    /**
     * Navigate to a destination using Google Maps.
     *
     * If latitude and longitude are provided, uses "geo:lat,lon?q=label" format.
     * If only label is provided, uses "geo:0,0?q=label" search format.
     */
    private fun handleNavigate(action: SmartGlassAction.Navigate) {
        val geoUri = when {
            action.latitude != null && action.longitude != null -> {
                // Have coordinates
                val label = action.destinationLabel ?: DEFAULT_DESTINATION_LABEL
                Uri.parse("geo:${action.latitude},${action.longitude}?q=${Uri.encode(label)}")
            }
            action.destinationLabel != null -> {
                // Only have label, use search
                Uri.parse("geo:0,0?q=${Uri.encode(action.destinationLabel)}")
            }
            else -> {
                Log.w(TAG, "Navigate action has no destination label or coordinates")
                return
            }
        }

        val intent = Intent(Intent.ACTION_VIEW, geoUri).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }

        if (intent.resolveActivity(context.packageManager) != null) {
            context.startActivity(intent)
            Log.d(TAG, "Navigate: Launched maps with URI: $geoUri")
        } else {
            Log.w(TAG, "Navigate: No app available to handle geo URI: $geoUri")
            Toast.makeText(context, "No maps app available", Toast.LENGTH_SHORT).show()
        }
    }

    /**
     * Remember a note by saving it to the database via repository.
     *
     * If repository is available, uses persistent Room database storage.
     * Otherwise, falls back to SharedPreferences for backwards compatibility.
     */
    private fun handleRememberNote(action: SmartGlassAction.RememberNote) {
        if (repository != null) {
            // Use persistent database storage
            coroutineScope.launch {
                try {
                    val noteId = repository.saveNote(action.note)
                    Log.d(TAG, "RememberNote: Saved note #$noteId to database: ${action.note}")
                    
                    // Show confirmation notification
                    showNotification(
                        title = "Note Saved",
                        body = action.note.take(50) + if (action.note.length > 50) "..." else ""
                    )
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to save note to database", e)
                }
            }
        } else {
            // Fallback to SharedPreferences
            val prefs = context.getSharedPreferences(NOTES_PREFS_NAME, Context.MODE_PRIVATE)
            val existingNotes = prefs.getString(NOTES_KEY, "") ?: ""
            
            val newNotes = if (existingNotes.isEmpty()) {
                action.note
            } else {
                existingNotes + NOTES_DELIMITER + action.note
            }

            prefs.edit().apply {
                putString(NOTES_KEY, newNotes)
                apply() // Non-blocking write
            }

            Log.d(TAG, "RememberNote: Stored note to SharedPreferences: ${action.note}")
        }
    }
    
    /**
     * Helper to show a notification.
     */
    private fun showNotification(title: String, body: String) {
        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        
        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(body)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setAutoCancel(true)
            .build()
        
        val notificationId = java.util.Objects.hash(title, body)
        notificationManager.notify(notificationId, notification)
    }

    /**
     * Open an Android application by package name.
     *
     * Attempts to get a launch intent for the package. If the app is not installed,
     * shows a toast message to inform the user.
     */
    private fun handleOpenApp(action: SmartGlassAction.OpenApp) {
        val intent = context.packageManager.getLaunchIntentForPackage(action.packageName)

        if (intent != null) {
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
            context.startActivity(intent)
            Log.d(TAG, "OpenApp: Launched ${action.packageName}")
        } else {
            val message = "App not installed: ${action.packageName}"
            Toast.makeText(context, message, Toast.LENGTH_SHORT).show()
            Log.w(TAG, "OpenApp: $message")
        }
    }

    /**
     * Show a system hint as a short toast and log it for debugging.
     *
     * Provides subtle feedback to the user without being intrusive.
     */
    private fun handleSystemHint(action: SmartGlassAction.SystemHint) {
        Toast.makeText(context, action.hint, Toast.LENGTH_SHORT).show()
        Log.d(TAG, "SystemHint: ${action.hint}")
    }

    /**
     * Create the notification channel for Android O and above.
     *
     * This is required for showing notifications on modern Android versions.
     */
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Notifications for SmartGlass actions"
                enableLights(true)
                enableVibration(true)
            }

            val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }
}
