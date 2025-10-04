# Implementation Plan: Data-Driven Normalization (No Version Change, Greek/Latin Excluded)

## Overview

This document outlines all code changes needed to support optional `normalization_rules.csv` files in custom dictionary imports **without changing the database version** and **keeping Greek/Latin normalization unchanged**.

## Key Principles

1. **No database version change** - Stays at version 7
2. **Greek uses existing `GreekNormalizer`** - No changes to Greek normalization
3. **Latin unchanged** - No normalization (as currently implemented)
4. **New system only for other languages** - Hebrew, Arabic, Aramaic, etc.
5. **Table created at runtime** - Using Room callback on database open
6. **Greek/Latin patterns filtered out** - If accidentally included in CSV

---

## Summary of Changes

### New Files (3):
1. **NormalizationPatternEntity.kt** - Database entity for storing patterns
2. **NormalizationPatternDao.kt** - DAO interface for queries
3. **PatternBasedNormalizer.kt** - Universal normalizer utility

### Modified Files (4-5):
1. **UserDatabase.kt** - Add entity, DAO, callback (NO version change)
2. **DictionaryZipParser.kt** - Parse optional `normalization_rules.csv`
3. **UserDictionaryRepository.kt** - Add methods with Greek/Latin exclusion
4. **PerseusRepository.kt** - Update normalization calls (~15 locations)
5. **Other files** - Update normalization calls as needed

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

## 3. Update UserDatabase.kt

**File:** `app/src/main/java/com/classicsviewer/app/database/UserDatabase.kt`

**Critical changes:**
- Add entity to list
- Add DAO abstract method
- Add callback to create table on open
- **Keep version = 7** (no version change)
- **Set exportSchema = false**
- **Do NOT insert Greek patterns**

```kotlin
package com.classicsviewer.app.database

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
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
    version = 7,  // KEEP AT 7 - NO VERSION CHANGE
    exportSchema = false  // MUST BE FALSE
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
                .fallbackToDestructiveMigration()
                .addCallback(object : RoomDatabase.Callback() {
                    override fun onOpen(db: SupportSQLiteDatabase) {
                        super.onOpen(db)
                        createNormalizationTableIfNeeded(db)
                    }
                })
                .build()
                INSTANCE = instance
                instance
            }
        }

        private fun createNormalizationTableIfNeeded(db: SupportSQLiteDatabase) {
            // Check if table exists
            val cursor = db.query("SELECT name FROM sqlite_master WHERE type='table' AND name='normalization_patterns'")
            val tableExists = cursor.count > 0
            cursor.close()

            if (!tableExists) {
                android.util.Log.d("UserDatabase", "Creating normalization_patterns table")

                // Create table
                db.execSQL("""
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
                db.execSQL("""
                    CREATE INDEX IF NOT EXISTS index_normalization_patterns_language
                    ON normalization_patterns(language)
                """)

                db.execSQL("""
                    CREATE INDEX IF NOT EXISTS index_normalization_patterns_package_id
                    ON normalization_patterns(package_id)
                """)

                db.execSQL("""
                    CREATE INDEX IF NOT EXISTS index_normalization_patterns_lang_pkg_pri
                    ON normalization_patterns(language, package_id, priority)
                """)

                // DO NOT insert any default patterns
                // Greek and Latin use existing hardcoded normalizers

                android.util.Log.d("UserDatabase", "normalization_patterns table created successfully")
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

**Change the data class at the top of the file:**

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

### Add import at top:

```kotlin
import com.classicsviewer.app.database.entities.NormalizationPatternEntity
```

### Add constant:

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

### Add to parseZipFile method (after morphology parsing):

Find the `parseZipFile()` method and add this code after the morphology CSV parsing block:

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

    // ... existing validation and ZIP opening code ...

    zip.use { zipArchive ->
        // ... existing dictionary.csv parsing ...

        // ... existing morphology.csv parsing ...

        // ADD THIS BLOCK - Extract and parse normalization_rules.csv (OPTIONAL)
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

    // ... rest of existing code ...

    return result
}
```

