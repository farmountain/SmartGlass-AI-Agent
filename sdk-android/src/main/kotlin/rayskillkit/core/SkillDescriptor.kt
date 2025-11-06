package rayskillkit.core

/**
 * Represents the metadata necessary to route a payload to a skill.
 *
 * @param Payload the type of payload the skill consumes to construct features.
 * @param Features the type of feature vector generated from the payload.
 * @param Result the type returned after the skill executes with the feature vector.
 */
interface SkillDescriptor<Payload : Any, Features : Any, Result : Any> {
    /**
     * Transform an incoming payload into a feature vector suitable for execution by the skill.
     */
    fun buildFeatures(payload: Payload): Features

    /**
     * Executes the skill using the feature vector produced by [buildFeatures].
     */
    val runner: SkillRunner<Features, Result>
}

fun interface SkillRunner<Features : Any, Result : Any> {
    fun runSkill(features: Features): Result
}
