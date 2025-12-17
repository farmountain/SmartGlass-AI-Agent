package com.smartglass.sample.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp

/**
 * Displays the connection status of the smart glasses.
 *
 * Shows a color-coded banner with:
 * - Connection state (disconnected/connecting/connected/streaming/error)
 * - Device ID when connected
 * - FPS and latency metrics when streaming
 *
 * @param state Current connection state
 * @param deviceId Optional device identifier
 * @param streamingMetrics Optional streaming performance metrics
 * @param modifier Modifier for styling
 */
@Composable
fun ConnectionStatusView(
    state: ConnectionState,
    deviceId: String?,
    streamingMetrics: StreamingMetrics?,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .background(statusColor(state))
            .padding(12.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.weight(1f)
        ) {
            Icon(
                imageVector = statusIcon(state),
                contentDescription = null,
                tint = Color.White
            )
            Spacer(Modifier.width(8.dp))
            Column {
                Text(
                    text = statusText(state),
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color.White
                )
                if (deviceId != null) {
                    Text(
                        text = "Device: $deviceId",
                        style = MaterialTheme.typography.bodySmall,
                        color = Color.White.copy(alpha = 0.7f)
                    )
                }
            }
        }

        // Streaming metrics
        if (streamingMetrics != null && state == ConnectionState.STREAMING) {
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = "${streamingMetrics.fps.toInt()} FPS",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color.White
                )
                Text(
                    text = "${streamingMetrics.latencyMs}ms",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color.White.copy(alpha = 0.7f)
                )
            }
        }
    }
}

@Composable
private fun statusColor(state: ConnectionState): Color = when (state) {
    ConnectionState.DISCONNECTED -> Color(0xFF9E9E9E) // Gray
    ConnectionState.CONNECTING -> Color(0xFFFFA726) // Orange
    ConnectionState.CONNECTED -> Color(0xFF66BB6A) // Green
    ConnectionState.STREAMING -> Color(0xFF42A5F5) // Blue
    ConnectionState.ERROR -> Color(0xFFEF5350) // Red
}

@Composable
private fun statusIcon(state: ConnectionState): ImageVector = when (state) {
    ConnectionState.DISCONNECTED -> Icons.Default.Close
    ConnectionState.CONNECTING -> Icons.Default.Refresh
    ConnectionState.CONNECTED -> Icons.Default.Check
    ConnectionState.STREAMING -> Icons.Default.PlayArrow
    ConnectionState.ERROR -> Icons.Default.Warning
}

private fun statusText(state: ConnectionState): String = when (state) {
    ConnectionState.DISCONNECTED -> "Not Connected"
    ConnectionState.CONNECTING -> "Connecting..."
    ConnectionState.CONNECTED -> "Connected"
    ConnectionState.STREAMING -> "Streaming"
    ConnectionState.ERROR -> "Connection Error"
}
