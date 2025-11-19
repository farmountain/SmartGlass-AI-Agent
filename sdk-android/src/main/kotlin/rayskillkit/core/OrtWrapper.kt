package rayskillkit.core

/**
 * Abstraction over the platform specific ONNX Runtime integration used by the SDK.
 */
interface OrtWrapper {
    /** Flag indicating whether inference should be skipped because the SDK is idling. */
    var isIdle: Boolean

    /**
     * Executes inference for the provided [modelName] using the supplied [features].
     */
    fun infer(modelName: String, features: FloatArray): FloatArray
}

/**
 * Deterministic mock implementation of [OrtWrapper] used for JVM unit tests.
 */
class MockOrt : OrtWrapper {
    override var isIdle: Boolean = false
    var activeInferenceCount: Int = 0
        private set
    var skippedInferenceCount: Int = 0
        private set

    override fun infer(modelName: String, features: FloatArray): FloatArray {
        if (isIdle) {
            skippedInferenceCount++
            return FloatArray(features.size)
        }

        activeInferenceCount++
        val adjustment = (modelName.length % 7 + 1).toFloat()
        return FloatArray(features.size) { index -> features[index] + adjustment }
    }
}

/**
 * Placeholder Android implementation that will bridge to the production ONNX Runtime runtime.
 */
class AndroidOrtWrapper : OrtWrapper {
    @Volatile
    override var isIdle: Boolean = false

    override fun infer(modelName: String, features: FloatArray): FloatArray {
        if (isIdle) {
            return FloatArray(features.size)
        }
        return features.copyOf()
    }
}
