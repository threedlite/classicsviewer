# Classics Viewer - Android app for reading classical texts

Always use venv to run python code.

Important: 
  Claude: Do not add, delete, or modify features not related to what is being worked on!  Investigate the impact of changes before making them. Avoid regressions. Test and verify fixes before declaring them fixed. Do not overstate effectiveness of changes without careful checking. BE PATIENT with database builds - sample takes 2-3 minutes, full takes 8-10 minutes. DO NOT assume builds are stuck just because they take time. The build may appear to pause at certain points (especially during translation lookup creation) but is still actively processing - check with `ps aux | grep python3` to verify it's still running. NEVER run multiple copies of create_perseus_database.py simultaneously as this will corrupt the database! If you see no new output for 30-60 seconds, that's NORMAL - the script is processing large data structures in memory. Always check db size and zip before packaging or deploying it. When you redeploy apk, clear app data, and uninstall the app first. Be sure you know what directory you are in before executing commands. Make sure you are in the right directory before running builds. Stick to facts, avoid unstubstantiated claims and opinions.
  Do not add, delete, or modify the contents of the folder "data-sources" in any way!
  The data-sources folder contains the cloned git repos for the following PerseusDL projects:
  canonical-greekLit  canonical-latinLit  canonical-pdlrefwk  perseus_catalog
Only build the apk with the sample db, not the full db, it is too large.
 

**CRITICAL: RUNNING LONG BUILDS IN CLAUDE - USE BACKGROUND EXECUTION**:

⚠️ **ATTENTION CLAUDE**: You have a 2-minute execution timeout. Commands that take longer must be run in the background!

**WHAT HAPPENS WITH DIRECT EXECUTION (WILL FAIL)**:
- ❌ `./gradlew bundleRelease` - takes 3-4 minutes, WILL timeout and create 0-byte AAB
- ❌ `python3 create_perseus_database.py` - takes 4+ minutes, WILL create corrupted database
- ❌ `zip` commands on large files - WILL create corrupt ZIPs

**CORRECT APPROACH - RUN IN BACKGROUND**:
```bash
# For gradle builds - Run in background:
nohup ./gradlew clean assembleDebug > build.log 2>&1 &
# Or for release builds:
nohup ./gradlew clean bundleRelease > aab_build.log 2>&1 &
# Monitor progress:
tail -f build.log
# Check completion:
ls -lah app/build/outputs/apk/debug/app-debug.apk

# For database creation - Run in background:
cd data-prep && nohup python3 create_perseus_database.py sample > build.log 2>&1 &
# Monitor with: tail -f build.log


# For any long-running command:
nohup [COMMAND] > output.log 2>&1 &
```

**CRITICAL GRADLE BUILD REQUIREMENT**:
- ⚠️ **ALWAYS use `clean` before building**: `./gradlew clean assembleDebug` or `./gradlew clean bundleRelease`
- **NEVER build without clean** - stale build artifacts can cause runtime issues
- Clean ensures all Kotlin files are recompiled and resources are properly regenerated

**CRITICAL DEPLOYMENT REQUIREMENT**:
- ⚠️ **ALWAYS deploy to phone after making code changes**
- After building, immediately uninstall and reinstall the app on the connected device
- This ensures you're testing the actual changes you made
- Standard deployment sequence:
  ```bash
  # 1. Build the app
  nohup ./gradlew clean assembleDebug > build.log 2>&1 &
  # 2. Wait for build to complete
  tail -f build.log  # Wait for "BUILD SUCCESSFUL"
  # 3. Deploy to phone
  adb uninstall com.classicsviewer.app.debug
  adb shell pm clear com.classicsviewer.app.debug
  adb install app/build/outputs/apk/debug/app-debug.apk
  ```

