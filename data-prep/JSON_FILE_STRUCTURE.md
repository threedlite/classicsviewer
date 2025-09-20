# JSON File Structure Documentation

This document describes all JSON files created during the Classics Viewer database build process. Each JSON file is now named after the Python module that creates it, making it easy to trace data flow through the pipeline.

## Overview

The database creation pipeline generates 14 JSON files that work together to create comprehensive Ancient Greek morphology and dictionary data. The files are organized into two main categories:

1. **Wiktionary Processing Files** - Extract morphological data from Wiktionary
2. **Data Preparation Files** - Process dictionary sources and create final mappings

## Pipeline Flow Diagram

```
Wiktionary Dump → all_greek_wiktionary_pages.json (cache)
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ Parallel Extraction (from cache):                          │
│ - extract_ancient_greek_conjugations.json                  │
│ - extract_ancient_greek_declensions.json                   │
│ - extract_declension_mappings.json                         │
│ - extract_inflection_of_template.json                      │
│ - extract_all_ancient_greek_words_with_diacritics.json    │
└─────────────────────────────────────────────────────────────┘
                   ↓
         combine_all_ancient_greek_morphology.json
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ Dictionary Extraction (parallel):                           │
│ - extract_cunliffe_new.json                               │
│ - extract_lsj_fixed.json                                  │
│ - extract_wiktionary_final.json                           │
└─────────────────────────────────────────────────────────────┘
                   ↓
         combine_dictionaries_to_lemma_map_1.json (dictionary entries)
         combine_dictionaries_to_lemma_map_2.json (lemma mappings)
                   ↓
         add_grave_accent_variants.json
                   ↓
         add_enclitic_variants.json (FINAL)
```

## Wiktionary Processing Files

### 1. `all_greek_wiktionary_pages.json`
- **Created by**: `extract_all_greek_pages.py`
- **Size**: ~46MB
- **Contents**: Cache of ~124,000 Greek pages from English Wiktionary XML dump
- **Format**: Dictionary mapping page titles to full page content
- **Special**: This is the only file preserved between runs; all others are regenerated
- **Purpose**: Avoids re-parsing the massive Wiktionary XML dump for each extraction script

### 2. `extract_ancient_greek_conjugations.json`
- **Created by**: `extract_ancient_greek_conjugations.py`
- **Processing time**: ~2 seconds
- **Contents**: Verb conjugation paradigms - maps inflected forms to lemmas
- **Format**: `{inflected_form: {lemma, conjugation_details}}`
- **Example**: `"ἔλυσα": {"lemma": "λύω", "mood": "indicative", "tense": "aorist", ...}`
- **Used by**: `combine_all_ancient_greek_morphology.py`

### 3. `extract_ancient_greek_declensions.json`
- **Created by**: `extract_ancient_greek_declensions.py`
- **Processing time**: ~2 seconds
- **Contents**: Noun and adjective declension paradigms
- **Format**: `{declined_form: {lemma, case, number, gender}}`
- **Example**: `"ἀνθρώπου": {"lemma": "ἄνθρωπος", "case": "genitive", "number": "singular"}`
- **Used by**: `combine_all_ancient_greek_morphology.py`

### 4. `extract_declension_mappings.json`
- **Created by**: `extract_declension_mappings.py`
- **Processing time**: ~100 seconds
- **Contents**: Additional declension patterns from Greek Wiktionary templates
- **Purpose**: Supplements English Wiktionary data with Greek Wiktionary patterns
- **Used by**: `combine_all_ancient_greek_morphology.py`

### 5. `extract_inflection_of_template.json`
- **Created by**: `extract_inflection_of_template.py`
- **Processing time**: ~90 seconds
- **Contents**: Morphological mappings from Wiktionary's "inflection of" templates
- **Format**: Maps inflected forms to lemmas with grammatical information
- **Used by**: `combine_all_ancient_greek_morphology.py`

### 6. `extract_all_ancient_greek_words_with_diacritics.json`
- **Created by**: `extract_all_ancient_greek_words_with_diacritics.py`
- **Processing time**: ~3 seconds
- **Contents**: All Ancient Greek words preserving diacritical marks
- **Purpose**: Comprehensive word list with proper accentuation
- **Used by**: `combine_all_ancient_greek_morphology.py`, `extract_wiktionary_final.py`

