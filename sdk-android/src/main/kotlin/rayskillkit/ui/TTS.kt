package rayskillkit.ui

open class TTS {
    var isInitialized: Boolean = false
        private set

    open fun initialize() {
        isInitialized = true
    }

    open fun speak(text: String): Boolean {
        return isInitialized && text.isNotBlank()
    }
}
