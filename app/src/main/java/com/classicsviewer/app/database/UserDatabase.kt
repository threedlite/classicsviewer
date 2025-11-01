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
    version = 8,
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

        private val MIGRATION_7_8 = object : Migration(7, 8) {
            override fun migrate(database: SupportSQLiteDatabase) {
                // Ensure normalization_patterns table exists
                // (no-op if it already exists from previous version)
                database.execSQL("""
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

                database.execSQL("""
                    CREATE INDEX IF NOT EXISTS index_normalization_patterns_language
                    ON normalization_patterns(language)
                """)

                database.execSQL("""
                    CREATE INDEX IF NOT EXISTS index_normalization_patterns_package_id
                    ON normalization_patterns(package_id)
                """)

                database.execSQL("""
                    CREATE INDEX IF NOT EXISTS index_normalization_patterns_lang_pkg_pri
                    ON normalization_patterns(language, package_id, priority)
                """)
            }
        }

        fun getInstance(context: Context): UserDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    UserDatabase::class.java,
                    "user_data.db"
                )
                .addMigrations(MIGRATION_7_8)
                .fallbackToDestructiveMigration()
                .addCallback(object : RoomDatabase.Callback() {
                    override fun onOpen(db: SupportSQLiteDatabase) {
                        super.onOpen(db)
                        createNormalizationTableIfNeeded(db)
                        autoActivatePackageIfNeeded(db)
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

        private fun autoActivatePackageIfNeeded(db: SupportSQLiteDatabase) {
            try {
                android.util.Log.d("UserDatabase", "autoActivatePackageIfNeeded: Starting check")

                // Check lemma counts for debugging
                val totalLemmasCursor = db.query("SELECT COUNT(*) FROM user_dictionary_lemmas")
                var totalLemmas = 0
                if (totalLemmasCursor.moveToFirst()) {
                    totalLemmas = totalLemmasCursor.getInt(0)
                }
                totalLemmasCursor.close()
                android.util.Log.w("UserDatabase", "Total lemmas in database (any package): $totalLemmas")

                // Check if there's an active package
                val activeCursor = db.query("SELECT COUNT(*) FROM user_dictionary_packages WHERE is_active = 1")
                var hasActive = false
                if (activeCursor.moveToFirst()) {
                    hasActive = activeCursor.getInt(0) > 0
                }
                activeCursor.close()

                android.util.Log.d("UserDatabase", "autoActivatePackageIfNeeded: hasActive=$hasActive")

                if (!hasActive) {
                    // Check if any packages exist
                    val packageCursor = db.query("SELECT id, package_name FROM user_dictionary_packages ORDER BY import_date DESC LIMIT 1")
                    if (packageCursor.moveToFirst()) {
                        val packageId = packageCursor.getLong(0)
                        val packageName = packageCursor.getString(1)
                        packageCursor.close()

                        android.util.Log.w("UserDatabase", "No active package found - auto-activating package: $packageName (id=$packageId)")
                        db.execSQL("UPDATE user_dictionary_packages SET is_active = 1 WHERE id = ?", arrayOf(packageId))
                        android.util.Log.w("UserDatabase", "Package activated successfully")
                    } else {
                        android.util.Log.d("UserDatabase", "autoActivatePackageIfNeeded: No packages found in database")
                        packageCursor.close()
                    }
                } else {
                    android.util.Log.d("UserDatabase", "autoActivatePackageIfNeeded: Active package already exists")
                }
            } catch (e: Exception) {
                android.util.Log.e("UserDatabase", "Error auto-activating package", e)
            }
        }

        fun destroyInstance() {
            INSTANCE?.close()
            INSTANCE = null
        }
    }
}