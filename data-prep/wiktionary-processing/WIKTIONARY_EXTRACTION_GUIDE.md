# Wiktionary Extraction Guide

## Overview

This guide documents the current process for extracting Ancient Greek morphological data from Wiktionary. The system combines multiple extraction methods to build a comprehensive morphology database with lemma mappings, verb conjugations, and noun declensions.

## Architecture

The extraction pipeline uses a two-stage approach:
1. **One-time cache creation**: Extract all Greek pages from Wiktionary dumps
2. **Multiple specialized extractors**: Parse different types of morphological information

## Data Sources

- **English Wiktionary** (`enwiktionary-latest-pages-articles.xml.bz2`): Primary source for inflections and morphology
- **Greek Wiktionary** (`elwiktionary-latest-pages-articles.xml.bz2`): Source for declension templates
- **Cached Greek pages** (`all_greek_wiktionary_pages.json`): Pre-extracted Greek content

## Current Pipeline

The extraction is handled by `combine_all_ancient_greek_morphology.py`, which runs these scripts in order:

### 1. Initial Setup

```bash
# Download Wiktionary dumps (if not already present)
cd data-sources/
wget https://dumps.wikimedia.org/enwiktionary/latest/enwiktionary-latest-pages-articles.xml.bz2
wget https://dumps.wikimedia.org/elwiktionary/latest/elwiktionary-latest-pages-articles.xml.bz2
```

### 2. One-Time Greek Page Extraction

```bash
# Extract all Greek pages from English Wiktionary (only needed once)
python3 extract_all_greek_pages.py
```

**What it does:**
- Scans the entire English Wiktionary dump ONCE
- Extracts pages with Greek characters in the title
- Filters for pages with Ancient Greek or Greek sections
- Creates `all_greek_wiktionary_pages.json` (~46MB, 124k pages)

**Performance:**
- Time: ~10 minutes
- Output: 124,116 Greek pages

### 3. Morphology Extraction Scripts

These scripts are run automatically by `combine_all_ancient_greek_morphology.py`:

#### a. `extract_ancient_greek_conjugations.py`
- Extracts verb conjugation tables from Wiktionary
- Parses templates like `{{grc-conj}}` for full verb paradigms
- Output: `ancient_greek_verb_conjugations.json`

#### b. `extract_ancient_greek_declensions.py`
- Extracts noun and adjective declension tables
- Parses templates like `{{grc-decl}}` for full declension paradigms
- Output: `ancient_greek_noun_declensions.json`

#### c. `extract_all_ancient_greek_words_with_diacritics.py`
- Extracts all Ancient Greek words preserving diacritics
- Identifies standalone lemmas (adverbs, particles, etc.)
- Output: `ancient_greek_morphology_with_diacritics.json`

#### d. `extract_inflection_of_template.py`
- Extracts mappings from `{{inflection of}}` templates
- Requires English Wiktionary dump
- Output: `greek_inflection_of_mappings.json`

#### e. `extract_declension_mappings.py`
- Extracts mappings from Greek Wiktionary declension templates
- Requires Greek Wiktionary dump
- Output: `ancient_greek_declension_mappings.json`

### 4. Combined Morphology Output

`combine_all_ancient_greek_morphology.py` merges all sources into:
- `ancient_greek_morphology_complete.json` - Unified morphology database

## Running the Complete Pipeline

### Full Extraction (From Scratch)

```bash
cd data-prep/wiktionary-processing

# Run the complete morphology extraction
python3 combine_all_ancient_greek_morphology.py
```

This will:
1. Check for `all_greek_wiktionary_pages.json` (create if missing)
2. Run all extraction scripts in order
3. Combine results into a unified morphology database

### Integration with Database Build

The morphology data is automatically used by the main database creation:

```bash
cd data-prep
python3 create_perseus_database.py sample  # or 'full'
```

## Key Components

### Greek Normalization

All scripts use consistent Greek normalization:
```python
def normalize_greek(text):
    """Normalize Greek text for matching"""
    if not text:
        return ""
    # Decompose to NFD
    text = unicodedata.normalize('NFD', text)
    # Remove diacritics
    text = ''.join(c for c in text if not unicodedata.combining(c))
    # Lowercase
    text = text.lower()
    # Replace final sigma
    text = text.replace('ς', 'σ')
    # Keep only Greek letters
    text = ''.join(c for c in text if c.isalpha() 
                   and ('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff'))
    return text
```

### Direct Import Architecture

The pipeline uses direct Python imports instead of subprocess calls:
```python
# In combine_all_ancient_greek_morphology.py
import extract_ancient_greek_conjugations
import extract_ancient_greek_declensions
import extract_all_ancient_greek_words_with_diacritics
import extract_inflection_of_template
import extract_declension_mappings

# Run each extractor
for extract_func, description in extractions:
    print(f"\n{description}...")
    try:
        extract_func()  # Direct function call
        print(f"✓ {description} completed successfully")
    except Exception as e:
        print(f"ERROR: {description} failed: {str(e)}")
        raise RuntimeError(f"Extraction failed: {description}") from e
```

### Fail-Fast Error Handling

All scripts follow a strict no-silent-failures policy:
```python
# Check for required files
if not dump_file.exists():
    print(f"ERROR: Required dump file {dump_file} not found!")
    raise FileNotFoundError(f"Wiktionary dump file required: {dump_file}")

# Never create empty default files
if not morphology_file.exists():
    raise FileNotFoundError(f"Required morphology file missing: {morphology_file}")
```

## Output Files

The extraction process generates these JSON files:

| File | Description | Typical Size |
|------|-------------|--------------|
| `all_greek_wiktionary_pages.json` | Cached Greek pages from English Wiktionary | ~46MB |
| `ancient_greek_verb_conjugations.json` | Verb paradigms with full conjugations | ~27MB |
| `ancient_greek_noun_declensions.json` | Noun/adjective declension paradigms | ~23MB |
| `ancient_greek_morphology_with_diacritics.json` | All words preserving diacritics | ~9MB |
| `greek_inflection_of_mappings.json` | Inflection mappings from templates | ~160KB |
| `ancient_greek_declension_mappings.json` | Greek Wiktionary declensions | ~12MB |
| `ancient_greek_morphology_complete.json` | Combined morphology database | ~50MB |

## Performance

- **Initial cache creation**: ~10 minutes (one-time only)
- **Full morphology extraction**: ~5 minutes
- **Database integration**: Automatic during `create_perseus_database.py`

## Important Notes

1. **Required Files**: The pipeline will fail immediately if required dump files are missing
2. **No Silent Failures**: Any missing file or error will stop the entire process
3. **Regeneration**: All morphology files are regenerated fresh each time (except the Greek pages cache)
4. **Direct Imports**: No subprocess calls - all scripts are imported directly for better error handling

## Troubleshooting

### Missing Dump Files
```
ERROR: Required dump file .../enwiktionary-latest-pages-articles.xml.bz2 not found!
```
**Solution**: Download the required dumps to the `data-sources/` directory

### Greek Pages Cache Missing
```
ERROR: Cache file all_greek_wiktionary_pages.json not found!
```
**Solution**: Run `extract_all_greek_pages.py` to create the cache

