# Persian Resources Analysis for ClassicsViewer

**Date:** October 4, 2025
**Purpose:** Evaluate available Persian texts and dictionaries with compatible open-source licenses

## Summary

**Persian resources for original language + translation:**
- ✅ **Perseus Digital Library** has Persian texts with parallel translations (CC BY-SA 3.0)
- ✅ **Steingass Persian-English Dictionary** available (public domain, 1892)
- ❌ **Project Gutenberg** has English-only translations (no Persian original - not useful for this app)
- ✅ Best option among non-European languages for integration

---

## ✅ Available Persian Texts (Compatible Licenses)

### Perseus Digital Library - Persian Texts with Parallel Translations

**License:** Creative Commons Attribution-ShareAlike 3.0 United States (CC BY-SA 3.0)
**Repository:** https://github.com/PerseusDL/canonical-farsiLit
**Format:** TEI XML

#### Available Works:

**Current Status:** Only 1 author available (as of October 2025)
- Perseus Catalog shows 0 Persian works in metadata
- canonical-farsiLit repository contains only Hafez

**Hafez - Divān (Complete)**
- Persian original: `hafez.divan.perseus-far1.xml`
  - **✅ Uses Persian script** (e.g., "الا یا ایها الساقی ادر کاسا و ناولها")
  - NOT transliteration - actual Persian/Arabic alphabet
- English translation: `hafez.divan.perseus-eng1.xml`
  - Line-by-line parallel translation
  - Each line has two segments (couplet structure)
- **Parallel Persian-English text available!** ✅

**Additional Restriction:** Users must offer Perseus any modifications they make

**Integration Potential:** ✅ Very High - TEI XML with parallel texts, Persian script, same format as Greek/Latin

---

## ❌ NOT VIABLE - Project Gutenberg (English-Only Translations)

### Project Gutenberg - Persian Poetry

**License:** Public Domain (pre-1928 works)
**Format:** Multiple formats (HTML, EPUB, Kindle, TXT)
**Access:** https://www.gutenberg.org

**Why Not Viable:**
- ❌ **English translations only** - no Persian original text
- The app requires original language texts for word lookup and language learning
- These translations are useless without the Persian source

#### Available Works (English only - not useful):

**Rumi (Jalāl ad-Dīn Muhammad Rūmī, 1207-1273)**
- "Jalálu'd-dín Rúmí" - Nicholson/Whinfield translations
- "The Festival of Spring" - English translation
- Project Gutenberg: https://www.gutenberg.org/ebooks/45159, https://www.gutenberg.org/ebooks/57068

**Hafiz (Hafez, c. 1315-1390)**
- "Hafiz in London" - McCarthy translation
- Project Gutenberg: https://www.gutenberg.org/ebooks/51392

**Omar Khayyam (1048-1131)**
- "Rubáiyát" - Fitzgerald translation
- Project Gutenberg: https://www.gutenberg.org/ebooks/35260

**Integration Potential:** ❌ None - English-only translations are not useful for this app

---

## ✅ Available Persian Dictionaries (Compatible Licenses)

### 1. Steingass Persian-English Dictionary

**Full Title:** "A Comprehensive Persian-English Dictionary, Including the Arabic Words and Phrases to be Met with in Persian Literature"
**Author:** Francis Joseph Steingass
**Published:** 1892, London (Routledge & K. Paul)
**Original License:** Public Domain (pre-1928)

#### ✅ Best Option - Explicit Public Domain License:

**Internet Archive**
- **URL:** https://archive.org/details/AComprehensivePersian-EnglishDictionary-FrancisJosephSteingass
- **License:** ✅ Public Domain (explicitly stated)
- **Formats:** Scanned PDF, EPUB, **TXT (7.0 MB - OCR already done!)**
- **Year:** 1892 edition
- **Status:** Clear licensing, no restrictions
- **CRITICAL LIMITATION:** ❌ TXT format is **transliteration only** (no Persian script)
- **Problem:** App requires Persian script for word lookup - transliteration is not usable
- **Alternative copies:**
  - 1872 edition: https://archive.org/details/in.ernet.dli.2015.237155
  - https://archive.org/details/acomprehensivepersianenglishdictionaryincludingthearabicnodrm

