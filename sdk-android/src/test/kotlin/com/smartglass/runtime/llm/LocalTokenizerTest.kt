package com.smartglass.runtime.llm

import android.test.mock.MockContext
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class LocalTokenizerTest {
    
    @Test
    fun encodeReturnsNonEmptyTokens() {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val tokens = tokenizer.encode("hello world")
        
        assertTrue(tokens.isNotEmpty(), "Expected non-empty token array")
        assertTrue(tokens.size == 2, "Expected 2 tokens for 'hello world'")
    }
    
    @Test
    fun encodeEmptyStringReturnsUnknownToken() {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val tokens = tokenizer.encode("")
        
        assertEquals(1, tokens.size, "Expected single token for empty string")
        assertEquals(0, tokens[0], "Expected unknown token ID for empty string")
    }
    
    @Test
    fun encodeRespectsMaxLength() {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val longText = "one two three four five six seven eight nine ten"
        val tokens = tokenizer.encode(longText, maxLength = 3)
        
        assertEquals(3, tokens.size, "Expected exactly 3 tokens with maxLength=3")
    }
    
    @Test
    fun padExpandsToDesiredLength() {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val tokens = intArrayOf(1, 2, 3)
        val padded = tokenizer.pad(tokens, 10)
        
        assertEquals(10, padded.size, "Expected padded array of length 10")
        assertEquals(1, padded[0], "Expected first token preserved")
        assertEquals(2, padded[1], "Expected second token preserved")
        assertEquals(3, padded[2], "Expected third token preserved")
        assertEquals(0, padded[3], "Expected padding token at index 3")
    }
    
    @Test
    fun padTruncatesToDesiredLength() {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val tokens = intArrayOf(1, 2, 3, 4, 5)
        val truncated = tokenizer.pad(tokens, 3)
        
        assertEquals(3, truncated.size, "Expected truncated array of length 3")
        assertEquals(1, truncated[0], "Expected first token preserved")
        assertEquals(2, truncated[1], "Expected second token preserved")
        assertEquals(3, truncated[2], "Expected third token preserved")
    }
    
    @Test
    fun decodeReturnsStringForHashBasedTokens() {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val tokens = intArrayOf(100, 200, 300)
        val decoded = tokenizer.decode(tokens)
        
        assertTrue(decoded.isNotEmpty(), "Expected non-empty decoded string")
        assertTrue(decoded.contains("token"), "Expected token placeholders in decoded output")
    }
    
    @Test
    fun decodeEmptyArrayReturnsEmptyString() {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val decoded = tokenizer.decode(intArrayOf())
        
        assertEquals("", decoded, "Expected empty string for empty token array")
    }
    
    @Test
    fun padTokenIdIsAccessible() {
        val tokenizer = LocalTokenizer(MockContext(), null)
        assertEquals(0, tokenizer.padTokenId, "Expected default pad token ID to be 0")
    }
    
    @Test
    fun maxSequenceLengthHasDefault() {
        val tokenizer = LocalTokenizer(MockContext(), null)
        assertTrue(tokenizer.maxSequenceLength > 0, "Expected positive max sequence length")
    }
    
    @Test
    fun encodeIsDeterministic() {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val text = "hello world test"
        val tokens1 = tokenizer.encode(text)
        val tokens2 = tokenizer.encode(text)
        
        assertTrue(tokens1.contentEquals(tokens2), "Expected deterministic encoding")
    }
    
    @Test
    fun encodeSupportsBasicAscii() {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val asciiText = "The quick brown fox jumps over the lazy dog 0123456789"
        val tokens = tokenizer.encode(asciiText, maxLength = 100)
        
        assertTrue(tokens.isNotEmpty(), "Expected non-empty tokens for ASCII text")
        assertTrue(tokens.all { it >= 0 }, "Expected all token IDs to be non-negative")
    }
    
    @Test
    fun decodeIsDeterministic() {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val tokens = intArrayOf(100, 200, 300)
        val decoded1 = tokenizer.decode(tokens)
        val decoded2 = tokenizer.decode(tokens)
        
        assertEquals(decoded1, decoded2, "Expected deterministic decoding")
    }
    
    @Test
    fun encodeDecodeRoundTripWithFallback() {
        val tokenizer = LocalTokenizer(MockContext(), null)
        val text = "test encoding"
        val tokens = tokenizer.encode(text)
        val decoded = tokenizer.decode(tokens)
        
        // With fallback mode, we can't fully recover the original text,
        // but decoded output should be non-empty and contain token placeholders
        assertTrue(decoded.isNotEmpty(), "Expected non-empty decoded output")
    }
}