**KEY POINTS**:
- ✅ You CAN run any command using `nohup ... &` to run in background
- ✅ Use `tail -f` to monitor progress (can timeout safely)
- ✅ Check completion by looking for output files or success messages
- ✅ Be sure you know what subdirectory you are in before executing commands (e.g. data-prep, wikitionary-processing)
- ✅ The database build process run by create_perseus_database.py aims to be all-inclusive and repeatable, able to rebuild the database from scratch in one go.
- ❌ NEVER run commands that take >90 seconds in foreground.  This includes create_perseus_database.py.
- ❌ Do not add logic that will fail the data build pipeline silently - the build should fail for anything missing or other issues.
- ❌ **NEVER kill a running database build process and then deploy the incomplete database!** Always let builds complete fully or restart them properly.
- ❌ **CRITICAL: If a database build appears to hang, DO NOT KILL IT AND DEPLOY!** The build may still be processing. Wait for completion signals like "Database creation complete" or "Successfully created" in the log. If truly stuck, restart the entire build from scratch.
- ❌ **NEVER assume a database is complete just because the file size looks right!** The script may be performing final critical steps like index creation, integrity checks, or compression.
- ❌ **WAIT FOR THE ZIP FILE TO BE CREATED!** The build process ends with compressing the database to perseus_texts.db.zip. You MUST see "Compressing database to" followed by successful ZIP creation before the build is complete. The ZIP step is critical and can take 1-2 minutes.
- ❌ **NEVER use warnings for critical failures** - If a required component fails to load, FAIL THE BUILD with a clear error, don't print a warning and continue.

**REMEMBER**: Background execution (`nohup ... &`) bypasses the timeout limitation!

**CRITICAL APK BUILD REQUIREMENT**:
- **THE APK MUST NEVER BE BUILT WITHOUT THE SAMPLE DATABASE**
- The Gradle build has a `checkDatabaseExists` task that ensures `app/src/debug/assets/perseus_texts.db.zip` exists
- **THE BUILD WILL SUCCEED EVEN WITH A CORRUPTED DATABASE** - Always verify ZIP integrity!
- **COMMON ERROR**: "Database not found in APK" at runtime means the ZIP file is corrupted
- If database is missing, the build will fail with clear instructions
- **ALWAYS** verify the database ZIP is updated before deployment
- The database creation script (`create_perseus_database.py`) automatically places the compressed database in both:
  - `app/src/debug/assets/perseus_texts.db.zip` (for debug builds)
  - `app/src/main/assets/perseus_texts.db.zip` (for release builds)

App has 100% local operation on phone; no internet access or other android permissions are required.


## CRITICAL: Database Schema and Room Compatibility

**EXTREMELY IMPORTANT**: When making ANY data structure changes:
1. **ALWAYS** fully analyze and validate that the database schema matches Room entities
2. **NEVER** make schema changes without checking ALL Room entity files in the Android app
3. **ALWAYS** verify column names, types, and constraints match exactly between:
   - The SQL schema used in data prep, including indexes and not null constraints.  primary keys should never be nullable.
   - The Room entity annotations in the Android app
   - The DAO query expectations
4. **The app WILL CRASH** on startup after language selection if there's ANY mismatch

### Room Schema Validation Errors:
When you see `java.lang.IllegalStateException: Pre-packaged database has an invalid schema`, Room provides EXACT details:
- **Expected**: What Room wants based on entity definitions
- **Found**: What's actually in the database
- Pay attention to `notNull=true/false` differences - these MUST match exactly
- Check `defaultValue` differences - SQLite DEFAULTs don't translate to Room the same way