### Add new parsing method (add at end of class):

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
 * NOTE: This normalizer is NOT used for Greek or Latin.
 * - Greek uses GreekNormalizer (hardcoded)
 * - Latin has no normalization
 * - Other languages (Hebrew, Arabic, etc.) use this normalizer
 *
 * Normalization happens in two phases:
 * 1. NFD (Unicode Canonical Decomposition) - separates base chars from combining marks
 * 2. Apply custom regex patterns in priority order
 *
 * Example (Hebrew):
 *   Input: "דָּבָר" (with nikud)
 *   After NFD: "דָּבָר" (nikud separated as combining marks)
 *   After pattern [\u0591-\u05C7] → "": "דבר" (nikud removed)
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
     * @param language The language code (e.g., "hebrew", "arabic") - NOT "greek" or "latin"
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

## 7. Update UserDictionaryRepository.kt

**File:** `app/src/main/java/com/classicsviewer/app/data/UserDictionaryRepository.kt`

### Add import at top:

```kotlin
import com.classicsviewer.app.database.entities.NormalizationPatternEntity
import com.classicsviewer.app.utils.PatternBasedNormalizer
import java.util.concurrent.ConcurrentHashMap
```

### Add these methods to the class:

```kotlin
// Normalization pattern cache (to avoid repeated DB queries)
private val normalizationCache = ConcurrentHashMap<String, List<NormalizationPatternEntity>>()

/**
 * Get normalization patterns for a language.
 * Returns empty list for Greek and Latin (they use existing normalizers).
 */
suspend fun getNormalizationPatterns(language: String): List<NormalizationPatternEntity> {
    // Greek and Latin use existing normalizers - return empty list
    if (language == "greek" || language == "latin") {
        return emptyList()
    }
    return userDatabase.normalizationPatternDao().getPatternsForLanguage(language)
}

/**
 * Insert normalization patterns, filtering out Greek and Latin.
 */
suspend fun insertNormalizationPatterns(patterns: List<NormalizationPatternEntity>) {
    // Filter out Greek and Latin patterns - they shouldn't be in CSV, but just in case
    val filteredPatterns = patterns.filter { it.language != "greek" && it.language != "latin" }

    if (filteredPatterns.isNotEmpty()) {
        userDatabase.normalizationPatternDao().insertAll(filteredPatterns)
        android.util.Log.d(TAG, "Inserted ${filteredPatterns.size} normalization patterns")
    }

    if (filteredPatterns.size < patterns.size) {
        android.util.Log.w(TAG, "Skipped ${patterns.size - filteredPatterns.size} Greek/Latin patterns (use existing normalization)")
    }
}

/**
 * Delete normalization patterns for a package.
 */
suspend fun deleteNormalizationPatternsForPackage(packageId: Long) {
    userDatabase.normalizationPatternDao().deleteByPackageId(packageId)
}

/**
 * Check if normalization patterns exist for a language.
 * Always returns false for Greek and Latin.
 */
suspend fun hasNormalizationPatterns(language: String): Boolean {
    if (language == "greek" || language == "latin") {
        return false  // Use existing normalizers
    }
    return userDatabase.normalizationPatternDao().countPatternsForLanguage(language) > 0
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
```

### Update the dictionary import method:

Find the method that imports dictionary data (likely named something like `importDictionaryPackage` or `importDictionary`) and add after inserting lemmas and mappings:

```kotlin
// After inserting lemmas and mappings, add:
if (importData.normalizationPatterns.isNotEmpty()) {
    insertNormalizationPatterns(importData.normalizationPatterns)
}
```

### Update the dictionary delete method:

Find the method that deletes a dictionary package and add:

```kotlin
// When deleting a package, also delete its normalization patterns:
deleteNormalizationPatternsForPackage(packageId)

// Also clear the cache for affected languages:
normalizationCache.clear()
PatternBasedNormalizer.clearCache()
```

---

## 8. Update Normalization Call Sites

Find all locations where normalization is currently called and update them.

### Current pattern (to find):

```kotlin
val normalizedLemma = if (language == "greek") {
    GreekNormalizer.normalize(lemma)
} else null
```

### Replace with:

```kotlin
val normalizedLemma = repository.normalizeText(lemma, language)
```

