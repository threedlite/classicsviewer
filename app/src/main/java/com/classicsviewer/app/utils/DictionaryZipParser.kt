package com.classicsviewer.app.utils

import android.util.Log
import com.classicsviewer.app.database.entities.UserDictionaryLemmaEntity
import com.classicsviewer.app.database.entities.UserLemmaMappingEntity
import com.classicsviewer.app.database.entities.NormalizationPatternEntity
import com.opencsv.CSVReaderBuilder
import java.io.File
import java.io.InputStreamReader
import java.util.zip.ZipFile

data class DictionaryImportData(
    var lemmas: List<UserDictionaryLemmaEntity> = emptyList(),
    var mappings: List<UserLemmaMappingEntity> = emptyList(),
    var normalizationPatterns: List<NormalizationPatternEntity> = emptyList(),
    val orphanedMappings: MutableList<String> = mutableListOf(),
    val errors: MutableList<String> = mutableListOf()
)

class DictionaryZipParser {
    companion object {
        private const val TAG = "DictionaryZipParser"
        private const val DICTIONARY_CSV = "dictionary.csv"
        private const val MORPHOLOGY_CSV = "morphology.csv"
        private const val NORMALIZATION_CSV = "normalization_rules.csv"

        // Safety limit to prevent malicious data
        private const val MAX_FIELD_LENGTH = 50000  // 50KB per field should be more than enough for any definition
    }
    
    suspend fun parseZipFile(zipFile: File): DictionaryImportData {
        return parseZipFile(zipFile, zipFile.name, 1L)
    }
    
    suspend fun parseZipFile(zipFile: File, originalFileName: String, packageId: Long): DictionaryImportData {
        return parseZipFile(zipFile, originalFileName, packageId, null)
    }
    
    suspend fun parseZipFile(
        zipFile: File, 
        originalFileName: String,
        packageId: Long,
        batchCallback: (suspend (List<UserLemmaMappingEntity>) -> Unit)?
    ): DictionaryImportData {
        val result = DictionaryImportData()
        val importDate = System.currentTimeMillis()
        val fileName = originalFileName
        
        // Validate file exists and is readable
        if (!zipFile.exists() || !zipFile.canRead()) {
            throw IllegalArgumentException("Cannot read ZIP file")
        }
        
        try {
            // Try to open as ZIP - will throw if corrupted
            val zip = try {
                ZipFile(zipFile)
            } catch (e: Exception) {
                throw IllegalArgumentException("Invalid or corrupted ZIP file: ${e.message}")
            }
            
            zip.use { zipArchive ->
                // STEP 1: Extract and parse normalization_rules.csv FIRST (OPTIONAL)
                // This must happen before dictionary parsing so patterns can be used for normalization
                val normalizationEntry = zipArchive.getEntry(NORMALIZATION_CSV)
                if (normalizationEntry != null) {
                    Log.d(TAG, "Found normalization_rules.csv in ZIP, parsing...")
                    zipArchive.getInputStream(normalizationEntry).use { stream ->
                        result.normalizationPatterns = parseNormalizationCSV(
                            InputStreamReader(stream, Charsets.UTF_8),
                            packageId
                        )
                    }
                    Log.d(TAG, "Parsed ${result.normalizationPatterns.size} normalization patterns")
                } else {
                    Log.d(TAG, "No normalization_rules.csv found in ZIP (optional)")
                }

                // STEP 2: Extract and parse dictionary.csv (optional - for morphology-only imports like CLTK)
                // Now normalization patterns are available for use during import
                val dictEntry = zipArchive.getEntry(DICTIONARY_CSV)
                if (dictEntry != null) {
                    Log.d(TAG, "Found dictionary.csv in ZIP, parsing...")
                    zipArchive.getInputStream(dictEntry).use { stream ->
                        result.lemmas = parseDictionaryCSV(
                            InputStreamReader(stream, Charsets.UTF_8),
                            fileName,
                            importDate,
                            packageId,
                            result.normalizationPatterns  // Pass patterns for normalization
                        )
                    }
                } else {
                    Log.d(TAG, "No dictionary.csv found in ZIP (optional - using morphology only)")
                }

                // STEP 3: Extract and parse morphology.csv with batch callback
                val morphEntry = zipArchive.getEntry(MORPHOLOGY_CSV)
                    ?: throw IllegalArgumentException("Missing $MORPHOLOGY_CSV in ZIP file")

                zipArchive.getInputStream(morphEntry).use { stream ->
                    if (batchCallback != null) {
                        // Stream processing with batch callback
                        parseMorphologyCSVStreaming(
                            InputStreamReader(stream, Charsets.UTF_8),
                            fileName,
                            importDate,
                            packageId,
                            result.normalizationPatterns,  // Pass patterns for normalization
                            batchCallback
                        )
                        // Don't accumulate mappings in memory
                    } else {
                        // Original behavior - accumulate all mappings
                        result.mappings = parseMorphologyCSV(
                            InputStreamReader(stream, Charsets.UTF_8),
                            fileName,
                            importDate,
                            packageId,
                            result.normalizationPatterns  // Pass patterns for normalization
                        )
                    }
                }
            }

            // Skip validation if streaming (can't validate without all mappings in memory)
            if (batchCallback == null) {
                // Validate cross-references
                val lemmaSet = result.lemmas.map { it.lemma to it.language }.toSet()
                val orphaned = result.mappings.filter { mapping ->
                    (mapping.lemma to mapping.language) !in lemmaSet
                }
                
                if (orphaned.isNotEmpty()) {
                    orphaned.forEach { mapping ->
                        result.orphanedMappings.add(
                            "Morphology entry '${mapping.wordForm}' references undefined lemma '${mapping.lemma}'"
                        )
                    }
                    Log.w(TAG, "${orphaned.size} morphology entries reference undefined lemmas")
                }
            }
            
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing ZIP file", e)
            throw e
        }
        
        return result
    }
    
