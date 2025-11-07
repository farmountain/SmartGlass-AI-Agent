package rayskillkit.core

import android.content.Context
import java.io.InputStream
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths

private const val SKILLS_ASSET_NAME = "skills.json"

class OrtHub(
    private val registry: SkillRegistry = SkillRegistry(),
    private val ortWrapper: OrtWrapper = defaultOrtWrapper(),
) {
    private val connectedEndpoints = mutableSetOf<String>()
    private val sessions = mutableMapOf<String, OrtSession>()
    private var initialized = false

    fun init(context: Context? = null) {
        if (initialized) {
            return
        }

        val runnerFactory: (String) -> SkillRunner<FloatArray, FloatArray> = { skillId ->
            val session = ensureSession(skillId)
            SkillRunner { features -> session.run(features) }
        }

        loadSkillsMetadata(context).use { stream ->
            registry.initializeFromStream(stream, runnerFactory)
        }

        registry.registrations().forEach { registration ->
            ensureSession(registration.id)
        }

        initialized = true
    }

    fun connect(endpoint: String): Boolean {
        connectedEndpoints += endpoint
        return true
    }

    fun disconnect(endpoint: String) {
        connectedEndpoints -= endpoint
    }

    fun isConnected(endpoint: String): Boolean = endpoint in connectedEndpoints

    fun session(skillId: String): OrtSession? = sessions[skillId]

    fun skillRegistry(): SkillRegistry = registry

    private fun ensureSession(skillId: String): OrtSession =
        sessions.getOrPut(skillId) { OrtSession(skillId, ortWrapper) }

    private fun loadSkillsMetadata(context: Context?): InputStream {
        val assetStream = context?.let {
            runCatching { it.assets.open(SKILLS_ASSET_NAME) }.getOrNull()
        }
        if (assetStream != null) {
            return assetStream
        }

        val classLoaderStream = javaClass.classLoader?.getResourceAsStream(SKILLS_ASSET_NAME)
        if (classLoaderStream != null) {
            return classLoaderStream
        }

        val fallbackStream = fallbackPaths()
            .asSequence()
            .mapNotNull { path -> openIfExists(path) }
            .firstOrNull()

        return fallbackStream
            ?: throw IllegalStateException("Unable to locate skills asset '$SKILLS_ASSET_NAME'.")
    }

    private fun fallbackPaths(): List<Path> = listOf(
        Paths.get("sdk-android", "src", "test", "resources", SKILLS_ASSET_NAME),
        Paths.get("src", "test", "resources", SKILLS_ASSET_NAME)
    )

    private fun openIfExists(path: Path): InputStream? {
        if (Files.exists(path)) {
            return Files.newInputStream(path)
        }
        return null
    }
}

private fun defaultOrtWrapper(): OrtWrapper {
    return if (BuildConfig.USE_ANDROID_ORT) {
        AndroidOrtWrapper()
    } else {
        MockOrt()
    }
}

class OrtSession(private val skillId: String, private val ortWrapper: OrtWrapper) {
    fun run(features: FloatArray): FloatArray = ortWrapper.infer(skillId, features)
    override fun toString(): String = "OrtSession(skillId=$skillId)"
}
