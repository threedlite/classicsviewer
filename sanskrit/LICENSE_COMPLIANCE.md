# License Compliance for Sanskrit Implementation

## Summary

All Sanskrit resources used in ClassicsViewer are properly licensed for commercial use.

**Status**: ✅ **FULLY COMPLIANT**

## Sources Used

### 1. Digital Corpus of Sanskrit (DCS) - Dictionary & Morphology

**Source**: Digital Corpus of Sanskrit by Oliver Hellwig
**License**: Creative Commons Attribution 4.0 International (CC BY 4.0)
**Repository**: https://github.com/OliverHellwig/sanskrit
**Website**: http://www.sanskrit-linguistics.org/dcs/

**What we use**:
- 179,806 dictionary lemmas with definitions
- 4,700,299 morphology mappings (word → lemma)
- Extracted from 5.5 million annotated words

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
- Added sandhi-split compound mappings (1,956 compounds)
- Reformatted to ClassicsViewer CSV schema

---

### 2. Sanskrit Parser - Sandhi Enhancement

**Source**: sanskrit_parser Python library
**License**: MIT License
**Repository**: https://github.com/kmadathil/sanskrit_parser

**What we use**:
- Automated sandhi (word junction) splitting for compound words
- Used during database creation only (not in app)
- Improves coverage from 40% → 88%

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
- ✅ Share-alike requirement (our app is MIT/open source)
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
- English prose translation (18 chapters)

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

## License Compatibility Matrix

| Resource | License | Commercial Use | Attribution Required | Share-Alike |
|----------|---------|----------------|---------------------|-------------|
| DCS Dictionary/Morphology | CC BY 4.0 | ✅ Yes | ✅ Yes | ❌ No |
| Sanskrit Parser | MIT | ✅ Yes | ✅ Yes (minimal) | ❌ No |
| Bhagavad Gita Sanskrit | CC BY-SA 4.0 | ✅ Yes | ✅ Yes | ✅ Yes |
| Arnold Translation | Public Domain | ✅ Yes | ❌ No | ❌ No |
| Besant Translation | Public Domain | ✅ Yes | ❌ No | ❌ No |

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

## Current Implementation

**Dictionary/Morphology**: DCS (CC BY 4.0) - 88% coverage
**Texts**: Bhagavad Gita from Wikisource (CC BY-SA 4.0)
**Translations**: Arnold (Public Domain) + Besant (Public Domain)
**Tools**: sanskrit_parser (MIT)

**Status**: ✅ Production ready, fully compliant

---

**Last Updated**: October 5, 2025
**Version**: 1.0 (DCS-based implementation)
