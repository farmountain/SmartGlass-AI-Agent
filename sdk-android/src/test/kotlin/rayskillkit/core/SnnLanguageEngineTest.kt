package rayskillkit.core

import android.test.mock.MockContext
import java.io.File
import java.nio.file.Files
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.test.Test
import kotlin.test.assertTrue

class SnnLanguageEngineTest {
    private class FakeSession(private val inputName: String = "input") : LanguageSession {
        private val sessionUsed = AtomicBoolean(false)
        private var lastTokens: LongArray? = null

        override val inputNames: Set<String> = setOf(inputName)

        override fun run(inputs: Map<String, ai.onnxruntime.OnnxTensor>): SessionResult {
            sessionUsed.set(true)
            val tensor = inputs.values.first()
            val capturedTokens = (tensor.value as? LongArray) ?: longArrayOf()
            lastTokens = capturedTokens
            val tokens = capturedTokens.filter { it != 0L }.take(3).toLongArray().ifEmpty { longArrayOf(1L) }
            return object : SessionResult {
                override val isEmpty: Boolean = tokens.isEmpty()

                override fun get(index: Int): SessionValue = SessionValue(tokens)

                override fun close() {
                    // no-op
                }
            }
        }

        override fun close() {
            // no-op
        }

        fun wasUsed(): Boolean = sessionUsed.get()

        fun capturedTokens(): LongArray? = lastTokens
    }

    @Test
    fun generateReplyReturnsNonEmptyString() {
        val engine = SnnLanguageEngine(MockContext(), session = FakeSession())
        val reply = engine.generateReply("Hello from the glasses")

        assertTrue(reply.isNotBlank(), "Expected generated reply to be non-empty")
    }

    @Test
    fun generateReplyUsesInjectedSession() {
        val fakeSession = FakeSession()
        val engine = SnnLanguageEngine(MockContext(), session = fakeSession)
        val reply = engine.generateReply("Hello from the glasses")

        assertTrue(fakeSession.wasUsed(), "Expected injected session to be invoked")
        assertTrue(reply.isNotBlank(), "Expected generated reply to be non-empty")
    }

    @Test
    fun generateReplyUsesMetadataTokenizerAndShapes() {
        val tempDir = Files.createTempDirectory("snn-metadata").toFile()
        val metadataFile = File(tempDir, "metadata.json")
        metadataFile.writeText(
            """
            {
              "tokenizer": {
                "vocab": ["<pad>", "hello", "from", "the", "glasses"],
                "lowercase": true,
                "pad_token_id": 0,
                "unk_token_id": 0,
                "max_length": 4
              },
              "inputs": {
                "input_ids": {"shape": [1, 4]}
              },
              "outputs": {
                "logits": {"shape": [1, 4, 5]}
              }
            }
            """.trimIndent()
        )
        val modelPath = File(tempDir, "student.onnx")

        val session = FakeSession(inputName = "input_ids")
        val engine = SnnLanguageEngine(MockContext(), modelAssetName = modelPath.path, session = session)

        val reply = engine.generateReply("Hello glasses", maxTokens = 2)

        val tokens = session.capturedTokens()
        assertTrue(tokens?.size == 4, "Expected tokens to be padded to metadata length")
        assertTrue(tokens?.take(2) == listOf(1L, 4L), "Expected vocabulary-backed token ids for prompt")
        assertTrue(reply.contains("hello") && reply.contains("glasses"), "Expected metadata vocab to drive decoding")
    }

    @Test
    fun generateReplyFallsBackWithoutMetadata() {
        val session = FakeSession()
        val engine = SnnLanguageEngine(MockContext(), modelAssetName = "/tmp/nonexistent/student.onnx", session = session)

        val reply = engine.generateReply("Fallback behavior")

        assertTrue(session.wasUsed(), "Expected inference to run even without metadata")
        assertTrue(reply.isNotBlank(), "Expected reply even when metadata is missing")
    }
}
