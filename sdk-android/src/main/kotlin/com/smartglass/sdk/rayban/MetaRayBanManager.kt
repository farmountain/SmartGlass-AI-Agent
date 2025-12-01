package com.smartglass.sdk.rayban

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Log
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

    private class ReflectionSdkFacade(
        private val context: Context,
        private val sdkInstance: Any,
        private val connectMethod: java.lang.reflect.Method?,
        private val disconnectMethod: java.lang.reflect.Method?,
        private val captureMethod: java.lang.reflect.Method?,
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
                val startAudio = sdkClass.java.methods.firstOrNull { it.name == "startAudioStreaming" || it.name == "startMicrophone" }
                val stopAudio = sdkClass.java.methods.firstOrNull { it.name == "stopAudioStreaming" || it.name == "stopMicrophone" }

                return ReflectionSdkFacade(
                    context = context,
                    sdkInstance = instance,
                    connectMethod = connect,
                    disconnectMethod = disconnect,
                    captureMethod = capture,
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
    }
}
