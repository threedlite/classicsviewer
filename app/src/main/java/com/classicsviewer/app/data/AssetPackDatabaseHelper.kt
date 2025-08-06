package com.classicsviewer.app.data

import android.content.Context
import com.google.android.play.core.assetpacks.AssetPackManager
import com.google.android.play.core.assetpacks.AssetPackManagerFactory
import com.google.android.play.core.assetpacks.AssetPackState
import com.google.android.play.core.assetpacks.AssetPackStates
import com.google.android.play.core.assetpacks.model.AssetPackStatus
import com.google.android.play.core.ktx.requestPackStates
import com.google.android.play.core.ktx.requestFetch
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.util.zip.ZipInputStream

/**
 * Helper class for handling database stored in Play Asset Packs
 */
class AssetPackDatabaseHelper(private val context: Context) {
    
    companion object {
        private const val ASSET_PACK_NAME = "perseus_database"
        private const val DB_NAME = "perseus_texts.db"
        private const val COMPRESSED_DB_NAME = "perseus_texts.db.zip"
    }
    
    private val assetPackManager: AssetPackManager = AssetPackManagerFactory.getInstance(context).also {
        android.util.Log.d("AssetPackDatabaseHelper", "AssetPackManager created for context: ${context.packageName}")
    }
    
    /**
     * Check if asset pack is installed and ready
     */
    fun isAssetPackReady(): Boolean {
        val location = assetPackManager.getPackLocation(ASSET_PACK_NAME)
        android.util.Log.d("AssetPackDatabaseHelper", "Checking asset pack ready: $ASSET_PACK_NAME, location: ${location?.path() ?: "null"}")
        
        // For local testing with bundletool, asset packs might not be accessible via AssetPackManager
        // Check if we have a debug build with database in assets
        if (location == null && isLocalTesting()) {
            return hasDebugDatabase()
        }
        
        return location != null
    }
    
    private fun isLocalTesting(): Boolean {
        // Simple heuristic: debug builds are likely local testing
        return context.packageName.endsWith(".debug")
    }
    
    private fun hasDebugDatabase(): Boolean {
        return try {
            context.assets.open(COMPRESSED_DB_NAME).use { 
                android.util.Log.d("AssetPackDatabaseHelper", "Found database in debug APK assets for local testing")
                true 
            }
        } catch (e: Exception) {
            android.util.Log.d("AssetPackDatabaseHelper", "Database not found in debug APK assets: ${e.message}")
            false
        }
    }
    
    /**
     * Get the path to the database file in the asset pack
     * Checks for both compressed and uncompressed versions
     */
    fun getAssetPackDatabasePath(): File? {
        val location = assetPackManager.getPackLocation(ASSET_PACK_NAME)
        if (location == null) {
            // For local testing, return a special marker that indicates we should use assets
            if (isLocalTesting() && hasDebugDatabase()) {
                android.util.Log.d("AssetPackDatabaseHelper", "Using debug assets for database")
                // Return a dummy file to indicate we should use assets
                return File("assets", COMPRESSED_DB_NAME)
            }
            android.util.Log.e("AssetPackDatabaseHelper", "Asset pack location is null for pack: $ASSET_PACK_NAME")
            return null
        }
        android.util.Log.d("AssetPackDatabaseHelper", "Asset pack location: ${location.path()}")
        android.util.Log.d("AssetPackDatabaseHelper", "Asset pack assets path: ${location.assetsPath()}")
        
        // Check for compressed version first
        val compressedDbPath = File(location.assetsPath(), COMPRESSED_DB_NAME)
        if (compressedDbPath.exists()) {
            android.util.Log.d("AssetPackDatabaseHelper", "Found compressed database: ${compressedDbPath.absolutePath}")
            return compressedDbPath
        }
        
        // Fall back to uncompressed
        val dbPath = File(location.assetsPath(), DB_NAME)
        android.util.Log.d("AssetPackDatabaseHelper", "Database path: ${dbPath.absolutePath}, exists: ${dbPath.exists()}")
        return dbPath
    }
    
