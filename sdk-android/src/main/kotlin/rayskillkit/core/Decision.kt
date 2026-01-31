package rayskillkit.core

data class Decision(
    val id: String,
    val skillName: String,
    val confidence: Float,
    val metadata: Map<String, Any?> = emptyMap()
) {
    /**
     * Check if confidence exceeds threshold.
     * 
     * WARNING: This uses raw model confidence which may not be calibrated.
     * For safety-critical decisions, use calibratedConfidence() instead.
     * 
     * @param threshold Minimum confidence level (default 0.5)
     * @return true if confidence >= threshold
     */
    fun isConfident(threshold: Float = 0.5f): Boolean = confidence >= threshold
    
    /**
     * Get calibrated confidence score using Expected Calibration Error correction.
     * 
     * Raw model confidence often doesn't match actual accuracy. This method applies
     * calibration based on historical accuracy data per confidence bucket.
     * 
     * Example: If model says 90% confident but historically only 70% accurate at
     * that level, this returns 0.70 instead of 0.90.
     * 
     * @param calibrationData Map of confidence buckets to actual accuracy
     * @return Calibrated confidence score [0.0, 1.0]
     */
    fun calibratedConfidence(
        calibrationData: Map<ConfidenceBucket, Float> = DEFAULT_CALIBRATION
    ): Float {
        val bucket = ConfidenceBucket.fromConfidence(confidence)
        return calibrationData[bucket] ?: confidence // Fallback to raw if no calibration
    }
    
    /**
     * Check if decision is safe for execution based on calibrated confidence.
     * 
     * Use this for safety-critical scenarios (medical, navigation, financial).
     * 
     * @param threshold Minimum calibrated confidence (default 0.8 for safety)
     * @return true if calibratedConfidence >= threshold
     */
    fun isSafeToExecute(threshold: Float = SAFETY_THRESHOLD): Boolean {
        return calibratedConfidence() >= threshold
    }

    fun decide(
        sigmaGateOverride: Float? = null,
        complianceDisclaimers: Map<String, List<String>> = HEALTH_COMPLIANCE_DISCLAIMERS
    ): DecisionOutcome {
        val sigmaGate = sigmaGateOverride ?: metadata.extractSigmaGate(DEFAULT_SIGMA_GATE)
        val action = if (confidence >= sigmaGate) skillName else ASK_OUTCOME

        val decoratedMetadata = metadata
            .withComplianceDisclaimersIfNeeded(skillName, complianceDisclaimers)
            .ensureSigmaGateRecorded(sigmaGate)

        return DecisionOutcome(action, decoratedMetadata)
    }

    private fun Map<String, Any?>.withComplianceDisclaimersIfNeeded(
        skillName: String,
        complianceDisclaimers: Map<String, List<String>>
    ): Map<String, Any?> {
        if (!skillName.startsWith(HEALTH_SKILL_PREFIX)) return this
        if (containsKey(COMPLIANCE_DISCLAIMERS_KEY)) return this
        return this + mapOf(COMPLIANCE_DISCLAIMERS_KEY to complianceDisclaimers)
    }

    private fun Map<String, Any?>.ensureSigmaGateRecorded(sigmaGate: Float): Map<String, Any?> {
        if (containsKey(SIGMA_GATE_KEY)) return this
        return this + mapOf(SIGMA_GATE_KEY to sigmaGate)
    }

    companion object {
        private const val DEFAULT_SIGMA_GATE = 0.5f
        private const val SAFETY_THRESHOLD = 0.8f // Higher bar for safety-critical decisions
        private const val HEALTH_SKILL_PREFIX = "hc_"
        private const val COMPLIANCE_DISCLAIMERS_KEY = "complianceDisclaimers"
        private const val SIGMA_GATE_KEY = "sigmaGate"
        private const val ASK_OUTCOME = "ask"
        
        /**
         * Default calibration mapping from model confidence buckets to actual accuracy.
         * 
         * These values should be updated based on A/B testing and real-world accuracy
         * measurements. Current values are conservative estimates.
         */
        private val DEFAULT_CALIBRATION: Map<ConfidenceBucket, Float> = mapOf(
            ConfidenceBucket.VERY_LOW to 0.3f,    // Model says 0-20% → Actually ~30% accurate
            ConfidenceBucket.LOW to 0.45f,         // Model says 20-40% → Actually ~45%
            ConfidenceBucket.MEDIUM to 0.6f,       // Model says 40-60% → Actually ~60%
            ConfidenceBucket.HIGH to 0.75f,        // Model says 60-80% → Actually ~75%
            ConfidenceBucket.VERY_HIGH to 0.88f    // Model says 80-100% → Actually ~88%
        )

        private val HEALTH_COMPLIANCE_DISCLAIMERS: Map<String, List<String>> = mapOf(
            "en-US" to listOf(
                "Health coaching insights are informational only and not a substitute for professional medical advice.",
                "If you are experiencing an emergency, contact local emergency services immediately."
            ),
            "zh-CN" to listOf(
                "健康指导内容仅供参考，不能替代专业医疗意见。",
                "如遇紧急情况，请立即联系当地紧急救援部门。"
            )
        )
    }
}

/**
 * Confidence buckets for calibration mapping.
 * 
 * Divides the [0, 1] confidence range into discrete buckets for
 * Expected Calibration Error (ECE) calculation.
 */
enum class ConfidenceBucket(val range: ClosedFloatingPointRange<Float>) {
    VERY_LOW(0.0f..0.2f),
    LOW(0.2f..0.4f),
    MEDIUM(0.4f..0.6f),
    HIGH(0.6f..0.8f),
    VERY_HIGH(0.8f..1.0f);
    
    companion object {
        fun fromConfidence(confidence: Float): ConfidenceBucket {
            return values().first { confidence in it.range }
        }
    }
}

data class DecisionOutcome(
    val action: String,
    val metadata: Map<String, Any?>
)

private fun Map<String, Any?>.extractSigmaGate(default: Float): Float {
    val candidates = listOf("sigmaGate", "sigma_gate", "sigma")
    for (key in candidates) {
        val value = this[key] ?: continue
        when (value) {
            is Number -> return value.toFloat()
            is String -> value.toFloatOrNull()?.let { return it }
        }
    }
    return default
}
