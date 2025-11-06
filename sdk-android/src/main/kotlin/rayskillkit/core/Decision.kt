package rayskillkit.core

data class Decision(
    val id: String,
    val skillName: String,
    val confidence: Float,
    val metadata: Map<String, Any?> = emptyMap()
) {
    fun isConfident(threshold: Float = 0.5f): Boolean = confidence >= threshold
}
