# Multi-Part Database Deployment Guide

## Overview

This guide documents the implementation for splitting large databases (>1GB) across multiple Google Play Asset Packs to overcome the 512MB per-pack limitation while maintaining database integrity.

## Problem Statement

- Full Greek corpus database: ~1.2GB compressed
- Play Store limits:
  - Single asset pack: 512MB maximum
  - Install-time delivery: 1GB total
- Solution: Binary split across multiple fast-follow packs

## Architecture

### Components

1. **Database Splitting** (`data-prep/split_database_for_assets.py`)
   - Splits compressed database at binary level
   - Maintains data integrity through manifest
   - Supports verification of splits

2. **Multi-Part Asset Helper** (`MultiPartAssetPackDatabaseHelper.kt`)
   - Downloads multiple asset packs
   - Reassembles parts in correct order
   - Extracts to final database

3. **Build Automation** (`build_multipart_database.sh`)
   - Automates splitting process
   - Creates asset pack modules
   - Updates Gradle configuration

4. **User Interface** (`MultiPartDatabaseExtractionActivity.kt`)
   - Shows per-part download progress
   - Handles assembly and extraction
   - Provides error recovery

## Implementation Details

### 1. Database Splitting Process

```bash
python3 split_database_for_assets.py split perseus_texts.db.zip 450 output_dir
```

**Features:**
- Configurable chunk size (default: 450MB)
- Creates manifest with metadata
- Binary-safe splitting
- SHA-256 verification support

**Manifest Structure:**
```json
{
  "original_file": "perseus_texts.db.zip",
  "total_size": 1258291200,
  "chunk_size": 471859200,
  "total_chunks": 3,
  "chunks": [
    {
      "name": "perseus_texts.db.part001",
      "index": 0,
      "size": 471859200
    },
    {
      "name": "perseus_texts.db.part002",
      "index": 1,
      "size": 471859200
    },
    {
      "name": "perseus_texts.db.part003",
      "index": 2,
      "size": 314572800
    }
  ]
}
```

### 2. Asset Pack Structure

Each part becomes a separate Gradle module:

```
perseus_database_part1/
├── build.gradle
├── src/
│   └── main/
│       ├── AndroidManifest.xml
│       └── assets/
│           ├── perseus_texts.db.part001
│           └── perseus_texts.db.manifest.json (part 1 only)
```

**build.gradle:**
```gradle
plugins {
    id 'com.android.asset-pack'
}

assetPack {
    packName = "perseus_database_part1"
    dynamicDelivery {
        deliveryType = "fast-follow"
    }
}
```

### 3. Assembly Process

The `MultiPartAssetPackDatabaseHelper` performs:

1. **Discovery**: Read manifest from part 1
2. **Validation**: Ensure all parts are downloaded
3. **Assembly**: Concatenate parts in order
4. **Extraction**: Decompress assembled ZIP
5. **Cleanup**: Remove temporary files

```kotlin
// Assembly logic
for (i in 0 until totalParts) {
    val chunkInfo = chunks.getJSONObject(i)
    val chunkFile = File(packLocation.assetsPath(), chunkName)
    
    FileInputStream(chunkFile).use { input ->
        // Copy chunk to output
        input.copyTo(output)
    }
}
```

### 4. Progress Tracking

Multi-level progress reporting:
- Overall progress (0-100%)
- Per-part download progress
- Assembly progress (50-75%)
- Extraction progress (75-100%)

## Build Process

### Step 1: Prepare Database
```bash
cd data-prep
python3 create_perseus_database.py
```

### Step 2: Run Multi-Part Build
```bash
./build_multipart_database.sh
```

This script:
1. Splits the compressed database
2. Creates asset pack modules
3. Updates Gradle configuration
4. Provides integration instructions

### Step 3: Update App Configuration

**settings.gradle:**
```gradle
include ':app'
include ':perseus_database_part1'
include ':perseus_database_part2'
include ':perseus_database_part3'
```

**app/build.gradle:**
```gradle
android {
    assetPacks = [':perseus_database_part1', ':perseus_database_part2', ':perseus_database_part3']
}
```

### Step 4: Update MainActivity

Replace `AssetPackDatabaseHelper` with `MultiPartAssetPackDatabaseHelper`:

```kotlin
private fun checkDatabaseAndProceed() {
    val dbFile = getDatabasePath("perseus_texts.db")
    if (!dbFile.exists()) {
        // Use multi-part extraction
        val intent = Intent(this, MultiPartDatabaseExtractionActivity::class.java)
        startActivity(intent)
        finish()
    }
}
```

