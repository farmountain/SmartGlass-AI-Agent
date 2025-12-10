package com.smartglass.runtime.llm

/**
 * Utility object for constructing structured prompts for the SNN (Student Neural Network) model.
 * 
 * Prompts are designed to instruct the SNN to emit structured JSON responses with:
 * - A natural language response field
 * - An array of actions to execute
 * 
 * This approach enables reliable parsing and action execution while keeping prompts
 * optimized for small student models.
 */
object SnnPromptBuilder {
    
    /**
     * Build a structured prompt that instructs the SNN model to respond in JSON format.
     * 
     * The prompt includes:
     * - System instructions for strict JSON format
     * - Descriptions of available action types
     * - Visual context (if provided)
     * - User query (if provided)
     * - Final instruction to emit valid JSON
     * 
     * Example output format:
     * ```json
     * {
     *   "response": "natural language answer to the user",
     *   "actions": [
     *     { "type": "...", "payload": { ... } }
     *   ]
     * }
     * ```
     * 
     * @param userQuery Optional text query from the user
     * @param visualContext Optional visual context description
     * @return Formatted prompt string optimized for SNN inference
     */
    fun buildStructuredPrompt(
        userQuery: String?,
        visualContext: String?
    ): String {
        val prompt = StringBuilder()
        
        // System instructions for JSON output
        prompt.append("SYSTEM: You are a helpful assistant. ")
        prompt.append("Always reply in strict JSON format: ")
        prompt.append("{\"response\": \"natural language answer\", \"actions\": [{\"type\": \"ACTION_TYPE\", \"payload\": {...}}]}. ")
        
        // Action type descriptions
        prompt.append("Available actions: ")
        prompt.append("SHOW_TEXT (payload: title, body) - display text; ")
        prompt.append("TTS_SPEAK (payload: text) - speak aloud; ")
        prompt.append("NAVIGATE (payload: destinationLabel or latitude+longitude) - navigate to location; ")
        prompt.append("REMEMBER_NOTE (payload: note) - save a note; ")
        prompt.append("OPEN_APP (payload: packageName) - open an app; ")
        prompt.append("SYSTEM_HINT (payload: hint) - provide a system hint. ")
        
        // Visual context section
        if (!visualContext.isNullOrBlank()) {
            prompt.append("\n\nVISUAL_CONTEXT: ")
            prompt.append(visualContext)
        }
        
        // User query section
        if (!userQuery.isNullOrBlank()) {
            prompt.append("\n\nUSER: ")
            prompt.append(userQuery)
        } else if (visualContext.isNullOrBlank()) {
            // If neither query nor context provided, use a default
            prompt.append("\n\nUSER: Hello")
        }
        
        // Final instruction
        prompt.append("\n\nASSISTANT: ")
        
        return prompt.toString()
    }
}
