# Lemmatization Improvements Documentation

## Overview
This document describes the comprehensive improvements made to the Greek lemmatization system for the Classics Viewer app, addressing dictionary lookup failures for inflected Greek words.

## Initial Problem
- Dictionary lookups were failing for many Greek words in texts (e.g., μῆνιν in Iliad line 1)
- Only 14/17 words from the first 3 lines of the Iliad could be found in the dictionary
- The system lacked mappings from inflected forms to dictionary headwords (lemmas)

## Solution Approach

### 1. Wiktionary Data Extraction
Created multiple extraction scripts to harvest morphological data:

#### a. English Wiktionary Extraction (`extract_inflection_of_template.py`)
- Extracts Greek forms using `{{inflection of}}` templates
- Found 653 mappings, 326 unique after filtering
- Example: εθηκε → τιθημι

#### b. English Wiktionary Comprehensive (`extract_all_ancient_greek_forms.py`)
- Extracts ALL Ancient Greek non-lemma forms, not just {{inflection of}}
- Searches for multiple template types: plural of, genitive of, aorist of, etc.
- Found 16,399 mappings from 16,027 forms
- Successfully found test words: μοι → εγω, τουτο → ουτοσ, εθηκε → τιθημι

#### c. Greek Wiktionary Extraction (`extract_greek_wiktionary_fixed.py`)
- Extracts from Greek Wiktionary (elwiktionary)
- Found 2,119 mappings
- Initially had parsing issues with templates

#### d. Declension Template Generation (`extract_declension_mappings.py`)
- Generates inflected forms from Greek declension templates
- Implements patterns for major declension types (1st, 2nd, 3rd)
- Generated 37,155 mappings

### 2. Database Schema Enhancement
Added morphological information to lemma mappings:

```sql
CREATE TABLE lemma_map (
    word_form TEXT NOT NULL,
    word_normalized TEXT NOT NULL,
    lemma TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    source TEXT,
    morph_info TEXT,  -- NEW: grammatical information
    PRIMARY KEY (word_form, lemma)
)
```

### 3. Normalization Improvements

#### Critical Fix: Punctuation Handling
**Problem**: Word normalization was preserving punctuation, preventing matches
- Word in text: "οὐλομένην," (with comma)
- Lemma mapping: "ουλομενην" (without comma)

**Solution**: Updated `normalize_greek()` to strip all punctuation:
```python
def normalize_greek(text):
    """Normalize Greek text by removing diacritics, punctuation, and converting to lowercase"""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = text.replace('ς', 'σ')
    # Remove punctuation - keep only Greek letters
    text = ''.join(c for c in text if c.isalpha() and ('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff'))
    return text
```

**Impact**: 
- Reduced unique words from 293,291 to 220,387
- Improved Iliad lines 1-3 coverage from 41% to 65%

### 4. Algorithmic Lemmatization
Implemented comprehensive algorithmic generation for words not in Wiktionary:

```python
def generate_comprehensive_lemmatization(cursor):
    # Process ALL words, not just unmapped ones
    # Try multiple strategies:
    1. Word as-is if it's already a lemma
    2. Add common dictionary endings (for elided forms like μυρί')
    3. Remove common inflectional endings
    4. Handle augmented verb forms (ε- prefix)
    5. Recognize patronymic patterns (son of X names)
    6. Assign confidence scores based on transformation type
```

#### Patronymic Recognition (Added August 2025)
Algorithmically identifies Greek patronymic forms:
- Patterns: -ιδης/-ιαδης (nominative), -ιδου/-ιαδεω (genitive)
- Examples: Πηληϊάδεω → Πηλεύς, Ἀχιλῆος → Ἀχιλλεύς
- Handles vowel changes: η→ε when forming base names
- Confidence score: 0.75 for patronymic matches

### 5. Wiktionary Integration
Added Wiktionary definitions for lemmas missing from LSJ:

**Approach**: Single unified dictionary table
- Keep existing `dictionary_entries` schema
- Add Wiktionary entries with `source='wiktionary'`
- No UI changes needed - single lookup handles both sources
- Wiktionary entries formatted to match LSJ style

**Added entries**:
- σφωέ (dual pronoun - "they two")
- Ἀτρεύς (Atreus - enabling patronymic mappings)
- πρῶτα (adverbial use of πρῶτος)
- νοῦσος (Ionic form of νόσος)
- ἑλώριον (prey, spoil)