#### ⚠️ Digital Versions with Unclear/Problematic Licenses:

**University of Chicago - Digital Dictionaries of South Asia (DDSA)**
- URL: https://dsal.uchicago.edu/dictionaries/steingass/
- License: ⚠️ "Creative Commons License" (variant not specified)
- Format: Online searchable database
- **Advantage:** ✅ Includes **Perso-Arabic and Roman alphabets** (has Persian script!)
- Mobile apps available (iOS/Android)
- **Problem:** License terms not explicitly stated - need clarification

**Alpheios Project - XML Version**
- Repository: https://github.com/alpheios-project/stg
- Source data: https://sourceforge.net/p/alpheios/code/HEAD/tree/dictionaries/per/stg/trunk/src/
- Format: XML (parseable)
- License: ❌ No LICENSE file in repository
- Deployed via Alpheios Lexi-Get service
- **Problem:** No explicit license

**Theo Beers - Improved SQLite Version**
- 69,888 entries in SQLite database
- Cleaned-up version with improved formatting
- Website: https://steingass.theobeers.com/
- GitHub: Available for download
- License: ⚠️ Not explicitly stated
- **Problem:** Need to verify licensing terms

**ACDH-OeAW - Alternative Persian Dictionary (TEI XML)**
- Different dictionary: "The Small Farsi-English Internet Dictionary"
- Source: University of Vienna, Department of Oriental Studies
- Format: TEI-XML (TEI Lex0 customization)
- Repository: https://github.com/acdh-oeaw/pes_eng_dict-data
- License: ⚠️ Need to verify
- **Problem:** Unclear licensing

**Integration Potential:** ⚠️ **REQUIRES PERSIAN SCRIPT VERSION**
- Internet Archive TXT is transliteration only (not usable)
- Need to verify if DDSA/Alpheios/Theo Beers versions have Persian script
- May require OCR from scanned PDF if no scripted version has clear license

---

### 2. Steingass Arabic-English Dictionary

**Note:** Steingass also authored an Arabic-English dictionary
- "The Student's Arabic-English Dictionary" (1884)
- Also available on Internet Archive
- Public Domain
- Could be useful for Arabic language support

**Integration Potential:** ✅ High - Same author as Persian dictionary, proven quality

---

## 📊 Comparison: Persian vs Arabic

| Feature | Persian | Arabic |
|---------|---------|--------|
| **Classical Poetry** | ✅ Rumi, Hafiz, Khayyam (public domain) | ❌ None available |
| **English Translations** | ✅ Yes (Project Gutenberg) | ❌ None (except Arabian Nights) |
| **Perseus Texts** | ✅ Yes (CC BY-SA 3.0) | ❌ Only Quran + dictionaries |
| **Parallel Texts** | ✅ Yes (Perseus TEI XML) | ❌ None |
| **Dictionary** | ✅ Steingass (public domain) | ✅ Lane's Lexicon (CC BY-SA 3.0) |
| **Format** | ✅ TEI XML, structured | ❌ Mostly PDFs or NC-licensed |
| **License Compatibility** | ✅ Public domain / CC BY-SA | ⚠️ Limited options |

**Winner:** Persian has **significantly more resources** with compatible licenses

---

## ❌ Incompatible Persian Resources

### OpenITI Persian Texts

**License:** CC BY-NC-SA 4.0 ❌
**Content:** Persian texts in the Islamicate corpus
**Repository:** https://github.com/OpenITI
**Problem:** NonCommercial restriction (same as Arabic)

### Global Medieval Sourcebook - Persian Texts

**License:** CC BY-NC-SA 4.0 ❌
**Content:** Medieval Persian texts with English translations
**Repository:** https://github.com/medieval-source-book
**Problem:** NonCommercial restriction

---

## 📋 Integration Recommendations

### ❌ Option 1: Project Gutenberg Poetry - NOT VIABLE

