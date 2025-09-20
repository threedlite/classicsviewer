# Classics Viewer Data Preparation

This directory contains all scripts and tools for preparing the Perseus Digital Library texts for use in the Classics Viewer Android app.

## Overview

The data preparation process:
1. Parses XML texts from Perseus Digital Library repositories
2. Extracts LSJ (Greek) and Lewis & Short (Latin) dictionaries
3. **Extracts morphological data from Wiktionary** for enhanced lemmatization
4. Creates a SQLite database with texts, translations, dictionary, and morphology
5. Applies translation alignment fixes for section-based texts
6. Generates compressed OBB (Opaque Binary Blob) files for Android deployment

## Database Schema

The database contains the following main tables:
- `authors`: Author metadata
- `works`: Works by each author
- `books`: Book divisions within works
- `text_lines`: Original Greek/Latin text lines
- `translation_segments`: English translations aligned to line ranges
- `dictionary_entries`: LSJ/Lewis & Short dictionary entries
- `lemma_map`: Basic word-to-lemma mappings
- `lemma_map_full`: Enhanced Wiktionary morphological mappings
- `word_forms`: Word occurrences with lemma references

## Key Scripts

### create_perseus_database.py
Main database creation script that:
- Parses Perseus XML files from data-sources/
- Extracts texts and translations
- Detects and fixes translation alignment issues
- Creates indexed SQLite database

**Translation Alignment Fix**: The script automatically detects when translations use section numbers instead of line numbers and creates proportional mappings. For example, if a text has 866 lines but translations only go to line 196 (sections), it distributes the 196 sections across all 866 lines.

### create_compressed_obb.sh
Creates compressed OBB files for Android deployment:
- Uses ZIP compression with -9 flag (maximum compression)
- Reduces database size from ~786MB to ~173MB (78% reduction)
- Creates both debug and release versions

### fix_alignment_post_import.py
Post-import script to fix translation alignments if needed:
- Fixes 30 books with section-as-line numbering
- Creates database backup before changes
- Safe detection criteria (only fixes texts where sections < 50% of lines)

## Wiktionary Data Extraction

The database build process uses pre-extracted Wiktionary data to enhance lemmatization:

### Pre-extracted Wiktionary Files Used:
1. **`wiktionary-processing/greek_inflection_of_mappings.json`** (470KB)
   - Maps inflected forms to their lemmas using {{inflection of}} templates
   - Example: μῆνιν → μῆνις (accusative singular)

2. **`wiktionary-processing/ancient_greek_declension_mappings.json`** (2.7MB)
   - Comprehensive declension patterns from Greek Wiktionary
   - 37,119 form-to-lemma mappings with full morphological details

3. **`wiktionary-processing/ancient_greek_all_morphology_correct.json`** (11MB)
   - Complete morphological data including verb conjugations
   - Used by `add_inflection_mappings.py` during build

### Wiktionary Processing Pipeline (if regenerating):
```bash
# Step 1: Extract Greek pages from Wiktionary dump (only Greek-related pages)
python3 wiktionary-processing/extract_all_greek_pages.py
# Input: enwiktionary-latest-pages-articles.xml.bz2 (1.4GB)
# Output: all_greek_wiktionary_pages.json (46MB, 124k pages)

# Step 2: Extract specific data from the Greek pages cache
python3 wiktionary-processing/extract_inflection_of_template.py
python3 wiktionary-processing/extract_declension_mappings.py
python3 wiktionary-processing/extract_all_ancient_greek_forms.py
```

The two-stage approach (dump → Greek cache → specific extractions) is much more efficient than repeatedly parsing the 1.4GB Wiktionary dump.

## Building the Database

```bash
# Full build from scratch (uses pre-extracted Wiktionary data)
python3 create_perseus_database.py

# Or use the master build script for complete processing:
python3 build_database.py

# The database will be created in output/perseus_texts.db
# Size: ~786MB uncompressed
```

## Creating OBB Files

```bash
# Create compressed OBBs for deployment
./create_compressed_obb.sh

# This creates:
# - output/main.1.com.classicsviewer.app.debug.obb (173MB)
# - output/main.1.com.classicsviewer.app.obb (173MB)
```

## OBB File Format

The OBB files are compressed ZIP archives containing the SQLite database:
- **NOT** raw SQLite files (despite the .obb extension)
- Must contain `perseus_texts.db` as the root entry in the ZIP
- Use maximum compression (-9) to reduce download size
- Android app extracts the database on first launch

## Deployment

For complete deployment to Android device:
```bash
cd ..  # Go to project root
./deploy_complete.sh
```

This script:
1. Builds/verifies the database
2. Creates compressed OBBs
3. Builds the Android app
4. Deploys APK and OBB to connected device
5. Launches the app

## Translation Coverage

Current coverage: 94.1% (255 out of 271 works have translations)

The translation alignment fix ensures proper distribution of section-based translations across line-based texts, particularly important for prose works like Aeschines.

## Directory Structure

```
data-prep/
├── create_perseus_database.py     # Main database creation
├── create_compressed_obb.sh       # OBB compression script
├── fix_alignment_post_import.py   # Translation alignment fixes
├── output/                        # Generated files
│   ├── perseus_texts.db          # SQLite database
│   ├── main.1.*.obb              # Compressed OBBs
│   └── *.backup                  # Database backups
└── data-sources/                  # Perseus XML repositories (DO NOT MODIFY)
    ├── canonical-greekLit/
    ├── canonical-latinLit/
    ├── canonical-pdlrefwk/
    └── perseus_catalog/
```

## Important Notes

1. **Never modify data-sources/** - These are cloned Perseus repositories
2. **Always use compression** - Raw database OBBs are too large (786MB)
3. **Test alignment fixes** - Run with small test database first
4. **Debug vs Release** - Debug builds use `.debug` suffix in package names and OBB paths
5. **Force restart after DB changes** - Use `adb shell pm clear` to ensure clean state

## Troubleshooting

### OBB Extraction Fails
- Ensure OBB is a ZIP file containing `perseus_texts.db`
- Check Android logs: `adb logcat | grep ObbDatabaseHelper`
- Verify OBB path matches build variant (debug/release)

### Translation Alignment Issues
- Check if text uses section numbering instead of line numbering
- Run `fix_alignment_post_import.py` to analyze and fix
- Verify with: `sqlite3 perseus_texts.db "SELECT * FROM translation_lines WHERE book_id='...' LIMIT 10"`

### Database Schema Mismatch
- Room validates exact schema match
- Check entity files in Android app before schema changes
- Common issues: nullable columns, AUTOINCREMENT, DEFAULT values