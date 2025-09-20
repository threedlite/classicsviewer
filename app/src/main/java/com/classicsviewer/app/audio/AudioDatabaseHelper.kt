package com.classicsviewer.app.audio

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import android.util.Log
import java.io.File

class AudioDatabaseHelper(private val context: Context) {
    companion object {
        private const val DATABASE_NAME = "audio_data.db"
        private const val DATABASE_VERSION = 1
        private const val TAG = "AudioDatabaseHelper"
        
        // Table creation SQL
        private const val CREATE_AUDIO_PACKAGES_TABLE = """
            CREATE TABLE IF NOT EXISTS audio_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_name TEXT NOT NULL UNIQUE,
                zip_filename TEXT NOT NULL,
                description TEXT,
                import_date INTEGER DEFAULT (strftime('%s', 'now') * 1000),
                total_files INTEGER,
                file_size_bytes INTEGER,
                is_active INTEGER DEFAULT 0,
                source_url TEXT,
                attribution TEXT
            )
        """
        
        private const val CREATE_AUDIO_MAPPINGS_TABLE = """
            CREATE TABLE IF NOT EXISTS audio_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_id INTEGER NOT NULL,
                author_name TEXT NOT NULL,
                work_title TEXT NOT NULL,
                book_number INTEGER NOT NULL,
                line_number INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                file_format TEXT NOT NULL,
                duration_ms INTEGER,
                created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000),
                FOREIGN KEY (package_id) REFERENCES audio_packages(id) ON DELETE CASCADE,
                UNIQUE(package_id, author_name, work_title, book_number, line_number)
            )
        """
        
        private const val CREATE_AUDIO_MAPPINGS_INDEX = """
            CREATE INDEX IF NOT EXISTS idx_audio_mappings_lookup 
            ON audio_mappings(package_id, author_name, work_title, book_number, line_number)
        """
        
        private const val CREATE_AUDIO_MAPPINGS_ACTIVE_INDEX = """
            CREATE INDEX IF NOT EXISTS idx_audio_mappings_active
            ON audio_mappings(author_name, work_title, book_number, line_number, package_id)
        """
    }
    
    private val dbPath = context.getDatabasePath(DATABASE_NAME)
    private var database: SQLiteDatabase? = null
    
    fun ensureTablesExist() {
        try {
            val db = getDatabase()
            db.execSQL(CREATE_AUDIO_PACKAGES_TABLE)
            db.execSQL(CREATE_AUDIO_MAPPINGS_TABLE)
            db.execSQL(CREATE_AUDIO_MAPPINGS_INDEX)
            db.execSQL(CREATE_AUDIO_MAPPINGS_ACTIVE_INDEX)
            Log.d(TAG, "Audio tables created/verified successfully")
        } catch (e: Exception) {
            Log.e(TAG, "Error creating audio tables", e)
            throw e
        }
    }
    
    fun hasAudioData(): Boolean {
        return try {
            if (!dbPath.exists()) return false
            val db = getDatabase()
            val cursor = db.rawQuery("SELECT COUNT(*) FROM audio_mappings", null)
            val count = cursor.use {
                if (it.moveToFirst()) it.getInt(0) else 0
            }
            count > 0
        } catch (e: Exception) {
            Log.e(TAG, "Error checking for audio data", e)
            false
        }
    }
    
