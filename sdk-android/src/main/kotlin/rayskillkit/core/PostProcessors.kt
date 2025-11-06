package rayskillkit.core

/**
 * Represents a localized summary emitted after a skill has executed. The SDK currently
 * communicates the primary English summary alongside a Simplified Chinese translation
 * so UI surfaces can display both without additional translation layers.
 */
data class LocalizedSkillSummary(
    val english: String,
    val zhCN: String
) {
    fun asMap(): Map<String, String> = mapOf("en-US" to english, "zh-CN" to zhCN)

    fun isChineseTranslationAvailable(): Boolean = zhCN.isNotBlank()
}

fun interface SkillPostProcessor {
    fun process(output: FloatArray, metadata: Map<String, Any?> = emptyMap()): LocalizedSkillSummary
}

object SkillPostProcessors {
    private val processors: Map<String, SkillPostProcessor> = mapOf(
        "education_assistant" to SkillPostProcessor { _, metadata ->
            val subject = metadata["subject"]?.toString()?.takeIf { it.isNotBlank() } ?: "学习"
            LocalizedSkillSummary(
                english = "Personalized study guidance prepared for $subject",
                zhCN = "已为$subject准备个性化学习指导"
            )
        },
        "retail_helper" to SkillPostProcessor { output, metadata ->
            val product = metadata["product"]?.toString()?.takeIf { it.isNotBlank() } ?: "商品"
            val price = metadata["price"]?.toString()?.takeIf { it.isNotBlank() }
            val topScore = output.maxOrNull() ?: 0f
            val englishSummary = buildString {
                append("Retail recommendation for $product")
                append(" (score %.2f".format(topScore))
                append(')')
                if (price != null) {
                    append(", priced at $price")
                }
            }
            val chineseSummary = buildString {
                append("推荐$product，评分%.2f".format(topScore))
                if (price != null) {
                    append("，价格$price")
                }
            }
            LocalizedSkillSummary(englishSummary, chineseSummary)
        },
        "travel_planner" to SkillPostProcessor { output, metadata ->
            val destination = metadata["destination"]?.toString()?.takeIf { it.isNotBlank() } ?: "旅程"
            val itinerary = metadata["itinerary"]?.toString()?.takeIf { it.isNotBlank() }
            val confidence = output.maxOrNull()?.coerceIn(0f, 1f) ?: 0f
            val englishSummary = buildString {
                append("Itinerary generated for $destination")
                append(" with %.0f%% confidence".format(confidence * 100f))
                if (itinerary != null) {
                    append(": $itinerary")
                }
            }
            val chineseSummary = buildString {
                append("已为$destination规划行程，置信度%.0f%%".format(confidence * 100f))
                if (itinerary != null) {
                    append("：$itinerary")
                }
            }
            LocalizedSkillSummary(englishSummary, chineseSummary)
        }
    )

    fun postProcess(
        skillId: String,
        output: FloatArray,
        metadata: Map<String, Any?> = emptyMap()
    ): LocalizedSkillSummary {
        val processor = processors[skillId] ?: defaultProcessor(skillId)
        return processor.process(output, metadata)
    }

    private fun defaultProcessor(skillId: String): SkillPostProcessor = SkillPostProcessor { _, metadata ->
        val english = metadata["summary"]?.toString()?.takeIf { it.isNotBlank() }
            ?: "Skill $skillId completed"
        val chinese = metadata["summaryZh"]?.toString()?.takeIf { it.isNotBlank() }
            ?: "技能$skillId已完成"
        LocalizedSkillSummary(english, chinese)
    }
}

