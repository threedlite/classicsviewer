# User Dictionary Import Feature Design

## Overview
This feature allows users to import a custom dictionary from a ZIP file containing two CSV files to supplement the built-in dictionaries (LSJ, Cunliffe, Wiktionary) and morphology data. Only one custom dictionary package can be active at a time, similar to the audio import feature. The imported entries will be displayed **before** the existing sources when looking up words, giving priority to user-provided definitions and lemmatizations. This enables users to add a specialized lexicon and morphology that takes precedence over built-in data.

## Architecture

### Database Design

#### On-Demand Table Creation
Following the pattern of bookmarks, user dictionary data will be stored in the existing `UserDatabase` (user_data.db), separate from the main Perseus database. Two tables will be created on-demand when first needed (no migration required):

```sql
-- Table for user-provided dictionary entries (lemmas with definitions)
CREATE TABLE user_dictionary_lemmas (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    lemma TEXT NOT NULL,
    lemma_normalized_ultra TEXT,
    language TEXT NOT NULL CHECK (language IN ('greek', 'latin')),
    definition_plain TEXT NOT NULL,
    definition_html TEXT,
    source_name TEXT NOT NULL DEFAULT 'User Import',
    import_file_name TEXT NOT NULL,
    import_date INTEGER NOT NULL,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

-- Table for user-provided inflected form mappings
CREATE TABLE user_lemma_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    word_form TEXT NOT NULL,
    word_form_normalized_ultra TEXT,
    lemma TEXT NOT NULL,
    lemma_normalized_ultra TEXT,
    morph_info TEXT,  -- e.g., "2 s pres actv impr"
    confidence REAL DEFAULT 1.0,
    language TEXT NOT NULL CHECK (language IN ('greek', 'latin')),
    source_name TEXT NOT NULL DEFAULT 'User Import',
    import_file_name TEXT NOT NULL,
    import_date INTEGER NOT NULL,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

-- Indexes for performance
CREATE INDEX idx_user_dict_lemma 
    ON user_dictionary_lemmas(lemma, language);
    
CREATE INDEX idx_user_dict_lemma_ultra 
    ON user_dictionary_lemmas(lemma_normalized_ultra, language);
    
CREATE INDEX idx_user_lemma_form 
    ON user_lemma_mappings(word_form, language);
    
CREATE INDEX idx_user_lemma_form_ultra 
    ON user_lemma_mappings(word_form_normalized_ultra, language);
```

### ZIP Package Format Specification

The import package must be a ZIP file containing exactly two CSV files:

1. **dictionary.csv** - Dictionary entries (lemmas with definitions)
2. **morphology.csv** - Inflected form to lemma mappings

#### Dictionary CSV Format

##### Required Columns
- `lemma` - The dictionary form of the word (e.g., "λόγος", "homo")
- `language` - Either "greek" or "latin" 
- `definition` - Plain text definition

##### Optional Columns
- `source_name` - Name of the dictionary/source (defaults to "User Import")
- `html_definition` - HTML-formatted definition (if not provided, plain text will be used)

##### Example dictionary.csv:
```csv
lemma,language,definition,html_definition,source_name
ἀείδω,greek,"Etymology: compare the morphological problems with ἀείρω
I. to sing; to twang; to whistle; to ring (Il., Od., Mosch., Theocr.)
II.
1. to sing, chant; to sing in one's praise; to be sung (Hom., Od., Hdt., Xen.)
2. to sing, praise","<div class='definition'>Etymology: compare the morphological problems with ἀείρω<br/>I. to sing; to twang; to whistle; to ring (Il., Od., Mosch., Theocr.)<br/>II.<br/>1. to sing, chant; to sing in one's praise; to be sung (Hom., Od., Hdt., Xen.)<br/>2. to sing, praise</div>","Custom entry"
λόγος,greek,"word, speech, divine utterance",,"Custom entry"
τέχνη,greek,"art, skill, craft",,"Custom entry"
homo,latin,"human being, man",,"Custom entry"
```

#### Morphology CSV Format

##### Required Columns
- `word_form` - The inflected form (e.g., "ἄειδε", "λόγων")
- `lemma` - The dictionary form it maps to
- `language` - Either "greek" or "latin"

