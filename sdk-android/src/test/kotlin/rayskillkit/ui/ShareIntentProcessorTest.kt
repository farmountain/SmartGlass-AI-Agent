package rayskillkit.ui

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.test.mock.MockContext
import java.nio.file.Files
import org.json.JSONObject
import rayskillkit.core.Router
import rayskillkit.core.SkillDescriptor
import rayskillkit.core.SkillRegistry
import rayskillkit.core.SkillRunner
import rayskillkit.core.Telemetry
import rayskillkit.core.ocr.OcrProvider
import kotlin.test.BeforeTest
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import kotlin.test.assertNotNull

class ShareIntentProcessorTest {
    private lateinit var context: Context
    private lateinit var registry: SkillRegistry
    private lateinit var descriptor: RecordingShareDescriptor
    private lateinit var router: Router
    private lateinit var tts: RecordingTts
    private lateinit var ocrProvider: FakeOcrProvider
    private lateinit var telemetry: Telemetry

    @BeforeTest
    fun setUp() {
        context = MockContext()
        registry = SkillRegistry()
        descriptor = RecordingShareDescriptor()
        registry.registerSkill(SHARE_SKILL_ID, descriptor)
        val telemetryDir = Files.createTempDirectory("telemetry-share").toFile()
        telemetry = Telemetry(storageDir = telemetryDir)
        router = Router(registry, telemetry)
        tts = RecordingTts().apply { initialize() }
        ocrProvider = FakeOcrProvider()
    }

    @Test
    fun processReturnsFalseWhenIntentMissing() {
        val processor = ShareIntentProcessor(context, router, tts, ocrProvider, telemetry)
        assertFalse(processor.process(null))
        assertEquals(emptyList(), tts.spoken)
        assertEquals(null, descriptor.lastPayload)
    }

    @Test
    fun processesSharedTextExtra() {
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, "Shared insight")
        }

        val processor = ShareIntentProcessor(context, router, tts, ocrProvider, telemetry)
        assertTrue(processor.process(intent))

        assertEquals(ShareTextPayload("Shared insight"), descriptor.lastPayload)
        assertEquals(listOf("Shared insight"), tts.spoken)

        val events = telemetry.events()
        assertTrue(events.isNotEmpty())
        val ttsEvent = events.map(::JSONObject).firstOrNull { it.getString("event") == "tts.performance" }
        assertNotNull(ttsEvent)
        val metrics = ttsEvent.getJSONObject("metrics")
        assertTrue(metrics.has("tts.ms"))
    }

    @Test
    fun processesSharedUrisWithOcr() {
        val first = Uri.parse("content://example/first")
        val second = Uri.parse("content://example/second")
        ocrProvider.register(first, "First page text")
        ocrProvider.register(second, "Second page text")

        val intent = Intent(Intent.ACTION_SEND_MULTIPLE).apply {
            type = "image/*"
            putParcelableArrayListExtra(Intent.EXTRA_STREAM, arrayListOf(first, second))
        }

        val processor = ShareIntentProcessor(context, router, tts, ocrProvider, telemetry)
        assertTrue(processor.process(intent))

        val expected = "First page text\nSecond page text"
        assertEquals(ShareTextPayload(expected), descriptor.lastPayload)
        assertEquals(listOf(expected), tts.spoken)

        val shareEvents = telemetry.events().map(::JSONObject).filter { it.getString("event") == "share_in.funnel" }
        assertTrue(shareEvents.isNotEmpty())
    }

    private class RecordingShareDescriptor : SkillDescriptor<ShareTextPayload, ShareTextPayload, ShareTextResult> {
        var lastPayload: ShareTextPayload? = null
            private set

        override fun buildFeatures(payload: ShareTextPayload): ShareTextPayload {
            lastPayload = payload
            return payload
        }

        override val runner: SkillRunner<ShareTextPayload, ShareTextResult> =
            SkillRunner { features -> ShareTextResult(features.text) }
    }

    private class RecordingTts : TTS() {
        val spoken = mutableListOf<String>()

        override fun speak(text: String): Boolean {
            val result = super.speak(text)
            if (result) {
                spoken += text
            }
            return result
        }
    }

    private class FakeOcrProvider : OcrProvider {
        private val responses = mutableMapOf<Uri, String>()

        fun register(uri: Uri, text: String) {
            responses[uri] = text
        }

        override fun extractText(context: Context, uri: Uri): String {
            return responses[uri] ?: ""
        }
    }
}
