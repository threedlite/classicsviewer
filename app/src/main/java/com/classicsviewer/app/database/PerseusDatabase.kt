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
import android.content.Intent
import android.os.Environment
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlinx.coroutines.runBlocking

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
                try {
                    android.util.Log.d("PerseusDatabase", "Attempting to create/open database")
                    
                    // Check for external database first
                    val externalDbUri = PreferencesManager.getExternalDatabaseUri(context)
                    
                    val instance = if (externalDbUri != null) {
                        android.util.Log.d("PerseusDatabase", "Attempting to use external database: $externalDbUri")
                        
                        // External database should already be copied during selection
                        val externalDbFile = File(context.getDatabasePath("dummy").parent, "external_perseus_texts.db")
                        
                        if (externalDbFile.exists() && externalDbFile.length() > 1000) {
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
                        android.util.Log.d("PerseusDatabase", "Using bundled database")
                        createBundledDatabase(context)
                    }
                    
                    android.util.Log.d("PerseusDatabase", "Database opened successfully")
                    
                    // Force Room to validate schema by triggering a simple query
                    try {
                        instance.openHelper.writableDatabase
                        android.util.Log.d("PerseusDatabase", "Schema validation passed")
                    } catch (e: Exception) {
                        android.util.Log.e("PerseusDatabase", "Schema validation failed", e)
                        throw e
                    }
                    
                    INSTANCE = instance
                    instance
                    
                } catch (e: Exception) {
                    // Log comprehensive error information
                    android.util.Log.e("PerseusDatabase", "Database initialization failed", e)
                    android.util.Log.e("PerseusDatabase", "Error type: ${e.javaClass.name}")
                    android.util.Log.e("PerseusDatabase", "Error message: ${e.message}")
                    android.util.Log.e("PerseusDatabase", "Stack trace:", e)
                    
                    // Log context information for debugging
                    val externalDbUri = PreferencesManager.getExternalDatabaseUri(context)
                    android.util.Log.e("PerseusDatabase", "Context: ${context.javaClass.name}")
                    android.util.Log.e("PerseusDatabase", "External DB URI: $externalDbUri")
                    android.util.Log.e("PerseusDatabase", "DB Path: ${context.getDatabasePath("perseus_texts.db").absolutePath}")
                    android.util.Log.e("PerseusDatabase", "DB Exists: ${context.getDatabasePath("perseus_texts.db").exists()}")
                    android.util.Log.e("PerseusDatabase", "DB Size: ${context.getDatabasePath("perseus_texts.db").length()}")
                    
                    // Try to export bookmarks if using bundled database
                    var backupPath: String? = null
                    if (externalDbUri == null) {
                        backupPath = tryExportBookmarks(context)
                    }
                    
                    // Show error activity
                    val intent = Intent(context, com.classicsviewer.app.DatabaseErrorActivity::class.java)
                    intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                    intent.putExtra("is_external_db", externalDbUri != null)
                    intent.putExtra("backup_path", backupPath)
                    intent.putExtra("error_details", "${e.javaClass.simpleName}: ${e.message}")
                    context.startActivity(intent)
                    
                    // Throw custom exception to prevent further execution
                    throw DatabaseFatalException("Database could not be initialized: ${e.message}")
                }
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
        
        private fun tryExportBookmarks(context: Context): String? {
            return try {
                android.util.Log.d("PerseusDatabase", "Attempting to export bookmarks")
                
                // Try to get bookmarks from UserDatabase
                val userDb = UserDatabase.getInstance(context)
                val bookmarkDao = userDb.bookmarkDao()
                
                // Use runBlocking since we're already in a critical error path
                val bookmarks = runBlocking {
                    try {
                        bookmarkDao.getAllBookmarksForExport()
                    } catch (e: Exception) {
                        android.util.Log.e("PerseusDatabase", "Failed to retrieve bookmarks", e)
                        emptyList()
                    }
                }
                
                if (bookmarks.isEmpty()) {
                    android.util.Log.d("PerseusDatabase", "No bookmarks to export")
                    return null
                }
                
                // Build CSV content (matching existing export format from BookmarksActivity)
                val csvContent = buildString {
                    // CSV Header
                    appendLine("work_id,book_id,line_number,sequence_number,author_name,work_title,book_label,line_text,note,created_at,last_accessed")
                    
                    // CSV Data
                    bookmarks.forEach { bookmark ->
                        append("\"${escapeCSV(bookmark.workId)}\",")
                        append("\"${escapeCSV(bookmark.bookId)}\",")
                        append("${bookmark.lineNumber},")
                        append("${bookmark.sequenceNumber},")
                        append("\"${escapeCSV(bookmark.authorName)}\",")
                        append("\"${escapeCSV(bookmark.workTitle)}\",")
                        append("\"${escapeCSV(bookmark.bookLabel ?: "")}\",")
                        append("\"${escapeCSV(bookmark.lineText)}\",")
                        append("\"${escapeCSV(bookmark.note ?: "")}\",")
                        append("${bookmark.createdAt},")
                        appendLine("${bookmark.lastAccessed}")
                    }
                }
                
                // Save to Download folder
                val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
                val filename = "bookmarks_${timestamp}.csv"
                val downloadsDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
                
                if (!downloadsDir.exists()) {
                    downloadsDir.mkdirs()
                }
                
                val backupFile = File(downloadsDir, filename)
                backupFile.writeText(csvContent)
                
                android.util.Log.i("PerseusDatabase", "Bookmarks exported successfully to: ${backupFile.absolutePath}")
                return "Download/$filename"
                
            } catch (e: Exception) {
                android.util.Log.e("PerseusDatabase", "Failed to export bookmarks", e)
                android.util.Log.e("PerseusDatabase", "Export error type: ${e.javaClass.name}")
                android.util.Log.e("PerseusDatabase", "Export error message: ${e.message}")
                null
            }
        }
        
        private fun escapeCSV(value: String): String {
            return value.replace("\"", "\"\"")
        }
    }
}