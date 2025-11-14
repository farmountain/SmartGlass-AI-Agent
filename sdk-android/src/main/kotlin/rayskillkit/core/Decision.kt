package rayskillkit.core

/**
 * Decision outcome with action, message, and confidence.
 */
data class DecisionOutcome(
    val action: String,
    val message: String,
    val confidence: Float
)

/**
 * Decision object for handling skill-based decisions with sigma gating and health disclaimers.
 */
object Decision {
    /**
     * Sigma gate thresholds for health skills.
     * Skills with confidence below their threshold will result in "ask" action.
     */
    private val SIGMA_GATES = mapOf(
        "hc_gait_guard" to 0.82f,
        "hc_med_sentinel" to 0.88f,
        "hc_sun_hydro" to 0.78f
    )

    /**
     * Health disclaimer text for health-related skills.
     */
    private const val HEALTH_DISCLAIMER = 
        "This information is for general awareness only and does not constitute medical advice. " +
        "Please consult a healthcare professional for medical concerns."

    /**
     * Make a decision based on skill ID and confidence.
     *
     * @param skillId The skill identifier
     * @param confidence The confidence score (0.0 to 1.0)
     * @param baseMessage The base message without disclaimers
     * @return DecisionOutcome with action, message, and confidence
     */
    fun makeDecision(skillId: String, confidence: Float, baseMessage: String = ""): DecisionOutcome {
        val sigmaGate = SIGMA_GATES[skillId]
        
        val action = if (sigmaGate != null && confidence < sigmaGate) {
            "ask"
        } else {
            "proceed"
        }

        val message = if (skillId.startsWith("hc_")) {
            addDisclaimer(baseMessage)
        } else {
            baseMessage
        }

        return DecisionOutcome(action, message, confidence)
    }

    /**
     * Add health disclaimer to a message.
     *
     * @param message The original message
     * @return Message with disclaimer appended
     */
    private fun addDisclaimer(message: String): String {
        return if (message.isNotEmpty()) {
            "$message\n\n$HEALTH_DISCLAIMER"
        } else {
            HEALTH_DISCLAIMER
        }
    }

    /**
     * Check if a skill has a sigma gate threshold.
     *
     * @param skillId The skill identifier
     * @return true if skill has a sigma gate, false otherwise
     */
    fun hasSigmaGate(skillId: String): Boolean {
        return SIGMA_GATES.containsKey(skillId)
    }

    /**
     * Get the sigma gate threshold for a skill.
     *
     * @param skillId The skill identifier
     * @return The sigma gate threshold, or null if not defined
     */
    fun getSigmaGate(skillId: String): Float? {
        return SIGMA_GATES[skillId]
    }
}

/**
 * Legacy Decision data class for backward compatibility.
 * Prefer using Decision.makeDecision() for new code.
 */
data class DecisionData(
    val id: String,
    val skillName: String,
    val confidence: Float,
    val metadata: Map<String, Any?> = emptyMap()
) {
    fun isConfident(threshold: Float = 0.5f): Boolean = confidence >= threshold
}

