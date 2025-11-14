package com.smartglass.agent.decision

/**
 * Decision logic for health skills with sigma gate thresholds.
 * 
 * Provides decision-making functionality that determines whether to ask the user
 * for confirmation or proceed with an action based on confidence scores and
 * skill-specific sigma gate thresholds.
 */
object Decision {
    /**
     * Sigma gate thresholds for each health skill.
     * Confidence scores below these thresholds result in "ask" decisions.
     */
    val SIGMA_GATES = mapOf(
        "hc_gait_guard" to 0.7,
        "hc_med_sentinel" to 0.75,
        "hc_sun_hydro" to 0.65
    )

    /**
     * Health disclaimer injected for health-related skills.
     */
    private const val HEALTH_DISCLAIMER = 
        " [This is not medical advice. Consult a healthcare professional for medical guidance.]"

    /**
     * Result of a decision evaluation.
     *
     * @property action The decision action: "ask" or "proceed"
     * @property message The message to display, with disclaimer if applicable
     * @property confidence The confidence score used in the decision
     */
    data class DecisionOutcome(
        val action: String,
        val message: String,
        val confidence: Double
    )

    /**
     * Make a decision based on skill name, confidence, and optional base message.
     *
     * @param skillName The name of the skill being evaluated
     * @param confidence The confidence score (0.0 to 1.0)
     * @param baseMessage Optional base message to augment with disclaimers
     * @return DecisionOutcome containing action, message, and confidence
     */
    fun decide(
        skillName: String,
        confidence: Double,
        baseMessage: String = ""
    ): DecisionOutcome {
        // Get sigma gate threshold for this skill
        val gate = SIGMA_GATES[skillName] ?: 0.5
        
        // Determine action based on confidence vs threshold
        val action = if (confidence < gate) "ask" else "proceed"
        
        // Build message with health disclaimer if applicable
        val message = if (skillName.startsWith("hc_")) {
            baseMessage + HEALTH_DISCLAIMER
        } else {
            baseMessage
        }
        
        return DecisionOutcome(
            action = action,
            message = message,
            confidence = confidence
        )
    }
}
