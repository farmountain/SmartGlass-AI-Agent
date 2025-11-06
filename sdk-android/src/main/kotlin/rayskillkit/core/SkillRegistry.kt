package rayskillkit.core

class SkillRegistry {
    private val skills = mutableMapOf<String, SkillDescriptor<*, *, *>>()

    fun <Payload : Any, Features : Any, Result : Any> registerSkill(
        name: String,
        descriptor: SkillDescriptor<Payload, Features, Result>
    ) {
        skills[name] = descriptor
    }

    fun unregisterSkill(name: String) {
        skills.remove(name)
    }

    @Suppress("UNCHECKED_CAST")
    fun <Payload : Any, Features : Any, Result : Any> getSkill(
        name: String
    ): SkillDescriptor<Payload, Features, Result>? {
        return skills[name] as? SkillDescriptor<Payload, Features, Result>
    }

    fun listSkills(): Set<String> = skills.keys
}
