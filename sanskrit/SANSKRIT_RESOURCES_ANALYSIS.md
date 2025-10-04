# Sanskrit Resources Analysis for ClassicsViewer

**Date:** October 4, 2025
**Purpose:** Evaluate available Sanskrit texts and dictionaries with compatible open-source licenses

## Summary

**Sanskrit resources for original language + translation:**
- ❌ **No compatible resources with Sanskrit original text + English translation**
- ⚠️ **Project Gutenberg** has ONE Sanskrit text (Vishnu Sahasranaamam, romanized, no translation)
- ✅ **Monier-Williams Dictionary** available (1899, public domain)
- ⚠️ **GRETIL/SARIT** have extensive Sanskrit texts but **CC BY-NC-SA** license (NonCommercial - incompatible)
- ⚠️ **Cologne dictionaries** are **CC BY-NC-SA** (NonCommercial - incompatible)
- ⚠️ **Internet Archive** has parallel texts but unclear licensing (likely copyrighted modern editions)

**Bottom Line:** One minor Sanskrit text available (romanized, no translation). No viable Sanskrit literary works with compatible licenses.

---

## ⚠️ Project Gutenberg - Limited Sanskrit Resources

### 1. Sri Vishnu Sahasranaamam (Sanskrit Original)

**License:** Public Domain
**Format:** Romanized Sanskrit (ITRANS transliteration)
**URL:** https://www.gutenberg.org/ebooks/9000
**Content:** 1000 names/epithets of Lord Vishnu

**Available:**
- ✅ Sanskrit original text (romanized)
- ❌ No Devanagari script
- ❌ No English translation included
- ⚠️ Single hymn/list, not a substantial literary work

**Integration Potential:** ⚠️ Limited - Single text, no translation, romanized only

---

### 2. Classical Sanskrit Works (English-Only Translations - NOT VIABLE)

**License:** Public Domain (pre-1928 works)
**Format:** Multiple formats (HTML, EPUB, Kindle, TXT)

**Why Not Viable:**
- ❌ **English translations only** - no Sanskrit original text
- The app requires original language texts for word lookup
- These translations are useless without the Sanskrit source

#### Available Works (English only - not useful):

**Bhagavad Gita**
- "The Song Celestial" translated by Sir Edwin Arnold
- Project Gutenberg: https://www.gutenberg.org/ebooks/2388

**Mahabharata**
- Translated by Kisari Mohan Ganguli
- Project Gutenberg: https://www.gutenberg.org/ebooks/7864

**Ramayana**
- Various English translations
- Project Gutenberg: https://www.gutenberg.org/ebooks/62496

**Integration Potential:** ❌ None - English-only translations are not useful for this app

---

## ⚠️ Available but Incompatible Resources (NonCommercial Licenses)

### 1. GRETIL - Göttingen Register of Electronic Texts in Indian Languages

**License:** CC BY-NC-SA 4.0 ❌ (NonCommercial - incompatible)
**Website:** http://gretil.sub.uni-goettingen.de/gretil.html
**Format:** TEI XML (converted from 2016)
**GitHub Mirror:** https://github.com/wujastyk/GRETIL-mirror

#### Content:
- Standardized machine-readable texts in Indian languages
- Sanskrit texts in romanized transliteration
- All files available in TEI/XML encoding (except Mahābhārata)
- Extensive corpus of classical Sanskrit literature

**Why Incompatible:**
- CC BY-NC-SA 4.0 has NonCommercial restriction
- Conflicts with MIT-licensed app goals
- Would restrict app distribution

**Translation Status:**
- Primarily Sanskrit originals, not parallel translations
- Focus on providing original texts in machine-readable format

**Integration Potential:** ❌ Blocked by license

---

### 2. SARIT - Search and Retrieval of Indic Texts

**License:** Creative Commons license (likely CC BY-NC-SA) ❌
**Website:** https://sarit.indology.info
**Format:** TEI XML
**GitHub:** https://github.com/sarit/SARIT-corpus

#### Content:
- Electronic editions of Sanskrit and other Indian language texts
- All texts marked up using TEI (Text Encoding Initiative) system
- Free and open-source
- Texts available for download in XML, EPUB, and PDF formats
- Both Devanagari script and romanized transliteration

**Why Incompatible:**
- Creative Commons license with restrictions (likely NC)
- Cannot be used commercially

**Translation Status:**
- Primarily Sanskrit originals
- TEI headers in English, main text in Sanskrit
- Occasional English notes, but not parallel translations

**Integration Potential:** ❌ Blocked by license

---

### 3. Cologne Digital Sanskrit Dictionaries

