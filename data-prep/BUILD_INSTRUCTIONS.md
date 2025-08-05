# Perseus Database Build Instructions

This document describes how to build the perseus_texts.db database from scratch with full morphological support and comprehensive lemmatization.

**Last Updated**: August 2025
**Database Version**: 2.0
**Coverage**: ~90% token coverage on Homer, ~98% unique word coverage

## Prerequisites

Before building, ensure you have the following files in place:

### 1. Perseus Digital Library Data (in `data-sources/`)
- `canonical-greekLit/` - Greek texts repository
- `canonical-latinLit/` - Latin texts repository  
- `canonical-pdlrefwk/` - Reference works (dictionaries)
- `perseus_catalog/` - Catalog metadata

### 2. Wiktionary Dumps (in `data-sources/`)
Download these files from Wikimedia dumps:
- `enwiktionary-latest-pages-articles.xml.bz2` - English Wiktionary (~1.4GB)
  - https://dumps.wikimedia.org/enwiktionary/latest/
- `elwiktionary-latest-pages-articles.xml.bz2` - Greek Wiktionary (~98MB)
  - https://dumps.wikimedia.org/elwiktionary/latest/

## Build Process

The build process consists of several steps that extract morphological data and create an optimized database:

## Build Architecture

The build system consists of two main scripts:

1. **`build_database.py`** - Master orchestrator
   - Entry point for the entire build process
   - Calls `create_perseus_database.py` for base database
   - Adds all Wiktionary enhancements
   - Generates final statistics and OBB file

2. **`create_perseus_database.py`** - Base database builder (~2,400 lines)
   - Parses Perseus XML texts from `data-sources/` folder
   - Processes LSJ Greek dictionary
   - Creates core database schema
   - Implements basic Greek lemmatization
   - Extracts translations where available

### Quick Build
```bash
cd data-prep
python3 build_database.py
```

This single command runs the complete build process (~10-15 minutes):
1. Creates base database with Perseus texts and LSJ dictionary
2. Adds 15,592 Wiktionary inflection mappings
3. Adds 37,119 Greek Wiktionary declension mappings
4. Generates nu-movable verb variants
5. Adds supplemental Wiktionary definitions for missing lemmas
6. Optimizes database and creates Android OBB file

### Manual Wiktionary Extraction (if needed)

The build process uses pre-extracted Wiktionary data. If you need to re-extract:

1. **Extract English Wiktionary inflections**
   ```bash
   python3 wiktionary-processing/extract_inflection_of_template.py
   ```
   Creates: `wiktionary-processing/greek_inflection_of_mappings.json`

2. **Extract Greek Wiktionary morphological forms**
   ```bash
   python3 wiktionary-processing/extract_greek_wiktionary_fixed.py
   ```
   Creates: `wiktionary-processing/ancient_greek_all_morphology_correct.json`

3. **Extract all Ancient Greek forms** (NEW)
   ```bash
   python3 wiktionary-processing/extract_all_ancient_greek_forms.py
   ```
   Creates: `wiktionary-processing/ancient_greek_all_forms.json`

4. **Generate declension mappings**
   ```bash
   python3 wiktionary-processing/extract_declension_mappings.py
   ```
   Creates: `wiktionary-processing/ancient_greek_declension_mappings.json`

5. **Build main database**
   ```bash
   python3 create_perseus_database.py
   ```
   This single command now:
   - Builds texts and dictionaries
   - Runs Wiktionary extraction if needed
   - Loads all morphological mappings
   - Generates algorithmic lemmatizations for ALL words
   - Optimizes to keep only words in texts
   - Creates final database with multiple lemmas per word

## Intermediate Files

The build process creates these intermediate files in `wiktionary-processing/`:

1. **greek_inflection_of_mappings.json** (~150KB)
   - Inflection mappings from English Wiktionary
   - Contains ~326 unique mappings

2. **ancient_greek_all_forms.json** (~3MB)
   - ALL Ancient Greek non-lemma forms from English Wiktionary
   - Contains ~16,399 mappings

3. **ancient_greek_all_morphology_correct.json** (~350KB)
   - Morphological forms from Greek Wiktionary
   - Contains ~2,119 unique mappings

4. **ancient_greek_declension_mappings.json** (~4MB)
   - Generated declension forms from Greek templates
   - Contains ~37,155 unique mappings

These files are kept so you can rebuild the database without re-parsing the Wiktionary dumps (which is slow).

## Output

The final `perseus_texts.db` contains:

- **Greek authors**: 63 authors
- **Greek works**: ~700 works  
- **Text lines**: ~300,000 lines
- **Unique Greek words**: 179,325 forms
- **Dictionary entries**: 28,300+ LSJ entries + Wiktionary supplements
- **Lemma mappings**: 96,875 total
  - LSJ-based: ~15,000
  - Wiktionary inflections: 15,592
  - Greek Wiktionary: 37,119
  - Nu-movable variants: ~29,000
- **Coverage**: 
  - Unique word coverage: ~98.3%
  - Token coverage on Homer: ~90.4%
- **Database size**: ~780MB

### Morphological Information Includes:
- Case and number (e.g., "genitive singular", "accusative plural")
- Part of speech (e.g., "noun", "verb", "adjective")
- Gender for adjectives (e.g., "masculine nominative singular")

## Database Schema

Key tables for morphology:

```sql
CREATE TABLE lemma_map (
    word_form TEXT NOT NULL,          -- inflected form (normalized)
    word_normalized TEXT NOT NULL,    -- same as word_form
    lemma TEXT NOT NULL,              -- dictionary headword (normalized)
    confidence REAL NOT NULL,         -- confidence score
    source TEXT NOT NULL,             -- data source
    morph_info TEXT,                  -- grammatical information
    PRIMARY KEY (word_form, lemma)
);
```

## Customization

To add more morphological data:

1. Add new extraction scripts in `wiktionary-processing/`
2. Update `create_perseus_database.py` to load your JSON files
3. Ensure your mappings include `morph_info` field
4. Rebuild the database

## Troubleshooting

- **"No such file or directory"**: Ensure you're in the `data-prep` directory
- **"Missing prerequisites"**: Check that all data files are in place
- **Memory errors**: The Wiktionary parsing uses ~2GB RAM
- **Slow extraction**: Wiktionary parsing takes 5-10 minutes per dump

## Database Schema

Key tables:

```sql
-- Authors and works
CREATE TABLE authors (id, name, language)
CREATE TABLE works (id, title, author_id)  
CREATE TABLE books (id, work_id, book_number)
CREATE TABLE text_lines (id, book_id, line_number, line_text)

-- Word analysis
CREATE TABLE word_forms (word, word_normalized, book_id, line_number, word_position)
CREATE TABLE lemma_map (word_form, word_normalized, lemma, morph_info, source, confidence)

-- Dictionary
CREATE TABLE dictionary_entries (id, headword, headword_normalized, language, entry_html, entry_plain)

-- Translations
CREATE TABLE translation_segments (id, book_id, start_line, end_line, translation_text, translator)
```

## Deployment

The build creates:
- `perseus_texts.db` - SQLite database
- `output/main.1.com.classicsviewer.app.debug.obb` - Android OBB file

Deploy to Android:
```bash
adb push output/main.1.com.classicsviewer.app.debug.obb \
    /storage/emulated/0/Android/obb/com.classicsviewer.app.debug/
```