**Or if you don't have access to the repository helper method, use:**

```kotlin
val normalizedLemma = when (language) {
    "greek" -> {
        // Use existing Greek normalizer
        GreekNormalizer.normalize(lemma)
    }
    "latin" -> {
        // Latin has no normalization currently
        null
    }
    else -> {
        // For other languages (Hebrew, Arabic, etc.), use pattern-based normalization
        try {
            val patterns = repository.getNormalizationPatterns(language)
            if (patterns.isNotEmpty()) {
                PatternBasedNormalizer.normalize(lemma, language, patterns)
            } else {
                null
            }
        } catch (e: Exception) {
            android.util.Log.w(TAG, "Normalization failed for $language: ${e.message}")
            null
        }
    }
}
```

### Files to update:

- `app/src/main/java/com/classicsviewer/app/data/PerseusRepository.kt` (~15 locations)
- `app/src/main/java/com/classicsviewer/app/data/UserDictionaryRepository.kt` (lines ~212, 224)
- `app/src/main/java/com/classicsviewer/app/utils/DictionaryZipParser.kt` (lines ~197, 306, 315, 459, 468)

Use grep to find all locations:

```bash
grep -rn "GreekNormalizer.normalize" app/src/main/java/
```

---

## 9. Update README

**File:** `hebrewOT/NORMALIZATION_RULES_README.md`

Add this important note at the top:

```markdown
## ⚠️ Important: Greek and Latin

**Greek and Latin normalization is built into the app and cannot be customized.**

- ✅ **Greek normalization:** Always applied using built-in code (removes accents, normalizes final sigma)
- ✅ **Latin normalization:** Currently not implemented
- ❌ **Do NOT include Greek or Latin in `normalization_rules.csv`** - they will be ignored

The data-driven normalization system is **only for other languages** like:
- Hebrew
- Arabic
- Aramaic
- Syriac
- Coptic
- Sanskrit
- Any other language you add

**If you include Greek or Latin patterns in your CSV:**
- They will be filtered out during import
- A warning will be logged: `Skipped X Greek/Latin patterns (use existing normalization)`
- No error will occur
- Your dictionary will still import successfully
```

---

## 10. Behavior Summary

### Normalization by Language

| Language | Normalization Method | Source | Customizable? |
|----------|---------------------|--------|---------------|
| **Greek** | `GreekNormalizer.normalize()` | Hardcoded in app | ❌ No |
| **Latin** | None (returns `null`) | N/A | ❌ No |
| **Hebrew** | `PatternBasedNormalizer.normalize()` | Database patterns from CSV | ✅ Yes |
| **Arabic** | `PatternBasedNormalizer.normalize()` | Database patterns from CSV | ✅ Yes |
| **Other** | `PatternBasedNormalizer.normalize()` | Database patterns from CSV | ✅ Yes |

### What Happens on App Update

**Existing User (has version 7 database with custom dictionaries):**

1. User updates app to new version
2. Database opens (still version 7)
3. `onOpen()` callback runs
4. Checks if `normalization_patterns` table exists
5. Table doesn't exist → creates it with indices
6. **User data preserved:**
   - ✅ All bookmarks still there
   - ✅ All custom dictionaries (Hebrew, Latin, etc.) still work
   - ✅ All lemma mappings preserved
7. New feature available: Can now import dictionaries with normalization rules

**New User (fresh install):**

1. App creates version 7 database
2. `onOpen()` callback runs
3. Creates `normalization_patterns` table
4. Ready to import dictionaries with normalization rules

---

## 11. Example User Workflows

### Example 1: Import Hebrew Dictionary with Normalization

**User has:**
- `hebrew_dictionary.zip` containing:
  - `dictionary.csv` (500 Hebrew entries)
  - `morphology.csv` (2000 Hebrew word forms)
  - `normalization_rules.csv` (6 Hebrew normalization patterns)

**Import process:**
1. User selects ZIP file in app
2. App parses all three CSV files
3. Inserts 500 dictionary entries
4. Inserts 2000 lemma mappings
5. Inserts 6 normalization patterns
6. Log: `Inserted 6 normalization patterns for Hebrew`

