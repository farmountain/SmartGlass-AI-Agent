package rayskillkit

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import rayskillkit.core.SkillPostProcessors

class PostProcessorLocalizationTest {
    @Test
    fun knownPostProcessorsReturnChineseSummaries() {
        val metadata = mapOf(
            "education_assistant" to mapOf("subject" to "数学辅导"),
            "retail_helper" to mapOf("product" to "智能眼镜", "price" to "¥3299"),
            "travel_planner" to mapOf("destination" to "北京", "itinerary" to "三日游")
        )

        val outputs = mapOf(
            "education_assistant" to floatArrayOf(0.92f, 0.07f),
            "retail_helper" to floatArrayOf(0.45f, 0.88f, 0.12f),
            "travel_planner" to floatArrayOf(0.63f, 0.41f, 0.27f)
        )

        outputs.forEach { (skillId, output) ->
            val summary = SkillPostProcessors.postProcess(skillId, output, metadata[skillId].orEmpty())
            assertTrue(summary.zhCN.containsChineseCharacters(), "Expected Chinese localization for $skillId")
            assertFalse(summary.zhCN.isBlank(), "Chinese localization should not be blank for $skillId")
        }
    }

    @Test
    fun defaultProcessorProvidesFallbackChineseString() {
        val summary = SkillPostProcessors.postProcess("unknown_skill", floatArrayOf(0.1f), emptyMap())
        assertTrue(summary.zhCN.containsChineseCharacters())
        assertTrue(summary.zhCN.contains("技能"))
    }

    private fun String.containsChineseCharacters(): Boolean = any { it.code in 0x4E00..0x9FFF }
}