    private fun sanitizeField(field: String?): String? {
        if (field == null) return null
        // Truncate extremely long fields to prevent memory issues
        return if (field.length > MAX_FIELD_LENGTH) {
            Log.w(TAG, "Field truncated from ${field.length} to $MAX_FIELD_LENGTH characters")
            field.substring(0, MAX_FIELD_LENGTH)
        } else {
            field
        }
    }
    
    private fun parseDictionaryCSV(
        reader: InputStreamReader,
        fileName: String,
        importDate: Long,
        packageId: Long,
        normalizationPatterns: List<NormalizationPatternEntity>
    ): List<UserDictionaryLemmaEntity> {
        val entries = mutableListOf<UserDictionaryLemmaEntity>()
        
        try {
            val csvReader = try {
                CSVReaderBuilder(reader)
                    .withSkipLines(0)
                    .build()
            } catch (e: Exception) {
                throw IllegalArgumentException("Invalid CSV format: ${e.message}")
            }
            
            csvReader.use { csv ->
                // Read header - handle null or empty
                val header = try {
                    csv.readNext()
                } catch (e: Exception) {
                    throw IllegalArgumentException("Cannot read CSV header: ${e.message}")
                }
                
                if (header == null || header.isEmpty()) {
                    throw IllegalArgumentException("Empty or invalid dictionary.csv")
                }
                
                val headerMap = try {
                    header.withIndex().associate { it.value.lowercase() to it.index }
                } catch (e: Exception) {
                    throw IllegalArgumentException("Invalid CSV header format: ${e.message}")
                }
                
                // Validate required columns
                val lemmaIdx = headerMap["lemma"] ?: throw IllegalArgumentException("Missing 'lemma' column in dictionary.csv")
                val languageIdx = headerMap["language"] ?: throw IllegalArgumentException("Missing 'language' column in dictionary.csv")
                val definitionIdx = headerMap["definition"] ?: throw IllegalArgumentException("Missing 'definition' column in dictionary.csv")
                
                // Optional columns
                val htmlDefinitionIdx = headerMap["html_definition"]
                val sourceNameIdx = headerMap["source_name"]
                
                var lineNumber = 2 // Start at 2 (header is line 1)
                csv.forEach { row ->
                    try {
                        // Skip null or empty rows
                        if (row == null) {
                            Log.w(TAG, "Skipping null row at line $lineNumber")
                            lineNumber++
                            return@forEach
                        }
                        
                        if (row.size > lemmaIdx && row.size > languageIdx && row.size > definitionIdx) {
                            val lemma = sanitizeField(row[lemmaIdx]?.trim()) ?: ""
                            val language = row[languageIdx]?.trim()?.lowercase() ?: ""
                            val definition = sanitizeField(row[definitionIdx]?.trim()) ?: ""
                            
                            if (lemma.isNotEmpty() && language.isNotEmpty()) {
                                val normalizedLemma = when (language) {
                                    "greek" -> {
                                        try {
                                            GreekNormalizer.normalize(lemma)
                                        } catch (e: Exception) {
                                            Log.w(TAG, "Failed to normalize Greek lemma: $lemma")
                                            null
                                        }
                                    }
                                    else -> {
                                        // Use pattern-based normalization for non-Greek languages
                                        val langPatterns = normalizationPatterns.filter { it.language == language }
                                        if (langPatterns.isNotEmpty()) {
                                            try {
                                                PatternBasedNormalizer.normalize(lemma, language, langPatterns)
                                            } catch (e: Exception) {
                                                Log.w(TAG, "Failed to normalize $language lemma: $lemma")
                                                null
                                            }
                                        } else {
                                            null
                                        }
                                    }
                                }
                                
                                entries.add(
                                    UserDictionaryLemmaEntity(
                                        packageId = packageId,
                                        lemma = lemma,
                                        lemmaNormalizedUltra = normalizedLemma,
                                        language = language,
                                        definitionPlain = definition,
                                        definitionHtml = sanitizeField(htmlDefinitionIdx?.let { row.getOrNull(it)?.trim() }),
                                        sourceName = sanitizeField(sourceNameIdx?.let { row.getOrNull(it)?.trim() }) ?: "User Import",
                                        importFileName = fileName,
                                        importDate = importDate
                                    )
                                )
                            }
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Error parsing dictionary.csv line $lineNumber: ${e.message}")
                    }
                    lineNumber++
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse dictionary CSV", e)
            throw e
        }
        
        Log.d(TAG, "Parsed ${entries.size} dictionary entries")
        return entries
    }
    
    private suspend fun parseMorphologyCSVStreaming(
        reader: InputStreamReader,
        fileName: String,
        importDate: Long,
        packageId: Long,
        normalizationPatterns: List<NormalizationPatternEntity>,
        batchCallback: suspend (List<UserLemmaMappingEntity>) -> Unit
    ) {
        val BATCH_SIZE = 1000 // Process in smaller batches
        val mappings = mutableListOf<UserLemmaMappingEntity>()
        var totalProcessed = 0
        var rejectedRowSize = 0
        var rejectedEmpty = 0
        var rejectedNormalization = 0
        
        try {
            val csvReader = try {
                CSVReaderBuilder(reader)
                    .withSkipLines(0)
                    .build()
            } catch (e: Exception) {
                throw IllegalArgumentException("Invalid CSV format: ${e.message}")
            }
            
            csvReader.use { csv ->
                // Read header - handle null or empty
                val header = try {
                    csv.readNext()
                } catch (e: Exception) {
                    throw IllegalArgumentException("Cannot read CSV header: ${e.message}")
                }
                
                if (header == null || header.isEmpty()) {
                    throw IllegalArgumentException("Empty or invalid morphology.csv")
                }
                
                val headerMap = try {
                    header.withIndex().associate { it.value.lowercase() to it.index }
                } catch (e: Exception) {
                    throw IllegalArgumentException("Invalid CSV header format: ${e.message}")
                }
                
                // Validate required columns
                val wordFormIdx = headerMap["word_form"] ?: throw IllegalArgumentException("Missing 'word_form' column in morphology.csv")
                val lemmaIdx = headerMap["lemma"] ?: throw IllegalArgumentException("Missing 'lemma' column in morphology.csv")
                val languageIdx = headerMap["language"] ?: throw IllegalArgumentException("Missing 'language' column in morphology.csv")
                
                // Optional columns - check for both possible header names
                val morphInfoIdx = headerMap["morph_info"] ?: headerMap["morphology_info"]
                if (morphInfoIdx == null && (headerMap.containsKey("morphology_info") || headerMap.containsKey("morph_info"))) {
                    Log.w(TAG, "Warning: morphology column found but with unexpected name")
                }
                
                // Validate CSV format if morph_info is expected but missing
                if (morphInfoIdx == null && headerMap.containsKey("morphology_info")) {
                    throw IllegalArgumentException("Invalid CSV format: found 'morphology_info' column but expected 'morph_info'. Please use the correct CSV format.")
                }
                
                val confidenceIdx = headerMap["confidence"]
                val sourceNameIdx = headerMap["source_name"]
                
                var lineNumber = 2 // Start at 2 (header is line 1)
                var row: Array<String>? = csv.readNext()
                
                // Stream through CSV one row at a time
                while (row != null) {
                    try {
                        val currentRow = row
                        if (currentRow == null || currentRow.size <= wordFormIdx || currentRow.size <= lemmaIdx || currentRow.size <= languageIdx) {
                            rejectedRowSize++
                            if (rejectedRowSize <= 5) {
                                Log.w(TAG, "REJECTED at line $lineNumber: Row size ${currentRow?.size ?: 0} too small (need > $wordFormIdx, $lemmaIdx, $languageIdx)")
                            }
                        } else {
                            val wordForm = sanitizeField(currentRow[wordFormIdx]?.trim()) ?: ""
                            val lemma = sanitizeField(currentRow[lemmaIdx]?.trim()) ?: ""
                            val language = currentRow[languageIdx]?.trim()?.lowercase() ?: ""

                            if (wordForm.isEmpty() || lemma.isEmpty() || language.isEmpty()) {
                                rejectedEmpty++
                                if (rejectedEmpty <= 5) {
                                    Log.w(TAG, "REJECTED at line $lineNumber: Empty fields - word='$wordForm' lemma='$lemma' lang='$language'")
                                }
                            } else if (wordForm.isNotEmpty() && lemma.isNotEmpty() && language.isNotEmpty()) {
                                val langPatterns = normalizationPatterns.filter { it.language == language }

                                val normalizedWord = when (language) {
                                    "greek" -> {
                                        try {
                                            GreekNormalizer.normalize(wordForm)
                                        } catch (e: Exception) {
                                            rejectedNormalization++
                                            if (rejectedNormalization <= 5) {
                                                Log.w(TAG, "NORMALIZATION FAILED at line $lineNumber: Greek word '$wordForm' - ${e.message}")
                                            }
                                            null
                                        }
                                    }
                                    else -> {
                                        if (langPatterns.isNotEmpty()) {
                                            try {
                                                PatternBasedNormalizer.normalize(wordForm, language, langPatterns)
                                            } catch (e: Exception) {
                                                rejectedNormalization++
                                                if (rejectedNormalization <= 5) {
                                                    Log.w(TAG, "NORMALIZATION FAILED at line $lineNumber: $language word '$wordForm' - ${e.message}")
                                                }
                                                null
                                            }
                                        } else null
                                    }
                                }

                                val normalizedLemma = when (language) {
                                    "greek" -> {
                                        try {
                                            GreekNormalizer.normalize(lemma)
                                        } catch (e: Exception) {
                                            rejectedNormalization++
                                            if (rejectedNormalization <= 5) {
                                                Log.w(TAG, "NORMALIZATION FAILED at line $lineNumber: Greek lemma '$lemma' - ${e.message}")
                                            }
                                            null
                                        }
                                    }
                                    else -> {
                                        if (langPatterns.isNotEmpty()) {
                                            try {
                                                PatternBasedNormalizer.normalize(lemma, language, langPatterns)
                                            } catch (e: Exception) {
                                                rejectedNormalization++
                                                if (rejectedNormalization <= 5) {
                                                    Log.w(TAG, "NORMALIZATION FAILED at line $lineNumber: $language lemma '$lemma' - ${e.message}")
                                                }
                                                null
                                            }
                                        } else null
                                    }
                                }

                                val confidence = confidenceIdx?.let {
                                    currentRow.getOrNull(it)?.toDoubleOrNull() ?: 1.0
                                } ?: 1.0

                                mappings.add(
                                    UserLemmaMappingEntity(
                                        packageId = packageId,
                                        wordForm = wordForm,
                                        wordFormNormalizedUltra = normalizedWord,
                                        lemma = lemma,
                                        lemmaNormalizedUltra = normalizedLemma,
                                        morphInfo = sanitizeField(morphInfoIdx?.let { currentRow.getOrNull(it)?.trim() }),
                                        confidence = confidence.coerceIn(0.0, 1.0),
                                        language = language,
                                        sourceName = sanitizeField(sourceNameIdx?.let { currentRow.getOrNull(it)?.trim() }) ?: "User Import",
                                        importFileName = fileName,
                                        importDate = importDate
                                    )
                                )

                                // Log first few successful imports
                                if (totalProcessed + mappings.size <= 3) {
                                    Log.d(TAG, "IMPORTED line $lineNumber: '$wordForm' → '$lemma' (normalized: ${normalizedWord != null})")
                                }

                                // Send batch when reaching BATCH_SIZE
                                if (mappings.size >= BATCH_SIZE) {
                                    batchCallback(mappings.toList())
                                    totalProcessed += mappings.size
                                    Log.d(TAG, "Streamed $totalProcessed morphology entries")
                                    mappings.clear()
                                }
                            }
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Error parsing morphology.csv line $lineNumber: ${e.message}")
                    }
                    lineNumber++
                    
                    // Read next row - streaming approach
                    row = try {
                        csv.readNext()
                    } catch (e: Exception) {
                        Log.w(TAG, "Error reading next row at line $lineNumber: ${e.message}")
                        null
                    }
                }
                
                // Send remaining mappings
                if (mappings.isNotEmpty()) {
                    batchCallback(mappings.toList())
                    totalProcessed += mappings.size
                    mappings.clear()
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse morphology CSV", e)
            throw e
        }
        
        Log.d(TAG, "Streamed total of $totalProcessed morphology mappings")
    }
    
    private fun parseMorphologyCSV(
        reader: InputStreamReader,
        fileName: String,
        importDate: Long,
        packageId: Long,
        normalizationPatterns: List<NormalizationPatternEntity>
    ): List<UserLemmaMappingEntity> {
        val mappings = mutableListOf<UserLemmaMappingEntity>()
        
        try {
            val csvReader = try {
                CSVReaderBuilder(reader)
                    .withSkipLines(0)
                    .build()
            } catch (e: Exception) {
                throw IllegalArgumentException("Invalid CSV format: ${e.message}")
            }
            
            csvReader.use { csv ->
                // Read header - handle null or empty
                val header = try {
                    csv.readNext()
                } catch (e: Exception) {
                    throw IllegalArgumentException("Cannot read CSV header: ${e.message}")
                }
                
                if (header == null || header.isEmpty()) {
                    throw IllegalArgumentException("Empty or invalid morphology.csv")
                }
                
                val headerMap = try {
                    header.withIndex().associate { it.value.lowercase() to it.index }
                } catch (e: Exception) {
                    throw IllegalArgumentException("Invalid CSV header format: ${e.message}")
                }
                
                // Validate required columns
                val wordFormIdx = headerMap["word_form"] ?: throw IllegalArgumentException("Missing 'word_form' column in morphology.csv")
                val lemmaIdx = headerMap["lemma"] ?: throw IllegalArgumentException("Missing 'lemma' column in morphology.csv")
                val languageIdx = headerMap["language"] ?: throw IllegalArgumentException("Missing 'language' column in morphology.csv")
                
                // Optional columns - check for both possible header names
                val morphInfoIdx = headerMap["morph_info"] ?: headerMap["morphology_info"]
                if (morphInfoIdx == null && (headerMap.containsKey("morphology_info") || headerMap.containsKey("morph_info"))) {
                    Log.w(TAG, "Warning: morphology column found but with unexpected name")
                }
                
                // Validate CSV format if morph_info is expected but missing
                if (morphInfoIdx == null && headerMap.containsKey("morphology_info")) {
                    throw IllegalArgumentException("Invalid CSV format: found 'morphology_info' column but expected 'morph_info'. Please use the correct CSV format.")
                }
                
                val confidenceIdx = headerMap["confidence"]
                val sourceNameIdx = headerMap["source_name"]
                
                var lineNumber = 2 // Start at 2 (header is line 1)
                var row: Array<String>? = csv.readNext()
                var processedCount = 0
                var rejectedRowSize = 0
                var rejectedEmpty = 0
                var rejectedNormalization = 0
                val BATCH_SIZE = 5000 // Clear list periodically to avoid memory issues

                // Stream through CSV one row at a time instead of loading all into memory
                while (row != null) {
                    try {
                        // Clear mappings list periodically if it gets too large
                        if (processedCount >= BATCH_SIZE) {
                            Log.d(TAG, "Processed $processedCount morphology entries, continuing...")
                            processedCount = 0
                            // Note: In a real implementation, we'd insert to DB here and clear the list
                            // For now, we'll keep accumulating but log progress
                        }

                        val currentRow = row
                        if (currentRow == null || currentRow.size <= wordFormIdx || currentRow.size <= lemmaIdx || currentRow.size <= languageIdx) {
                            rejectedRowSize++
                            if (rejectedRowSize <= 5) {
                                Log.w(TAG, "REJECTED at line $lineNumber: Row size ${currentRow?.size ?: 0} too small (need > $wordFormIdx, $lemmaIdx, $languageIdx)")
                            }
                        } else {
                            val wordForm = sanitizeField(currentRow[wordFormIdx]?.trim()) ?: ""
                            val lemma = sanitizeField(currentRow[lemmaIdx]?.trim()) ?: ""
                            val language = currentRow[languageIdx]?.trim()?.lowercase() ?: ""

                            if (wordForm.isEmpty() || lemma.isEmpty() || language.isEmpty()) {
                                rejectedEmpty++
                                if (rejectedEmpty <= 5) {
                                    Log.w(TAG, "REJECTED at line $lineNumber: Empty fields - word='$wordForm' lemma='$lemma' lang='$language'")
                                }
                            } else if (wordForm.isNotEmpty() && lemma.isNotEmpty() && language.isNotEmpty()) {
                                val langPatterns = normalizationPatterns.filter { it.language == language }

                                val normalizedWord = when (language) {
                                    "greek" -> {
                                        try {
                                            GreekNormalizer.normalize(wordForm)
                                        } catch (e: Exception) {
                                            rejectedNormalization++
                                            if (rejectedNormalization <= 5) {
                                                Log.w(TAG, "NORMALIZATION FAILED at line $lineNumber: Greek word '$wordForm' - ${e.message}")
                                            }
                                            null
                                        }
                                    }
                                    else -> {
                                        if (langPatterns.isNotEmpty()) {
                                            try {
                                                PatternBasedNormalizer.normalize(wordForm, language, langPatterns)
                                            } catch (e: Exception) {
                                                rejectedNormalization++
                                                if (rejectedNormalization <= 5) {
                                                    Log.w(TAG, "NORMALIZATION FAILED at line $lineNumber: $language word '$wordForm' - ${e.message}")
                                                }
                                                null
                                            }
                                        } else null
                                    }
                                }

                                val normalizedLemma = when (language) {
                                    "greek" -> {
                                        try {
                                            GreekNormalizer.normalize(lemma)
                                        } catch (e: Exception) {
                                            rejectedNormalization++
                                            if (rejectedNormalization <= 5) {
                                                Log.w(TAG, "NORMALIZATION FAILED at line $lineNumber: Greek lemma '$lemma' - ${e.message}")
                                            }
                                            null
                                        }
                                    }
                                    else -> {
                                        if (langPatterns.isNotEmpty()) {
                                            try {
                                                PatternBasedNormalizer.normalize(lemma, language, langPatterns)
                                            } catch (e: Exception) {
                                                rejectedNormalization++
                                                if (rejectedNormalization <= 5) {
                                                    Log.w(TAG, "NORMALIZATION FAILED at line $lineNumber: $language lemma '$lemma' - ${e.message}")
                                                }
                                                null
                                            }
                                        } else null
                                    }
                                }

                                val confidence = confidenceIdx?.let {
                                    currentRow.getOrNull(it)?.toDoubleOrNull() ?: 1.0
                                } ?: 1.0

                                mappings.add(
                                    UserLemmaMappingEntity(
                                        packageId = packageId,
                                        wordForm = wordForm,
                                        wordFormNormalizedUltra = normalizedWord,
                                        lemma = lemma,
                                        lemmaNormalizedUltra = normalizedLemma,
                                        morphInfo = sanitizeField(morphInfoIdx?.let { currentRow.getOrNull(it)?.trim() }),
                                        confidence = confidence.coerceIn(0.0, 1.0),
                                        language = language,
                                        sourceName = sanitizeField(sourceNameIdx?.let { currentRow.getOrNull(it)?.trim() }) ?: "User Import",
                                        importFileName = fileName,
                                        importDate = importDate
                                    )
                                )
                                processedCount++

                                // Log first few successful imports to verify
                                if (processedCount <= 3) {
                                    Log.d(TAG, "IMPORTED line $lineNumber: '$wordForm' → '$lemma' (normalized: ${normalizedWord != null})")
                                }
                            }
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Error parsing morphology.csv line $lineNumber: ${e.message}")
                    }
                    lineNumber++

                    // Read next row - streaming approach
                    row = try {
                        csv.readNext()
                    } catch (e: Exception) {
                        Log.w(TAG, "Error reading next row at line $lineNumber: ${e.message}")
                        null
                    }
                }

                // Log final statistics
                Log.d(TAG, "=== IMPORT STATISTICS ===")
                Log.d(TAG, "Successfully imported: $processedCount entries")
                Log.d(TAG, "Rejected (row size): $rejectedRowSize")
                Log.d(TAG, "Rejected (empty fields): $rejectedEmpty")
                Log.d(TAG, "Normalization warnings: $rejectedNormalization")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse morphology CSV", e)
            throw e
        }
        
        Log.d(TAG, "Parsed ${mappings.size} morphology mappings")
        return mappings
    }

    private fun parseNormalizationCSV(
        reader: InputStreamReader,
        packageId: Long
    ): List<NormalizationPatternEntity> {
        val patterns = mutableListOf<NormalizationPatternEntity>()

        try {
            val csvReader = CSVReaderBuilder(reader)
                .withSkipLines(1)  // Skip header row
                .build()

            var row: Array<String>?
            var lineNum = 1  // Start at 1 for header

            while (csvReader.readNext().also { row = it } != null) {
                lineNum++
                val currentRow = row ?: continue

                // Expected columns: language, pattern, replacement, description, priority
                if (currentRow.size < 5) {
                    Log.w(TAG, "Skipping malformed normalization rule at line $lineNum: expected 5 columns, got ${currentRow.size}")
                    continue
                }

                val language = currentRow[0]?.trim()?.lowercase() ?: ""
                val patternRaw = currentRow[1]?.trim() ?: ""

                if (lineNum == 2) {  // Log first data row
                    Log.d(TAG, "CSV gave us: '$patternRaw'")
                    Log.d(TAG, "Contains backslash? ${patternRaw.contains("\\")}")
                    Log.d(TAG, "Char codes: ${patternRaw.map { it.code }.joinToString(",")}")
                }

                val pattern = unescapeUnicode(patternRaw)
                val replacement = unescapeUnicode(currentRow[2]?.trim() ?: "")
                val description = currentRow.getOrNull(3)?.trim()
                val priorityStr = currentRow.getOrNull(4)?.trim() ?: ""

                if (lineNum == 2) {  // Log first data row
                    Log.d(TAG, "After unescape: '$pattern'")
                }

                // Validate required fields
                if (language.isEmpty()) {
                    Log.w(TAG, "Skipping normalization rule at line $lineNum: empty language")
                    continue
                }

                if (pattern.isEmpty()) {
                    Log.w(TAG, "Skipping normalization rule at line $lineNum: empty pattern")
                    continue
                }

                // Parse priority (default to 999 if invalid)
                val priority = try {
                    priorityStr.toInt()
                } catch (e: NumberFormatException) {
                    Log.w(TAG, "Invalid priority '$priorityStr' at line $lineNum, defaulting to 999")
                    999
                }

                // Validate regex pattern
                try {
                    Regex(pattern)
                } catch (e: Exception) {
                    Log.w(TAG, "Skipping normalization rule at line $lineNum: invalid regex pattern '$pattern': ${e.message}")
                    continue
                }

                patterns.add(
                    NormalizationPatternEntity(
                        packageId = packageId,
                        language = language,
                        pattern = pattern,
                        replacement = replacement,
                        description = description,
                        priority = priority
                    )
                )
            }

            csvReader.close()

        } catch (e: Exception) {
            Log.e(TAG, "Error parsing normalization CSV", e)
            throw IllegalArgumentException("Failed to parse normalization_rules.csv: ${e.message}")
        }

        return patterns
    }

    /**
     * Convert Unicode escape sequences (\\uXXXX) in a string to actual Unicode characters.
     * For example: "[\\u064B-\\u065F]" -> "[ً-ٟ]"
     */
    private fun unescapeUnicode(input: String): String {
        if (!input.contains("\\u")) {
            return input  // Fast path - no escapes
        }

        val sb = StringBuilder()
        var i = 0
        while (i < input.length) {
            if (i < input.length - 5 && input[i] == '\\' && input[i + 1] == 'u') {
                // Found \uXXXX
                try {
                    val hexCode = input.substring(i + 2, i + 6)
                    val codePoint = hexCode.toInt(16)
                    sb.append(codePoint.toChar())
                    i += 6  // Skip \uXXXX
                } catch (e: Exception) {
                    // Invalid escape sequence - keep as-is
                    sb.append(input[i])
                    i++
                }
            } else {
                sb.append(input[i])
                i++
            }
        }
        return sb.toString()
    }
}