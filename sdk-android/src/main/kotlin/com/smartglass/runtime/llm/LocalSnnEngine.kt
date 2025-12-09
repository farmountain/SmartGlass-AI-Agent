package com.smartglass.runtime.llm

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

private const val TAG = "LocalSnnEngine"

/**
 * Local SNN engine that runs a TorchScript or ONNX SNN student model fully on device.
 * 
 * Designed to support PyTorch Mobile (org.pytorch.Module) with an abstraction layer
 * that allows swapping to ONNX Runtime implementation with minimal changes.
 * 
 * @param context Android context for accessing assets
 * @param modelAssetPath Path to model file in assets (e.g., "snn_student_ts.pt")
 * @param tokenizer Tokenizer for encoding/decoding text
 */
class LocalSnnEngine(
    private val context: Context,
    private val modelAssetPath: String,
    private val tokenizer: LocalTokenizer
) {
    private var modelBackend: ModelBackend? = null
    
    init {
        // Initialize the model backend lazily
        initializeModel()
    }
    
    /**
     * Generate text based on input prompt and optional visual context.
     * 
     * @param prompt The text prompt
     * @param visualContext Optional visual context to include
     * @param maxTokens Maximum number of tokens to generate (default: 64)
     * @return Generated text response
     */
    suspend fun generate(
        prompt: String,
        visualContext: String? = null,
        maxTokens: Int = 64
    ): String = withContext(Dispatchers.Default) {
        try {
            // Concatenate visual context if provided
            val fullPrompt = if (visualContext != null) {
                "$prompt\n[vision]: $visualContext"
            } else {
                prompt
            }
            
            // Encode the prompt to token IDs
            val inputIds = tokenizer.encode(fullPrompt, maxTokens)
            
            // Pad to expected sequence length
            val paddedIds = tokenizer.pad(inputIds, tokenizer.maxSequenceLength)
            
            // Run inference
            val backend = modelBackend ?: throw IllegalStateException("Model not initialized")
            val outputIds = backend.forward(paddedIds)
            
            // Decode output tokens to text
            val result = tokenizer.decode(outputIds)
            
            // Return result or fallback
            if (result.isNotBlank()) result else getFallbackResponse()
            
        } catch (e: Exception) {
            Log.e(TAG, "Error during generation", e)
            getFallbackResponse()
        }
    }
    
    private fun initializeModel() {
        try {
            // Try PyTorch Mobile first if available
            modelBackend = tryLoadPyTorchModel()
            if (modelBackend != null) {
                Log.d(TAG, "Loaded PyTorch Mobile model: $modelAssetPath")
                return
            }
            
            // Fall back to ONNX Runtime if available
            modelBackend = tryLoadOnnxModel()
            if (modelBackend != null) {
                Log.d(TAG, "Loaded ONNX Runtime model: $modelAssetPath")
                return
            }
            
            Log.w(TAG, "No model backend available, using mock backend")
            modelBackend = MockModelBackend()
        } catch (e: Exception) {
            Log.e(TAG, "Error initializing model", e)
            modelBackend = MockModelBackend()
        }
    }
    
    private fun tryLoadPyTorchModel(): ModelBackend? {
        return try {
            // Check if PyTorch classes are available
            val moduleClass = Class.forName("org.pytorch.Module")
            val loadMethod = moduleClass.getMethod("load", String::class.java)
            
            // Copy model from assets to internal storage (PyTorch requires file path)
            val modelFile = copyAssetToFile(modelAssetPath)
            
            // Load the model using reflection
            val module = loadMethod.invoke(null, modelFile.absolutePath)
            
            PyTorchModelBackend(module)
        } catch (e: ClassNotFoundException) {
            Log.d(TAG, "PyTorch Mobile not available")
            null
        } catch (e: Exception) {
            Log.w(TAG, "Failed to load PyTorch model", e)
            null
        }
    }
    
    private fun tryLoadOnnxModel(): ModelBackend? {
        return try {
            // Check if ONNX Runtime classes are available
            Class.forName("ai.onnxruntime.OrtEnvironment")
            Class.forName("ai.onnxruntime.OrtSession")
            
            // Use ONNX Runtime backend
            OnnxModelBackend(context, modelAssetPath)
        } catch (e: ClassNotFoundException) {
            Log.d(TAG, "ONNX Runtime not available")
            null
        } catch (e: Exception) {
            Log.w(TAG, "Failed to load ONNX model", e)
            null
        }
    }
    
    private fun copyAssetToFile(assetPath: String): File {
        val outputFile = File(context.filesDir, assetPath.replace("/", "_"))
        if (!outputFile.exists()) {
            context.assets.open(assetPath).use { input ->
                outputFile.outputStream().use { output ->
                    input.copyTo(output)
                }
            }
        }
        return outputFile
    }
    
    private fun getFallbackResponse(): String {
        return "I'm having trouble thinking right now."
    }
}

