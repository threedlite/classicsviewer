# Sanskrit for ClassicsViewer

**Status**: ✅ Production Ready
**Texts**: 7 major texts (14,672 verses total)
**Lexicon Coverage**: 88.0% on classical Sanskrit
**License**: CC BY 4.0, CC BY-SA 4.0, Public Domain (all commercial-use compatible)

## Overview

This implementation provides complete Sanskrit support for ClassicsViewer with:
1. **Sanskrit Texts Database** - 7 major texts with English translations
   - Bhagavad Gita (700 verses)
   - Rig Veda (10,551 verses)
   - Atharvaveda (518 verses)
   - Yajur Veda (2,516 verses)
   - Aitareya Upanishad (13 verses)
   - Chandogya Upanishad (151 verses)
   - Svetasvatara Upanishad (223 verses)
2. **DCS Lexicon** - Dictionary and morphology for word lookups

---

## Part 1: Sanskrit Texts Database

### Quick Start

```bash
# Setup
cd sanskrit
source venv/bin/activate
pip install -r requirements.txt

# Create complete database (one command)
python3 create_sanskrit_database.py

# Output: sanskrit_texts.db.zip (6.69 MB)
```

### What You Get

**7 Major Texts:**
- **Bhagavad Gita**: 700 verses, 2 English translations (Arnold + Besant)
- **Rig Veda**: 10,551 verses, Griffith translation
- **Atharvaveda**: 518 verses, Whitney translation
- **Yajur Veda (Vājasaneyisaṃhitā)**: 2,516 verses, Griffith translation
- **Aitareya Upanishad**: 13 verses, Olivelle translation
- **Chandogya Upanishad**: 151 verses, Olivelle translation
- **Svetasvatara Upanishad**: 223 verses, Olivelle translation

**Combined Statistics:**
- **14,672 total verses**
- **270,059 words** (53,540 unique)
- **11,227 translations**
- **7 authors, 7 works, 79 books**
- **Database**: 25.95 MB uncompressed, 6.69 MB compressed

### Implementation Details

The main script `create_sanskrit_database.py` uses:
1. **Direct JSON loading** for Bhagavad Gita (from Wikisource)
2. **DCS pada-and-analysis.dat** for Rig Veda (special TSV format)
3. **Generic DCS CoNLL-U parser** for 5 other texts (Atharvaveda, Yajur Veda, 3 Upanishads)

The CoNLL-U parser automatically handles:
- 2-part citations (chapter only): Svetasvatara, Yajur Veda
- 3-part citations (book.chapter.verse): Aitareya, Chandogya, Atharvaveda
- Sequential verse numbering within chapters
- IAST to Devanagari conversion

---

## Part 2: DCS Sanskrit Lexicon

### Quick Start

```bash
# Complete lexicon workflow (4 minutes total)
python3 extract_dcs_lexicon.py    # Extract + enhance (4 min)
python3 create_dcs_lexicon.py     # Package ZIP (5 sec)
python3 test_dcs_coverage.py      # Test coverage (2 sec)

# Output: dcs_sanskrit_lexicon.zip (34.5 MB)
```

### What You Get

- **179,806** dictionary lemmas with definitions
- **4.7 million** morphology forms (word → lemma mappings)
- **3,699** sandhi-split compound forms (automatic enhancement)
- **88.0% coverage** on classical Sanskrit texts
- **Ready for app import** - one ZIP file

### Coverage Results

| Category | Words | Percentage |
|----------|-------|------------|
| **Total BG vocabulary** | 4,055 | 100% |
| Found in dictionary | 658 | 16.2% |
| Found in morphology | 3,197 | 78.8% |
| **Total found** | **3,569** | **88.0%** |
| Missing | 486 | 12.0% |

**Improvement from sandhi splitting**: 40% → 88% (+48 percentage points)

---

## Data Sources

### Texts

1. **Bhagavad Gita Sanskrit** - Sanskrit Wikisource (CC BY-SA 4.0)
2. **Bhagavad Gita English (Arnold)** - Public Domain (1885)
3. **Bhagavad Gita English (Besant)** - Public Domain (1922)
4. **Rig Veda Sanskrit** - DCS pada-and-analysis.dat (CC BY 4.0, Oliver Hellwig)
5. **Rig Veda English (Griffith)** - Public Domain (1896)
6. **Atharvaveda Sanskrit** - DCS CoNLL-U files (CC BY 4.0)
7. **Atharvaveda English (Whitney)** - Public Domain (1905)
8. **Yajur Veda Sanskrit** - DCS CoNLL-U files (CC BY 4.0)
9. **Yajur Veda English (Griffith)** - Public Domain (1899)
10. **Aitareya Upanishad Sanskrit** - DCS CoNLL-U files (CC BY 4.0)
11. **Aitareya Upanishad English (Olivelle)** - Used with permission
12. **Chandogya Upanishad Sanskrit** - DCS CoNLL-U files (CC BY 4.0)
13. **Chandogya Upanishad English (Olivelle)** - Used with permission
14. **Svetasvatara Upanishad Sanskrit** - DCS CoNLL-U files (CC BY 4.0)
15. **Svetasvatara Upanishad English (Olivelle)** - Used with permission

### Lexicon