**License:** CC BY-NC-SA 3.0 ❌ (pre-2016) / CC BY (2016+, variant unclear)
**Website:** https://www.sanskrit-lexicon.uni-koeln.de/
**Format:** XML, text files

#### Content:
- Multiple Sanskrit dictionaries including Monier-Williams
- XML encoding in collaboration with Brown University
- Downloadable files: mw.xml, mw.txt, documentation

**Why Incompatible (for pre-2016 materials):**
- CC BY-NC-SA 3.0 has NonCommercial restriction
- Commercial use requires separate license negotiation
- Materials published 2016+ may have better licensing (need verification)

**Note:** Original 1899 Monier-Williams is public domain, but Cologne's digital encoding may have separate rights

**Integration Potential:** ⚠️ Mixed - Original scans are public domain, but digital XML encoding has restrictions

---

## ✅ Available Sanskrit Dictionary (Compatible License)

### Monier-Williams Sanskrit-English Dictionary

**Full Title:** "A Sanskrit-English Dictionary"
**Author:** Sir Monier Monier-Williams
**Published:** 1899 edition (public domain)
**Earlier Edition:** 1872 (also public domain)

#### Digital Sources:

**Internet Archive**
- Multiple scanned versions
- Formats: PDF, EPUB, TXT
- 1899 edition: https://archive.org/details/in.ernet.dli.2015.31959
- 1872 edition: https://archive.org/details/in.ernet.dli.2015.237155
- License: Public Domain ✅

**University of Cologne - XML Version**
- Monier-Williams Sanskrit Dictionary 1899 Basic
- Online searchable: https://www.sanskrit-lexicon.uni-koeln.de/scans/MWScan/2020/web/webtc/indexcaller.php
- Download: XML and text files available
- License: CC BY-NC-SA 3.0 for digital encoding ❌

**INRIA (French National Institute) - Online Version**
- Searchable interface: https://sanskrit.inria.fr/DICO/index.en.html
- Digital encoding of Monier-Williams
- License: Unclear ⚠️

**Recommendation:**
Use **Internet Archive scanned PDFs** (public domain) rather than Cologne XML (NC restriction). Will require OCR or manual entry for digital integration.

**Integration Potential:** ✅ High (from public domain sources), Medium (requires OCR processing)

---

## ⚠️ Unclear Licensing - Internet Archive Parallel Texts

### Gita Press Editions (Sanskrit-English Parallel Texts)

**Content on Internet Archive:**
- "Srimad Valmiki Ramayana" - Sanskrit text with English translation (Gita Press, Gorakhpur)
- "Mahabharata" - Hindi and Sanskrit versions
- Multiple volumes with parallel translations

**URLs:**
- Ramayana (complete, searchable): https://archive.org/details/valmiki-ramayana-g-p-english
- Ramayana (parts): https://archive.org/details/RmEH_srimad-valmiki-ramayana-with-sanskrit-text-and-english-trans.-balakanda-ayodhya-
- Condensed versions with translations

**License Issue:**
- Gita Press editions are **modern publications** (20th century)
- **Copyright status unclear** - may be under copyright
- Just because it's on Internet Archive doesn't guarantee public domain
- Original ancient texts are public domain, but modern translations/editions are not
- Need to verify copyright status before using

**Translation Quality:**
- High quality Sanskrit-English parallel texts
- Devanagari script with English translation
- Would be ideal IF licensing is compatible

**Integration Potential:** ⚠️ Unknown - Requires license verification

---

## ❌ No Perseus Sanskrit Collection

**Finding:** Perseus Digital Library does NOT have a Sanskrit collection

- Perseus focuses on Greek, Latin, and related classical materials
- 1,639 Greek works, 636 Latin works
- Has Persian/Farsi collection (canonical-farsiLit)
- Has Arabic collection (limited to Quran + dictionaries)
- **No Sanskrit collection found**

---

## 📊 Comparison: Sanskrit vs Other Languages

| Feature | Sanskrit | Persian | Arabic | Greek/Latin |
|---------|----------|---------|--------|-------------|
| **Original Language Texts** | ❌ None (compatible) | ✅ Perseus XML | ❌ None | ✅ Perseus XML |
| **Parallel Texts** | ❌ None (compatible) | ✅ Perseus XML | ❌ None | ✅ Perseus XML |
| **TEI XML Corpus** | ❌ NC-licensed only | ✅ Perseus | ❌ NC or limited | ✅ Perseus |
| **Dictionary** | ✅ MW (PD scans) | ✅ Steingass (PD) | ✅ Lane's (CC BY-SA) | ✅ LSJ/Lewis (PD/CC) |
| **English Translations** | ✅ PG (useless without original) | ✅ Perseus/PG | ❌ None | ✅ Perseus |
| **License Compatibility** | ❌ Poor | ✅ Good | ❌ Poor | ✅ Excellent |

