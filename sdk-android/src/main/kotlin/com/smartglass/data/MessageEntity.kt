package com.smartglass.data

import androidx.room.ColumnInfo
import androidx.room.Dao
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import kotlinx.coroutines.flow.Flow
import java.util.UUID

/**
 * Entity representing a conversation message stored in the local database.
 *
 * @property id Unique identifier for the message
 * @property content The text content of the message
 * @property timestamp Unix timestamp when the message was created
 * @property isFromUser Whether this message is from the user or the AI
 * @property visualContext Optional visual context associated with the message
 * @property sessionId Optional session identifier for grouping related messages
 * @property actionsJson JSON-serialized list of actions associated with this message
 */
@Entity(tableName = "messages")
data class MessageEntity(
    @PrimaryKey
    val id: String = UUID.randomUUID().toString(),
    
    @ColumnInfo(name = "content")
    val content: String,
    
    @ColumnInfo(name = "timestamp")
    val timestamp: Long = System.currentTimeMillis(),
    
    @ColumnInfo(name = "is_from_user")
    val isFromUser: Boolean,
    
    @ColumnInfo(name = "visual_context")
    val visualContext: String? = null,
    
    @ColumnInfo(name = "session_id")
    val sessionId: String? = null,
    
    @ColumnInfo(name = "actions_json")
    val actionsJson: String? = null
)

/**
 * Data Access Object for messages table.
 * Provides methods for querying, inserting, and managing conversation messages.
 */
@Dao
interface MessageDao {
    /**
     * Get all messages ordered by timestamp (oldest first for conversation flow).
     */
    @Query("SELECT * FROM messages ORDER BY timestamp ASC")
    fun getAllMessages(): Flow<List<MessageEntity>>
    
    /**
     * Get messages for a specific session.
     */
    @Query("SELECT * FROM messages WHERE session_id = :sessionId ORDER BY timestamp ASC")
    fun getMessagesBySession(sessionId: String): Flow<List<MessageEntity>>
    
    /**
     * Get recent messages after a specific timestamp.
     */
    @Query("SELECT * FROM messages WHERE timestamp >= :afterTimestamp ORDER BY timestamp ASC")
    fun getRecentMessages(afterTimestamp: Long): Flow<List<MessageEntity>>
    
    /**
     * Insert a new message.
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMessage(message: MessageEntity)
    
    /**
     * Delete messages older than the specified timestamp.
     * @return Number of messages deleted
     */
    @Query("DELETE FROM messages WHERE timestamp < :beforeTimestamp")
    suspend fun deleteMessagesBefore(beforeTimestamp: Long): Int
    
    /**
     * Delete all messages.
     */
    @Query("DELETE FROM messages")
    suspend fun deleteAllMessages()
    
    /**
     * Get the total count of messages.
     */
    @Query("SELECT COUNT(*) FROM messages")
    suspend fun getMessagesCount(): Int
}
