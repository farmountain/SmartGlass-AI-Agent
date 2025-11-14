package rayskillkit.core

import org.junit.Assert.*
import org.junit.Test

/**
 * Unit tests for Decision object with sigma gating and health disclaimers.
 */
class DecisionTest {

    @Test
    fun testHealthSkillAboveSigmaGate_Proceeds() {
        val outcome = Decision.makeDecision("hc_gait_guard", 0.85f, "Low fall risk detected")
        assertEquals("proceed", outcome.action)
        assertEquals(0.85f, outcome.confidence, 0.001f)
        assertTrue(outcome.message.contains("This information is for general awareness only"))
        assertTrue(outcome.message.contains("Low fall risk detected"))
    }

    @Test
    fun testHealthSkillAtSigmaGate_Proceeds() {
        val outcome = Decision.makeDecision("hc_gait_guard", 0.82f, "Gait analysis complete")
        assertEquals("proceed", outcome.action)
        assertEquals(0.82f, outcome.confidence, 0.001f)
        assertTrue(outcome.message.contains("This information is for general awareness only"))
    }

    @Test
    fun testHealthSkillBelowSigmaGate_Asks() {
        val outcome = Decision.makeDecision("hc_gait_guard", 0.75f, "Gait analysis uncertain")
        assertEquals("ask", outcome.action)
        assertEquals(0.75f, outcome.confidence, 0.001f)
        assertTrue(outcome.message.contains("This information is for general awareness only"))
    }

    @Test
    fun testMedSentinelHighThreshold_BelowAsk() {
        val outcome = Decision.makeDecision("hc_med_sentinel", 0.85f, "Checking interactions")
        assertEquals("ask", outcome.action)
        assertEquals(0.85f, outcome.confidence, 0.001f)
        assertTrue(outcome.message.contains("This information is for general awareness only"))
    }

    @Test
    fun testMedSentinelAboveThreshold_Proceeds() {
        val outcome = Decision.makeDecision("hc_med_sentinel", 0.90f, "No interactions found")
        assertEquals("proceed", outcome.action)
        assertEquals(0.90f, outcome.confidence, 0.001f)
        assertTrue(outcome.message.contains("This information is for general awareness only"))
    }

    @Test
    fun testSunHydroAboveThreshold_Proceeds() {
        val outcome = Decision.makeDecision("hc_sun_hydro", 0.80f, "Moderate sun exposure")
        assertEquals("proceed", outcome.action)
        assertEquals(0.80f, outcome.confidence, 0.001f)
        assertTrue(outcome.message.contains("This information is for general awareness only"))
    }

    @Test
    fun testSunHydroBelowThreshold_Asks() {
        val outcome = Decision.makeDecision("hc_sun_hydro", 0.70f, "Sun exposure uncertain")
        assertEquals("ask", outcome.action)
        assertEquals(0.70f, outcome.confidence, 0.001f)
        assertTrue(outcome.message.contains("This information is for general awareness only"))
    }

    @Test
    fun testNonHealthSkill_AlwaysProceeds() {
        val outcome = Decision.makeDecision("travel_fastlane", 0.50f, "Wait time: 15 minutes")
        assertEquals("proceed", outcome.action)
        assertEquals(0.50f, outcome.confidence, 0.001f)
        assertFalse(outcome.message.contains("This information is for general awareness only"))
        assertEquals("Wait time: 15 minutes", outcome.message)
    }

    @Test
    fun testNonHealthSkill_NoDisclaimer() {
        val outcome = Decision.makeDecision("skill_001", 0.95f, "Route calculated")
        assertEquals("proceed", outcome.action)
        assertEquals(0.95f, outcome.confidence, 0.001f)
        assertEquals("Route calculated", outcome.message)
        assertFalse(outcome.message.contains("This information is for general awareness only"))
    }

    @Test
    fun testHealthSkillWithEmptyMessage_OnlyDisclaimer() {
        val outcome = Decision.makeDecision("hc_gait_guard", 0.85f, "")
        assertEquals("proceed", outcome.action)
        assertEquals("This information is for general awareness only and does not constitute medical advice. " +
                     "Please consult a healthcare professional for medical concerns.", outcome.message)
    }

