# DCS Sanskrit Texts Catalog

**Digital Corpus of Sanskrit (DCS)** by Oliver Hellwig
**Total Texts Available**: 268
**Texts with English Translations in DCS**: 16 (6%)
**License**: CC BY 4.0 (commercial use allowed with attribution)
**Repository**: https://github.com/OliverHellwig/sanskrit

---

## IMPORTANT: Translation Availability

**Of 268 texts in DCS, only 16 have English translations in the repository.**

This catalog lists all 268 texts by priority, but **clearly marks which have DCS translations** (✅) versus which would require external translation sources (⚠️).

**For texts ready to implement** (with DCS translations), see: `DCS_TRANSLATIONS_AVAILABLE.md`

---

## Currently Implemented

### ✅ Bhagavad Gita
- **Source**: Sanskrit Wikisource (separate from DCS)
- **Verses**: 700 across 18 chapters
- **Translations**: Edwin Arnold (prose), Annie Besant (verse-by-verse)
- **DCS Translation**: ⚠️ NO (using external Wikisource translations)
- **Status**: ✅ Implemented in `create_sanskrit_database.py`

### ✅ Rig Veda
- **Source**: DCS pada-and-analysis.dat
- **Verses**: 10,551 across 10 mandalas (complete)
- **Translation**: Ralph T.H. Griffith (94.6% coverage)
- **DCS Translation**: ✅ YES (translations/RV-Griffith.txt)
- **Status**: ✅ Implemented in `create_sanskrit_database.py`

---

## Priority 1: Major Epics (Highly Recommended)

### ⚠️ Mahābhārata
- **Files**: 1,995 CoNLL-U files
- **Size**: ~200,000 verses (18 parvas/books)
- **Significance**: India's longest epic, includes Bhagavad Gita
- **Content**: Philosophy, ethics, mythology, history
- **Educational Value**: ⭐⭐⭐⭐⭐
- **DCS Translation**: ⚠️ **NO** - Would need external translation (Kisari Mohan Ganguli)
- **Implementation Complexity**: High (requires external translation integration)
- **Recommendation**: **HIGH** - Essential classical text (but needs external work)

### ⚠️ Rāmāyaṇa
- **Files**: 606 CoNLL-U files
- **Size**: ~24,000 verses (7 kandas/books)
- **Significance**: Second major Sanskrit epic
- **Content**: Story of Rama, dharma, devotion
- **Educational Value**: ⭐⭐⭐⭐⭐
- **DCS Translation**: ⚠️ **NO** - Would need external translation
- **Implementation Complexity**: High (requires external translation integration)
- **Recommendation**: **HIGH** - Completes the two great epics (but needs external work)

---

## Priority 2: Vedic Literature

### ⚠️ Atharvaveda (Paippalāda)
- **Files**: Available in DCS
- **Significance**: Fourth Veda, spells and incantations
- **Educational Value**: ⭐⭐⭐⭐
- **DCS Translation**: ⚠️ **NO** - Paippalāda recension lacks translation
- **Recommendation**: **LOW** - Specialized recension, no translation

### ✅ Atharvaveda (Śaunaka)
- **Files**: Available in DCS
- **Significance**: Fourth Veda, most complete recension
- **Educational Value**: ⭐⭐⭐⭐⭐
- **DCS Translation**: ✅ **YES** - 3 translations (Whitney, Griffith, Bloomfield)
- **Verses**: ~6,000
- **Recommendation**: **HIGHEST** - Completes the four Vedas, ready to implement

### Aitareya-Āraṇyaka
- **Significance**: Forest treatise associated with Rig Veda
- **Educational Value**: ⭐⭐⭐
- **Recommendation**: **LOW** - Specialized scholarly interest

### Aitareyabrāhmaṇa
- **Significance**: Ritual text of Rig Veda
- **Educational Value**: ⭐⭐⭐
- **Recommendation**: **LOW** - Specialized

---

## Priority 3: Upanishads & Philosophy

### ✅ Chāndogyopaniṣad
- **Significance**: One of the oldest and largest Upanishads
- **Educational Value**: ⭐⭐⭐⭐⭐
- **DCS Translation**: ✅ **YES** - Patrick Olivelle translation
- **Recommendation**: **HIGHEST** - Major philosophical text, ready to implement

### ✅ Aitareyopaniṣad
- **Significance**: Major Upanishad from Rig Veda
- **Educational Value**: ⭐⭐⭐⭐
- **DCS Translation**: ✅ **YES** - Patrick Olivelle translation
- **Recommendation**: **HIGH** - Important philosophical text, ready to implement