### Before Any Schema Changes:
1. Check all Room entities in `app/src/main/java/com/classicsviewer/app/database/entities/`
2. Verify all DAO interfaces in `app/src/main/java/com/classicsviewer/app/database/dao/`
3. Test with both test and full databases
4. When redeploying to phone, **FORCE RESTART** the app (don't just reinstall)
5. **CRITICAL**: After ANY database schema change:
   - Rebuild the database from scratch
   - Use `adb shell pm clear com.classicsviewer.app.debug` to clear old data
   - Check crash logs with `adb logcat | grep "Pre-packaged database"` for schema validation errors

### Common Schema Pitfalls:
- Column name mismatches (Room is case-sensitive)
- Missing indexes that Room expects
- Different column types (INTEGER vs TEXT)
- Missing or extra columns
- Primary key mismatches
- Foreign key constraint differences
- **AUTOINCREMENT makes columns nullable** - Room sees `INTEGER PRIMARY KEY AUTOINCREMENT` as nullable, use `INTEGER PRIMARY KEY NOT NULL` instead
- **SQLite DEFAULT values cause mismatches** - Room doesn't recognize DEFAULT constraints in the same way. Either:
  - Remove DEFAULT from SQL schema and handle defaults in Kotlin code
  - Or make the Room entity property nullable to match
- **Room validates EXACT schema match** - Even minor differences like nullable vs non-null will crash the app
- **Always test with pm clear** - Old databases can mask schema issues

### CRITICAL: Backwards Compatibility - Never Change Room Schema Versions

**IMPORTANT FOR FUTURE DEVELOPMENT**: To preserve existing user data and prevent crashes on app upgrades:

1. **NEVER increment Room database versions** for either PerseusDatabase or UserDatabase
2. **NEVER add or remove entities** from the `@Database` entities list
3. **NEVER change tracked table schemas** - any change will break existing installations
4. **DO use dynamic table creation** for new features:
   - Create new tables via SQL in RoomDatabase.Callback().onOpen()
   - Access new tables using raw SQL queries through helper classes (not Room DAOs)
   - Example: `normalization_patterns` table in UserDatabase
   - Pattern: Helper class with SupportSQLiteDatabase access, not Room entity

**Why this matters**: When users upgrade the app:
- Their existing databases remain on device (perseus_texts.db, user_data.db)
- Room validates schema hash against tracked entities
- Any mismatch = instant crash on app launch
- Version bumps require migrations which can fail or lose data

**Approved pattern for new tables**:
```kotlin
// In UserDatabase.kt - add callback, not entity
.addCallback(object : RoomDatabase.Callback() {
    override fun onOpen(db: SupportSQLiteDatabase) {
        super.onOpen(db)
        createNewTableIfNeeded(db)  // Create via SQL
    }
})

// Access via helper, not DAO
fun getNewTableHelper(context: Context): NewTableHelper {
    return NewTableHelper(getInstance(context).openHelper.writableDatabase)
}
```

## Play Asset Delivery

**IMPORTANT**: This app uses Google Play Asset Delivery for efficient database distribution.

### Goal: Fast-Follow Delivery
- **Production Goal**: Use fast-follow delivery type (downloads after app install)
- **Database Size**: 1.4GB uncompressed, 300MB compressed
- **Current Status**: Using install-time delivery for easier local testing

### CRITICAL: Database Size Limits and Multi-Part Strategy

**WARNING**: Always verify ZIP integrity with `unzip -t` before deployment. Corrupted ZIP files cause `Unexpected end of ZLIB input stream` errors during extraction.

### Key Components:

1. **Database Extraction Flow**:
   - App launches → MainActivity checks if DB exists
   - If not → Immediately launches DatabaseExtractionActivity
   - Extracts and decompresses database (~6-7 seconds)
   - Returns to MainActivity for language selection

Debug builds include database in APK assets
```bash
# Database is copied to debug assets:
cp perseus_database/src/main/assets/perseus_texts.db.zip app/src/debug/assets/
```

### Deployment Commands:

**For local testing (debug build)**:
```bash
./gradlew installDebug
# Database is included in APK, no separate asset pack needed
```

**For bundletool testing**:
```bash
./deploy_with_bundletool.sh
# Uses bundletool to simulate Play Store deployment
```

### Code Structure:
- **DatabaseExtractionActivity**: Shows progress during extraction
- **MainActivity**: Checks DB on launch, triggers extraction if needed

### Production Deployment:
1. Build AAB: `./gradlew bundleRelease`

## File Structure Explanation

### AndroidManifest.xml File:
1. **`app/src/main/AndroidManifest.xml`** - Main app manifest
   - Declares activities, permissions, app metadata
   - Standard Android app configuration


### Multiple Database Files:
1. **`data-prep/perseus_texts_sample.db`** - Sample database source
   - Created by `create_perseus_database.py sample`
   - Contains only authors from SAMPLE_AUTHORS.md
   - Smaller size for initial Play Store release

2. **`data-prep/perseus_texts_full.db`** - Full database source
   - Created by `create_perseus_database.py full`
   - Contains all ~100 Greek and Latin authors
   - Original uncompressed SQLite (1.4GB)
   - For local debugging and future release

3. **`data-prep/perseus_texts_extended.db`** - Extended database source
   - Created by `create_perseus_database.py extended`
   - Contains Perseus + 991 non-duplicate First1KGreek works
   - Original uncompressed SQLite (14GB)
   - For comprehensive Greek text coverage

4. **`/data/data/.../databases/perseus_texts.db`** - Final extracted database
   - On-device location after extraction
   - Uncompressed database from whichever version was deployed
   - Created on first app launch

## Interlinear Generation

### Running Interlinear Generation:

**CRITICAL**: ALWAYS use `run_interlinear_no_sleep.sh`. NEVER run without the no-sleep script as sleep delays waste hours of processing time.

```bash
# Always run from build_modules/generate_interlinear directory
cd build_modules/generate_interlinear

# For all Greek works (Perseus + First1K):
./run_interlinear_no_sleep.sh INTERLINEAR_ALL_GREEK_WITH_IDS.csv ../../perseus_texts_extended.db 8

# For all Latin works:
./run_latin_interlinear_no_sleep.sh INTERLINEAR_ALL_LATIN_WITH_IDS.csv ../../perseus_texts_full.db 8
```

### Interlinear Build Times (8 workers):
- **Greek (1,855 works, 3.05M lines)**: ~12.9 hours
- **Latin (230 works)**: ~15 seconds

Output location: `/Users/user1/git/classicsviewer/data-sources/classicsviewer_interlinear`

### Stopping Interlinear Generation:
**IMPORTANT**: Always use specific PIDs to stop processes, NOT `pkill`

```bash
# Step 1: Find all Python processes
ps aux | grep -E "interlinear|spawn_main|python" | grep -v grep

# Step 2: Kill specific PIDs (replace with actual PIDs from step 1)
kill -9 [PID1] [PID2] [PID3] ...

# Step 3: Verify all stopped
ps aux | grep python | grep -v grep
```

**Why**: `pkill` doesn't reliably catch all multiprocessing worker processes. Always identify PIDs first, then kill them explicitly.

## Translation Alignment System

### Background
Some Perseus texts (especially prose works) have translations that use section numbers rather than line numbers. For example, Aeschines' "Against Timarchus" has 866 lines but translations for 196 sections. The database creation process now automatically detects and fixes this alignment issue.

### How It Works
1. **During Import** (`create_perseus_database.py`):
   - Detects when translation segment numbers (e.g., 1-196) are much smaller than total lines (e.g., 866)
   - Creates a proportional mapping: each section covers `total_lines / num_sections` lines
   - Applies the mapping during translation import
   
2. **Detection Criteria**:
   - Max translation line number < 50% of total lines
   - Max translation line number equals number of segments (suggests section numbering)
   - Total lines > 2x max translation line number

3. **Example**: Aeschines "Against Timarchus"
   - Greek text: 866 lines
   - Translation: 196 sections
   - Mapping: Section 1 → Lines 1-4, Section 2 → Lines 5-8, etc.
   - Result: Full translation coverage across all 866 lines

### Bekker Numbering
**Bekker numbering** is a citation system used for Aristotle's works (and sometimes Plato's), based on the 1831 Berlin Academy edition by Immanuel Bekker. References use the format `[page][column][line]`, for example:
- `1447a8` = page 1447, column a, line 8
- `1450b12` = page 1450, column b, line 12

