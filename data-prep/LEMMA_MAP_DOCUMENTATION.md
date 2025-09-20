# Lemma Map and Dictionary System Documentation

## Overview

The Classics Viewer app uses a sophisticated lemma mapping system to connect Greek word forms to their dictionary entries. This system combines data from three sources:
1. **Cunliffe's Homeric Lexicon** - specialized for Homer
2. **Liddell-Scott-Jones (LSJ)** - comprehensive Greek dictionary  
3. **Wiktionary** - morphological data with inflection mappings

## Key Challenges and Solutions

### 1. Unicode Normalization Issues
**Problem**: Different sources use different Unicode representations:
- Some use precomposed characters (ά)
- Others use combining diacriticals (α + ́)
- NFD vs NFC normalization differences

**Solution**: All text is normalized to NFC (Canonical Composition) during processing to ensure consistent matching.

### 2. Diacritical Variations
**Problem**: Greek text uses various diacritical marks that need special handling:
- Acute accents (ά) vs grave accents (ὰ)
- Macrons (ᾱ) and breves (ᾰ) in lemmas
- Breathing marks, circumflexes, iotas subscript

**Solutions**:
- Generate grave accent variants for all words (καί → καὶ)
- Strip macrons/breves from Wiktionary lemmas (πολῠ́ς → πολύς)
- Preserve all other diacriticals for accurate matching

### 3. Enclitic Particles
**Problem**: Greek particles (τε, που, γε, etc.) lose their accents when enclitic.

**Solution**: Generate unaccented variants for known enclitics to ensure they can be found.

### 4. Missing Definitions
**Problem**: Wiktionary morphology includes many forms without actual dictionary definitions.

**Solution**: Generate meaningful placeholder text based on part of speech and morphological patterns:
- Patronymics: "Patronymic name (son of X)"
- Verbs: "Verb (morphological entry)"
- Proper names: "Proper name"

## Script Pipeline

### 1. Extraction Scripts

#### `extract_cunliffe_fixed.py`
- Extracts from Cunliffe's Homeric Lexicon XML
- Handles betacode conversion for headwords
- Preserves XML structure for formatted display
- Output: `cunliffe_extracted.json`

#### `extract_lsj_fixed.py`
- Extracts from LSJ XML files
- Processes complex nested entry structures
- Handles cross-references and etymologies
- Output: `lsj_extracted_fixed.json`

#### `extract_wiktionary_final.py`
- Uses preprocessed Wiktionary morphology data
- Implements lemma simplification (removes macrons/breves)
- Generates meaningful placeholders for missing definitions
- Handles patronymic detection
- Output: `wiktionary_extracted_final.json`

### 2. Combination Script

#### `combine_dictionaries_to_lemma_map.py`
- Merges all three dictionary sources
- Resolves conflicts (Cunliffe > LSJ > Wiktionary priority)
- Creates unified dictionary entries
- Generates lemma mappings from all sources
- Outputs:
  - `combined_dictionary_entries.json`
  - `combined_lemma_mappings.json`

### 3. Variant Generation Scripts

#### `normalize_unicode.py`
- Ensures all text is in NFC form
- Handles Unicode normalization edge cases
- Input/Output: `combined_lemma_mappings.json` → `combined_lemma_mappings_normalized.json`

#### `add_grave_accent_variants.py`
- Generates grave accent versions of all acute accents
- Essential for finding words at end of clauses
- Input/Output: `combined_lemma_mappings_normalized.json` → `combined_lemma_mappings_with_graves.json`

#### `add_enclitic_variants.py`
- Creates unaccented versions of enclitic particles
- Handles: τε, που, γε, με, σε, etc.
- Input/Output: `combined_lemma_mappings_with_graves.json` → `combined_lemma_mappings_final.json`

### 4. Database Loading

#### `load_combined_dictionaries.py`
- Orchestrates the entire pipeline when run
- Creates database tables with proper schema
- Loads dictionary entries and lemma mappings
- Can be called standalone or from `create_perseus_database.py`

## Database Schema

### dictionary_entries table
```sql
CREATE TABLE dictionary_entries (
    id INTEGER PRIMARY KEY NOT NULL,
    headword TEXT NOT NULL,
    language TEXT NOT NULL,
    entry_xml TEXT,
    entry_html TEXT,
    entry_plain TEXT,
    source TEXT,
    CHECK (language IN ('greek', 'latin'))
);
```

### lemma_map table
```sql
CREATE TABLE lemma_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    word_form TEXT NOT NULL,
    lemma TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    source TEXT,
    morph_info TEXT
);
```

## Critical Implementation Details

### 1. Lemma Simplification
Wiktionary uses scholarly lemma forms with length marks:
- πολῠ́ς (with breve on υ)
- ᾱ̓́νθρωπος (with macron on α)

These must be simplified to match actual dictionary headwords:
- πολῠ́ς → πολύς
- ᾱ̓́νθρωπος → ἄνθρωπος

### 2. Source Priority
When the same word appears in multiple sources:
1. **Cunliffe** takes precedence (specialized for Homer)
2. **LSJ** is used if not in Cunliffe
3. **Wiktionary** provides additional morphological coverage

### 3. Morphological Placeholders
For words without definitions, meaningful placeholders are generated:
- Part of speech identification
- Patronymic pattern detection (names ending in -άδης, -ίδης)
- Proper name detection (capitalized nouns)

### 4. Coverage Statistics
Typical database contains:
- ~11,000 Cunliffe headwords
- ~116,000 LSJ headwords  
- ~37,000 Wiktionary entries
- ~440,000 total lemma mappings (including variants)

## Common Issues and Fixes

### "Unknown morphological entry"
**Cause**: Wiktionary entry without definition
**Fix**: Improved placeholder generation in `extract_wiktionary_final.py`

### Missing word lookups
**Cause**: Missing grave/enclitic variants
**Fix**: Ensure variant generation scripts run in pipeline

### Unicode mismatch errors
**Cause**: NFD/NFC normalization differences
**Fix**: All text normalized to NFC during processing

### Schema validation errors
**Cause**: Database schema doesn't match Room entities
**Fix**: Use autoincrement ID, not composite primary key

## Running the Pipeline

### Complete rebuild:
```bash
cd data-prep
python3 load_combined_dictionaries.py
```

### Individual steps:
```bash
# 1. Extract dictionaries
python3 extract_cunliffe_fixed.py
python3 extract_lsj_fixed.py  
python3 extract_wiktionary_final.py

# 2. Combine sources
python3 combine_dictionaries_to_lemma_map.py

# 3. The combination script automatically runs:
#    - normalize_unicode.py
#    - add_grave_accent_variants.py
#    - add_enclitic_variants.py
```

### Integration with main database:
```bash
python3 create_perseus_database.py sample
# This calls load_combined_dictionaries() internally
```

## Validation

After building, verify:
1. Check specific test words: μῆνιν, θεά, πολλάς
2. Verify patronymics show meaningful text, not "[unknown]"
3. Confirm variant generation (καί should also find καὶ)
4. Test coverage with `SELECT COUNT(DISTINCT lemma) FROM lemma_map`