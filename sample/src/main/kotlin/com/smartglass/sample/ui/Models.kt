package com.smartglass.sample.ui

import com.smartglass.actions.SmartGlassAction
import java.util.UUID

/**
 * Represents a message in the conversation.
 *
 * @property id Unique identifier for the message
 * @property content The text content of the message
 * @property timestamp Unix timestamp when the message was created
 * @property isFromUser Whether this message is from the user or the AI
 * @property actions List of actions associated with this message (for AI responses)
 * @property visualContext Optional visual context information (for AI responses)
 */
data class Message(
    val id: String = UUID.randomUUID().toString(),
    val content: String,
    val timestamp: Long = System.currentTimeMillis(),
    val isFromUser: Boolean,
    val actions: List<SmartGlassAction> = emptyList(),
    val visualContext: String? = null
)

/**
 * Represents the connection state of the smart glasses.
 */
enum class ConnectionState {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    STREAMING,
    ERROR
}

/**
 * Metrics for video streaming performance.
 *
 * @property fps Current frames per second
 * @property latencyMs Average latency in milliseconds
 * @property framesProcessed Total number of frames processed
 */
data class StreamingMetrics(
    val fps: Float,
    val latencyMs: Int,
    val framesProcessed: Int
)
