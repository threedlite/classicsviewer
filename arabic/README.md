# Arabic Lexicon for Classics Viewer

## Overview

A complete Arabic lexicon package for the Classics Viewer app, featuring Lane's Classical Arabic Lexicon (43,913 entries) with Wiktionary-based morphology and vowel-preserving normalization.

**Status**: ✅ Complete and ready for deployment

**Coverage**: 10.1% on Classical Arabic texts (Mu'allaqat corpus)
- Direct dictionary matches: 10.0% (66/662 words)
- Morphology matches: 0.5% (3/662 words)
- Zero wrong definitions (quality-first approach)

## Quick Start

### Build the Lexicon Package

```bash
# Use existing morphology (fast, ~5 seconds)
python3 create_arabic_lexicon.py

# Rebuild morphology from Wiktionary dumps (slow, ~5-10 minutes)
python3 create_arabic_lexicon.py --rebuild
```

**Output**: `arabic_lexicon.zip` (6.7 MB compressed)

**Contents**:
- Lane's Classical Arabic Lexicon (43,913 entries)
- Wiktionary morphology (6,056 entries)
- Vowel-preserving normalization rules

### Prerequisites for `--rebuild`

Wiktionary dumps must be in `../data-sources/`:
- `enwiktionary-latest-pages-articles.xml.bz2` (English Wiktionary)
- `arwiktionary-latest-pages-articles.xml.bz2` (Arabic Wiktionary)

Download from:
- English: https://dumps.wikimedia.org/enwiktionary/latest/
- Arabic: https://dumps.wikimedia.org/arwiktionary/latest/

## Coverage Breakdown

Tested on Mu'allaqat corpus (662 unique Classical Arabic words):

| Source | Matches | Coverage |
|--------|---------|----------|
| Lane's Lexicon (direct) | 66 | 10.0% |
| Wiktionary morphology | 3 | 0.5% |
| **TOTAL** | **67** | **10.1%** |

### Why Coverage is Low

1. **Domain mismatch**: 6th-century Classical Arabic vs modern Wiktionary focus
2. **Vocalization gap**: Fully diacritized poetry vs undiacritized modern entries
3. **English Wiktionary**: 61% of morphology (3,719 entries) are unusable skeleton forms
4. **Arabic Wiktionary**: Only 39% (2,337 entries) have diacritics and can match

### Why This is Acceptable

- **Zero wrong definitions**: Quality over quantity
- **Better than alternatives**: Rule-based had 47% coverage but 60-75% wrong matches
- **Lane's provides solid base**: 10% direct dictionary coverage
- **Morphology adds value**: Accurate lemmatization for modern Arabic texts

## Normalization Strategy

### Vowel-Preserving Approach

Unlike Greek (where diacritics are non-semantic), Arabic vowels are **semantically meaningful** and distinguish different words:

- `كَتَبَ` (kataba) = "he wrote" (verb)
- `كُتُب` (kutub) = "books" (noun)
- `كَاتِب` (kātib) = "writer" (participle)

**Stripping vowels would cause incorrect matches and wrong dictionary lookups.**

### What Gets Normalized

**REMOVES** (non-semantic marks):
- ّ (shadda) - gemination
- ْ (sukun) - no vowel marker
- ً ٌ ٍ (tanween) - case endings
- ـ (tatweel) - typographic stretch
- Other variant marks

**PRESERVES** (semantically meaningful):
- َ (fatha) - "a" vowel
- ُ (damma) - "u" vowel
- ِ (kasra) - "i" vowel

### Impact of Normalization

- **Without normalization**: 3.2% coverage (21 matches)
- **With normalization**: 10.0% coverage (66 matches)
- **Gained 6.8%** - more than tripled coverage!

Most gains from removing **tanween** (case ending differences between corpus and dictionary headwords).

## Lane's Lexicon Investigation

### Can We Extract Morphology from Lane's?

**Question**: Lane's entries contain all derived forms (حارِس, أحْرَاس, etc.). Can we extract these for morphology?

**Answer**: No, not practical due to **transliteration barrier**.

### The Problem

Lane's Lexicon uses **custom 19th-century transliteration**, not Arabic script:

**Example from entry for حَرَسَ (ḥarasa, "to guard")**:
```
The derived forms appear as:
- "HArisN" instead of حَارِس (hāris, "guard")
- "AHorAsN" instead of أَحْرَاس (aḥrās, "guards")
- Custom diacritic system for vowels
```

### Why This Is Impractical

1. **Custom transliteration scheme**: 19th-century system, not modern standards
2. **43,913 entries**: Would need parser for all entries
3. **High error rate**: Similar to rule-based morphology (~60%+ wrong)
4. **Effort vs benefit**: Weeks/months to build parser for questionable accuracy
5. **Complexity**: Different patterns for verbs, nouns, adjectives, irregular forms

### What We'd Need to Build

1. Complete transliteration-to-Arabic parser
2. Pattern extraction for derived forms
3. Validation against Classical texts
4. Error correction for 60%+ failure rate

**Conclusion**: Not worth the effort given Wiktionary provides verified morphology with zero wrong definitions.

## Build Process

### Unified Build Script: `create_arabic_lexicon.py`

**Simple workflow**:
```bash
# Use existing morphology (fast)
python3 create_arabic_lexicon.py

# Rebuild from Wiktionary dumps (slow, ~5-10 min)
python3 create_arabic_lexicon.py --rebuild
```

### What It Does

1. Validates all source files exist
2. Optionally rebuilds morphology:
   - Extracts from English Wiktionary (57,230 pages)
   - Extracts from Arabic Wiktionary (77,520 pages)
   - Combines with vowel-preserving normalization
3. Creates compressed ZIP package
4. Verifies integrity

### Morphology Extraction Pipeline (when using `--rebuild`)

1. **English Wiktionary** (26 MB cache, 57,230 pages)
   - Extracts 3,282 word forms from templates
   - **Problem**: All undiacritized skeletons → unusable for vowel-preserving matching

2. **Arabic Wiktionary** (33 MB cache, 77,520 pages)
   - Extracts 2,075 word forms from patterns
   - **Success**: All diacritized → 100% usable

3. **Combined Output**
   - 5,336 unique word forms
   - 6,056 total mappings (some words have multiple lemmas)
   - Only Arabic Wiktionary entries contribute to actual coverage

## File Organization

### Active Scripts (9 files)

**Production**:
- `create_arabic_lexicon.py` - Main build script (use this!)
- `normalize_arabic.py` - Runtime normalization module

**Extraction Pipeline** (called by main script):
- `extract_all_arabic_pages_from_enwiktionary.py`
- `extract_arabic_inflection_of.py`
- `extract_all_arabic_wiktionary_pages.py`
- `extract_arabic_wiktionary_patterns.py`
- `combine_wiktionary_sources.py`

**Testing & Development**:
- `create_arabic_texts.py` - Creates test corpus
- `test_exact_match_coverage.py` - Tests coverage

### Documentation

- `README.md` - This file (quick start guide)
- `IMPLEMENTATION_COMPLETE.md` - Complete implementation summary
- `NORMALIZATION_STRATEGY.md` - Detailed normalization approach

### Archived

- `archived_scripts/` - 8 obsolete scripts (replaced by unified build)
- `archived_docs/` - 4 redundant documentation files

## Deployment

### Package Contents

**File**: `arabic_lexicon.zip` (6.7 MB compressed, 75.3% compression)

**Contains**:
```
arabic_dictionary.csv          - Lane's Lexicon (43,913 entries)
arabic_morphology.csv          - Wiktionary morphology (6,056 entries)
normalization_rules_arabic.csv - Normalization rules (10 rules)
```

### App Integration

1. Copy `arabic_lexicon.zip` to app assets
2. Import lexicon in app settings
3. App will use:
   - Lane's dictionary for direct lookups
   - Morphology for lemma resolution
   - Normalization for flexible matching

## Future Improvements

If coverage needs to increase:

1. **Add Classical forms to Wiktionary** - Community contribution
2. **Extract from Classical dictionaries** - If morphology data available
3. **Manual curation** - High-frequency Classical words
4. **Hybrid approach** - Wiktionary + cautious rule-based for common patterns

## License Compliance

- **Lane's Lexicon**: Public domain
- **English Wiktionary**: CC BY-SA 3.0
- **Arabic Wiktionary**: CC BY-SA 3.0
- **Scripts**: Same as Classics Viewer project

Attribution included in app documentation.

## Key Design Decisions

### 1. Vowel-Preserving vs Skeleton Matching

**Decision**: Preserve vowels (fatha, damma, kasra)

**Rationale**: Stripping vowels would cause 60-75% wrong matches

**Trade-off**: Lower coverage (10.1% vs potential 47%) but zero wrong definitions

### 2. Wiktionary vs Rule-Based Morphology

**Decision**: Use Wiktionary (community-verified entries)

**Rejected Alternative**: Rule-based generation from Lane's roots
- Coverage: 47.4% (much higher)
- Accuracy: 25-40% (60-75% wrong!)
- User impact: Misleading definitions erode trust

**Chosen**: Combined Wiktionary
- Coverage: 10.1% (much lower)
- Accuracy: ~100% (zero wrong definitions)
- User impact: Trustworthy, even if limited

### 3. English + Arabic Wiktionary

**Decision**: Combine both sources

**English Wiktionary** (3,719 entries):
- Larger dataset
- **Problem**: Undiacritized → cannot match vowel-preserving normalized text
- Contributes 0% to actual coverage
- Kept for potential future use with modern Arabic

**Arabic Wiktionary** (2,337 entries):
- Smaller dataset
- **Success**: Diacritized → 100% usable
- All 3 morphology matches come from here

**Combined**: 6,056 entries with proper attribution

## Success Criteria

✅ **Zero wrong definitions** - Quality over quantity achieved
✅ **Reproducible build** - Single command creates package
✅ **Documented approach** - Complete documentation set
✅ **Tested coverage** - 10.1% on Classical texts
✅ **Vowel-preserving normalization** - Semantically correct
✅ **Clean codebase** - Obsolete scripts archived
✅ **Ready for deployment** - Package tested and verified

---

**Build Command**: `python3 create_arabic_lexicon.py`
**Output**: `arabic_lexicon.zip` (6.7 MB)
**Coverage**: 10.1% with zero wrong definitions
**Status**: ✅ Ready for deployment