**Usage:**
1. User reads Hebrew Bible text
2. Clicks on word "דָּבָר" (with nikud)
3. App applies Hebrew normalization:
   - Fetches 6 patterns from database
   - Applies NFD normalization
   - Removes nikud → "דבר"
4. Looks up "דבר" in dictionary
5. Shows definition: "word, thing, matter"

### Example 2: Import Greek Dictionary (Accidentally includes Greek patterns)

**User has:**
- `greek_supplement.zip` containing:
  - `dictionary.csv` (100 additional Greek entries)
  - `morphology.csv` (500 Greek word forms)
  - `normalization_rules.csv` (4 Greek patterns - not needed!)

**Import process:**
1. User selects ZIP file in app
2. App parses all three CSV files
3. Inserts 100 dictionary entries
4. Inserts 500 lemma mappings
5. **Filters out Greek patterns:**
   - Log: `Skipped 4 Greek/Latin patterns (use existing normalization)`
6. Import succeeds with warning

**Usage:**
1. User reads Greek text
2. Clicks on word "λόγος" (with accent)
3. App uses existing `GreekNormalizer` (NOT database patterns)
4. Normalizes to "λογος"
5. Looks up in dictionary
6. Shows definition: "word, reason, account"

### Example 3: Import Arabic Quran Dictionary

**User has:**
- `arabic_quran.zip` containing:
  - `dictionary.csv` (1000 Arabic entries)
  - `morphology.csv` (5000 Arabic word forms)
  - `normalization_rules.csv` (7 Arabic patterns)

**Import process:**
1. User selects ZIP file in app
2. App parses and imports all data
3. Inserts 7 Arabic normalization patterns
4. Log: `Inserted 7 normalization patterns for Arabic`

**Usage:**
1. User reads Quran with full tashkeel
2. Clicks on "كِتَابٌ" (with diacritics)
3. App applies Arabic normalization:
   - Removes tashkeel
   - Normalizes alif variants
   - Result: "كتاب"
4. Looks up "كتاب"
5. Shows definition: "book"

---

## 12. Testing Checklist

### Database Tests

1. ✅ **Fresh install:**
   - Uninstall app
   - Install new version
   - Verify `normalization_patterns` table created
   - Check with: `adb shell "sqlite3 /data/data/com.classicsviewer.app.debug/databases/user_data.db 'SELECT name FROM sqlite_master WHERE type=\"table\"'"`
   - Should see `normalization_patterns` in list

2. ✅ **Existing user upgrade:**
   - Install old version (without normalization support)
   - Add bookmarks and custom Hebrew dictionary
   - Update to new version
   - Verify bookmarks still there
   - Verify Hebrew dictionary still works
   - Verify `normalization_patterns` table created

3. ✅ **Table structure:**
   ```bash
   adb shell
   cd /data/data/com.classicsviewer.app.debug/databases
   sqlite3 user_data.db
   .schema normalization_patterns
   ```
   Should show table with all columns and indices

### Import Tests

4. ✅ **Hebrew dictionary with normalization:**
   - Import `hebrew_dictionary.zip` with `normalization_rules_hebrew.csv`
   - Verify 6 patterns inserted
   - Check: `SELECT COUNT(*) FROM normalization_patterns WHERE language='hebrew'` → should return 6

5. ✅ **Arabic dictionary with normalization:**
   - Import `arabic_dictionary.zip` with `normalization_rules_arabic.csv`
   - Verify 7 patterns inserted
   - Check: `SELECT COUNT(*) FROM normalization_patterns WHERE language='arabic'` → should return 7

6. ✅ **Greek dictionary (filter patterns):**
   - Create test ZIP with Greek patterns
   - Import
   - Verify warning logged: `Skipped X Greek/Latin patterns`
   - Check: `SELECT COUNT(*) FROM normalization_patterns WHERE language='greek'` → should return 0

7. ✅ **Dictionary without normalization:**
   - Import ZIP without `normalization_rules.csv`
   - Verify no errors
   - Dictionary works normally

### Normalization Tests