In Perseus texts, Bekker references appear as milestones in the XML and require special handling:
- The database creation process detects Bekker milestones and creates appropriate line mappings
- Translation segments using Bekker references are aligned to the corresponding line ranges
- This ensures proper synchronization between Greek text and translations in works like Aristotle's Poetics

Plato has its own numbering system as well.


## Translation Alignment Solution

### Universal Translation Lookup
The app now uses a `translation_lookup` table to handle all translation alignment patterns:

### How It Works
1. **During Database Creation**: A lookup table is built mapping every Greek line to its translation segments
2. **Pattern Detection**: Automatically detects and handles:
   - **Direct mapping**: Translation line numbers match Greek lines
   - **Offset translations**: Consistent offset between Greek and translation numbers
   - **Section-based**: Translation uses section numbers instead of line numbers
   - **Partial coverage**: Translation only covers part of the text
   - **Complex patterns**: Bekker numbering, Stephanus pagination, etc.

3. **Proximity Mapping**: For lines without direct translation, finds nearest segment within 100 lines
4. **Universal Query**: The app's DAO queries check both direct range overlap AND lookup table

### Benefits
- **Always finds translations**: Even with misaligned numbering systems
- **Handles all edge cases**: Bekker, sections, offsets, partial translations
- **No manual fixes needed**: Works generically for all texts
- **Fast lookups**: Indexed for performance

