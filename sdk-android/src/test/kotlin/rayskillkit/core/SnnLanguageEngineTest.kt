package rayskillkit.core

import android.content.res.AssetManager
import android.test.mock.MockContext
import java.io.ByteArrayInputStream
import kotlin.test.Test
import kotlin.test.assertTrue

class SnnLanguageEngineTest {
    private class FakeAssetManager(private val bytes: ByteArray) : AssetManager() {
        override fun open(fileName: String): java.io.InputStream {
            return ByteArrayInputStream(bytes)
        }

        override fun open(fileName: String, accessMode: Int): java.io.InputStream {
            return ByteArrayInputStream(bytes)
        }
    }

    @Test
    fun generateReplyReturnsNonEmptyString() {
        val context = object : MockContext() {
            private val assetManager = FakeAssetManager(byteArrayOf(0x0, 0x1))
            override fun getAssets(): AssetManager = assetManager
        }

        val engine = SnnLanguageEngine(context)
        val reply = engine.generateReply("Hello from the glasses")

        assertTrue(reply.isNotBlank(), "Expected generated reply to be non-empty")
    }
}
