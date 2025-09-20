package com.classicsviewer.app.audio

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.net.Uri
import android.util.Log
import androidx.work.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipInputStream

class AudioImportWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {
    
    companion object {
        private const val TAG = "AudioImportWorker"
        const val KEY_URI = "uri_string"
        const val KEY_STATUS = "status"
        const val KEY_DETAILS = "details"
        const val KEY_BOOK = "book"
        const val KEY_FILES_IMPORTED = "files_imported"
        const val KEY_ERROR = "error"
        
        fun createWorkRequest(uri: Uri): OneTimeWorkRequest {
            val inputData = workDataOf(
                KEY_URI to uri.toString()
            )
            
            return OneTimeWorkRequestBuilder<AudioImportWorker>()
                .setInputData(inputData)
                .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
                .build()
        }
    }
    
    private lateinit var audioDbHelper: AudioDatabaseHelper
    private lateinit var audioRepository: AudioRepository
    
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            audioDbHelper = AudioDatabaseHelper(applicationContext)
            audioRepository = AudioRepository(applicationContext)
            
            val uriString = inputData.getString(KEY_URI)
                ?: return@withContext Result.failure(
                    workDataOf(KEY_ERROR to "No URI provided")
                )
            
            val uri = Uri.parse(uriString)
            
            Log.d(TAG, "Starting audio import from: $uri")
            
            // Ensure audio tables exist
            audioDbHelper.ensureTablesExist()
            
            // Get filename from URI
            val filename = getFileName(uri)
            val packageName = filename.replace(".zip", "")
            
            // Check if package already exists
            val existingPackages = audioRepository.getAllPackages()
            if (existingPackages.any { it.packageName == packageName }) {
                return@withContext Result.failure(
                    workDataOf(
                        KEY_ERROR to "Package '$packageName' already exists"
                    )
                )
            }
            
            setProgressAsync(
                workDataOf(
                    KEY_STATUS to "Analyzing package...",
                    KEY_DETAILS to filename
                )
            )
            
            // Create package directory
            val packageId = System.currentTimeMillis() // Use timestamp as temporary ID
            val packageDir = audioRepository.getPackageDirectory(packageId, packageName)
            packageDir.mkdirs()
            
            // First, count total entries for progress tracking
            setProgressAsync(
                workDataOf(
                    KEY_STATUS to "Counting files...",
                    KEY_DETAILS to "Please wait..."
                )
            )
            
