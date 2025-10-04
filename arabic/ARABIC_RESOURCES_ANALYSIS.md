# Arabic Resources Analysis for ClassicsViewer

**Date:** October 4, 2025
**Purpose:** Evaluate available Arabic texts and dictionaries with compatible open-source licenses

## Summary

For medieval Arabic texts with English translations under compatible licenses (CC-BY, CC BY-SA, MIT, Public Domain): **None found**.

Only Lane's Arabic-English Lexicon is available with a compatible license.

---

## ✅ Available Resources (Compatible Licenses)

### 1. Lane's Arabic-English Lexicon

**License:** Creative Commons Attribution-ShareAlike 3.0 United States (CC BY-SA 3.0)
**Source:** Perseus Digital Library (Tufts University)
**Format:** TEI XML
**Content:** Comprehensive classical Arabic dictionary (8 volumes, 1863-1893)

**Details:**
- Based on 112 classical Arabic sources (mostly medieval)
- Organized by root structure (traditional Arabic lexicography)
- Digital edition created by Perseus with support from US Dept of Education & Max Planck Society
- TEI XML edition by Harry Diakoff (Alpheios Project)

**Access:**
- **Direct Download:** https://www.perseus.tufts.edu/hopper/opensource/downloads/texts/hopper-texts-Arabic.tar.gz (15.5 MB)
- **GitHub Mirror:** https://github.com/cltk/arabic_text_perseus
- **Amended Version:** https://github.com/laneslexicon/lexicon_xml (⚠️ no license for amendments; use Perseus originals branch)

**Additional Restriction:** Users must offer Perseus any modifications they make


---

### 2. Quran

**License:** CC BY-SA 3.0 (from Perseus)
**Source:** Perseus Digital Library
**Format:** TEI XML
**Content:** Quran text with transliteration

**Access:**
- Same Perseus archive as Lane's Lexicon
- Available at: https://github.com/cltk/arabic_text_perseus/tree/master/Quran/opensource


---

## ❌ Incompatible Resources (NonCommercial Licenses)

### 1. OpenITI (Open Islamicate Texts Initiative)

**License:** CC BY-NC-SA 4.0 ❌
**Content:** ~4,300 unique Arabic texts (9th-16th century CE)
**GitHub:** https://github.com/OpenITI

**Why Incompatible:**
- NC (NonCommercial) restriction prevents commercial use
- Conflicts with MIT-licensed app goals
- Would restrict app distribution in app stores
- Some texts include translations

**Coverage:**
- Most comprehensive corpus (period 800-1600 CE)
- Built from Shamilah, al-Jāmiʿ al-Kabīr, Maktabat al-Shiʿa collections
- Machine-actionable scholarly corpus
- TEI XML and mARkdown formats

---

### 2. Global Medieval Sourcebook

**License:** CC BY-NC-SA 4.0 ❌
**Website:** https://sourcebook.stanford.edu
**GitHub:** https://github.com/medieval-source-book

**Why Incompatible:**
- NC (NonCommercial) restriction
- Would limit app distribution and user rights

**Content:**
- 100 medieval texts (600-1600 CE)
- 25 languages including Arabic, Persian, Hebrew
- Parallel text display (original + English translation)
- TEI-XML files downloadable from GitHub
- Backed by NEH grant (2018-2020)

**Note:** This would be ideal if licensing were compatible - has Arabic texts with English translations in TEI-XML format

---

## ⚠️ Resources with Access/Licensing Issues

### 1. Arabic Collections Online (ACO)

**Website:** https://dlib.nyu.edu/aco
**License:** Mixed (mostly public domain, some CC BY-NC-ND 4.0)

**Content:**
- 17,699 volumes of public domain Arabic texts
- Classical Islamic period through modern
- Topics: literature, philosophy, law, religion, science

**Problems:**
- No API or bulk download capability
- Individual PDF downloads only (high/low res)
- Mixed licensing (some partner institutions use CC BY-NC-ND 4.0)
- No standardized text format (PDFs only)
- Would require manual download of 17,699 files

**GitHub:**
- `NYULibraries/aco-site` - website code only
- `pulibrary/aco` - collaboration code only
- No text repository