**Project Gutenberg has English-only translations**
- ❌ No Persian text (English only)
- ❌ Not useful for this app (requires original language)
- The app is designed for original language texts with word lookup
- English-only translations provide no value

**Recommendation:** Do not pursue

---

### Option 1: Perseus Persian Texts (High Priority - BEST OPTION)

**Add Hafez Divan from Perseus**
- ✅ CC BY-SA 3.0 - compatible license
- ✅ TEI XML format - same as Greek/Latin
- ✅ **Parallel Persian-English text** available
- ✅ Same processing pipeline as existing Perseus texts
- ✅ Can integrate into existing database creation script

**Implementation Path:**
1. Clone https://github.com/PerseusDL/canonical-farsiLit
2. Parse Hafez Divan TEI XML files
3. Extract Persian text and English translation
4. Create parallel text view (like Greek/Latin)
5. Add to database creation pipeline

**Effort:** Low-Medium (reuse existing Perseus parsers)
**Value:** Very High (parallel texts, structured data)

---

### Option 2: Steingass Dictionary (Medium Priority)

**Add Steingass Persian-English Dictionary**
- ✅ Public domain - fully compatible (Internet Archive version)
- ✅ **TXT format available (7.0 MB) - no OCR needed!**
- ✅ Clear licensing (unlike XML versions)
- ✅ Similar to Lane's Lexicon integration

**Implementation Path:**
1. Download TXT file from Internet Archive (public domain)
2. Parse dictionary entries from plain text (headword, definition, examples)
3. Create Persian normalization rules
4. Package as dictionary.csv + normalization_rules.csv
5. Integrate with existing dictionary import system

**Alternative (if licensing can be verified):**
- Use Alpheios XML or Theo Beers SQLite if explicit license is obtained
- May have cleaner structure than raw TXT

**Effort:** Medium (TXT parsing) or Low (if XML/SQLite licensing verified)
**Value:** High (enables Persian word lookup)

---

## Technical Notes

### Perseus canonical-farsiLit Structure

```
canonical-farsiLit/
├── data/
│   └── hafez/
│       └── divan/
│           ├── hafez.divan.perseus-far1.xml  (Persian original)
│           └── hafez.divan.perseus-eng1.xml  (English translation)
└── README.md
```

**License:** CC BY-SA 3.0
**Additional Restriction:** Users must offer Perseus any modifications

---

### ❌ Project Gutenberg Text Formats (NOT USED)

Project Gutenberg Persian texts are English-only translations:
- ❌ No Persian original text
- ❌ Not useful for this app
- English translations without the original language defeat the purpose of the app

---

### Steingass Dictionary Data Formats

1. **XML (Alpheios):** Custom format, parseable
2. **SQLite (Theo Beers):** 69,888 entries, structured
3. **Online (DDSA):** Web scraping possible, CC license
4. **Scanned PDFs (Internet Archive):** OCR required, less ideal

**Recommendation:** Use Alpheios XML or Theo Beers SQLite

---

## Normalization Rules for Persian

Persian text normalization needed for dictionary lookups:

```csv
language,pattern,replacement,description,priority
persian,[\u064B-\u0652],,Remove Arabic diacritics,1
persian,[\u0670],,Remove alef khanjariyah,2
persian,ى,ی,Normalize Arabic yeh to Farsi yeh,3
persian,ك,ک,Normalize Arabic kaf to Farsi kaf,4
persian,ي,ی,Normalize yeh forms,5
```

**Additional considerations:**
- Zero-width non-joiner (ZWNJ) handling
- Persian-specific characters vs Arabic variants
- Compound words and affixes

---

## Comparison to Current App Languages

