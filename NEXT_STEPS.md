# NEXT STEPS - Multi-Part Database Implementation

## Current Status

### What's Been Done
1. **Analysis Complete**: Determined that adding all ~100 Greek authors will result in a 1.0-1.2GB compressed database (6-7x current size)
2. **Solution Designed**: Created binary splitting approach to divide database across multiple 450MB asset packs
3. **Implementation Created**:
   - `data-prep/split_database_for_assets.py` - Splits compressed DB into chunks
   - `MultiPartAssetPackDatabaseHelper.kt` - Handles multi-part download and assembly
   - `MultiPartDatabaseExtractionActivity.kt` - UI for extraction progress
   - `build_multipart_database.sh` - Automates the build process
4. **Documentation Written**:
   - `docs/database-expansion-analysis.md` - Impact analysis
   - `docs/multipart-database-deployment.md` - Complete implementation guide

### What Needs To Be Done

## 1. Update Database Creation Script (PRIORITY: HIGH)

The `data-prep/create_perseus_database.py` currently only includes 14 Greek authors. It needs to be modified to include all ~100 authors from `canonical-greekLit`.

**Steps:**
1. Review current author selection logic in `create_perseus_database.py`
2. Remove or expand the author filter to include all Greek authors
3. Test with a small subset first (maybe 30 authors) to verify:
   - Translation alignment still works
   - Dictionary generation handles increased vocabulary
   - No memory issues during creation
4. Run full build with all authors (expect 5-10x longer build time)

**Key consideration**: Some authors may not have translations available, which is fine.

## 2. Integration Testing (PRIORITY: HIGH)

Before deploying the multi-part solution:

1. **Test the splitting process**:
   ```bash
   cd data-prep
   python3 split_database_for_assets.py split perseus_texts.db.zip 450
   python3 split_database_for_assets.py verify perseus_texts.db.manifest.json
   ```

2. **Update MainActivity.kt** to use `MultiPartDatabaseExtractionActivity`:
   ```kotlin
   // In checkDatabaseAndProceed()
   val intent = Intent(this, MultiPartDatabaseExtractionActivity::class.java)
   ```

3. **Update Gradle files** as per the build script output

4. **Test locally** with bundletool to verify the multi-part flow works

## 3. Optimize Build Process (PRIORITY: MEDIUM)

The current `create_perseus_database.py` script needs optimization for the larger dataset:

1. **Memory optimization**: Process authors in batches
2. **Progress reporting**: Add progress indicators for long-running operations
3. **Incremental builds**: Support adding authors without rebuilding entire DB
4. **Parallel processing**: Use multiprocessing for independent operations

## 4. Handle Edge Cases (PRIORITY: MEDIUM)

1. **Partial author sets**: Allow users to download specific author groups
2. **Update mechanism**: How to update the database without re-downloading everything
3. **Fallback options**: What if a user can't download 1.2GB?

## 5. UI/UX Improvements (PRIORITY: LOW)

1. **Download scheduling**: Allow users to schedule large downloads
2. **Pause/resume**: Implement pause/resume for downloads
3. **Storage warnings**: Better upfront communication about space needs
4. **Author preview**: Show what authors are included before download

## Quick Start for Next Session

```bash
# 1. First, check current implementation
cd /home/user/git2/classicsviewer
cat docs/multipart-database-deployment.md

# 2. Modify create_perseus_database.py to include all authors
# Look for author filtering logic and expand it

# 3. Test with expanded dataset
cd data-prep
python3 create_perseus_database.py  # This will take longer!

# 4. If successful, test the splitting
./build_multipart_database.sh

# 5. Update the app to use multi-part extraction
# Modify MainActivity.kt as described above

# 6. Test the full flow
./gradlew installDebug
adb shell pm clear com.classicsviewer.app.debug
```

## Important Notes

1. **Database Schema**: The schema is already set up to handle more authors - no changes needed
2. **Room Compatibility**: Be extra careful about schema when testing - always use `pm clear`
3. **Build Time**: Expect the full database build to take 30-60 minutes with all authors
4. **Testing Device**: Need a device with at least 7GB free storage for testing

## Potential Issues to Watch For

1. **Memory during build**: The build script might need memory limit increases
2. **Translation gaps**: Some works won't have translations - this is expected
3. **Dictionary size**: May need to optimize dictionary queries with the larger dataset
4. **Asset pack limits**: If database grows beyond projection, might need 4 parts instead of 3

## Success Criteria

- [ ] Database builds successfully with all ~100 Greek authors
- [ ] Compressed size is within 1.0-1.2GB estimate
- [ ] Multi-part download and assembly works smoothly
- [ ] App performance remains acceptable with larger database
- [ ] User experience is clear about download size and progress

The implementation is ready - the main task is updating the database creation to include all authors and testing the multi-part deployment flow end-to-end.