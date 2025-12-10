package com.smartglass.actions

import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

class SmartGlassActionTest {
    
    @Test
    fun parseShowTextAction() {
        val json = """
            [
                {
                    "type": "SHOW_TEXT",
                    "payload": {
                        "title": "Welcome",
                        "body": "Hello, world!"
                    }
                }
            ]
        """.trimIndent()
        
        val actions = SmartGlassAction.fromJsonArray(json)
        
        assertEquals(1, actions.size)
        val action = actions[0]
        assertIs<SmartGlassAction.ShowText>(action)
        assertEquals("Welcome", action.title)
        assertEquals("Hello, world!", action.body)
    }
    
    @Test
    fun parseTtsSpeakAction() {
        val json = """
            [
                {
                    "type": "TTS_SPEAK",
                    "payload": {
                        "text": "This is a test message"
                    }
                }
            ]
        """.trimIndent()
        
        val actions = SmartGlassAction.fromJsonArray(json)
        
        assertEquals(1, actions.size)
        val action = actions[0]
        assertIs<SmartGlassAction.TtsSpeak>(action)
        assertEquals("This is a test message", action.text)
    }
    
    @Test
    fun parseNavigateActionWithLabel() {
        val json = """
            [
                {
                    "type": "NAVIGATE",
                    "payload": {
                        "destinationLabel": "Coffee Shop"
                    }
                }
            ]
        """.trimIndent()
        
        val actions = SmartGlassAction.fromJsonArray(json)
        
        assertEquals(1, actions.size)
        val action = actions[0]
        assertIs<SmartGlassAction.Navigate>(action)
        assertEquals("Coffee Shop", action.destinationLabel)
        assertEquals(null, action.latitude)
        assertEquals(null, action.longitude)
    }
    
    @Test
    fun parseNavigateActionWithCoordinates() {
        val json = """
            [
                {
                    "type": "NAVIGATE",
                    "payload": {
                        "latitude": 37.7749,
                        "longitude": -122.4194
                    }
                }
            ]
        """.trimIndent()
        
        val actions = SmartGlassAction.fromJsonArray(json)
        
        assertEquals(1, actions.size)
        val action = actions[0]
        assertIs<SmartGlassAction.Navigate>(action)
        assertEquals(null, action.destinationLabel)
        assertEquals(37.7749, action.latitude)
        assertEquals(-122.4194, action.longitude)
    }
    
    @Test
    fun parseNavigateActionWithBothLabelAndCoordinates() {
        val json = """
            [
                {
                    "type": "NAVIGATE",
                    "payload": {
                        "destinationLabel": "Golden Gate Bridge",
                        "latitude": 37.8199,
                        "longitude": -122.4783
                    }
                }
            ]
        """.trimIndent()
        
        val actions = SmartGlassAction.fromJsonArray(json)
        
        assertEquals(1, actions.size)
        val action = actions[0]
        assertIs<SmartGlassAction.Navigate>(action)
        assertEquals("Golden Gate Bridge", action.destinationLabel)
        assertEquals(37.8199, action.latitude)
        assertEquals(-122.4783, action.longitude)
    }
    
    @Test
    fun parseRememberNoteAction() {
        val json = """
            [
                {
                    "type": "REMEMBER_NOTE",
                    "payload": {
                        "note": "Buy milk on the way home"
                    }
                }
            ]
        """.trimIndent()
        
        val actions = SmartGlassAction.fromJsonArray(json)
        
        assertEquals(1, actions.size)
        val action = actions[0]
        assertIs<SmartGlassAction.RememberNote>(action)
        assertEquals("Buy milk on the way home", action.note)
    }
    
    @Test
    fun parseOpenAppAction() {
        val json = """
            [
                {
                    "type": "OPEN_APP",
                    "payload": {
                        "packageName": "com.spotify.music"
                    }
                }
            ]
        """.trimIndent()
        
        val actions = SmartGlassAction.fromJsonArray(json)
        
        assertEquals(1, actions.size)
        val action = actions[0]
        assertIs<SmartGlassAction.OpenApp>(action)
        assertEquals("com.spotify.music", action.packageName)
    }
    
    @Test
    fun parseSystemHintAction() {
        val json = """
            [
                {
                    "type": "SYSTEM_HINT",
                    "payload": {
                        "hint": "Battery low, please charge soon"
                    }
                }
            ]
        """.trimIndent()
        
        val actions = SmartGlassAction.fromJsonArray(json)
        
        assertEquals(1, actions.size)
        val action = actions[0]
        assertIs<SmartGlassAction.SystemHint>(action)
        assertEquals("Battery low, please charge soon", action.hint)
    }
    