**Assessment:** Sanskrit is **same as Arabic** (no original language texts with compatible licenses), **worse than Persian** (Persian has parallel texts from Perseus)

---

## 📋 Integration Recommendations

### ❌ Option 1: Project Gutenberg Texts - NOT VIABLE

**Project Gutenberg has English-only translations**
- ❌ No Sanskrit text (English only)
- ❌ Not useful for this app (requires original language)
- The app is designed for original language texts with word lookup
- English-only translations provide no value

**Recommendation:** Do not pursue

---

### Option 1: Monier-Williams Dictionary (If needed for future Sanskrit texts)

**Add MW Sanskrit-English Dictionary**
- ✅ Public domain (1899 edition)
- ✅ Available from Internet Archive
- ❌ No XML (requires OCR or manual processing)
- ⚠️ Large work (~1600 pages)
- ⚠️ Only useful if Sanskrit texts become available

**Implementation Path:**
1. Download scanned PDF from Internet Archive
2. OCR processing or use existing digital text
3. Parse dictionary entries (headword, definition, etymology)
4. Create Sanskrit normalization rules (Devanagari)
5. Package as dictionary.csv + normalization_rules.csv

**Effort:** High (OCR or data extraction from scans)
**Value:** High IF Sanskrit texts become available

---

### Option 2: Investigate Gita Press Licensing (Medium-term)

**Verify copyright status of parallel texts**
- Contact Gita Press directly
- Check copyright pages in Internet Archive scans
- Determine if any editions are public domain
- If compatible, these would provide ideal parallel Sanskrit-English texts

**Effort:** Low (research and contact)
**Potential Value:** Very High (if compatible, would provide parallel texts)

---

### Option 3: Wait for Open Sanskrit Corpus (Long-term)

**Monitor for new developments:**
- GRETIL/SARIT license changes to CC BY or CC BY-SA
- New digital humanities projects with compatible licenses
- Community-driven open Sanskrit initiatives

**Effort:** Minimal (passive monitoring)
**Timeline:** Uncertain

**This is the only realistic path forward for Sanskrit integration**

---

## Technical Notes

### Sanskrit Text Encoding

**Scripts:**
- **Devanagari** (देवनागरी): Primary script for Sanskrit
- **IAST** (International Alphabet of Sanskrit Transliteration): Romanization
- **Harvard-Kyoto**: ASCII transliteration scheme

**GRETIL/SARIT Format:**
- Primarily romanized transliteration
- SARIT also provides Devanagari
- TEI XML structure

---

### Sanskrit Normalization Rules

Devanagari normalization needed for dictionary lookups:

```csv
language,pattern,replacement,description,priority
sanskrit,[\u0900-\u0903],,Remove combining marks,1
sanskrit,[\u093C],,Remove nukta,2
sanskrit,[\u0951-\u0952],,Remove Vedic accents,3
sanskrit,[\u0964-\u0965],,Remove dandas (sentence markers),4
```

**Additional considerations:**
- Sandhi rules (word combination transformations)
- Vowel length variations
- Anusvara/Visarga normalization
- IAST to Devanagari conversion

---

### Project Gutenberg Text Structure

**Bhagavad Gita Example:**
- 18 chapters
- ~700 verses total
- Verse structure varies by chapter
- Available in multiple translations

**Mahabharata:**
- 18 books (parvas)
- ~100,000 verses (original)
- Ganguli translation: condensed prose
- Can extract chapter/section structure

**Ramayana:**
- 7 kandas (books)
- ~24,000 verses (original)
- Various translations available

---

## Comparison to Current App Languages

| Language | Texts | Authors/Works | Translations | Dictionary | Format | License | Status |
|----------|-------|---------------|--------------|------------|--------|---------|--------|
| Greek | Perseus | ~100 authors | Yes | LSJ | TEI XML | CC BY-SA 3.0 | ✅ Integrated |
| Latin | Perseus | ~95 authors | Yes | Whitaker's | TEI XML | CC BY-SA 3.0 | ✅ Integrated |
| Hebrew | OSHB | 39 books | No | Strong's | OSIS XML | CC BY 4.0 | ✅ Integrated |
| Persian | Perseus + PG | ~4 poets | Yes | Steingass | TEI XML/HTML | PD/CC BY-SA | ❌ Not integrated |
| Sumerian | Public Domain | 2 works | Yes | N/A | Custom | Public Domain | ✅ Integrated |
| Akkadian | Public Domain | 1 work | Yes | N/A | Custom | Public Domain | ✅ Integrated |
| **Sanskrit** | **Project Gutenberg** | **3+ epics** | **Yes (English only)** | **MW (scans)** | **HTML/EPUB** | **Public Domain** | **❌ Not integrated** |
| Arabic | Perseus | Quran only | No | Lane's | TEI XML | CC BY-SA 3.0 | ❌ Not integrated |

