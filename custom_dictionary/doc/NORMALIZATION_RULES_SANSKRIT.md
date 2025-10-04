# Sanskrit Normalization Rules

## Overview

These normalization rules handle Sanskrit text written in Devanagari script, removing diacritical marks and phonetic annotations that vary between texts while preserving the base consonants and vowels needed for dictionary lookups.

## Normalization Rules

### 1. Vedic Accent Marks (Priority 1)
- **Pattern**: `[\u0951-\u0954]`
- **Replacement**: (empty)
- **Purpose**: Remove Vedic accent marks (svarita, udatta, anudatta)
- **Unicode Range**: U+0951 to U+0954
- **Example**: `अ॑ग्नि॒` → `अग्नि` (removes accent marks from Vedic texts)

### 2. Breathing Marks and Visarga Variants (Priority 2)
- **Pattern**: `[\u0900-\u0903]`
- **Replacement**: (empty)
- **Purpose**: Remove breathing marks and visarga variants
- **Unicode Range**: U+0900 to U+0903 (inverted candrabindu, candrabindu, anusvara signs)
- **Example**: `अँगुली` → `अगुली`

### 3. Visarga (Priority 3)
- **Pattern**: `ः`
- **Replacement**: (empty)
- **Purpose**: Remove visarga (word-final aspiration)
- **Unicode**: U+0903
- **Example**: `नमः` → `नम` (namah → nama)
- **Note**: Visarga represents final 'h' or 's' sound, often varies in transcription

### 4. Anusvara (Priority 4)
- **Pattern**: `ं`
- **Replacement**: (empty)
- **Purpose**: Remove anusvara (nasal marker)
- **Unicode**: U+0902
- **Example**: `संस्कृत` → `सस्कृत` (removes nasal marker)
- **Note**: Often represents 'm' or 'n' before consonants

### 5. Virama/Halant (Priority 5)
- **Pattern**: `्`
- **Replacement**: (empty)
- **Purpose**: Remove virama/halant (vowel killer)
- **Unicode**: U+094D
- **Example**: `क्त` → `कत` (removes consonant conjunct marker)
- **Note**: Marks consonants without following vowels

### 6. Nukta (Priority 6)
- **Pattern**: `़`
- **Replacement**: (empty)
- **Purpose**: Remove nukta (dot below for non-Sanskrit sounds)
- **Unicode**: U+093C
- **Example**: `क़` → `क` (removes dot indicating foreign sounds)
- **Note**: Used for sounds borrowed from Persian/Arabic

### 7. Om Symbol (Priority 7)
- **Pattern**: `ॐ`
- **Replacement**: `ओम`
- **Purpose**: Normalize Om symbol to standard spelling
- **Unicode**: U+0950 → ओम (U+0913 U+092E)
- **Example**: `ॐ` → `ओम`

### 8. Inverted Candrabindu (Priority 8)
- **Pattern**: `ऀ`
- **Replacement**: (empty)
- **Purpose**: Remove Devanagari sign inverted candrabindu
- **Unicode**: U+0900
- **Example**: Rare Vedic notation mark

### 9. Prishthamatra E (Priority 9)
- **Pattern**: `ॎ`
- **Replacement**: (empty)
- **Purpose**: Remove Devanagari sign prishthamatra e
- **Unicode**: U+090E
- **Example**: Archaic vowel notation

### 10. AW Sign (Priority 10)
- **Pattern**: `ॏ`
- **Replacement**: (empty)
- **Purpose**: Remove Devanagari sign aw
- **Unicode**: U+090F
- **Example**: Rare vowel sign

### 11. Zero-Width Characters (Priority 11)
- **Pattern**: `[\u094D\u200C\u200D]`
- **Replacement**: (empty)
- **Purpose**: Remove virama and zero-width joiners/non-joiners
- **Unicode**: U+094D, U+200C (ZWNJ), U+200D (ZWJ)
- **Example**: Cleanup invisible formatting characters

## Usage in Dictionary Files

Include this file as `normalization_rules.csv` in your Sanskrit dictionary ZIP file:

```
my-sanskrit-dictionary.zip
├── dictionary.csv          (Sanskrit entries)
├── morphology.csv          (Optional: lemma mappings)
└── normalization_rules.csv (This file, renamed)
```

Or use the language-specific filename:
```
└── normalization_rules_sanskrit.csv
```

## Example Transformations

### Bhagavad Gita Text
**Input (with diacritics):**
```
धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः।
मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय॥
```

**After normalization:**
```
धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः
मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय
```
(Removes visarga ः, punctuation normalization happens separately)

### Vedic Text
**Input (with accents):**
```
अ॒ग्निमी॑ळे पु॒रोहि॑तं य॒ज्ञस्य॑ दे॒वमृ॒त्विज॑म्।
```

**After normalization:**
```
अग्निमीळे पुरोहितं यज्ञस्य देवमृत्विजम्
```
(Removes Vedic accent marks)

### Conjuncts
**Input:**
```
प्रज्ञा संस्कृतं
```

**After normalization:**
```
प्रज्ञा ससकृत
```
(Removes virama and anusvara for matching)

## Technical Details

### Unicode NFD Normalization
All patterns are applied **after** Unicode NFD (Canonical Decomposition) normalization, which separates base characters from combining marks.

### Pattern Order
Patterns are applied in priority order (1-11). Lower numbers are applied first.

### Compatibility
- ✅ Works with Sanskrit texts in Devanagari script
- ✅ Handles Vedic accent marks
- ✅ Normalizes Om symbol
- ✅ Removes phonetic annotations
- ❌ Not for IAST (romanized Sanskrit) - those need different rules
- ❌ Not for Bengali/Telugu Sanskrit - different scripts need different rules

## Common Use Cases

### Classical Sanskrit Dictionaries
- Monier-Williams Sanskrit Dictionary
- Apte Sanskrit Dictionary
- Sanskrit-English lexicons

### Vedic Texts
- Rigveda
- Yajurveda
- Samaveda
- Atharvaveda

### Epic Texts
- Mahabharata
- Ramayana
- Puranas

### Philosophical Texts
- Bhagavad Gita
- Upanishads
- Brahma Sutras

## Notes

### Why Remove Virama?
The virama (्) creates consonant clusters. Removing it helps match dictionary entries that may be stored without cluster notation.

### Why Remove Anusvara and Visarga?
These phonetic marks vary significantly between:
- Different text traditions
- Sandhi applications
- Transliteration systems

Removing them creates more consistent dictionary matching.

### Regional Variations
Sanskrit can be written in multiple scripts (Devanagari, Bengali, Telugu, Malayalam, etc.). These rules are **Devanagari-specific**. Other scripts need their own normalization rules.

## Implementation Notes

When using these rules in the Classics Viewer app:
1. Rules are loaded from the CSV file during dictionary import
2. Greek and Latin patterns are automatically filtered out
3. Normalization happens at **lookup time**, not import time
4. Patterns are cached for performance
5. Text undergoes NFD normalization before pattern application

## References

- Unicode Standard for Devanagari: U+0900 to U+097F
- Vedic Extensions: U+1CD0 to U+1CFF
- Sanskrit grammar and phonetics (sandhi rules)
- IAST (International Alphabet of Sanskrit Transliteration)
