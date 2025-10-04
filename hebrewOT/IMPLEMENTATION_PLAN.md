# Implementation Plan: Data-Driven Normalization Support

## Overview

This document outlines all code changes needed to support optional `normalization_rules.csv` files in custom dictionary imports.

## Summary of Changes

1. **Database Schema** - Add new entity and table for normalization patterns
2. **Entity Class** - Create `NormalizationPatternEntity`
3. **DAO** - Create `NormalizationPatternDao` for database queries
4. **Database Update** - Add entity to `UserDatabase` and increment version
5. **Parser Update** - Modify `DictionaryZipParser` to parse normalization CSV
6. **Normalizer Class** - Create `PatternBasedNormalizer` utility
7. **Replace Calls** - Update all normalization call sites
8. **Repository Methods** - Add methods to fetch normalization patterns

---

## 1. Create Entity Class

**File:** `app/src/main/java/com/classicsviewer/app/database/entities/NormalizationPatternEntity.kt`

```kotlin
package com.classicsviewer.app.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "normalization_patterns",
    indices = [
        Index(value = ["language"]),
        Index(value = ["package_id"]),
        Index(value = ["language", "package_id", "priority"])
    ]
)
data class NormalizationPatternEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    @ColumnInfo(name = "package_id")
    val packageId: Long,

    @ColumnInfo(name = "language")
    val language: String,

    @ColumnInfo(name = "pattern")
    val pattern: String,

    @ColumnInfo(name = "replacement")
    val replacement: String,

    @ColumnInfo(name = "description")
    val description: String?,

    @ColumnInfo(name = "priority")
    val priority: Int,

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis()
)
```

---

## 2. Create DAO Interface

**File:** `app/src/main/java/com/classicsviewer/app/database/dao/NormalizationPatternDao.kt`

```kotlin
package com.classicsviewer.app.database.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.classicsviewer.app.database.entities.NormalizationPatternEntity

@Dao
interface NormalizationPatternDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(patterns: List<NormalizationPatternEntity>)

    @Query("SELECT * FROM normalization_patterns WHERE language = :language ORDER BY priority ASC")
    suspend fun getPatternsForLanguage(language: String): List<NormalizationPatternEntity>

    @Query("SELECT * FROM normalization_patterns WHERE package_id = :packageId ORDER BY language, priority ASC")
    suspend fun getPatternsForPackage(packageId: Long): List<NormalizationPatternEntity>

    @Query("DELETE FROM normalization_patterns WHERE package_id = :packageId")
    suspend fun deleteByPackageId(packageId: Long)

    @Query("SELECT COUNT(*) FROM normalization_patterns WHERE language = :language")
    suspend fun countPatternsForLanguage(language: String): Int

    @Query("DELETE FROM normalization_patterns")
    suspend fun deleteAll()
}
```

---

## 3. Update UserDatabase

**File:** `app/src/main/java/com/classicsviewer/app/database/UserDatabase.kt`

**Changes:**
1. Add `NormalizationPatternEntity` to entities list
2. Add abstract DAO method
3. Increment database version from 7 to 8

```kotlin
package com.classicsviewer.app.database

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.classicsviewer.app.database.dao.BookmarkDao
import com.classicsviewer.app.database.dao.UserDictionaryDao
import com.classicsviewer.app.database.dao.UserLemmaMappingDao
import com.classicsviewer.app.database.dao.UserDictionaryPackageDao
import com.classicsviewer.app.database.dao.NormalizationPatternDao  // ADD THIS
import com.classicsviewer.app.database.entities.BookmarkEntity
import com.classicsviewer.app.database.entities.UserDictionaryLemmaEntity
import com.classicsviewer.app.database.entities.UserLemmaMappingEntity
import com.classicsviewer.app.database.entities.UserDictionaryPackageEntity
import com.classicsviewer.app.database.entities.NormalizationPatternEntity  // ADD THIS

@Database(
    entities = [
        BookmarkEntity::class,
        UserDictionaryLemmaEntity::class,
        UserLemmaMappingEntity::class,
        UserDictionaryPackageEntity::class,
        NormalizationPatternEntity::class  // ADD THIS
    ],
    version = 8,  // INCREMENT FROM 7 TO 8
    exportSchema = true
)
abstract class UserDatabase : RoomDatabase() {
    abstract fun bookmarkDao(): BookmarkDao
    abstract fun userDictionaryDao(): UserDictionaryDao
    abstract fun userLemmaMappingDao(): UserLemmaMappingDao
    abstract fun userDictionaryPackageDao(): UserDictionaryPackageDao
    abstract fun normalizationPatternDao(): NormalizationPatternDao  // ADD THIS

    companion object {
        @Volatile
        private var INSTANCE: UserDatabase? = null

        fun getInstance(context: Context): UserDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    UserDatabase::class.java,
                    "user_data.db"
                )
                .fallbackToDestructiveMigration() // Just recreate on schema change
                .build()
                INSTANCE = instance
                instance
            }
        }

        fun destroyInstance() {
            INSTANCE?.close()
            INSTANCE = null
        }
    }
}
```

