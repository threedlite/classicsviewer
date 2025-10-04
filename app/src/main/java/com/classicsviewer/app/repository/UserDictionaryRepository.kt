package com.classicsviewer.app.repository

import android.content.Context
import android.net.Uri
import android.util.Log
import com.classicsviewer.app.database.UserDatabase
import com.classicsviewer.app.database.entities.UserDictionaryLemmaEntity
import com.classicsviewer.app.database.entities.UserLemmaMappingEntity
import com.classicsviewer.app.database.entities.UserDictionaryPackageEntity
import com.classicsviewer.app.database.entities.NormalizationPatternEntity
import com.classicsviewer.app.utils.DictionaryImportData
import com.classicsviewer.app.utils.DictionaryZipParser
import com.classicsviewer.app.utils.GreekNormalizer
import com.classicsviewer.app.utils.PatternBasedNormalizer
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.util.concurrent.ConcurrentHashMap

class UserDictionaryRepository(private val context: Context) {
    private val userDatabase = UserDatabase.getInstance(context)
    private val dictionaryDao = userDatabase.userDictionaryDao()
    private val mappingDao = userDatabase.userLemmaMappingDao()
    private val packageDao = userDatabase.userDictionaryPackageDao()
    private val normalizationDao = userDatabase.normalizationPatternDao()
    private val zipParser = DictionaryZipParser()

    // Normalization pattern cache (to avoid repeated DB queries)
    private val normalizationCache = ConcurrentHashMap<String, List<NormalizationPatternEntity>>()

    companion object {
        private const val TAG = "UserDictionaryRepo"
        private const val BATCH_SIZE = 100
    }
    
    private fun getFileName(uri: Uri): String? {
        var fileName: String? = null
        
        // Try to get the display name from the content resolver
        context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val nameIndex = cursor.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
            if (nameIndex >= 0 && cursor.moveToFirst()) {
                fileName = cursor.getString(nameIndex)
            }
        }
        
        // Fallback to getting the last segment of the URI path
        if (fileName == null) {
            fileName = uri.lastPathSegment
        }
        
