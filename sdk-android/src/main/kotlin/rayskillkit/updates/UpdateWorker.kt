package rayskillkit.updates

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.goterl.lazysodium.LazySodiumAndroid
import com.goterl.lazysodium.SodiumAndroid
import java.io.IOException
import java.net.URL
import java.nio.charset.StandardCharsets
import java.util.Base64
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import rayskillkit.core.BuildConfig

/**
 * Periodically fetches and verifies release manifests before triggering updates.
 */
class UpdateWorker(
    appContext: Context,
    workerParams: WorkerParameters,
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        if (BuildConfig.IS_CI) {
            Log.i(TAG, "Skipping update verification in CI environment.")
            return@withContext Result.success()
        }

        val manifestUrl = inputData.getString(KEY_MANIFEST_URL)
        val signatureBase64 = inputData.getString(KEY_SIGNATURE_BASE64)
        val releaseKeyBase64 = inputData.getString(KEY_RELEASE_PUBLIC_KEY)

        if (manifestUrl.isNullOrBlank() || signatureBase64.isNullOrBlank() || releaseKeyBase64.isNullOrBlank()) {
            Log.w(TAG, "Missing manifest URL, signature, or public key input data.")
            return@withContext Result.failure()
        }

        val manifestJson = try {
            fetchManifest(manifestUrl)
        } catch (ioe: IOException) {
            Log.e(TAG, "Unable to download manifest from $manifestUrl", ioe)
            return@withContext Result.retry()
        }

        val releasePublicKey = try {
            Base64.getDecoder().decode(releaseKeyBase64)
        } catch (iae: IllegalArgumentException) {
            Log.e(TAG, "Invalid Base64 encoding for release public key.", iae)
            return@withContext Result.failure()
        }

        val verifier = try {
            ManifestVerifier(LazySodiumAndroid(SodiumAndroid()), releasePublicKey)
        } catch (iae: IllegalArgumentException) {
            Log.e(TAG, "Release public key has incorrect length.", iae)
            return@withContext Result.failure()
        }

        return@withContext if (verifier.verify(manifestJson, signatureBase64)) {
            Log.i(TAG, "Manifest signature verified successfully.")
            Result.success()
        } else {
            Log.w(TAG, "Manifest signature verification failed.")
            Result.failure()
        }
    }

    @Throws(IOException::class)
    private fun fetchManifest(manifestUrl: String): String {
        return URL(manifestUrl).openStream().use { input ->
            input.bufferedReader(StandardCharsets.UTF_8).use { it.readText() }
        }
    }

    companion object {
        const val KEY_MANIFEST_URL = "manifest_url"
        const val KEY_SIGNATURE_BASE64 = "manifest_signature"
        const val KEY_RELEASE_PUBLIC_KEY = "release_public_key"

        private const val TAG = "UpdateWorker"
    }
}