### 6. Multiple Lemma Support
Enhanced system to support multiple possible lemmas per word:

**Example**: μυρί' now maps to:
- μυριοσ (0.7) - "countless" (correct)
- μυρον (0.8) - "perfume" (incorrect but valid word)
- μυρω (0.5) - verb form

Android app can use:
- `getLemmaForWord()` - returns highest confidence match
- `getAllLemmasForWord()` - returns all possibilities

### 6. Database Optimization
Implemented optimization to keep only mappings for words that appear in texts:
- Before: 1,031,208 mappings
- After: 68,802 mappings (93.3% reduction)
- Maintains all alternative lemmas for words in texts

## Results

### Coverage Statistics
- **Initial**: ~5% of words had lemma mappings
- **After Wiktionary**: ~17% coverage
- **After algorithmic**: ~26% coverage (overall)
- **Greek texts only**: ~32.3% coverage
- **Test words**: 100% success (μηνιν, αειδε, πολλασ, ψυχασ, εθηκε, ουλομενην)

### Sample Text Analysis
Analysis of Homer's Odyssey (first 100 lines) shows **77.1% coverage** - a realistic 
representation of performance on epic Greek text.

Successfully mapped word types:
- Patronymic patterns (e.g., -ιδης → -ευς)
- Proper names (when in dictionary or Wiktionary)
- Aorist passive participles (-θεις forms)
- Dual pronouns (e.g., σφωέ via Wiktionary)
- Ionic/Epic variants (e.g., νοῦσος for νόσος)
- Multiple lemma alternatives for ambiguous forms

Remaining gaps typically include:
- Compound verbs with prefixes
- Rare dialectal forms
- Some particles and clitics
- Proper names not in dictionaries

### Database Metrics
- **Total lemma mappings**: ~69,400+
- **With morphological info**: ~9,000 (13%)
- **Dictionary entries**: 28,652 (28,647 LSJ + 5 Wiktionary)
- **Database size**: ~775MB
- **Unique words in texts**: 220,387

## Integration with Android App

The app already supports multiple lemmas through Room DAOs:
```kotlin
@Query("SELECT lemma FROM lemma_map WHERE word_normalized = :wordNormalized ORDER BY confidence DESC LIMIT 1")
suspend fun getLemmaForWord(wordNormalized: String): String?

@Query("SELECT DISTINCT lemma FROM lemma_map WHERE word_form = :wordForm OR word_normalized = :wordNormalized ORDER BY confidence DESC")
suspend fun getAllLemmasForWord(wordForm: String, wordNormalized: String): List<String>
```

## Build Process

### Prerequisites
1. Perseus Digital Library data in `data-sources/`
2. Wiktionary dumps:
   - `enwiktionary-latest-pages-articles.xml.bz2`
   - `elwiktionary-latest-pages-articles.xml.bz2`

### Build Commands
```bash
cd data-prep
python3 create_perseus_database.py  # Integrated build
# OR
python3 build_database.py           # Wrapper script
```

### Build Steps
1. Extract Perseus texts and dictionaries
2. Generate LSJ-based lemmatizations
3. Extract Wiktionary mappings (if needed)
4. Load all Wiktionary data
5. Generate algorithmic mappings for ALL words
6. Optimize to keep only words in texts
7. Create OBB file for Android deployment

## Key Files

### Extraction Scripts
- `wiktionary-processing/extract_inflection_of_template.py`
- `wiktionary-processing/extract_all_ancient_greek_forms.py`
- `wiktionary-processing/extract_greek_wiktionary_fixed.py`
- `wiktionary-processing/extract_declension_mappings.py`

### Main Database Creation
- `create_perseus_database.py` - Integrated database builder
- `build_database.py` - Simple wrapper

### Output Files
- `perseus_texts.db` - Main database
- `main.1.com.classicsviewer.app.debug.obb` - Android deployment package
- `database_manifest.json` - Database contents summary
- `database_quality_report.txt` - Detailed quality metrics

## Future Improvements

1. **Compound verb analysis**: προΐαψεν → προ + ἵημι
2. **Extended patronymic patterns**: Handle more complex name formations
3. **Context-aware disambiguation**: Use surrounding words to choose correct lemma
4. **Dialectal form mapping**: Better support for Epic, Ionic, Doric variants
5. **Morphological parsing**: Full grammatical analysis beyond simple tags
6. **Dual form recognition**: Better handling of dual pronouns and verb forms
7. **Participle patterns**: More comprehensive participle ending recognition