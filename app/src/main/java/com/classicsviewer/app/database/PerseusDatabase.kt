package com.classicsviewer.app.database

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.classicsviewer.app.database.dao.*
import com.classicsviewer.app.database.entities.*
import com.classicsviewer.app.data.ObbDatabaseHelper
import com.classicsviewer.app.utils.PreferencesManager
import android.widget.Toast
import java.io.File

@Database(
    entities = [
        AuthorEntity::class,
        WorkEntity::class,
        BookEntity::class,
        TextLineEntity::class,
        WordEntity::class,
        LemmaMapEntity::class,
        DictionaryEntity::class,
        TranslationSegmentEntity::class,
        TranslationLookupEntity::class
    ],
    version = 4,
    exportSchema = false
)
abstract class PerseusDatabase : RoomDatabase() {
    abstract fun authorDao(): AuthorDao
    abstract fun workDao(): WorkDao
    abstract fun bookDao(): BookDao
    abstract fun textLineDao(): TextLineDao
    abstract fun wordDao(): WordDao
    abstract fun lemmaDao(): LemmaDao
    abstract fun lemmaMapDao(): LemmaMapDao
    abstract fun dictionaryDao(): DictionaryDao
    abstract fun translationSegmentDao(): TranslationSegmentDao
    
    companion object {
        @Volatile
        private var INSTANCE: PerseusDatabase? = null
        
        fun getInstance(context: Context): PerseusDatabase {
            return INSTANCE ?: synchronized(this) {
                // Check for external database first
                val externalDbUri = PreferencesManager.getExternalDatabaseUri(context)
                
                val instance = if (externalDbUri != null) {
                    // External database should already be copied during selection
                    val externalDbFile = File(context.getDatabasePath("dummy").parent, "external_perseus_texts.db")
                    
                    if (externalDbFile.exists() && externalDbFile.length() > 1000000) {
                        // Open the pre-copied external database
                        android.util.Log.d("PerseusDatabase", "Using pre-copied external database: ${externalDbFile.absolutePath}, size: ${externalDbFile.length() / (1024 * 1024)}MB")
                        
                        Room.databaseBuilder(
                            context.applicationContext,
                            PerseusDatabase::class.java,
                            externalDbFile.absolutePath
                        )
                        .fallbackToDestructiveMigration()
                        .build()
                    } else {
                        // External database not found or too small - fall back
                        android.util.Log.e("PerseusDatabase", "External database not found or invalid. File exists: ${externalDbFile.exists()}, size: ${externalDbFile.length()}")
                        android.os.Handler(android.os.Looper.getMainLooper()).post {
                            Toast.makeText(context, "External database not found. Using bundled database.", Toast.LENGTH_LONG).show()
                        }
                        // Clear the invalid URI
                        PreferencesManager.clearExternalDatabaseUri(context)
                        // Fall back to bundled database
                        createBundledDatabase(context)
                    }
                } else {
                    // Use bundled database
                    createBundledDatabase(context)
                }
                
                INSTANCE = instance
                instance
            }
        }
        
        private fun createBundledDatabase(context: Context): PerseusDatabase {
            // Check if database needs to be extracted from OBB
            checkAndExtractFromObb(context)
            
            return Room.databaseBuilder(
                context.applicationContext,
                PerseusDatabase::class.java,
                "perseus_texts.db"
            )
            .fallbackToDestructiveMigration()
            .build()
        }
        
        fun destroyInstance() {
            INSTANCE?.close()
            INSTANCE = null
        }
        
        private fun checkAndExtractFromObb(context: Context) {
            val dbFile = context.getDatabasePath("perseus_texts.db")
            
            // The extraction is now handled by DatabaseExtractionActivity
            // This method just logs the current state
            if (dbFile.exists()) {
                android.util.Log.d("PerseusDatabase", "Database found: ${dbFile.length()} bytes")
            } else {
                android.util.Log.d("PerseusDatabase", "Database not found - will need extraction")
            }
        }
        
        // Removed copyFromAssets - we only load from OBB now
    }
}