##### Optional Columns
- `morph_info` - Morphological tags (e.g., "2 s pres actv impr", "gen pl")
- `confidence` - Confidence score 0.0-1.0 (defaults to 1.0)
- `source_name` - Name of the source (defaults to "User Import")

##### Example morphology.csv:
```csv
word_form,lemma,morph_info,language,confidence,source_name
ἄειδε,ἀείδω,"2 s pres actv impr",greek,1.0,"Custom entry"
λόγων,λόγος,"gen pl",greek,1.0,"Custom entry"
λόγοις,λόγος,"dat pl",greek,0.95,"Custom entry"
homines,homo,"nom pl",latin,1.0,"Custom entry"
```

### Import Process

#### File Handling
1. **Only `.zip` files are supported** (must contain both dictionary.csv and morphology.csv)
2. UTF-8 encoding required for both CSV files
3. Validate ZIP structure and CSV formats before import

#### Import Flow (Following Manage Audio Pattern)
1. User selects "Manage Dictionary" from dictionary screen menu
2. Screen shows current dictionary status (if any)
3. User taps "Select Dictionary" or "Change Dictionary" button
4. File picker launches (accepts .zip only)
5. ZIP validation:
   - Verify ZIP contains exactly `dictionary.csv` and `morphology.csv`
   - Extract and validate both CSV files
   - Verify UTF-8 encoding
   - Validate required columns exist in each
   - Check language values are valid
   - Ensure lemmas in morphology.csv have corresponding entries in dictionary.csv (warning if missing)
6. Import process:
   - If replacing: Clear existing entries from both tables first
   - Store ZIP filename as identifier
   - Process dictionary entries first, then morphology mappings
   - Normalize Greek text for ultra-normalized search
   - Show progress indicator for both phases
   - Show toast with "Dictionary imported successfully"
7. Screen updates to show new dictionary as active
8. "Remove Dictionary" button appears for clearing custom content

### Integration with Existing Dictionary System

#### Modified Repository Methods

##### Lemmatization Process
Update `PerseusRepository.getLemmaForWord()` to check user mappings first:

```kotlin
suspend fun getLemmaForWord(word: String, language: String): LemmaResult {
    // FIRST: Check user-provided lemma mappings
    val userMapping = userDatabase.userLemmaMappingDao()
        .getMappingForWord(word, normalizedWord, language)
    
    if (userMapping != null) {
        return LemmaResult(
            lemma = userMapping.lemma,
            confidence = userMapping.confidence,
            morphInfo = userMapping.morphInfo,
            source = "User: ${userMapping.sourceName}"
        )
    }
    
    // THEN: Fall back to built-in lemma_map
    // ... existing code ...
}
```

##### Dictionary Lookup
Update `PerseusRepository.getAllDictionaryEntries()` to query user dictionary first:

```kotlin
suspend fun getAllDictionaryEntries(lemma: String, language: String): DictionaryResultMultiple {
    val entries = mutableListOf<DictionaryEntry>()
    
    // FIRST: Get user dictionary entries for this lemma (highest priority)
    val userEntries = userDatabase.userDictionaryDao()
        .getEntriesForLemma(lemma, normalizedLemma, language)
    
    for (entry in userEntries) {
        entries.add(DictionaryEntry(
            lemma = entry.lemma,
            definition = entry.definitionHtml ?: entry.definitionPlain,
            isDirectMatch = true,
            confidence = 1.0,
            source = "User: ${entry.sourceName}",
            isUserEntry = true
        ))
    }
    
    // THEN: Add built-in dictionary entries
    // ... existing code for main dictionaries ...
    
    // Sort with user entries FIRST
    val sortedEntries = entries.sortedWith(compareBy(
        { entry ->
            when {
                entry.isUserEntry -> 0  // User entries come FIRST
                entry.source?.contains("LSJ") == true -> 1
                entry.source?.contains("Cunliffe") == true -> 2
                entry.source?.contains("Wiktionary") == true -> 3
                else -> 4
            }
        },
        { entry -> entry.lemma.length }
    ))
}
```

### User Interface

#### Import Management Screen (UserDictionaryImportActivity)
Following the "Manage Audio" screen pattern exactly:
- Toolbar with back button and title "Manage Dictionary"
- Current dictionary status:
  - If active: Shows "Current dictionary: [filename.zip]" with counts
    - "X dictionary entries, Y morphology mappings"
  - If no dictionary: Shows "No custom dictionary selected"