## Deployment

### Local Testing
```bash
# Build AAB
./gradlew bundleDebug

# Deploy with bundletool
bundletool build-apks \
    --bundle=app/build/outputs/bundle/debug/app-debug.aab \
    --output=app-debug.apks \
    --local-testing

bundletool install-apks --apks=app-debug.apks
```

### Production Release
```bash
# Build release AAB
./gradlew bundleRelease

# Upload to Play Console
# Asset packs will be processed automatically
```

## User Experience

### First Launch Flow
1. App installation (~30-50MB)
2. Launch triggers database check
3. Multi-part extraction activity:
   - Check for existing parts
   - Download missing parts (3 × ~450MB)
   - Show per-part progress
   - Assemble parts
   - Extract database
4. Return to main activity

### Storage Requirements
- Download: ~1.2GB (compressed parts)
- Extraction: ~5.4GB temporary (assembly + extraction)
- Final: ~5.4GB (uncompressed database)
- **Total needed**: ~6.6GB free space

### Time Estimates
- Download: 2-10 minutes (connection dependent)
- Assembly: 10-20 seconds
- Extraction: 30-40 seconds
- **Total**: 3-12 minutes typical

## Error Handling

### Download Failures
- Automatic retry via Play Core
- Manual retry option in UI
- Partial download resume supported

### Assembly Failures
- Manifest validation
- Size verification
- Cleanup of partial files

### Storage Errors
- Pre-check available space
- Clear error messaging
- Cleanup on failure

## Testing

### Verification Script
```bash
# After splitting
python3 split_database_for_assets.py verify output/perseus_texts.db.manifest.json
```

### Integration Testing
1. Test with limited storage
2. Test download interruption
3. Test app backgrounding
4. Test multiple devices

## Troubleshooting

### Common Issues

**"Asset pack not found"**
- Ensure all parts in settings.gradle
- Check module names match
- Verify bundletool includes packs

**"Assembly failed"**
- Check all parts downloaded
- Verify manifest present
- Check storage space

**"Extraction failed"**
- Verify ZIP integrity
- Check available storage
- Review logcat for errors

### Debug Commands
```bash
# List asset packs in AAB
bundletool dump manifest --bundle=app.aab | grep asset-pack

# Check pack sizes
unzip -l app.aab | grep perseus_database_part

# Monitor download
adb logcat | grep MultiPartAssetPackDatabaseHelper
```

## Optimization Opportunities

### Future Improvements
1. **Selective Download**: Download parts on-demand
2. **Compression**: Experiment with better algorithms
3. **Incremental Updates**: Delta updates for database
4. **Parallel Extraction**: Extract while downloading

### Alternative Approaches
1. **Author-based Packs**: One pack per author group
2. **Cloud Delivery**: Download from CDN post-install
3. **Streaming**: Query remote database directly

## Migration Guide

### From Single Pack to Multi-Part

1. **Backup Current Implementation**
   ```bash
   git add -A && git commit -m "Backup before multi-part migration"
   ```

2. **Add New Components**
   - Copy provided files
   - Run build script

3. **Update References**
   - Replace AssetPackDatabaseHelper usage
   - Update MainActivity database check

4. **Test Thoroughly**
   - Clean install test
   - Upgrade test
   - Various network conditions

### Rollback Plan
```bash
# Revert to single pack
git checkout -- settings.gradle app/build.gradle
rm -rf perseus_database_part*
# Rebuild with original perseus_database module
```

## Performance Metrics

### Expected Performance

| Metric | Single Pack | Multi-Part (3) |
|--------|------------|----------------|
| Download Start | Immediate | Immediate |
| Download Time | 5-15 min | 5-15 min |
| Assembly Time | N/A | 10-20 sec |
| Extraction Time | 30-40 sec | 30-40 sec |
| Total Time | 5-16 min | 5-17 min |
| Complexity | Low | Medium |
| Error Points | 2 | 5 |

### Resource Usage

| Phase | CPU | Memory | Storage | Network |
|-------|-----|--------|---------|---------|
| Download | Low | Low | 1.2GB | High |
| Assembly | Medium | Low | 2.4GB | None |
| Extraction | High | Medium | 6.6GB | None |
| Runtime | Low | High | 5.4GB | None |

## Conclusion

The multi-part database deployment solution successfully overcomes Play Store limitations while maintaining a reasonable user experience. The binary splitting approach preserves database integrity while the modular architecture allows for future enhancements like selective downloading or incremental updates.