---

## 4. Update DictionaryImportData

**File:** `app/src/main/java/com/classicsviewer/app/utils/DictionaryZipParser.kt`

**Change the data class:**

```kotlin
data class DictionaryImportData(
    var lemmas: List<UserDictionaryLemmaEntity> = emptyList(),
    var mappings: List<UserLemmaMappingEntity> = emptyList(),
    var normalizationPatterns: List<NormalizationPatternEntity> = emptyList(),  // ADD THIS
    val orphanedMappings: MutableList<String> = mutableListOf(),
    val errors: MutableList<String> = mutableListOf()
)
```

---

## 5. Update DictionaryZipParser to Parse Normalization CSV

**File:** `app/src/main/java/com/classicsviewer/app/utils/DictionaryZipParser.kt`

**Add constant:**

```kotlin
class DictionaryZipParser {
    companion object {
        private const val TAG = "DictionaryZipParser"
        private const val DICTIONARY_CSV = "dictionary.csv"
        private const val MORPHOLOGY_CSV = "morphology.csv"
        private const val NORMALIZATION_CSV = "normalization_rules.csv"  // ADD THIS

        private const val MAX_FIELD_LENGTH = 50000
    }
```

**Add to parseZipFile method (after morphology parsing):**

```kotlin
suspend fun parseZipFile(
    zipFile: File,
    originalFileName: String,
    packageId: Long,
    batchCallback: (suspend (List<UserLemmaMappingEntity>) -> Unit)?
): DictionaryImportData {
    val result = DictionaryImportData()
    val importDate = System.currentTimeMillis()
    val fileName = originalFileName

    // ... existing code for dictionary.csv and morphology.csv ...

    zip.use { zipArchive ->
        // ... existing dictionary and morphology parsing ...

        // Extract and parse normalization_rules.csv (OPTIONAL)
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
    }

    return result
}
```

**Add new parsing method:**

```kotlin
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
            val pattern = currentRow[1]?.trim() ?: ""
            val replacement = currentRow[2]?.trim() ?: ""
            val description = currentRow.getOrNull(3)?.trim()
            val priorityStr = currentRow.getOrNull(4)?.trim() ?: ""

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
```

---

## 6. Create PatternBasedNormalizer Utility

**File:** `app/src/main/java/com/classicsviewer/app/utils/PatternBasedNormalizer.kt`

