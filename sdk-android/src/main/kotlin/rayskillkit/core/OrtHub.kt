package rayskillkit.core

class OrtHub {
    private val connectedEndpoints = mutableSetOf<String>()

    fun connect(endpoint: String): Boolean {
        connectedEndpoints += endpoint
        return true
    }

    fun disconnect(endpoint: String) {
        connectedEndpoints -= endpoint
    }

    fun isConnected(endpoint: String): Boolean = endpoint in connectedEndpoints
}
