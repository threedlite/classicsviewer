package com.classicsviewer.app.audio

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

class AudioRepository(private val context: Context) {
    companion object {
        private const val TAG = "AudioRepository"
        private const val AUDIO_DIR = "audio"
    }
    
    private val audioDbHelper = AudioDatabaseHelper(context)
    
    init {
        // Ensure audio tables exist when repository is created
        try {
            audioDbHelper.ensureTablesExist()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to create audio tables", e)
        }
    }
    
    suspend fun hasAudioData(): Boolean = withContext(Dispatchers.IO) {
        audioDbHelper.hasAudioData()
    }
    
    suspend fun getActivePackage(): AudioPackage? = withContext(Dispatchers.IO) {
        val packages = audioDbHelper.getAllPackages()
        packages.find { it.isActive }
    }
    
    suspend fun getAllPackages(): List<AudioPackage> = withContext(Dispatchers.IO) {
        audioDbHelper.getAllPackages()
    }
    
    suspend fun setActivePackage(packageId: Long): Boolean = withContext(Dispatchers.IO) {
        audioDbHelper.setActivePackage(packageId)
    }
    
    suspend fun getAudioForLine(
        authorName: String, 
        workTitle: String, 
        bookNumber: Int, 
        lineNumber: Int
    ): AudioMapping? = withContext(Dispatchers.IO) {
        audioDbHelper.getAudioForLine(authorName, workTitle, bookNumber, lineNumber)
    }
    
    suspend fun getAudioForLineRange(
        authorName: String, 
        workTitle: String, 
        bookNumber: Int, 
        startLine: Int, 
        endLine: Int
    ): List<AudioMapping> = withContext(Dispatchers.IO) {
        audioDbHelper.getAudioForLineRange(authorName, workTitle, bookNumber, startLine, endLine)
    }
    
    suspend fun deletePackage(packageId: Long): Boolean = withContext(Dispatchers.IO) {
        try {
            // Get package info to find directory
            val packages = audioDbHelper.getAllPackages()
            val packageToDelete = packages.find { it.id == packageId }
            
            if (packageToDelete != null) {
                // Delete audio files from storage
                val packageDir = getPackageDirectory(packageId, packageToDelete.packageName)
                if (packageDir.exists()) {
                    packageDir.deleteRecursively()
                    Log.d(TAG, "Deleted audio files for package: ${packageToDelete.packageName}")
                }
            }
            
            // Delete from database
            audioDbHelper.deletePackage(packageId)
        } catch (e: Exception) {
            Log.e(TAG, "Error deleting package", e)
            false
        }
    }
    
    fun getPackageDirectory(packageId: Long, packageName: String): File {
        val audioDir = File(context.filesDir, AUDIO_DIR)
        
        // Special handling for bundled package
        if (packageId == -1L) {
            return File(audioDir, "default_bundled_audio")
        }
        
        val safeName = packageName.replace(Regex("[^a-zA-Z0-9_-]"), "_")
        return File(audioDir, "package_${packageId}_$safeName")
    }
    
    fun getAudioFile(mapping: AudioMapping): File? {
        return try {
            // Get the active package to build correct path
            val activePackageId = audioDbHelper.getActivePackageId()
            if (activePackageId == null || activePackageId != mapping.packageId) {
                Log.w(TAG, "Audio file requested for inactive package")
                return null
            }
            
            val packages = audioDbHelper.getAllPackages()
            val activePackage = packages.find { it.id == activePackageId }
            if (activePackage == null) {
                Log.e(TAG, "Active package not found")
                return null
            }
            
            val packageDir = getPackageDirectory(activePackageId, activePackage.packageName)
            val audioFile = File(packageDir, mapping.filePath)
            
            if (audioFile.exists()) {
                audioFile
            } else {
                Log.e(TAG, "Audio file not found: ${audioFile.absolutePath}")
                null
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error getting audio file", e)
            null
        }
    }
    
    fun close() {
        audioDbHelper.close()
    }
}