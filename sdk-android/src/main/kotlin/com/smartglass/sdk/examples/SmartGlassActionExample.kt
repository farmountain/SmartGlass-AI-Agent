package com.smartglass.sdk.examples

import android.content.Context
import com.smartglass.actions.SmartGlassAction

/**
 * Example demonstrating how to use the SmartGlassAction sealed class
 * for type-safe action parsing and execution.
 */
object SmartGlassActionExample {
    
    /**
     * Parse actions from a JSON response and execute them with type safety.
     *
     * @param jsonResponse JSON array string from the agent
     * @param context Android context for executing actions
     */
    fun parseAndExecuteActions(jsonResponse: String, context: Context) {
        // Parse JSON into strongly-typed actions
        val actions = SmartGlassAction.fromJsonArray(jsonResponse)
        
        // Handle each action with exhaustive type checking
        actions.forEach { action ->
            when (action) {
                is SmartGlassAction.ShowText -> {
                    // Type-safe access to title and body
                    println("Showing text: ${action.title} - ${action.body}")
                    // TODO: Display in UI
                }
                
                is SmartGlassAction.TtsSpeak -> {
                    // Type-safe access to text
                    println("Speaking: ${action.text}")
                    // TODO: Use Android TTS
                }
                
                is SmartGlassAction.Navigate -> {
                    // Type-safe access to navigation parameters
                    if (action.destinationLabel != null) {
                        println("Navigating to: ${action.destinationLabel}")
                    } else if (action.latitude != null && action.longitude != null) {
                        println("Navigating to coordinates: ${action.latitude}, ${action.longitude}")
                    }
                    // TODO: Launch navigation intent
                }
                
                is SmartGlassAction.RememberNote -> {
                    // Type-safe access to note
                    println("Remembering note: ${action.note}")
                    // TODO: Store in local database
                }
                
                is SmartGlassAction.OpenApp -> {
                    // Type-safe access to package name
                    println("Opening app: ${action.packageName}")
                    // TODO: Launch app with intent
                }
                
                is SmartGlassAction.SystemHint -> {
                    // Type-safe access to hint
                    println("System hint: ${action.hint}")
                    // TODO: Show subtle UI hint
                }
            }
        }
    }
    
    /**
     * Example showing type-safe filtering of actions.
     */
    fun filterNavigationActions(jsonResponse: String): List<SmartGlassAction.Navigate> {
        val actions = SmartGlassAction.fromJsonArray(jsonResponse)
        // Type-safe filtering
        return actions.filterIsInstance<SmartGlassAction.Navigate>()
    }
    
    /**
     * Example JSON response that would be parsed by SmartGlassAction.
     */
    fun exampleJsonResponse(): String {
        return """
            [
                {
                    "type": "SHOW_TEXT",
                    "payload": {
                        "title": "Weather Update",
                        "body": "It's sunny today with a high of 75°F"
                    }
                },
                {
                    "type": "TTS_SPEAK",
                    "payload": {
                        "text": "The weather is sunny today"
                    }
                },
                {
                    "type": "NAVIGATE",
                    "payload": {
                        "destinationLabel": "Nearest Coffee Shop",
                        "latitude": 37.7749,
                        "longitude": -122.4194
                    }
                }
            ]
        """.trimIndent()
    }
}
