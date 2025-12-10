package com.smartglass.actions

import android.util.Log
import com.squareup.moshi.JsonAdapter
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory

/**
 * Sealed class representing strongly-typed actions that can be executed by SmartGlass.
 *
 * Each subtype has a well-defined payload structure, making action handling type-safe
 * and eliminating the need for runtime type checking of payload maps.
 *
 * Actions can be parsed from JSON using the companion object's [fromJsonArray] function.
 */
sealed class SmartGlassAction {
    
    /**
     * Display text content to the user.
     *
     * @property title The title or heading of the text to display
     * @property body The main body content to display
     */
    data class ShowText(
        val title: String,
        val body: String,
    ) : SmartGlassAction()
    
    /**
     * Speak text using text-to-speech (TTS).
     *
     * @property text The text content to be spoken aloud
     */
    data class TtsSpeak(
        val text: String,
    ) : SmartGlassAction()
    
    /**
     * Navigate to a destination using GPS coordinates or a location label.
     *
     * Either destinationLabel OR both latitude and longitude should be provided.
     *
     * @property destinationLabel Human-readable destination name (e.g., "Coffee Shop")
     * @property latitude GPS latitude coordinate (decimal degrees)
     * @property longitude GPS longitude coordinate (decimal degrees)
     */
    data class Navigate(
        val destinationLabel: String?,
        val latitude: Double?,
        val longitude: Double?,
    ) : SmartGlassAction()
    
    /**
     * Store a note for later retrieval.
     *
     * @property note The text content to remember
     */
    data class RememberNote(
        val note: String,
    ) : SmartGlassAction()
    
    /**
     * Open an Android application by package name.
     *
     * @property packageName The Android package name (e.g., "com.spotify.music")
     */
    data class OpenApp(
        val packageName: String,
    ) : SmartGlassAction()
    
    /**
     * Provide a system-level hint or suggestion to the user.
     *
     * @property hint The hint text to display or communicate
     */
    data class SystemHint(
        val hint: String,
    ) : SmartGlassAction()

    companion object {
        private const val TAG = "SmartGlassAction"
        
        /**
         * Parse a JSON array of actions into a list of [SmartGlassAction] instances.
         *
         * Expected JSON format:
         * ```json
         * [
         *   {
         *     "type": "SHOW_TEXT",
         *     "payload": {
         *       "title": "Hello",
         *       "body": "World"
         *     }
         *   },
         *   {
         *     "type": "TTS_SPEAK",
         *     "payload": {
         *       "text": "Hello there"
         *     }
         *   }
         * ]
         * ```
         *
         * Unknown action types are ignored with a warning logged.
         *
         * @param json JSON string containing an array of action objects
         * @return List of parsed [SmartGlassAction] instances (may be empty)
         */
        fun fromJsonArray(json: String): List<SmartGlassAction> {
            val moshi = Moshi.Builder()
                .add(KotlinJsonAdapterFactory())
                .build()
            
            // Parse as List<Map<String, Any>>
            val listOfMapsType = Types.newParameterizedType(
                List::class.java,
                Types.newParameterizedType(
                    Map::class.java,
                    String::class.java,
                    Any::class.java
                )
            )
            val adapter: JsonAdapter<List<Map<String, Any>>> = moshi.adapter(listOfMapsType)
            
            val actionMaps = try {
                adapter.fromJson(json) ?: emptyList()
            } catch (e: Exception) {
                Log.w(TAG, "Failed to parse JSON array: ${e.message}")
                return emptyList()
            }
            
            return actionMaps.mapNotNull { actionMap ->
                parseAction(actionMap)
            }
        }
        
        private fun parseAction(actionMap: Map<String, Any>): SmartGlassAction? {
            val type = (actionMap["type"] as? String)?.uppercase() ?: run {
                Log.w(TAG, "Action missing 'type' field: $actionMap")
                return null
            }
            
            val payload = actionMap["payload"] as? Map<*, *> ?: run {
                Log.w(TAG, "Action '$type' missing 'payload' field: $actionMap")
                return null
            }
            
            return when (type) {
                "SHOW_TEXT" -> {
                    val title = payload["title"] as? String
                    val body = payload["body"] as? String
                    if (title != null && body != null) {
                        ShowText(title, body)
                    } else {
                        Log.w(TAG, "SHOW_TEXT action missing required fields (title, body): $payload")
                        null
                    }
                }
                
                "TTS_SPEAK" -> {
                    val text = payload["text"] as? String
                    if (text != null) {
                        TtsSpeak(text)
                    } else {
                        Log.w(TAG, "TTS_SPEAK action missing required field 'text': $payload")
                        null
                    }
                }
                
                "NAVIGATE" -> {
                    val destinationLabel = payload["destinationLabel"] as? String
                    val latitude = (payload["latitude"] as? Number)?.toDouble()
                    val longitude = (payload["longitude"] as? Number)?.toDouble()
                    
                    // At least one form of destination should be provided
                    if (destinationLabel != null || (latitude != null && longitude != null)) {
                        Navigate(destinationLabel, latitude, longitude)
                    } else {
                        Log.w(TAG, "NAVIGATE action missing destination information: $payload")
                        null
                    }
                }
                
                "REMEMBER_NOTE" -> {
                    val note = payload["note"] as? String
                    if (note != null) {
                        RememberNote(note)
                    } else {
                        Log.w(TAG, "REMEMBER_NOTE action missing required field 'note': $payload")
                        null
                    }
                }
                
                "OPEN_APP" -> {
                    val packageName = payload["packageName"] as? String
                    if (packageName != null) {
                        OpenApp(packageName)
                    } else {
                        Log.w(TAG, "OPEN_APP action missing required field 'packageName': $payload")
                        null
                    }
                }
                
                "SYSTEM_HINT" -> {
                    val hint = payload["hint"] as? String
                    if (hint != null) {
                        SystemHint(hint)
                    } else {
                        Log.w(TAG, "SYSTEM_HINT action missing required field 'hint': $payload")
                        null
                    }
                }
                
                else -> {
                    Log.w(TAG, "Unknown action type: $type")
                    null
                }
            }
        }
    }
}
