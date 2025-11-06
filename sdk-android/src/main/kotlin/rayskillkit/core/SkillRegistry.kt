package rayskillkit.core

class SkillRegistry {
    private val skills = mutableMapOf<String, Any>()

    fun registerSkill(name: String, handler: Any) {
        skills[name] = handler
    }

    fun unregisterSkill(name: String) {
        skills.remove(name)
    }

    fun getSkill(name: String): Any? = skills[name]

    fun listSkills(): Set<String> = skills.keys
}
