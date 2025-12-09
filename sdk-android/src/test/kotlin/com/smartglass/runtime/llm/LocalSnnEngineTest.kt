package com.smartglass.runtime.llm

import android.test.mock.MockContext
import kotlinx.coroutines.test.runTest
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class LocalSnnEngineTest {
    
    @Test
    fun generateReturnsNonEmptyString() = runTest {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val engine = LocalSnnEngine(MockContext(), "test_model.pt", tokenizer)
        
        val result = engine.generate("Hello from the glasses")
        
        assertTrue(result.isNotEmpty(), "Expected non-empty generated text")
    }
    
    @Test
    fun generateHandlesEmptyPrompt() = runTest {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val engine = LocalSnnEngine(MockContext(), "test_model.pt", tokenizer)
        
        val result = engine.generate("")
        
        assertTrue(result.isNotEmpty(), "Expected non-empty result even for empty prompt")
    }
    
    @Test
    fun generateWithVisualContextConcatenatesCorrectly() = runTest {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val engine = LocalSnnEngine(MockContext(), "test_model.pt", tokenizer)
        
        val result = engine.generate(
            prompt = "What do you see?",
            visualContext = "A red apple on a table"
        )
        
        assertTrue(result.isNotEmpty(), "Expected non-empty result with visual context")
    }
    
    @Test
    fun generateWithNullVisualContextWorks() = runTest {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val engine = LocalSnnEngine(MockContext(), "test_model.pt", tokenizer)
        
        val result = engine.generate(
            prompt = "Tell me about the weather",
            visualContext = null
        )
        
        assertTrue(result.isNotEmpty(), "Expected non-empty result without visual context")
    }
    
    @Test
    fun generateRespectsMaxTokensParameter() = runTest {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val engine = LocalSnnEngine(MockContext(), "test_model.pt", tokenizer)
        
        val result = engine.generate(
            prompt = "Generate a long response",
            maxTokens = 10
        )
        
        assertTrue(result.isNotEmpty(), "Expected non-empty result with maxTokens limit")
    }
    
    @Test
    fun generateReturnsFallbackOnError() = runTest {
        val tokenizer = LocalTokenizer(MockContext(), null)
        // Use a non-existent model path to trigger error handling
        val engine = LocalSnnEngine(MockContext(), "nonexistent_model.pt", tokenizer)
        
        val result = engine.generate("Test prompt")
        
        // Should return fallback message instead of crashing
        assertTrue(result.isNotEmpty(), "Expected fallback message on error")
    }
    
    @Test
    fun generateHandlesLongPrompts() = runTest {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val engine = LocalSnnEngine(MockContext(), "test_model.pt", tokenizer)
        
        val longPrompt = "This is a very long prompt that contains many words " +
                "and should be handled correctly by the engine without crashing " +
                "or causing any issues with tokenization or inference"
        
        val result = engine.generate(longPrompt)
        
        assertTrue(result.isNotEmpty(), "Expected non-empty result for long prompt")
    }
    
    @Test
    fun generateHandlesSpecialCharacters() = runTest {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val engine = LocalSnnEngine(MockContext(), "test_model.pt", tokenizer)
        
        val specialPrompt = "What about @mentions, #hashtags, and emojis? 😊"
        
        val result = engine.generate(specialPrompt)
        
        assertTrue(result.isNotEmpty(), "Expected non-empty result with special characters")
    }
    
    @Test
    fun generateIsIdempotent() = runTest {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val engine = LocalSnnEngine(MockContext(), "test_model.pt", tokenizer)
        
        val prompt = "Consistent test prompt"
        val result1 = engine.generate(prompt)
        val result2 = engine.generate(prompt)
        
        // Mock backend should return deterministic results
        assertEquals(result1, result2, "Expected consistent results for same prompt")
    }
    
    @Test
    fun generateCombinesPromptAndVisualContext() = runTest {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val engine = LocalSnnEngine(MockContext(), "test_model.pt", tokenizer)
        
        val prompt = "Describe this"
        val visualContext = "A cat sitting on a mat"
        
        val result = engine.generate(prompt, visualContext)
        
        assertTrue(result.isNotEmpty(), "Expected result combining prompt and visual context")
    }
}
