package rayskillkit.core

data class Decision(
    val id: String,
    val skillName: String,
    val confidence: Float,
    val metadata: Map<String, Any?> = emptyMap()
) {
    fun isConfident(threshold: Float = 0.5f): Boolean = confidence >= threshold

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
        private const val HEALTH_SKILL_PREFIX = "hc_"
        private const val COMPLIANCE_DISCLAIMERS_KEY = "complianceDisclaimers"
        private const val SIGMA_GATE_KEY = "sigmaGate"
        private const val ASK_OUTCOME = "ask"

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
