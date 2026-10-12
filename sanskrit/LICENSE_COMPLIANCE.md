# License Compliance for Sanskrit Implementation

## Summary

All Sanskrit texts and English translations shipped in the app are public
domain, CC BY or CC BY-SA. Policy:

- The app is free, but app-store distribution may count as commercial use,
  so sources with a NonCommercial clause are not used.
- A text that is on Project Gutenberg is included on that basis, under the
  Project Gutenberg License. The app's licence screen (Android
  `LicenseActivity.kt`, iOS `LicenseView.swift`) names Project Gutenberg
  and the ebook number for every such text, carries the licence's
  required notice (paragraph 1.E.1) with a link to the full licence, states
  that no fee is charged (1.E.7), and points to gutenberg.org for the
  original files (1.E.6). The build strips the Gutenberg header, footer
  and licence text from the file that ships; only the body is used.
- Transcribed e-texts only (Gutenberg, Wikisource, DCS); OCR output is never
  a source.
- Preferred order when choosing a source: Project Gutenberg, then
  Wikisource, then another transcription with an explicit public-domain,
  CC BY or CC BY-SA statement.

**Status**: ✅ **COMPLIANT** with the policy above.

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
- ✅ Share-alike requirement (our app is open source, MIT OR Apache-2.0 ✓)
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

**Source**: English Wikisource, *The Hymns of the Rigveda* (2nd ed., 1896),
1,028 hymn pages, Books 1–10
**Translator**: Ralph T.H. Griffith (1826–1906)
**License**: Public Domain translation; Wikisource contributions CC BY-SA
**URL**: https://en.wikisource.org/wiki/The_Hymns_of_the_Rigveda

**What we use**:
- The complete translation, one segment per stanza, matched to the DCS
  Rig Veda by book, hymn and stanza number
- Fetched and parsed by `data-sources/download_rigveda_griffith.py` and
  `data-sources/parse_rigveda_griffith.py`; the build runs them when the
  parsed file is missing

**License Terms**:
- ✅ Public Domain translation (published 1896; translator died 1906)
- ✅ Wikisource's transcription terms (CC BY-SA) are already accepted for
  the Bhagavad Gita text

---

### 7. Mahabharata Translation - Kisari Mohan Ganguli

**Source**: Project Gutenberg, ebooks 15474, 15475, 15476, 15477
**Translator**: Kisari Mohan Ganguli (1883–1896), published by P. C. Roy
**License**: Public Domain
**URL**: https://www.gutenberg.org/ebooks/15474 (and 15475–15477)

**What we use**:
- The complete English prose translation, 18 books, 2,106 section units
- Attached to the DCS critical-edition text chapter by chapter through the
  Brodbeck & Black concordance (see `data-sources/SOURCES.md`)
- Ganguli's footnotes, appended to the section that cites them

**License Terms**:
- ✅ Public Domain: the translator died in 1908; Gutenberg marks the texts
  "Public domain in the USA"; included under the Gutenberg rule above
- Project Gutenberg License: the build uses only the text between the
  `*** START OF` / `*** END OF` markers (header, footer and licence text
  removed); the licence screen credits ebooks 15474–15477 to Project
  Gutenberg and shows the licence notice, as the rule above requires

**Note on the Sanskrit side**: the DCS Mahābhārata derives from the
Tokunaga/Smith electronic critical edition, whose file header carries a
BORI copyright notice without a licence grant; DCS licenses its corpus
CC BY 4.0 and the app ships the DCS text.

---

### 8. Chāndogya Upaniṣad Translation - F. Max Müller

**Source**: English Wikisource, *Sacred Books of the East*, vol. 1 (1879),
Khândogya-upanishad, eight prapāṭhaka pages transcluded from validated scans
**Translator**: Friedrich Max Müller (1823–1900)
**License**: Public Domain translation; Wikisource contributions CC BY-SA
**URL**: https://en.wikisource.org/wiki/Sacred_Books_of_the_East/Volume_1/Khândogya-upanishad

