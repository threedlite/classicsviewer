# Sanskrit Database Build Guide

## Quick Start

```bash
cd sanskrit

# Single command - builds complete database automatically!
./run_build.sh

# Or manually with venv Python (required for multiprocessing):
nohup ./venv/bin/python3 create_sanskrit_database_interlinear.py > build_sanskrit.log 2>&1 &
tail -f build_sanskrit.log

# Build only the works listed in a CSV, into a separately named database
# (sanskrit_texts_<name>.db, interlinear_output_<name>/, build_sanskrit_<name>.log);
# the main database is untouched.  Used to test a change on a few works:
./run_build.sh full SANSKRIT_MAHABHARATA_TEST.csv mbhtest
```

**Output**: `sanskrit_texts.db.zip` (~486MB) with:
- 272 Sanskrit works with texts
- 179,806 dictionary entries
- 4,705,160 lemma mappings
- 494,931 interlinear translations with **Stanza NLP morph data** (case/number/gender, POS, dependencies)

**Build time**: ~95 minutes (fully automated, no manual intervention)
- DCS loading phase: ~75 minutes (8 parallel workers)
- Interlinear generation with Stanza NLP: ~20 minutes

**CRITICAL**: Always use `./run_build.sh` or `./venv/bin/python3` directly. Do NOT use `source venv/bin/activate` because multiprocessing workers spawn with system Python, not the activated venv. The build uses `fork` start method so workers inherit loaded Stanza models.

**Note**: Uses pre-built lexicon ZIP (`dcs_sanskrit_lexicon.zip`, 35 MB) that's already in the repo. You don't need to regenerate the lexicon unless you're updating DCS data or improving coverage.

## Prerequisites

- Python 3.8+: `pip install indic-transliteration`
- Data sources in `../data-sources/sanskrit/dcs/` (DCS CoNLL-U files)
- **Pre-built lexicon**: `dcs_sanskrit_lexicon.zip` (already checked into repo, no action needed)

## What the Script Does Automatically

The `create_sanskrit_database_interlinear.py` script is a **complete automated pipeline**:

1. ✅ **Creates database** with 272 Sanskrit texts (~96 min with 8 workers)
   - Bhagavad Gita from Wikisource JSON
   - Rig Veda from DCS pada format
   - 270 works from DCS CoNLL-U files, parsed by 8 worker processes that
     run Stanza on sentences without treebank data (see "Stanza models" below)

2. ✅ **Imports lexicon** from `dcs_sanskrit_lexicon.zip` (2 min)
   - 179,806 dictionary entries with transliterations
   - 4,705,160 word form → lemma mappings
   - 6 normalization patterns for text matching

3. ✅ **Generates interlinear XML with Stanza NLP** for all 272 works (~2 h)
   - Creates TEI XML files with word-by-word glosses
   - Uses **Stanza NLP** to add morphological data:
     - Case/number/gender (e.g., "acc s m" = accusative singular masculine)
     - POS tags (NOUN, VERB, ADJ, etc.)
     - Dependency relations (nsubj, obj, compound:coord, etc.)
   - Outputs to `interlinear_output/` directory: `.interlinear.txt` and
     `.dcs-eng99.xml` per work, written in one pass (each line fetched,
     Stanza-parsed and glossed once), to `.tmp` siblings that are renamed
     into place only when both are complete, so a killed worker never
     leaves a truncated XML for the import step
   - Uses parallel processing (8 workers) with `fork` start method
   - Pre-loads Stanza models before spawning workers

4. ✅ **Imports interlinear** into database (2 min)
   - Parses XML files to extract translations with morph data
   - Creates 494,931 interlinear segments (one per line)
   - Builds translation lookup table for efficient retrieval

5. ✅ **Compresses to ZIP** (1 min)
   - Creates `sanskrit_texts.db.zip` (~486 MB)
   - Ready for standalone use or merging into extended database

**No manual steps required! NEVER run intermediate scripts manually.**

## Important Notes

- **Schema**: Identical to extended database (100% compatible for merging)
- **Standalone**: Database includes all lexicon data, works without extended DB
- **Merge-ready**: Can be merged into extended database using `merge_database.py`
- **Interlinear**: All 272 works have word-by-word interlinear translations

## Database Contents

**Full mode** includes all 272 works total:
- **Bhagavad Gita** (18 chapters, Wikisource with English translations)
  - Source: Sanskrit Wikisource (CC BY-SA 4.0)
  - Parsed from downloaded HTML via `data-sources/parse_bhagavad_gita_sanskrit.py`
  - Creates JSON intermediate: `data-sources/bhagavad_gita_sanskrit.json`
  - Translations: Edwin Arnold (prose, Public Domain), Annie Besant (verse-by-verse, Public Domain)
  - Work ID: `bhagavad_gita_wikisource`, Author ID: `vyasa_wikisource`
