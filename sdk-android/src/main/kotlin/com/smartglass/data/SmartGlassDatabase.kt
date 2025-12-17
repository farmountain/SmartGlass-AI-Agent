package com.smartglass.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

/**
 * Room database for SmartGlass application.
 * 
 * Provides persistent storage for:
 * - Notes: User-created notes with visual context
 * - Messages: Conversation history
 * - Knowledge: Offline FAQ and knowledge base
 *
 * Database is configured with fallbackToDestructiveMigration for development.
 * In production, proper migration strategies should be implemented.
 */
@Database(
    entities = [NoteEntity::class, MessageEntity::class, KnowledgeEntity::class],
    version = 1,
    exportSchema = true
)
abstract class SmartGlassDatabase : RoomDatabase() {
    /**
     * Data Access Object for notes.
     */
    abstract fun noteDao(): NoteDao
    
    /**
     * Data Access Object for messages.
     */
    abstract fun messageDao(): MessageDao
    
    /**
     * Data Access Object for knowledge base.
     */
    abstract fun knowledgeDao(): KnowledgeDao
    
    companion object {
        @Volatile
        private var INSTANCE: SmartGlassDatabase? = null
        
        /**
         * Get the singleton database instance.
         * 
         * Uses double-checked locking pattern to ensure thread-safe initialization.
         *
         * @param context Android context
         * @return Database instance
         */
        fun getDatabase(context: Context): SmartGlassDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    SmartGlassDatabase::class.java,
                    "smartglass_database"
                )
                    .fallbackToDestructiveMigration()
                    .build()
                INSTANCE = instance
                instance
            }
        }
    }
}