**What we use**:
- All 8 prapāṭhakas, numbered prapāṭhaka.khaṇḍa.verse like the DCS text;
  each khaṇḍa's verses form one segment on the DCS chapter with the same
  label (Müller's khaṇḍa 7.26 has no DCS counterpart and is not written)
- Fetched and parsed by `data-sources/download_chandogya_mueller.sh` and
  `data-sources/parse_chandogya_mueller.py`; the build runs them when the
  parsed file is missing
- The only entry in the build's `translation_map`

**License Terms**:
- ✅ Public Domain translation (published 1879; translator died 1900)

---

### 9. Translation files in the DCS repository that are not used

The DCS repository (`data-sources/sanskrit/translations/`) carries English
translations beside its corpus. None of them is used, for these reasons:

| Files | Translator | Reason not used |
|---|---|---|
| `AU-`, `ChUp-`, `SvetUp-Olivelle.txt`, `GautDhS-Olivelle.txt` | Patrick Olivelle (Oxford 1996–2000) | No statement releasing the English translations was found: not in the files, the folder readme, or the DCS readmes (`dcs/data/readme.md` states CC BY 4.0 for `dcs/data` and its child directories; the `translations/` folder is outside it). Olivelle's own CC BY 4.0 / CC BY-SA 4.0 releases at the University of Texas cover his Sanskrit editions, not the translations. |
| `RV-Griffith.txt`, `VS-Griffith.txt`, `SB-Eggeling.txt`, `ApGS-`, `GobhGS-`, `HirGS-`, `SankhGS-Oldenberg.txt` | Griffith, Eggeling, Oldenberg (public-domain translations) | Digitised by sacred-texts.com, whose title pages (SBE 12, 26, 29) state "These files may be used for any non-commercial purpose" and whose terms of service apply the same restriction to all texts on its produced-texts list (`stbib.htm`), which includes all of these. The Rig Veda is taken from Wikisource instead (section 6); no transcribed alternative exists for the others. |
| `RV-Jamison, Brereton.csv` | Jamison & Brereton (Oxford 2014) | Copyright. |
| `AVŚ-Griffith.txt`, `Harshacarita-Cowell.txt`, `ParGS-Oldenberg.txt`, `Rgvidhana-Gonda.txt` and the Atharvaveda translations under `dcs/data/atharvaveda-shaunaka/` | various | Not mapped to any work in the build. |

---

### 10. Translations registered in `data-sources/translation_sources.py`

One entry per DCS work; see `data-sources/SOURCES.md` for alignment and
coverage. All are public-domain translations; Project Gutenberg texts are
included under the Gutenberg rule, Wikisource transcriptions under
Wikisource's CC BY-SA terms (already accepted for the Gītā text).

| DCS work | Translator (dates) | Source | Licence |
|---|---|---|---|
| Rāmāyaṇa | Manmatha Nath Dutt (1855–1912), 1891–94 | Project Gutenberg 57265, 57826, 60188, 62496 | Public Domain |
| Viṣṇupurāṇa | M. N. Dutt after H. H. Wilson, 1894–96 | Project Gutenberg 66208 | Public Domain |
| Saddharmapuṇḍarīkasūtra | Hendrik Kern (1833–1917), SBE 21, 1884 | English Wikisource | Public Domain |
| Atharvaveda (Śaunaka) | W. D. Whitney (1827–1894), ed. Lanman 1905 | English Wikisource | Public Domain |
| Kathāsaritsāgara | C. H. Tawney (1837–1922), 1880–84 | English Wikisource | Public Domain |
| Arthaśāstra | R. Shamasastry (1868–1944), 1915 | English Wikisource | Public Domain |
| Kāmasūtra | R. F. Burton and F. F. Arbuthnot, 1883 | English Wikisource | Public Domain |
| Suśrutasaṃhitā | K. L. Bhishagratna, 1907–16 | English Wikisource | Public Domain |
| Yogasūtra | Charles Johnston (1867–1931), 1912 | Project Gutenberg 2526 | Public Domain |
| Kumārasaṃbhava | R. T. H. Griffith (1826–1906), 1853 | Project Gutenberg 31968 | Public Domain |
| Gītagovinda | Edwin Arnold (1832–1904), 1875 | Project Gutenberg 25965 | Public Domain |
| Sarvadarśanasaṃgraha | E. B. Cowell and A. E. Gough, 1882 | Project Gutenberg 34125 | Public Domain |
| Hitopadeśa | Edwin Arnold, 1861 | Project Gutenberg 13268 | Public Domain |

The Rāmāyaṇa pairing uses the Sanskrit text of the vulgate on Sanskrit
Wikisource (रामायणम्, CC BY-SA) only to match sarga openings; none of that
text is shipped.

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
| Griffith Rig Veda Translation (Wikisource) | Public Domain | ✅ Yes | ❌ No | ❌ No |
| Ganguli Mahabharata Translation (Gutenberg) | Public Domain | ✅ Yes | ❌ No | ❌ No |
| Müller Chāndogya Translation (Wikisource) | Public Domain | ✅ Yes | ❌ No | ❌ No |
| Registry translations, section 10 (Gutenberg, Wikisource) | Public Domain | ✅ Yes | ❌ No | ❌ No |

**ClassicsViewer App License**: MIT OR Apache-2.0, at the user's option (open source, commercial use allowed)

**Compliance**: ✅ All share-alike requirements satisfied (app is open source, MIT OR Apache-2.0)

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
- **License**: per file. The Mahābhārata file (`mahabharata-devanagari.xml`)
  carries CC BY-SA 3.0 Unported in its TEI header, with no NonCommercial
  clause; other files may differ.
- **Reason**: not the licence but the edition: SARIT's Mahābhārata is the
  Kumbhakonam Southern recension (2,318 chapters), which matches neither the
  critical edition that DCS annotates nor the published concordance to
  Ganguli. See `MAHABHARATA_GANGULI_PROPOSAL.md` section 2.

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
- English (Griffith, Wikisource transcription): Public Domain

**Mahabharata**:
- Sanskrit: CC BY 4.0 (DCS - Oliver Hellwig)
- English (Ganguli, Project Gutenberg): Public Domain, 2,106 section segments attached per chapter

**Chāndogya Upaniṣad**:
- Sanskrit: CC BY 4.0 (DCS - Oliver Hellwig)
- English (Müller, Wikisource transcription): Public Domain, one segment per khaṇḍa

**Thirteen further DCS works** (section 10: Rāmāyaṇa in all seven kāṇḍas (four of them approximately, with a note in each segment), Viṣṇupurāṇa, Lotus Sūtra, Atharvaveda, Kathāsaritsāgara, Arthaśāstra, Kāmasūtra, Suśruta, Yogasūtra, Kumārasaṃbhava, Gītagovinda, Sarvadarśanasaṃgraha, Hitopadeśa):
- Sanskrit: CC BY 4.0 (DCS - Oliver Hellwig)
- English: public-domain translations from Project Gutenberg and Wikisource, one segment per chapter

**All other DCS works**:
- Sanskrit: CC BY 4.0 (DCS - Oliver Hellwig)
- English: machine-generated interlinear glosses only

**Combined** (Bhagavad Gita + Rig Veda, historical figures):
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
Source: English Wikisource, The Hymns of the Rigveda
License: Public Domain

Mahabharata (Sanskrit)
Source: Digital Corpus of Sanskrit (DCS)
Author: Oliver Hellwig
License: CC BY 4.0

Mahabharata (English)
Translator: Kisari Mohan Ganguli (1883-1896)
Source: Project Gutenberg ebooks 15474, 15475, 15476, 15477
License: Public Domain (Project Gutenberg License notice on the licence screen)
Chapter correspondences from the concordance in S. Brodbeck and
B. Black (eds), Gender and Narrative in the Mahabharata (2007)

Chandogya Upanishad (English)
Translator: F. Max Müller (Sacred Books of the East, vol. 1, 1879)
Source: English Wikisource
License: Public Domain

Further English translations (all Public Domain)
Ramayana: Manmatha Nath Dutt (1891-94), Project Gutenberg 57265, 57826, 60188, 62496
Vishnu Purana: M. N. Dutt after H. H. Wilson, Project Gutenberg 66208
Saddharma-pundarika: Hendrik Kern (1884), English Wikisource
Atharva-Veda: W. D. Whitney (1905), English Wikisource
Katha Sarit Sagara: C. H. Tawney (1880-84), English Wikisource
Arthashastra: R. Shamasastry (1915), English Wikisource
Kama Sutra: R. F. Burton and F. F. Arbuthnot (1883), English Wikisource
Sushruta Samhita: K. L. Bhishagratna (1907-16), English Wikisource
Yoga Sutras: Charles Johnston (1912), Project Gutenberg 2526
Kumarasambhava: R. T. H. Griffith (1853), Project Gutenberg 31968
Gita Govinda: Edwin Arnold (1875), Project Gutenberg 25965
Sarva-darsana-samgraha: E. B. Cowell and A. E. Gough (1882), Project Gutenberg 34125
Hitopadesa: Edwin Arnold (1861, abridged), Project Gutenberg 13268
All Project Gutenberg texts: see the Project Gutenberg section of the
licence screen for the licence notice and the full list of ebooks used

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
