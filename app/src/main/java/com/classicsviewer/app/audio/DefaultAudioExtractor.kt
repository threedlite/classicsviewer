package com.classicsviewer.app.audio

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.util.zip.ZipInputStream

/**
 * Helper class for extracting and managing the default bundled audio package
 */
class DefaultAudioExtractor(private val context: Context) {
    
    companion object {
        private const val TAG = "DefaultAudioExtractor"
        private const val DEFAULT_AUDIO_ZIP = "homer_iliad_chamberlain_audio_7.zip"
        private const val DEFAULT_PACKAGE_ID = -1L // Special ID for bundled package
        private const val DEFAULT_PACKAGE_NAME = "Homer - Iliad (Chamberlain) [Bundled]"
        private const val AUDIO_DIR = "audio"
    }
    
    private val audioDbHelper = AudioDatabaseHelper(context)
    
    /**
     * Check if default audio needs extraction
     */
    suspend fun needsExtraction(): Boolean = withContext(Dispatchers.IO) {
        try {
            // Check if we have any audio packages
            val packages = audioDbHelper.getAllPackages()
            if (packages.isEmpty()) {
                Log.d(TAG, "No audio packages found, need to extract default")
                return@withContext true
            }
            
            // Check if default package exists
            val hasDefault = packages.any { it.id == DEFAULT_PACKAGE_ID }
            if (!hasDefault) {
                Log.d(TAG, "Default package not found, need to extract")
                return@withContext true
            }
            
            // Check if the default package files still exist
            val defaultPackage = packages.find { it.id == DEFAULT_PACKAGE_ID }
            if (defaultPackage != null) {
                val packageDir = getPackageDirectory()
                if (!packageDir.exists()) {
                    Log.d(TAG, "Default package directory missing, need to re-extract")
                    return@withContext true
                }
            }
            
            false
        } catch (e: Exception) {
            Log.e(TAG, "Error checking extraction status", e)
            true
        }
    }
    
    /**
     * Extract default audio package from APK assets
     */
    suspend fun extractDefaultAudio(progressCallback: ((Float) -> Unit)? = null): Boolean = withContext(Dispatchers.IO) {
        try {
            Log.d(TAG, "Starting extraction of default audio package")
            
            // Ensure audio tables exist
            audioDbHelper.ensureTablesExist()
            
            // Check if asset exists
            if (!hasDefaultAudioInAssets()) {
                Log.e(TAG, "Default audio not found in assets")
                return@withContext false
            }
            
            // Create package directory
            val packageDir = getPackageDirectory()
            packageDir.mkdirs()
            
            // Extract audio files from ZIP and build metadata
            val audioFiles = mutableListOf<JSONObject>()
            var fileCount = 0
            
            context.assets.open(DEFAULT_AUDIO_ZIP).use { assetInput ->
                ZipInputStream(assetInput.buffered(8 * 1024)).use { zipInput ->
                    var entry = zipInput.nextEntry
                    val totalEntries = 100 // Approximate for progress
                    var processedEntries = 0
                    
                    while (entry != null) {
                        val entryName = entry.name
                        
                        when {
                            entryName.endsWith(".mp4") || entryName.endsWith(".mp3") -> {
                                // Extract audio file
                                val audioFile = File(packageDir, entryName)
                                audioFile.parentFile?.mkdirs()
                                
                                audioFile.outputStream().use { output ->
                                    zipInput.copyTo(output)
                                }
                                fileCount++
                                Log.d(TAG, "Extracted: $entryName")
                                
                                // Parse file path to extract metadata
                                // Expected format: Homer/Iliad/book_X/line_Y.mp4
                                val parts = entryName.split("/")
                                if (parts.size >= 4) {
                                    val author = parts[0]
                                    val work = parts[1] 
                                    val bookStr = parts[2].replace("book_", "")
                                    val lineStr = parts[3].substringBefore(".").replace("line_", "")
                                    
                                    try {
                                        val book = bookStr.toInt()
                                        val line = lineStr.toInt()
                                        
                                        val mapping = JSONObject().apply {
                                            put("author", author)
                                            put("work", work)
                                            put("book", book)
                                            put("line", line)
                                            put("file_path", entryName)
                                        }
                                        audioFiles.add(mapping)
                                    } catch (e: NumberFormatException) {
                                        Log.w(TAG, "Could not parse book/line from: $entryName")
                                    }
                                }
                            }
                        }
                        
                        processedEntries++
                        progressCallback?.invoke(processedEntries.toFloat() / totalEntries)
                        
                        zipInput.closeEntry()
                        entry = zipInput.nextEntry
                    }
                }
            }
            
            Log.d(TAG, "Extracted $fileCount audio files")
            
            // Build metadata from extracted files
            val metadata = JSONObject().apply {
                put("total_files", fileCount)
                put("file_size", 500000) // Approximate
                put("mappings", org.json.JSONArray(audioFiles))
            }
            
            // Import metadata into database
            importMetadataToDatabase(metadata, packageDir)
            
            Log.d(TAG, "Default audio extraction completed successfully")
            true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to extract default audio", e)
            false
        }
    }
    
    /**
     * Check if default audio exists in APK assets
     */
    fun hasDefaultAudioInAssets(): Boolean {
        return try {
            context.assets.open(DEFAULT_AUDIO_ZIP).use {
                true
            }
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Get the directory for the default audio package
     */
    private fun getPackageDirectory(): File {
        val audioDir = File(context.filesDir, AUDIO_DIR)
        return File(audioDir, "default_bundled_audio")
    }
    
    /**
     * Import metadata to database
     */
    private suspend fun importMetadataToDatabase(metadata: JSONObject, packageDir: File) = withContext(Dispatchers.IO) {
        try {
            Log.d(TAG, "Importing metadata to database")
            
            // Insert default package data using helper method
            val success = audioDbHelper.insertBundledPackage(
                DEFAULT_PACKAGE_ID,
                DEFAULT_PACKAGE_NAME,
                metadata
            )
            
            if (success) {
                Log.d(TAG, "Successfully imported default audio package to database")
            } else {
                Log.e(TAG, "Failed to import default audio package")
                throw Exception("Failed to import default audio package")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error importing metadata to database", e)
            throw e
        }
    }
    
    /**
     * Check if default audio is currently active
     */
    suspend fun isDefaultAudioActive(): Boolean = withContext(Dispatchers.IO) {
        try {
            val packages = audioDbHelper.getAllPackages()
            val defaultPackage = packages.find { it.id == DEFAULT_PACKAGE_ID }
            defaultPackage?.isActive == true
        } catch (e: Exception) {
            Log.e(TAG, "Error checking default audio status", e)
            false
        }
    }
}