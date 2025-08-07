# Classics Viewer - Android app for reading classical texts

Important: 
  Do not add, delete, or modify the contents of the folder "data-sources" in any way!
  The data-sources folder contains the cloned git repos for the following PerseusDL projects:
  canonical-greekLit  canonical-latinLit  canonical-pdlrefwk  perseus_catalog 

**CRITICAL SCRIPT TIMEOUT HANDLING**:
- **NEVER** assume a script was successful just because it timed out
- If a long-running script times out (like database creation), run it in background:
  ```bash
  ./deploy_complete.sh > deploy.log 2>&1 &
  # Monitor with: tail -f deploy.log
  ```
- Always verify completion by checking output files, timestamps, and success messages
- Database creation takes ~4 minutes and will timeout at 5 minutes - this is normal
- Only continue deployment if you can verify the script actually completed successfully

App has 100% local operation on phone; no internet access or other android permissions are required.

Takes inspiration from the Perseus Hopper and Scaife viewer web apps.

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

## Play Asset Delivery

**IMPORTANT**: This app uses Google Play Asset Delivery for efficient database distribution.

### Goal: Fast-Follow Delivery
- **Production Goal**: Use fast-follow delivery type (downloads after app install)
- **Database Size**: 1.4GB uncompressed, 300MB compressed
- **Current Status**: Using install-time delivery for easier local testing

### CRITICAL: Database Size Limits and Multi-Part Strategy

**Play Asset Delivery has a 512MB limit per asset pack**. When the compressed database exceeds ~450MB, it MUST be split into multiple parts:

1. **Current Setup**: Single 300MB ZIP file works for debug/testing
2. **Future Scaling**: As database grows, use `build_multipart_database.sh`
3. **Multi-part Process**:
   - Creates `perseus_database_part1`, `perseus_database_part2`, etc. modules
   - Each part stays under 450MB (safe margin)
   - App code uses `MultiPartAssetPackDatabaseHelper` to reassemble
   - Parts are downloaded as separate fast-follow asset packs

### When to Switch to Multi-Part:
- If `perseus_database/src/main/assets/perseus_texts.db.zip` exceeds 450MB
- Run `./build_multipart_database.sh` instead of single-file approach
- Update `settings.gradle` to include all part modules
- Switch app code from `AssetPackDatabaseHelper` to `MultiPartAssetPackDatabaseHelper`

**WARNING**: Always verify ZIP integrity with `unzip -t` before deployment. Corrupted ZIP files cause `Unexpected end of ZLIB input stream` errors during extraction.

### Key Components:
1. **Asset Pack Module**: `perseus_database`
   - Contains compressed database: `perseus_texts.db.zip`
   - Manifest location: `perseus_database/src/main/AndroidManifest.xml`
   - Change delivery type to `<dist:fast-follow />` for production

2. **Database Extraction Flow**:
   - App launches → MainActivity checks if DB exists
   - If not → Immediately launches DatabaseExtractionActivity
   - Extracts and decompresses database (~6-7 seconds)
   - Returns to MainActivity for language selection

### Local Testing Challenge & Solution:

**Problem**: Bundletool with `--local-testing` doesn't properly support asset packs
- Asset packs aren't accessible via AssetPackManager API
- Fast-follow packs behave as on-demand in local testing

**Solution**: Debug builds include database in APK assets
```bash
# Database is copied to debug assets:
cp perseus_database/src/main/assets/perseus_texts.db.zip app/src/debug/assets/
```

**How it works**:
- AssetPackDatabaseHelper detects debug builds
- Falls back to extracting from APK assets instead of asset pack
- Allows seamless local testing without asset pack infrastructure

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
- **AssetPackDatabaseHelper**: Handles both asset pack and debug fallback
- **DatabaseExtractionActivity**: Shows progress during extraction
- **MainActivity**: Checks DB on launch, triggers extraction if needed

### Production Deployment:
1. Change to fast-follow in `perseus_database/src/main/AndroidManifest.xml`
2. Build AAB: `./gradlew bundleRelease`
3. Upload to Play Console - asset pack will be handled automatically

## File Structure Explanation

### Multiple AndroidManifest.xml Files:
1. **`app/src/main/AndroidManifest.xml`** - Main app manifest
   - Declares activities, permissions, app metadata
   - Standard Android app configuration

2. **`perseus_database/src/main/AndroidManifest.xml`** - Asset pack manifest
   - Separate module for Play Asset Delivery
   - Declares delivery type (install-time/fast-follow/on-demand)
   - Contains: `<dist:delivery><dist:install-time /></dist:delivery>`

### Multiple Database Files:
1. **`data-prep/perseus_texts_sample.db`** - Sample database source
   - Created by `create_perseus_database.py sample`
   - Contains only authors from SAMPLE_AUTHORS.md
   - Smaller size for initial Play Store release
   - Never shipped directly with app

2. **`data-prep/perseus_texts_full.db`** - Full database source  
   - Created by `create_perseus_database.py full`
   - Contains all ~100 Greek and Latin authors
   - Original uncompressed SQLite (1.4GB)
   - For local debugging and future release

