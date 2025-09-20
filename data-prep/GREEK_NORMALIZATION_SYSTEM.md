# Greek Text Normalization System

## Overview

The Classics Viewer app uses a multi-tier normalization system for Greek text to ensure robust dictionary lookups and text searching. This system handles the complexities of polytonic Greek orthography and various Unicode encoding issues.

## Three Levels of Text Processing

### 1. Punctuation Removal (`normalizeGreek()` in Kotlin)

This is a minimal normalization used for direct dictionary lookups in the Android app.

**What it does:**
- Removes punctuation only (period, comma, semicolon, raised dot)
- Preserves all diacritics, breathings, and accents
- Preserves apostrophes (for elided forms)
- Preserves case

**Example transformations:**
- `καὶ.` → `καὶ` (removes period, keeps grave accent)
- `λόγος,` → `λόγος` (removes comma, keeps accent)
- `δ'` → `δ'` (preserves apostrophe for elision)

**Used for:**
- Direct dictionary lookups in `getDictionaryEntry()` and `getDictionaryEntryWithMorphology()`
- These functions search for exact matches in the database where headwords are stored WITH diacritics

**Code location:** 
- Kotlin: `app/.../data/PerseusRepository.kt` (normalizeGreek function)

### 2. Standard Normalization (`normalize_greek()` in Python)

This is the primary normalization used during database creation for indexing and searching.

**What it does:**
- Normalizes to NFD (decomposed form) using Unicode normalization
- Removes combining diacritical marks (accents, breathings, etc.)
- Converts to lowercase
- Replaces final sigma (ς) with regular sigma (σ)
- Removes all punctuation
- Keeps only Greek letter characters

**Example transformations:**
- `καὶ` → `και` (removes grave accent)
- `Ἀχιλλεύς` → `αχιλλευσ` (removes breathing, accent, converts to lowercase, normalizes final sigma)
- `τοῦ` → `του` (removes circumflex)

**Used for:**
- Creating normalized search indices during database creation
- Text searching within works
- Word occurrence searches
- Building lemma mappings

**Code location:** 
- Python: `data-prep/create_perseus_database.py`

### 3. Ultra Normalization (`normalize_greek_ultra()`)

This is an aggressive normalization used as a last-resort fallback when standard normalization fails to find matches.

**What it does:**
- Everything that standard normalization does
- PLUS: Handles pre-composed Unicode characters that don't decompose properly
- PLUS: Uses an extensive hardcoded mapping table for every possible Greek character with diacritics

**Key feature:** Explicit character mapping table
```python
# Examples from the mapping table:
'ᾳ' → 'α'  # alpha with iota subscript
'ᾷ' → 'α'  # alpha with iota subscript and circumflex
'ῃ' → 'η'  # eta with iota subscript
'ῇ' → 'η'  # eta with iota subscript and circumflex
'ῳ' → 'ω'  # omega with iota subscript
'ᾧ' → 'ω'  # omega with rough breathing, circumflex, and iota subscript
```

**Example transformations:**
- `τῇ` → `τη` (handles iota subscript that might not decompose)
- `ᾧ` → `ω` (complex pre-composed character)
- `ῥήτωρ` → `ρητωρ` (handles rho with breathing mark)

**Used for:**
- Fallback dictionary lookups when standard search fails
- Handling text with unusual or complex diacritics
- Supporting searches where users type without diacritics

## Database Implementation

### Schema

The database stores both the original text and ultra-normalized versions:

```sql
-- Dictionary entries table
CREATE TABLE dictionary_entries (
    id INTEGER PRIMARY KEY NOT NULL,
    headword TEXT NOT NULL,
    headword_normalized_ultra TEXT,  -- Ultra-normalized version
    language TEXT NOT NULL,
    -- other columns...
);

-- Lemma mappings table  
CREATE TABLE lemma_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    word_form TEXT NOT NULL,
    word_form_normalized_ultra TEXT,  -- Ultra-normalized version
    lemma TEXT NOT NULL,
    -- other columns...
);

-- Indexes for fast lookups
CREATE INDEX idx_dictionary_headword_ultra 
    ON dictionary_entries(headword_normalized_ultra, language);
CREATE INDEX idx_lemma_map_word_ultra 
    ON lemma_map(word_form_normalized_ultra);
```

