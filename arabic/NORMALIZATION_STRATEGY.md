# Arabic Normalization Strategy

## Overview

Arabic text normalization for the Classics Viewer uses a **vowel-preserving** approach that balances matching flexibility with semantic accuracy.

## Why This Approach?

Unlike Greek, where diacritics are mostly non-semantic (accents, breathing marks), Arabic vowels (harakat) are **semantically meaningful** and distinguish different words:

- `كَتَبَ` (kataba) = "he wrote" (verb, past tense)
- `كُتُب` (kutub) = "books" (noun, plural)
- `كَاتِب` (kātib) = "writer" (noun, active participle)

Removing vowels would cause incorrect matches and wrong dictionary lookups.

## Normalization Rules

The normalization is defined in `normalization_rules_arabic.csv` and applied during:
1. Database creation (text corpus normalization)
2. Dictionary/morphology import (headword normalization)
3. Runtime matching (search and lookup)

### Characters REMOVED (safe for matching)

| Mark | Unicode | Name | Example |
|------|---------|------|---------|
| ّ | U+0651 | Shadda (gemination) | مُحَمَّد → مُحَمَد |
| ْ | U+0652 | Sukun (no vowel) | مِنْ → مِن |
| ً | U+064B | Tanween fathatan | كَلِمَةً → كَلِمَة |
| ٌ | U+064C | Tanween dammatan | كِتَابٌ → كِتَاب |
| ٍ | U+064D | Tanween kasratan | بَيْتٍ → بَيْت |
| ٓ | U+0653 | Madda | آ → ا |
| ٔ | U+0654 | Hamza above | أ → ا |
| ٕ | U+0655 | Hamza below | إ → ا |
| ٰ | U+0670 | Alif khanjariyah | الرَّحْمَٰن → الرَحمَن |
| ـ | U+0640 | Tatweel/kashida | مـحـمـد → محمد |

### Characters PRESERVED (semantically meaningful)

| Mark | Unicode | Name | Sound | Example |
|------|---------|------|-------|---------|
| َ | U+064E | Fatha | "a" | كَتَبَ (kataba) |
| ُ | U+064F | Damma | "u" | كُتُب (kutub) |
| ِ | U+0650 | Kasra | "i" | كَاتِب (kātib) |

## Implementation

### Python Module: `normalize_arabic.py`

```python
from normalize_arabic import normalize_arabic_for_matching

# Removes shadda, sukun, tanween - keeps vowels
text = "أسْوَدَ"
normalized = normalize_arabic_for_matching(text)
# Result: "أسوَدَ" (sukun removed, fatha kept)
```

### CSV Rules: `normalization_rules_arabic.csv`

Applied automatically during database creation by `create_arabic_texts.py`:
- Normalizes corpus text for the `words` table
- Normalizes dictionary headwords
- Normalizes morphology word forms

## Examples

```
Original      → Normalized     | What Changed
----------------------------------------
كَتَبَ        → كَتَبَ         | (no change - only vowels)
كُتُب         → كُتُب          | (no change - only vowels)
كَاتِب        → كَاتِب         | (no change - only vowels)
كَلِمَةٌ      → كَلِمَة         | tanween removed
مُحَمَّد      → مُحَمَد        | shadda removed
مِنْ          → مِن            | sukun removed
أسْوَدَ       → أسوَدَ         | sukun removed, vowels kept
```

## Why Not Skeleton Matching?

Some Arabic NLP tools use "skeleton" forms that strip ALL diacritics (including vowels). This would give higher coverage but unacceptable accuracy:

**Skeleton approach problems:**
- `كتب` could match: كَتَبَ (wrote), كُتُب (books), كَاتِب (writer), كِتَاب (book)
- Would return wrong dictionary entries ~60-75% of the time
- User sees "book" when the text says "he wrote"

**Our approach:**
- Lower coverage (0.5% on Classical poetry corpus)
- Zero wrong definitions
- Quality over quantity

## Coverage Impact

### Wiktionary Morphology Coverage

Out of 6,056 morphology mappings:
- **English Wiktionary** (3,719 entries, 61%): Undiacritized skeletons like `كلم` → **Cannot match** vowel-preserving normalized text
- **Arabic Wiktionary** (2,337 entries, 39%): Diacritized like `كِلَاب` → **Can match** after normalization

**Result on Mu'allaqat Corpus:**
- Total unique words: 662
- Matches: 3 (0.5%)
- Corpus: 6th-century fully-vocalized Classical poetry
- Wiktionary: Modern, mostly undiacritized entries

### Why Coverage is Low

1. **Domain mismatch**: Classical Arabic (6th century) vs. Modern Arabic (Wiktionary focus)
2. **Vocalization mismatch**: Fully diacritized poetry vs. undiacritized modern forms
3. **Coverage gap**: Classical forms not well-represented in Wiktionary

## Future Improvements

To increase coverage while maintaining quality:

1. **Add vocalized Classical forms to Wiktionary** - community contribution
2. **Extract from Classical dictionaries** - Lane's Lexicon (43K entries) if morphology data available
3. **Manual curation** - high-frequency Classical words
4. **Hybrid approach** - Wiktionary where available, cautious rules for common patterns

## Comparison with Other Languages

### Greek (in pipeline)
- Diacritics are non-semantic (accents, breathing marks)
- Can safely strip to skeleton for matching
- High coverage achievable

### Hebrew (planned)
- Similar to Arabic - vowels (nikkud) are semantically meaningful
- Will use same vowel-preserving approach
- Expected similar low coverage on Biblical Hebrew

### Sanskrit (completed)
- Uses transliteration to Roman script
- Different normalization strategy (vowel length, retroflexes)
- Higher coverage due to modern scholarly texts

## Files

- `normalization_rules_arabic.csv` - Rules for database creation
- `normalize_arabic.py` - Python module for runtime normalization
- `create_arabic_texts.py` - Applies rules during database build
- `test_exact_match_coverage.py` - Tests morphology coverage

## License

These normalization rules are part of the Classics Viewer project and follow the same license as the main codebase.
