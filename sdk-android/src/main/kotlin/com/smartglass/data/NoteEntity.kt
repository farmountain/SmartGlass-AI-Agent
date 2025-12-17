package com.smartglass.data

import androidx.room.ColumnInfo
import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

/**
 * Entity representing a note stored in the local database.
 *
 * @property id Auto-generated unique identifier
 * @property content The text content of the note
 * @property visualContext Optional visual context when the note was created
 * @property timestamp Unix timestamp when the note was created
 * @property sourceActionId Optional ID linking to the source action
 * @property isSynced Whether the note has been synced to a remote server
 */
@Entity(tableName = "notes")
data class NoteEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    
    @ColumnInfo(name = "content")
    val content: String,
    
    @ColumnInfo(name = "visual_context")
    val visualContext: String? = null,
    
    @ColumnInfo(name = "timestamp")
    val timestamp: Long = System.currentTimeMillis(),
    
    @ColumnInfo(name = "source_action_id")
    val sourceActionId: String? = null,
    
    @ColumnInfo(name = "is_synced")
    val isSynced: Boolean = false
)

/**
 * Data Access Object for notes table.
 * Provides methods for querying, inserting, updating, and deleting notes.
 */
@Dao
interface NoteDao {
    /**
     * Get all notes ordered by timestamp (newest first).
     */
    @Query("SELECT * FROM notes ORDER BY timestamp DESC")
    fun getAllNotes(): Flow<List<NoteEntity>>
    
    /**
     * Get a specific note by its ID.
     */
    @Query("SELECT * FROM notes WHERE id = :noteId")
    suspend fun getNoteById(noteId: Long): NoteEntity?
    
    /**
     * Search notes by content.
     */
    @Query("SELECT * FROM notes WHERE content LIKE '%' || :searchQuery || '%' ORDER BY timestamp DESC")
    fun searchNotes(searchQuery: String): Flow<List<NoteEntity>>
    
    /**
     * Insert a new note and return its ID.
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertNote(note: NoteEntity): Long
    
    /**
     * Update an existing note.
     */
    @Update
    suspend fun updateNote(note: NoteEntity)
    
    /**
     * Delete a note.
     */
    @Delete
    suspend fun deleteNote(note: NoteEntity)
    
    /**
     * Delete notes older than the specified timestamp.
     * @return Number of notes deleted
     */
    @Query("DELETE FROM notes WHERE timestamp < :beforeTimestamp")
    suspend fun deleteNotesBefore(beforeTimestamp: Long): Int
    
    /**
     * Get the total count of notes.
     */
    @Query("SELECT COUNT(*) FROM notes")
    suspend fun getNotesCount(): Int
}
