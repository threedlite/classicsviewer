package com.classicsviewer.app.database

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.classicsviewer.app.database.dao.*
import com.classicsviewer.app.database.entities.*
import com.classicsviewer.app.data.ObbDatabaseHelper
import java.io.File

@Database(
    entities = [
        AuthorEntity::class,
        WorkEntity::class,
        BookEntity::class,
        TextLineEntity::class,
        WordFormEntity::class,
        LemmaMapEntity::class,
        DictionaryEntity::class,
        TranslationSegmentEntity::class
    ],
    version = 2,
    exportSchema = false
)
abstract class PerseusDatabase : RoomDatabase() {
    abstract fun authorDao(): AuthorDao
    abstract fun workDao(): WorkDao
    abstract fun bookDao(): BookDao
    abstract fun textLineDao(): TextLineDao
    abstract fun wordFormDao(): WordFormDao
    abstract fun lemmaDao(): LemmaDao
    abstract fun lemmaMapDao(): LemmaMapDao
    abstract fun dictionaryDao(): DictionaryDao
    abstract fun translationSegmentDao(): TranslationSegmentDao
    
    companion object {
        @Volatile
        private var INSTANCE: PerseusDatabase? = null
        
        fun getInstance(context: Context): PerseusDatabase {
            return INSTANCE ?: synchronized(this) {
                // Check if database needs to be extracted from OBB
                checkAndExtractFromObb(context)
                
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    PerseusDatabase::class.java,
                    "perseus_texts.db"
                )
                .fallbackToDestructiveMigration()
                .build()
                INSTANCE = instance
                instance
            }
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