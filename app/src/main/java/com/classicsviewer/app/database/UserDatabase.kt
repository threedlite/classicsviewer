package com.classicsviewer.app.database

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.classicsviewer.app.database.dao.BookmarkDao
import com.classicsviewer.app.database.dao.UserDictionaryDao
import com.classicsviewer.app.database.dao.UserLemmaMappingDao
import com.classicsviewer.app.database.dao.UserDictionaryPackageDao
import com.classicsviewer.app.database.entities.BookmarkEntity
import com.classicsviewer.app.database.entities.UserDictionaryLemmaEntity
import com.classicsviewer.app.database.entities.UserLemmaMappingEntity
import com.classicsviewer.app.database.entities.UserDictionaryPackageEntity
import com.classicsviewer.app.database.helpers.NormalizationPatternHelper

@Database(
    entities = [
        BookmarkEntity::class,
        UserDictionaryLemmaEntity::class,
        UserLemmaMappingEntity::class,
        UserDictionaryPackageEntity::class
    ],
    version = 6,
    exportSchema = false
)
abstract class UserDatabase : RoomDatabase() {
    abstract fun bookmarkDao(): BookmarkDao
    abstract fun userDictionaryDao(): UserDictionaryDao
    abstract fun userLemmaMappingDao(): UserLemmaMappingDao
    abstract fun userDictionaryPackageDao(): UserDictionaryPackageDao
    
    companion object {
        @Volatile
        private var INSTANCE: UserDatabase? = null
        
        fun getInstance(context: Context): UserDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    UserDatabase::class.java,
                    "user_data.db"
                )
                .fallbackToDestructiveMigration()
                .addCallback(object : RoomDatabase.Callback() {
                    override fun onOpen(db: SupportSQLiteDatabase) {
                        super.onOpen(db)
                        createNormalizationTableIfNeeded(db)
                    }
                })
                .build()
                INSTANCE = instance
                instance
            }
        }

        fun getNormalizationPatternHelper(context: Context): NormalizationPatternHelper {
            val database = getInstance(context)
            return NormalizationPatternHelper(database.openHelper.writableDatabase)
        }

        private fun createNormalizationTableIfNeeded(db: SupportSQLiteDatabase) {
            // Check if table exists
            val cursor = db.query("SELECT name FROM sqlite_master WHERE type='table' AND name='normalization_patterns'")
            val tableExists = cursor.count > 0
            cursor.close()

            if (!tableExists) {
                android.util.Log.d("UserDatabase", "Creating normalization_patterns table")

                // Create table
                db.execSQL("""
                    CREATE TABLE IF NOT EXISTS normalization_patterns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                        package_id INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        pattern TEXT NOT NULL,
                        replacement TEXT NOT NULL,
                        description TEXT,
                        priority INTEGER NOT NULL,
                        created_at INTEGER NOT NULL
                    )
                """)

                // Create indices
                db.execSQL("""
                    CREATE INDEX IF NOT EXISTS index_normalization_patterns_language
                    ON normalization_patterns(language)
                """)

                db.execSQL("""
                    CREATE INDEX IF NOT EXISTS index_normalization_patterns_package_id
                    ON normalization_patterns(package_id)
                """)

                db.execSQL("""
                    CREATE INDEX IF NOT EXISTS index_normalization_patterns_lang_pkg_pri
                    ON normalization_patterns(language, package_id, priority)
                """)

                android.util.Log.d("UserDatabase", "normalization_patterns table created successfully")
            }
        }
        
        fun destroyInstance() {
            INSTANCE?.close()
            INSTANCE = null
        }
    }
}