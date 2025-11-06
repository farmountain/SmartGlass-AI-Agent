package rayskillkit.core

import kotlin.test.Test
import kotlin.test.assertNotNull
import kotlin.test.assertSame
import kotlin.test.assertTrue

class OrtHubTest {
    @Test
    fun initLoadsSkillsUsingJvmFallback() {
        val registry = SkillRegistry()
        val hub = OrtHub(registry)

        hub.init()
        val firstStub = hub.sessionStub("education_assistant")

        assertTrue(registry.isRegistered("education_assistant"))
        assertNotNull(firstStub, "Expected ORT session stub for education_assistant")

        val features = floatArrayOf(1f, 2f, 3f)
        val result = firstStub.run(features)
        assertTrue(result.contentEquals(features), "ORT stub should echo the features for JVM tests")

        hub.init() // ensure idempotent
        val secondStub = hub.sessionStub("education_assistant")
        assertSame(firstStub, secondStub, "Init should not recreate session stubs when re-invoked")
    }
}