```kotlin
package com.classicsviewer.app.utils

import android.util.Log
import com.classicsviewer.app.database.entities.NormalizationPatternEntity
import java.text.Normalizer
import java.util.concurrent.ConcurrentHashMap

/**
 * Data-driven text normalizer that applies regex patterns from the database.
 *
 * Normalization happens in two phases:
 * 1. NFD (Unicode Canonical Decomposition) - separates base chars from combining marks
 * 2. Apply custom regex patterns in priority order
 *
 * Example:
 *   Input: "λόγος" (with accent)
 *   After NFD: "λο\u0301γος" (accent separated)
 *   After pattern [\u0300-\u036F] → "": "λογος" (accent removed)
 */
object PatternBasedNormalizer {
    private const val TAG = "PatternNormalizer"

    // Cache compiled regex patterns per language for performance
    private data class CompiledPattern(
        val regex: Regex,
        val replacement: String,
        val priority: Int,
        val description: String?
    )

    private val compiledCache = ConcurrentHashMap<String, List<CompiledPattern>>()

    /**
     * Normalize text using database-driven patterns for the given language.
     *
     * @param text The text to normalize
     * @param language The language code (e.g., "greek", "hebrew", "arabic")
     * @param patterns The normalization patterns to apply (fetched from database)
     * @return Normalized text
     */
    fun normalize(text: String, language: String, patterns: List<NormalizationPatternEntity>): String {
        if (text.isEmpty()) return text

        val compiledPatterns = getCompiledPatterns(language, patterns)

        if (compiledPatterns.isEmpty()) {
            // No normalization rules for this language - return as-is
            return text
        }

        var result = text

        // Step 1: Apply NFD normalization (separates base chars from diacritics)
        result = Normalizer.normalize(result, Normalizer.Form.NFD)

        // Step 2: Apply custom regex patterns in priority order
        for (compiled in compiledPatterns) {
            try {
                result = compiled.regex.replace(result, compiled.replacement)
            } catch (e: Exception) {
                Log.w(TAG, "Error applying pattern '${compiled.regex.pattern}' for $language: ${e.message}")
            }
        }

        return result
    }

    /**
     * Convenience method that takes a single pattern (for testing)
     */
    fun normalize(text: String, language: String, pattern: NormalizationPatternEntity): String {
        return normalize(text, language, listOf(pattern))
    }

    /**
     * Get compiled regex patterns for a language, using cache for performance.
     */
    private fun getCompiledPatterns(language: String, patterns: List<NormalizationPatternEntity>): List<CompiledPattern> {
        // Create cache key from pattern contents (so cache updates if patterns change)
        val cacheKey = "$language:${patterns.size}:${patterns.hashCode()}"

        return compiledCache.getOrPut(cacheKey) {
            patterns
                .sortedBy { it.priority }  // Apply in priority order
                .mapNotNull { pattern ->
                    try {
                        CompiledPattern(
                            regex = Regex(pattern.pattern),
                            replacement = pattern.replacement,
                            priority = pattern.priority,
                            description = pattern.description
                        )
                    } catch (e: Exception) {
                        Log.w(TAG, "Failed to compile pattern '${pattern.pattern}' for $language: ${e.message}")
                        null
                    }
                }
        }
    }

    /**
     * Clear the compiled pattern cache (useful when patterns are updated)
     */
    fun clearCache() {
        compiledCache.clear()
        Log.d(TAG, "Normalization pattern cache cleared")
    }

    /**
     * Clear cache for a specific language
     */
    fun clearCache(language: String) {
        compiledCache.keys.removeIf { it.startsWith("$language:") }
        Log.d(TAG, "Normalization pattern cache cleared for $language")
    }
}
```

---

## 7. Add Repository Methods

**File:** `app/src/main/java/com/classicsviewer/app/data/UserDictionaryRepository.kt`

Add these methods:

```kotlin
// In UserDictionaryRepository class

suspend fun getNormalizationPatterns(language: String): List<NormalizationPatternEntity> {
    return userDatabase.normalizationPatternDao().getPatternsForLanguage(language)
}

suspend fun insertNormalizationPatterns(patterns: List<NormalizationPatternEntity>) {
    userDatabase.normalizationPatternDao().insertAll(patterns)
}

suspend fun deleteNormalizationPatternsForPackage(packageId: Long) {
    userDatabase.normalizationPatternDao().deleteByPackageId(packageId)
}

suspend fun hasNormalizationPatterns(language: String): Boolean {
    return userDatabase.normalizationPatternDao().countPatternsForLanguage(language) > 0
}
```

**Also update the import method to insert normalization patterns:**

Find the method that imports dictionary data and add:

```kotlin
// After inserting lemmas and mappings:
if (importData.normalizationPatterns.isNotEmpty()) {
    insertNormalizationPatterns(importData.normalizationPatterns)
    Log.d(TAG, "Inserted ${importData.normalizationPatterns.size} normalization patterns")
}
```

**Also update the delete method to delete normalization patterns:**

Find the method that deletes a dictionary package and add:

```kotlin
// Delete normalization patterns for this package
deleteNormalizationPatternsForPackage(packageId)
```

---

## 8. Update All Normalization Call Sites

Find and replace all instances of:

```kotlin
val normalizedLemma = if (language == "greek") {
    GreekNormalizer.normalize(lemma)
} else null
```