### Population

During database creation (`load_combined_dictionaries.py`):
```python
# For each dictionary entry
headword_ultra = normalize_greek_ultra(entry['headword']) if entry['language'] == 'greek' else None

# For each lemma mapping
word_form_ultra = normalize_greek_ultra(mapping['word_form'])
```

## Search Algorithm

The app uses a cascading search strategy in `PerseusRepository.getAllDictionaryEntries()`:

1. **Clean the input** (remove punctuation, preserve apostrophes and diacritics)
2. **Try direct dictionary lookup** with cleaned word (searches headwords that have diacritics)
3. **Try grave-to-acute conversion** if word has grave accents (creates acute variant)
4. **Search lemma mappings** for inflected forms (using the original word form)
5. **Try prefix search** for words ending with apostrophe (for elided forms like δ')
6. **Check morphologically related forms** (stem analysis)
7. **Try lowercase** if word starts with uppercase (only for non-Greek words)
8. **Ultra-normalized search** (last resort for Greek only):
   - Compute ultra-normalized form
   - Search dictionary by `headword_normalized_ultra` column
   - Search lemma mappings by `word_form_normalized_ultra` column
   - Return results with lower confidence scores (0.6-0.7)

Note: The standard `normalizeGreek()` function is NOT used in `getAllDictionaryEntries()` because it needs to preserve diacritics for accurate matching against the database entries.

## Why Two Levels?

### Unicode Complexity
- Some Greek characters exist as pre-composed forms (single Unicode codepoint)
- Standard NFD decomposition doesn't always separate these into base + diacritics
- Examples: `ᾳ` (U+1FB3), `ῃ` (U+1FC3), `ῳ` (U+1FF3)

### Performance vs Completeness
- Standard normalization is fast and handles 99% of cases
- Ultra normalization is more computationally intensive but guarantees results
- Using ultra normalization only as fallback optimizes performance

### Edge Cases Handled
1. **Iota subscripts**: `ᾳ`, `ῃ`, `ῳ` and all their variants with accents
2. **Complex combinations**: `ᾧ` (omega + rough breathing + circumflex + iota subscript)
3. **Rho variants**: `ῥ`, `ῤ` (rho with/without breathing)
4. **Pre-composed vs decomposed**: Different Unicode representations of the same visual character
5. **User input variations**: Users typing without proper polytonic support

## Usage Examples

### Successful lookup with standard normalization:
```
Input: "λόγος"
Standard normalized: "λογοσ"
Result: Found directly
```

### Successful lookup with ultra normalization:
```
Input: "τῇ" (with iota subscript)
Standard normalized: might fail if iota subscript doesn't decompose
Ultra normalized: "τη"
Result: Found via fallback
```

### Complex example:
```
Input: "ᾧτινι" (complex relative pronoun)
Standard normalized: might partially work
Ultra normalized: "ωτινι"  
Result: Found lemma "ὅστις" via ultra-normalized search
```

## Benefits

1. **Robustness**: No Greek word is unfindable regardless of diacritics
2. **User-friendly**: Works even if users can't type polytonic Greek
3. **Unicode-agnostic**: Handles different Unicode encodings of the same text
4. **Performance**: Fast primary path, comprehensive fallback
5. **Future-proof**: Easy to extend the mapping table for new edge cases

## Implementation Notes

- The ultra-normalization mapping table should be kept in sync between Python and Kotlin implementations
- Lower confidence scores (0.6-0.7) are assigned to ultra-normalized matches to indicate they're approximations
- The system logs when ultra-normalization is used for debugging
- Results show "found via simplified form" to indicate the match method

## Testing

To test the normalization system:

1. Search for words with complex diacritics: `ᾧ`, `τῇ`, `ῥήτωρ`
2. Search for words without any diacritics: `και`, `λογος`
3. Search for words with mixed Unicode encodings
4. Verify that results indicate when ultra-normalization was used