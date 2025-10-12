# Compound Word Decomposition - Developer Summary

## Quick Overview

The Android app now automatically decomposes Greek compound words when direct dictionary lookups fail. This significantly improves dictionary coverage for Homeric and archaic Greek texts.

## What It Does

When a word like **πολυμῆτις** isn't found in any dictionary:
1. System detects prefix **πολυ-** ("many, much")
2. Identifies stem **μῆτις** ("counsel")
3. Displays: "Compound word analysis: πολυ- (many, much) + μῆτις" + full definition of μῆτις

## Implementation Location

**File**: `app/src/main/java/com/classicsviewer/app/data/PerseusRepository.kt`

### Key Functions:
- **decomposeCompoundWord()** (lines 779-832) - Main decomposition logic
- **findStemLemma()** (lines 838-879) - Finds dictionary entry for stem
- **createCompoundEntry()** (lines 884-925) - Formats results for display
- **Integration** (lines 762-774) - Added to getAllDictionaryEntries() fallback chain

## Coverage

### Verbal Prefixes (Preverbs)
ἀνά, ἀντί, ἀπό, διά, εἰς, ἐκ, ἐν, ἐπί, κατά, μετά, παρά, περί, πρό, πρός, συν (+ assimilated forms), ὑπέρ, ὑπό

### Nominal Prefixes
ἀ-/ἀν- (privative), δυσ-, εὐ-, πολυ-

## Activation Criteria

Only activates when:
1. No direct dictionary match found
2. Language is Greek
3. Word length ≥ 6 characters

## Technical Details

### Phonological Handling
- **Diacritic Normalization**: Normalizes both word and prefix to strip breathing marks and accents during comparison (preserves diacritics in extracted stem)
- **Assimilation**: Detects συν → συμ/συλ/συγ
- **Variants**: Tries 7 stem variants (adds ς, σ, ν, ρ, α, η, ις)
- **Greedy Matching**: Longest prefix first to handle nested compounds

### Performance
- O(26) prefix checks per word
- Max 16 database queries per decomposition attempt
- Only runs as fallback (when entries.isEmpty())

### Confidence Score
Compound entries receive **0.7 confidence**:
- Lower than direct matches (1.0)
- Higher than ultra-normalized search (0.6)

## Testing

### Test in DictionaryActivity
1. Launch app
2. Open a Greek text (e.g., Iliad)
3. Tap on a compound word like πολυμῆτις
4. Should see "Compound word analysis:" section

### Expected Behavior
**Successful decomposition**:
- Shows prefix + meaning
- Shows stem + full definition
- Source: "[dictionary] (compound analysis)"

**No decomposition** (fallback to other strategies):
- Word has direct dictionary entry
- Word is too short (< 6 chars)
- Stem not found in dictionary

## Common Issues

### Issue: Word not decomposing when it should
**Check**:
1. Is word length ≥ 6?
2. Does the stem (after prefix removal) exist in dictionary?
3. Try adding the stem to user dictionary manually

### Issue: Incorrect decomposition
**Check**:
1. Is word actually a compound? (Some words coincidentally start with prefix letters)
2. Is greedy matching selecting wrong prefix?
3. Consider adding word as direct dictionary entry

### Issue: Stem variants not working
**Check**:
1. Does the stem need a different ending than the 7 provided?
2. Check database for actual stem headword spelling
3. May need to add more variants in findStemLemma()

### Issue: Prefix matching fails on words with diacritics
**Fixed**: As of latest update, algorithm normalizes both word and prefix before comparison
- Strips breathing marks, accents, and other diacritics
- Example: εὐφρήνῃ (with ὐ = U+1F50) now matches prefix ευ (with υ = U+03C5)
- Stem extraction preserves original diacritics

### Known Limitations After Testing
Tested on Homeric Hymn 27 (114 unique words):
- **Inflected stems**: Algorithm requires stem to have dictionary entry, but inflected forms like participles often don't
  - Example: κατακρεμάσασα = κατα + κρεμάσασα (participle, not in dictionary)
- **Missing morphology**: Some poetic/dialectical forms not in lemma_map
  - Example: φρήνῃ (Epic dative) not mapped to φρήν
- **Complex compounds**: Only handles single prefix, not compound prefixes
  - Example: αὐτοκασιγνήτην = αὐτο + κασίγνητος (needs multi-prefix support)

## Future Enhancements

1. **Noun + noun compounds**: ἀνδροφόνος (man-slayer)
2. **Recursive decomposition**: ἀντεισφέρω → ἀντι + (εἰς + φέρω)
3. **Elision handling**: ἀπάγω from ἀπό + ἄγω
4. **Semantic hints**: Flag when literal ≠ actual meaning
5. **Caching**: Cache decomposition results

## Documentation

**Detailed docs**: `/data-prep/COMPOUND_WORD_DECOMPOSITION.md`
**Edge cases**: `/data-prep/DICTIONARY_CAVEATS.md` (section 4)
**Prefix reference**: `/tmp/greek_prefixes.md`

## Debugging

### Enable detailed logging
Look for these log tags in Logcat:
```
PerseusRepository: "Attempting compound word decomposition for: [word]"
PerseusRepository: "Decomposed: [prefix]- ([meaning]) + [stem]"
PerseusRepository: "Found stem via variant: [stem] -> [variant]"
```

### Trace decomposition flow
1. Check if entries.isEmpty() = true
2. Check if cleanedWord.length >= 6
3. Check if any prefix matches word start
4. Check if findStemLemma() returns non-null
5. Check if createCompoundEntry() generates entry

## Integration with Dictionary Lookup Chain

Position: **6th** in the fallback sequence

```
1. User dictionary (direct)
2. User lemma mappings
3. Built-in dictionary (direct)
4. Lemma map lookups
5. Morphologically related forms
6. ▶ Compound decomposition ◀ (NEW)
7. Deduplication & sorting
8. Ultra-normalized search
```

## Code Example

```kotlin
// Manual decomposition test
val compoundParts = decomposeCompoundWord("πολυμῆτις")
if (compoundParts != null) {
    println("Prefix: ${compoundParts.prefix} (${compoundParts.prefixMeaning})")
    println("Stem: ${compoundParts.stem}")
    println("Lemma: ${compoundParts.stemLemma}")
}
```

## Related Files Modified

- `PerseusRepository.kt` - Core implementation
- `DICTIONARY_CAVEATS.md` - Updated compound word section
- `COMPOUND_WORD_DECOMPOSITION.md` - Comprehensive documentation

## Performance Impact

**Minimal**: Only runs when normal lookups fail (empty results)
- No impact on direct matches
- No impact on common words with lemma map entries
- Only affects rare/compound words without dictionary entries

## Rollback Plan

If issues arise, comment out lines 762-774 in PerseusRepository.kt:
```kotlin
// // Try compound word decomposition for Greek words if still no results
// if (entries.isEmpty() && normalizedLanguage == "greek" && cleanedWord.length >= 6) {
//     ...
// }
```

System will fall back to previous behavior (ultra-normalized search only).
