package com.classicsviewer.app.data

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.os.Build
import android.os.Environment
import android.os.storage.StorageManager
import java.io.File
import java.io.FileOutputStream
import java.util.zip.ZipFile
import java.util.zip.ZipEntry
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Helper class for handling database stored in OBB expansion files
 */
class ObbDatabaseHelper(private val context: Context) {
    
    companion object {
        private const val OBB_VERSION = 1
        private const val DB_NAME = "perseus_texts.db"
    }
    
    /**
     * Get the path to the OBB file if it exists
     */
    fun getObbDatabasePath(): File? {
        // Try multiple possible OBB locations
        val possiblePaths = listOf(
            // External storage with Environment
            File(Environment.getExternalStorageDirectory(), "Android/obb/${context.packageName}/main.$OBB_VERSION.${context.packageName}.obb"),
            // Hardcoded /sdcard path
            File("/sdcard/Android/obb/${context.packageName}/main.$OBB_VERSION.${context.packageName}.obb"),
            // Context's OBB directory
            File(context.obbDir, "main.$OBB_VERSION.${context.packageName}.obb")
        )
        
        for (path in possiblePaths) {
            android.util.Log.d("ObbDatabaseHelper", "Checking OBB at: ${path.absolutePath}, exists: ${path.exists()}")
            if (path.exists()) {
                return path
            }
        }
        
        return null
    }
    
    /**
     * Check if OBB file exists
     */
    fun isObbAvailable(): Boolean {
        return getObbDatabasePath()?.exists() == true
    }
    
    /**
     * Extract database from OBB file to internal storage
     * Now supports both compressed (ZIP) and uncompressed OBB files
     */
    suspend fun extractDatabaseFromObb(progressCallback: ((Float) -> Unit)? = null): Boolean = withContext(Dispatchers.IO) {
        val obbFile = getObbDatabasePath() ?: return@withContext false
        
        try {
            val targetDb = context.getDatabasePath(DB_NAME)
            targetDb.parentFile?.mkdirs()
            
            // Check if it's a ZIP file by trying to open it
            val isZipFile = try {
                ZipFile(obbFile).use { true }
            } catch (e: Exception) {
                false
            }
            
            if (isZipFile) {
                // Extract from ZIP
                android.util.Log.d("ObbDatabaseHelper", "Extracting from compressed OBB (ZIP)")
                extractFromZip(obbFile, targetDb, progressCallback)
            } else {
                // Direct copy (legacy uncompressed OBB)
                android.util.Log.d("ObbDatabaseHelper", "Copying from uncompressed OBB")
                var bytesCopied = 0L
                val totalBytes = obbFile.length()
                
                obbFile.inputStream().buffered(1024 * 1024).use { input ->
                    targetDb.outputStream().buffered(1024 * 1024).use { output ->
                        val buffer = ByteArray(1024 * 1024) // 1MB buffer
                        var bytesRead: Int
                        
                        while (input.read(buffer).also { bytesRead = it } != -1) {
                            output.write(buffer, 0, bytesRead)
                            bytesCopied += bytesRead
                            progressCallback?.invoke(bytesCopied.toFloat() / totalBytes.toFloat())
                        }
                    }
                }
            }
            
            android.util.Log.d("ObbDatabaseHelper", "Database extracted successfully from ${obbFile.absolutePath} to ${targetDb.absolutePath}")
            true
        } catch (e: Exception) {
            android.util.Log.e("ObbDatabaseHelper", "Failed to extract database", e)
            false
        }
    }
    
    private fun extractFromZip(zipFile: File, targetDb: File, progressCallback: ((Float) -> Unit)?) {
        ZipFile(zipFile).use { zip ->
            // Find the database entry in the ZIP
            val entry = zip.getEntry(DB_NAME) 
                ?: zip.getEntry("perseus_texts.db")
                ?: zip.entries().asSequence().firstOrNull { it.name.endsWith(".db") }
                ?: throw Exception("No database file found in ZIP")
            
            val totalBytes = entry.size
            var bytesCopied = 0L
            
            zip.getInputStream(entry).buffered(1024 * 1024).use { input ->
                FileOutputStream(targetDb).buffered(1024 * 1024).use { output ->
                    val buffer = ByteArray(1024 * 1024) // 1MB buffer
                    var bytesRead: Int
                    
                    while (input.read(buffer).also { bytesRead = it } != -1) {
                        output.write(buffer, 0, bytesRead)
                        bytesCopied += bytesRead
                        progressCallback?.invoke(bytesCopied.toFloat() / totalBytes.toFloat())
                    }
                }
            }
        }
    }
    
    /**
     * Get the expected OBB file size for validation
     */
    fun getExpectedObbSize(): Long {
        // This should match your actual OBB file size
        return 66 * 1024 * 1024 // 66MB in bytes
    }
    
    /**
     * Validate OBB file
     */
    fun validateObbFile(): Boolean {
        val obbFile = getObbDatabasePath() ?: return false
        
        // Basic validation - check if it's a valid SQLite database
        return try {
            // Check file size (should be > 100MB for our database)
            if (obbFile.length() < 100 * 1024 * 1024) {
                android.util.Log.e("ObbDatabaseHelper", "OBB file too small: ${obbFile.length()} bytes")
                return false
            }
            
            // Try to open as SQLite database to validate
            SQLiteDatabase.openDatabase(obbFile.absolutePath, null, SQLiteDatabase.OPEN_READONLY).use { db ->
                // Check if key tables exist
                val cursor = db.rawQuery("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('authors', 'works', 'books', 'text_lines', 'translation_segments')", null)
                val tableCount = cursor.count
                cursor.close()
                
                val isValid = tableCount == 5
                android.util.Log.d("ObbDatabaseHelper", "OBB validation: found $tableCount/5 required tables")
                isValid
            }
        } catch (e: Exception) {
            android.util.Log.e("ObbDatabaseHelper", "OBB validation failed", e)
            false
        }
    }
    
    /**
     * Get OBB download directory path for user instructions
     */
    fun getObbDirectoryPath(): String {
        return "/sdcard/Android/obb/${context.packageName}"
    }
}