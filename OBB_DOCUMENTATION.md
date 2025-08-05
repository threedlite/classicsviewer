# OBB (Opaque Binary Blob) Documentation for Classics Viewer

## Overview

The Classics Viewer app uses Android's OBB expansion file system to distribute the large Perseus database (~786MB uncompressed) separately from the APK. This keeps the APK small and allows for efficient updates.

## OBB File Format

**CRITICAL**: The OBB files are **compressed ZIP archives**, not raw database files!

- Despite the `.obb` extension, these are standard ZIP files
- Must contain `perseus_texts.db` as the root entry
- Use maximum compression (-9) to reduce size from 786MB to 173MB (78% reduction)
- Android app extracts the database on first launch

### Correct OBB Creation

```bash
# CORRECT - Creates a ZIP file containing the database
cd data-prep
zip -9 main.1.com.classicsviewer.app.obb perseus_texts.db

# WRONG - Just renaming the database file
cp perseus_texts.db main.1.com.classicsviewer.app.obb  # DON'T DO THIS!
```

## File Naming Convention

OBB files must follow Android's naming convention:
```
main.<version-code>.<package-name>.obb
```

Examples:
- Debug: `main.1.com.classicsviewer.app.debug.obb`
- Release: `main.1.com.classicsviewer.app.obb`

## Debug vs Release Builds

**IMPORTANT**: Debug and release builds use different package names and OBB paths!

### Debug Build
- Package: `com.classicsviewer.app.debug`
- OBB Path: `/storage/emulated/0/Android/obb/com.classicsviewer.app.debug/`
- OBB Name: `main.1.com.classicsviewer.app.debug.obb`

### Release Build
- Package: `com.classicsviewer.app`
- OBB Path: `/storage/emulated/0/Android/obb/com.classicsviewer.app/`
- OBB Name: `main.1.com.classicsviewer.app.obb`

## Deployment Process

### 1. Create Compressed OBBs
```bash
cd data-prep
./create_compressed_obb.sh
```

This creates both debug and release OBBs in the output directory.

### 2. Deploy to Device
```bash
# For complete deployment (APK + OBB)
./deploy_complete.sh

# For OBB only
adb shell mkdir -p /storage/emulated/0/Android/obb/com.classicsviewer.app.debug/
adb push data-prep/output/main.1.com.classicsviewer.app.debug.obb \
    /storage/emulated/0/Android/obb/com.classicsviewer.app.debug/
```

### 3. Force App Restart
After deploying a new OBB, force the app to restart:
```bash
adb shell am force-stop com.classicsviewer.app.debug
adb shell pm clear com.classicsviewer.app.debug  # Clears data and forces re-extraction
```

## How the App Uses OBBs

1. **Language Selection**: On first launch, user selects Greek or Latin
2. **OBB Detection**: App checks for OBB at the expected path
3. **Extraction**: If found, extracts `perseus_texts.db` from the ZIP
4. **Progress Dialog**: Shows extraction progress (typically 2-3 seconds)
5. **Database Copy**: Copies extracted database to app's internal storage
6. **Cleanup**: Removes temporary extraction files

## Common Issues and Solutions

### Issue: "Failed to extract database"
**Cause**: OBB is not a valid ZIP file or doesn't contain `perseus_texts.db`
**Solution**: 
```bash
# Verify OBB structure
unzip -l main.1.com.classicsviewer.app.debug.obb
# Should show: perseus_texts.db (not another .obb file!)
```

### Issue: No authors shown after deployment
**Cause**: App looking for OBB in wrong location (debug vs release mismatch)
**Solution**: Check logs to see which path the app is checking:
```bash
adb logcat | grep "OBB path"
```

### Issue: Extraction takes too long
**Cause**: OBB is not compressed
**Solution**: Always use `-9` flag when creating OBBs:
```bash
zip -9 main.1.com.classicsviewer.app.debug.obb perseus_texts.db
```

## Build Scripts

All build scripts have been updated to use compressed OBBs:

- `create_compressed_obb.sh` - Main OBB creation script
- `deploy_complete.sh` - Full deployment (build + deploy)
- `build_and_deploy.sh` - Standard build and deploy
- `deploy_database_only.sh` - Deploy just the OBB
- `build_and_deploy_optimized.sh` - Build without database in APK
- `create_obb.sh` - Legacy script (updated to use compression)

## Google Play Release

For Google Play releases:
1. Build the release AAB: `./build_release_aab.sh`
2. Create release OBB: `cd data-prep && ./create_release_obb.sh`
3. Upload both AAB and OBB to Google Play Console
4. The OBB will be automatically downloaded by Google Play when users install the app

## Testing OBB Extraction

To test the extraction process:
```bash
# Clear app data to force re-extraction
adb shell pm clear com.classicsviewer.app.debug

# Monitor extraction logs
adb logcat -c
adb shell am start -n com.classicsviewer.app.debug/com.classicsviewer.app.MainActivity
adb logcat | grep -E "ObbDatabaseHelper|DatabaseExtraction|progress"
```

## Size Comparison

- Uncompressed OBB: 786MB (raw SQLite database)
- Compressed OBB: 173MB (78% reduction)
- APK without database: ~8MB
- Total download size: ~181MB (vs 794MB uncompressed)

This compression significantly improves:
- Download time for users
- Storage space on device during download
- Google Play serving costs
- User experience (faster installs)