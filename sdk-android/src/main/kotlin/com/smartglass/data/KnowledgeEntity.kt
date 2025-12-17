package com.smartglass.data

import androidx.room.ColumnInfo
import androidx.room.Dao
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

/**
 * Entity representing a knowledge base entry for offline FAQ and facts.
 *
 * @property id Auto-generated unique identifier
 * @property question The question text
 * @property answer The answer text
 * @property category Optional category for organizing knowledge
 * @property keywords Comma-separated keywords for search
 * @property confidenceScore Confidence score for the answer (0.0 to 1.0)
 * @property lastAccessed Unix timestamp of last access
 * @property accessCount Number of times this knowledge has been accessed
 */
@Entity(tableName = "knowledge_base")
data class KnowledgeEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    
    @ColumnInfo(name = "question")
    val question: String,
    
    @ColumnInfo(name = "answer")
    val answer: String,
    
    @ColumnInfo(name = "category")
    val category: String? = null,
    
    @ColumnInfo(name = "keywords")
    val keywords: String,
    
    @ColumnInfo(name = "confidence_score")
    val confidenceScore: Float = 1.0f,
    
    @ColumnInfo(name = "last_accessed")
    val lastAccessed: Long = System.currentTimeMillis(),
    
    @ColumnInfo(name = "access_count")
    val accessCount: Int = 0
)

/**
 * Data Access Object for knowledge_base table.
 * Provides methods for querying and managing offline knowledge.
 */
@Dao
interface KnowledgeDao {
    /**
     * Get all knowledge entries ordered by confidence and popularity.
     */
    @Query("SELECT * FROM knowledge_base ORDER BY confidence_score DESC, access_count DESC")
    fun getAllKnowledge(): Flow<List<KnowledgeEntity>>
    
    /**
     * Search knowledge base by query string.
     * Searches in question, answer, and keywords fields.
     */
    @Query("""
        SELECT * FROM knowledge_base 
        WHERE question LIKE '%' || :query || '%' 
           OR answer LIKE '%' || :query || '%' 
           OR keywords LIKE '%' || :query || '%'
        ORDER BY confidence_score DESC, access_count DESC
        LIMIT :limit
    """)
    suspend fun searchKnowledge(query: String, limit: Int = 5): List<KnowledgeEntity>
    
    /**
     * Insert a new knowledge entry and return its ID.
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertKnowledge(knowledge: KnowledgeEntity): Long
    
    /**
     * Update an existing knowledge entry.
     */
    @Update
    suspend fun updateKnowledge(knowledge: KnowledgeEntity)
    
    /**
     * Record access to a knowledge entry (updates timestamp and counter).
     */
    @Query("UPDATE knowledge_base SET last_accessed = :timestamp, access_count = access_count + 1 WHERE id = :id")
    suspend fun recordAccess(id: Long, timestamp: Long = System.currentTimeMillis())
    
    /**
     * Delete a knowledge entry.
     */
    @Query("DELETE FROM knowledge_base WHERE id = :id")
    suspend fun deleteKnowledge(id: Long)
}
