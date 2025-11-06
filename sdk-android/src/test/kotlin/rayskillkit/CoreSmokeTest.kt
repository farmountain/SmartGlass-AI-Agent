package rayskillkit

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import rayskillkit.core.Decision
import rayskillkit.core.OrtHub
import rayskillkit.core.Router
import rayskillkit.core.SkillRegistry
import rayskillkit.core.Telemetry
import rayskillkit.ui.TTS

class CoreSmokeTest {
    @Test
    fun instantiateCoreComponents() {
        val ortHub = OrtHub()
        assertFalse(ortHub.isConnected("local"))
        assertTrue(ortHub.connect("local"))
        assertTrue(ortHub.isConnected("local"))
        ortHub.disconnect("local")
        assertFalse(ortHub.isConnected("local"))

        val registry = SkillRegistry()
        val handler = Any()
        registry.registerSkill("demo", handler)
        assertTrue(registry.listSkills().contains("demo"))

        val router = Router(registry)
        assertTrue(router.route("demo", Any()))

        val decision = Decision(id = "1", skillName = "demo", confidence = 0.75f)
        assertTrue(decision.isConfident())

        val telemetry = Telemetry()
        telemetry.record("event")
        assertTrue(telemetry.events().isNotEmpty())

        val tts = TTS()
        tts.initialize()
        assertTrue(tts.speak("Hello"))
    }
}
