package rayskillkit.core

import android.test.mock.MockContext
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.test.Test
import kotlin.test.assertTrue

class SnnLanguageEngineTest {
    private class FakeSession : LanguageSession {
        private val sessionUsed = AtomicBoolean(false)

        override val inputNames: Set<String> = setOf("input")

        override fun run(inputs: Map<String, ai.onnxruntime.OnnxTensor>): SessionResult {
            sessionUsed.set(true)
            val tensor = inputs.values.first()
            val tokens = (tensor.value as? LongArray)?.filter { it != 0L }?.take(3)?.toLongArray()
                ?: longArrayOf(1L)
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
}
