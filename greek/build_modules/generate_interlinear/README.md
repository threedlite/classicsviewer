# Interlinear Translation Generator

This module generates word-by-word interlinear translations for Greek texts with English glosses.

## Module Architecture

### Core Files

1. **`ui_dictionary_lookup.py`** - Production dictionary lookup module
   - Contains `PerseusRepository` class with dictionary lookup logic
   - Replicates exact Android UI dictionary behavior (normalization, precedence, sorting)
   - **Used by**: `generate_interlinear.py` imports and uses this for all word lookups
   - **Also runnable**: Can be run standalone to test dictionary lookups (`python3 ui_dictionary_lookup.py`)

2. **`generate_interlinear.py`** - Interlinear generation engine
   - Contains `InterlinearGenerator` class that generates interlinear glosses
   - Imports `PerseusRepository` from `ui_dictionary_lookup.py`
   - Features streaming architecture (processes one book at a time)
   - LRU caching for dictionary lookups (95%+ query reduction)
   - Single-threaded, no threading within this module
   - Can be run standalone for single work: `python3 generate_interlinear.py tlg0012.tlg001`

3. **`interlinear_list.py`** - Batch coordinator with multiprocessing
   - Reads CSV file listing multiple works to process
   - Spawns worker processes (default: 4 workers)
   - Each worker loads `generate_interlinear.py` and processes one work
   - Distributes load across workers for parallel generation
   - Usage: `python3 interlinear_list.py WORKS.csv DATABASE.db --workers 4`

### Architecture Summary

```
interlinear_list.py (coordinator)
├── Worker 1 → generate_interlinear.py → ui_dictionary_lookup.py → database queries
├── Worker 2 → generate_interlinear.py → ui_dictionary_lookup.py → database queries
├── Worker 3 → generate_interlinear.py → ui_dictionary_lookup.py → database queries
└── Worker 4 → generate_interlinear.py → ui_dictionary_lookup.py → database queries
```

**Key principles:**
- NO threading in `generate_interlinear.py` (completely single-threaded)
- Multiprocessing ONLY in `interlinear_list.py` (spawns workers)
- Each worker has its own database connection and LRU cache
- Streaming architecture: process and write one book at a time

## Separation from Database Build

**IMPORTANT:** As of 2025-11-04, interlinear generation is **NO LONGER** part of the database build process.

### New Workflow

**Step 1: Generate Interlinear XML Files (ONE TIME)**
```bash
cd data-prep

# Generate XML files for all canonical works
python3 build_modules/generate_interlinear/interlinear_list.py \
    INTERLINEAR_WORKS.csv \
    perseus_texts_extended.db \
    --workers 4 \
    --output ../greek/interlinear_output
```

**Output:** 14 works × 2 files each (XML + TXT) = 28 files in `greek/interlinear_output/`

**Step 2: Build Database (USES PREGENERATED FILES)**
```bash
cd data-prep

# Full mode - imports 12 select works
python3 create_perseus_database.py full

# Extended mode - imports 14 works (default)
python3 create_perseus_database.py extended

# Extended mode - import ALL Greek works
python3 create_perseus_database.py extended --interlineate
```

**Default source:** `greek/interlinear_output/`

### Why This Change

1. **Reliability**: Generation was causing worker hangs and file write failures during builds
2. **Speed**: Database builds are faster without generation (~5-10 min saved)
3. **Separation of Concerns**: Generation and import are now separate steps
4. **Reproducibility**: Pregenerated files ensure consistent output across builds

See `DATABASE_BUILD_INTERLINEAR_CHANGE.md` for full details.

### Output Files

Generated files are placed in `greek/interlinear_output/`:

- `tlg0012.tlg001.perseus-eng99.xml` - Homer Iliad TEI XML
- `tlg0012.tlg001.txt` - Iliad plain text
- `tlg0012.tlg002.perseus-eng99.xml` - Homer Odyssey TEI XML
- `tlg0012.tlg002.txt` - Odyssey plain text
- ... (12 more works)

## API

### generate_interlinear_translations()

```python
def generate_interlinear_translations(db_path: Path, output_dir: Path, works=None):
    """
    Generate interlinear translations for Homer's works

    Args:
        db_path: Path to the Perseus database
        output_dir: Directory where XML files will be written
        works: List of works to process (e.g., ['iliad', 'odyssey']).
               If None, processes both.
    """
```

### Features

- **Exact Android UI dictionary logic**: Uses `ui_dictionary_lookup.py` for consistency
- **HTML table formatting**: Each word formatted as a table for proper display
- **TEI XML output**: Perseus-compatible XML format
- **Plain text output**: Pipe-delimited format for easy analysis

## Output Format

### XML Format (used in app)

Each word is formatted as an HTML table:

```xml
<table><tr><td>μῆνιν</td></tr><tr><td><b>wrath, anger</b></td></tr><tr><td>μῆνις acc s</td></tr></table>
<table><tr><td>ἄειδε</td></tr><tr><td><b>to sing</b></td></tr><tr><td>ἀείδω 2 s pres actv impr</td></tr></table>
```

This renders as:

| μῆνιν |
|-------|
| **wrath, anger** |
| μῆνις acc s |

| ἄειδε |
|-------|
| **to sing** |
| ἀείδω 2 s pres actv impr |

### Text Format (for debugging)

```
1. μῆνιν | ἄειδε | θεὰ
wrath, anger | to sing | a goddess

```

## Dictionary Lookup

The `ui_dictionary_lookup.py` module contains the `PerseusRepository` class which implements dictionary lookup logic matching the Android app exactly:

### Lookup Flow

1. **Normalization**: Apostrophes, grave→acute conversion, ultra-normalization (diacritic removal)
2. **Direct match**: Check `dictionary_entries` table for exact headword match
3. **Lemma mapping**: Check `lemma_map` table for inflected forms → lemmas
4. **Lemma chain resolution**: Follow lemma chains to find canonical dictionary entries
5. **Ultra-normalized fallback**: If still no match, try removing all diacritics
6. **Sorting**: Apply multi-level sorting (non-treebank first, source priority, confidence, length)

### Source Priority

1. User-defined entries (highest)
2. LSJ (Liddell-Scott-Jones)
3. Cunliffe (Homeric Lexicon)
4. Wiktionary
5. Other sources (lowest)

### LRU Caching (NEW)

As of 2025-11-04, dictionary lookups use `@lru_cache(maxsize=10000)` to cache results:
- Common words (καί, δέ, τε, etc.) only queried once
- Reduces ~100,000+ queries to ~few thousand for large works like Homer's Iliad
- Each worker process has its own cache (no shared state)
- 95%+ query reduction, 2-5x speedup expected

### Testing Dictionary Lookups

Run `ui_dictionary_lookup.py` standalone to test lookups:

```bash
# Test first 7 lines of Iliad (default)
python3 ui_dictionary_lookup.py

# Test first 30 lines
python3 ui_dictionary_lookup.py 30
```

This shows the exact dictionary results that would appear in the Android UI for each word.

## Next Steps

The interlinear translations can now be:
- Imported into the Android app database
- Used for study tools and language learning features
- Exported to other formats as needed
