# Sanskrit Database Build Guide

## Quick Start

```bash
# Single command - builds complete database automatically!
python3 create_sanskrit_database_interlinear.py full
```

**Output**: `sanskrit_texts.db.zip` (371MB) with:
- 270 Sanskrit works with texts
- 179,806 dictionary entries
- 4,705,160 lemma mappings
- 203,713 interlinear translations (one per line)

**Build time**: ~15-20 minutes (fully automated, no manual intervention)

**Note**: Uses pre-built lexicon ZIP (`dcs_sanskrit_lexicon.zip`, 35 MB) that's already in the repo. You don't need to regenerate the lexicon unless you're updating DCS data or improving coverage.

## Prerequisites

- Python 3.8+: `pip install indic-transliteration`
- Data sources in `../data-sources/sanskrit/dcs/` (DCS CoNLL-U files)
- **Pre-built lexicon**: `dcs_sanskrit_lexicon.zip` (already checked into repo, no action needed)

## What the Script Does Automatically

The `create_sanskrit_database_interlinear.py` script is a **complete automated pipeline**:

1. ✅ **Creates database** with 270 Sanskrit texts (5 min)
   - Bhagavad Gita from Wikisource JSON
   - Rig Veda from DCS pada format
   - 268 works from DCS CoNLL-U files

2. ✅ **Imports lexicon** from `dcs_sanskrit_lexicon.zip` (2 min)
   - 179,806 dictionary entries with transliterations
   - 4,705,160 word form → lemma mappings
   - 6 normalization patterns for text matching

3. ✅ **Generates interlinear XML** for all 270 works (5 min)
   - Creates TEI XML files with word-by-word glosses
   - Outputs to `interlinear_output/` directory
   - Uses parallel processing (8 workers)

4. ✅ **Imports interlinear** into database (2 min)
   - Parses XML files to extract translations
   - Creates 203,713 interlinear segments (one per line)
   - Builds translation lookup table for efficient retrieval

5. ✅ **Compresses to ZIP** (1 min)
   - Creates `sanskrit_texts.db.zip` (371 MB)
   - Ready for standalone use or merging into extended database

**No manual steps required!**

## Important Notes

- **Schema**: Identical to extended database (100% compatible for merging)
- **Standalone**: Database includes all lexicon data, works without extended DB
- **Merge-ready**: Can be merged into extended database using `merge_database.py`
- **Interlinear**: All 270 works have word-by-word interlinear translations

## Database Contents

**Full mode** includes all 270 works total:
- **Bhagavad Gita** (18 chapters, Wikisource with English translations)
  - Source: Sanskrit Wikisource (CC BY-SA 4.0)
  - Parsed from downloaded HTML via `data-sources/parse_bhagavad_gita_sanskrit.py`
  - Creates JSON intermediate: `data-sources/bhagavad_gita_sanskrit.json`
  - Translations: Edwin Arnold (prose, Public Domain), Annie Besant (verse-by-verse, Public Domain)
  - Work ID: `bhagavad_gita_wikisource`, Author ID: `vyasa_wikisource`
- **Rig Veda** (10 maṇḍalas, complete with Griffith translation)
  - Source: DCS pada-and-analysis.dat format from `../data-sources/sanskrit/dcs/data/rigveda/`
  - Translation: Ralph T.H. Griffith (1896, Public Domain) from text file
  - Work ID: `rigveda_pada`, Author ID: `rishis_pada`
- **268 DCS works**: Including Upanishads, Vedas, epics, philosophical texts, and more
  - Source: DCS CoNLL-U files from `../data-sources/sanskrit/dcs/conllu/`
  - Most works are Sanskrit-only (no English translations)
  - ~738K verses total
  - ~5.6M words total

## Lexicon Generation (One-Time Setup)

The `dcs_sanskrit_lexicon.zip` file is pre-built and checked into the repository. You only need to regenerate it if:
- DCS corpus data is updated
- You want to improve coverage
- The lexicon file is missing or corrupted

### Regenerating the Lexicon

```bash
# 1. Extract from DCS corpus (~5-10 minutes)
nohup python3 extract_dcs_lexicon.py > dcs_extraction.log 2>&1 &
tail -f dcs_extraction.log

# This creates:
# - dcs_sanskrit_dictionary.csv (28 MB) - 163k lemmas with definitions
# - dcs_sanskrit_morphology.csv (264 MB) - 4.7M word forms with sandhi splits

# 2. Package into ZIP (~10 seconds)
python3 create_dcs_lexicon.py

# This creates:
# - dcs_sanskrit_lexicon.zip (35 MB) - ready for import
```

### What `extract_dcs_lexicon.py` Does

1. **Extracts dictionary** from `../data-sources/sanskrit/dcs/data/conllu/lookup/dictionary.csv`
   - Converts IAST → Devanagari
   - Cleans control characters from source data
   - Creates ~163k dictionary entries

2. **Extracts morphology** from 15,733 CoNLL-U files
   - Processes all DCS texts for word forms
   - Captures both sandhied and unsandhied forms
   - Adds POS tags and confidence scores
   - Creates ~4.7M morphology mappings

