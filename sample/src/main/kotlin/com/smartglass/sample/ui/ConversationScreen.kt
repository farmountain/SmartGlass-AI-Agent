package com.smartglass.sample.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.smartglass.actions.SmartGlassAction
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Main conversation screen displaying messages and connection status.
 *
 * Features:
 * - Chat-style message list with user and AI bubbles
 * - Connection status bar at the top
 * - Input field with send button at the bottom
 * - FAB for connection toggle
 *
 * @param messages List of conversation messages
 * @param connectionState Current connection state
 * @param streamingMetrics Optional streaming metrics
 * @param onSendMessage Callback when user sends a message
 * @param onConnect Callback to connect to glasses
 * @param onDisconnect Callback to disconnect from glasses
 * @param onOpenPrivacySettings Callback to open privacy settings
 * @param modifier Modifier for styling
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConversationScreen(
    messages: List<Message>,
    connectionState: ConnectionState,
    streamingMetrics: StreamingMetrics?,
    onSendMessage: (String) -> Unit,
    onConnect: () -> Unit,
    onDisconnect: () -> Unit,
    onOpenPrivacySettings: () -> Unit,
    modifier: Modifier = Modifier
) {
    var inputText by remember { mutableStateOf("") }
    val listState = rememberLazyListState()

    // Auto-scroll to bottom when new messages arrive
    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    Scaffold(
        topBar = {
            Column {
                TopAppBar(
                    title = { Text("SmartGlass AI") },
                    actions = {
                        IconButton(onClick = onOpenPrivacySettings) {
                            Icon(Icons.Default.Menu, contentDescription = "Privacy Settings")
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(
                        containerColor = MaterialTheme.colorScheme.primary,
                        titleContentColor = Color.White,
                        actionIconContentColor = Color.White
                    )
                )
                ConnectionStatusView(
                    state = connectionState,
                    deviceId = if (connectionState != ConnectionState.DISCONNECTED) "MOCK-001" else null,
                    streamingMetrics = streamingMetrics
                )
            }
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = {
                    if (connectionState == ConnectionState.DISCONNECTED || connectionState == ConnectionState.ERROR) {
                        onConnect()
                    } else {
                        onDisconnect()
                    }
                },
                containerColor = if (connectionState == ConnectionState.DISCONNECTED || connectionState == ConnectionState.ERROR) {
                    MaterialTheme.colorScheme.primary
                } else {
                    MaterialTheme.colorScheme.error
                }
            ) {
                Icon(
                    imageVector = if (connectionState == ConnectionState.DISCONNECTED || connectionState == ConnectionState.ERROR) {
                        Icons.Default.Send
                    } else {
                        Icons.Default.Close
                    },
                    contentDescription = if (connectionState == ConnectionState.DISCONNECTED || connectionState == ConnectionState.ERROR) {
                        "Connect"
                    } else {
                        "Disconnect"
                    }
                )
            }
        },
        modifier = modifier
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            // Messages list
            LazyColumn(
                state = listState,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .padding(horizontal = 8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(messages, key = { it.id }) { message ->
                    MessageBubble(message = message)
                }
            }

            // Input area
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                TextField(
                    value = inputText,
                    onValueChange = { inputText = it },
                    placeholder = { Text("Type a message...") },
                    modifier = Modifier.weight(1f),
                    colors = TextFieldDefaults.colors(
                        focusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                        unfocusedContainerColor = MaterialTheme.colorScheme.surfaceVariant
                    ),
                    maxLines = 3
                )
                Spacer(Modifier.width(8.dp))
                IconButton(
                    onClick = {
                        if (inputText.isNotBlank()) {
                            onSendMessage(inputText)
                            inputText = ""
                        }
                    },
                    enabled = inputText.isNotBlank()
                ) {
                    Icon(Icons.Default.Send, contentDescription = "Send")
                }
                IconButton(
                    onClick = { /* Future: audio input */ },
                    enabled = false
                ) {
                    Icon(Icons.Default.Mic, contentDescription = "Voice input")
                }
            }
        }
    }
}

/**
 * Displays a single message bubble.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun MessageBubble(message: Message) {
    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = if (message.isFromUser) Alignment.CenterEnd else Alignment.CenterStart
    ) {
        Card(
            colors = CardDefaults.cardColors(
                containerColor = if (message.isFromUser) {
                    MaterialTheme.colorScheme.primaryContainer
                } else {
                    MaterialTheme.colorScheme.surfaceVariant
                }
            ),
            modifier = Modifier
                .widthIn(max = 300.dp)
                .padding(vertical = 4.dp)
        ) {
            Column(modifier = Modifier.padding(12.dp)) {
                Text(
                    text = message.content,
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurface
                )
                
                Spacer(Modifier.height(4.dp))
                
                Text(
                    text = formatTime(message.timestamp),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                )

                // Visual context (for AI messages)
                if (!message.isFromUser && message.visualContext != null) {
                    Spacer(Modifier.height(8.dp))
                    Text(
                        text = "Context: ${message.visualContext}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )
                }

                // Action chips (for AI messages)
                if (!message.isFromUser && message.actions.isNotEmpty()) {
                    Spacer(Modifier.height(8.dp))
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(4.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        message.actions.forEach { action ->
                            ActionChipView(action = action)
                        }
                    }
                }
            }
        }
    }
}

/**
 * Displays an action chip for a SmartGlassAction.
 */
@Composable
private fun ActionChipView(action: SmartGlassAction) {
    val label = when (action) {
        is SmartGlassAction.ShowText -> "Show: ${action.title}"
        is SmartGlassAction.TtsSpeak -> "🔊 TTS"
        is SmartGlassAction.Navigate -> "📍 Navigate"
        is SmartGlassAction.RememberNote -> "📝 Note"
        is SmartGlassAction.OpenApp -> "📱 App"
        is SmartGlassAction.SystemHint -> "💡 Hint"
    }

    AssistChip(
        onClick = { /* Actions are already executed */ },
        label = {
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        },
        colors = AssistChipDefaults.assistChipColors(
            containerColor = MaterialTheme.colorScheme.secondary.copy(alpha = 0.2f)
        )
    )
}

/**
 * Formats a timestamp to HH:mm format.
 */
private fun formatTime(timestamp: Long): String {
    val formatter = SimpleDateFormat("HH:mm", Locale.getDefault())
    return formatter.format(Date(timestamp))
}
