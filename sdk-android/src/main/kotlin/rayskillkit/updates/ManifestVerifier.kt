package rayskillkit.updates

import com.goterl.lazysodium.LazySodium
import com.goterl.lazysodium.interfaces.Sign
import java.io.InputStream
import java.nio.charset.StandardCharsets
import java.util.Base64

/**
 * Validates signed release manifests using an Ed25519 public key.
 */
class ManifestVerifier(
    private val sodium: LazySodium,
    private val releasePublicKey: ByteArray,
) {

    private val decoder: Base64.Decoder = Base64.getDecoder()

    init {
        require(releasePublicKey.size == Sign.PUBLICKEYBYTES) {
            "Release public key must be ${Sign.PUBLICKEYBYTES} bytes for Ed25519"
        }
    }

    /**
     * Reads the manifest from the provided [InputStream] and validates the detached signature.
     */
    fun verify(manifestStream: InputStream, signatureBase64: String): Boolean {
        val manifestJson = manifestStream.bufferedReader(StandardCharsets.UTF_8).use { it.readText() }
        return verify(manifestJson, signatureBase64)
    }

    /**
     * Validates the detached signature for the supplied [manifestJson].
     */
    fun verify(manifestJson: String, signatureBase64: String): Boolean {
        val manifestBytes = manifestJson.toByteArray(StandardCharsets.UTF_8)
        val signatureBytes = try {
            decoder.decode(signatureBase64)
        } catch (_: IllegalArgumentException) {
            return false
        }

        if (signatureBytes.size != Sign.BYTES) {
            return false
        }

        return sodium.cryptoSignVerifyDetached(
            signatureBytes,
            manifestBytes,
            manifestBytes.size,
            releasePublicKey,
        )
    }
}
