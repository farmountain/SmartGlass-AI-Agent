package rayskillkit.core

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import kotlin.math.absoluteValue

private const val DEFAULT_LANGUAGE_MODEL_ASSET = "models/snn_student.onnx"
private const val TOKEN_SPACE = 32768L
private const val UNKNOWN_TOKEN_ID = 0L

/**
 * Minimal language engine wrapper that wires an ONNX Runtime session to the SNN language model.
 *
 * The implementation intentionally keeps tokenization/decoding lightweight and documents the
 * assumptions so it can be replaced with the real tokenizer and model-specific tensor shapes
 * once they are available.
 */
class SnnLanguageEngine(
    context: Context,
    modelAssetName: String = DEFAULT_LANGUAGE_MODEL_ASSET
) {
    private val environment: OrtEnvironment = OrtEnvironment.getEnvironment()
    private val inferenceSession: OrtSession

    init {
        val modelBytes = context.assets.open(modelAssetName).use { it.readBytes() }
        inferenceSession = environment.createSession(modelBytes)
    }

    /**
     * Generates a reply for [prompt] by running a single ONNX inference.
     *
     * The tokenizer is a placeholder that splits on whitespace and hashes tokens into a fixed
     * integer space. The decoder mirrors that simplicity by mapping predicted token IDs back to
     * the observed prompt vocabulary. TODO: Swap to the production tokenizer and model-aligned
     * input/output formatting once those components are finalized.
     */
    fun generateReply(prompt: String, maxTokens: Int = 32): String {
        val sanitizedPrompt = prompt.trim()
        if (sanitizedPrompt.isEmpty()) {
            return fallbackReply(sanitizedPrompt)
        }
        val (tokenIds, reverseVocab) = tokenize(sanitizedPrompt, maxTokens)
        val inputName = inferenceSession.inputNames.firstOrNull()
            ?: return fallbackReply(sanitizedPrompt)

        val paddedTokens = padTokens(tokenIds, maxTokens)
        val shape = longArrayOf(1L, paddedTokens.size.toLong())

        OnnxTensor.createTensor(environment, paddedTokens, shape).use { inputTensor ->
            inferenceSession.run(mapOf(inputName to inputTensor)).use { result ->
                val decoded = decode(result, reverseVocab)
                return decoded.ifBlank { fallbackReply(sanitizedPrompt) }
            }
        }
    }

    private fun tokenize(prompt: String, maxTokens: Int): Pair<LongArray, Map<Long, String>> {
        val vocabulary = mutableMapOf<Long, String>()
        val maxCount = maxTokens.coerceAtLeast(1)
        val tokens = prompt
            .split(Regex("\\s+"))
            .filter { it.isNotEmpty() }
            .take(maxCount)
            .map { word ->
                val tokenId = (word.lowercase().hashCode().toLong().absoluteValue % TOKEN_SPACE) + 1
                vocabulary.putIfAbsent(tokenId, word)
                tokenId
            }

        val tokenArray = if (tokens.isNotEmpty()) tokens.toLongArray() else longArrayOf(UNKNOWN_TOKEN_ID)
        return tokenArray to vocabulary
    }

    private fun padTokens(tokens: LongArray, maxTokens: Int): LongArray {
        val desiredLength = maxTokens.coerceAtLeast(1)
        if (tokens.size >= desiredLength) {
            return tokens.copyOf(desiredLength)
        }

        val padded = LongArray(desiredLength)
        tokens.copyInto(padded)
        return padded
    }

    private fun decode(result: OrtSession.Result?, vocabulary: Map<Long, String>): String {
        if (result == null || result.isEmpty()) {
            return ""
        }

        val raw = result[0].value
        val tokenIds: List<Long> = when (raw) {
            is LongArray -> raw.toList()
            is IntArray -> raw.map { it.toLong() }
            is FloatArray -> raw.map { it.toLong() }
            is Array<*> -> raw.firstOrNull { it is LongArray }?.let { (it as LongArray).toList() }
                ?: raw.firstOrNull { it is IntArray }?.let { (it as IntArray).map { value -> value.toLong() } }
                ?: raw.firstOrNull { it is FloatArray }?.let { (it as FloatArray).map { value -> value.toLong() } }
                ?: emptyList()
            else -> emptyList()
        }

        val decoded = tokenIds
            .mapNotNull { vocabulary[it] }
            .takeIf { it.isNotEmpty() }
            ?.joinToString(separator = " ")
            .orEmpty()

        return decoded
    }

    private fun fallbackReply(prompt: String): String {
        if (prompt.isNotBlank()) {
            return prompt.lines().firstOrNull()?.take(64).orEmpty()
        }
        return "Acknowledged"
    }
}
