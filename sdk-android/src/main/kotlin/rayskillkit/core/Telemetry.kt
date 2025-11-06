package rayskillkit.core

class Telemetry {
    private val events = mutableListOf<String>()

    fun record(event: String) {
        events += event
    }

    fun clear() {
        events.clear()
    }

    fun events(): List<String> = events.toList()
}
