package rayskillkit.ui

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
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
            tts = ShareInGraph.tts(),
            ocrProvider = ShareInGraph.ocrProvider(applicationContext)
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

            val created = Router(registry, Telemetry())
            router = created
            return created
        }
    }

    fun tts(): TTS {
        val existing = tts
        if (existing != null) {
            return existing
        }

        synchronized(lock) {
            val cached = tts
            if (cached != null) {
                return cached
            }

            val created = TTS().apply { initialize() }
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
    private val ocrProvider: OcrProvider
) {
    fun process(intent: Intent?): Boolean {
        val action = intent?.action ?: return false
        if (action != Intent.ACTION_SEND && action != Intent.ACTION_SEND_MULTIPLE) {
            return false
        }

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

        val aggregated = fragments.joinToString(separator = "\n") { it.trim() }
            .lines()
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .joinToString(separator = "\n")

        if (aggregated.isBlank()) {
            return false
        }

        val payload = ShareTextPayload(aggregated)
        val result = router.routeSkill<ShareTextPayload, ShareTextPayload, ShareTextResult>(
            SHARE_SKILL_ID,
            payload
        )

        val spokenText = when (result) {
            is Router.RouteResult.Success -> result.value.text.ifBlank { aggregated }
            is Router.RouteResult.Failure -> aggregated
        }

        tts.speak(spokenText)
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
