# Classics Viewer - Android app for reading classical texts

Important: 
  Do not add, delete, or modify the contents of the folder "data-sources" in any way!
  The data-sources folder contains the cloned git repos for the following PerseusDL projects:
  canonical-greekLit  canonical-latinLit  canonical-pdlrefwk  perseus_catalog 

App has 100% local operation on phone; no internet access or other android permissions are required.

Takes inspiration from the Perseus Hopper and Scaife viewer web apps.

## CRITICAL: Database Schema and Room Compatibility

**EXTREMELY IMPORTANT**: When making ANY data structure changes:
1. **ALWAYS** fully analyze and validate that the database schema matches Room entities
2. **NEVER** make schema changes without checking ALL Room entity files in the Android app
3. **ALWAYS** verify column names, types, and constraints match exactly between:
   - The SQL schema used in data prep
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

## Play Asset Delivery Migration (Replaces OBB)

**IMPORTANT**: This app now uses Google Play Asset Delivery instead of OBB files.

### Goal: Fast-Follow Delivery
- **Production Goal**: Use fast-follow delivery type (downloads after app install)
- **Database Size**: 774MB uncompressed, 171MB compressed
- **Current Status**: Using install-time delivery for easier local testing

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
1. **`data-prep/perseus_texts.db`** - Source database
   - Created by `create_perseus_database.py`
   - Original uncompressed SQLite (774MB)
   - Never shipped with app

2. **`perseus_database/src/main/assets/perseus_texts.db.zip`** - Production asset pack
   - Compressed version (171MB)
   - For Play Asset Delivery via Google Play
   - Used in production releases

3. **`app/src/debug/assets/perseus_texts.db.zip`** - Debug fallback
   - Copy for local testing only
   - Included in debug APKs because bundletool doesn't work well locally
   - NOT included in release builds

4. **`/data/data/.../databases/perseus_texts.db`** - Final extracted database
   - On-device location after extraction
   - Full 774MB uncompressed database
   - Created on first app launch

### Why This Structure?
- **Modular**: Asset pack is a separate module for Play Store delivery
- **Dual approach**: Production uses Play Asset Delivery, debug uses APK assets
- **Compression**: Reduces download from 774MB to 171MB
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

## Quick Deployment Instructions

To rebuild and deploy the app from scratch:

```bash
# 1. Build the database (takes ~5 minutes)
cd data-prep
python3 create_perseus_database.py
# This creates perseus_texts.db and automatically:
# - Compresses it to perseus_texts.db.zip (774MB → 171MB)
# - Copies to perseus_database/src/main/assets/
cd ..

# 2. For debug builds (recommended for local testing):
cp perseus_database/src/main/assets/perseus_texts.db.zip app/src/debug/assets/
./gradlew installDebug
adb shell pm clear com.classicsviewer.app.debug

# 3. For production-like testing with bundletool:
./deploy_with_bundletool.sh
# This builds AAB and uses bundletool for deployment
```

### Important Notes:
- The database build creates a ~774MB SQLite file that gets compressed to ~171MB
- Debug builds include database in APK for easy local testing
- The `pm clear` command ensures the app starts fresh
- First launch extracts the database (takes ~6-7 seconds with progress dialog)
- Database location shown in Settings screen

### Troubleshooting:
- **"./gradlew: No such file or directory"**: Run `chmod +x gradlew` first
- **"adb: command not found"**: Ensure Android SDK platform-tools are in your PATH
- **App shows "Error"**: Check logs with `adb logcat | grep AssetPackDatabaseHelper`
- **No authors shown**: Force clear with `adb shell pm clear com.classicsviewer.app.debug`
- **Asset pack not found**: For local testing, use debug build method above



