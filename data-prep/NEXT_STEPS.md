# Next Steps for Database Completion

## Current Status (as of Aug 5, 2025)

### Completed Today:
1. ✓ Extracted Wiktionary definitions (6,755 found, 1,828 added to database)
2. ✓ Optimized extraction process (50x speedup: 12 hours → 15 minutes)
3. ✓ Created Greek pages cache (124,116 pages in all_greek_wiktionary_pages.json)
4. ✓ Extracted inflection mappings (15,583 mappings with morphology)
5. ✓ Added inflection mappings to lemma_map table

### Database Status:
- Dictionary entries: 30,475 total (28,647 LSJ + 1,828 Wiktionary)
- Lemma mappings: 73,956 word forms (increased from 58,373)
- Corpus: 179,325 unique Greek words

## Immediate Tasks to Complete

### 1. Rebuild Database with All Improvements (5-10 minutes)
```bash
cd /home/user/classics-viewer/data-prep
python3 build_database.py
```

This will incorporate:
- New Wiktionary dictionary entries
- New lemma mappings from inflections
- Previous improvements (punctuation normalization, patronymics, aorist participles)

### 2. Test Coverage on Odyssey Sample
```bash
cd /home/user/classics-viewer/data-prep

# First, create a test script to measure coverage
python3 test_odyssey_coverage.py
```

Expected improvement: 77% → 85-95% coverage

### 3. Create and Deploy OBB File
```bash
cd /home/user/classics-viewer/data-prep/output

# Create OBB file (it's just the database renamed)
cp perseus_texts.db main.1.com.classicsviewer.app.debug.obb

# Check file size
ls -lh main.1.com.classicsviewer.app.debug.obb

# Deploy to Android device
adb push main.1.com.classicsviewer.app.debug.obb /storage/emulated/0/Android/obb/com.classicsviewer.app.debug/

# Clear app data and restart
adb shell pm clear com.classicsviewer.app.debug
adb shell am start -n com.classicsviewer.app.debug/com.classicsviewer.app.MainActivity
```

### 4. Verify Results on Device
```bash
# Monitor logs for dictionary lookups
adb logcat | grep -E "(Dictionary|Lemma|lookup)" --line-buffered
```

## Optional Further Improvements

### Extract More Definitions from Greek Pages Cache
We have 124k Greek pages cached but only extracted inflections. We could also extract:
- Definitions for lemmas (not just inflected forms)
- Etymology information
- Usage examples

```bash
cd /home/user/classics-viewer/data-prep/wiktionary-processing
# Create and run: extract_lemma_definitions_from_cache.py
```

### Process Greek Wiktionary
For additional coverage, download and process Greek Wiktionary:
```bash
wget https://dumps.wikimedia.org/elwiktionary/latest/elwiktionary-latest-pages-articles.xml.bz2
```

## Key Files and Locations

### Wiktionary Processing Directory
`/home/user/classics-viewer/data-prep/wiktionary-processing/`
- `all_greek_wiktionary_pages.json` - 46MB cache of 124k Greek pages
- `inflection_extraction_results/` - Contains inflection mappings
- `wiktionary_extraction_results/` - Contains definition extractions

### Documentation Created
- `WIKTIONARY_EXTRACTION_GUIDE.md` - Detailed optimization explanation
- `QUICK_PROCESS_SUMMARY.md` - Quick command reference

### Database Location
`/home/user/classics-viewer/data-prep/perseus_texts.db`

## Expected Final Results

After completing all steps:
- Dictionary coverage: ~10% improvement (30k+ entries)
- Lemmatization: ~27% improvement (74k mapped forms)
- Overall lookup success: Significant improvement in user experience
- Database size: ~755MB (suitable for mobile deployment)

## Notes for Next Instance

The hard work is done! The remaining tasks are straightforward:
1. Run build_database.py to create the final database
2. Test the improvements 
3. Deploy to Android

All the Wiktionary data has been extracted and added to the database. The Greek pages cache can be reused for future extractions without re-processing the 1.4GB dump.