package rayskillkit.core

import java.nio.file.Files
import org.json.JSONObject
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import kotlin.test.fail

class RouterTest {
    data class Payload(val value: String)

    @Test
    fun routeSkillBuildsFeaturesAndRunsExecutor() {
        val registry = SkillRegistry()
        val telemetry = Telemetry(storageDir = Files.createTempDirectory("telemetry-router").toFile())
        val router = Router(registry, telemetry)

        val expectedFeatures = listOf(1, 2, 3)
        var builtPayload: Payload? = null
        var executedFeatures: List<Int>? = null

        val descriptor = object : SkillDescriptor<Payload, List<Int>, String> {
            override fun buildFeatures(payload: Payload): List<Int> {
                builtPayload = payload
                return expectedFeatures
            }

            override val runner = SkillRunner<List<Int>, String> { features ->
                executedFeatures = features
                "success"
            }
        }

        registry.registerSkill("test-skill", descriptor)

        val result: Router.RouteResult<String> =
            router.routeSkill("test-skill", Payload("input"))

        when (result) {
            is Router.RouteResult.Success -> assertEquals("success", result.value)
            is Router.RouteResult.Failure -> fail("Expected success but received failure: ${result.error}")
        }

        assertEquals(Payload("input"), builtPayload)
        assertEquals(expectedFeatures, executedFeatures)
        val events = telemetry.events()
        assertEquals(1, events.size)
        val payload = JSONObject(events.first())
        assertEquals("router.outcome", payload.getString("event"))
        val attributes = payload.getJSONObject("attributes")
        assertEquals("test-skill", attributes.getString("skill"))
        assertEquals("success", attributes.getString("outcome"))
    }

    @Test
    fun routeSkillDelegatesToMockOrtAndRecordsTelemetry() {
        val mockOrt = MockOrt()
        val ortHub = OrtHub(ortWrapper = mockOrt)
        ortHub.init()

        val telemetry = Telemetry(storageDir = Files.createTempDirectory("telemetry-router").toFile())
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

        val registration = ortHub.skillRegistry()
            .getRegistration<FeaturePayload, FloatArray, FloatArray>("education_assistant")
            ?: fail("education_assistant not registered")
        val builtFeatures = registration.descriptor.buildFeatures(payload)
        val expected = mockOrt.infer("education_assistant", builtFeatures)

        val result = router.routeSkill<FeaturePayload, FloatArray, FloatArray>(
            "education_assistant",
            payload
        )

        val actual = when (result) {
            is Router.RouteResult.Success -> result.value
            is Router.RouteResult.Failure -> fail("Expected success but router failed: ${result.error}")
        }

        assertTrue(actual.contentEquals(expected), "Router should use MockOrt for JVM tests")

        val events = telemetry.events()
        assertEquals(1, events.size)
        val payload = JSONObject(events.first())
        assertEquals("router.outcome", payload.getString("event"))
        val attributes = payload.getJSONObject("attributes")
        assertEquals("education_assistant", attributes.getString("skill"))
        assertEquals("success", attributes.getString("outcome"))
    }
}
