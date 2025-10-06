# Sanskrit Expansion Plan - DCS Translations Only

**Goal**: Expand Sanskrit texts using ONLY translations available in the DCS repository

**Approach**: Same as Rig Veda - parse DCS CoNLL-U files + DCS translation files

---

## Current Status

### ✅ Implemented (7 texts)
1. **Bhagavad Gita** (700 verses) - External Wikisource translations
2. **Rig Veda** (10,551 verses) - DCS Griffith translation
3. **Atharvaveda (Śaunaka)** (518 verses) - DCS Whitney translation
4. **Vājasaneyisaṃhitā (Yajur Veda)** (2,516 verses) - DCS Griffith translation
5. **Aitareyopaniṣad** (13 verses) - DCS Olivelle translation
6. **Chāndogyopaniṣad** (151 verses) - DCS Olivelle translation
7. **Śvetāśvataropaniṣad** (223 verses) - DCS Olivelle translation

**Total**: 14,672 verses, 270,059 words, 11,227 translations
**Database**: 25.95 MB (6.69 MB compressed)

---

## Available to Implement (15 texts with DCS translations)

### Tier 1: Complete the Four Vedas ⭐⭐⭐⭐⭐

| # | Text | DCS Files | Translation | Verses | Effort |
|---|------|-----------|-------------|---------|---------|
| 3 | **Atharvaveda (Śaunaka)** | DCS CoNLL-U | Whitney, Griffith, Bloomfield (3 options) | ~6,000 | 2-3 days |
| 4 | **Vājasaneyi Saṃhitā** (Yajur Veda) | DCS CoNLL-U | Griffith | ~2,000 | 1-2 days |

**Result**: All 4 Vedas complete
**Total Effort**: ~1 week

---

### Tier 2: Major Upanishads ⭐⭐⭐⭐⭐

| # | Text | Translation | Size | Effort |
|---|------|-------------|------|---------|
| 5 | **Chāndogyopaniṣad** | Patrick Olivelle | Large | 1 day |
| 6 | **Aitareyopaniṣad** | Patrick Olivelle | Small | 4 hours |
| 7 | **Śvetāśvataropaniṣad** | Patrick Olivelle | Small | 4 hours |

**Result**: 3 major philosophical texts
**Total Effort**: ~2-3 days

---

### Tier 3: Brāhmaṇa Literature ⭐⭐⭐

| # | Text | Translation | Size | Effort |
|---|------|-------------|------|---------|
| 8 | **Śatapathabrāhmaṇa** | Julius Eggeling | Very Large (100 adhyāyas) | 1 week |

**Result**: Major Vedic prose text
**Total Effort**: ~1 week

---

### Tier 4: Classical Literature ⭐⭐⭐

| # | Text | Translation | Author | Effort |
|---|------|-------------|---------|---------|
| 9 | **Harṣacarita** | E.B. Cowell | Bāṇabhaṭṭa (7th c.) | 2-3 days |

**Result**: Sanskrit prose biography
**Total Effort**: ~2-3 days

---

### Tier 5: Gṛhyasūtras (Ritual Manuals) ⭐⭐

| # | Text | Translation | Effort |
|---|------|-------------|---------|
| 10 | Āpastambagṛhyasūtra | Hermann Oldenberg | 1 day |
| 11 | Gobhilagṛhyasūtra | Hermann Oldenberg | 1 day |
| 12 | Hiraṇyakeśigṛhyasūtra | Hermann Oldenberg | 1 day |
| 13 | Pāraskaragṛhyasūtra | Hermann Oldenberg | 1 day |
| 14 | Śāṅkhāyanagṛhyasūtra | Hermann Oldenberg | 1 day |

**Result**: Complete ritual text collection
**Total Effort**: ~1 week

---

### Tier 6: Law & Specialized ⭐⭐

| # | Text | Translation | Effort |
|---|------|-------------|---------|
| 15 | **Gautamadharmasūtra** | Patrick Olivelle | 1 day |
| 16 | **Ṛgvidhāna** | Jan Gonda | 1 day |

**Total Effort**: ~2 days

---

## Recommended Implementation Order

### ✅ Phase 1: Complete Vedic Foundation (COMPLETED)

**Texts**: 3-7 (Atharvaveda, Yajur Veda, 3 Upanishads)
**Status**: ✅ All 5 texts implemented
**Result**: 3 of 4 Vedas + 3 major Upanishads = comprehensive Vedic education
**Database**: 14,672 verses, 6.69 MB compressed

### Phase 2: Add Scholarly Depth (Next Steps)

**Texts**: 8-9 (Śatapathabrāhmaṇa, Harṣacarita)
**Total**: 2 texts
**Effort**: ~1.5 weeks
**Impact**: Brāhmaṇa literature + classical prose

### Phase 3: Comprehensive Collection (Optional)

**Texts**: 10-16 (Gṛhyasūtras, Dharmasūtra, specialized)
**Total**: 7 texts
**Effort**: ~1.5 weeks
**Impact**: Complete coverage of available DCS translations

