package rayskillkit

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import kotlin.test.fail
import rayskillkit.core.DEFAULT_FEATURE_INPUT_DIM
import rayskillkit.core.FeaturePayload
import rayskillkit.core.OrtHub
import rayskillkit.core.Router
import rayskillkit.core.SkillPostProcessors
import rayskillkit.core.Telemetry

class CoreIntegrationTest {
    @Test
    fun endToEndRoutingProducesChineseSummary() {
        val ortHub = OrtHub()
        ortHub.init()

        assertFalse(ortHub.isConnected("local"))
        assertTrue(ortHub.connect("local"))
        assertTrue(ortHub.isConnected("local"))

        val telemetry = Telemetry()
        val router = Router(ortHub.skillRegistry(), telemetry)

        val payload: FeaturePayload = mapOf(
            "gradeLevel" to 9f,
            "difficulty" to 6f,
            "question" to "How do I balance chemical equations?",
            "topic" to "science chemistry",
            "correctCount" to 7f,
            "incorrectCount" to 2f,
            "timeRemaining" to 18f,
            "equation" to "2H2 + O2 -> 2H2O",
            "needsStepByStep" to true
        )

        val result = router.routeSkill<FeaturePayload, FloatArray, FloatArray>(
            "education_assistant",
            payload
        )

        val featureVector = when (result) {
            is Router.RouteResult.Success -> result.value
            is Router.RouteResult.Failure -> fail("Expected success but router failed: ${result.error}")
        }

        assertEquals(DEFAULT_FEATURE_INPUT_DIM, featureVector.size)
        assertEquals(listOf("router.success.education_assistant"), telemetry.events())

        val localized = SkillPostProcessors.postProcess(
            skillId = "education_assistant",
            output = featureVector,
            metadata = mapOf("subject" to "化学")
        )

        assertTrue(localized.zhCN.containsChineseCharacters())

        ortHub.disconnect("local")
        assertFalse(ortHub.isConnected("local"))
    }

    private fun String.containsChineseCharacters(): Boolean = any { it.code in 0x4E00..0x9FFF }
}

