package rayskillkit.core

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import java.io.File
import java.util.Locale
import kotlin.math.absoluteValue
import org.json.JSONArray
import org.json.JSONObject

private const val DEFAULT_LANGUAGE_MODEL_ASSET = "models/snn_student.onnx"
private const val TOKEN_SPACE = 32768L
private const val UNKNOWN_TOKEN_ID = 0L

private data class ModelMetadata(
    val vocab: List<String> = emptyList(),
    val lowercase: Boolean = true,
    val padTokenId: Long = 0L,
    val unkTokenId: Long = UNKNOWN_TOKEN_ID,
    val maxSequenceLength: Int? = null,
    val inputName: String? = null,
    val inputShape: LongArray? = null,
    val outputShape: LongArray? = null,
)

interface SessionFactory {
    fun create(context: Context, modelAssetName: String): LanguageSession
}

interface LanguageSession : AutoCloseable {
    val inputNames: Set<String>
    fun run(inputs: Map<String, OnnxTensor>): SessionResult
}

interface SessionResult : AutoCloseable {
    val isEmpty: Boolean
    operator fun get(index: Int): SessionValue
}

data class SessionValue(val value: Any?)

class DefaultSessionFactory(private val environment: OrtEnvironment) : SessionFactory {
    override fun create(context: Context, modelAssetName: String): LanguageSession {
        val modelBytes = context.assets.open(modelAssetName).use { it.readBytes() }
        val ortSession = environment.createSession(modelBytes)
        return OrtLanguageSession(ortSession)
    }
}

class OrtLanguageSession(private val delegate: OrtSession) : LanguageSession {
    override val inputNames: Set<String>
        get() = delegate.inputNames

    override fun run(inputs: Map<String, OnnxTensor>): SessionResult =
        OrtSessionResult(delegate.run(inputs))

    override fun close() {
        delegate.close()
    }
}

class OrtSessionResult(private val delegate: OrtSession.Result) : SessionResult {
    override val isEmpty: Boolean
        get() = delegate.isEmpty

    override fun get(index: Int): SessionValue = SessionValue(delegate[index].value)

    override fun close() {
        delegate.close()
    }
}

/**
 * Minimal language engine wrapper that wires an ONNX Runtime session to the SNN language model.
 *
 * The implementation intentionally keeps tokenization/decoding lightweight and documents the
 * assumptions so it can be replaced with the real tokenizer and model-specific tensor shapes
 * once they are available.
 */