### Implementation
```sql
-- Enhanced translation query
SELECT DISTINCT ts.* FROM translation_segments ts
WHERE ts.book_id = :bookId 
AND (
    -- Original range-based lookup
    (ts.start_line <= :endLine AND (ts.end_line IS NULL OR ts.end_line >= :startLine))
    OR
    -- Lookup table based mapping
    EXISTS (
        SELECT 1 FROM translation_lookup tl 
        WHERE tl.book_id = :bookId 
        AND tl.segment_id = ts.id
        AND tl.line_number BETWEEN :startLine AND :endLine
    )
)
```

This ensures that when viewing any Greek text and swiping to translation view, the appropriate translation will be found regardless of the numbering scheme used.

## Occurrence Highlighting System

### Word Position-Based Highlighting
The app now highlights matching words in occurrence lists using precomputed word number positions:

### How It Works
1. **Database Storage**: The `words` table stores each word with its position number (1, 2, 3, etc.) within each line
   ```sql
   CREATE TABLE words (
       word TEXT NOT NULL,
       word_normalized TEXT NOT NULL,
       book_id TEXT NOT NULL,
       line_number INTEGER NOT NULL,
       word_position INTEGER NOT NULL  -- 1-based word number in line
   )
   ```

2. **Position Calculation**: During database creation, word positions are computed using:
   ```python
   for word_pos, word in enumerate(words, 1):  # 1-based indexing
   ```

3. **Highlighting Display**: When showing occurrences:
   - Retrieves matching words with their positions from database
   - Applies background color and bold styling to words at those positions
   - Uses yellow highlight for inverted mode, dark yellow for normal mode
   - Respects color inversion user setting

### Benefits
- **Accurate positioning**: Uses word numbers (1st, 2nd, 3rd word) not character positions
- **Fast rendering**: No runtime text analysis needed, uses precomputed data
- **Lemma-aware**: Highlights all forms of a lemma, not just exact matches
- **Visually clear**: Makes it easy to spot the searched term in context

## Database Creation Process

The database build uses a comprehensive morphological extraction pipeline from Wiktionary:

### Morphology Extraction Pipeline

The morphology extraction is handled automatically by `combine_all_ancient_greek_morphology.py`, which runs these scripts:

1. **One-Time Greek Pages Cache** (created only if missing):
   ```bash
   python3 wiktionary-processing/extract_all_greek_pages.py
   ```
   - Extracts ~124k Greek pages from English Wiktionary dump into 46MB cache
   - Subsequent scripts use this cache for fast lookups