        return fileName
    }
    
    // Import operations
    suspend fun importDictionary(
        uri: Uri,
        progressCallback: ((Int, String) -> Unit)? = null
    ): ImportResult = withContext(Dispatchers.IO) {
        try {
            Log.d(TAG, "Starting dictionary import from URI: $uri")
            
            // Get the original filename from the URI
            val originalFileName = getFileName(uri) ?: "imported_dictionary.zip"
            Log.d(TAG, "Original filename: $originalFileName")
            
            progressCallback?.invoke(5, "Opening file...")
            
            // Copy file to temp location
            val tempFile = File(context.cacheDir, "temp_dictionary.zip")
            context.contentResolver.openInputStream(uri)?.use { input ->
                FileOutputStream(tempFile).use { output ->
                    input.copyTo(output)
                }
            } ?: throw IllegalArgumentException("Cannot open file from URI")
            
            progressCallback?.invoke(10, "Creating dictionary package...")
            
            // Create a new package for this import
            val packageName = originalFileName.removeSuffix(".zip")
            val packageEntity = UserDictionaryPackageEntity(
                packageName = packageName,
                fileName = originalFileName,
                description = "Imported from $originalFileName",
                importDate = System.currentTimeMillis(),
                isActive = false // Will be activated after successful import
            )
            val packageId = packageDao.insertPackage(packageEntity)
            
            progressCallback?.invoke(15, "Processing dictionary entries...")
            
            // Parse the ZIP file with streaming for morphology
            var mappingCount = 0
            var totalEstimated = 2000000 // Estimate for progress calculation
            val importData = zipParser.parseZipFile(tempFile, originalFileName, packageId) { batch ->
                // This callback is called for each batch of morphology mappings
                mappingDao.insertMappings(batch)
                mappingCount += batch.size
                
                // Calculate progress (15-90% range for morphology import)
                val morphProgress = (mappingCount.toFloat() / totalEstimated * 75).toInt().coerceAtMost(75)
                val totalProgress = 15 + morphProgress
                
                progressCallback?.invoke(totalProgress, "Importing morphology: ${mappingCount / 1000}k entries...")
                Log.d(TAG, "Imported batch of ${batch.size} mappings, total: $mappingCount")
            }
            
            progressCallback?.invoke(92, "Importing dictionary definitions...")
            
            // Import lemmas in batches (these are smaller, so no streaming needed)
            var lemmaCount = 0
            importData.lemmas.chunked(BATCH_SIZE).forEach { batch ->
                dictionaryDao.insertLemmas(batch)
                lemmaCount += batch.size
                val lemmaProgress = (lemmaCount.toFloat() / importData.lemmas.size * 5).toInt()
                progressCallback?.invoke(92 + lemmaProgress, "Importing definitions: ${lemmaCount} / ${importData.lemmas.size}")
            }

            // Import normalization patterns (filter out Greek/Latin)
            if (importData.normalizationPatterns.isNotEmpty()) {
                val filteredPatterns = importData.normalizationPatterns.filter {
                    it.language != "greek" && it.language != "latin"
                }

                if (filteredPatterns.isNotEmpty()) {
                    normalizationDao.insertAll(filteredPatterns)
                    Log.d(TAG, "Inserted ${filteredPatterns.size} normalization patterns")
                }

                if (filteredPatterns.size < importData.normalizationPatterns.size) {
                    Log.w(TAG, "Skipped ${importData.normalizationPatterns.size - filteredPatterns.size} Greek/Latin patterns (use existing normalization)")
                }
            }

            // Clean up temp file
            tempFile.delete()

            progressCallback?.invoke(98, "Finalizing import...")
            
            // Update package statistics
            val greekLemmaCount = importData.lemmas.count { it.language == "greek" }
            val latinLemmaCount = importData.lemmas.count { it.language == "latin" }
            packageDao.updatePackageStats(
                packageId = packageId,
                totalLemmas = importData.lemmas.size,
                totalMappings = mappingCount,
                greekLemmas = greekLemmaCount,
                latinLemmas = latinLemmaCount
            )
            
            // Activate this package and deactivate others
            packageDao.setActivePackage(packageId)
            
            // Get counts for result
            val finalLemmaCount = importData.lemmas.size
            // mappingCount already tracked during streaming
            
            progressCallback?.invoke(100, "Import complete!")
            
            Log.d(TAG, "Import complete: $finalLemmaCount lemmas, $mappingCount mappings")
            Log.d(TAG, "UserDatabase instance used for import: ${userDatabase.hashCode()}")
            
            // Double check Latin entries specifically
            val latinCount = dictionaryDao.getLemmaCount("latin")
            Log.d(TAG, "Latin lemmas after import: $latinCount")
            
            ImportResult(
                success = true,
                lemmaCount = finalLemmaCount,
                mappingCount = mappingCount,
                warnings = importData.orphanedMappings,
                errors = importData.errors
            )
        } catch (e: Exception) {
            Log.e(TAG, "Import failed", e)
            ImportResult(
                success = false,
                errors = listOf(e.message ?: "Unknown error during import")
            )
        }
    }
    
    suspend fun clearAllData() = withContext(Dispatchers.IO) {
        Log.d(TAG, "Clearing all user dictionary data")
        dictionaryDao.deleteAllLemmas()
        mappingDao.deleteAllMappings()
        normalizationDao.deleteAll()  // Also clear normalization patterns

        // Clear normalization caches
        normalizationCache.clear()
        PatternBasedNormalizer.clearCache()

        // Note: App will be restarted after this to clear all in-memory caches
        // Note: We don't delete packages, they remain for switching
    }
    
    suspend fun deletePackage(packageId: Long) = withContext(Dispatchers.IO) {
        // Delete all data associated with this package
        dictionaryDao.deleteLemmasByPackageId(packageId)
        mappingDao.deleteMappingsByPackageId(packageId)
        normalizationDao.deleteByPackageId(packageId)
        packageDao.deletePackageById(packageId)

        // Clear normalization caches
        normalizationCache.clear()
        PatternBasedNormalizer.clearCache()
    }
    
    suspend fun setActivePackage(packageId: Long) = withContext(Dispatchers.IO) {
        packageDao.setActivePackage(packageId)
    }
    
    fun getAllPackages() = packageDao.getAllPackages()
    
    suspend fun getActivePackage() = withContext(Dispatchers.IO) {
        packageDao.getActivePackage()
    }
    
    // Query operations
    suspend fun getCurrentDictionaryInfo(): DictionaryInfo? = withContext(Dispatchers.IO) {
        val fileName = dictionaryDao.getCurrentDictionaryFileName()
        if (fileName != null) {
            val greekLemmas = dictionaryDao.getLemmaCount("greek")
            val latinLemmas = dictionaryDao.getLemmaCount("latin")
            val greekMappings = mappingDao.getMappingCount("greek")
            val latinMappings = mappingDao.getMappingCount("latin")
            
            DictionaryInfo(
                fileName = fileName,
                greekLemmaCount = greekLemmas,
                latinLemmaCount = latinLemmas,
                greekMappingCount = greekMappings,
                latinMappingCount = latinMappings,
                totalLemmaCount = greekLemmas + latinLemmas,
                totalMappingCount = greekMappings + latinMappings
            )
        } else {
            null
        }
    }
    
    suspend fun getEntriesForLemma(
        lemma: String,
        language: String
    ): List<UserDictionaryLemmaEntity> = withContext(Dispatchers.IO) {
        val normalized = normalizeText(lemma, language) ?: lemma.lowercase()
        dictionaryDao.getEntriesForLemma(lemma, normalized, language)
    }
    
    suspend fun getMappingForWord(
        word: String,
        language: String
    ): UserLemmaMappingEntity? = withContext(Dispatchers.IO) {
        val normalized = normalizeText(word, language) ?: word.lowercase()
        mappingDao.getMappingForWord(word, normalized, language)
    }
    
    fun getAllEntries(): Flow<List<UserDictionaryLemmaEntity>> = dictionaryDao.getAllEntries()
    
    fun getAllMappings(): Flow<List<UserLemmaMappingEntity>> = mappingDao.getAllMappings()
    
    // Data classes for results
    data class ImportResult(
        val success: Boolean,
        val lemmaCount: Int = 0,
        val mappingCount: Int = 0,
        val warnings: List<String> = emptyList(),
        val errors: List<String> = emptyList()
    )
    
    data class DictionaryInfo(
        val fileName: String,
        val greekLemmaCount: Int,
        val latinLemmaCount: Int,
        val greekMappingCount: Int,
        val latinMappingCount: Int,
        val totalLemmaCount: Int,
        val totalMappingCount: Int
    )

    // Normalization pattern methods

    /**
     * Get normalization patterns for a language.
     * Returns empty list for Greek and Latin (they use existing normalizers).
     */
    suspend fun getNormalizationPatterns(language: String): List<NormalizationPatternEntity> {
        // Greek and Latin use existing normalizers - return empty list
        if (language == "greek" || language == "latin") {
            return emptyList()
        }
        return normalizationDao.getPatternsForLanguage(language)
    }

    /**
     * Check if normalization patterns exist for a language.
     * Always returns false for Greek and Latin.
     */
    suspend fun hasNormalizationPatterns(language: String): Boolean {
        if (language == "greek" || language == "latin") {
            return false  // Use existing normalizers
        }
        return normalizationDao.countPatternsForLanguage(language) > 0
    }

    /**
     * Normalize text for any language using the appropriate normalizer.
     * - Greek: Uses GreekNormalizer (hardcoded)
     * - Latin: No normalization (returns null)
     * - Other: Uses PatternBasedNormalizer with database patterns
     */
    suspend fun normalizeText(text: String, language: String): String? {
        return when (language) {
            "greek" -> {
                // Use existing Greek normalizer
                GreekNormalizer.normalize(text)
            }
            "latin" -> {
                // No Latin normalization currently
                null
            }
            else -> {
                // Use cached patterns for non-Greek/Latin languages
                val patterns = normalizationCache.getOrPut(language) {
                    getNormalizationPatterns(language)
                }
                if (patterns.isNotEmpty()) {
                    PatternBasedNormalizer.normalize(text, language, patterns)
                } else {
                    null
                }
            }
        }
    }
}