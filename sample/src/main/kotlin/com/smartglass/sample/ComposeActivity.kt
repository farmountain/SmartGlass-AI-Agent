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
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.smartglass.sample.ui.BackendConfigDialog
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
    private lateinit var config: Config

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Initialize config
        config = Config(this)

        setContent {
            SmartGlassTheme {
                var showBackendDialog by remember { mutableStateOf(false) }
                
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
                        onOpenPrivacySettings = { openPrivacySettings() },
                        onOpenBackendSettings = { showBackendDialog = true }
                    )
                    
                    // Backend configuration dialog
                    if (showBackendDialog) {
                        BackendConfigDialog(
                            currentUrl = config.backendUrl,
                            config = config,
                            onSave = { newUrl ->
                                config.backendUrl = newUrl
                                viewModel.updateBackendUrl(newUrl)
                            },
                            onDismiss = { showBackendDialog = false }
                        )
                    }
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