**Sanskrit Status:** Classical texts available but **English translations only** (no parallel Sanskrit-English), dictionary requires OCR processing

---

## License Compatibility Summary

### ✅ Compatible Licenses:
- **Public Domain** (Project Gutenberg texts, Internet Archive Monier-Williams scans)
- All compatible with MIT-licensed app
- Allow commercial use
- Can be redistributed

### ❌ Incompatible Licenses:
- **CC BY-NC-SA** (GRETIL, SARIT, Cologne dictionaries pre-2016)
- NonCommercial restriction conflicts with app goals
- Would limit app distribution

### ⚠️ License Verification Needed:
- **Gita Press editions** on Internet Archive (modern publications, likely copyrighted)
- **Cologne dictionaries post-2016** (may be CC BY, need verification)
- **INRIA Monier-Williams** (online version, unclear license)

---

## Next Steps

### Immediate Actions (Low Risk):

1. ✅ **Add Project Gutenberg Texts** (English only)
   - Bhagavad Gita (Edwin Arnold translation)
   - Mahabharata (Ganguli translation)
   - Ramayana (various translations)
   - Parse and structure for app

2. ⏸️ **Monier-Williams Dictionary** (if needed)
   - Download Internet Archive scans
   - OCR processing required
   - High effort, high value

### Research Actions (Medium Priority):

3. ⚠️ **Investigate Gita Press Licensing**
   - Contact Gita Press for copyright clarification
   - Check if any editions are public domain
   - Would provide ideal parallel Sanskrit-English texts

4. ⏸️ **Monitor GRETIL/SARIT**
   - Watch for license changes
   - Track community discussions
   - Consider requesting CC BY licensing

---

## Conclusion

**Sanskrit for ClassicsViewer: NOT VIABLE**

**Available NOW with Compatible Licenses:**
- ❌ **No Sanskrit texts** with compatible licenses
- ❌ Project Gutenberg has English-only translations (not useful for this app)
- ✅ Monier-Williams dictionary (public domain scans, requires OCR - but useless without texts)

**Blocked by Licensing:**
- ❌ GRETIL/SARIT (extensive Sanskrit corpus with original texts, but CC BY-NC-SA)
- ❌ Cologne dictionaries XML (CC BY-NC-SA for pre-2016 materials)

**Unclear/Research Needed:**
- ⚠️ Gita Press parallel texts (may be copyrighted modern editions)
- ⚠️ Post-2016 Cologne materials (license unclear)

**Comparison:**
- **Same as Arabic:** No texts with original language available under compatible licenses
- **Worse than Persian:** Persian has Perseus parallel texts (CC BY-SA 3.0)
- **Worse than Greek/Latin:** No Perseus-equivalent parallel text corpus

**Recommendation:**
**Do NOT integrate Sanskrit at this time.** The app requires original language texts for word lookup and language learning. English-only translations provide no value.

To add Sanskrit in the future:
1. Verify Gita Press licensing for parallel texts, or
2. Wait for GRETIL/SARIT license changes to CC BY or CC BY-SA, or
3. Commission new parallel translations with open licenses

**Sanskrit is NOT viable** without the original language texts. English-only translations defeat the purpose of the app.

---

## Resources Summary

### Sanskrit Texts (Compatible):
- **Project Gutenberg Bhagavad Gita:** https://www.gutenberg.org/ebooks/2388
- **Project Gutenberg Mahabharata:** https://www.gutenberg.org/ebooks/7864
- **Project Gutenberg Ramayana:** https://www.gutenberg.org/ebooks/62496

### Sanskrit Texts (Incompatible - NC License):
- **GRETIL:** http://gretil.sub.uni-goettingen.de/gretil.html
- **SARIT:** https://sarit.indology.info

### Sanskrit Dictionaries (Compatible):
- **Monier-Williams 1899 (Internet Archive):** https://archive.org/details/in.ernet.dli.2015.31959

### Sanskrit Dictionaries (Incompatible - NC License):
- **Cologne Digital Sanskrit Dictionaries:** https://www.sanskrit-lexicon.uni-koeln.de/

### Unclear Licensing (Requires Research):
- **Internet Archive Gita Press Ramayana:** https://archive.org/details/valmiki-ramayana-g-p-english

### License Information:
- **Public Domain:** Pre-1928 works in US, fully compatible
- **CC BY-NC-SA:** https://creativecommons.org/licenses/by-nc-sa/4.0/ (incompatible)