| Language | Texts | Authors/Works | Translations | Dictionary | Format | License | Status |
|----------|-------|---------------|--------------|------------|--------|---------|--------|
| Greek | Perseus | ~100 authors | Yes | LSJ | TEI XML | CC BY-SA 3.0 | ✅ Integrated |
| Latin | Perseus | ~95 authors | Yes | Whitaker's | TEI XML | CC BY-SA 3.0 | ✅ Integrated |
| Hebrew | OSHB | 39 books | No | Strong's | OSIS XML | CC BY 4.0 | ✅ Integrated |
| Sumerian | Public Domain | 2 works | Yes | N/A | Custom | Public Domain | ✅ Integrated |
| Akkadian | Public Domain | 1 work | Yes | N/A | Custom | Public Domain | ✅ Integrated |
| **Persian** | **Perseus** | **Hafez Divan** | **Yes** | **Steingass** | **TEI XML** | **CC BY-SA 3.0** | **❌ Not integrated** |
| Arabic | Perseus | Quran only | No | Lane's | TEI XML | CC BY-SA 3.0 | ❌ Not integrated |

**Persian offers:** Parallel Persian-English texts from Perseus, comprehensive dictionary - **ready for integration**

---

## License Compatibility Summary

### ✅ Compatible Licenses:
- **Public Domain** (Steingass dictionary)
- **CC BY-SA 3.0** (Perseus Persian texts)
- All compatible with MIT-licensed app
- Allow commercial use
- Can be redistributed

### ❌ Incompatible Licenses:
- **CC BY-NC-SA 4.0** (OpenITI, Global Medieval Sourcebook)
- NonCommercial restriction conflicts with app goals
- Would limit app distribution

### ⚠️ License Verification Needed:
- Alpheios Steingass XML (repository has no LICENSE file)
- Theo Beers SQLite version (need to check terms)
- ACDH-OeAW Persian dictionary (need to verify license)

**Recommendation:** Use sources with explicit public domain or CC BY-SA licenses

---

## Next Steps

### Immediate Actions:
1. ✅ **Add Perseus Hafez** - Parallel Persian-English text (HIGHEST PRIORITY)
   - Clone canonical-farsiLit repository
   - Integrate with existing Perseus parser
   - TEI XML format same as Greek/Latin
   - **Persian script available** - ready for integration
   - **No dictionary initially** - integrate texts first, add dictionary later when licensing is resolved

### Dictionary Status:
- **Current decision:** Integrate Persian texts WITHOUT dictionary initially
- **Reasoning:** No Persian-script dictionary with clear compatible licensing available
- Internet Archive: Transliteration only (not usable)
- DDSA/Alpheios/Theo Beers: Have Persian script but unclear licensing

### Long-term Goals:
1. Monitor for openly-licensed Persian dictionary with Persian script
2. Consider DDSA if licensing can be clarified
3. Monitor for new open Persian text corpora
4. Consider commissioning Persian-English parallel texts for other classical works
5. Expand beyond poetry to prose (if sources become available)

---

## Conclusion

**Persian vs Arabic for ClassicsViewer:**

**Persian:** ✅ **Ready to integrate**
- Classical poetry with English translations (public domain)
- Parallel Persian-English texts from Perseus (CC BY-SA 3.0)
- Comprehensive dictionary (Steingass, public domain)
- TEI XML format compatible with existing pipeline

**Arabic:** ❌ **Limited options**
- Only dictionary available (Lane's Lexicon)
- No classical texts with compatible licenses
- No parallel texts available

**Recommendation:** Persian has all the necessary components (texts, translations, dictionary) with compatible licenses and formats, making it a much better candidate for the next language addition to ClassicsViewer.

---

## Resources Summary

### Persian Texts (Compatible):
- **Project Gutenberg:** https://www.gutenberg.org/ebooks/author/43130 (Rumi)
- **Perseus canonical-farsiLit:** https://github.com/PerseusDL/canonical-farsiLit

### Persian Dictionaries (Compatible):
- **Steingass (DDSA):** https://dsal.uchicago.edu/dictionaries/steingass/
- **Steingass (Internet Archive):** https://archive.org/details/AComprehensivePersian-EnglishDictionary-FrancisJosephSteingass
- **Alpheios XML:** https://sourceforge.net/p/alpheios/code/HEAD/tree/dictionaries/per/stg/trunk/src/

### License Information:
- **CC BY-SA 3.0:** https://creativecommons.org/licenses/by-sa/3.0/us/
- **Public Domain:** Pre-1928 works, fully compatible
