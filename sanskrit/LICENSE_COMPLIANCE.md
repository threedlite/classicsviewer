# License Compliance for Sanskrit Implementation

## Summary

All Sanskrit resources used in ClassicsViewer are properly licensed for commercial use.

**Status**: ✅ **FULLY COMPLIANT**

---

## Sources Used

### 1. Digital Corpus of Sanskrit (DCS) - Rig Veda & Morphology

**Source**: Digital Corpus of Sanskrit by Oliver Hellwig
**License**: Creative Commons Attribution 4.0 International (CC BY 4.0)
**Repository**: https://github.com/OliverHellwig/sanskrit
**Website**: http://www.sanskrit-linguistics.org/dcs/

**What we use**:
- **Rig Veda Text**: pada-and-analysis.dat (10,551 verses, 39,830 padas)
- **Dictionary**: 179,806 lemmas with definitions
- **Morphology**: 4,700,299 word→lemma mappings (including 3,699 sandhi-enhanced)
- **Extracted from**: 5.5 million annotated words across 268 classical texts

**License Terms**:
- ✅ Commercial use allowed
- ✅ Modification allowed
- ✅ Distribution allowed
- ✅ Requires attribution

**Attribution** (included in app's LicenseActivity.kt):
```
Digital Corpus of Sanskrit (DCS)
Author: Oliver Hellwig
License: CC BY 4.0
Source: http://www.sanskrit-linguistics.org/dcs/
```

**Our modifications**:
- Converted IAST transliteration → Devanagari script
- Added sandhi-split compound mappings (1,956 compounds automatically resolved)
- Reformatted to ClassicsViewer CSV/database schema
- Combined padas into verses for readability

---

### 2. Sanskrit Parser - Sandhi Enhancement

**Source**: sanskrit_parser Python library
**License**: MIT License
**Repository**: https://github.com/kmadathil/sanskrit_parser

**What we use**:
- Automated sandhi (word junction) splitting for compound words
- Used during database creation only (not in app runtime)
- Improves lexicon coverage from 40% → 88%

**License Terms**:
- ✅ Commercial use allowed
- ✅ Modification allowed
- ✅ Distribution allowed
- ✅ Minimal requirements (copyright notice)

**Attribution**:
```
sanskrit_parser - MIT License
Copyright (c) 2017-2024 Sanskrit Parser Contributors
Repository: https://github.com/kmadathil/sanskrit_parser
```

---

### 3. Bhagavad Gita Text - Sanskrit

**Source**: Sanskrit Wikisource
**License**: Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0)
**URL**: https://sa.wikisource.org/wiki/भगवद्गीता

**What we use**:
- Sanskrit text: 700 verses across 18 chapters
- Ancient text (public domain), Wikisource encoding (CC BY-SA 4.0)

**License Terms**:
- ✅ Commercial use allowed
- ✅ Share-alike requirement (our app is MIT/open source ✓)
- ✅ Requires attribution

**Attribution**:
```
Bhagavad Gita (Sanskrit)
Source: Sanskrit Wikisource
License: CC BY-SA 4.0
URL: https://sa.wikisource.org/wiki/भगवद्गीता
```

---

### 4. Bhagavad Gita Translation 1 - Edwin Arnold

**Source**: English Wikisource
**Translator**: Edwin Arnold (1885)
**License**: Public Domain
**URL**: https://en.wikisource.org/wiki/The_Bhagavad_Gita_(Arnold_translation)

**What we use**:
- English prose translation (18 chapters, chapter-level segments)

**License Terms**:
- ✅ Public Domain (no restrictions)

---

### 5. Bhagavad Gita Translation 2 - Annie Besant

**Source**: English Wikisource
**Translator**: Annie Besant (1922, 4th edition)
**License**: Public Domain
**URL**: https://en.wikisource.org/wiki/Bhagavad-Gita_(Besant_4th)

**What we use**:
- English verse-by-verse translation (700 verses)

**License Terms**:
- ✅ Public Domain (no restrictions)

---

### 6. Rig Veda Translation - Ralph T.H. Griffith

**Source**: Sacred-texts.com / English translation
**Translator**: Ralph T.H. Griffith (1896)
**License**: Public Domain
**URL**: http://www.sacred-texts.com/hin/rigveda/

**What we use**:
- English translation of Rig Veda
- 10,218 translated verses (94.6% coverage of 10,551 total verses)
- Citation-based format matching DCS structure

**License Terms**:
- ✅ Public Domain (no restrictions)
- Published 1896, well before copyright cutoff

---

## License Compatibility Matrix

| Resource | License | Commercial Use | Attribution Required | Share-Alike |
|----------|---------|----------------|---------------------|-------------|
| DCS Rig Veda Sanskrit | CC BY 4.0 | ✅ Yes | ✅ Yes | ❌ No |
| DCS Dictionary/Morphology | CC BY 4.0 | ✅ Yes | ✅ Yes | ❌ No |
| Sanskrit Parser | MIT | ✅ Yes | ✅ Yes (minimal) | ❌ No |
| Bhagavad Gita Sanskrit | CC BY-SA 4.0 | ✅ Yes | ✅ Yes | ✅ Yes |
| Arnold Translation | Public Domain | ✅ Yes | ❌ No | ❌ No |
| Besant Translation | Public Domain | ✅ Yes | ❌ No | ❌ No |
| Griffith Translation | Public Domain | ✅ Yes | ❌ No | ❌ No |

