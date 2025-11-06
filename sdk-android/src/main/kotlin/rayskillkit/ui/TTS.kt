package rayskillkit.ui

class TTS {
    var isInitialized: Boolean = false
        private set

    fun initialize() {
        isInitialized = true
    }

    fun speak(text: String): Boolean {
        return isInitialized && text.isNotBlank()
    }
}