    /**
     * Copy database from asset pack to internal storage
     * Handles both compressed and uncompressed databases
     */
    suspend fun copyDatabaseFromAssetPack(progressCallback: ((Float) -> Unit)? = null): Boolean = withContext(Dispatchers.IO) {
        try {
            val assetDbPath = getAssetPackDatabasePath() ?: run {
                android.util.Log.e("AssetPackDatabaseHelper", "Asset pack not found or not ready")
                return@withContext false
            }
            
            val targetDb = context.getDatabasePath(DB_NAME)
            targetDb.parentFile?.mkdirs()
            
            android.util.Log.d("AssetPackDatabaseHelper", "Processing database from ${assetDbPath.absolutePath} to ${targetDb.absolutePath}")
            
            // Check if we're using debug assets
            if (assetDbPath.parent == "assets" && isLocalTesting()) {
                // Extract from APK assets for local testing
                android.util.Log.d("AssetPackDatabaseHelper", "Extracting database from debug APK assets...")
                
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
                            android.util.Log.d("AssetPackDatabaseHelper", "Database extracted from debug assets successfully")
                        } else {
                            android.util.Log.e("AssetPackDatabaseHelper", "No valid database entry found in debug assets ZIP")
                            return@withContext false
                        }
                    }
                }
            } else if (assetDbPath.name == COMPRESSED_DB_NAME) {
                // Decompress from ZIP file
                android.util.Log.d("AssetPackDatabaseHelper", "Decompressing database from asset pack...")
                
                assetDbPath.inputStream().buffered(8 * 1024).use { fileInput ->
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
                            android.util.Log.d("AssetPackDatabaseHelper", "Database decompressed successfully")
                        } else {
                            android.util.Log.e("AssetPackDatabaseHelper", "No valid database entry found in ZIP")
                            return@withContext false
                        }
                    }
                }
            } else {
                // Direct copy for uncompressed
                android.util.Log.d("AssetPackDatabaseHelper", "Copying uncompressed database...")
                
                var bytesCopied = 0L
                val totalBytes = assetDbPath.length()
                
                assetDbPath.inputStream().buffered(1024 * 1024).use { input ->
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
                android.util.Log.d("AssetPackDatabaseHelper", "Database copied successfully")
            }
            
            true
        } catch (e: Exception) {
            android.util.Log.e("AssetPackDatabaseHelper", "Failed to process database", e)
            false
        }
    }
    
    /**
     * Get asset pack size for display
     */
    fun getAssetPackSize(): Long {
        val location = getAssetPackDatabasePath()
        return location?.length() ?: 0L
    }
    
    /**
     * Request fast-follow pack download (needed for local testing)
     * Returns the pack status
     */
    suspend fun requestPackIfNeeded(): Int = withContext(Dispatchers.IO) {
        try {
            val states = assetPackManager.requestPackStates(listOf(ASSET_PACK_NAME))
            val packState = states.packStates()[ASSET_PACK_NAME]
            
            android.util.Log.d("AssetPackDatabaseHelper", "Pack state: ${packState?.status()}")
            
            when (packState?.status()) {
                AssetPackStatus.COMPLETED -> {
                    android.util.Log.d("AssetPackDatabaseHelper", "Pack already available")
                    AssetPackStatus.COMPLETED
                }
                AssetPackStatus.UNKNOWN -> {
                    android.util.Log.d("AssetPackDatabaseHelper", "Requesting pack download")
                    assetPackManager.requestFetch(listOf(ASSET_PACK_NAME))
                    AssetPackStatus.PENDING
                }
                else -> packState?.status() ?: AssetPackStatus.UNKNOWN
            }
        } catch (e: Exception) {
            android.util.Log.e("AssetPackDatabaseHelper", "Failed to get pack states", e)
            AssetPackStatus.UNKNOWN
        }
    }
    
    /**
     * Monitor pack download progress
     */
    fun registerListener(listener: (AssetPackState) -> Unit) {
        assetPackManager.registerListener { packState ->
            if (packState.name() == ASSET_PACK_NAME) {
                android.util.Log.d("AssetPackDatabaseHelper", "Pack status update: ${packState.status()}, ${packState.bytesDownloaded()}/${packState.totalBytesToDownload()}")
                listener(packState)
            }
        }
    }
}