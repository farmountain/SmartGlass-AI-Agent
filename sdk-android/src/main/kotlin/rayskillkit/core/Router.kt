package rayskillkit.core

class Router(
    private val registry: SkillRegistry,
    private val telemetry: Telemetry? = null
) {
    sealed class RouteResult<out Result> {
        data class Success<Result>(val value: Result) : RouteResult<Result>()
        data class Failure(val error: Throwable) : RouteResult<Nothing>()
    }

    fun <Payload : Any, Features : Any, Result : Any> routeSkill(
        skillName: String,
        payload: Payload
    ): RouteResult<Result> {
        val descriptor = registry.getSkill<Payload, Features, Result>(skillName)
            ?: return handleFailure(skillName, SkillNotFoundException(skillName))

        return try {
            val features = descriptor.buildFeatures(payload)
            val result = descriptor.runner.runSkill(features)
            telemetry?.recordRouterSuccess(skillName)
            RouteResult.Success(result)
        } catch (error: Exception) {
            handleFailure(skillName, error)
        }
    }

    private fun handleFailure(skillName: String, error: Throwable): RouteResult.Failure {
        telemetry?.recordRouterFailure(skillName, error)
        return RouteResult.Failure(error)
    }
}

class SkillNotFoundException(skillName: String) : IllegalArgumentException(
    "Skill '$skillName' is not registered"
)