### ✅ Śvetāśvataropaniṣad
- **Significance**: Important theistic Upanishad
- **Educational Value**: ⭐⭐⭐⭐
- **DCS Translation**: ✅ **YES** - Patrick Olivelle translation
- **Recommendation**: **HIGH** - Ready to implement

### ⚠️ Kauṣītakyupaniṣad
- **Significance**: Principal Upanishad
- **Educational Value**: ⭐⭐⭐⭐
- **DCS Translation**: ⚠️ **NO** - Would need external translation
- **Recommendation**: **MEDIUM** - Needs external work

### ⚠️ Yogasūtra
- **Files**: 4 CoNLL-U files
- **Significance**: Patanjali's foundational text on yoga philosophy
- **Size**: 195 sutras in 4 chapters
- **Educational Value**: ⭐⭐⭐⭐⭐
- **DCS Translation**: ⚠️ **NO** - Would need external translation
- **Implementation Complexity**: Low if translation found
- **Recommendation**: **HIGH** - Extremely influential (but needs external translation)

### Yogasūtrabhāṣya
- **Significance**: Vyasa's commentary on Yoga Sutras
- **Educational Value**: ⭐⭐⭐⭐
- **Recommendation**: **MEDIUM** - Pairs with Yogasūtra

---

## Priority 4: Classical Poetry & Drama

### ⚠️ Meghadūta
- **Files**: 2 CoNLL-U files
- **Author**: Kālidāsa
- **Significance**: Famous lyric poem "Cloud Messenger"
- **Size**: ~120 verses
- **Educational Value**: ⭐⭐⭐⭐
- **DCS Translation**: ⚠️ **NO** - Would need external translation
- **Implementation Complexity**: Low if translation found
- **Recommendation**: **MEDIUM** - Masterpiece but needs external translation

### ✅ Harṣacarita
- **Files**: Available in DCS
- **Author**: Bāṇabhaṭṭa (7th century CE)
- **Significance**: Sanskrit prose biography of King Harsha
- **Educational Value**: ⭐⭐⭐⭐
- **DCS Translation**: ✅ **YES** - E.B. Cowell translation
- **Recommendation**: **MEDIUM** - Important classical literature, ready to implement

### Amaruśataka
- **Author**: Amaru
- **Significance**: 100 love poems
- **Educational Value**: ⭐⭐⭐
- **Recommendation**: **LOW** - Specialized literary interest

### Bhallaṭaśataka
- **Author**: Bhallaṭa
- **Significance**: Collection of 100 verses
- **Educational Value**: ⭐⭐⭐
- **Recommendation**: **LOW**

---

## Priority 5: Fables & Moral Literature

### ⚠️ Hitopadeśa
- **Files**: 5 CoNLL-U files
- **Significance**: Collection of moral fables (similar to Panchatantra)
- **Educational Value**: ⭐⭐⭐⭐
- **DCS Translation**: ⚠️ **NO** - Would need external translation
- **Implementation Complexity**: Low if translation found
- **Recommendation**: **MEDIUM** - Popular for learning (but needs external translation)

### Vetālapañcaviṃśatikā
- **Significance**: 25 vampire tales (frame story)
- **Educational Value**: ⭐⭐⭐
- **Recommendation**: **LOW** - Entertaining but not essential

---

## Priority 6: Law & Ethics

### ⚠️ Manusmṛti
- **Files**: Available in DCS
- **Significance**: Ancient law code, Laws of Manu
- **Educational Value**: ⭐⭐⭐⭐
- **DCS Translation**: ⚠️ **NO** - Would need external translation
- **Implementation Complexity**: Medium if translation found
- **Recommendation**: **MEDIUM** - Important historical document (needs external translation)
- **Note**: Controversial content regarding caste/gender - important historical document

### ✅ Gautamadharmasūtra
- **Significance**: Ancient law code
- **Educational Value**: ⭐⭐⭐
- **DCS Translation**: ✅ **YES** - Patrick Olivelle translation
- **Recommendation**: **LOW-MEDIUM** - Historical/legal interest, ready to implement

### Arthaśāstra
- **Author**: Kauṭilya/Chanakya
- **Significance**: Treatise on statecraft and economics
- **Educational Value**: ⭐⭐⭐⭐
- **Recommendation**: **MEDIUM** - Influential political text

---