3. **`perseus_database/src/main/assets/perseus_texts.db.zip`** - Production asset pack
   - Compressed version of sample database
   - For Play Asset Delivery via Google Play
   - Used in production releases
   - Note: Always named `perseus_texts.db.zip` for app compatibility

4. **`app/src/debug/assets/perseus_texts.db.zip`** - Debug fallback
   - Copy for local testing only
   - Included in debug APKs because bundletool doesn't work well locally
   - NOT included in release builds

5. **`/data/data/.../databases/perseus_texts.db`** - Final extracted database
   - On-device location after extraction
   - Uncompressed database from whichever version was deployed
   - Created on first app launch

### Why This Structure?
- **Modular**: Asset pack is a separate module for Play Store delivery
- **Dual approach**: Production uses Play Asset Delivery, debug uses APK assets
- **Compression**: Reduces download from 1.4GB to 300MB
- **Local testing**: Debug fallback avoids bundletool limitations

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

The database build uses pre-extracted Wiktionary data for morphological analysis:

### Wiktionary Data Pipeline
1. **Greek Pages Extraction** (if regenerating from scratch):
   ```bash
   python3 wiktionary-processing/extract_all_greek_pages.py
   ```
   - Extracts ~124k Greek pages from 1.4GB Wiktionary dump into 46MB cache
   - All subsequent scripts use this cache for efficiency

2. **Pre-extracted Files Used**:
   - `greek_inflection_of_mappings.json` - 15,592 inflection mappings
   - `ancient_greek_declension_mappings.json` - 37,119 declension patterns
   - `ancient_greek_all_morphology_correct.json` - Complete morphological data

## Automated Deployment Instructions

**CRITICAL**: Database deployment is error-prone if done manually. Always use automated scripts.

### Database Build Modes

The database creation now supports two modes:
- **Sample Database** (`perseus_texts_sample.db`): Contains only authors from SAMPLE_AUTHORS.md - for Play Store release
- **Full Database** (`perseus_texts_full.db`): Contains all ~100 Greek and Latin authors - for local debugging

### Database Creation

```bash
# Build both databases (default)
cd data-prep
python3 create_perseus_database.py

# Build only sample database
python3 create_perseus_database.py sample

# Build only full database  
python3 create_perseus_database.py full
```

### Deployment Scripts (Fully Automated)

```bash
# Option 1: Deploy sample database (for Play Store release)
# - Rebuilds sample database from scratch
# - Creates fresh compressed database
# - Deploys and clears app data
./deploy_complete.sh

# Option 2: Deploy full database (for local debugging)
# - Rebuilds full database from scratch
# - Deploys with all authors for testing
./deploy_full_database.sh

# Option 3: Deploy with existing database (faster, but dangerous if schema changed)
# - Uses existing database in perseus_database/src/main/assets/
# - Only use if you're certain database is current
./deploy_simple.sh

# Option 4: Production-like testing with bundletool
# - Creates AAB with asset pack
# - Uses bundletool for deployment simulation
./deploy_with_bundletool.sh
```

### **CRITICAL DEPLOYMENT RULES**:

1. **After ANY schema changes**: ALWAYS use `./deploy_complete.sh`
2. **Never manually copy database files** - the timestamps and versions get out of sync
3. **Always clear app data** after schema changes - Room caches schema validation
4. **Test immediately after deployment** - schema mismatches crash on startup
5. **TIMEOUT = CORRUPTION**: If any script times out during compression, the ZIP file is corrupted
6. **Always verify ZIP integrity**: Use `unzip -t` before deployment
7. **Database size check**: Extracted database should be ~1.4GB, not 4KB

### Database Build Process
- **Full database creation**: ~4 minutes
- Processes 100 Greek authors and 95 Latin authors
- Creates comprehensive translation lookup table for all texts
- **Schema validation**: Room expects exact match between SQLite and entity definitions

### Common Deployment Errors:

**Error: `Pre-packaged database has an invalid schema`**
- **Cause**: Database schema doesn't match Room entities
- **Solution**: Use `./deploy_complete.sh` to rebuild everything from scratch
- **Never**: Try to manually fix by copying files

**Error: `Unexpected end of ZLIB input stream`**  
- **Cause**: Corrupted ZIP file from incomplete compression
- **Solution**: Use `./deploy_complete.sh` to recreate compression
- **Verify**: Always test ZIP integrity with `unzip -t`

**Script Timeout Issue**:
- **Problem**: `./deploy_complete.sh` times out during 4-minute database rebuild
- **Solution**: Run in background: `./deploy_complete.sh > deploy.log 2>&1 &`
- **Monitor**: Watch progress with `tail -f deploy.log`
- **Check completion**: Look for "DEPLOYMENT COMPLETE!" message
- **CRITICAL**: If script times out during `zip` command, the ZIP file is corrupted and unusable

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
2. ZIP file size is ~300MB (not tiny or huge)
3. Source database `data-prep/perseus_texts.db` exists and is ~1.4GB
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
- **Asset pack ZIP**: `perseus_database/src/main/assets/perseus_texts.db.zip` (300MB compressed)  
- **Debug fallback**: `app/src/debug/assets/perseus_texts.db.zip` (copy of asset pack for local testing)
- **Device database**: `/data/data/.../databases/perseus_texts.db` (1.4GB extracted)



