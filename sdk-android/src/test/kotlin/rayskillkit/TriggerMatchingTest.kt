package rayskillkit

import java.io.ByteArrayInputStream
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertSame
import rayskillkit.core.FeaturePayload
import rayskillkit.core.SkillFeatureBuilder
import rayskillkit.core.SkillRegistry
import rayskillkit.core.SkillRunner

class TriggerMatchingTest {
    @Test
    fun registryResolvesSkillsFromTriggerPhrases() {
        val registry = SkillRegistry()
        val definition = """
            {
              "skills": [
                {
                  "id": "education_assistant",
                  "featureBuilder": "education",
                  "triggers": ["Education", "learning"]
                },
                {
                  "id": "travel_planner",
                  "featureBuilder": "travel",
                  "triggers": ["trip", "Journey"]
                }
              ]
            }
        """.trimIndent()

        val runnerInvocations = mutableMapOf<String, Int>()

        registry.initializeFromStream(
            ByteArrayInputStream(definition.toByteArray()),
            runnerFactory = { skillId ->
                SkillRunner<FloatArray, FloatArray> { features ->
                    runnerInvocations[skillId] = runnerInvocations.getOrDefault(skillId, 0) + 1
                    features
                }
            }
        )

        assertEquals(setOf("education", "learning", "trip", "journey"), registry.listTriggers())

        val education = registry.getSkillByTrigger<FeaturePayload, FloatArray, FloatArray>("EDUCATION")
        assertNotNull(education)
        val educationFeatures = education.buildFeatures(emptyMap())
        assertEquals(64, educationFeatures.size)

        val travel = registry.getSkillByTrigger<FeaturePayload, FloatArray, FloatArray>("journey")
        assertNotNull(travel)
        val travelFeatures = travel.buildFeatures(mapOf("distanceKm" to 1000f))
        assertEquals(64, travelFeatures.size)

        val descriptor = registry.getSkill<FeaturePayload, FloatArray, FloatArray>("education_assistant")
        assertSame(education, descriptor)

        val builder = SkillFeatureBuilder.registry["education"]
        assertSame(SkillFeatureBuilder.Education, builder)

        // Execute the runners to ensure the mocked factory is used.
        education.runner.runSkill(educationFeatures)
        travel.runner.runSkill(travelFeatures)

        assertEquals(1, runnerInvocations["education_assistant"])
        assertEquals(1, runnerInvocations["travel_planner"])
    }
}

