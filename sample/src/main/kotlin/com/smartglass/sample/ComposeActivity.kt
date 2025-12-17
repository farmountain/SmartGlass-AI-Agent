package com.smartglass.sample

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import com.smartglass.sample.ui.ConversationScreen
import com.smartglass.sample.ui.theme.SmartGlassTheme

/**
 * Main activity using Jetpack Compose for the UI.
 *
 * This activity demonstrates the modern Compose-based UI for the SmartGlass sample app,
 * featuring:
 * - Chat-style conversation display
 * - Connection status visualization
 * - Real-time streaming metrics
 * - Action execution feedback
 */
class ComposeActivity : ComponentActivity() {
    private val viewModel: SmartGlassViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            SmartGlassTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val messages by viewModel.messages.collectAsState()
                    val connectionState by viewModel.connectionState.collectAsState()
                    val streamingMetrics by viewModel.streamingMetrics.collectAsState()

                    ConversationScreen(
                        messages = messages,
                        connectionState = connectionState,
                        streamingMetrics = streamingMetrics,
                        onSendMessage = { text -> viewModel.sendMessage(text) },
                        onConnect = { viewModel.connect() },
                        onDisconnect = { viewModel.disconnect() },
                        onOpenPrivacySettings = { openPrivacySettings() }
                    )
                }
            }
        }
    }

    /**
     * Open the privacy settings activity.
     */
    private fun openPrivacySettings() {
        startActivity(Intent(this, PrivacySettingsActivity::class.java))
    }
}
