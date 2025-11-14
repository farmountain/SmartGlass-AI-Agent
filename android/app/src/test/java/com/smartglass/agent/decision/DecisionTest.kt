package com.smartglass.agent.decision

import org.junit.Assert.*
import org.junit.Test

/**
 * Unit tests for Decision object.
 * 
 * Tests sigma gate thresholds, action determination, and health disclaimer injection.
 */
class DecisionTest {

    @Test
    fun testGaitGuardBelowThresholdAsks() {
        val result = Decision.decide("hc_gait_guard", 0.5, "Gait analysis complete.")
        assertEquals("ask", result.action)
        assertEquals(0.5, result.confidence, 0.001)
    }

    @Test
    fun testGaitGuardAboveThresholdProceeds() {
        val result = Decision.decide("hc_gait_guard", 0.8, "Gait analysis complete.")
        assertEquals("proceed", result.action)
        assertEquals(0.8, result.confidence, 0.001)
    }

    @Test
    fun testGaitGuardAtThresholdProceeds() {
        val result = Decision.decide("hc_gait_guard", 0.7, "Gait analysis complete.")
        assertEquals("proceed", result.action)
        assertEquals(0.7, result.confidence, 0.001)
    }

    @Test
    fun testMedSentinelBelowThresholdAsks() {
        val result = Decision.decide("hc_med_sentinel", 0.7, "Medication reminder set.")
        assertEquals("ask", result.action)
        assertEquals(0.7, result.confidence, 0.001)
    }

    @Test
    fun testMedSentinelAboveThresholdProceeds() {
        val result = Decision.decide("hc_med_sentinel", 0.85, "Medication reminder set.")
        assertEquals("proceed", result.action)
        assertEquals(0.85, result.confidence, 0.001)
    }

    @Test
    fun testMedSentinelAtThresholdProceeds() {
        val result = Decision.decide("hc_med_sentinel", 0.75, "Medication reminder set.")
        assertEquals("proceed", result.action)
        assertEquals(0.75, result.confidence, 0.001)
    }

    @Test
    fun testSunHydroBelowThresholdAsks() {
        val result = Decision.decide("hc_sun_hydro", 0.5, "Hydration level checked.")
        assertEquals("ask", result.action)
        assertEquals(0.5, result.confidence, 0.001)
    }

    @Test
    fun testSunHydroAboveThresholdProceeds() {
        val result = Decision.decide("hc_sun_hydro", 0.8, "Hydration level checked.")
        assertEquals("proceed", result.action)
        assertEquals(0.8, result.confidence, 0.001)
    }

    @Test
    fun testSunHydroAtThresholdProceeds() {
        val result = Decision.decide("hc_sun_hydro", 0.65, "Hydration level checked.")
        assertEquals("proceed", result.action)
        assertEquals(0.65, result.confidence, 0.001)
    }

    @Test
    fun testHealthSkillIncludesDisclaimer() {
        val result = Decision.decide("hc_gait_guard", 0.8, "Analysis complete.")
        assertTrue(result.message.contains("This is not medical advice"))
        assertTrue(result.message.contains("Consult a healthcare professional"))
        assertTrue(result.message.startsWith("Analysis complete."))
    }

    @Test
    fun testNonHealthSkillNoDisclaimer() {
        val result = Decision.decide("navigation_assist", 0.8, "Route calculated.")
        assertFalse(result.message.contains("This is not medical advice"))
        assertFalse(result.message.contains("Consult a healthcare professional"))
        assertEquals("Route calculated.", result.message)
    }

    @Test
    fun testHealthSkillWithEmptyMessage() {
        val result = Decision.decide("hc_med_sentinel", 0.9, "")
        assertTrue(result.message.contains("This is not medical advice"))
        assertTrue(result.message.trim().startsWith("[This is not medical advice"))
    }

    @Test
    fun testAllHealthSkillsHaveDisclaimer() {
        val healthSkills = listOf("hc_gait_guard", "hc_med_sentinel", "hc_sun_hydro")
        
        for (skill in healthSkills) {
            val result = Decision.decide(skill, 0.9, "Test message")
            assertTrue(
                "Skill $skill should include health disclaimer",
                result.message.contains("This is not medical advice")
            )
        }
    }

    @Test
    fun testSigmaGatesAreConfigured() {
        assertEquals(0.7, Decision.SIGMA_GATES["hc_gait_guard"], 0.001)
        assertEquals(0.75, Decision.SIGMA_GATES["hc_med_sentinel"], 0.001)
        assertEquals(0.65, Decision.SIGMA_GATES["hc_sun_hydro"], 0.001)
    }

    @Test
    fun testUnknownSkillUsesDefaultThreshold() {
        // Unknown skills should use default 0.5 threshold
        val belowDefault = Decision.decide("unknown_skill", 0.4, "Test")
        assertEquals("ask", belowDefault.action)
        
        val aboveDefault = Decision.decide("unknown_skill", 0.6, "Test")
        assertEquals("proceed", aboveDefault.action)
    }

    @Test
    fun testEdgeCaseZeroConfidence() {
        val result = Decision.decide("hc_gait_guard", 0.0, "Low confidence")
        assertEquals("ask", result.action)
    }

    @Test
    fun testEdgeCaseMaxConfidence() {
        val result = Decision.decide("hc_gait_guard", 1.0, "High confidence")
        assertEquals("proceed", result.action)
    }
}