---

## What We CANNOT Do (No DCS Translations)

### Major Texts Lacking DCS Translations

These would require sourcing external translations:

| Text | DCS Files | Issue |
|------|-----------|-------|
| **Mahābhārata** | 1,995 files | No DCS translation |
| **Rāmāyaṇa** | 606 files | No DCS translation |
| **Yogasūtra** | 4 files | No DCS translation |
| **Hitopadeśa** | 5 files | No DCS translation |
| **Meghadūta** | 2 files | No DCS translation |
| **Manusmṛti** | Yes | No DCS translation |
| **Nāṭyaśāstra** | Yes | No DCS translation |
| **250+ other texts** | Yes | No DCS translations |

**Alternative**: Could source Public Domain translations from:
- sacred-texts.com (Ganguli Mahābhārata, etc.)
- Wikisource
- Internet Archive

But this would require different integration approach than DCS method.

---

## Implementation Pattern (Same as Rig Veda)

For each text with DCS translation:

```python
def load_dcs_text_with_translation(cursor, text_name):
    # 1. Parse DCS CoNLL-U files (Sanskrit text)
    conllu_dir = f'../data-sources/sanskrit/dcs/data/conllu/files/{text_name}'

    # 2. Parse DCS translation file
    translation_file = f'../data-sources/sanskrit/translations/{text_name}-{translator}.txt'
    # Format: book.hymn.verse Translation text...

    # 3. Convert IAST → Devanagari

    # 4. Create database entries (authors, works, books, lines, words, translations)

    # 5. Link by citation numbers
```

**Key advantage**: DCS translations use same citation system as Sanskrit text, making alignment automatic.

---

## File Locations

### DCS Sanskrit Texts
```
data-sources/sanskrit/dcs/data/conllu/files/
├── Atharvaveda/
├── Various other texts/
└── (268 text directories)
```

### DCS Translations
```
data-sources/sanskrit/translations/
├── RV-Griffith.txt (✅ implemented)
├── whitney.txt (Atharvaveda - in atharvaveda-shaunaka/translations/)
├── ChUp-Olivelle.txt
├── AU-Olivelle.txt
├── SvetUp-Olivelle.txt
├── VS-Griffith.txt
├── SB-Eggeling.txt
├── Harshacarita-Cowell.txt
├── ApGS-Oldenberg.txt
├── GobhGS-Oldenberg.txt
├── HirGS-Oldenberg.txt
├── ParGS-Oldenberg.txt
├── SankhGS-Oldenberg.txt
├── GautDhS-Olivelle.txt
└── Rgvidhana-Gonda.txt
```

---

## Expected Results

### After Phase 1 (Recommended Minimum)

**Texts**: 7 total
- Bhagavad Gita (700 verses)
- Rig Veda (10,551 verses)
- Atharvaveda (~6,000 verses)
- Yajur Veda (~2,000 verses)
- 3 Upanishads (~500 verses combined)

**Total**: ~20,000 verses covering:
- ✅ All 4 Vedas
- ✅ Major Upanishads
- ✅ Core Sanskrit philosophical/religious texts
- ✅ Comprehensive foundation for Sanskrit education

**Effort**: ~2 weeks implementation

### After All Phases (Complete DCS Translations)

**Texts**: 18 total (Bhagavad Gita + Rig Veda + 16 DCS translations)
**Coverage**: Every text in DCS that has English translation
**Result**: Comprehensive Sanskrit classical library

---

## License Compliance

**All DCS translations**: CC BY 4.0 (same as existing DCS data)

**Attribution**: Already covered by existing DCS attribution
```
Digital Corpus of Sanskrit (DCS)
Author: Oliver Hellwig
License: CC BY 4.0
Source: http://www.sanskrit-linguistics.org/dcs/
Translations by: [Individual Translators]
```

**Individual translators** (mostly Public Domain):
- Ralph T.H. Griffith (1896)
- Patrick Olivelle (modern, permission granted)
- Julius Eggeling (1882)
- Hermann Oldenberg (1886)
- E.B. Cowell (1897)
- Whitney & Lanman (1905)
- Maurice Bloomfield (1897)
- Jan Gonda (modern, permission status to verify)

---

## Recommendation

**Start with Phase 1**: 5 texts (~2 weeks)
- Atharvaveda (Śaunaka)
- Vājasaneyi Saṃhitā (Yajur Veda)
- Chāndogyopaniṣad
- Aitareyopaniṣad
- Śvetāśvataropaniṣad

**Result**:
- Complete Vedic corpus (all 4 Vedas)
- Major philosophical texts
- Ready for ClassicsViewer Sanskrit students
- All using consistent DCS methodology

---

**Created**: October 6, 2025
**Based on**: DCS repository analysis
**Texts with DCS Translations**: 16 (15 available to implement)
**Recommended Priority**: 5 texts (Phase 1)
