# Arabic Morphology Solution: Dictionary-Only Approach

## License Constraint Summary

After thorough investigation, **no permissively-licensed Arabic morphological analyzer exists** for Classical Arabic:

| Tool | Code License | Data License | Verdict |
|------|-------------|--------------|---------|
| CAMeL Tools MSA | MIT ✅ | GPL v2 ❌ | Incompatible |
| CAMeL Tools Gulf/Levantine | MIT ✅ | CC BY 4.0 ✅ | Wrong dialect |
| Quranic Arabic Corpus | GPL ❌ | GPL ❌ | Incompatible |
| Qalsadi | GPL ❌ | GPL ❌ | Incompatible |
| Arramooz | GPL ❌ | GPL ❌ | Incompatible |
| Lane's Lexicon inflections | CC BY-SA 3.0 ✅ | CC BY-SA 3.0 ✅ | Transliterated, not Arabic script |

**Conclusion:** Must proceed with dictionary-only approach (no automatic morphology)

---

## Implemented Solution

### Current Implementation ✅

**arabic_lexicon.zip** contains:
1. **dictionary.csv** - 43,940 entries from Lane's Arabic-English Lexicon
2. **normalization_rules.csv** - Arabic text normalization rules

**arabic_texts.db** contains:
- 78 verses of Mu'allaqa of Imru' al-Qays
- 770 total words, 606 unique normalized words
- Full word position tracking

### User Experience

**Without morphology:**
- User taps on inflected word (e.g., "كتب")
- App applies normalization rules
- User searches dictionary by root form (e.g., "ك ت ب")
- Similar to early Greek/Latin dictionary usage

**Comparison to other languages in app:**
- **Greek:** ✅ Full morphology from Wiktionary + LSJ
- **Latin:** ✅ Full morphology from Whitaker's Words
- **Hebrew:** ✅ Full morphology from Open Scriptures morphhb
- **Arabic:** ❌ Dictionary-only, manual root lookup required

---

## Alternative Approaches Considered

### Option 1: Manual Morphology Creation
**Approach:** Hand-create morphology.csv for all 606 unique words in Mu'allaqa

**Pros:**
- ✅ 100% coverage for demonstration text
- ✅ High accuracy
- ✅ No license issues (original work under MIT)

**Cons:**
- ❌ Labor intensive (~40-60 hours for 606 words)
- ❌ Only covers one poem
- ❌ Not scalable to other Arabic texts
- ❌ Requires Arabic linguistic expertise

**Verdict:** Not practical for initial implementation

---

### Option 2: Extract from Lane's Lexicon Structure
**Approach:** Parse Lane's XML entry structure to extract headwords and map to inflected forms

**Investigation:**
- Lane's headwords are in Arabic script ✅
- Entries include root information
- Some verb paradigms included

**Limitations:**
- Headwords are lemmas (dictionary forms), not inflected forms
- No comprehensive inflection tables
- Would require Arabic morphological generation rules (complex)

**Verdict:** Insufficient data in Lane's for automatic morphology generation

---

### Option 3: Use Gulf/Levantine Databases (CC BY 4.0)
**Approach:** Try CAMeL Tools with permissively-licensed dialect databases

**Available databases:**
- `morphology-db-glf-01` (Gulf Arabic, CC BY 4.0, 8.0 MB)
- `morphology-db-lev-01` (Levantine Arabic, CC BY 4.0, 10.6 MB)

