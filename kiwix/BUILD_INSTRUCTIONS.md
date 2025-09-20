# ZIM Build Instructions

## Prerequisites
1. Ensure databases exist:
   - `../data-prep/perseus_texts_sample.db` (693MB)
   - `../data-prep/perseus_texts_full.db` (2.9GB)
   - `../data-prep/perseus_texts_extended.db` (9.4GB - Perseus + First1KGreek)

2. Python virtual environment with libzim:
   ```bash
   cd kiwix
   source venv/bin/activate
   pip install libzim
   ```

## Building ZIM Files

### Sample Build (10 Greek + 2 Latin authors)
**Time:** ~8-10 minutes total
**Size:** ~427MB
**Content:** ~316,000 dictionary pages + text pages

```bash
cd kiwix
# Clean any previous attempts
rm -f /tmp/*.lock
rm -rf zim_content_optimized
ps aux | grep -E "python.*zim" | grep -v grep | awk '{print $2}' | xargs kill 2>/dev/null || true

# Run the build
source venv/bin/activate
python3 create_zim_content_optimized.py --sample --output zim_content_optimized
python3 create_zim_optimized.py --input zim_content_optimized --output classicsviewer_sample.zim
```

### Full Build (88 Greek + 40 Latin authors)
**Time:** ~1.5 hours total
**Size:** ~2.3GB
**Content:** ~2.35 million dictionary pages + text pages

```bash
cd kiwix
# Clean any previous attempts
rm -f /tmp/*.lock
rm -rf zim_content_full
ps aux | grep -E "python.*zim" | grep -v grep | awk '{print $2}' | xargs kill 2>/dev/null || true

# Run the build - DO NOT run both steps simultaneously!
source venv/bin/activate

# Step 1: Generate HTML content (20 minutes)
python3 create_zim_content_optimized.py --output zim_content_full

# Step 2: Create ZIM archive (1-2 hours)
python3 create_zim_optimized.py --input zim_content_full --output classicsviewer_full.zim
```

### Extended Build (391 authors - Perseus + First1KGreek)
**Time:** ~2-3 hours total
**Size:** ~4-5GB (estimated)
**Content:** ~4+ million dictionary pages + text pages
**Note:** Includes non-duplicate works from First1KGreek collection (991 unique works not in Perseus)

```bash
cd kiwix
# Clean any previous attempts
rm -f /tmp/*.lock
rm -rf zim_content_optimized
ps aux | grep -E "python.*zim" | grep -v grep | awk '{print $2}' | xargs kill 2>/dev/null || true

# Run the build - DO NOT run both steps simultaneously!
source venv/bin/activate

# Step 1: Generate HTML content (3-4 minutes)
python3 create_zim_content_optimized.py --extended --output zim_content_optimized

# Step 2: Create ZIM archive (60-90 minutes)
python3 create_zim_optimized.py --input zim_content_optimized --output classicsviewer_extended.zim
```

**OR use the automated script:**
```bash
cd kiwix
./build_extended_clean.sh
```

## Progress Monitoring

The builds have two phases:

### Phase 1: Content Generation
- Sample: ~2 minutes, generates ~316,000 HTML files
- Full: ~20 minutes, generates ~2.35 million HTML files
- Extended: ~3-4 minutes, generates ~4+ million HTML files
- Progress shown: "Generated X dictionary pages..."
- Includes Latin dictionary support with Whitaker's Words data

### Phase 2: ZIM Creation
- Sample: ~7 minutes, compresses to ~427MB
- Full: ~1 hour 15 minutes, compresses to ~2.3GB
- Extended: ~60-90 minutes, compresses to ~4-5GB (estimated)
- Progress shown: "T:X; A:Y; C:Z" (Time, Assets added, Compressed count)

## Common Issues and Solutions

### Issue: Script appears to hang after "DEBUG: Connected to database"
**Solution:** This is normal! The script is loading data. Wait ~30 seconds for progress to appear.

### Issue: "Lock file exists" error
**Solution:** 
```bash
rm -f /tmp/*.lock
rm -f /tmp/build_zim*.lock
```

### Issue: Multiple Python processes running
**Solution:**
```bash
killall python3
killall Python
```

### Issue: Out of memory
**Solution:** Close other applications. The process needs ~2GB RAM.

## Verification

After successful build:
```bash
# Check file size
ls -lh classicsviewer_*.zim

# Test in Kiwix
open -a Kiwix classicsviewer_sample.zim
# Or
kiwix-serve --port 8080 classicsviewer_sample.zim
```

## Clean Build Script

For a guaranteed clean build, use this script:

```bash
#!/bin/bash
# clean_build_sample.sh

set -e  # Exit on error

echo "=== Cleaning environment ==="
killall python3 2>/dev/null || true
killall Python 2>/dev/null || true
rm -f /tmp/*.lock
rm -rf zim_content_optimized

echo "=== Starting Sample Build ==="
source venv/bin/activate

echo "Phase 1: Generating content..."
python3 create_zim_content_optimized.py --sample

echo "Phase 2: Creating ZIM file..."
python3 create_zim_optimized.py --output classicsviewer_sample.zim

echo "=== Build Complete ==="
ls -lh classicsviewer_sample.zim
```

## Expected Output

Successful build shows:
```
==================================================
Generation Complete!
  Authors: 12
  Works: 278
  Books: 705
  Pages: 1803
  Dictionary entries: 286153
  Total time: 94.2 seconds (1.6 minutes)
==================================================

Creating ZIM file...
T:450; A:287868; C:287868; CC:287868
...
Successfully created classicsviewer_sample.zim (318MB)
```

## Tips
1. Run one build at a time - don't run sample and full simultaneously
2. Use `tee` to capture output while seeing progress
3. The DEBUG messages are normal - wait for actual progress
4. Content generation is fast (~90s), ZIM creation is slow (7-40min)