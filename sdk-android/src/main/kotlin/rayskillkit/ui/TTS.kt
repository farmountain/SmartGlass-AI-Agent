package rayskillkit.ui

import android.content.Context
import kotlin.math.roundToLong
import rayskillkit.core.Telemetry

open class TTS(
    private val telemetryProvider: (Context) -> TelemetryRecorder = { context ->
        TelemetryRecorder.fromTelemetry(Telemetry(context))
    },
    private val charsPerSecond: Double = DEFAULT_CHARS_PER_SECOND
) {
    var isInitialized: Boolean = false
        private set

    private val telemetryLock = Any()
    @Volatile
    private var cachedTelemetry: TelemetryRecorder? = null

    open fun initialize() {
        isInitialized = true
    }

    open fun speak(text: String): Boolean {
        return isInitialized && text.isNotBlank()
    }

    open fun say(context: Context, text: String): Long {
        check(isInitialized) { "TTS must be initialized before calling say" }

        val sanitized = text.trim()
        require(sanitized.isNotEmpty()) { "Text to speak must not be blank" }

        val characterCount = sanitized.length
        val durationSeconds = characterCount / charsPerSecond
        val durationMs = (durationSeconds * 1000.0).roundToLong().coerceAtLeast(1L)

        val telemetry = resolveTelemetry(context)
        telemetry.recordTts(durationMs, characterCount, success = true)

        return durationMs
    }

    private fun resolveTelemetry(context: Context): TelemetryRecorder {
        val existing = cachedTelemetry
        if (existing != null) {
            return existing
        }

        synchronized(telemetryLock) {
            val cached = cachedTelemetry
            if (cached != null) {
                return cached
            }

            val created = telemetryProvider(context)
            cachedTelemetry = created
            return created
        }
    }

    fun interface TelemetryRecorder {
        fun recordTts(durationMs: Long, characterCount: Int, success: Boolean)

        companion object {
            fun fromTelemetry(telemetry: Telemetry): TelemetryRecorder {
                return TelemetryRecorder { durationMs, characterCount, success ->
                    telemetry.recordTts(durationMs, characterCount, success)
                }
            }
        }
    }

    companion object {
        const val DEFAULT_CHARS_PER_SECOND = 14.0
    }
}
