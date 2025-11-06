package rayskillkit.core

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

class SkillRegistryTest {
    @Test
    fun initializeFromResourceRegistersSkillsAndTriggers() {
        val registry = SkillRegistry()
        val runners = mutableMapOf<String, SkillRunner<FloatArray, FloatArray>>()

        registry.initializeFromResource { skillId ->
            val runner = SkillRunner<FloatArray, FloatArray> { features -> features }
            runners[skillId] = runner
            runner
        }

        assertTrue(registry.isRegistered("education_assistant"))
        assertTrue(registry.isRegistered("travel_planner"))

        val triggers = registry.listTriggers()
        assertTrue("education" in triggers)
        assertTrue("journey" in triggers)

        val educationIds = registry.findSkillIdsForTrigger("education")
        assertEquals(setOf("education_assistant"), educationIds)

        val descriptor = registry.getSkill<FeaturePayload, FloatArray, FloatArray>("education_assistant")
        assertNotNull(descriptor)

        val retrieved = registry.getSkillByTrigger<FeaturePayload, FloatArray, FloatArray>("travel")
        assertNotNull(retrieved)

        val registration = registry.getRegistration<FeaturePayload, FloatArray, FloatArray>("travel_planner")
        assertNotNull(registration)
        assertTrue(registration.runner === runners["travel_planner"])
    }
}