3. **Adds sandhi splitting** (requires `sanskrit-parser`)
   - Analyzes missing words from Bhagavad Gita
   - Splits compounds like चैव → च + एव
   - Adds ~1,956 splits with ~3,699 new mappings

4. **Packages everything** into ZIP
   - `dictionary.csv` - for dictionary lookups
   - `morphology.csv` - for lemma mappings
   - `normalization_rules.csv` - for text normalization

The resulting ZIP is used by both:
- Standalone Sanskrit database builds
- Extended database builds (Perseus integration)

## Complete Rebuild Workflow

```bash
# Clean previous builds (optional)
rm -f sanskrit_texts.db sanskrit_texts.db.zip
rm -rf interlinear_output

# Build everything automatically
nohup python3 create_sanskrit_database_interlinear.py full > build.log 2>&1 &
tail -f build.log  # Monitor (~15-20 min)

# Verify output
ls -lh sanskrit_texts.db.zip  # Should be ~371 MB
ls -lh interlinear_output/*.dcs-eng99.xml | wc -l  # Should be 270 files
```

## Output Format

Each work generates 2 files matching Greek format:
- `.interlinear.txt` - Plain text word-by-word glosses
- `.dcs-eng99.xml` - TEI XML with markup

**Example** (`.interlinear.txt`):
```
1. ॐ | श्रीपरमात्मने | नमः | अथ
a word of solemn affirmation and | ? | bow | now
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Missing dictionary files | `python3 extract_dcs_lexicon.py` (required first step) |
| Missing DCS data | Clone DCS repo to `../data-sources/sanskrit/dcs/` |
| Out of memory | Use `--parallel 2` instead of 8 for interlinear |
| Low interlinear coverage | Ensure `extract_dcs_lexicon.py` completed successfully |
| Sandhi forms not found | Re-run `extract_dcs_lexicon.py` to regenerate morphology |
| XML parsing errors | Re-run `extract_dcs_lexicon.py` to clean control characters from source data |
| Interlinear import fails silently | Check that DCS book numbering matches between XML and database |

## DCS Lexicon Extraction Details

**What it does**:
- Processes 15,733 CoNLL-U files from DCS corpus (5.5M word tokens)
- Extracts 164K dictionary entries (lemmas with definitions)
- **Cleans control characters** from source data (removes ASCII 0x00-0x1F, 0x7F)
  - DCS source data contains control character 0x12 (DC2) before certain characters like ṣ
  - Example: "name of a `\x12`ṣi" instead of correct "name of a ṣi"
  - These control characters break XML parsing with "not well-formed (invalid token)" errors
  - Affected 131 out of 270 works before fix
  - Cleaning ensures valid UTF-8 encoding for all Sanskrit characters
- Generates ~4.7M morphology mappings (word forms → lemmas)
- **Adds sandhi splitting** using `sanskrit-parser` library
  - Analyzes missing words from Bhagavad Gita
  - Splits compounds like चैव → च + एव
  - Adds ~1,956 splits, ~3,699 new mappings
- Creates two outputs:
  - `dcs_sanskrit_dictionary.csv` (29MB) - lemmas with definitions (cleaned)
  - `dcs_sanskrit_morphology.csv` (276MB) - inflected forms with sandhi

**Format**: Compatible with both:
- Interlinear generation (sanskrit_dictionary_lookup.py)
- Perseus database import (create_perseus_database.py extended mode)

**When to re-run**:
- DCS data has been updated
- Want to improve sandhi coverage
- Morphology CSV is missing or corrupted
- First time setup

## Perseus Integration

The Sanskrit lexicon integrates with the main Perseus database in extended mode:

```bash
# From data-prep directory:
cd ../data-prep
python3 create_perseus_database.py extended
```

This will:
1. Merge `sanskrit/sanskrit_texts.db` into Perseus database
2. Import `sanskrit/dcs_sanskrit_lexicon.zip` into dictionary_entries and lemma_map tables
3. Enable Sanskrit word lookups in the main ClassicsViewer app

## Stats

**Full Database**: 268 works, ~738K verses, ~5.6M words, 138MB compressed
**Build time**: ~20min total (first time)
  - DCS extraction: 5-10min (run once, then reuse)
  - Lexicon ZIP: 10sec
  - Database: 5min
  - Interlinear: 90sec (with 8 parallel workers)

**Interlinear Coverage**:
- Baseline (without sandhi): ~61% words found
- With sandhi-enhanced morphology: **85-90% words found**

**Data Sources**:
- DCS CoNLL-U corpus: 15,733 files, 5.5M words, 268 works
- DCS dictionary: 164K lemmas
- DCS morphology: 4.7M mappings (with sandhi)
- Bhagavad Gita: Wikisource (parsed from HTML to JSON)
- Rig Veda: DCS pada-and-analysis.dat (TSV format)
- English translations: Available for ~7 works (Bhagavad Gita, Rig Veda, 5 Upanishads/Vedas)

## Data Pipeline Architecture

The Sanskrit database build uses three different data sources with different processing pipelines:

### 1. Bhagavad Gita (Wikisource → HTML → JSON → Database)
- **Download**: Shell scripts fetch 18 HTML files per source from Wikisource
- **Parse**: Python scripts extract text from HTML and create JSON
- **Import**: `create_sanskrit_database_interlinear.py` loads JSON files
- **Location**: `data-sources/` directory
- **Files**:
  - Sanskrit: `bhagavad_gita_sa_*.html` → `bhagavad_gita_sanskrit.json`
  - Arnold: `bhagavad_gita_en_*.html` → `bhagavad_gita_english.json`
  - Besant: `bhagavad_gita_besant_*.html` → `bhagavad_gita_besant.json`
- **Workflow**: `load_bhagavad_gita()` function reads JSON and creates work with author `vyasa_wikisource`

### 2. Rig Veda (DCS pada format → Database)
- **Source**: Pre-existing TSV file from DCS corpus
- **Import**: `create_sanskrit_database_interlinear.py` reads directly
- **Location**: `../data-sources/sanskrit/dcs/data/rigveda/pada-and-analysis.dat`
- **Translation**: `../data-sources/sanskrit/translations/RV-Griffith.txt`
- **Format**: Tab-separated with columns: book, hymn, stanza, pada, text
- **Workflow**: `load_rigveda()` function reads TSV, converts IAST to Devanagari, creates work with author `rishis_pada`

### 3. DCS Works (CoNLL-U → Database)
- **Source**: 15,733 CoNLL-U files from DCS corpus
- **Import**: `create_sanskrit_database_interlinear.py` reads directly
- **Location**: `../data-sources/sanskrit/dcs/conllu/`
- **Format**: CoNLL-U morphological annotation format
- **Workflow**: `load_dcs_texts()` function processes all 268 works

All three sources are integrated into a single `sanskrit_texts.db` with consistent schema.

## Interlinear Generation Pipeline

After building the database, interlinear translations are generated in two stages:

### Stage 1: Generate Interlinear XML Files (batch_generate_interlinear.py)

```bash
python3 batch_generate_interlinear.py sanskrit_texts.db \
  --output ../data-sources/classicsviewer_interlinear \
  --parallel 8