    @Test
    fun parseMultipleActions() {
        val json = """
            [
                {
                    "type": "SHOW_TEXT",
                    "payload": {
                        "title": "Notification",
                        "body": "Message received"
                    }
                },
                {
                    "type": "TTS_SPEAK",
                    "payload": {
                        "text": "You have a new message"
                    }
                },
                {
                    "type": "SYSTEM_HINT",
                    "payload": {
                        "hint": "Swipe to read"
                    }
                }
            ]
        """.trimIndent()
        
        val actions = SmartGlassAction.fromJsonArray(json)
        
        assertEquals(3, actions.size)
        assertIs<SmartGlassAction.ShowText>(actions[0])
        assertIs<SmartGlassAction.TtsSpeak>(actions[1])
        assertIs<SmartGlassAction.SystemHint>(actions[2])
    }
    
    @Test
    fun ignoresUnknownActionType() {
        val json = """
            [
                {
                    "type": "SHOW_TEXT",
                    "payload": {
                        "title": "Valid",
                        "body": "Action"
                    }
                },
                {
                    "type": "UNKNOWN_ACTION",
                    "payload": {
                        "someField": "someValue"
                    }
                },
                {
                    "type": "TTS_SPEAK",
                    "payload": {
                        "text": "Another valid action"
                    }
                }
            ]
        """.trimIndent()
        
        val actions = SmartGlassAction.fromJsonArray(json)
        
        // Should only parse the known actions, ignoring the unknown one
        assertEquals(2, actions.size)
        assertIs<SmartGlassAction.ShowText>(actions[0])
        assertIs<SmartGlassAction.TtsSpeak>(actions[1])
    }
    
    @Test
    fun handlesInvalidJsonGracefully() {
        val json = "not valid json at all"
        
        val actions = SmartGlassAction.fromJsonArray(json)
        
        // Should return empty list without crashing
        assertEquals(0, actions.size)
    }
    
    @Test
    fun handlesEmptyArray() {
        val json = "[]"
        
        val actions = SmartGlassAction.fromJsonArray(json)
        
        assertEquals(0, actions.size)
    }
    
    @Test
    fun handlesMissingTypeField() {
        val json = """
            [
                {
                    "payload": {
                        "title": "Test",
                        "body": "Missing type field"
                    }
                }
            ]
        """.trimIndent()
        
        val actions = SmartGlassAction.fromJsonArray(json)
        
        // Should skip the action with missing type
        assertEquals(0, actions.size)
    }
    
    @Test
    fun handlesMissingPayloadField() {
        val json = """
            [
                {
                    "type": "SHOW_TEXT"
                }
            ]
        """.trimIndent()
        
        val actions = SmartGlassAction.fromJsonArray(json)
        
        // Should skip the action with missing payload
        assertEquals(0, actions.size)
    }
    
    @Test
    fun handlesMissingRequiredFieldsInPayload() {
        val json = """
            [
                {
                    "type": "SHOW_TEXT",
                    "payload": {
                        "title": "Only title"
                    }
                },
                {
                    "type": "TTS_SPEAK",
                    "payload": {}
                }
            ]
        """.trimIndent()
        
        val actions = SmartGlassAction.fromJsonArray(json)
        
        // Both actions are missing required fields, should be skipped
        assertEquals(0, actions.size)
    }
    
    @Test
    fun handlesCaseInsensitiveActionTypes() {
        val json = """
            [
                {
                    "type": "show_text",
                    "payload": {
                        "title": "Test",
                        "body": "Lowercase type"
                    }
                },
                {
                    "type": "tts_speak",
                    "payload": {
                        "text": "Mixed case"
                    }
                }
            ]
        """.trimIndent()
        
        val actions = SmartGlassAction.fromJsonArray(json)
        
        // Should handle case-insensitive type names
        assertEquals(2, actions.size)
        assertIs<SmartGlassAction.ShowText>(actions[0])
        assertIs<SmartGlassAction.TtsSpeak>(actions[1])
    }
    
    @Test
    fun handlesNavigateWithMissingCoordinates() {
        val json = """
            [
                {
                    "type": "NAVIGATE",
                    "payload": {
                        "latitude": 37.7749
                    }
                }
            ]
        """.trimIndent()
        
        val actions = SmartGlassAction.fromJsonArray(json)
        
        // NAVIGATE requires either label OR both lat/lon, not just one coordinate
        assertEquals(0, actions.size)
    }
    
    @Test
    fun handlesNumericTypesForCoordinates() {
        val json = """
            [
                {
                    "type": "NAVIGATE",
                    "payload": {
                        "latitude": 37,
                        "longitude": -122
                    }
                }
            ]
        """.trimIndent()
        
        val actions = SmartGlassAction.fromJsonArray(json)
        
        assertEquals(1, actions.size)
        val action = actions[0]
        assertIs<SmartGlassAction.Navigate>(action)
        assertEquals(37.0, action.latitude)
        assertEquals(-122.0, action.longitude)
    }
}
