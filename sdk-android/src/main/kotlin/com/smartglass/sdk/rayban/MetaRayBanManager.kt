package com.smartglass.sdk.rayban

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.YuvImage
import android.util.Log
import java.io.ByteArrayOutputStream
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.reflect.KClass
import kotlin.reflect.full.createInstance
import kotlin.reflect.full.primaryConstructor
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.withContext
import rayskillkit.core.R

class MetaRayBanManager private constructor(
    private val context: Context,
    private val sdkFacade: SdkFacade,
) {

    enum class Transport {
        BLE,
        WIFI
    }

    constructor(context: Context) : this(
        context = context.applicationContext,
        sdkFacade = MetaRayBanSdkLoader.load(context.applicationContext),
    )

    internal constructor(context: Context, sdkFacade: SdkFacade) : this(
        context = context.applicationContext,
        sdkFacade = sdkFacade,
    )

    suspend fun connect(deviceId: String, transport: Transport) {
        sdkFacade.connect(deviceId, transport.toSdkHint())
    }

    fun disconnect() {
        sdkFacade.disconnect()
    }

    suspend fun capturePhoto(): Bitmap? {
        return sdkFacade.capturePhoto()
    }

    /**
     * Start continuous video streaming from the glasses.
     * @param onFrame Callback invoked for each frame with JPEG bytes and timestamp
     */
    suspend fun startStreaming(onFrame: (frame: ByteArray, timestampMs: Long) -> Unit) {
        sdkFacade.startStreaming(onFrame)
    }

    /**
     * Stop the active streaming session.
     */
    fun stopStreaming() {
        sdkFacade.stopStreaming()
    }

    fun startAudioStreaming(): Flow<ByteArray> {
        return sdkFacade.startAudioStreaming()
    }

    fun stopAudioStreaming() {
        sdkFacade.stopAudioStreaming()
    }

    interface SdkFacade {
        suspend fun connect(deviceId: String, transportHint: String)
        fun disconnect()
        suspend fun capturePhoto(): Bitmap?
        suspend fun startStreaming(onFrame: (frame: ByteArray, timestampMs: Long) -> Unit)
        fun stopStreaming()
        fun startAudioStreaming(): Flow<ByteArray>
        fun stopAudioStreaming()
    }

    private class MockSdkFacade(private val context: Context) : SdkFacade {

        private val streaming = AtomicBoolean(false)

        override suspend fun connect(deviceId: String, transportHint: String) {
            Log.i(TAG, "Connecting to Meta Ray-Ban device $deviceId over $transportHint (mock)")
            withContext(Dispatchers.IO) {
                delay(CONNECTION_DELAY_MS)
            }
        }

        override fun disconnect() {
            streaming.set(false)
            Log.i(TAG, "Disconnecting from Meta Ray-Ban device (mock)")
        }

        override suspend fun capturePhoto(): Bitmap? {
            Log.d(TAG, "Capturing photo from Meta Ray-Ban device (mock)")
            return withContext(Dispatchers.IO) {
                BitmapFactory.decodeResource(context.resources, R.drawable.meta_rayban_placeholder)
            }.also {
                if (it == null) {
                    Log.w(TAG, "Failed to decode placeholder; returning null")
                }
            }
        }

        override suspend fun startStreaming(onFrame: (frame: ByteArray, timestampMs: Long) -> Unit) {
            streaming.set(true)
            Log.d(TAG, "Starting video streaming from Meta Ray-Ban device (mock)")
            withContext(Dispatchers.IO) {
                repeat(FAKE_VIDEO_FRAME_COUNT) { index ->
                    if (!streaming.get()) return@withContext
                    val fakeFrame = "fake-video-frame-$index".encodeToByteArray()
                    val timestamp = System.currentTimeMillis()
                    onFrame(fakeFrame, timestamp)
                    delay(FAKE_VIDEO_DELAY_MS)
                }
                Log.d(TAG, "Video streaming completed (mock)")
            }
        }

        override fun stopStreaming() {
            streaming.set(false)
            Log.d(TAG, "Stopping video streaming from Meta Ray-Ban device (mock)")
        }

        override fun startAudioStreaming(): Flow<ByteArray> {
            streaming.set(true)
            Log.d(TAG, "Starting audio streaming from Meta Ray-Ban device (mock)")
            return flow {
                repeat(FAKE_AUDIO_EMISSION_COUNT) { index ->
                    if (!streaming.get()) return@flow
                    emit("fake-audio-chunk-$index".encodeToByteArray())
                    delay(FAKE_AUDIO_DELAY_MS)
                }
                Log.d(TAG, "Audio streaming completed (mock)")
            }
        }

        override fun stopAudioStreaming() {
            streaming.set(false)
            Log.d(TAG, "Stopping audio streaming from Meta Ray-Ban device (mock)")
        }
    }

    /**
     * Real DAT SDK integration using Meta Wearables Device Access Toolkit.
     * This facade uses the official DAT SDK APIs for production use.
     */
    private class DatSdkFacade(
        private val context: Context,
        private val wearablesClass: Class<*>,
        private val streamSessionClass: Class<*>,
        private val fallback: MockSdkFacade,
    ) : SdkFacade {

        @Volatile
        private var streamSession: Any? = null
        
        @Volatile
        private var streamingJob: kotlinx.coroutines.Job? = null

        override suspend fun connect(deviceId: String, transportHint: String) {
            // TODO: Implement device registration flow
            // The DAT SDK requires users to go through the Meta AI app for pairing.
            // Here we should:
            // 1. Call Wearables.startRegistration(context) to initiate pairing
            // 2. Wait for RegistrationState.Registered
            // 3. Monitor Wearables.devices flow for available devices
            //
            // For now, log the intent and delegate to mock if DAT SDK classes aren't available
            Log.i(TAG, "DAT SDK connect requested for device $deviceId via $transportHint")
            
            runCatching {
                // Attempt to call Wearables.startRegistration(context)
                val startRegistrationMethod = wearablesClass.getDeclaredMethod(
                    "startRegistration",
                    Context::class.java
                )
                startRegistrationMethod.invoke(null, context)
                
                // In a real implementation, we'd wait for registration to complete
                // by collecting from Wearables.registrationState flow
                delay(CONNECTION_DELAY_MS)
            }.onFailure { exc ->
                Log.w(TAG, "DAT SDK registration failed, falling back to mock", exc)
                fallback.connect(deviceId, transportHint)
            }
        }

        override fun disconnect() {
            streamingJob?.cancel()
            streamingJob = null
            
            runCatching {
                streamSession?.let { session ->
                    // Close the stream session
                    val closeMethod = session.javaClass.getDeclaredMethod("close")
                    closeMethod.invoke(session)
                }
                streamSession = null
                
                // TODO: Optionally call Wearables.startUnregistration(context) if user wants to unpair
                Log.i(TAG, "DAT SDK disconnected")
            }.onFailure { exc ->
                Log.w(TAG, "DAT SDK disconnect failed, falling back to mock", exc)
                fallback.disconnect()
            }
        }

        override suspend fun capturePhoto(): Bitmap? {
            return runCatching {
                val session = streamSession
                if (session != null) {
                    // Call StreamSession.capturePhoto() which returns Result<PhotoData>
                    val captureMethod = session.javaClass.getDeclaredMethod("capturePhoto")
                    val resultObj = captureMethod.invoke(session)
                    
                    // Extract PhotoData from Result
                    val photoData = extractPhotoDataFromResult(resultObj)
                    
                    // Convert PhotoData to Bitmap
                    photoDataToBitmap(photoData)
                } else {
                    Log.w(TAG, "No active stream session for photo capture")
                    fallback.capturePhoto()
                }
            }.getOrElse { exc ->
                Log.w(TAG, "DAT SDK photo capture failed, falling back to mock", exc)
                fallback.capturePhoto()
            }
        }

        override suspend fun startStreaming(onFrame: (frame: ByteArray, timestampMs: Long) -> Unit) {
            stopStreaming()
            
            runCatching {
                // TODO: Request camera permission via Wearables.checkPermissionStatus() and 
                // Wearables.requestPermission() before starting stream
                
                // Start a stream session using Wearables.startStreamSession()
                val startStreamMethod = wearablesClass.getDeclaredMethod(
                    "startStreamSession",
                    Context::class.java,
                    Class.forName("com.meta.wearable.dat.core.selectors.DeviceSelector"),
                    Class.forName("com.meta.wearable.dat.camera.types.StreamConfiguration")
                )
                
                // Create AutoDeviceSelector
                val autoDeviceSelectorClass = Class.forName("com.meta.wearable.dat.core.selectors.AutoDeviceSelector")
                val deviceSelector = autoDeviceSelectorClass.getDeclaredConstructor().newInstance()
                
                // Create StreamConfiguration (medium quality, 24 fps)
                val streamConfigClass = Class.forName("com.meta.wearable.dat.camera.types.StreamConfiguration")
                val videoQualityClass = Class.forName("com.meta.wearable.dat.camera.types.VideoQuality")
                val mediumQuality = videoQualityClass.getDeclaredField("MEDIUM").get(null)
                val streamConfig = streamConfigClass.getDeclaredConstructor(
                    videoQualityClass,
                    Int::class.java
                ).newInstance(mediumQuality, 24)
                
                // Start the stream session
                val session = startStreamMethod.invoke(null, context, deviceSelector, streamConfig)
                streamSession = session
                
                // Collect video frames from StreamSession.videoStream
                val videoStreamField = session.javaClass.getDeclaredField("videoStream")
                val videoStream = videoStreamField.get(session) as? Flow<*>
                
                if (videoStream != null) {
                    streamingJob = kotlinx.coroutines.CoroutineScope(Dispatchers.IO).launch {
                        videoStream.collect { videoFrame ->
                            // Convert VideoFrame to JPEG bytes
                            val jpegBytes = videoFrameToJpeg(videoFrame)
                            val timestamp = System.currentTimeMillis()
                            onFrame(jpegBytes, timestamp)
                        }
                    }
                    Log.i(TAG, "DAT SDK video streaming started")
                } else {
                    Log.w(TAG, "Unable to access video stream from DAT SDK")
                    fallback.startStreaming(onFrame)
                }
            }.onFailure { exc ->
                Log.w(TAG, "DAT SDK streaming start failed, falling back to mock", exc)
                fallback.startStreaming(onFrame)
            }
        }

        override fun stopStreaming() {
            streamingJob?.cancel()
            streamingJob = null
            
            runCatching {
                streamSession?.let { session ->
                    val closeMethod = session.javaClass.getDeclaredMethod("close")
                    closeMethod.invoke(session)
                }
                streamSession = null
                Log.i(TAG, "DAT SDK streaming stopped")
            }.onFailure { exc ->
                Log.w(TAG, "DAT SDK streaming stop failed", exc)
            }
        }

        override fun startAudioStreaming(): Flow<ByteArray> {
            // TODO: Implement audio streaming using DAT SDK
            // The DAT SDK may provide microphone access through a similar pattern.
            // For now, fall back to mock implementation.
            Log.w(TAG, "Audio streaming not yet implemented in DAT SDK, using mock")
            return fallback.startAudioStreaming()
        }

        override fun stopAudioStreaming() {
            // TODO: Implement audio streaming stop
            Log.d(TAG, "Audio streaming stop (not yet implemented in DAT SDK)")
            fallback.stopAudioStreaming()
        }

        private fun extractPhotoDataFromResult(resultObj: Any?): Any? {
            // Result<PhotoData> may have isSuccess, getOrNull methods
            return runCatching {
                val getOrNullMethod = resultObj?.javaClass?.getDeclaredMethod("getOrNull")
                getOrNullMethod?.invoke(resultObj)
            }.getOrNull()
        }

        private fun photoDataToBitmap(photoData: Any?): Bitmap? {
            if (photoData == null) return null
            
            return runCatching {
                // PhotoData can be either PhotoData.Bitmap or PhotoData.HEIC
                when (photoData.javaClass.simpleName) {
                    "Bitmap" -> {
                        // PhotoData.Bitmap contains a bitmap field
                        val bitmapField = photoData.javaClass.getDeclaredField("bitmap")
                        bitmapField.isAccessible = true
                        bitmapField.get(photoData) as? Bitmap
                    }
                    "HEIC" -> {
                        // PhotoData.HEIC contains ByteBuffer data
                        val dataField = photoData.javaClass.getDeclaredField("data")
                        dataField.isAccessible = true
                        val byteBuffer = dataField.get(photoData) as? java.nio.ByteBuffer
                        byteBuffer?.let { buffer ->
                            val byteArray = ByteArray(buffer.remaining())
                            buffer.get(byteArray)
                            buffer.rewind()
                            BitmapFactory.decodeByteArray(byteArray, 0, byteArray.size)
                        }
                    }
                    else -> null
                }
            }.getOrNull()
        }

        private fun videoFrameToJpeg(videoFrame: Any?): ByteArray {
            if (videoFrame == null) return ByteArray(0)
            
            return runCatching {
                // VideoFrame contains: buffer (ByteBuffer with I420 data), width, height
                val bufferField = videoFrame.javaClass.getDeclaredField("buffer")
                val widthField = videoFrame.javaClass.getDeclaredField("width")
                val heightField = videoFrame.javaClass.getDeclaredField("height")
                
                bufferField.isAccessible = true
                widthField.isAccessible = true
                heightField.isAccessible = true
                
                val buffer = bufferField.get(videoFrame) as java.nio.ByteBuffer
                val width = widthField.get(videoFrame) as Int
                val height = heightField.get(videoFrame) as Int
                
                // Extract I420 data
                val dataSize = buffer.remaining()
                val i420Data = ByteArray(dataSize)
                val originalPosition = buffer.position()
                buffer.get(i420Data)
                buffer.position(originalPosition)
                
                // Convert I420 to NV21 (Android-compatible format)
                val nv21Data = convertI420toNV21(i420Data, width, height)
                
                // Convert to JPEG
                val yuvImage = YuvImage(nv21Data, ImageFormat.NV21, width, height, null)
                val outputStream = ByteArrayOutputStream()
                yuvImage.compressToJpeg(Rect(0, 0, width, height), 80, outputStream)
                outputStream.toByteArray()
            }.getOrElse { exc ->
                Log.w(TAG, "Failed to convert VideoFrame to JPEG", exc)
                ByteArray(0)
            }
        }

        private fun convertI420toNV21(input: ByteArray, width: Int, height: Int): ByteArray {
            val output = ByteArray(input.size)
            val size = width * height
            val quarter = size / 4

            // Copy Y plane as-is
            input.copyInto(output, 0, 0, size)

            // Interleave U and V planes (V first for NV21)
            for (n in 0 until quarter) {
                output[size + n * 2] = input[size + quarter + n] // V
                output[size + n * 2 + 1] = input[size + n] // U
            }
            return output
        }

        companion object {
            fun tryCreate(context: Context, fallback: MockSdkFacade): DatSdkFacade? {
                return runCatching {
                    val wearablesClass = Class.forName("com.meta.wearable.dat.core.Wearables")
                    val streamSessionClass = Class.forName("com.meta.wearable.dat.camera.StreamSession")
                    DatSdkFacade(context, wearablesClass, streamSessionClass, fallback)
                }.getOrNull()
            }
        }
    }

    private class ReflectionSdkFacade(
        private val context: Context,
        private val sdkInstance: Any,
        private val connectMethod: java.lang.reflect.Method?,
        private val disconnectMethod: java.lang.reflect.Method?,
        private val captureMethod: java.lang.reflect.Method?,
        private val startStreamingMethod: java.lang.reflect.Method?,
        private val stopStreamingMethod: java.lang.reflect.Method?,
        private val startAudioMethod: java.lang.reflect.Method?,
        private val stopAudioMethod: java.lang.reflect.Method?,
        private val fallback: MockSdkFacade,
    ) : SdkFacade {

        override suspend fun connect(deviceId: String, transportHint: String) {
            val method = connectMethod ?: return fallback.connect(deviceId, transportHint)
            runCatching {
                withContext(Dispatchers.IO) {
                    val params = mutableListOf<Any>()
                    val expectsContext = method.parameterTypes.firstOrNull() == Context::class.java
                    val acceptsTransport = method.parameterTypes.size >= (if (expectsContext) 3 else 2)
                    if (expectsContext) params.add(context)
                    params.add(deviceId)
                    if (acceptsTransport) params.add(transportHint)
                    method.invoke(sdkInstance, *params.toTypedArray())
                }
            }.onFailure { exc ->
                Log.w(TAG, "Meta Ray-Ban SDK connect failed, falling back to mock", exc)
                fallback.connect(deviceId, transportHint)
            }
        }

        override fun disconnect() {
            val method = disconnectMethod
            if (method == null) {
                fallback.disconnect()
                return
            }

            runCatching {
                method.invoke(sdkInstance)
            }.onFailure { exc ->
                Log.w(TAG, "Meta Ray-Ban SDK disconnect failed, falling back to mock", exc)
                fallback.disconnect()
            }
        }

        override suspend fun capturePhoto(): Bitmap? {
            val method = captureMethod ?: return fallback.capturePhoto()
            return runCatching {
                withContext(Dispatchers.IO) {
                    val result = method.invoke(sdkInstance)
                    when (result) {
                        is Bitmap -> result
                        is ByteArray -> BitmapFactory.decodeByteArray(result, 0, result.size)
                        else -> null
                    }
                }
            }.getOrElse { exc ->
                Log.w(TAG, "Meta Ray-Ban SDK capture failed, falling back to mock", exc)
                fallback.capturePhoto()
            }
        }

        override suspend fun startStreaming(onFrame: (frame: ByteArray, timestampMs: Long) -> Unit) {
            val method = startStreamingMethod
            if (method == null) {
                fallback.startStreaming(onFrame)
                return
            }
            
            runCatching {
                // Try to invoke the streaming method with the callback
                method.invoke(sdkInstance, onFrame)
            }.onFailure { exc ->
                Log.w(TAG, "Meta Ray-Ban SDK streaming start failed, falling back to mock", exc)
                fallback.startStreaming(onFrame)
            }
        }

        override fun stopStreaming() {
            val method = stopStreamingMethod
            if (method == null) {
                fallback.stopStreaming()
                return
            }

            runCatching {
                method.invoke(sdkInstance)
            }.onFailure { exc ->
                Log.w(TAG, "Meta Ray-Ban SDK streaming stop failed, falling back to mock", exc)
                fallback.stopStreaming()
            }
        }

        override fun startAudioStreaming(): Flow<ByteArray> {
            val method = startAudioMethod ?: return fallback.startAudioStreaming()
            return runCatching {
                @Suppress("UNCHECKED_CAST")
                val result = method.invoke(sdkInstance)
                when (result) {
                    is Flow<*> -> result as Flow<ByteArray>
                    is Iterable<*> -> flow {
                        result.forEach { chunk ->
                            if (chunk is ByteArray) emit(chunk)
                        }
                    }
                    else -> fallback.startAudioStreaming()
                }
            }.getOrElse { exc ->
                Log.w(TAG, "Meta Ray-Ban SDK audio start failed, falling back to mock", exc)
                fallback.startAudioStreaming()
            }
        }

        override fun stopAudioStreaming() {
            val method = stopAudioMethod
            if (method == null) {
                fallback.stopAudioStreaming()
                return
            }

            runCatching {
                method.invoke(sdkInstance)
            }.onFailure { exc ->
                Log.w(TAG, "Meta Ray-Ban SDK audio stop failed, falling back to mock", exc)
                fallback.stopAudioStreaming()
            }
        }

        companion object {
            fun tryCreate(
                context: Context,
                fallback: MockSdkFacade,
                candidateClassNames: List<String>,
                instantiate: (KClass<*>) -> Any?,
            ): ReflectionSdkFacade? {
                val sdkClass = candidateClassNames.firstNotNullOfOrNull { className ->
                    runCatching { Class.forName(className).kotlin }.getOrNull()
                } ?: return null

                val instance = instantiate(sdkClass) ?: return null
                val connect = sdkClass.java.methods.firstOrNull { it.name == "connect" }
                val disconnect = sdkClass.java.methods.firstOrNull { it.name == "disconnect" }
                val capture = sdkClass.java.methods.firstOrNull { it.name == "capturePhoto" || it.name == "takePhoto" }
                val startStreaming = sdkClass.java.methods.firstOrNull { it.name == "startStreaming" || it.name == "startVideoStream" }
                val stopStreaming = sdkClass.java.methods.firstOrNull { it.name == "stopStreaming" || it.name == "stopVideoStream" }
                val startAudio = sdkClass.java.methods.firstOrNull { it.name == "startAudioStreaming" || it.name == "startMicrophone" }
                val stopAudio = sdkClass.java.methods.firstOrNull { it.name == "stopAudioStreaming" || it.name == "stopMicrophone" }

                return ReflectionSdkFacade(
                    context = context,
                    sdkInstance = instance,
                    connectMethod = connect,
                    disconnectMethod = disconnect,
                    captureMethod = capture,
                    startStreamingMethod = startStreaming,
                    stopStreamingMethod = stopStreaming,
                    startAudioMethod = startAudio,
                    stopAudioMethod = stopAudio,
                    fallback = fallback,
                )
            }
        }
    }

    private object MetaRayBanSdkLoader {
        private val candidateClassNames = listOf(
            "com.meta.rayban.sdk.MetaRayBanSdk",
            "com.rayban.meta.sdk.MetaRayBanSdk",
            "com.facebook.wearables.metarayban.sdk.MetaRayBanSdk",
        )

        fun load(context: Context): SdkFacade {
            val fallback = MockSdkFacade(context)
            
            // First try to load the official DAT SDK
            val datFacade = DatSdkFacade.tryCreate(context, fallback)
            if (datFacade != null) {
                Log.i(TAG, "Loaded Meta Wearables DAT SDK")
                return datFacade
            }
            
            // Fall back to reflection-based loading for other SDK variants
            val reflectionFacade = ReflectionSdkFacade.tryCreate(
                context = context,
                fallback = fallback,
                candidateClassNames = candidateClassNames,
                instantiate = { kClass -> instantiateSdk(kClass, context) },
            )
            return reflectionFacade ?: fallback
        }

        private fun instantiateSdk(kClass: KClass<*>, context: Context): Any? {
            return runCatching {
                kClass.primaryConstructor?.call(context)
                    ?: kClass.primaryConstructor?.call()
                    ?: kClass.constructors.firstOrNull { it.parameters.isEmpty() }?.call()
                    ?: kClass.createInstance()
            }.getOrElse {
                Log.w(TAG, "Unable to instantiate Meta Ray-Ban SDK; falling back to mock", it)
                null
            }
        }
    }

    private fun Transport.toSdkHint(): String = name.lowercase()

    companion object {
        private const val TAG = "MetaRayBanManager"
        private const val CONNECTION_DELAY_MS = 250L
        internal const val FAKE_AUDIO_EMISSION_COUNT = 3
        internal const val FAKE_AUDIO_DELAY_MS = 200L
        internal const val FAKE_VIDEO_FRAME_COUNT = 10
        internal const val FAKE_VIDEO_DELAY_MS = 100L // ~10 fps mock rate
    }
}
