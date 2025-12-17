package com.smartglass.data

import android.content.Context
import android.util.Log
import com.smartglass.sample.ui.Message
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.encodeToString
import kotlinx.serialization.decodeFromString

/**
 * Repository providing unified data access for SmartGlass application.
 * 
 * Handles all database operations and provides a clean API for the ViewModel layer.
 * Uses Room DAOs internally for data persistence.
 *
 * @property context Android context for database access
 */
class SmartGlassRepository(context: Context) {
    private val database = SmartGlassDatabase.getDatabase(context)
    private val noteDao = database.noteDao()
    private val messageDao = database.messageDao()
    private val knowledgeDao = database.knowledgeDao()
    
    private val json = Json { 
        ignoreUnknownKeys = true
        isLenient = true
    }
    
    companion object {
        private const val TAG = "SmartGlassRepository"
        private const val PREFS_NAME = "smartglass"
        private const val KEY_KNOWLEDGE_SEEDED = "knowledge_seeded"
    }
    
    // ==================== Notes ====================
    
    /**
     * Flow of all notes, ordered by timestamp (newest first).
     */
    val allNotes: Flow<List<NoteEntity>> = noteDao.getAllNotes()
    
    /**
     * Save a note to the database.
     *
     * @param content The note content
     * @param visualContext Optional visual context
     * @return The ID of the inserted note
     */
    suspend fun saveNote(content: String, visualContext: String? = null): Long {
        return noteDao.insertNote(
            NoteEntity(
                content = content,
                visualContext = visualContext
            )
        )
    }
    
    /**
     * Search notes by content.
     *
     * @param query Search query string
     * @return List of matching notes
     */
    suspend fun searchNotes(query: String): List<NoteEntity> {
        return noteDao.searchNotes(query).first()
    }
    
    /**
     * Delete old notes beyond retention period.
     *
     * @param daysToKeep Number of days to keep notes (default: 30)
     * @return Number of notes deleted
     */
    suspend fun deleteOldNotes(daysToKeep: Int = 30): Int {
        val cutoffTime = System.currentTimeMillis() - (daysToKeep * 24 * 60 * 60 * 1000L)
        return noteDao.deleteNotesBefore(cutoffTime)
    }
    
    // ==================== Messages ====================
    
    /**
     * Flow of all messages, ordered by timestamp (oldest first).
     */
    val allMessages: Flow<List<MessageEntity>> = messageDao.getAllMessages()
    
    /**
     * Save a message to the database.
     *
     * @param message The message to save
     */
    suspend fun saveMessage(message: Message) {
        try {
            messageDao.insertMessage(
                MessageEntity(
                    id = message.id,
                    content = message.content,
                    timestamp = message.timestamp,
                    isFromUser = message.isFromUser,
                    visualContext = message.visualContext,
                    actionsJson = null // Actions are not persisted in this version
                )
            )
        } catch (e: Exception) {
            Log.e(TAG, "Failed to save message", e)
        }
    }
    
    /**
     * Delete old messages beyond retention period.
     *
     * @param daysToKeep Number of days to keep messages (default: 7)
     * @return Number of messages deleted
     */
    suspend fun deleteOldMessages(daysToKeep: Int = 7): Int {
        val cutoffTime = System.currentTimeMillis() - (daysToKeep * 24 * 60 * 60 * 1000L)
        return messageDao.deleteMessagesBefore(cutoffTime)
    }
    
    /**
     * Clear all messages from the database.
     */
    suspend fun clearAllMessages() {
        messageDao.deleteAllMessages()
    }
    
    // ==================== Knowledge Base ====================
    
    /**
     * Query the knowledge base for relevant entries.
     *
     * @param query Search query string
     * @return List of relevant knowledge entries
     */
    suspend fun queryKnowledge(query: String): List<KnowledgeEntity> {
        return knowledgeDao.searchKnowledge(query, limit = 5)
    }
    
    /**
     * Add a new knowledge entry to the database.
     *
     * @param question The question text
     * @param answer The answer text
     * @param category Optional category
     * @return The ID of the inserted knowledge entry
     */
    suspend fun addKnowledge(question: String, answer: String, category: String? = null): Long {
        val keywords = (question + " " + answer).lowercase()
            .split("\\s+".toRegex())
            .filter { it.length > 3 }
            .joinToString(",")
        
        return knowledgeDao.insertKnowledge(
            KnowledgeEntity(
                question = question,
                answer = answer,
                category = category,
                keywords = keywords
            )
        )
    }
    
    /**
     * Record that a knowledge entry was accessed.
     *
     * @param id The knowledge entry ID
     */
    suspend fun recordKnowledgeAccess(id: Long) {
        knowledgeDao.recordAccess(id)
    }
    
    // ==================== Knowledge Base Seeding ====================
    
    /**
     * Seed the knowledge base with initial data from JSON asset.
     * Only runs once on first application launch.
     *
     * @param context Android context for accessing assets
     */
    suspend fun seedKnowledgeBase(context: Context) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        if (prefs.getBoolean(KEY_KNOWLEDGE_SEEDED, false)) {
            Log.d(TAG, "Knowledge base already seeded, skipping")
            return
        }
        
        try {
            val jsonString = context.assets.open("knowledge_base.json")
                .bufferedReader()
                .use { it.readText() }
            
            val entries = json.decodeFromString<List<KnowledgeSeed>>(jsonString)
            
            entries.forEach { seed ->
                addKnowledge(seed.question, seed.answer, seed.category)
            }
            
            prefs.edit().putBoolean(KEY_KNOWLEDGE_SEEDED, true).apply()
            Log.d(TAG, "Successfully seeded ${entries.size} knowledge entries")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to seed knowledge base", e)
        }
    }
}

/**
 * Data class for deserializing knowledge base seed data from JSON.
 */
@Serializable
data class KnowledgeSeed(
    val question: String,
    val answer: String,
    val category: String,
    val keywords: String
)
