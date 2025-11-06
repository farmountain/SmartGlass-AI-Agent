package rayskillkit.core

import android.content.Context
import java.io.InputStream
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths

private const val SKILLS_ASSET_NAME = "skills.json"

class OrtHub(
    private val registry: SkillRegistry = SkillRegistry()
) {
    private val connectedEndpoints = mutableSetOf<String>()
    private val sessionStubs = mutableMapOf<String, OrtSessionStub>()
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

    fun sessionStub(skillId: String): OrtSessionStub? = sessionStubs[skillId]

    fun skillRegistry(): SkillRegistry = registry

    private fun ensureSession(skillId: String): OrtSessionStub =
        sessionStubs.getOrPut(skillId) { OrtSessionStub(skillId) }

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

class OrtSessionStub(private val skillId: String) {
    fun run(features: FloatArray): FloatArray = features
    override fun toString(): String = "OrtSessionStub(skillId=$skillId)"
}
