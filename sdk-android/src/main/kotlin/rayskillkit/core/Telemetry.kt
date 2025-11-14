package rayskillkit.core

import android.content.Context
import java.io.File
import java.io.FileWriter
import java.time.Clock
import kotlin.math.max
import kotlin.random.Random
import org.json.JSONObject

class Telemetry @JvmOverloads constructor(
    context: Context? = null,
    storageDir: File? = null,
    private val samplingConfig: SamplingConfig = SamplingConfig(),
    private val clock: Clock = Clock.systemUTC(),
    private val random: Random = Random.Default
) {
    data class SamplingConfig(
        val rules: Map<String, Double> = emptyMap(),
        val defaultRate: Double = 1.0
    ) {
        init {
            require(defaultRate in 0.0..1.0) { "defaultRate must be between 0 and 1" }
            rules.forEach { (key, value) ->
                require(key.isNotBlank()) { "Sampling rule names cannot be blank" }
                require(value in 0.0..1.0) { "Sampling rule for '$key' must be between 0 and 1" }
            }
        }

        fun shouldSample(event: String, random: Random): Boolean {
            val rate = rateFor(event)
            if (rate <= 0.0) {
                return false
            }
            if (rate >= 1.0) {
                return true
            }
            return random.nextDouble() < rate
        }

        private fun rateFor(event: String): Double {
            var bestMatchLength = -1
            var bestRate: Double? = null
            for ((ruleEvent, rate) in rules) {
                if (event.startsWith(ruleEvent) && ruleEvent.length > bestMatchLength) {
                    bestMatchLength = ruleEvent.length
                    bestRate = rate
                }
            }
            return bestRate ?: defaultRate
        }
    }

    private val storageDirectory: File = (storageDir ?: context?.let { determineDirectory(it) }
        ?: defaultFallbackDirectory()).apply { mkdirs() }
    private val storageFile: File = File(storageDirectory, EVENTS_FILE_NAME)
    private val lock = Any()

    fun record(
        event: String,
        metrics: Map<String, Number> = emptyMap(),
        attributes: Map<String, Any?> = emptyMap()
    ) {
        if (!samplingConfig.shouldSample(event, random)) {
            return
        }

        val payload = buildPayload(event, metrics, attributes)
        val line = payload.toString()
        synchronized(lock) {
            FileWriter(storageFile, /* append = */ true).use { writer ->
                writer.append(line)
                writer.append('\n')
            }
        }
    }

    fun recordRouterSuccess(skillName: String) {
        record(
            event = ROUTER_EVENT,
            metrics = mapOf(
                "router.success" to 1,
                "router.failure" to 0
            ),
            attributes = mapOf(
                "skill" to skillName,
                "outcome" to "success"
            )
        )
    }

    fun recordRouterFailure(skillName: String, error: Throwable) {
        record(
            event = ROUTER_EVENT,
            metrics = mapOf(
                "router.success" to 0,
                "router.failure" to 1
            ),
            attributes = mapOf(
                "skill" to skillName,
                "outcome" to "failure",
                "error" to (error.message ?: error.javaClass.simpleName)
            )
        )
    }

    fun recordTts(durationMs: Long, characterCount: Int, success: Boolean) {
        record(
            event = TTS_EVENT,
            metrics = mapOf(
                "tts.ms" to max(0L, durationMs),
                "tts.characters" to max(0, characterCount)
            ),
            attributes = mapOf(
                "success" to success
            )
        )
    }

    fun recordShareInEvent(stage: String, attributes: Map<String, Any?> = emptyMap()) {
        val combined = attributes.toMutableMap()
        combined["stage"] = stage
        record(
            event = SHARE_IN_EVENT,
            attributes = combined
        )
    }

    fun clear() {
        synchronized(lock) {
            if (storageFile.exists()) {
                storageFile.writeText("")
            }
        }
    }

    fun events(): List<String> {
        synchronized(lock) {
            if (!storageFile.exists()) {
                return emptyList()
            }
            return storageFile.readLines().filter { it.isNotBlank() }
        }
    }

    private fun buildPayload(
        event: String,
        metrics: Map<String, Number>,
        attributes: Map<String, Any?>
    ): JSONObject {
        val payload = JSONObject()
        payload.put("timestamp", clock.instant().toString())
        payload.put("event", event)

        val metricsObject = JSONObject()
        metrics.forEach { (key, value) ->
            metricsObject.put(key, value)
        }
        payload.put("metrics", metricsObject)

        val attributesObject = JSONObject()
        attributes.forEach { (key, value) ->
            attributesObject.put(key, value ?: JSONObject.NULL)
        }
        payload.put("attributes", attributesObject)

        return payload
    }

    private fun determineDirectory(context: Context): File {
        val external = context.getExternalFilesDir(TELEMETRY_DIRECTORY_NAME)
        if (external != null) {
            return external
        }
        val internal = File(context.filesDir, TELEMETRY_DIRECTORY_NAME)
        internal.mkdirs()
        return internal
    }

    private fun defaultFallbackDirectory(): File {
        val base = File(System.getProperty("java.io.tmpdir"), TELEMETRY_DIRECTORY_NAME)
        base.mkdirs()
        return base
    }

    companion object {
        private const val EVENTS_FILE_NAME = "events.jsonl"
        private const val TELEMETRY_DIRECTORY_NAME = "telemetry"
        private const val ROUTER_EVENT = "router.outcome"
        private const val TTS_EVENT = "tts.performance"
        private const val SHARE_IN_EVENT = "share_in.funnel"
    }
}
