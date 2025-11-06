package rayskillkit.core

class Router(private val registry: SkillRegistry) {
    fun route(skillName: String, payload: Any): Boolean {
        val skill = registry.getSkill(skillName) ?: return false
        // In a real implementation, the payload would be dispatched to the skill handler.
        // This placeholder simply indicates that the skill exists and can handle the payload.
        return skillName.isNotEmpty() && payload != null
    }
}
