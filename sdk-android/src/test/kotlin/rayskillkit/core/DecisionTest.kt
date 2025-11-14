package rayskillkit.core

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

class DecisionTest {
    @Test
    fun decideFallsBackToAskWhenBelowSigmaGate() {
        val decision = Decision(
            id = "decision-001",
            skillName = "hc_gait_guard",
            confidence = 0.28f,
            metadata = mapOf("sigmaGate" to 0.3f)
        )

        val outcome = decision.decide()

        assertEquals("ask", outcome.action)
        assertEquals(0.3f, outcome.metadata["sigmaGate"])

        val disclaimers = outcome.metadata["complianceDisclaimers"] as? Map<*, *>
        assertNotNull(disclaimers, "Health skills must include compliance disclaimers")
        assertTrue(
            (disclaimers["en-US"] as? List<*>)?.all { it is String && it.isNotBlank() } == true,
            "English compliance disclaimers should be present and non-blank"
        )
        assertTrue(
            (disclaimers["zh-CN"] as? List<*>)?.all { it is String && it.isNotBlank() } == true,
            "Simplified Chinese compliance disclaimers should be present and non-blank"
        )
    }

    @Test
    fun decideReturnsSkillNameWhenAboveGateWithoutInjectingDisclaimers() {
        val decision = Decision(
            id = "decision-002",
            skillName = "travel_planner",
            confidence = 0.82f
        )

        val outcome = decision.decide(sigmaGateOverride = 0.6f)

        assertEquals("travel_planner", outcome.action)
        assertTrue("complianceDisclaimers" !in outcome.metadata)
        assertEquals(0.6f, outcome.metadata["sigmaGate"])
    }
}