---

### 2. Qafiyah Arabic Poetry Database

**License:** MIT ✅
**Website:** https://qafiyah.com
**GitHub:** https://github.com/alwalxed/qafiyah

**Content:**
- 944,000 verses by 932 poets
- 10 historical eras (classical & modern)
- Open API and database dumps

**Problem:**
- **No English translations** ❌
- Arabic text only
- Focuses on meter, rhyme analysis
- Not useful without translations for ClassicsViewer's parallel-text model

---

### 3. Perseus Arabic Collection

**License:** CC BY-SA 3.0 ✅
**Content:** Very limited

**What's Included:**
- Lane's Arabic-English Lexicon ✅
- Quran ✅
- Possibly Salmone (unknown lexicon/reference work)

**What's Missing:**
- No medieval Arabic literature
- No classical poetry (al-Mutanabbi, Abu Nuwas, etc.)
- No philosophy (Ibn Rushd, al-Farabi, etc.)
- No history (Ibn Khaldun, al-Tabari, etc.)

---

## License Compatibility Analysis

### ClassicsViewer Current Licenses:
- **App:** MIT License
- **Greek/Latin texts:** CC BY-SA 3.0 (commercial use allowed ✅)
- **Hebrew Bible:** CC BY 4.0 (commercial use allowed ✅)
- **Cuneiform:** Public Domain (commercial use allowed ✅)

### CC BY-NC-SA 4.0 Issues:
- **NC (NonCommercial):** Users cannot use texts for commercial purposes
- **App Store Conflicts:** Google Play/Apple may reject apps with NC content
- **Mixed Licensing:** Creates confusion about user rights
- **Violates Project Goals:** Conflicts with open-source unrestricted access

**Technical Compatibility:** MIT → CC BY-NC-SA is technically allowed
**Practical Compatibility:** ❌ Creates restricted subset of content, defeats purpose of open app

---

---

## Comparison to Other Languages

| Language | Texts Available | Translations | License | Status |
|----------|----------------|--------------|---------|--------|
| Greek | ~100 authors | Yes | CC BY-SA 3.0 | ✅ Integrated |
| Latin | ~95 authors | Yes | CC BY-SA 3.0 | ✅ Integrated |
| Hebrew | 39 books (Bible) | No | CC BY 4.0 | ✅ Integrated |
| Sumerian | 2 works | Yes | Public Domain | ✅ Integrated |
| Akkadian | 1 work | Yes | Public Domain | ✅ Integrated |
| **Arabic** | **0 texts** | **N/A** | **N/A** | **❌ None available** |

**Arabic Uniquely Lacks:** Literary texts with translations under compatible licenses

---

## Technical Notes

### Perseus Download Structure
```
hopper-texts-Arabic.tar.gz (15.5 MB)
├── Lane/
│   └── opensource/
│       ├── _A0.xml
│       ├── _A1.xml
│       └── ... (lexicon entries by letter)
├── Quran/
│   └── opensource/
│       └── arabic-translit.xml
└── Salmone/
    └── opensource/
        └── (unknown content)
```

### Integration Path (Lane's Lexicon)
1. Parse TEI XML structure
2. Extract lemma (headwords)
3. Extract definitions
4. Extract root information
5. Create normalization rules for Arabic (remove diacritics, etc.)
6. Build morphology mappings if available
7. Package as dictionary.csv + normalization_rules.csv

---

## Conclusion

**Current Reality:**
The open-source ecosystem for Arabic classical/medieval texts with English translations is severely limited compared to Greek/Latin. Only lexicographical resources (dictionaries) are available with compatible licenses.

**Immediate Action:**
Add Lane's Arabic-English Lexicon as a dictionary resource to enable Arabic word lookup functionality.

**Long-term Goal:**
Monitor the digital humanities community for new openly-licensed Arabic text corpora or consider commissioning translations of key works.

**The Gap:**
Unlike Perseus Digital Library's comprehensive Greek/Latin offerings, there is no equivalent open-access corpus of classical Arabic literature with parallel English translations under permissive licenses.
