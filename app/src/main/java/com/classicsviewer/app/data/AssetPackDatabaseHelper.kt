package com.classicsviewer.app.data

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.zip.ZipInputStream

/**
 * Helper class for handling database extraction from APK assets
 * (Previously handled Play Asset Packs, now simplified to use APK assets directly)
 */
class AssetPackDatabaseHelper(private val context: Context) {
    
    companion object {
        private const val DB_NAME = "perseus_texts.db"
        private const val COMPRESSED_DB_NAME = "perseus_texts.db.zip"
    }
    
    /**
     * Check if asset pack is installed and ready
     * Now always returns true since database is in APK assets
     */
    fun isAssetPackReady(): Boolean {
        // Database is now included directly in APK assets
        return try {
            context.assets.open(COMPRESSED_DB_NAME).use { 
                android.util.Log.d("AssetPackDatabaseHelper", "Database found in APK assets")
                true 
            }
        } catch (e: Exception) {
            android.util.Log.e("AssetPackDatabaseHelper", "Database not found in APK assets: ${e.message}")
            false
        }
    }
    
    /**
     * Copy database from asset pack to internal storage
     * Handles both compressed and uncompressed databases
     */
    suspend fun copyDatabaseFromAssetPack(progressCallback: ((Float) -> Unit)? = null): Boolean = withContext(Dispatchers.IO) {
        try {
            android.util.Log.d("AssetPackDatabaseHelper", "Extracting database from APK assets...")
            
            // Database is always in APK assets now
            
            val targetDb = context.getDatabasePath(DB_NAME)
            targetDb.parentFile?.mkdirs()
            
            android.util.Log.d("AssetPackDatabaseHelper", "Extracting database from APK assets to ${targetDb.absolutePath}")
            
            // Extract from APK assets (database is now always included)
            context.assets.open(COMPRESSED_DB_NAME).buffered(8 * 1024).use { fileInput ->
                ZipInputStream(fileInput).use { zipInput ->
                    val entry = zipInput.nextEntry
                    if (entry != null && entry.name == DB_NAME) {
                        val totalBytes = entry.size
                        var bytesCopied = 0L
                        
                        targetDb.outputStream().buffered(1024 * 1024).use { output ->
                            val buffer = ByteArray(1024 * 1024) // 1MB buffer
                            var bytesRead: Int
                            
                            while (zipInput.read(buffer).also { bytesRead = it } != -1) {
                                output.write(buffer, 0, bytesRead)
                                bytesCopied += bytesRead
                                if (totalBytes > 0) {
                                    progressCallback?.invoke(bytesCopied.toFloat() / totalBytes.toFloat())
                                }
                            }
                        }
                        android.util.Log.d("AssetPackDatabaseHelper", "Database extracted successfully from APK assets")
                    } else {
                        android.util.Log.e("AssetPackDatabaseHelper", "No valid database entry found in ZIP")
                        return@withContext false
                    }
                }
            }
            
            true
        } catch (e: Exception) {
            android.util.Log.e("AssetPackDatabaseHelper", "Failed to process database", e)
            false
        }
    }
}