class SnnLanguageEngine(
    context: Context,
    modelAssetName: String = DEFAULT_LANGUAGE_MODEL_ASSET,
    environment: OrtEnvironment = OrtEnvironment.getEnvironment(),
    sessionFactory: SessionFactory = DefaultSessionFactory(environment),
    session: LanguageSession? = null
) {
    private val environment: OrtEnvironment = environment
    private val metadata: ModelMetadata = loadMetadata(context, modelAssetName)
    private val inferenceSession: LanguageSession = session ?: sessionFactory.create(context, modelAssetName)

    /**
     * Generates a reply for [prompt] by running a single ONNX inference.
     *
     * Tokenization follows the exported SNN `metadata.json` when available to keep ID and tensor
     * shapes aligned with training. If metadata is missing or malformed, the engine falls back to
     * a lightweight hashed tokenizer/decoder to maintain API compatibility for demos and tests.
     */
    fun generateReply(prompt: String, maxTokens: Int = 32): String {
        val sanitizedPrompt = prompt.trim()
        if (sanitizedPrompt.isEmpty()) {
            return fallbackReply(sanitizedPrompt)
        }
        val (tokenIds, reverseVocab) = tokenize(sanitizedPrompt, maxTokens)
        val inputName = resolveInputName()
            ?: return fallbackReply(sanitizedPrompt)

        val paddedTokens = padTokens(tokenIds, maxTokens)
        val shape = inputShapeFor(paddedTokens.size)

        OnnxTensor.createTensor(environment, paddedTokens, shape).use { inputTensor ->
            inferenceSession.run(mapOf(inputName to inputTensor)).use { result ->
                val decoded = decode(result, reverseVocab)
                return decoded.ifBlank { fallbackReply(sanitizedPrompt) }
            }
        }
    }

    private fun tokenize(prompt: String, maxTokens: Int): Pair<LongArray, Map<Long, String>> {
        val vocabulary = mutableMapOf<Long, String>()
        if (metadata.vocab.isNotEmpty()) {
            val vocabIndex = metadata.vocab.withIndex().associate { (idx, token) -> token to idx.toLong() }
            val maxCount = desiredSequenceLength(maxTokens)
            val splitPattern = Regex("\\s+")
            val tokens = prompt
                .split(splitPattern)
                .filter { it.isNotEmpty() }
                .take(maxCount)
                .map { raw ->
                    val normalized = normalizeToken(raw)
                    val tokenId = vocabIndex[normalized] ?: metadata.unkTokenId
                    vocabulary.putIfAbsent(tokenId, metadata.vocab.getOrNull(tokenId.toInt()) ?: normalized)
                    tokenId
                }

            val tokenArray = if (tokens.isNotEmpty()) tokens.toLongArray() else longArrayOf(metadata.unkTokenId)
            return tokenArray to vocabulary
        }

        val maxCount = maxTokens.coerceAtLeast(1)
        val tokens = prompt
            .split(Regex("\\s+"))
            .filter { it.isNotEmpty() }
            .take(maxCount)
            .map { word ->
                val tokenId = (normalizeToken(word).hashCode().toLong().absoluteValue % TOKEN_SPACE) + 1
                vocabulary.putIfAbsent(tokenId, word)
                tokenId
            }

        val tokenArray = if (tokens.isNotEmpty()) tokens.toLongArray() else longArrayOf(UNKNOWN_TOKEN_ID)
        return tokenArray to vocabulary
    }

    private fun padTokens(tokens: LongArray, maxTokens: Int): LongArray {
        val desiredLength = desiredSequenceLength(maxTokens)
        if (tokens.size >= desiredLength) {
            return tokens.copyOf(desiredLength)
        }

        val padded = LongArray(desiredLength) { metadata.padTokenId }
        tokens.copyInto(padded)
        return padded
    }

    private fun decode(result: SessionResult?, vocabulary: Map<Long, String>): String {
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

        val decoded = if (metadata.vocab.isNotEmpty()) {
            tokenIds
                .mapNotNull { tokenId ->
                    val idx = tokenId.toInt()
                    metadata.vocab.getOrNull(idx)
                        ?.takeIf { tokenId != metadata.padTokenId }
                }
                .filter { it.isNotEmpty() }
        } else {
            tokenIds.mapNotNull { vocabulary[it] }
        }

        return decoded
            .takeIf { it.isNotEmpty() }
            ?.joinToString(separator = " ")
            .orEmpty()
    }

    private fun desiredSequenceLength(maxTokens: Int): Int {
        val metadataLength = metadata.inputShape?.lastOrNull()?.takeIf { it > 0 }?.toInt()
            ?: metadata.maxSequenceLength
        return (metadataLength ?: maxTokens).coerceAtLeast(1)
    }

    private fun normalizeToken(raw: String): String =
        if (metadata.lowercase) raw.lowercase(Locale.US) else raw

    private fun resolveInputName(): String? {
        val candidate = metadata.inputName
        if (candidate != null && inferenceSession.inputNames.contains(candidate)) {
            return candidate
        }
        return inferenceSession.inputNames.firstOrNull()
    }

    private fun inputShapeFor(paddedLength: Int): LongArray {
        val template = metadata.inputShape
        if (template == null || template.isEmpty()) {
            return longArrayOf(1L, paddedLength.toLong())
        }

        val shape = template.copyOf()
        if (shape.isNotEmpty()) {
            val lastIndex = shape.lastIndex
            if (shape[lastIndex] <= 0) {
                shape[lastIndex] = paddedLength.toLong()
            }
        }
        return shape
    }

    private fun fallbackReply(prompt: String): String {
        if (prompt.isNotBlank()) {
            return prompt.lines().firstOrNull()?.take(64).orEmpty()
        }
        return "Acknowledged"
    }

    private fun loadMetadata(context: Context, modelAssetName: String): ModelMetadata {
        val candidates = metadataCandidates(modelAssetName)
        for (candidate in candidates) {
            val file = File(candidate)
            if (file.exists()) {
                return runCatching { parseMetadata(file.readText()) }.getOrElse { ModelMetadata() }
            }

            val stream = runCatching { context.assets?.open(candidate) }.getOrNull() ?: continue
            val contents = stream.bufferedReader().use { it.readText() }
            return runCatching { parseMetadata(contents) }.getOrElse { ModelMetadata() }
        }
        return ModelMetadata()
    }

    private fun metadataCandidates(modelAssetName: String): List<String> {
        val modelFile = File(modelAssetName)
        val baseName = modelFile.nameWithoutExtension
        val directory = modelFile.parent
        val suffixes = listOf("metadata.json", "$baseName.metadata.json", "${baseName}_metadata.json")

        if (directory.isNullOrEmpty()) {
            return suffixes
        }
        return suffixes.map { File(directory, it).path }
    }

    private fun parseMetadata(raw: String): ModelMetadata {
        val json = JSONObject(raw)
        val tokenizer = json.optJSONObject("tokenizer") ?: json.optJSONObject("tokenizer_config")
        val vocab = tokenizer?.optJSONArray("vocab")?.toStringList() ?: emptyList()
        val lowercase = tokenizer?.optBoolean("lowercase", true) ?: true
        val padTokenId = tokenizer?.optLong("pad_token_id", 0L) ?: 0L
        val unkTokenId = tokenizer?.optLong("unk_token_id", UNKNOWN_TOKEN_ID) ?: UNKNOWN_TOKEN_ID
        val maxSequenceLength = tokenizer?.optIntOrNull("max_length")

        val inputs = json.optJSONObject("inputs")
        val inputName = inputs?.keys()?.asSequence()?.firstOrNull()
        val inputShape = inputName?.let { name -> inputs.optJSONObject(name)?.optJSONArray("shape")?.toLongArrayOrNull() }

        val outputs = json.optJSONObject("outputs")
        val outputName = outputs?.keys()?.asSequence()?.firstOrNull()
        val outputShape = outputName?.let { name -> outputs.optJSONObject(name)?.optJSONArray("shape")?.toLongArrayOrNull() }

        return ModelMetadata(
            vocab = vocab,
            lowercase = lowercase,
            padTokenId = padTokenId,
            unkTokenId = unkTokenId,
            maxSequenceLength = maxSequenceLength,
            inputName = inputName,
            inputShape = inputShape,
            outputShape = outputShape,
        )
    }
}

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

private fun JSONArray.toLongArrayOrNull(): LongArray? {
    val values = mutableListOf<Long>()
    for (index in 0 until length()) {
        val value = opt(index)
        when (value) {
            is Number -> values.add(value.toLong())
            is String -> value.toLongOrNull()?.let { values.add(it) }
        }
    }
    return if (values.isEmpty()) null else values.toLongArray()
}

private fun JSONObject.optIntOrNull(key: String): Int? {
    if (!has(key)) return null
    return runCatching { getInt(key) }.getOrNull()
}