8. ✅ **Greek normalization unchanged:**
   - Click on Greek word "λόγος"
   - Verify `GreekNormalizer` is called (check logs)
   - Verify dictionary lookup works

9. ✅ **Latin normalization unchanged:**
   - Click on Latin word
   - Verify no normalization applied
   - Dictionary lookup uses exact form

10. ✅ **Hebrew normalization:**
    - Import Hebrew dictionary with patterns
    - Click on "דָּבָר" (with nikud)
    - Verify normalized to "דבר"
    - Verify dictionary lookup finds entry

11. ✅ **Arabic normalization:**
    - Import Arabic dictionary with patterns
    - Click on "كِتَابٌ" (with tashkeel)
    - Verify normalized to "كتاب"
    - Verify dictionary lookup finds entry

### Delete Tests

12. ✅ **Delete dictionary package:**
    - Import Hebrew dictionary with patterns
    - Delete the dictionary package
    - Verify patterns deleted: `SELECT COUNT(*) FROM normalization_patterns WHERE package_id=X` → should return 0

### Cache Tests

13. ✅ **Pattern caching:**
    - Import Hebrew dictionary
    - Look up several Hebrew words
    - Check logs - should only fetch patterns once per language
    - Subsequent lookups use cache

14. ✅ **Cache clearing:**
    - Import Hebrew dictionary
    - Look up Hebrew word (loads cache)
    - Delete Hebrew dictionary
    - Verify cache cleared (check logs)

### Error Handling Tests

15. ✅ **Invalid regex pattern:**
    - Create CSV with invalid regex: `pattern: "[invalid("`
    - Import
    - Verify warning logged: `invalid regex pattern`
    - Verify import continues (skips invalid pattern)

16. ✅ **Malformed CSV:**
    - Create CSV with missing columns
    - Import
    - Verify warning logged: `expected 5 columns, got X`
    - Verify import continues (skips malformed row)

17. ✅ **Empty language field:**
    - Create CSV with empty language column
    - Import
    - Verify warning logged: `empty language`
    - Verify row skipped

---

## 13. Performance Considerations

### Database

- **Indices created** on `language`, `package_id`, and `(language, package_id, priority)`
- **Fast lookups** - O(log n) with index on language
- **Batch insert** - All patterns inserted in single transaction

### Caching

- **Compiled regex cache** - Patterns compiled once, reused
- **Repository cache** - Database patterns cached per language
- **Cache invalidation** - Cleared when dictionary deleted

### Startup

- **Table creation check** - Runs on every app open
- **Fast check** - `SELECT name FROM sqlite_master` is fast
- **CREATE IF NOT EXISTS** - No-op if table exists
- **Negligible overhead** - ~1ms per app start

---

## 14. Files Changed Summary

### New Files (3):

1. `app/src/main/java/com/classicsviewer/app/database/entities/NormalizationPatternEntity.kt` (~50 lines)
2. `app/src/main/java/com/classicsviewer/app/database/dao/NormalizationPatternDao.kt` (~30 lines)
3. `app/src/main/java/com/classicsviewer/app/utils/PatternBasedNormalizer.kt` (~120 lines)

**Total: ~200 lines of new code**

### Modified Files (4-5):

1. `app/src/main/java/com/classicsviewer/app/database/UserDatabase.kt`
   - Add entity to list
   - Add abstract DAO method
   - Add callback with table creation
   - Set `exportSchema = false`
   - **~30 lines added**

2. `app/src/main/java/com/classicsviewer/app/utils/DictionaryZipParser.kt`
   - Add `normalizationPatterns` field to data class
   - Add constant
   - Add parsing code in `parseZipFile()`
   - Add `parseNormalizationCSV()` method
   - **~80 lines added**

3. `app/src/main/java/com/classicsviewer/app/data/UserDictionaryRepository.kt`
   - Add cache field
   - Add 5 new methods
   - Update import method
   - Update delete method
   - **~60 lines added**

4. `app/src/main/java/com/classicsviewer/app/data/PerseusRepository.kt`
   - Update ~15 normalization call sites
   - **~30 lines changed**

5. Other files with normalization calls
   - **~10 lines changed**

**Total changes: ~210 lines added/modified**

---

## 15. Implementation Order