- Single button that changes based on state:
  - "Select Dictionary ZIP" when no dictionary is active
  - "Change Dictionary ZIP" when a dictionary is already active
- "Remove Dictionary" button (only visible when dictionary is active)
- Simple, clean interface matching audio management

#### Dictionary Display Changes
- User entries shown FIRST with distinctive styling:
  - Different background color (subtle green tint for active user content)
  - "User: [Source Name]" label
  - Slightly larger font to emphasize user content
- No maximum limit on user entries (user content takes priority)

#### Settings Integration
New menu option in Dictionary screen:
- "Manage Dictionary" option in overflow menu (similar to "Manage Audio")
- Opens the dictionary management screen

### Data Management

#### Import Validation
- **Dictionary entries**: Reject entries with empty lemma or definition
- **Morphology mappings**: Reject entries with empty word_form or lemma
- Auto-detect language if not specified (based on script)
- Sanitize HTML content if provided
- Warn if morphology references lemmas not in dictionary

#### File Management
- Only one dictionary ZIP package can be active at a time
- Importing a new ZIP replaces all previous entries
- Removing the dictionary clears all entries from both tables

### Implementation Components

#### New Classes
1. `UserDictionaryLemmaEntity.kt` - Room entity for dictionary entries
2. `UserLemmaMappingEntity.kt` - Room entity for morphology mappings
3. `UserDictionaryDao.kt` - DAO interface for dictionary operations
4. `UserLemmaMappingDao.kt` - DAO interface for morphology operations
5. `UserDictionaryImportActivity.kt` - Import UI
6. `UserDictionaryViewModel.kt` - Business logic
7. `DictionaryZipParser.kt` - ZIP extraction and CSV parsing
8. `UserDictionaryRepository.kt` - Data operations

#### Modified Classes
1. `UserDatabase.kt` - Add new entities and DAOs
2. `PerseusRepository.kt` - Include user entries in lemmatization and dictionary lookup (prioritized)
3. `DictionaryActivity.kt` - Display user entries first
4. `menu_dictionary.xml` - Add "Manage Dictionary" option

### Error Handling

#### Import Errors
- Missing CSV files in ZIP → "ZIP must contain dictionary.csv and morphology.csv"
- Invalid CSV format → Show specific column errors for each file
- Encoding issues → Suggest UTF-8 conversion
- Large file → Process in batches automatically
- Orphaned morphology entries → Warning: "X morphology entries reference undefined lemmas"
- Duplicate entries → Show count of skipped items

#### Runtime Errors
- Database errors → Rollback transaction for both tables
- Memory issues → Process in chunks of 100 entries
- Malformed entries → Skip and log with line numbers

### Performance Considerations

1. **Batch Processing**: Import in chunks of 100 entries
2. **Indexing**: Create indexes after bulk import
3. **Caching**: Cache user dictionary entries in memory

### Security Considerations

1. **Input Sanitization**: Clean all HTML content
2. **File Validation**: Check file headers for actual CSV
3. **SQL Injection**: Use parameterized queries only

### Testing Strategy

1. **Unit Tests**:
   - CSV parser with various formats
   - Ultra-normalization for Greek text
   - Duplicate detection logic

2. **Integration Tests**:
   - Import flow with real database
   - Search integration with mixed sources
   - Batch deletion

3. **UI Tests**:
   - File picker interaction
   - Progress indication
   - Error message display

### Table Creation

The tables will be created on-demand when first accessed (no migration needed):