2. **Morphology Extraction Scripts** (run automatically):
   - `extract_ancient_greek_conjugations.py` - Verb paradigms (~2 seconds)
   - `extract_ancient_greek_declensions.py` - Noun/adjective paradigms (~2 seconds)
   - `extract_all_ancient_greek_words_with_diacritics.py` - All words with diacritics (~3 seconds)
   - `extract_inflection_of_template.py` - Inflection mappings from English Wiktionary (~90 seconds)
   - `extract_declension_mappings.py` - Declension patterns from Greek Wiktionary (~100 seconds)

3. **Combined Output**:
   - Total morphology extraction time: ~3-4 minutes
   - Creates `ancient_greek_morphology_complete.json` with all combined data
   - Includes grave accent variants (e.g., πολλὰς → πολύς)

### Key Features
- **No Silent Failures**: Missing files cause immediate build failure
- **Direct Imports**: Uses Python imports instead of subprocess for better error handling
- **Fresh Generation**: All morphology files regenerated each build (except Greek pages cache)
- **Performance Optimized**: Set-based duplicate checking for O(n) performance

## Automated Deployment Instructions

**CRITICAL**: Database deployment is error-prone if done manually. Always use automated scripts.

### Database Build Modes

The database creation now supports three modes:
- **Sample Database** (`perseus_texts_sample.db`): Contains only authors from SAMPLE_AUTHORS.csv - for Play Store release
- **Full Database** (`perseus_texts_full.db`): Contains all ~100 Greek and Latin authors - for local debugging
- **Extended Database** (`perseus_texts_extended.db`): Full Perseus + 991 non-duplicate First1KGreek works - for Greek students

### Database Creation

Note: **Never, ever, EVER, add word-specific fixes!!!!!!!!**: Always use the most general solution possible that covers all cases.
Note: **No standalone Python scripts**: All functionality should be integrated into create_perseus_database.py, not separate files.

```bash
# Build both databases (sample + full, default)
cd data-prep
python3 create_perseus_database.py

# Build only sample database
python3 create_perseus_database.py sample

# Build only full database
python3 create_perseus_database.py full

# Build extended database (Perseus + First1KGreek)
python3 create_perseus_database.py extended
```

### Deployment Scripts

**IMPORTANT**: After any database schema changes, rebuild the database first:
```bash
cd data-prep && nohup python3 create_perseus_database.py sample > build.log 2>&1 &
# Monitor with: tail -f build.log
```

```bash
# Option 1: Deploy with existing database (verify ZIP is updated first!)
# - Uses existing database in perseus_database/src/main/assets/
# - Assumes app/src/debug/assets/perseus_texts.db.zip is valid
# - Will fail at runtime if database is corrupted
./deploy_simple.sh

# Option 2: Production-like testing with bundletool
# - Creates AAB with asset pack
# - Uses bundletool for deployment simulation
./deploy_with_bundletool.sh
```

### **CRITICAL DEPLOYMENT RULES**:

1. **ALWAYS UNINSTALL APP FIRST**: Use `adb uninstall com.classicsviewer.app.debug` before reinstalling
   - This ensures Room doesn't use cached schema validation
   - Prevents "Pre-packaged database has an invalid schema" errors after schema changes
2. **VERIFY DATABASE ZIP IS NEW**: After rebuilding database, check timestamp:
   ```bash
   ls -la app/src/debug/assets/perseus_texts.db.zip
   # Should show recent timestamp matching your database build
   ```
3. **Never manually copy database files** - the timestamps and versions get out of sync
4. **Always clear app data** after schema changes - Room caches schema validation
5. **Test immediately after deployment** - schema mismatches crash on startup
6. **TIMEOUT = CORRUPTION**: If any script times out during compression, the ZIP file is corrupted
7. **Always verify ZIP integrity**: Use `unzip -t` before deployment
8. **Database size check**: Extracted database should be ~1.4GB, not 4KB
9. **Never, ever, EVER, add word-specific fixes!!!!!!!!**: Always use the most general solution possible that covers all cases.
10. Don't create ad-hoc scripts for data fixes as one-offs.  Integrate into the main db creation flow so it happens in future runs also.