**Digital Corpus of Sanskrit (DCS)** by Oliver Hellwig
- **Repository**: https://github.com/OliverHellwig/sanskrit
- **Website**: http://www.sanskrit-linguistics.org/dcs/
- **License**: Creative Commons Attribution 4.0 International
- **Corpus**: 5.5 million words from 268 classical texts

---

## Available Texts in DCS

The DCS corpus contains **268 Sanskrit texts**. However, **only 16 texts have English translations** in the DCS repository.

### Texts with DCS Translations

**Currently Implemented (7 texts):**
- ✅ **Bhagavad Gita** (700 verses) - Arnold + Besant translations
- ✅ **Rig Veda** (10,551 verses) - Griffith translation
- ✅ **Atharvaveda** (Śaunaka) (518 verses) - Whitney translation
- ✅ **Vājasaneyisaṃhitā** (Yajur Veda) (2,516 verses) - Griffith translation
- ✅ **Aitareyopaniṣad** (13 verses) - Olivelle translation
- ✅ **Chāndogyopaniṣad** (151 verses) - Olivelle translation
- ✅ **Śvetāśvataropaniṣad** (223 verses) - Olivelle translation

**Available to Implement** (9 more texts):
- **Śatapathabrāhmaṇa** - Eggeling translation (very large)
- **Harṣacarita** - Cowell translation
- 5 Gṛhyasūtras (ritual manuals) - Oldenberg translations
- Gautamadharmasūtra - Olivelle translation
- Ṛgvidhāna - Gonda translation

See `DCS_TRANSLATIONS_AVAILABLE.md` and `EXPANSION_PLAN.md` for complete details.

### Texts WITHOUT DCS Translations (Would Need External Sources)

These major texts are in DCS but lack English translations in the repository:
- **Mahābhārata** (1,995 files) - Would need external translation
- **Rāmāyaṇa** (606 files) - Would need external translation
- **Yogasūtra** (4 files) - Would need external translation
- **Hitopadeśa** (5 files) - Would need external translation
- **Meghadūta** (2 files) - Would need external translation
- **Manusmṛti** - Would need external translation
- **Nāṭyaśāstra** - Would need external translation
- 250+ other texts

See `DCS_TEXTS_CATALOG.md` for all 268 available texts.

---

## License Compliance

All sources are commercial-use compatible:

### DCS Data: CC BY 4.0
**Attribution** (included in app license screen):
```
Digital Corpus of Sanskrit (DCS)
Author: Oliver Hellwig
License: CC BY 4.0
Source: http://www.sanskrit-linguistics.org/dcs/
```

### Bhagavad Gita Sanskrit: CC BY-SA 4.0
```
Sanskrit Wikisource
License: CC BY-SA 4.0
Source: https://sa.wikisource.org/wiki/भगवद्गीता
```

### Translations: Public Domain
- Edwin Arnold translation (1885)
- Annie Besant translation (1922)
- Ralph T.H. Griffith translation (1896)

### Sanskrit Parser: MIT License
Used for sandhi splitting enhancement (build-time only).

See `LICENSE_COMPLIANCE.md` for complete details.

---

## Dependencies

```bash
pip install indic-transliteration sanskrit_parser
```

Or use the venv:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Documentation

- **README.md** - This file (overview)
- **WORKFLOW.md** - Step-by-step workflow
- **EXPANSION_PLAN.md** - Recommended implementation plan for DCS-translated texts
- **DCS_LEXICON_DOCUMENTATION.md** - Complete lexicon technical docs
- **DCS_TEXTS_CATALOG.md** - All 268 available texts in DCS (marked with translation status)
- **DCS_TRANSLATIONS_AVAILABLE.md** - Detailed analysis of 16 texts with DCS translations
- **LICENSE_COMPLIANCE.md** - License details and attribution

---

## File Structure

```
sanskrit/
├── create_sanskrit_database.py     # Main script (BG + RV)
├── create_sanskrit_texts.py        # Bhagavad Gita only
├── create_rigveda_texts.py         # Rig Veda only
├── extract_dcs_lexicon.py          # Extract DCS lexicon
├── create_dcs_lexicon.py           # Package lexicon ZIP
├── test_dcs_coverage.py            # Test lexicon coverage
├── normalization_rules_sanskrit.csv
├── requirements.txt
├── venv/                           # Python virtual environment
├── data-sources/                   # Downloaded source data
│   ├── bhagavad_gita_sanskrit.json
│   ├── bhagavad_gita_english.json
│   ├── bhagavad_gita_besant.json
│   └── SOURCES.md
└── outputs/
    ├── sanskrit_texts.db           # Combined texts database
    ├── sanskrit_texts.db.zip       # Compressed (4.67 MB)
    ├── dcs_sanskrit_lexicon.zip    # Lexicon (34.5 MB)
    └── dcs_extraction_stats.json
```

---

**Last Updated**: October 6, 2025
**Version**: 3.0 (7 Major Texts + DCS Lexicon)
**Texts**: Bhagavad Gita, 3 Vedas (Rig/Atharva/Yajur), 3 Upanishads
**Lexicon Coverage**: 88.0%
**Total Verses**: 14,672
**Database Size**: 25.95 MB (6.69 MB compressed)