## Priority 7: Purāṇas

### Bhāgavatapurāṇa
- **Files**: Available in DCS
- **Significance**: Major Purāṇa, stories of Vishnu/Krishna
- **Size**: Very large (12 books)
- **Educational Value**: ⭐⭐⭐⭐
- **Implementation Complexity**: High (very large)
- **Recommendation**: **MEDIUM** - Important devotional text

### Agnipurāṇa
- **Significance**: Encyclopedic Purāṇa
- **Educational Value**: ⭐⭐⭐
- **Recommendation**: **LOW** - Very large, encyclopedic nature

---

## Priority 8: Technical & Scientific

### ⚠️ Nāṭyaśāstra
- **Files**: Available in DCS
- **Significance**: Ancient treatise on performing arts, drama, dance
- **Educational Value**: ⭐⭐⭐⭐
- **DCS Translation**: ⚠️ **NO** - Would need external translation
- **Implementation Complexity**: Medium-High (large text + needs translation)
- **Recommendation**: **MEDIUM** - Important for scholars (but needs external translation)

### Aṣṭādhyāyī
- **Author**: Pāṇini
- **Significance**: Foundational Sanskrit grammar
- **Educational Value**: ⭐⭐⭐⭐
- **Implementation Complexity**: High (technical)
- **Recommendation**: **LOW** - Highly specialized, technical

### Haṭhayogapradīpikā
- **Significance**: Medieval text on Hatha Yoga
- **Educational Value**: ⭐⭐⭐
- **Recommendation**: **LOW** - Specialized yoga text

### Amarakośa
- **Significance**: Sanskrit thesaurus/dictionary
- **Educational Value**: ⭐⭐⭐
- **Recommendation**: **LOW** - Reference work, not narrative

---

## Priority 9: Medical Texts (Āyurveda)

### Aṣṭāṅgahṛdayasaṃhitā
- **Significance**: Ayurvedic medical text
- **Educational Value**: ⭐⭐⭐
- **Recommendation**: **LOW** - Specialized medical interest

### Aṣṭāṅgasaṃgraha
- **Significance**: Ayurvedic compendium
- **Educational Value**: ⭐⭐⭐
- **Recommendation**: **LOW**

---

## Priority 10: Buddhist Texts

### Aṣṭasāhasrikā
- **Full Name**: Aṣṭasāhasrikā Prajñāpāramitā
- **Significance**: Important Mahayana Buddhist sutra
- **Educational Value**: ⭐⭐⭐⭐
- **Recommendation**: **MEDIUM** - Major Buddhist philosophical text

### Bodhicaryāvatāra
- **Author**: Śāntideva
- **Significance**: Guide to Bodhisattva path
- **Educational Value**: ⭐⭐⭐⭐
- **Recommendation**: **MEDIUM** - Important Mahayana text

### Abhidharmakośa
- **Author**: Vasubandhu
- **Significance**: Buddhist philosophical encyclopedia
- **Educational Value**: ⭐⭐⭐⭐
- **Recommendation**: **MEDIUM** - Important for Buddhist studies

---

## Implementation Recommendations

### Phase 1: Complete the Epics (ESSENTIAL)
1. **Mahābhārata** (1,995 files)
2. **Rāmāyaṇa** (606 files)

**Impact**: Two most important Sanskrit texts
**Effort**: Medium-High (large but well-structured)
**Priority**: ⭐⭐⭐⭐⭐

### Phase 2: Add Philosophy & Poetry (HIGH VALUE)
3. **Yogasūtra** (4 files) - Quick win, highly influential
4. **Meghadūta** (2 files) - Quick win, beautiful poetry
5. **Principal Upanishads** - Add major Upanishads

**Impact**: Core philosophical and literary works
**Effort**: Low-Medium
**Priority**: ⭐⭐⭐⭐

### Phase 3: Expand Vedic Corpus (SCHOLARLY)
6. **Atharvaveda** (both recensions)
7. **Vedic Brahmanas** (ritual texts)

**Impact**: Complete Vedic literature
**Effort**: Medium
**Priority**: ⭐⭐⭐

### Phase 4: Add Cultural/Educational Texts (BREADTH)
8. **Hitopadeśa** - Fables for Sanskrit learners
9. **Manusmṛti** - Historical/legal importance
10. **Arthaśāstra** - Political philosophy

**Impact**: Broaden cultural coverage
**Effort**: Low-Medium
**Priority**: ⭐⭐⭐

