package rayskillkit.updates

import com.goterl.lazysodium.LazySodiumJava
import com.goterl.lazysodium.SodiumJava
import com.goterl.lazysodium.interfaces.Sign
import java.nio.charset.StandardCharsets
import java.util.Base64
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import org.junit.Test

class ManifestVerifierTest {

    private val sodium = LazySodiumJava(SodiumJava())
    private val manifestJson = """{"version":"1.0.0","files":["skill.bin"]}"""
    private val keyPair = sodium.cryptoSignKeypair()
    private val verifier = ManifestVerifier(sodium, keyPair.publicKey.asBytes)
    private val validSignature = sign(manifestJson, keyPair.secretKey.asBytes)

    @Test
    fun `returns true when signature matches manifest`() {
        assertTrue(verifier.verify(manifestJson, validSignature))
    }

    @Test
    fun `returns false when signature is corrupted`() {
        val corruptedSignature = corruptSignature(validSignature)

        assertFalse(verifier.verify(manifestJson, corruptedSignature))
    }

    private fun sign(manifestJson: String, secretKey: ByteArray): String {
        val message = manifestJson.toByteArray(StandardCharsets.UTF_8)
        val signature = ByteArray(Sign.BYTES)
        val success = sodium.cryptoSignDetached(signature, message, message.size.toLong(), secretKey)
        check(success) { "Unable to sign manifest fixture" }
        return Base64.getEncoder().encodeToString(signature)
    }

    private fun corruptSignature(signatureBase64: String): String {
        val decoded = Base64.getDecoder().decode(signatureBase64)
        decoded[0] = decoded[0].inv()
        return Base64.getEncoder().encodeToString(decoded)
    }
}