With:

```kotlin
val normalizedLemma = try {
    val patterns = repository.getNormalizationPatterns(language)
    if (patterns.isNotEmpty()) {
        PatternBasedNormalizer.normalize(lemma, language, patterns)
    } else {
        null
    }
} catch (e: Exception) {
    Log.w(TAG, "Normalization failed for $language: ${e.message}")
    null
}
```

**Files to update:**
- `app/src/main/java/com/classicsviewer/app/data/PerseusRepository.kt` (~15 locations)
- `app/src/main/java/com/classicsviewer/app/data/UserDictionaryRepository.kt` (lines 212, 224)
- `app/src/main/java/com/classicsviewer/app/utils/DictionaryZipParser.kt` (lines 197, 306, 315, 459, 468)

**Optimization:** To avoid repeated database queries, cache the patterns in the repository:

```kotlin
// In PerseusRepository or UserDictionaryRepository
private val normalizationCache = ConcurrentHashMap<String, List<NormalizationPatternEntity>>()

suspend fun getNormalizationPatternsForLanguage(language: String): List<NormalizationPatternEntity> {
    return normalizationCache.getOrPut(language) {
        userDictionaryRepository.getNormalizationPatterns(language)
    }
}

// Helper method to normalize with caching
suspend fun normalizeText(text: String, language: String): String? {
    val patterns = getNormalizationPatternsForLanguage(language)
    return if (patterns.isNotEmpty()) {
        PatternBasedNormalizer.normalize(text, language, patterns)
    } else {
        null
    }
}
```

---

## 9. Backward Compatibility with Greek

To maintain existing Greek normalization behavior, add default Greek patterns on app startup or database creation:

**Option 1: Migration**

Create default Greek patterns when upgrading to database version 8:

```kotlin
// In UserDatabase companion object, add migration
val MIGRATION_7_8 = object : Migration(7, 8) {
    override fun migrate(database: SupportSQLiteDatabase) {
        // Create normalization_patterns table
        database.execSQL("""
            CREATE TABLE IF NOT EXISTS normalization_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                package_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                pattern TEXT NOT NULL,
                replacement TEXT NOT NULL,
                description TEXT,
                priority INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)

        // Create indices
        database.execSQL("CREATE INDEX IF NOT EXISTS index_normalization_patterns_language ON normalization_patterns(language)")
        database.execSQL("CREATE INDEX IF NOT EXISTS index_normalization_patterns_package_id ON normalization_patterns(package_id)")
        database.execSQL("CREATE INDEX IF NOT EXISTS index_normalization_patterns_language_package_id_priority ON normalization_patterns(language, package_id, priority)")

        // Insert default Greek normalization patterns (package_id = 0 for built-in)
        database.execSQL("""
            INSERT INTO normalization_patterns (package_id, language, pattern, replacement, description, priority, created_at)
            VALUES
                (0, 'greek', '[\u0300-\u036F]', '', 'Remove combining diacritics', 1, ${System.currentTimeMillis()}),
                (0, 'greek', 'ς', 'σ', 'Final sigma to regular sigma', 2, ${System.currentTimeMillis()})
        """)
    }
}

// Then use it in databaseBuilder:
Room.databaseBuilder(...)
    .addMigrations(MIGRATION_7_8)
    .build()
```

**Option 2: Fallback to GreekNormalizer**

Keep `GreekNormalizer` as a fallback:

```kotlin
suspend fun normalizeText(text: String, language: String): String? {
    val patterns = getNormalizationPatternsForLanguage(language)
    return if (patterns.isNotEmpty()) {
        PatternBasedNormalizer.normalize(text, language, patterns)
    } else if (language == "greek") {
        // Fallback to hardcoded Greek normalizer
        GreekNormalizer.normalize(text)
    } else {
        null
    }
}
```

---

## 10. Testing Checklist

After implementing:

1. ✅ Test Greek dictionary import without normalization_rules.csv (should still work with fallback)
2. ✅ Test Hebrew dictionary import with `normalization_rules_hebrew.csv`
3. ✅ Test Arabic dictionary import with `normalization_rules_arabic.csv`
4. ✅ Test clicking on Hebrew word with nikud - should find normalized lemma
5. ✅ Test clicking on Arabic word with tashkeel - should find normalized lemma
6. ✅ Test deleting a dictionary package - should delete associated normalization patterns
7. ✅ Verify normalization patterns are cached (check logs for repeated queries)
8. ✅ Test invalid regex pattern in CSV - should log warning and skip
9. ✅ Test malformed CSV (missing columns) - should handle gracefully

