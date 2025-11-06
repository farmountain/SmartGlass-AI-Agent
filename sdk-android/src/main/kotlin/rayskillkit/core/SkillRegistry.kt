package rayskillkit.core

import org.json.JSONArray
import org.json.JSONObject
import java.io.InputStream

private const val DEFAULT_SKILLS_RESOURCE = "skills.json"

data class SkillRegistration<Payload : Any, Features : Any, Result : Any>(
    val id: String,
    val triggerPhrases: Set<String>,
    val featureBuilder: SkillFeatureBuilder?,
    val descriptor: SkillDescriptor<Payload, Features, Result>,
    val runner: SkillRunner<Features, Result> = descriptor.runner
)

class SkillRegistry {
    private val skills = mutableMapOf<String, SkillRegistration<*, *, *>>()
    private val triggers = mutableMapOf<String, MutableSet<String>>()

    fun initializeFromResource(
        resourceName: String = DEFAULT_SKILLS_RESOURCE,
        runnerFactory: (String) -> SkillRunner<FloatArray, FloatArray> = { SkillRunner { features -> features } }
    ) {
        val stream = locateResource(resourceName)
            ?: throw IllegalStateException("Unable to locate $resourceName on the classpath.")

        stream.use { input ->
            initializeFromStream(input, runnerFactory)
        }
    }

    fun initializeFromStream(
        stream: InputStream,
        runnerFactory: (String) -> SkillRunner<FloatArray, FloatArray> = { SkillRunner { features -> features } }
    ) {
        loadDefinitions(stream).forEach { definition ->
            val featureBuilder = builderForSkill(definition.featureBuilder)
                ?: throw IllegalArgumentException(
                    "Unknown feature builder '${definition.featureBuilder}' for skill '${definition.id}'"
                )

            val descriptor = FeatureBuilderDescriptor(featureBuilder, runnerFactory(definition.id))
            val registration = SkillRegistration(
                id = definition.id,
                triggerPhrases = definition.triggerPhrases,
                featureBuilder = featureBuilder,
                descriptor = descriptor
            )
            registerSkill(registration)
        }
    }

    fun <Payload : Any, Features : Any, Result : Any> registerSkill(
        registration: SkillRegistration<Payload, Features, Result>
    ) {
        val normalizedRegistration = registration.copy(
            triggerPhrases = registration.triggerPhrases.map(::normalizeTrigger).toSet()
        )

        unregisterSkill(normalizedRegistration.id)
        skills[normalizedRegistration.id] = normalizedRegistration
        normalizedRegistration.triggerPhrases.forEach { trigger ->
            triggers.getOrPut(trigger) { mutableSetOf() }.add(normalizedRegistration.id)
        }
    }

    fun <Payload : Any, Features : Any, Result : Any> registerSkill(
        name: String,
        descriptor: SkillDescriptor<Payload, Features, Result>,
        triggerPhrases: Set<String> = emptySet(),
        featureBuilder: SkillFeatureBuilder? = null
    ) {
        registerSkill(
            SkillRegistration(
                id = name,
                triggerPhrases = triggerPhrases,
                featureBuilder = featureBuilder,
                descriptor = descriptor
            )
        )
    }

    fun unregisterSkill(id: String) {
        val removed = skills.remove(id) ?: return
        removed.triggerPhrases.forEach { trigger ->
            val skillIds = triggers[trigger] ?: return@forEach
            skillIds.remove(id)
            if (skillIds.isEmpty()) {
                triggers.remove(trigger)
            }
        }
    }

    @Suppress("UNCHECKED_CAST")
    fun <Payload : Any, Features : Any, Result : Any> getSkill(
        id: String
    ): SkillDescriptor<Payload, Features, Result>? {
        return (skills[id] as? SkillRegistration<Payload, Features, Result>)?.descriptor
    }

    @Suppress("UNCHECKED_CAST")
    fun <Payload : Any, Features : Any, Result : Any> getRegistration(
        id: String
    ): SkillRegistration<Payload, Features, Result>? {
        return skills[id] as? SkillRegistration<Payload, Features, Result>
    }

    fun <Payload : Any, Features : Any, Result : Any> getSkillByTrigger(
        trigger: String
    ): SkillDescriptor<Payload, Features, Result>? {
        val skillId = triggers[normalizeTrigger(trigger)]?.firstOrNull() ?: return null
        return getSkill(skillId)
    }

    fun findSkillIdsForTrigger(trigger: String): Set<String> =
        triggers[normalizeTrigger(trigger)]?.toSet() ?: emptySet()

    fun listTriggers(): Set<String> = triggers.keys

    fun isRegistered(id: String): Boolean = skills.containsKey(id)

    fun listSkills(): Set<String> = skills.keys

    fun registrations(): Collection<SkillRegistration<*, *, *>> = skills.values

    private fun normalizeTrigger(trigger: String): String = trigger.trim().lowercase()

    private fun loadDefinitions(stream: InputStream): List<SkillDefinition> {
        val content = stream.bufferedReader().use { it.readText() }
        if (content.isBlank()) {
            return emptyList()
        }

        val root = JSONObject(content)
        val skillsArray = root.optJSONArray("skills") ?: return emptyList()
        return buildList {
            for (index in 0 until skillsArray.length()) {
                val skill = skillsArray.getJSONObject(index)
                val id = skill.getString("id")
                val featureBuilder = skill.getString("featureBuilder")
                val triggers = parseTriggers(skill)
                add(
                    SkillDefinition(
                        id = id,
                        featureBuilder = featureBuilder,
                        triggerPhrases = triggers
                    )
                )
            }
        }
    }

    private fun locateResource(resourceName: String): InputStream? {
        val classLoader = SkillRegistry::class.java.classLoader
        return classLoader?.getResourceAsStream(resourceName)
    }

    private fun parseTriggers(skillObject: JSONObject): Set<String> {
        val triggers = mutableSetOf<String>()
        when {
            skillObject.has("triggers") -> triggers += readTriggerArray(skillObject.getJSONArray("triggers"))
            skillObject.has("triggerPhrases") -> triggers += readTriggerArray(skillObject.getJSONArray("triggerPhrases"))
            skillObject.has("trigger") -> triggers += normalizeTrigger(skillObject.getString("trigger"))
        }
        return triggers
    }

    private fun readTriggerArray(array: JSONArray): Set<String> {
        val result = mutableSetOf<String>()
        for (index in 0 until array.length()) {
            val trigger = array.optString(index)
            if (trigger.isNotBlank()) {
                result += normalizeTrigger(trigger)
            }
        }
        return result
    }

    private data class SkillDefinition(
        val id: String,
        val featureBuilder: String,
        val triggerPhrases: Set<String>
    )

    private class FeatureBuilderDescriptor(
        private val builder: SkillFeatureBuilder,
        override val runner: SkillRunner<FloatArray, FloatArray>
    ) : SkillDescriptor<FeaturePayload, FloatArray, FloatArray> {
        override fun buildFeatures(payload: FeaturePayload): FloatArray = builder.build(payload)
    }
}
