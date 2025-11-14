package rayskillkit.ui

import android.content.ContextWrapper
import java.nio.file.Files
import org.json.JSONObject
import rayskillkit.core.Telemetry
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class TtsTest {
    @Test
    fun sayReturnsPositiveDurationAndRecordsTelemetryMetric() {
        val directory = Files.createTempDirectory("tts-telemetry").toFile()
        val telemetry = Telemetry(storageDir = directory)
        val recorder = TTS.TelemetryRecorder.fromTelemetry(telemetry)
        val tts = TTS(telemetryProvider = { recorder }).apply { initialize() }
        val context = object : ContextWrapper(null) {}

        val text = "Hello world"
        val durationMs = tts.say(context, text)

        assertTrue(durationMs > 0)

        val events = telemetry.events().map(::JSONObject)
        assertEquals(1, events.size)
        val payload = events.first()
        assertEquals("tts.performance", payload.getString("event"))
        val metrics = payload.getJSONObject("metrics")
        assertTrue(metrics.getLong("tts.ms") > 0)
        assertEquals(text.trim().length, metrics.getInt("tts.characters"))
    }
}
