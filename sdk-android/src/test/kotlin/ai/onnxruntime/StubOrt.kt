package ai.onnxruntime

/** Lightweight stubs for ONNX Runtime APIs used in JVM unit tests. */
open class OnnxValue(open val value: Any?)

class OnnxTensor private constructor(private val data: Any?) : OnnxValue(data), AutoCloseable {
    companion object {
        fun createTensor(env: OrtEnvironment, data: LongArray, shape: LongArray): OnnxTensor {
            return OnnxTensor(data.copyOf())
        }
    }

    override fun close() {
        // nothing to release in the stub
    }
}

class OrtEnvironment private constructor() {
    companion object {
        private val shared = OrtEnvironment()
        fun getEnvironment(): OrtEnvironment = shared
    }

    fun createSession(modelBytes: ByteArray): OrtSession = OrtSession()
}

class OrtSession : AutoCloseable {
    val inputNames: Set<String> = setOf("input")

    fun run(inputs: Map<String, OnnxTensor>): Result {
        // Return a simple token ID so decoding has content to work with
        return Result(listOf(OnnxValue(longArrayOf(1L))))
    }

    override fun close() {
        // no-op for stub
    }

    class Result(private val values: List<OnnxValue>) : AutoCloseable {
        fun isEmpty(): Boolean = values.isEmpty()
        operator fun get(index: Int): OnnxValue = values[index]
        override fun close() {
            // nothing to close in the stub
        }
    }
}