### Database Build Process
- **Sample database creation**: ~2-3 minutes (subset of authors from SAMPLE_AUTHORS.csv)
- **Full database creation**: ~4-5 minutes (100 Greek authors and 95 Latin authors)
- **Extended database creation**: ~24 minutes (Perseus + First1K + interlinear + all lexicons)
- Creates comprehensive translation lookup table for all texts
- **Schema validation**: Room expects exact match between SQLite and entity definitions

### Extended Mode Details
The extended mode includes non-duplicate works from the First1KGreek collection:
- **991 unique works** not in Perseus
- **391 total authors** (196 more than full mode)
- **1,849 total works** (nearly double the full mode)
- **2.8 million text lines**, **43.69 million words**
- **Database size**: 16.5GB uncompressed, 3.3GB compressed ZIP
- **Only 7% have English translations** - primarily for Greek students
- Works include: Byzantine texts, patristic writings, commentaries, scholiasts
- **Source tracking**: Database quality report shows `[Perseus]` or `[First1KGreek]` at work level

### Common Deployment Errors:

**Error: `Pre-packaged database has an invalid schema`**
- **Cause**: Database schema doesn't match Room entities
- **Solution**: Rebuild database and uninstall app before reinstalling
- **Prevention**: Always uninstall app first: `adb uninstall com.classicsviewer.app.debug`
- **Never**: Try to manually fix by copying files

**Error: `Unexpected end of ZLIB input stream`**  
- **Cause**: Corrupted ZIP file from incomplete compression
- **Verify**: Always test ZIP integrity with `unzip -t`


**Monitoring Progress During Deployment**:
- **Greek Authors**: Watch for `[XX/100] Processing` messages (takes ~2-3 minutes)
- **Latin Authors**: Look for `=== PROCESSING LATIN AUTHORS ===` marker
- **Critical ZIP Phase**: When you see `Compressing database to`, monitor closely with `ps aux | grep zip`
- **ZIP Completion**: Verify with `ls -la perseus_database/src/main/assets/perseus_texts.db.zip`
- **Final Verification**: Always run `unzip -t` before continuing

**Database Corruption Detection**:
- **Symptom**: `java.io.EOFException: Unexpected end of ZLIB input stream`
- **Symptom**: Database shows only 4096 bytes instead of ~1.4GB
- **Symptom**: Authors list is empty after successful app launch
- **Fix**: Delete corrupted ZIP, recreate with proper `cd data-prep && zip -9 ../perseus_database/src/main/assets/perseus_texts.db.zip perseus_texts.db`
- **Verify**: Always run `unzip -t` to check integrity before deployment

### Deployment Verification Checklist:

**Before launching the app, verify:**
1. `unzip -t perseus_database/src/main/assets/perseus_texts.db.zip` returns "OK"
2. ZIP file size matches expected (sample: ~150MB, full: ~300MB, extended: ~1.3GB)
3. Source database exists with expected size (sample: ~650MB, full: ~1.4GB, extended: ~5.5GB)
4. App launches without crash
5. Database extraction completes (watch for progress dialog)
6. Authors list shows 100+ Greek and Latin authors

**If any step fails, STOP and fix before proceeding**

### Common Troubleshooting:
- **"./gradlew: No such file or directory"**: Run `chmod +x gradlew` first
- **"adb: command not found"**: Ensure Android SDK platform-tools are in your PATH  
- **Schema crash on startup**: Use `adb logcat | grep "Pre-packaged database"` - schema mismatch
- **ZIP extraction fails**: Check `adb logcat | grep "EOFException"` - corrupted ZIP file
- **Empty authors list**: Database is 4KB stub - ZIP corruption during build
- **App stuck on splash**: Clear data with `adb shell pm clear com.classicsviewer.app.debug`

### Directory Structure Reference:
- **Source database**: `data-prep/perseus_texts.db` (1.4GB uncompressed)
- **Device database**: `/data/data/.../databases/perseus_texts.db` (1.4GB extracted)



