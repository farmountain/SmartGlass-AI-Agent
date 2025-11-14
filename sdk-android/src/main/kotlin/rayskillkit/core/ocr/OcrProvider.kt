package rayskillkit.core.ocr

import android.content.Context
import android.net.Uri
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import java.util.concurrent.TimeUnit

private const val DEFAULT_TIMEOUT_MS = 5_000L

interface OcrProvider {
    fun extractText(context: Context, uri: Uri): String

    fun extractText(context: Context, uris: Collection<Uri>): String =
        uris.joinToString(separator = "\n") { extractText(context, it).trim() }
            .lines()
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .joinToString(separator = "\n")
}

class MlKitOcrProvider(
    private val timeoutMs: Long = DEFAULT_TIMEOUT_MS
) : OcrProvider {
    override fun extractText(context: Context, uri: Uri): String {
        val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
        return try {
            val image = InputImage.fromFilePath(context, uri)
            val task = recognizer.process(image)
            val result = Tasks.await(task, timeoutMs, TimeUnit.MILLISECONDS)
            result?.text?.trim().orEmpty()
        } catch (error: Exception) {
            ""
        } finally {
            recognizer.close()
        }
    }
}

class MockOcrProvider(
    private val responses: MutableMap<Uri, String> = mutableMapOf(),
    private val defaultText: String = ""
) : OcrProvider {
    fun registerResponse(uri: Uri, text: String) {
        responses[uri] = text
    }

    override fun extractText(context: Context, uri: Uri): String {
        return responses[uri] ?: defaultText
    }
}

object OcrProviderModule {
    private val lock = Any()
    @Volatile
    private var cachedProvider: OcrProvider? = null
    @Volatile
    private var overrideFactory: ((Context) -> OcrProvider)? = null

    fun setOverride(factory: ((Context) -> OcrProvider)?) {
        synchronized(lock) {
            overrideFactory = factory
            cachedProvider = null
        }
    }

    fun resolve(context: Context): OcrProvider {
        overrideFactory?.let { factory ->
            return factory(context)
        }

        val existing = cachedProvider
        if (existing != null) {
            return existing
        }

        synchronized(lock) {
            val cached = cachedProvider
            if (cached != null) {
                return cached
            }
            val provider = MlKitOcrProvider()
            cachedProvider = provider
            return provider
        }
    }
}
