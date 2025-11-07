package rayskillkit.core

import kotlin.test.Test
import kotlin.test.assertNotNull
import kotlin.test.assertSame
import kotlin.test.assertTrue

class OrtHubTest {
    @Test
    fun initLoadsSkillsUsingJvmFallback() {
        val registry = SkillRegistry()
        val mockOrt = MockOrt()
        val hub = OrtHub(registry, mockOrt)

        hub.init()
        val firstSession = hub.session("education_assistant")

        assertTrue(registry.isRegistered("education_assistant"))
        assertNotNull(firstSession, "Expected ORT session for education_assistant")

        val features = floatArrayOf(1f, 2f, 3f)
        val expected = mockOrt.infer("education_assistant", features)
        val result = firstSession!!.run(features)
        assertTrue(result.contentEquals(expected), "ORT session should delegate to the provided wrapper")

        hub.init() // ensure idempotent
        val secondSession = hub.session("education_assistant")
        assertSame(firstSession, secondSession, "Init should not recreate sessions when re-invoked")
    }
}