            var totalEntries = 0
            applicationContext.contentResolver.openInputStream(uri)?.use { inputStream ->
                try {
                    ZipInputStream(inputStream).use { zis ->
                        var entry: ZipEntry? = zis.nextEntry
                        while (entry != null) {
                            if (!entry.isDirectory && entry.name.endsWith(".mp4")) {
                                totalEntries++
                            }
                            zis.closeEntry()
                            entry = zis.nextEntry
                        }
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Error reading ZIP file", e)
                    return@withContext Result.failure(
                        workDataOf(
                            KEY_ERROR to "Invalid or corrupted ZIP file: ${e.message}"
                        )
                    )
                }
            } ?: return@withContext Result.failure(
                workDataOf(KEY_ERROR to "Cannot read selected file")
            )
            
            Log.d(TAG, "Found $totalEntries audio files to import")
            
            // Check if ZIP contains any audio files
            if (totalEntries == 0) {
                return@withContext Result.failure(
                    workDataOf(
                        KEY_ERROR to "No audio files found in ZIP (expected .mp4 files)"
                    )
                )
            }
            
            setProgressAsync(
                workDataOf(
                    KEY_STATUS to "Starting import",
                    KEY_DETAILS to "$totalEntries files to process"
                )
            )
            
            // Extract ZIP and collect file info
            val audioMappings = mutableListOf<AudioMappingEntry>()
            var totalSize = 0L
            var fileCount = 0
            var skippedCount = 0
            var currentBook = -1
            var filesProcessed = 0
            
            applicationContext.contentResolver.openInputStream(uri)?.use { inputStream ->
                try {
                    ZipInputStream(inputStream).use { zis ->
                        var zipEntry: ZipEntry? = zis.nextEntry
                        
                        while (zipEntry != null) {
                            val currentEntry = zipEntry // Capture current value for use in closure
                            
                            if (!currentEntry.isDirectory && currentEntry.name.endsWith(".mp4")) {
                                val file = File(packageDir, currentEntry.name)
                                file.parentFile?.mkdirs()
                                
                                try {
                                    FileOutputStream(file).use { fos ->
                                        zis.copyTo(fos)
                                    }
                                } catch (e: Exception) {
                                    Log.e(TAG, "Error extracting file: ${currentEntry.name}", e)
                                    // Continue with next file instead of failing completely
                                    skippedCount++
                                    zipEntry = zis.nextEntry
                                    continue
                                }
                                
                                filesProcessed++
                                
                                // Parse file path to extract metadata
                                val mapping = parseAudioFile(currentEntry.name)
                                if (mapping != null) {
                                    audioMappings.add(mapping)
                                    fileCount++
                                    totalSize += file.length()
                                
                                    // Update notification every 10 files or when book changes
                                    if (mapping.bookNumber != currentBook) {
                                        currentBook = mapping.bookNumber
                                    }
                                    
                                    if (filesProcessed % 10 == 0 || mapping.bookNumber != currentBook) {
                                        val percentage = (filesProcessed * 100) / totalEntries
                                        setProgressAsync(
                                            workDataOf(
                                                KEY_STATUS to "Importing files ($percentage%)",
                                                KEY_DETAILS to "Book $currentBook of 24",
                                                KEY_BOOK to currentBook
                                            )
                                        )
                                    }
                                } else {
                                    skippedCount++
                                    Log.w(TAG, "Skipped file (couldn't parse): ${currentEntry.name}")
                                }
                            }
                        
                        zis.closeEntry()
                        zipEntry = zis.nextEntry
                    }
                }
                } catch (e: Exception) {
                    Log.e(TAG, "Error extracting audio files", e)
                    return@withContext Result.failure(
                        workDataOf(
                            KEY_ERROR to "Failed to extract audio files: ${e.message}"
                        )
                    )
                }
            }
            
            // Validate that we successfully extracted some files
            if (fileCount == 0) {
                Log.e(TAG, "No valid audio files were extracted (parsed: 0, skipped: $skippedCount)")
                return@withContext Result.failure(
                    workDataOf(
                        KEY_ERROR to "No valid audio files could be imported. Files may be corrupted or in wrong format."
                    )
                )
            }
            
            setProgressAsync(
                workDataOf(
                    KEY_STATUS to "Saving to database",
                    KEY_DETAILS to "Almost done..."
                )
            )
            
            // Insert package into database
            val isFirstPackage = existingPackages.isEmpty()
            Log.d(TAG, "Inserting package: $packageName, isFirstPackage=$isFirstPackage, will be active=$isFirstPackage")
            val actualPackageId = insertPackage(
                packageName = packageName,
                zipFilename = filename,
                totalFiles = fileCount,
                fileSizeBytes = totalSize,
                isActive = isFirstPackage // Make active if first package
            )
            
            // Insert audio mappings
            insertAudioMappings(actualPackageId, audioMappings)
            
            // If this was the first package, rename the directory with actual ID
            if (actualPackageId != packageId) {
                val newPackageDir = audioRepository.getPackageDirectory(actualPackageId, packageName)
                packageDir.renameTo(newPackageDir)
            }
            
            Log.d(TAG, "Import complete: $fileCount files imported")
            
            Result.success(
                workDataOf(
                    KEY_STATUS to "Import complete",
                    KEY_DETAILS to "$fileCount files imported successfully",
                    KEY_FILES_IMPORTED to fileCount
                )
            )
            
        } catch (e: Exception) {
            Log.e(TAG, "Error importing audio package", e)
            return@withContext Result.failure(
                workDataOf(
                    KEY_ERROR to (e.message ?: "Unknown error")
                )
            )
        }
    }
    
    private fun parseAudioFile(path: String): AudioMappingEntry? {
        return try {
            // Handle both formats:
            // - Direct: Author/Work/book_N/line_X.{mp4|mid}
            // - Package: package_name/Author/Work/book_N/line_X.{mp4|mid}
            
            val parts = path.split("/")
            
            // Find where the Author/Work/book_N pattern starts
            var startIdx = 0
            for (i in 0 until parts.size - 2) {
                if (parts[i + 2].startsWith("book_")) {
                    startIdx = i
                    break
                }
            }
            
            if (parts.size >= startIdx + 4) {
                val author = parts[startIdx]
                val work = parts[startIdx + 1]
                val bookFolder = parts[startIdx + 2]
                val fileName = parts[startIdx + 3]
                
                // Extract book number from "book_N"
                val bookNumber = bookFolder.replace("book_", "").toIntOrNull() ?: 1
                
                // Extract line number from "line_X.ext"
                val lineNumber = fileName.substringAfter("line_")
                    .substringBefore(".")
                    .toIntOrNull() ?: return null
                
                val format = fileName.substringAfterLast(".")
                
                AudioMappingEntry(
                    authorName = author,
                    workTitle = work,
                    bookNumber = bookNumber,
                    lineNumber = lineNumber,
                    filePath = path,
                    fileFormat = format
                )
            } else null
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing audio file path: $path", e)
            null
        }
    }
    
    private fun insertPackage(
        packageName: String,
        zipFilename: String,
        totalFiles: Int,
        fileSizeBytes: Long,
        isActive: Boolean
    ): Long {
        val db = applicationContext.getDatabasePath("audio_data.db")
        val database = SQLiteDatabase.openDatabase(db.absolutePath, null, SQLiteDatabase.OPEN_READWRITE)
        
        val values = ContentValues().apply {
            put("package_name", packageName)
            put("zip_filename", zipFilename)
            put("total_files", totalFiles)
            put("file_size_bytes", fileSizeBytes)
            put("is_active", if (isActive) 1 else 0)
            put("import_date", System.currentTimeMillis())
        }
        
        val id = database.insert("audio_packages", null, values)
        database.close()
        return id
    }
    
    private fun insertAudioMappings(packageId: Long, mappings: List<AudioMappingEntry>) {
        val db = applicationContext.getDatabasePath("audio_data.db")
        val database = SQLiteDatabase.openDatabase(db.absolutePath, null, SQLiteDatabase.OPEN_READWRITE)
        
        database.beginTransaction()
        try {
            mappings.forEach { mapping ->
                val values = ContentValues().apply {
                    put("package_id", packageId)
                    put("author_name", mapping.authorName)
                    put("work_title", mapping.workTitle)
                    put("book_number", mapping.bookNumber)
                    put("line_number", mapping.lineNumber)
                    put("file_path", mapping.filePath)
                    put("file_format", mapping.fileFormat)
                    put("duration_ms", 0) // Will be updated when played
                    put("created_at", System.currentTimeMillis())
                }
                database.insert("audio_mappings", null, values)
            }
            database.setTransactionSuccessful()
        } finally {
            database.endTransaction()
            database.close()
        }
    }
    
    private fun getFileName(uri: Uri): String {
        var name = "audio_package.zip"
        applicationContext.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val nameIndex = cursor.getColumnIndex("_display_name")
            if (cursor.moveToFirst() && nameIndex >= 0) {
                name = cursor.getString(nameIndex)
            }
        }
        return name
    }
    
    data class AudioMappingEntry(
        val authorName: String,
        val workTitle: String,
        val bookNumber: Int,
        val lineNumber: Int,
        val filePath: String,
        val fileFormat: String
    )
}