    @Test
    fun testNonHealthSkillWithEmptyMessage_EmptyResult() {
        val outcome = Decision.makeDecision("travel_fastlane", 0.80f, "")
        assertEquals("proceed", outcome.action)
        assertEquals("", outcome.message)
    }

    @Test
    fun testDisclaimerFormat_ProperlyFormatted() {
        val outcome = Decision.makeDecision("hc_med_sentinel", 0.90f, "Analysis complete")
        assertTrue(outcome.message.startsWith("Analysis complete"))
        assertTrue(outcome.message.contains("\n\n"))
        assertTrue(outcome.message.endsWith("Please consult a healthcare professional for medical concerns."))
    }

    @Test
    fun testHasSigmaGate_HealthSkills() {
        assertTrue(Decision.hasSigmaGate("hc_gait_guard"))
        assertTrue(Decision.hasSigmaGate("hc_med_sentinel"))
        assertTrue(Decision.hasSigmaGate("hc_sun_hydro"))
    }

    @Test
    fun testHasSigmaGate_NonHealthSkills() {
        assertFalse(Decision.hasSigmaGate("travel_fastlane"))
        assertFalse(Decision.hasSigmaGate("skill_001"))
        assertFalse(Decision.hasSigmaGate("unknown_skill"))
    }

    @Test
    fun testGetSigmaGate_CorrectThresholds() {
        assertEquals(0.82f, Decision.getSigmaGate("hc_gait_guard")!!, 0.001f)
        assertEquals(0.88f, Decision.getSigmaGate("hc_med_sentinel")!!, 0.001f)
        assertEquals(0.78f, Decision.getSigmaGate("hc_sun_hydro")!!, 0.001f)
    }

    @Test
    fun testGetSigmaGate_NonHealthSkill_ReturnsNull() {
        assertNull(Decision.getSigmaGate("travel_fastlane"))
        assertNull(Decision.getSigmaGate("skill_001"))
    }

    @Test
    fun testLegacyDecisionData_BackwardCompatibility() {
        val decision = DecisionData(
            id = "test_001",
            skillName = "TestSkill",
            confidence = 0.75f,
            metadata = mapOf("key" to "value")
        )
        
        assertEquals("test_001", decision.id)
        assertEquals("TestSkill", decision.skillName)
        assertEquals(0.75f, decision.confidence, 0.001f)
        assertTrue(decision.isConfident(0.5f))
        assertFalse(decision.isConfident(0.8f))
    }

    @Test
    fun testConfidenceBoundaries() {
        // Test at 0.0
        val lowOutcome = Decision.makeDecision("hc_gait_guard", 0.0f, "Test")
        assertEquals("ask", lowOutcome.action)

        // Test at 1.0
        val highOutcome = Decision.makeDecision("hc_gait_guard", 1.0f, "Test")
        assertEquals("proceed", highOutcome.action)
    }

    @Test
    fun testAllHealthSkillsHaveDisclaimer() {
        val healthSkills = listOf("hc_gait_guard", "hc_med_sentinel", "hc_sun_hydro")
        
        for (skill in healthSkills) {
            val outcome = Decision.makeDecision(skill, 0.95f, "Test message")
            assertTrue("$skill should have disclaimer", 
                outcome.message.contains("This information is for general awareness only"))
        }
    }

    @Test
    fun testSkillIdPrefixMatching() {
        // Any skill starting with "hc_" should get disclaimer
        val outcome1 = Decision.makeDecision("hc_custom_skill", 0.90f, "Test")
        assertTrue(outcome1.message.contains("This information is for general awareness only"))

        // Skills not starting with "hc_" should not get disclaimer
        val outcome2 = Decision.makeDecision("custom_hc_skill", 0.90f, "Test")
        assertFalse(outcome2.message.contains("This information is for general awareness only"))
    }
}