```kotlin
// In UserDictionaryRepository
fun ensureTablesExist(database: SupportSQLiteDatabase) {
    // Create dictionary lemmas table
    database.execSQL("""
        CREATE TABLE IF NOT EXISTS user_dictionary_lemmas (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            lemma TEXT NOT NULL,
            lemma_normalized_ultra TEXT,
            language TEXT NOT NULL,
            definition_plain TEXT NOT NULL,
            definition_html TEXT,
            source_name TEXT NOT NULL DEFAULT 'User Import',
            import_file_name TEXT NOT NULL,
            import_date INTEGER NOT NULL,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            CHECK (language IN ('greek', 'latin'))
        )
    """)
    
    // Create morphology mappings table
    database.execSQL("""
        CREATE TABLE IF NOT EXISTS user_lemma_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            word_form TEXT NOT NULL,
            word_form_normalized_ultra TEXT,
            lemma TEXT NOT NULL,
            lemma_normalized_ultra TEXT,
            morph_info TEXT,
            confidence REAL DEFAULT 1.0,
            language TEXT NOT NULL,
            source_name TEXT NOT NULL DEFAULT 'User Import',
            import_file_name TEXT NOT NULL,
            import_date INTEGER NOT NULL,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            CHECK (language IN ('greek', 'latin'))
        )
    """)
    
    // Create indexes for dictionary
    database.execSQL("""
        CREATE INDEX IF NOT EXISTS idx_user_dict_lemma 
        ON user_dictionary_lemmas(lemma, language)
    """)
    
    database.execSQL("""
        CREATE INDEX IF NOT EXISTS idx_user_dict_lemma_ultra 
        ON user_dictionary_lemmas(lemma_normalized_ultra, language)
    """)
    
    // Create indexes for morphology
    database.execSQL("""
        CREATE INDEX IF NOT EXISTS idx_user_lemma_form 
        ON user_lemma_mappings(word_form, language)
    """)
    
    database.execSQL("""
        CREATE INDEX IF NOT EXISTS idx_user_lemma_form_ultra 
        ON user_lemma_mappings(word_form_normalized_ultra, language)
    """)
}
```


## Appendix: Sample Implementation Snippets

### UserDictionaryDao.kt
```kotlin
@Dao
interface UserDictionaryDao {
    @Query("""
        SELECT * FROM user_dictionary_lemmas 
        WHERE (lemma = :lemma OR lemma_normalized_ultra = :normalizedLemma) 
        AND language = :language
    """)
    suspend fun getEntriesForLemma(
        lemma: String, 
        normalizedLemma: String, 
        language: String
    ): List<UserDictionaryLemmaEntity>
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertLemmas(entries: List<UserDictionaryLemmaEntity>)
    
    @Query("DELETE FROM user_dictionary_lemmas")
    suspend fun deleteAllLemmas()
    
    @Query("SELECT COUNT(*) FROM user_dictionary_lemmas WHERE language = :language")
    suspend fun getLemmaCount(language: String): Int
}
```

### UserLemmaMappingDao.kt
```kotlin
@Dao
interface UserLemmaMappingDao {
    @Query("""
        SELECT * FROM user_lemma_mappings 
        WHERE (word_form = :word OR word_form_normalized_ultra = :normalizedWord) 
        AND language = :language
        ORDER BY confidence DESC
        LIMIT 1
    """)
    suspend fun getMappingForWord(
        word: String, 
        normalizedWord: String, 
        language: String
    ): UserLemmaMappingEntity?
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMappings(mappings: List<UserLemmaMappingEntity>)
    
    @Query("DELETE FROM user_lemma_mappings")
    suspend fun deleteAllMappings()
    
    @Query("SELECT COUNT(*) FROM user_lemma_mappings WHERE language = :language")
    suspend fun getMappingCount(language: String): Int
}
```

### DictionaryZipParser.kt
```kotlin
class DictionaryZipParser {
    fun parseZipFile(zipFile: File): DictionaryImportData {
        val result = DictionaryImportData()
        
        ZipFile(zipFile).use { zip ->
            // Extract and parse dictionary.csv
            val dictEntry = zip.getEntry("dictionary.csv") 
                ?: throw IllegalArgumentException("Missing dictionary.csv")
            zip.getInputStream(dictEntry).use { stream ->
                result.lemmas = parseDictionaryCSV(stream)
            }
            
            // Extract and parse morphology.csv
            val morphEntry = zip.getEntry("morphology.csv")
                ?: throw IllegalArgumentException("Missing morphology.csv")
            zip.getInputStream(morphEntry).use { stream ->
                result.mappings = parseMorphologyCSV(stream)
            }
        }
        
        // Validate cross-references
        val lemmaSet = result.lemmas.map { it.lemma }.toSet()
        val orphanedMappings = result.mappings.filter { it.lemma !in lemmaSet }
        if (orphanedMappings.isNotEmpty()) {
            // Log warning about orphaned mappings
        }
        
        return result
    }
}
```
