package rayskillkit.ui

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import java.util.concurrent.TimeUnit
import rayskillkit.core.OrtHub
import rayskillkit.core.Router
import rayskillkit.core.SkillDescriptor
import rayskillkit.core.SkillRegistry
import rayskillkit.core.SkillRunner
import rayskillkit.core.Telemetry
import rayskillkit.core.ocr.OcrProvider
import rayskillkit.core.ocr.OcrProviderModule

internal const val SHARE_SKILL_ID = "share_in.text_pipeline"

class ShareInActivity : Activity() {
    private val processor: ShareIntentProcessor by lazy {
        ShareIntentProcessor(
            context = this,
            router = ShareInGraph.router(applicationContext),
            tts = ShareInGraph.tts(applicationContext),
            ocrProvider = ShareInGraph.ocrProvider(applicationContext),
            telemetry = ShareInGraph.telemetry(applicationContext)
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        processIntent(intent)
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        processIntent(intent)
    }

    private fun processIntent(intent: Intent?) {
        processor.process(intent)
        finish()
    }
}

internal object ShareInGraph {
    private val lock = Any()
    @Volatile
    private var ortHub: OrtHub? = null
    @Volatile
    private var router: Router? = null
    @Volatile
    private var tts: TTS? = null
    @Volatile
    private var telemetryInstance: Telemetry? = null

    fun router(context: Context): Router {
        val existing = router
        if (existing != null) {
            return existing
        }

        synchronized(lock) {
            val cached = router
            if (cached != null) {
                return cached
            }

            val hub = ortHub ?: OrtHub().also { created ->
                created.init(context)
                ortHub = created
            }
            val registry = hub.skillRegistry()
            ensureShareSkill(registry)

            val telemetryInstance = telemetry(context)
            val created = Router(registry, telemetryInstance)
            router = created
            return created
        }
    }

    fun telemetry(context: Context): Telemetry {
        val existing = telemetryInstance
        if (existing != null) {
            return existing
        }

        synchronized(lock) {
            val cached = telemetryInstance
            if (cached != null) {
                return cached
            }

            val created = Telemetry(context)
            telemetryInstance = created
            return created
        }
    }

    fun tts(context: Context): TTS {
        val existing = tts
        if (existing != null) {
            return existing
        }

        synchronized(lock) {
            val cached = tts
            if (cached != null) {
                return cached
            }

            val created = TTS { _ ->
                val telemetry = telemetry(context)
                TTS.TelemetryRecorder.fromTelemetry(telemetry)
            }.apply { initialize() }
            tts = created
            return created
        }
    }

    fun ocrProvider(context: Context): OcrProvider {
        return OcrProviderModule.resolve(context)
    }

    private fun ensureShareSkill(registry: SkillRegistry) {
        if (registry.isRegistered(SHARE_SKILL_ID)) {
            return
        }
        registry.registerSkill(
            SHARE_SKILL_ID,
            ShareTextSkillDescriptor()
        )
    }
}

internal class ShareIntentProcessor(
    private val context: Context,
    private val router: Router,
    private val tts: TTS,
    private val ocrProvider: OcrProvider,
    private val telemetry: Telemetry
) {
    fun process(intent: Intent?): Boolean {
        if (intent == null) {
            telemetry.recordShareInEvent("missing_intent")
            return false
        }

        val action = intent.action ?: run {
            telemetry.recordShareInEvent("missing_action")
            return false
        }
        if (action != Intent.ACTION_SEND && action != Intent.ACTION_SEND_MULTIPLE) {
            telemetry.recordShareInEvent("unsupported_action", mapOf("action" to action))
            return false
        }

        telemetry.recordShareInEvent("intent_received", mapOf("action" to action))

        val fragments = mutableListOf<String>()
        val textExtra = intent.getCharSequenceExtra(Intent.EXTRA_TEXT)?.toString()?.trim().orEmpty()
        if (textExtra.isNotBlank()) {
            fragments += textExtra
        }

        val streamUris = intent.extractStreamUris()
        if (streamUris.isNotEmpty()) {
            val resolved = ocrProvider.extractText(context, streamUris)
            if (resolved.isNotBlank()) {
                fragments += resolved
            }
        }

        telemetry.recordShareInEvent(
            "payload_collected",
            mapOf(
                "fragments" to fragments.size,
                "streams" to streamUris.size
            )
        )

        val aggregated = fragments.joinToString(separator = "\n") { it.trim() }
            .lines()
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .joinToString(separator = "\n")

        if (aggregated.isBlank()) {
            telemetry.recordShareInEvent("empty_payload", mapOf("action" to action))
            return false
        }

        telemetry.recordShareInEvent(
            "payload_ready",
            mapOf(
                "length" to aggregated.length
            )
        )

        val payload = ShareTextPayload(aggregated)
        val result = router.routeSkill<ShareTextPayload, ShareTextPayload, ShareTextResult>(
            SHARE_SKILL_ID,
            payload
        )

        val spokenText = when (result) {
            is Router.RouteResult.Success -> {
                telemetry.recordShareInEvent(
                    "router_result",
                    mapOf(
                        "outcome" to "success",
                        "skill" to SHARE_SKILL_ID
                    )
                )
                result.value.text.ifBlank { aggregated }
            }

            is Router.RouteResult.Failure -> {
                telemetry.recordShareInEvent(
                    "router_result",
                    mapOf(
                        "outcome" to "failure",
                        "skill" to SHARE_SKILL_ID,
                        "error" to (result.error.message ?: result.error.javaClass.simpleName)
                    )
                )
                aggregated
            }
        }

        telemetry.recordShareInEvent(
            "tts_requested",
            mapOf(
                "characters" to spokenText.length
            )
        )
        val start = System.nanoTime()
        val ttsSuccess = tts.speak(spokenText)
        val elapsedMs = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start)
        telemetry.recordTts(elapsedMs, spokenText.length, ttsSuccess)
        telemetry.recordShareInEvent(
            "tts_completed",
            mapOf(
                "success" to ttsSuccess,
                "duration_ms" to elapsedMs,
                "characters" to spokenText.length
            )
        )
        return true
    }
}

internal data class ShareTextPayload(val text: String)

internal data class ShareTextResult(val text: String)

private class ShareTextSkillDescriptor : SkillDescriptor<ShareTextPayload, ShareTextPayload, ShareTextResult> {
    override fun buildFeatures(payload: ShareTextPayload): ShareTextPayload = payload

    override val runner: SkillRunner<ShareTextPayload, ShareTextResult> =
        SkillRunner { features -> ShareTextResult(features.text) }
}

private fun Intent.extractStreamUris(): List<Uri> {
    return when (action) {
        Intent.ACTION_SEND -> listOfNotNull(singleUriExtra())
        Intent.ACTION_SEND_MULTIPLE -> multipleUriExtras()
        else -> emptyList()
    }
}

@Suppress("DEPRECATION")
private fun Intent.singleUriExtra(): Uri? {
    return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
    } else {
        getParcelableExtra(Intent.EXTRA_STREAM)
    }
}

@Suppress("DEPRECATION")
private fun Intent.multipleUriExtras(): List<Uri> {
    return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        getParcelableArrayListExtra(Intent.EXTRA_STREAM, Uri::class.java)?.filterNotNull() ?: emptyList()
    } else {
        @Suppress("UNCHECKED_CAST")
        val legacy = getParcelableArrayListExtra<Uri>(Intent.EXTRA_STREAM)
        legacy?.filterNotNull() ?: emptyList()
    }
}
