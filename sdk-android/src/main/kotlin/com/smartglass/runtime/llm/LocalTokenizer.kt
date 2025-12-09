package com.smartglass.runtime.llm

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.Locale
import kotlin.math.absoluteValue

/**
 * Size of hash space for fallback tokenization. Using 2^15 to keep token IDs manageable
 * while providing reasonable distribution for vocabulary-less tokenization.
 */
private const val TOKEN_SPACE = 32768L

/**
 * Token ID used for unknown or padding tokens in fallback mode.
 */
private const val UNKNOWN_TOKEN_ID = 0L

/**
 * Lightweight tokenizer for on-device SNN models.
 * 
 * Supports vocabulary-based tokenization when metadata is available,
 * or falls back to hash-based tokenization for compatibility.
 */
class LocalTokenizer(
    context: Context,
    modelAssetPath: String? = null
) {
    private val metadata: TokenizerMetadata = loadMetadata(context, modelAssetPath)
    
    /**
     * Encode a text string into token IDs.
     * 
     * @param text The input text to tokenize
     * @param maxLength Maximum number of tokens to generate
     * @return Array of token IDs
     */
    fun encode(text: String, maxLength: Int = 64): LongArray {
        val sanitized = text.trim()
        if (sanitized.isEmpty()) {
            return longArrayOf(metadata.unkTokenId)
        }
        
        if (metadata.vocab.isNotEmpty()) {
            val vocabIndex = metadata.vocab.withIndex().associate { (idx, token) -> token to idx.toLong() }
            val tokens = sanitized
                .split(Regex("\\s+"))
                .filter { it.isNotEmpty() }
                .take(maxLength)
                .map { raw ->
                    val normalized = normalizeToken(raw)
                    vocabIndex[normalized] ?: metadata.unkTokenId
                }
            
            return if (tokens.isNotEmpty()) tokens.toLongArray() else longArrayOf(metadata.unkTokenId)
        }
        
        // Fallback to hash-based tokenization
        val tokens = sanitized
            .split(Regex("\\s+"))
            .filter { it.isNotEmpty() }
            .take(maxLength)
            .map { word ->
                (normalizeToken(word).hashCode().toLong().absoluteValue % TOKEN_SPACE) + 1
            }
        
        return if (tokens.isNotEmpty()) tokens.toLongArray() else longArrayOf(UNKNOWN_TOKEN_ID)
    }
    
    /**
     * Decode token IDs back into text.
     * 
     * @param tokenIds Array of token IDs
     * @return Decoded text string
     */
    fun decode(tokenIds: LongArray): String {
        if (tokenIds.isEmpty()) {
            return ""
        }
        
        val decoded = if (metadata.vocab.isNotEmpty()) {
            tokenIds
                .mapNotNull { tokenId ->
                    val idx = tokenId.toInt()
                    metadata.vocab.getOrNull(idx)
                        ?.takeIf { tokenId != metadata.padTokenId }
                }
                .filter { it.isNotEmpty() }
        } else {
            // For hash-based tokens, we can't decode them back
            // Return a placeholder representation
            tokenIds.filter { it != metadata.padTokenId }.map { "[token_$it]" }
        }
        
        return decoded
            .takeIf { it.isNotEmpty() }
            ?.joinToString(separator = " ")
            .orEmpty()
    }
    
    /**
     * Pad or truncate token IDs to a specific length.
     * 
     * @param tokenIds Input token IDs
     * @param length Desired length
     * @return Padded or truncated token array
     */
    fun pad(tokenIds: LongArray, length: Int): LongArray {
        if (tokenIds.size >= length) {
            return tokenIds.copyOf(length)
        }
        
        val padded = LongArray(length) { metadata.padTokenId }
        tokenIds.copyInto(padded)
        return padded
    }
    
    /**
     * Get the maximum sequence length from metadata or use default.
     */
    val maxSequenceLength: Int
        get() = metadata.maxSequenceLength ?: 64
    
    /**
     * Get the padding token ID.
     */
    val padTokenId: Long
        get() = metadata.padTokenId
    
    private fun normalizeToken(raw: String): String =
        if (metadata.lowercase) raw.lowercase(Locale.US) else raw
    
    private fun loadMetadata(context: Context, modelAssetPath: String?): TokenizerMetadata {
        if (modelAssetPath == null) {
            return TokenizerMetadata()
        }
        
        val candidates = metadataCandidates(modelAssetPath)
        for (candidate in candidates) {
            val file = File(candidate)
            if (file.exists()) {
                return runCatching { parseMetadata(file.readText()) }.getOrElse { TokenizerMetadata() }
            }
            
            // Use runCatching with use block to ensure stream is closed even on exception
            val metadata = runCatching {
                context.assets.open(candidate).use { stream ->
                    val contents = stream.bufferedReader().readText()
                    parseMetadata(contents)
                }
            }.getOrNull()
            
            if (metadata != null) {
                return metadata
            }
        }
        return TokenizerMetadata()
    }
    
    private fun metadataCandidates(modelAssetPath: String): List<String> {
        val modelFile = File(modelAssetPath)
        val baseName = modelFile.nameWithoutExtension
        val directory = modelFile.parent
        val suffixes = listOf("metadata.json", "$baseName.metadata.json", "${baseName}_metadata.json")
        
        if (directory.isNullOrEmpty()) {
            return suffixes
        }
        return suffixes.map { File(directory, it).path }
    }
    
    private fun parseMetadata(raw: String): TokenizerMetadata {
        val json = JSONObject(raw)
        val tokenizer = json.optJSONObject("tokenizer") ?: json.optJSONObject("tokenizer_config")
        val vocab = tokenizer?.optJSONArray("vocab")?.toStringList() ?: emptyList()
        val lowercase = tokenizer?.optBoolean("lowercase", true) ?: true
        val padTokenId = tokenizer?.optLong("pad_token_id", 0L) ?: 0L
        val unkTokenId = tokenizer?.optLong("unk_token_id", UNKNOWN_TOKEN_ID) ?: UNKNOWN_TOKEN_ID
        val maxSequenceLength = tokenizer?.optIntOrNull("max_length")
        
        return TokenizerMetadata(
            vocab = vocab,
            lowercase = lowercase,
            padTokenId = padTokenId,
            unkTokenId = unkTokenId,
            maxSequenceLength = maxSequenceLength
        )
    }
}

private data class TokenizerMetadata(
    val vocab: List<String> = emptyList(),
    val lowercase: Boolean = true,
    val padTokenId: Long = 0L,
    val unkTokenId: Long = UNKNOWN_TOKEN_ID,
    val maxSequenceLength: Int? = null
)

private fun JSONArray.toStringList(): List<String> {
    val values = mutableListOf<String>()
    for (index in 0 until length()) {
        val value = opt(index)
        if (value is String) {
            values.add(value)
        } else if (value != null) {
            values.add(value.toString())
        }
    }
    return values
}

private fun JSONObject.optIntOrNull(key: String): Int? {
    if (!has(key)) return null
    return runCatching { getInt(key) }.getOrNull()
}
