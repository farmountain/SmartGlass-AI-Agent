package rayskillkit.core

/**
 * Abstraction over the platform specific ONNX Runtime integration used by the SDK.
 */
interface OrtWrapper {
    /**
     * Executes inference for the provided [modelName] using the supplied [features].
     */
    fun infer(modelName: String, features: FloatArray): FloatArray
}

/**
 * Deterministic mock implementation of [OrtWrapper] used for JVM unit tests.
 */
class MockOrt : OrtWrapper {
    override fun infer(modelName: String, features: FloatArray): FloatArray {
        val adjustment = (modelName.length % 7 + 1).toFloat()
        return FloatArray(features.size) { index -> features[index] + adjustment }
    }
}

/**
 * Placeholder Android implementation that will bridge to the production ONNX Runtime runtime.
 */
class AndroidOrtWrapper : OrtWrapper {
    override fun infer(modelName: String, features: FloatArray): FloatArray = features.copyOf()
}