    fun getActivePackageId(): Long? {
        return try {
            val db = getDatabase()
            val cursor = db.query("audio_packages", 
                arrayOf("id"), "is_active = 1", 
                null, null, null, null)
            cursor.use {
                if (it.moveToFirst()) it.getLong(0) else null
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error getting active package", e)
            null
        }
    }
    
    fun setActivePackage(packageId: Long): Boolean {
        return try {
            val db = getDatabase()
            db.beginTransaction()
            try {
                // Deactivate all packages
                db.execSQL("UPDATE audio_packages SET is_active = 0")
                // Activate selected package
                db.execSQL("UPDATE audio_packages SET is_active = 1 WHERE id = ?", 
                    arrayOf(packageId))
                db.setTransactionSuccessful()
                true
            } finally {
                db.endTransaction()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error setting active package", e)
            false
        }
    }
    
    fun getAudioForLine(authorName: String, workTitle: String, 
                       bookNumber: Int, lineNumber: Int): AudioMapping? {
        return try {
            val db = getDatabase()
            val sql = """
                SELECT m.* FROM audio_mappings m
                JOIN audio_packages p ON m.package_id = p.id
                WHERE p.is_active = 1 
                AND m.author_name = ? 
                AND m.work_title = ?
                AND m.book_number = ? 
                AND m.line_number = ?
            """
            val cursor = db.rawQuery(sql, 
                arrayOf(authorName, workTitle, bookNumber.toString(), lineNumber.toString()))
            
            cursor.use {
                if (it.moveToFirst()) {
                    AudioMapping(
                        id = it.getLong(it.getColumnIndexOrThrow("id")),
                        packageId = it.getLong(it.getColumnIndexOrThrow("package_id")),
                        authorName = it.getString(it.getColumnIndexOrThrow("author_name")),
                        workTitle = it.getString(it.getColumnIndexOrThrow("work_title")),
                        bookNumber = it.getInt(it.getColumnIndexOrThrow("book_number")),
                        lineNumber = it.getInt(it.getColumnIndexOrThrow("line_number")),
                        filePath = it.getString(it.getColumnIndexOrThrow("file_path")),
                        fileFormat = it.getString(it.getColumnIndexOrThrow("file_format")),
                        durationMs = it.getLong(it.getColumnIndexOrThrow("duration_ms"))
                    )
                } else null
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error getting audio for line", e)
            null
        }
    }
    
    fun getAudioForLineRange(authorName: String, workTitle: String, 
                            bookNumber: Int, startLine: Int, endLine: Int): List<AudioMapping> {
        return try {
            val db = getDatabase()
            val sql = """
                SELECT m.* FROM audio_mappings m
                JOIN audio_packages p ON m.package_id = p.id
                WHERE p.is_active = 1 
                AND m.author_name = ? 
                AND m.work_title = ?
                AND m.book_number = ? 
                AND m.line_number BETWEEN ? AND ?
                ORDER BY m.line_number
            """
            val cursor = db.rawQuery(sql, 
                arrayOf(authorName, workTitle, bookNumber.toString(), 
                       startLine.toString(), endLine.toString()))
            
            val mappings = mutableListOf<AudioMapping>()
            cursor.use {
                while (it.moveToNext()) {
                    mappings.add(AudioMapping(
                        id = it.getLong(it.getColumnIndexOrThrow("id")),
                        packageId = it.getLong(it.getColumnIndexOrThrow("package_id")),
                        authorName = it.getString(it.getColumnIndexOrThrow("author_name")),
                        workTitle = it.getString(it.getColumnIndexOrThrow("work_title")),
                        bookNumber = it.getInt(it.getColumnIndexOrThrow("book_number")),
                        lineNumber = it.getInt(it.getColumnIndexOrThrow("line_number")),
                        filePath = it.getString(it.getColumnIndexOrThrow("file_path")),
                        fileFormat = it.getString(it.getColumnIndexOrThrow("file_format")),
                        durationMs = it.getLong(it.getColumnIndexOrThrow("duration_ms"))
                    ))
                }
            }
            mappings
        } catch (e: Exception) {
            Log.e(TAG, "Error getting audio for line range", e)
            emptyList()
        }
    }
    
    fun getAllPackages(): List<AudioPackage> {
        return try {
            val db = getDatabase()
            val cursor = db.query("audio_packages", null, null, 
                null, null, null, "import_date DESC")
            
            val packages = mutableListOf<AudioPackage>()
            cursor.use {
                while (it.moveToNext()) {
                    packages.add(AudioPackage(
                        id = it.getLong(it.getColumnIndexOrThrow("id")),
                        packageName = it.getString(it.getColumnIndexOrThrow("package_name")),
                        zipFilename = it.getString(it.getColumnIndexOrThrow("zip_filename")),
                        description = it.getString(it.getColumnIndexOrThrow("description")),
                        importDate = it.getLong(it.getColumnIndexOrThrow("import_date")),
                        totalFiles = it.getInt(it.getColumnIndexOrThrow("total_files")),
                        fileSizeBytes = it.getLong(it.getColumnIndexOrThrow("file_size_bytes")),
                        isActive = it.getInt(it.getColumnIndexOrThrow("is_active")) == 1,
                        sourceUrl = it.getString(it.getColumnIndexOrThrow("source_url")),
                        attribution = it.getString(it.getColumnIndexOrThrow("attribution"))
                    ))
                }
            }
            packages
        } catch (e: Exception) {
            Log.e(TAG, "Error getting all packages", e)
            emptyList()
        }
    }
    
    fun deletePackage(packageId: Long): Boolean {
        return try {
            val db = getDatabase()
            val rowsDeleted = db.delete("audio_packages", "id = ?", arrayOf(packageId.toString()))
            rowsDeleted > 0
        } catch (e: Exception) {
            Log.e(TAG, "Error deleting package", e)
            false
        }
    }
    
    private fun getDatabase(): SQLiteDatabase {
        if (database == null || !database!!.isOpen) {
            database = SQLiteDatabase.openOrCreateDatabase(dbPath, null)
        }
        return database!!
    }
    
    fun insertBundledPackage(packageId: Long, packageName: String, metadata: org.json.JSONObject): Boolean {
        return try {
            val db = getDatabase()
            
            // Begin transaction
            db.beginTransaction()
            try {
                // Clear any existing default package data
                db.delete("audio_mappings", "package_id = ?", arrayOf(packageId.toString()))
                db.delete("audio_packages", "id = ?", arrayOf(packageId.toString()))
                
                // Insert package record with special ID
                db.execSQL("""
                    INSERT INTO audio_packages (
                        id, package_name, zip_filename, description, 
                        total_files, file_size_bytes, is_active, 
                        source_url, attribution
                    ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                """, arrayOf(
                    packageId,
                    packageName,
                    "homer_iliad_chamberlain_audio_7.zip",
                    "Bundled audio for Homer's Iliad",
                    metadata.optInt("total_files", 0),
                    metadata.optLong("file_size", 0),
                    "bundled",
                    "Chamberlain translation"
                ))
                
                // Deactivate other packages
                db.execSQL("UPDATE audio_packages SET is_active = 0 WHERE id != ?", arrayOf(packageId))
                
                // Import mappings from metadata
                val mappings = metadata.getJSONArray("mappings")
                for (i in 0 until mappings.length()) {
                    val mapping = mappings.getJSONObject(i)
                    
                    db.execSQL("""
                        INSERT INTO audio_mappings (
                            package_id, author_name, work_title, book_number, 
                            line_number, file_path, file_format
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, arrayOf(
                        packageId,
                        mapping.getString("author"),
                        mapping.getString("work"),
                        mapping.getInt("book"),
                        mapping.getInt("line"),
                        mapping.getString("file_path"),
                        "mp3"
                    ))
                }
                
                db.setTransactionSuccessful()
                Log.d(TAG, "Imported ${mappings.length()} audio mappings for bundled package")
                true
            } finally {
                db.endTransaction()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error inserting bundled package", e)
            false
        }
    }
    
    fun close() {
        database?.close()
        database = null
    }
}

data class AudioPackage(
    val id: Long,
    val packageName: String,
    val zipFilename: String,
    val description: String?,
    val importDate: Long,
    val totalFiles: Int,
    val fileSizeBytes: Long,
    var isActive: Boolean,  // Changed to var for mutability
    val sourceUrl: String?,
    val attribution: String?
)

data class AudioMapping(
    val id: Long,
    val packageId: Long,
    val authorName: String,
    val workTitle: String,
    val bookNumber: Int,
    val lineNumber: Int,
    val filePath: String,
    val fileFormat: String,
    val durationMs: Long
)