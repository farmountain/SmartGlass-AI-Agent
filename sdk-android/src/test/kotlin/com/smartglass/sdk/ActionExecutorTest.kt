package com.smartglass.sdk

import android.app.Application
import android.content.Intent
import android.content.pm.ActivityInfo
import android.content.pm.ResolveInfo
import android.net.Uri
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.robolectric.Shadows.shadowOf

class ActionExecutorTest {

    @Test
    fun `navigate action launches maps intent with encoded destination`() {
        val application = ApplicationProvider.getApplicationContext<Application>()
        val destination = "Central Park"
        val encodedUri = Uri.parse("geo:0,0?q=${Uri.encode(destination)}")

        val mapsIntent = Intent(Intent.ACTION_VIEW, encodedUri).apply {
            setPackage("com.google.android.apps.maps")
        }

        shadowOf(application.packageManager).addResolveInfoForIntent(
            mapsIntent,
            ResolveInfo().apply { activityInfo = ActivityInfo().apply { packageName = "com.google.android.apps.maps" } },
        )

        val actions = listOf(Action(type = "NAVIGATE", payload = mapOf("destination" to destination)))

        ActionExecutor.execute(actions, application)

        val startedIntent = shadowOf(application).nextStartedActivity
        assertEquals("geo:0,0?q=Central%20Park", startedIntent.dataString)
        assertEquals("com.google.android.apps.maps", startedIntent.`package`)
        assertEquals(Intent.ACTION_VIEW, startedIntent.action)
        assertTrue(startedIntent.flags and Intent.FLAG_ACTIVITY_NEW_TASK != 0)
    }
}