/**
 * Abstract interface for model backends.
 * This allows us to swap between PyTorch Mobile and ONNX Runtime implementations.
 */
private interface ModelBackend {
    fun forward(inputIds: LongArray): LongArray
}

/**
 * PyTorch Mobile backend implementation using reflection to avoid compile-time dependency.
 */
private class PyTorchModelBackend(private val module: Any) : ModelBackend {
    override fun forward(inputIds: LongArray): LongArray {
        try {
            // Get Module class and methods
            val moduleClass = module.javaClass
            val forwardMethod = moduleClass.getMethod("forward", Class.forName("org.pytorch.IValue"))
            
            // Create IValue from input tensor
            val iValueClass = Class.forName("org.pytorch.IValue")
            val tensorClass = Class.forName("org.pytorch.Tensor")
            val fromMethod = iValueClass.getMethod("from", tensorClass)
            
            // Create tensor from long array
            val fromBlobMethod = tensorClass.getMethod("fromBlob", LongArray::class.java, LongArray::class.java)
            val shape = longArrayOf(1L, inputIds.size.toLong())
            val tensor = fromBlobMethod.invoke(null, inputIds, shape)
            
            // Create IValue from tensor
            val inputIValue = fromMethod.invoke(null, tensor)
            
            // Run forward pass
            val outputIValue = forwardMethod.invoke(module, inputIValue)
            
            // Extract output tensor
            val toTensorMethod = iValueClass.getMethod("toTensor")
            val outputTensor = toTensorMethod.invoke(outputIValue)
            
            // Get data as long array
            val dataAsLongArrayMethod = tensorClass.getMethod("getDataAsLongArray")
            return dataAsLongArrayMethod.invoke(outputTensor) as LongArray
        } catch (e: Exception) {
            Log.e(TAG, "Error in PyTorch forward pass", e)
            throw e
        }
    }
}

/**
 * ONNX Runtime backend implementation using reflection to avoid compile-time dependency.
 */
private class OnnxModelBackend(context: Context, modelAssetPath: String) : ModelBackend {
    private val environment: Any
    private val session: Any
    
    init {
        val ortEnvClass = Class.forName("ai.onnxruntime.OrtEnvironment")
        val getEnvironmentMethod = ortEnvClass.getMethod("getEnvironment")
        environment = getEnvironmentMethod.invoke(null)!!
        
        // Load model
        val modelBytes = context.assets.open(modelAssetPath).use { it.readBytes() }
        val createSessionMethod = ortEnvClass.getMethod("createSession", ByteArray::class.java)
        session = createSessionMethod.invoke(environment, modelBytes)!!
    }
    
    override fun forward(inputIds: LongArray): LongArray {
        try {
            val ortTensorClass = Class.forName("ai.onnxruntime.OnnxTensor")
            val ortSessionClass = Class.forName("ai.onnxruntime.OrtSession")
            
            // Get input name
            val getInputNamesMethod = ortSessionClass.getMethod("getInputNames")
            val inputNames = getInputNamesMethod.invoke(session) as Set<*>
            val inputName = inputNames.firstOrNull() as String
            
            // Create tensor
            val shape = longArrayOf(1L, inputIds.size.toLong())
            val createTensorMethod = ortTensorClass.getMethod(
                "createTensor",
                Class.forName("ai.onnxruntime.OrtEnvironment"),
                LongArray::class.java,
                LongArray::class.java
            )
            val inputTensor = createTensorMethod.invoke(null, environment, inputIds, shape)
            
            // Run inference
            val runMethod = ortSessionClass.getMethod("run", Map::class.java)
            val inputs = mapOf(inputName to inputTensor)
            val result = runMethod.invoke(session, inputs)
            
            // Extract output
            val resultClass = Class.forName("ai.onnxruntime.OrtSession\$Result")
            val getMethod = resultClass.getMethod("get", Int::class.javaPrimitiveType)
            val output = getMethod.invoke(result, 0)
            
            val valueClass = Class.forName("ai.onnxruntime.OnnxValue")
            val getValueMethod = valueClass.getMethod("getValue")
            val outputValue = getValueMethod.invoke(output)
            
            // Convert output to long array
            return when (outputValue) {
                is LongArray -> outputValue
                is IntArray -> outputValue.map { it.toLong() }.toLongArray()
                is FloatArray -> outputValue.map { it.toLong() }.toLongArray()
                else -> longArrayOf()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error in ONNX forward pass", e)
            throw e
        }
    }
}

/**
 * Mock backend for testing or when no real backend is available.
 */
private class MockModelBackend : ModelBackend {
    override fun forward(inputIds: LongArray): LongArray {
        // Simple mock: return first few non-zero tokens
        return inputIds.filter { it != 0L }.take(5).toLongArray()
    }
}