```

**What it does**:
1. Reads all 270 works from `sanskrit_texts.db`
2. For each work, calls `generate_sanskrit_interlinear.py` to create:
   - `.interlinear.txt` - Plain text word-by-word glosses
   - `.dcs-eng99.xml` - TEI XML format with glosses embedded
3. Uses `sanskrit_dictionary_lookup.py` to find word definitions
4. Looks up words in `dcs_sanskrit_morphology.csv` (4.7M entries with sandhi support)
5. Writes 540 files (2 per work) to `../data-sources/classicsviewer_interlinear/`

**Key components**:
- `batch_generate_interlinear.py` - Parallel orchestrator script
- `generate_sanskrit_interlinear.py` - Per-work XML/text generator
- `sanskrit_dictionary_lookup.py` - Dictionary lookup with sandhi splitting
- `dcs_sanskrit_morphology.csv` - Morphology database (word → lemma → gloss)
- `dcs_sanskrit_dictionary.csv` - Dictionary entries (lemma → definition)

**Performance**: ~90 seconds with 8 parallel workers for all 270 works

### Stage 2: Import Interlinear into Extended Database (create_perseus_database.py)

When building the extended database:

```bash
cd ../data-prep
python3 create_perseus_database.py extended
```

**What it does**:
1. Merges `sanskrit/sanskrit_texts.db` into Perseus database (all 270 works)
2. Scans `../data-sources/classicsviewer_interlinear/` for `*.dcs-eng99.xml` files
3. Parses TEI XML to extract word-by-word glosses
4. Creates `translation_segments` with translator "Interlinear (Beta, AI-generated from app dictionary)"
5. Uses book_id lookup that handles both:
   - Greek/Latin format: `tlg0012.tlg001.001` (tries work_id + book_number lookup)
   - Sanskrit/DCS format: Direct book_id like `21312` (tries direct construction first)

**Book ID Matching**:
The interlinear import was failing because XML files used book IDs from one database while the extended database merged from a different version. The fix (in `create_perseus_database.py` lines 3738-3757):

```python
# Try to construct book_id directly first (for Sanskrit DCS texts)
constructed_book_id = f"{work_id}.{book_n}"
cursor.execute("SELECT id FROM books WHERE id = ?", (constructed_book_id,))
result = cursor.fetchone()

if result:
    book_id = result[0]
else:
    # Fallback: Look up by work_id and book_number (for Greek/Latin)
    cursor.execute("SELECT id FROM books WHERE work_id = ? AND book_number = ?",
                   (work_id, int(book_n)))
```

This ensures both numbering schemes work correctly.

**Verification**: After extended database build completes, check:
```bash
sqlite3 perseus_texts_extended.db "SELECT COUNT(DISTINCT book_id) FROM translation_segments WHERE translator LIKE 'Interlinear%' AND book_id LIKE '%.%'"
# Should return 270 (all Sanskrit works)
```