- **Rig Veda** (10 maṇḍalas, complete with Griffith translation)
  - Source: DCS pada-and-analysis.dat format from `../data-sources/sanskrit/dcs/data/rigveda/`
  - Translation: Ralph T.H. Griffith (1896, Public Domain), English Wikisource
    transcription fetched and parsed by `data-sources/download_rigveda_griffith.py`
    and `parse_rigveda_griffith.py` (the build runs them when the file is missing)
  - Work ID: `rigveda_pada`, Author ID: `rishis_pada`
- **270 DCS works**: Including Upanishads, Vedas, epics, philosophical texts, and more
  - Source: DCS CoNLL-U files from `../data-sources/sanskrit/dcs/conllu/`
  - Most works are Sanskrit-only (no English translations)
  - Works whose DCS chapter headers have three or more parts (97 three-part,
    23 four-part, 2 five-part) are loaded one line per DCS verse
    (`# sent_counter`), with a `[book.chapter.verse]` citation prefix on the
    line like the Rig Veda; two-part works are one line per sentence.
    Books and chapters follow DCS file order; non-numeric labels keep their
    text (e.g. `[6.BhaGī 1.1]`) and books with non-numeric labels are
    numbered by order of appearance (label kept for display).
  - **Mahābhārata**: Ganguli's English translation (Project Gutenberg
    15474–15477) is attached per critical-edition chapter through
    `data-sources/mbh_ce_ganguli_concordance.csv`; see
    `mahabharata_ganguli.py` and `data-sources/SOURCES.md`. The Gutenberg
    files are downloaded by the build when missing. Any inconsistency in
    the texts or the table fails the build.
  - **Chāndogyopaniṣad**: Müller's translation (Sacred Books of the East
    vol. 1, Wikisource) is attached per khaṇḍa through `translation_map`;
    the files are fetched and parsed by `data-sources/download_chandogya_mueller.sh`
    and `parse_chandogya_mueller.py` when missing. A mapped translation that
    yields no segment fails the build. The translation files in the DCS
    repository itself are not used (`LICENSE_COMPLIANCE.md` section 9).
  - **Thirteen further works** take their English translation from the
    registry in `data-sources/translation_sources.py` (Project Gutenberg and
    English Wikisource; the Rāmāyaṇa through `data-sources/ramayana_dutt.py`).
    The build fetches and parses them on demand for the works it includes;
    `python3 data-sources/translation_sources.py --check` compares each
    parser's keys with the DCS labels. Coverage per work is in
    `data-sources/SOURCES.md`.

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
tail -f build.log  # Monitor (~3 h 45 min)