Suggested order to minimize breakage:

1. ✅ Create `NormalizationPatternEntity.kt`
2. ✅ Create `NormalizationPatternDao.kt`
3. ✅ Update `UserDatabase.kt` (add entity, DAO, callback, set exportSchema=false)
4. ✅ Test app launches without errors
5. ✅ Create `PatternBasedNormalizer.kt`
6. ✅ Test normalizer with hardcoded patterns
7. ✅ Update `DictionaryZipParser.kt` data class
8. ✅ Add `parseNormalizationCSV()` method
9. ✅ Update `parseZipFile()` to parse normalization CSV
10. ✅ Test CSV parsing with sample file
11. ✅ Add repository methods in `UserDictionaryRepository.kt`
12. ✅ Update import method to insert patterns
13. ✅ Update delete method to delete patterns
14. ✅ Add `normalizeText()` helper method
15. ✅ Update normalization call sites (one file at a time)
16. ✅ Test with Hebrew dictionary + normalization CSV
17. ✅ Test with Arabic dictionary + normalization CSV
18. ✅ Verify Greek still uses `GreekNormalizer`
19. ✅ Test on device with existing user data
20. ✅ Deploy

**Estimated effort: 4-6 hours**

---

## 16. Common Issues and Solutions

### Issue 1: Room schema validation error

**Error:** `Pre-packaged database has an invalid schema`

**Cause:** `exportSchema` not set to false

**Solution:** Set `exportSchema = false` in `@Database` annotation

### Issue 2: Table not created

**Error:** `no such table: normalization_patterns`

**Cause:** Callback not running

**Solution:**
- Verify `.addCallback()` is called in database builder
- Check logs for "Creating normalization_patterns table"
- Manually create table: `adb shell "sqlite3 /path/to/user_data.db 'CREATE TABLE normalization_patterns...'"`

### Issue 3: Greek patterns being inserted

**Error:** Greek normalization broken

**Cause:** Filter not working in `insertNormalizationPatterns()`

**Solution:** Check that `if (language == "greek" || language == "latin")` filter is in place

### Issue 4: Normalization not working for Hebrew

**Cause:** Patterns not fetched or cache issue

**Debug:**
```kotlin
// Add logging:
val patterns = getNormalizationPatterns("hebrew")
Log.d("Debug", "Hebrew patterns: ${patterns.size}")
patterns.forEach { Log.d("Debug", "Pattern: ${it.pattern}") }
```

**Solution:** Check database has patterns, clear cache

### Issue 5: App crashes on startup after update

**Cause:** Migration issue

**Debug:** Check logcat for errors

**Solution:**
- Verify `exportSchema = false`
- Verify callback syntax correct
- Test with fresh install first

---

## 17. Final Checklist

Before deploying:

- [ ] All 3 new files created
- [ ] All 4-5 files modified correctly
- [ ] `UserDatabase` version still = 7
- [ ] `exportSchema = false` set
- [ ] Callback creates table on open
- [ ] Greek/Latin filtered in `insertNormalizationPatterns()`
- [ ] `normalizeText()` delegates Greek to `GreekNormalizer`
- [ ] All normalization call sites updated
- [ ] Tested fresh install
- [ ] Tested existing user upgrade
- [ ] Tested Hebrew import with patterns
- [ ] Tested Arabic import with patterns
- [ ] Tested Greek still works (uses old normalizer)
- [ ] Tested delete removes patterns
- [ ] No crashes, no errors
- [ ] README updated with Greek/Latin warning

---

## Conclusion

This implementation adds data-driven normalization support for **non-Greek/Latin languages only**, with:

- ✅ **No database version change** - Existing users unaffected
- ✅ **Greek unchanged** - Still uses `GreekNormalizer`
- ✅ **Latin unchanged** - No normalization
- ✅ **Hebrew/Arabic/others** - Use customizable pattern-based normalization
- ✅ **Backward compatible** - Table created automatically on first run
- ✅ **Safe upgrade** - User data preserved
- ✅ **Simple to use** - Just include `normalization_rules.csv` in dictionary ZIP

Total effort: **4-6 hours** for implementation and testing.
