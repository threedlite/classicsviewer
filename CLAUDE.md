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

## CRITICAL: Debug vs Release OBB Deployment

**EXTREMELY IMPORTANT**: Debug builds look for OBB files with `.debug` suffix!

### When deploying debug builds:
1. The app package name is `com.classicsviewer.app.debug` (note the `.debug` suffix)
2. The OBB must be at: `/storage/emulated/0/Android/obb/com.classicsviewer.app.debug/main.1.com.classicsviewer.app.debug.obb`
3. If you only have the release OBB, copy it to the debug location:
   ```bash
   adb shell mkdir -p /storage/emulated/0/Android/obb/com.classicsviewer.app.debug/
   adb shell cp /storage/emulated/0/Android/obb/com.classicsviewer.app/main.1.com.classicsviewer.app.obb \
                /storage/emulated/0/Android/obb/com.classicsviewer.app.debug/main.1.com.classicsviewer.app.debug.obb
   ```

### To avoid this issue:
- Always check the logs for which OBB path the app is looking for
- Debug builds ALWAYS add `.debug` suffix to package names and OBB paths
- After copying OBB, force stop and restart the app for clean database extraction

### IMPORTANT: APK and OBB Deployment
**When reinstalling the APK, you MUST also reinstall the OBB file!**
- Android cleans up the OBB directory when uninstalling an app
- The OBB file is the uncompressed SQLite database (not a ZIP)
- After `adb install`, always push the OBB:
  ```bash
  adb shell mkdir -p /storage/emulated/0/Android/obb/com.classicsviewer.app.debug/
  adb push data-prep/output/main.1.com.classicsviewer.app.debug.obb /storage/emulated/0/Android/obb/com.classicsviewer.app.debug/
  ```
- **CRITICAL**: Even if you only update the APK code (not the database), you still need to redeploy the OBB because `adb uninstall` removes it!

### How the OBB Database System Works
1. **OBB File Format**: The OBB file is a compressed ZIP containing the SQLite database
   - Created by zipping the database: `zip -9 main.1.com.classicsviewer.app.debug.obb perseus_texts.db`
   - Compressed size: ~173MB (78% reduction from 786MB)
   - The ZIP must contain `perseus_texts.db` as the root entry
   
2. **Database Extraction Process**:
   - On first launch after language selection, the app extracts the database from the compressed OBB
   - From: `/storage/emulated/0/Android/obb/com.classicsviewer.app.debug/main.1.com.classicsviewer.app.debug.obb`
   - To: `/data/data/com.classicsviewer.app.debug/databases/perseus_texts.db`
   - Shows a progress dialog during extraction (takes ~2 seconds)
   - The app automatically detects if the OBB is compressed (ZIP) or uncompressed (raw SQLite)
   
3. **Creating OBB Files**:
   ```bash
   cd data-prep/output
   # For compressed OBB (recommended):
   zip -9 main.1.com.classicsviewer.app.debug.obb perseus_texts.db
   
   # For release:
   zip -9 main.1.com.classicsviewer.app.obb perseus_texts.db
   ```
   
4. **Common Issues**:
   - If extraction fails, check:
     - OBB is a valid ZIP file: `file main.1.com.classicsviewer.app.debug.obb` should show "Zip archive data"
     - ZIP contains perseus_texts.db: `unzip -l main.1.com.classicsviewer.app.debug.obb`
     - NOT a ZIP of a ZIP (common mistake)
   - If no authors show after deployment, check:
     - Language selection in preferences (`adb shell pm clear` forces re-selection)
     - Database extracted successfully to internal storage
     - OBB file exists and is readable
   - The Settings screen shows the OBB path and size for debugging

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

### Manual Fix (if needed)
If translations aren't properly aligned after import:
```bash
cd data-prep
python3 fix_alignment_post_import.py
```

This script:
- Creates a backup of the database
- Identifies texts with alignment issues
- Applies proportional mapping to fix them
- Reports which texts were fixed



