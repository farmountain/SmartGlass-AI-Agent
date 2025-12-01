package com.smartglass.sdk.rayban

import android.graphics.Bitmap
import androidx.test.core.app.ApplicationProvider
import java.util.concurrent.atomic.AtomicInteger
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class MetaRayBanManagerTest {

    @Test
    fun connectThreadsDeviceAndTransportHints() = runTest {
        val facade = RecordingSdkFacade()
        val manager = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = facade,
        )

        manager.connect("device-123", MetaRayBanManager.Transport.WIFI)

        assertEquals("device-123", facade.connectedDeviceId)
        assertEquals("wifi", facade.connectedTransport)
    }

    @Test
    fun capturePhotoDelegatesToSdkFacade() = runTest {
        val photo = Bitmap.createBitmap(1, 1, Bitmap.Config.ARGB_8888)
        val facade = RecordingSdkFacade(photo)
        val manager = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = facade,
        )

        val captured = manager.capturePhoto()

        assertEquals(photo, captured)
        assertEquals(1, facade.captureCount.get())
    }

    @Test
    fun audioStreamingStopsWhenRequested() = runTest {
        val audioFlow = MutableSharedFlow<ByteArray>(replay = 1)
        val facade = RecordingSdkFacade(audioFlow = audioFlow)
        val manager = MetaRayBanManager(
            context = ApplicationProvider.getApplicationContext(),
            sdkFacade = facade,
        )

        audioFlow.tryEmit(byteArrayOf(1, 2, 3))
        val chunk = manager.startAudioStreaming().first()
        assertEquals(3, chunk.size)

        manager.stopAudioStreaming()
        assertEquals(1, facade.stopAudioCount.get())
    }

    @Test
    fun fallbackStreamingIsDeterministicWithoutSdk() = runTest {
        val manager = MetaRayBanManager(ApplicationProvider.getApplicationContext())
        val emissions = mutableListOf<ByteArray>()

        manager.startAudioStreaming().collect { chunk ->
            emissions.add(chunk)
        }

        assertEquals(MetaRayBanManager.FAKE_AUDIO_EMISSION_COUNT, emissions.size)
        assertEquals("fake-audio-chunk-0", emissions.first().decodeToString())
    }

    @Test
    fun fallbackCaptureReturnsPlaceholderWhenAvailable() = runTest {
        val manager = MetaRayBanManager(ApplicationProvider.getApplicationContext())
        val bitmap = manager.capturePhoto()
        assertNotNull(bitmap)
    }

    private class RecordingSdkFacade(
        private val photo: Bitmap? = null,
        private val audioFlow: Flow<ByteArray> = flowOf(byteArrayOf(0)),
    ) : MetaRayBanManager.SdkFacade {
        var connectedDeviceId: String? = null
        var connectedTransport: String? = null
        val captureCount = AtomicInteger(0)
        val stopAudioCount = AtomicInteger(0)

        override suspend fun connect(deviceId: String, transportHint: String) {
            connectedDeviceId = deviceId
            connectedTransport = transportHint
        }

        override fun disconnect() = Unit

        override suspend fun capturePhoto(): Bitmap? {
            captureCount.incrementAndGet()
            return photo
        }

        override fun startAudioStreaming(): Flow<ByteArray> = audioFlow

        override fun stopAudioStreaming() {
            stopAudioCount.incrementAndGet()
        }
    }
}