**Problems:**
- Pre-Islamic poetry (6th century Classical Arabic) ≠ Modern dialects
- Expected coverage: <20% (most words won't match)
- Would confuse users with incorrect dialect-specific analyses

**Verdict:** Wrong dialect, unacceptably low coverage

---

### Option 4: Crowdsource from Arabic Scholars
**Approach:** Create partial morphology, publish, and invite contributions

**Workflow:**
1. Start with dictionary-only release
2. Publish blank morphology template for Mu'allaqa
3. Invite Arabic scholars to contribute lemma mappings
4. Incrementally add to morphology.csv

**Pros:**
- ✅ Scalable over time
- ✅ Community contribution model
- ✅ No license issues

**Cons:**
- ⏳ Slow (depends on contributor availability)
- ⚠️ Quality control needed

**Verdict:** Viable long-term strategy, not for initial release

---

## Recommended Implementation Path

### Phase 1: Initial Release (Current) ✅

**What's included:**
- Lane's Lexicon dictionary (43,940 entries)
- Mu'allaqa text (78 verses, 770 words)
- F.E. Johnson English translation
- Arabic normalization rules
- Full text navigation and display

**What's missing:**
- Automatic word → root resolution
- Morphological analysis

**User workflow:**
1. Read Mu'allaqa in Arabic with English translation
2. Tap word to see normalized form
3. Manually search dictionary by root
4. View Lane's Lexicon entry

**Status:** Fully implemented and working

---

### Phase 2: Manual High-Frequency Words (Future)

**Approach:** Manually create morphology for top 100-200 most frequent words

**Prioritization:**
1. Particles and prepositions (من، في، على، إلى) - ~20 words
2. Common verbs (قال، جاء، كان) - ~50 words
3. Common nouns (بيت، يوم، ليل) - ~50 words
4. High-frequency Mu'allaqa-specific words - ~80 words

**Effort estimate:** 8-12 hours for 200 words

**Coverage impact:** ~40-50% of Mu'allaqa word occurrences

**Deliverable:** `arabic_morphology_manual.csv`

---

### Phase 3: Expanded Arabic Corpus (Long-term)

**Approach:** Add more Classical Arabic texts as sources become available

**Potential sources:**
- Additional Mu'allaqat poems (6 more)
- Classical Arabic prose (license permitting)
- Pre-Islamic poetry collections

**Morphology strategy:**
- Continue manual annotation for new high-frequency words
- Build incrementally over time
- Focus on most commonly read texts

---

## Technical Implementation Details

### Dictionary-Only Architecture

**Already implemented in app (Hebrew model):**

```kotlin
// UserDictionaryRepository.kt
fun lookupWord(word: String): DictionaryEntry? {
    val normalized = normalizeWord(word)  // Apply normalization rules
    return dictionaryDao.findByLemma(normalized)
}
```

**Arabic follows same pattern:**
1. User taps word: "كِتَابٍ"
2. App normalizes: "كتاب" (removes diacritics, normalizes letters)
3. User searches dictionary with root: "كتب"
4. Lane's entry for "كتب" shown

**No code changes needed** - existing custom dictionary import handles this.

---

### Morphology File Format (If/When Added)

**File:** `arabic_morphology.csv` (currently does not exist)

```csv
word_form,lemma,root,pos,language,confidence,source_name
كتب,كَتَبَ,ك-ت-ب,verb,arabic,1.0,Manual annotation
من,مِن,,prep,arabic,1.0,Manual annotation
قفا,قَفَا,ق-ف-و,verb,arabic,1.0,Manual annotation
منزل,مَنزِل,ن-ز-ل,noun,arabic,1.0,Manual annotation
```

**Integration:**
- Add to `arabic_lexicon.zip` as `morphology.csv`
- App's `DictionaryZipParser.kt` already supports morphology import
- Enables automatic word → lemma lookup

---

## Comparison to MORPHOLOGY_ANALYSIS.md Findings

The original analysis document correctly identified:
1. ✅ GPL-licensed tools are incompatible (Quranic Corpus, Qalsadi, Arramooz)
2. ✅ CAMeL Tools code is MIT but data licensing varies
3. ✅ Lane's Lexicon inflections are insufficient
4. ✅ Dictionary-only is the pragmatic immediate approach

**This document adds:**
- ❌ CAMeL MSA database is GPL v2 (not CC BY 4.0 as hoped)
- ❌ Gulf/Levantine CC BY 4.0 databases won't work (wrong dialect)
- ✅ Manual morphology creation is the only viable path forward
- ✅ Phased approach: dictionary-only → high-frequency manual → expanded corpus

---

## Success Criteria

### Phase 1 (Current) ✅
- ✅ Arabic text readable in app (Mu'allaqa, 78 verses)
- ✅ English translation available (F.E. Johnson)
- ✅ Lane's Lexicon integrated (43,940 entries)
- ✅ Normalization rules working
- ✅ Dictionary search functional

### Phase 2 (Future - Manual Morphology)
- ⏳ Top 200 words have lemma mappings
- ⏳ 40-50% of Mu'allaqa word occurrences auto-resolve to dictionary
- ⏳ Remaining words still accessible via manual root search

### Phase 3 (Long-term - Expanded Corpus)
- ⏳ Multiple Classical Arabic texts available
- ⏳ 500+ morphology entries covering common vocabulary
- ⏳ Community contribution model established

---

## License Attribution

**Current dependencies (all compatible):**

### Lane's Arabic-English Lexicon
```
Source: Perseus Digital Library
License: Creative Commons Attribution-ShareAlike 3.0 United States (CC BY-SA 3.0)
https://creativecommons.org/licenses/by-sa/3.0/us/

Original Work: Lane, Edward William. An Arabic-English Lexicon.
               London: Williams and Norgate, 1863-1893. 8 volumes.

Text provided by Perseus Digital Library, with funding from
The U.S. Department of Education and The Max Planck Society.
```

### Mu'allaqa Arabic Text
```
Source: Arabic Wikisource
License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
https://creativecommons.org/licenses/by-sa/4.0/

URL: https://ar.wikisource.org/wiki/معلقة_امرئ_القيس
Author: Imru' al-Qays (امرؤ القيس), c. 501-544 CE
```

### F.E. Johnson Translation
```
Source: English Wikisource
License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
https://creativecommons.org/licenses/by-sa/4.0/

From: The Sacred Books and Early Literature of the East, Volume V
Translator: F. E. Johnson (c. 1894)
```

**No GPL dependencies** ✅ All licenses compatible with MIT

---

## Conclusion

The dictionary-only approach is the **only viable option** for Arabic morphology given:
1. No permissively-licensed MSA morphological analyzer exists
2. GPL-licensed tools cannot be used in MIT app
3. Manual creation is feasible but labor-intensive

**Current status:** Dictionary-only implementation complete and functional

**Future path:** Incremental manual morphology creation for high-frequency words