### 7. `combine_all_ancient_greek_morphology.json`
- **Created by**: `combine_all_ancient_greek_morphology.py`
- **Processing time**: ~3-4 minutes total
- **Contents**: Unified morphology database merging all sources above
- **Features**:
  - Deduplicates entries from multiple sources
  - Adds grave accent variants (e.g., πολλὰς → πολύς)
  - Comprehensive lemma mappings for all word forms
- **Used by**: `combine_dictionaries_to_lemma_map.py`, database creation

## Data Preparation Files

### 8. `extract_cunliffe_new.json`
- **Created by**: `extract_cunliffe_new.py`
- **Contents**: Dictionary entries from Cunliffe's Homeric Lexicon
- **Purpose**: Specialized vocabulary for Homer's epics
- **Format**: `{lemma: {definition, usage_notes, references}}`
- **Used by**: `combine_dictionaries_to_lemma_map.py`, `extract_wiktionary_final.py`

### 9. `extract_lsj_fixed.json`
- **Created by**: `extract_lsj_fixed.py`
- **Contents**: Liddell-Scott-Jones Greek-English Lexicon entries
- **Purpose**: Comprehensive Ancient Greek dictionary (primary source)
- **Format**: `{lemma: {definition, etymology, citations}}`
- **Used by**: `combine_dictionaries_to_lemma_map.py`, `extract_wiktionary_final.py`

### 10. `extract_wiktionary_final.json`
- **Created by**: `extract_wiktionary_final.py`
- **Contents**: Wiktionary definitions not found in LSJ or Cunliffe
- **Purpose**: Supplements traditional dictionaries with modern entries
- **Features**: Avoids duplicating entries already in LSJ/Cunliffe
- **Used by**: `combine_dictionaries_to_lemma_map.py`

### 11. `combine_dictionaries_to_lemma_map_1.json`
- **Created by**: `combine_dictionaries_to_lemma_map.py` (first output)
- **Contents**: Merged dictionary entries from all sources
- **Format**: `{lemma: {definition, source, metadata}}`
- **Purpose**: Complete dictionary database for the app
- **Used by**: Database creation process

### 12. `combine_dictionaries_to_lemma_map_2.json`
- **Created by**: `combine_dictionaries_to_lemma_map.py` (second output)
- **Contents**: Initial word-to-lemma mappings
- **Format**: `{word_form: lemma}`
- **Purpose**: Base mapping table before variants are added
- **Used by**: `add_grave_accent_variants.py`

### 13. `add_grave_accent_variants.json`
- **Created by**: `add_grave_accent_variants.py`
- **Contents**: Lemma mappings with grave accent variants added
- **Purpose**: Handles Greek grave accents on final syllables
- **Example**: Adds πολλὰς → πολύς (from πολλάς)
- **Used by**: `add_enclitic_variants.py`

### 14. `add_enclitic_variants.json`
- **Created by**: `add_enclitic_variants.py`
- **Contents**: Final lemma mappings including enclitic variants
- **Purpose**: Complete mapping table for all word forms to lemmas
- **Format**: `{word_form: lemma}` with ~1M+ entries
- **Used by**: Database creation (`create_perseus_database.py`)

## Database Creation Usage

The final database creation uses three key files:
1. **`combine_all_ancient_greek_morphology.json`** - Morphological data
2. **`combine_dictionaries_to_lemma_map_1.json`** - Dictionary entries
3. **`add_enclitic_variants.json`** - Complete lemma mappings

These files are loaded by `create_perseus_database.py` to populate the SQLite database with:
- Dictionary entries for each lemma
- Morphological mappings for inflected forms
- Word indices for fast searching
- Translation alignment tables

## File Dependencies

Files must be generated in order due to dependencies:
1. First: `all_greek_wiktionary_pages.json` (or use existing cache)
2. Parallel: All `extract_*.json` files in wiktionary-processing/
3. Then: `combine_all_ancient_greek_morphology.json`
4. Parallel: Dictionary extraction files
5. Then: `combine_dictionaries_to_lemma_map_*.json`
6. Then: `add_grave_accent_variants.json`
7. Finally: `add_enclitic_variants.json`

## Maintenance Notes

- JSON files are named after their creating Python modules for traceability
- All files except `all_greek_wiktionary_pages.json` are regenerated each build
- Total processing time: ~4-5 minutes for complete regeneration
- Files use UTF-8 encoding and preserve all Greek diacritical marks
- The pipeline is designed to fail loudly if any required file is missing