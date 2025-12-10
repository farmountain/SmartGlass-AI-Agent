package com.smartglass.runtime.llm

import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class SnnPromptBuilderTest {
    
    @Test
    fun buildPromptWithBothQueryAndContext() {
        val query = "What do you see?"
        val context = "A red car parked on the street"
        
        val prompt = SnnPromptBuilder.buildStructuredPrompt(query, context)
        
        // Verify system instructions are present
        assertTrue(prompt.contains("SYSTEM: You are a helpful assistant"))
        assertTrue(prompt.contains("strict JSON format"))
        assertTrue(prompt.contains("{\"response\":"))
        assertTrue(prompt.contains("\"actions\":"))
        
        // Verify action type descriptions are present
        assertTrue(prompt.contains("Available actions:"))
        assertTrue(prompt.contains("SHOW_TEXT"))
        assertTrue(prompt.contains("TTS_SPEAK"))
        assertTrue(prompt.contains("NAVIGATE"))
        assertTrue(prompt.contains("REMEMBER_NOTE"))
        assertTrue(prompt.contains("OPEN_APP"))
        assertTrue(prompt.contains("SYSTEM_HINT"))
        
        // Verify visual context is included
        assertTrue(prompt.contains("VISUAL_CONTEXT: $context"))
        
        // Verify user query is included
        assertTrue(prompt.contains("USER: $query"))
        
        // Verify final instruction
        assertTrue(prompt.contains("ASSISTANT:"))
    }
    
    @Test
    fun buildPromptWithQueryOnly() {
        val query = "Tell me a joke"
        
        val prompt = SnnPromptBuilder.buildStructuredPrompt(query, null)
        
        // Should have system instructions
        assertTrue(prompt.contains("SYSTEM:"))
        assertTrue(prompt.contains("Available actions:"))
        
        // Should NOT have visual context section
        assertTrue(!prompt.contains("VISUAL_CONTEXT:"))
        
        // Should have user query
        assertTrue(prompt.contains("USER: $query"))
        
        // Should have final instruction
        assertTrue(prompt.contains("ASSISTANT:"))
    }
    
    @Test
    fun buildPromptWithContextOnly() {
        val context = "A person holding a coffee cup"
        
        val prompt = SnnPromptBuilder.buildStructuredPrompt(null, context)
        
        // Should have system instructions
        assertTrue(prompt.contains("SYSTEM:"))
        
        // Should have visual context
        assertTrue(prompt.contains("VISUAL_CONTEXT: $context"))
        
        // Should NOT have explicit user query, but context serves as input
        assertTrue(!prompt.contains("USER:"))
        
        // Should have final instruction
        assertTrue(prompt.contains("ASSISTANT:"))
    }
    
    @Test
    fun buildPromptWithNullInputs() {
        val prompt = SnnPromptBuilder.buildStructuredPrompt(null, null)
        
        // Should have system instructions
        assertTrue(prompt.contains("SYSTEM:"))
        
        // Should have default user query when both are null
        assertTrue(prompt.contains("USER: Hello"))
        
        // Should NOT have visual context
        assertTrue(!prompt.contains("VISUAL_CONTEXT:"))
        
        // Should have final instruction
        assertTrue(prompt.contains("ASSISTANT:"))
    }
    
    @Test
    fun buildPromptWithEmptyStrings() {
        val prompt = SnnPromptBuilder.buildStructuredPrompt("", "")
        
        // Empty strings should be treated as null/blank
        assertTrue(prompt.contains("SYSTEM:"))
        assertTrue(prompt.contains("USER: Hello"))
        assertTrue(!prompt.contains("VISUAL_CONTEXT:"))
        assertTrue(prompt.contains("ASSISTANT:"))
    }
    
    @Test
    fun buildPromptWithBlankStrings() {
        val prompt = SnnPromptBuilder.buildStructuredPrompt("   ", "   ")
        
        // Blank strings should be treated as null/blank
        assertTrue(prompt.contains("SYSTEM:"))
        assertTrue(prompt.contains("USER: Hello"))
        assertTrue(!prompt.contains("VISUAL_CONTEXT:"))
        assertTrue(prompt.contains("ASSISTANT:"))
    }
    
    @Test
    fun verifyAllActionTypesDescribed() {
        val prompt = SnnPromptBuilder.buildStructuredPrompt("test", null)
        
        // Verify all 6 action types are described with their payloads
        assertTrue(prompt.contains("SHOW_TEXT") && prompt.contains("title, body"))
        assertTrue(prompt.contains("TTS_SPEAK") && prompt.contains("text"))
        assertTrue(prompt.contains("NAVIGATE") && prompt.contains("destinationLabel"))
        assertTrue(prompt.contains("REMEMBER_NOTE") && prompt.contains("note"))
        assertTrue(prompt.contains("OPEN_APP") && prompt.contains("packageName"))
        assertTrue(prompt.contains("SYSTEM_HINT") && prompt.contains("hint"))
    }
    
    @Test
    fun verifyPromptStructureOrder() {
        val query = "What's the weather?"
        val context = "Sunny outside"
        
        val prompt = SnnPromptBuilder.buildStructuredPrompt(query, context)
        
        // Verify the order of sections
        val systemIndex = prompt.indexOf("SYSTEM:")
        val actionsIndex = prompt.indexOf("Available actions:")
        val contextIndex = prompt.indexOf("VISUAL_CONTEXT:")
        val userIndex = prompt.indexOf("USER:")
        val assistantIndex = prompt.indexOf("ASSISTANT:")
        
        // System should come first
        assertTrue(systemIndex >= 0)
        
        // Actions description should come after system
        assertTrue(actionsIndex > systemIndex)
        
        // Visual context should come after actions
        assertTrue(contextIndex > actionsIndex)
        
        // User query should come after visual context
        assertTrue(userIndex > contextIndex)
        
        // Assistant should come last
        assertTrue(assistantIndex > userIndex)
    }
    
    @Test
    fun verifyPromptIsCompact() {
        val query = "Test query"
        val context = "Test context"
        
        val prompt = SnnPromptBuilder.buildStructuredPrompt(query, context)
        
        // Prompt should be reasonably sized for a small student model
        // Not too long (arbitrary threshold of 1000 characters for basic inputs)
        assertTrue(prompt.length < 1000, "Prompt should be compact: ${prompt.length} characters")
        
        // Should not have excessive whitespace
        val lines = prompt.split("\n")
        assertTrue(lines.size < 15, "Prompt should not have excessive line breaks")
    }
    
    @Test
    fun verifyJSONFormatInstructions() {
        val prompt = SnnPromptBuilder.buildStructuredPrompt("test", null)
        
        // Should explicitly mention the JSON structure expected
        assertTrue(prompt.contains("\"response\":"))
        assertTrue(prompt.contains("\"actions\":"))
        assertTrue(prompt.contains("\"type\":"))
        assertTrue(prompt.contains("\"payload\":"))
    }
}