**ClassicsViewer App License**: MIT (open source, commercial use allowed)

**Compliance**: ✅ All share-alike requirements satisfied (app is MIT/open source)

---

## What We CANNOT Use (Reference)

The following sources were evaluated and rejected due to license incompatibility:

### ❌ Cologne Digital Sanskrit Dictionaries
- **License**: CC BY-NC-SA 3.0
- **Reason**: NonCommercial clause prohibits commercial distribution

### ❌ GRETIL (Göttingen Register of Electronic Texts)
- **License**: CC BY-NC-SA 4.0
- **Reason**: NonCommercial clause

### ❌ SARIT (Search and Retrieval of Indic Texts)
- **License**: CC BY-NC-SA
- **Reason**: NonCommercial clause

### ❌ sanskritdocuments.org
- **License**: "Personal study and research only"
- **Reason**: Explicit commercial use restriction

---

## Verification Checklist

Before using any new Sanskrit source:
- [ ] Verify license is one of: Public Domain, CC0, CC BY, CC BY-SA, MIT
- [ ] Check for NO "NonCommercial" (NC) clause
- [ ] Check for NO "personal use only" restrictions
- [ ] Document license in this file
- [ ] Add attribution to app's LicenseActivity.kt if required

---

## Current Implementation Summary

### Texts Database (sanskrit_texts.db.zip)

**Bhagavad Gita**:
- Sanskrit: CC BY-SA 4.0 (Wikisource)
- English (Arnold): Public Domain
- English (Besant): Public Domain

**Rig Veda**:
- Sanskrit: CC BY 4.0 (DCS - Oliver Hellwig)
- English (Griffith): Public Domain

**Combined**:
- 11,251 verses
- 171,351 words
- 10,694 translation segments
- File size: 4.67 MB compressed

### Lexicon (dcs_sanskrit_lexicon.zip)

**Source**: DCS (CC BY 4.0)
- 179,806 dictionary entries
- 4,700,299 morphology mappings
- 88.0% coverage on Bhagavad Gita
- File size: 34.5 MB compressed

### Build Tools

**sanskrit_parser**: MIT License (build-time only, not distributed)

---

## Required App Attribution

The following attributions must be included in the app's license screen:

```
=== Sanskrit Texts ===

Bhagavad Gita (Sanskrit)
Source: Sanskrit Wikisource
License: CC BY-SA 4.0
URL: https://sa.wikisource.org/wiki/भगवद्गीता

Bhagavad Gita (English - Arnold)
Translator: Edwin Arnold (1885)
License: Public Domain

Bhagavad Gita (English - Besant)
Translator: Annie Besant (1922)
License: Public Domain

Rig Veda (Sanskrit)
Source: Digital Corpus of Sanskrit (DCS)
Author: Oliver Hellwig
License: CC BY 4.0
URL: http://www.sanskrit-linguistics.org/dcs/

Rig Veda (English)
Translator: Ralph T.H. Griffith (1896)
License: Public Domain

=== Sanskrit Lexicon ===

Digital Corpus of Sanskrit (DCS)
Author: Oliver Hellwig
License: CC BY 4.0
Source: http://www.sanskrit-linguistics.org/dcs/
Corpus: 5.5 million words from 268 classical texts
```

---

## Future Expansion Compliance

When adding new texts from DCS (see `DCS_TEXTS_CATALOG.md`):

**All DCS texts**: CC BY 4.0
- ✅ Commercial use allowed
- ✅ Requires attribution (already included for DCS)

**Translations**: Must verify individually
- Pre-1928 works: Generally Public Domain in USA
- Modern translations: Check specific license
- Sacred-texts.com: Many Public Domain translations available
- Wikisource: Check individual work licenses

---

## Academic Citations

For academic use, cite:

**DCS:**
```
Hellwig, Oliver (2010-2024). Digital Corpus of Sanskrit (DCS).
Available at: http://www.sanskrit-linguistics.org/dcs/
```

**Sanskrit Parser:**
```
sanskrit_parser. Available at: https://github.com/kmadathil/sanskrit_parser
```

**Bhagavad Gita Translations:**
```
Arnold, Edwin (1885). The Bhagavad Gita (The Song Celestial).
Available at: https://en.wikisource.org/wiki/The_Bhagavad_Gita_(Arnold_translation)

Besant, Annie (1922). Bhagavad-Gita (4th edition).
Available at: https://en.wikisource.org/wiki/Bhagavad-Gita_(Besant_4th)
```

**Rig Veda Translation:**
```
Griffith, Ralph T.H. (1896). The Rig Veda.
Available at: http://www.sacred-texts.com/hin/rigveda/
```

---

## Status

**Current Implementation**: ✅ Production ready, fully compliant

**Texts**: Bhagavad Gita (700 verses) + Rig Veda (10,551 verses)
**Lexicon**: DCS dictionary + morphology (88% coverage)
**All licenses**: Commercial-use compatible
**Attribution**: Complete and properly included

---

**Last Updated**: October 6, 2025
**Version**: 2.0 (Bhagavad Gita + Rig Veda + DCS Lexicon)
