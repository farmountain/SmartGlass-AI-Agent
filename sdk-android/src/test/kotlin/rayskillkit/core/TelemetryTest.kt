package rayskillkit.core

import java.nio.file.Files
import org.json.JSONObject
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class TelemetryTest {
    @Test
    fun writesMultipleEventsToDisk() {
        val directory = Files.createTempDirectory("telemetry-events").toFile()
        val telemetry = Telemetry(storageDir = directory)

        telemetry.recordShareInEvent("intent_received", mapOf("action" to "send"))
        telemetry.recordRouterSuccess("demo.skill")

        val events = telemetry.events().map(::JSONObject)
        assertEquals(2, events.size)

        val first = events[0]
        assertEquals("share_in.funnel", first.getString("event"))
        val firstAttributes = first.getJSONObject("attributes")
        assertEquals("intent_received", firstAttributes.getString("stage"))

        val second = events[1]
        assertEquals("router.outcome", second.getString("event"))
        val secondAttributes = second.getJSONObject("attributes")
        assertEquals("demo.skill", secondAttributes.getString("skill"))
        assertEquals("success", secondAttributes.getString("outcome"))
    }

    @Test
    fun samplingRulesAreHonored() {
        val directory = Files.createTempDirectory("telemetry-sampling").toFile()
        val telemetry = Telemetry(
            storageDir = directory,
            samplingConfig = Telemetry.SamplingConfig(
                rules = mapOf(
                    "share_in" to 1.0,
                    "router" to 0.0
                ),
                defaultRate = 0.0
            )
        )

        telemetry.recordShareInEvent("intent_received")
        telemetry.recordRouterSuccess("blocked.skill")

        val events = telemetry.events().map(::JSONObject)
        assertEquals(1, events.size)
        assertEquals("share_in.funnel", events[0].getString("event"))
    }

    @Test
    fun recordTtsIncludesDurationMetric() {
        val directory = Files.createTempDirectory("telemetry-tts").toFile()
        val telemetry = Telemetry(storageDir = directory)

        telemetry.recordTts(durationMs = 42, characterCount = 120, success = true)

        val events = telemetry.events().map(::JSONObject)
        assertEquals(1, events.size)
        val payload = events.first()
        assertEquals("tts.performance", payload.getString("event"))
        val metrics = payload.getJSONObject("metrics")
        assertEquals(42, metrics.getInt("tts.ms"))
        assertEquals(120, metrics.getInt("tts.characters"))
        val attributes = payload.getJSONObject("attributes")
        assertTrue(attributes.getBoolean("success"))
    }
}