### Phase 5: Specialized Collections (OPTIONAL)
11. **Buddhist texts** (for Buddhist studies)
12. **Purāṇas** (devotional literature)
13. **Technical texts** (grammar, medicine, arts)

**Impact**: Serve specialized audiences
**Effort**: Variable
**Priority**: ⭐⭐

---

## Implementation Complexity Estimates

### Easy Additions (< 1 day)
- **Yogasūtra** (4 files) - ~2 hours
- **Meghadūta** (2 files) - ~1 hour
- **Hitopadeśa** (5 files) - ~2 hours

### Medium Additions (1-3 days)
- **Upanishads collection** - ~2 days (multiple small texts)
- **Atharvaveda** - ~2 days
- **Manusmṛti** - ~1 day
- **Buddhist short texts** - ~1-2 days each

### Large Additions (1-2 weeks)
- **Rāmāyaṇa** (606 files) - ~1 week
- **Mahābhārata** (1,995 files) - ~2 weeks
- **Bhāgavatapurāṇa** - ~1 week

---

## Complete DCS Text List (268 texts)

The DCS corpus contains texts in these categories:

**Vedic Literature**: ~15 texts
- Rig Veda, Atharvaveda, Brahmanas, Aranyakas, Upanishads

**Epics & Purāṇas**: ~20 texts
- Mahābhārata, Rāmāyaṇa, 18 major Purāṇas

**Philosophy**: ~30 texts
- Yogasūtra, Buddhist sutras, Vedānta texts, Sāṃkhya

**Poetry & Drama**: ~40 texts
- Kālidāsa works, Bhaṭṭikāvya, various stotras

**Grammar & Linguistics**: ~20 texts
- Pāṇini, Patañjali, commentaries

**Law & Ethics**: ~10 texts
- Dharmasūtras, Dharmaśāstras

**Medicine**: ~25 texts
- Ayurvedic treatises, commentaries

**Arts & Sciences**: ~30 texts
- Nāṭyaśāstra, music, architecture, astronomy

**Jain & Buddhist**: ~40 texts
- Sutras, philosophical treatises

**Miscellaneous**: ~38 texts
- Dictionaries, encyclopedias, technical works

---

## Translation Availability

**Challenge**: Most DCS texts lack English translations in the corpus.

**Current Translations Available:**
- ✅ Rig Veda - Griffith translation
- ✅ Bhagavad Gita - Arnold & Besant translations

**Potential Sources for Future Translations:**
- Sacred-texts.com (Public Domain translations)
- Internet Archive (old translations)
- Wikisource (various translators)
- Academic open-access publications

**Recommendation**: Start with texts that have readily available public domain English translations.

---

## Technical Considerations

### DCS File Format
All DCS texts are in **CoNLL-U format** with:
- Word-by-word morphological analysis
- Lemma IDs linking to DCS dictionary
- Dependency parsing annotations
- Reference IDs for cross-referencing

### Integration Pattern
For each new text, the implementation would:
1. Parse CoNLL-U files to extract text and structure
2. Convert IAST → Devanagari
3. Create author/work/books structure
4. Insert text lines and words
5. Add translations if available
6. Link morphology to existing DCS lexicon

### Script Template
Create a generic `load_dcs_text()` function that can handle any DCS text:
```python
def load_dcs_text(cursor, text_name, author_name, translation_source=None):
    # Parse CoNLL-U files
    # Create database entries
    # Add translations if available
```

---

## License & Attribution

All DCS texts require attribution:

```
Digital Corpus of Sanskrit (DCS)
Author: Oliver Hellwig
License: CC BY 4.0
Source: http://www.sanskrit-linguistics.org/dcs/
```

Individual translations have their own licenses (mostly Public Domain for pre-1928 works).

---

## Recommended Next Steps

1. **Immediate** (Next sprint):
   - Implement Mahābhārata (high value, medium effort)
   - Implement Yogasūtra (high value, low effort)

2. **Short-term** (Next month):
   - Implement Rāmāyaṇa
   - Add 2-3 principal Upanishads
   - Add Meghadūta

3. **Long-term** (Future releases):
   - Expand Vedic corpus (Atharvaveda)
   - Add Buddhist texts for specialized users
   - Add Purāṇas based on user demand

---

**Last Updated**: October 6, 2025
**DCS Repository**: https://github.com/OliverHellwig/sanskrit
**Current Implementation**: Bhagavad Gita (700 verses) + Rig Veda (10,551 verses)