---

## Summary of Files to Create/Modify

### New Files (3):
1. `app/src/main/java/com/classicsviewer/app/database/entities/NormalizationPatternEntity.kt`
2. `app/src/main/java/com/classicsviewer/app/database/dao/NormalizationPatternDao.kt`
3. `app/src/main/java/com/classicsviewer/app/utils/PatternBasedNormalizer.kt`

### Modified Files (5-6):
1. `app/src/main/java/com/classicsviewer/app/database/UserDatabase.kt` - Add entity, DAO, increment version
2. `app/src/main/java/com/classicsviewer/app/utils/DictionaryZipParser.kt` - Parse normalization CSV
3. `app/src/main/java/com/classicsviewer/app/data/UserDictionaryRepository.kt` - Add methods, update import/delete
4. `app/src/main/java/com/classicsviewer/app/data/PerseusRepository.kt` - Update normalization calls (~15 locations)
5. Potentially other files with normalization calls

### Total Changes:
- **3 new files** (~300 lines of code)
- **5-6 modified files** (~100 lines added/changed)
- **Database version increment** (7 → 8)

---

## Migration Strategy

1. **Phase 1:** Create new entity, DAO, and utility class
2. **Phase 2:** Update database schema and add migration
3. **Phase 3:** Update DictionaryZipParser to parse CSV
4. **Phase 4:** Add repository methods
5. **Phase 5:** Update normalization call sites (can be gradual)
6. **Phase 6:** Test with sample dictionaries
7. **Phase 7:** Deploy with default Greek patterns for backward compatibility

---

## Performance Considerations

- **Caching:** Compiled regex patterns are cached per language
- **Lazy Loading:** Patterns only loaded when needed for a language
- **Batch Insert:** Normalization patterns inserted in batch, not one-by-one
- **Index:** Database indices on `language` for fast lookups
- **NFD Once:** NFD normalization applied once, then all patterns in sequence

---

## Future Enhancements

1. **User-editable patterns** - UI to enable/disable specific normalization rules
2. **Pattern profiles** - "Strict" vs "Fuzzy" normalization modes
3. **Export patterns** - Allow users to export normalization rules from existing dictionaries
4. **Pattern testing** - UI to test regex patterns before import
5. **Default patterns** - Ship app with default Hebrew/Arabic patterns

---

## Questions to Resolve

1. **Should Greek patterns be hardcoded or in database?**
   - Recommendation: Migration inserts default Greek patterns, deprecate `GreekNormalizer`

2. **Should NFD normalization always be applied?**
   - Recommendation: Yes, it's safe and handles most cases automatically

3. **Should normalization be per-dictionary or per-language?**
   - Current design: Per-language (all dictionaries for a language share patterns)
   - Alternative: Per-package (each dictionary has its own patterns)
   - Recommendation: Keep per-language for simplicity

4. **What happens if multiple dictionaries have conflicting patterns?**
   - Current design: Later imports override (REPLACE conflict strategy)
   - Alternative: Merge and use all patterns
   - Recommendation: Keep REPLACE for simplicity, document in README

---

## Implementation Order

Suggested order to minimize breakage:

1. Create `NormalizationPatternEntity.kt`
2. Create `NormalizationPatternDao.kt`
3. Update `UserDatabase.kt` (add entity, DAO, version)
4. Create `PatternBasedNormalizer.kt`
5. Test normalizer with hardcoded patterns
6. Update `DictionaryZipParser.kt` data class
7. Add `parseNormalizationCSV()` method
8. Update `parseZipFile()` to call parser
9. Add repository methods in `UserDictionaryRepository.kt`
10. Update import/delete methods
11. Create helper method `normalizeText()` with caching
12. Update normalization call sites one file at a time
13. Test with sample dictionaries
14. Add migration with default Greek patterns
15. Deploy and test on device

Total estimated effort: **4-6 hours** for experienced Android/Kotlin developer.
