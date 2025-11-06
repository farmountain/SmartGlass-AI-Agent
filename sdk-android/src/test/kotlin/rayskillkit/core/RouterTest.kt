package rayskillkit.core

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.fail

class RouterTest {
    data class Payload(val value: String)

    @Test
    fun routeSkillBuildsFeaturesAndRunsExecutor() {
        val registry = SkillRegistry()
        val telemetry = Telemetry()
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
        assertEquals(listOf("router.success.test-skill"), telemetry.events())
    }
}
