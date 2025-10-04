# Arabic Text Integration for ClassicsViewer

## Selected Text: Mu'allaqa of Imru' al-Qays

**Source:** https://ar.wikisource.org/wiki/معلقة_امرئ_القيس
**License:** CC BY-SA 4.0 ✅ (compatible - allows commercial use)
**Author:** Imru' al-Qays (امرؤ القيس) - Pre-Islamic poet (~6th century CE)
**Work:** Mu'allaqa (معلقة) - One of the Seven Hanging Odes
**Length:** ~78-82 verses

## Why This Text

The Mu'allaqa of Imru' al-Qays is the perfect demonstration text for Arabic support:

1. ✅ **Compatible License** - CC BY-SA 4.0 (same as Greek/Latin Perseus texts)
2. ✅ **Classical Arabic** - Canonical pre-Islamic poetry, represents the foundation of Arabic literature
3. ✅ **Manageable Size** - Single poem ideal for demonstration (not thousands of volumes)
4. ✅ **Structured Data** - Verse-by-verse layout on Wikisource
5. ✅ **Public Domain** - Ancient text, author died 1,400+ years ago
6. ✅ **Can be Translated** - Unlike Quran, has no religious restrictions on translation
7. ✅ **Well-Known** - Most famous pre-Islamic Arabic poem, recognized by all Arabic students
8. ✅ **Translations Available** - Multiple English translations exist in public domain

## Integration Components

### 1. Text Source
- Download from Arabic Wikisource
- Parse verse-by-verse structure
- Create database entry: Author "Imru' al-Qays", Work "Mu'allaqa"

### 2. Dictionary Resource
- **Lane's Arabic-English Lexicon**
- Source: Perseus Digital Library
- License: CC BY-SA 3.0
- Format: TEI XML
- Download: https://www.perseus.tufts.edu/hopper/opensource/downloads/texts/hopper-texts-Arabic.tar.gz

### 3. Normalization Rules
- Use existing `custom_dictionary/normalization_rules_arabic.csv`
- Handles diacritic removal, letter variants, etc.

### 4. Database Schema
Same structure as Greek/Latin texts:
- `authors` table: Imru' al-Qays
- `works` table: Mu'allaqa
- `text_lines` table: Individual verses
- `words` table: Tokenized words with positions
- Optional: `translation_segments` if English translation is added

## Implementation Steps

1. **Download Text**
   - Fetch HTML from Wikisource
   - Parse verse structure
   - Extract clean Arabic text

2. **Process with Normalization**
   - Apply Arabic normalization rules
   - Tokenize into words
   - Calculate word positions

3. **Integrate Lane's Lexicon**
   - Parse TEI XML from Perseus
   - Extract headwords and definitions
   - Create dictionary lookup table

4. **Build Database Entry**
   - Add to `create_perseus_database.py` as Arabic section
   - Generate sample database with Arabic text
   - Test word lookup and navigation

## Public Domain Translations Available

For future enhancement, these public domain English translations can be added:

- **F. E. Johnson translation** (1893) - Available on Wikisource
- **William Jones translation** (1881) - Available on Wikisource
- **Lady Anne and Sir Wilfrid Scawen Blunt** - The Seven Golden Odes of Pagan Arabia (1903)
- **A.J. Arberry** - The Seven Odes (1957)

## License Compatibility Summary

| Component | License | Commercial Use | Compatible |
|-----------|---------|----------------|------------|
| ClassicsViewer App | MIT | ✅ Yes | - |
| Mu'allaqa (Wikisource) | CC BY-SA 4.0 | ✅ Yes | ✅ |
| Lane's Lexicon | CC BY-SA 3.0 | ✅ Yes | ✅ |
| Normalization Rules | MIT (our code) | ✅ Yes | ✅ |

All components are compatible and allow commercial distribution via app stores.

## Future Expansion Possibilities

Once Arabic infrastructure is proven with the Mu'allaqa:

1. **Other Mu'allaqat** - Add remaining six hanging odes from Wikisource
2. **Pre-Islamic Poetry** - Additional poets from Arabic Wikisource
3. **Classical Prose** - Kalila wa Dimna (if clean text source found)
4. **Medieval Philosophy** - Monitor for permissively-licensed texts
5. **Persian Integration** - Similar approach with Persian classical poetry

## Notes

- **No Quran** - Avoided due to translation sensitivities
- **No OpenITI** - CC BY-NC-SA license incompatible (NonCommercial restriction)
- **No ACO** - Only scanned images, no machine-readable text
- **Wikisource First** - Best source for structured public domain Arabic texts