# Verify output
ls -lh sanskrit_texts.db.zip  # Should be ~486 MB
ls -lh interlinear_output/*.dcs-eng99.xml | wc -l  # Should be 272 files
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

**Full Database**: 272 works, 495K verse lines, 5.9M words, ~486MB compressed
**Build time**: ~3 h 45 min total (fully automated; measured 2026-10-10)
  - DCS loading phase: ~96 minutes (8 parallel workers)
  - Interlinear generation with Stanza NLP: ~2 hours (7,297 s)
  - Import and compression: ~2 minutes

**Interlinear Coverage**:
- Dictionary coverage: **99.8%** words found
- Morph data (case/number/gender): Available for all words processed by Stanza
- POS tags and dependencies: Added by Stanza NLP

**Morph Data Format**:
```
| lemma [case number gender] ~ POS deprel head sentPos |
```
Example: `| पूर्व voc s m ~ ADJ conj 1 3 |`
- `voc s m` = vocative singular masculine
- `ADJ` = adjective POS tag
- `conj 1 3` = conjunction relation, head word 1, sentence position 3

**Data Sources**:
- DCS CoNLL-U corpus: 15,900 files, 270 works
- DCS dictionary: 164K lemmas
- DCS morphology: 4.7M mappings (with sandhi)
- Bhagavad Gita: Wikisource (parsed from HTML to JSON)
- Rig Veda: DCS pada-and-analysis.dat (TSV format)
- English translations: Bhagavad Gita (Arnold, Besant), Rig Veda (Griffith), Mahabharata (Ganguli), Chāndogya Upaniṣad (Müller)

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
- **Translation**: `data-sources/wikisource/rigveda_griffith.txt` (generated from Wikisource by `data-sources/download_rigveda_griffith.py` + `parse_rigveda_griffith.py`)
- **Format**: Tab-separated with columns: book, hymn, stanza, pada, text
- **Workflow**: `load_rigveda()` function reads TSV, converts IAST to Devanagari, creates work with author `rishis_pada`

### 3. DCS Works (CoNLL-U → Database)
- **Source**: 15,733 CoNLL-U files from DCS corpus
- **Import**: `create_sanskrit_database_interlinear.py` reads directly
- **Location**: `../data-sources/sanskrit/dcs/conllu/`
- **Format**: CoNLL-U morphological annotation format
- **Workflow**: `load_dcs_texts()` function processes all 270 works

### 4. Mahabharata translation (Gutenberg text + concordance CSV → Database)
- **Download**: `data-sources/download_ganguli.sh` fetches the four Gutenberg
  volumes into `data-sources/ganguli/` (the build runs it when they are missing)
- **Verify**: `mahabharata_ganguli.py` strips the Gutenberg boilerplate and
  checks a SHA-256 of the remaining text
- **Parse**: books, section headings (roman or bare arabic), footnotes
- **Align**: `data-sources/mbh_ce_ganguli_concordance.csv` (generated once
  by `data-sources/extract_mbh_concordance.py` from the Brodbeck & Black
  appendix) maps critical-edition chapters to Ganguli sections; segments
  span the lines of the chapters each section is attached to
- **Workflow**: `write_parsed_work_to_db()` calls
  `mahabharata_ganguli.write_ganguli_translation()` after writing the
  Mahābhārata lines; the report it prints lists every merged heading,
  interval placement and rejected row

All four sources are integrated into a single `sanskrit_texts.db` with consistent schema.

## Interlinear Generation Pipeline

After building the database, interlinear translations are generated in two stages:

### Stage 1: Generate Interlinear XML Files (batch_generate_interlinear.py)

**This is called automatically by `create_sanskrit_database_interlinear.py` - NEVER run manually!**

```bash
# Called internally by the main build script:
python3 batch_generate_interlinear.py sanskrit_texts.db \
  --output interlinear_output \
  --parallel 8
```

**What it does**:
1. Pre-loads **Stanza Sanskrit NLP models** before spawning workers
2. Uses `fork` multiprocessing start method so workers inherit loaded models
3. For each work, calls `generate_sanskrit_interlinear.py` to create:
   - `.interlinear.txt` - Plain text word-by-word glosses
   - `.dcs-eng99.xml` - TEI XML format with glosses and **morph data**
4. Uses `sanskrit_dictionary_lookup.py` to find word definitions
5. Uses **Stanza NLP** (`stanza.Pipeline('sa')`) to add:
   - Case/number/gender (e.g., "nom s m")
   - POS tags (NOUN, VERB, ADJ, PART, etc.)
   - Dependency relations (nsubj, obj, compound:coord, etc.)
6. Writes 540 files (2 per work) to `interlinear_output/`

**Key components**:
- `batch_generate_interlinear.py` - Parallel orchestrator with Stanza pre-loading
- `generate_sanskrit_interlinear.py` - Per-work XML/text generator with Stanza integration
- `sanskrit_dictionary_lookup.py` - Dictionary lookup with sandhi splitting
- **Stanza NLP** - Sanskrit language models for morphological analysis

**Critical Implementation Details**:
- Uses `mp.set_start_method('fork')` so workers inherit loaded Stanza models
- Pre-loads Stanza before `mp.Pool()` creation
- Without this fix, workers spawn with system Python and can't access Stanza

**Performance**: ~2 hours with 8 parallel workers for all 272 works (slower due to Stanza NLP processing)

### Stanza models

Stanza's Sanskrit models live in `~/Library/Caches/stanza/<version>/resources/sa/`
(or `~/stanza_resources/` on Linux). The rule in every build step is:

- **Only the main process downloads.** Before a worker pool starts, the main
  process calls `stanza.download('sa')` once and loads a pipeline to verify the
  files. `stanza.download` rewrites every model file it fetches, so it must
  never run while another process is reading the models.
- **Workers never download.** Worker processes create their pipeline with
  `stanza.Pipeline('sa', ..., download_method=None)`, which loads the files
  the main process verified and refuses to fetch anything.
- **A model that fails to load stops the build.** There is no fallback to an
  empty parse: a worker, the pre-load, or the serial loader raises, the pool
  propagates the error, and the build exits with a traceback in the log. A
  database with missing trees must never be produced silently.

Symptom this rule prevents: a line `ERROR: Cannot load model from .../sa/depparse/vedic_nocharlm.pt`
in the log while the model files' modification times keep changing. That means
a process is re-downloading the models while others read them; if you see it,
the build script has regressed on this rule.

### Stage 2: Import Interlinear into Extended Database (create_perseus_database.py)

When building the extended database:

```bash
cd ../data-prep
python3 create_perseus_database.py extended
```

**What it does**:
1. Merges `sanskrit/sanskrit_texts.db` into Perseus database (all 272 works)
2. Scans `../data-sources/classicsviewer_interlinear/` for `*.dcs-eng99.xml` files
3. Parses TEI XML to extract word-by-word glosses
4. Creates `translation_segments` with translator "Interlinear (AI-generated from app dictionary)"
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
