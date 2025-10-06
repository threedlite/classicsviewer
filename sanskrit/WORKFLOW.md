# Sanskrit Implementation - Complete Workflow

## Overview

This workflow creates a complete Sanskrit implementation for ClassicsViewer with:
1. **Texts Database** - Bhagavad Gita + Rig Veda with English translations
2. **Lexicon** - DCS dictionary and morphology for word lookups

---

## Quick Start (5 minutes total)

```bash
cd sanskrit
source venv/bin/activate

# 1. Create texts database (30 seconds)
python3 create_sanskrit_database.py

# 2. Extract DCS lexicon (4 minutes)
python3 extract_dcs_lexicon.py
python3 create_dcs_lexicon.py
python3 test_dcs_coverage.py

# Outputs:
# - sanskrit_texts.db.zip (4.67 MB) - Ready for app
# - dcs_sanskrit_lexicon.zip (34.5 MB) - Ready for app
```

---

## Part 1: Sanskrit Texts Database

### One-Command Complete Database

```bash
# Creates both Bhagavad Gita + Rig Veda in single database
python3 create_sanskrit_database.py
```

**Output:**
- `sanskrit_texts.db` (16.47 MB uncompressed)
- `sanskrit_texts.db.zip` (4.67 MB compressed)

**Contents:**
- **2 authors**: Ved Vyasa, Various Rishis
- **2 works**: Bhagavad Gita, Rig Veda
- **28 books**: 18 BG chapters + 10 RV mandalas
- **11,251 verses**: 700 BG + 10,551 RV
- **171,351 words** (33,184 unique)
- **10,694 translations**

### Individual Text Scripts (Optional)

If you need only one text:

```bash
# Bhagavad Gita only (700 verses)
python3 create_sanskrit_texts.py
# Output: sanskrit_texts.db.zip (~200 KB)

# Rig Veda only (10,551 verses)
python3 create_rigveda_texts.py
# Output: rigveda_texts.db.zip (4.39 MB)
```

### Prerequisites: Source Data

The texts are built from JSON files in `data-sources/`. If these don't exist, create them:

```bash
cd data-sources

# Bhagavad Gita sources
./download_bhagavad_gita_sanskrit.sh
./download_bhagavad_gita_english.sh
./download_bhagavad_gita_besant.sh

python3 parse_bhagavad_gita_sanskrit.py
python3 parse_bhagavad_gita_english.py
python3 parse_bhagavad_gita_besant.py

# Rig Veda sources (already in DCS repository)
# Located at: ../../data-sources/sanskrit/dcs/data/rigveda/pada-and-analysis.dat
# Translation at: ../../data-sources/sanskrit/translations/RV-Griffith.txt
```

---

## Part 2: DCS Lexicon (Dictionary + Morphology)

### Three-Step Lexicon Creation

```bash
# Step 1: Extract DCS lexicon with sandhi enhancement (4 minutes)
python3 extract_dcs_lexicon.py
# Outputs:
# - dcs_sanskrit_dictionary.csv (26 MB)
# - dcs_sanskrit_morphology.csv (264 MB)
# - dcs_extraction_stats.json

# Step 2: Package into ZIP (5 seconds)
python3 create_dcs_lexicon.py
# Output: dcs_sanskrit_lexicon.zip (34.5 MB)

# Step 3: Test coverage on Bhagavad Gita (2 seconds)
python3 test_dcs_coverage.py
# Output: dcs_missing_words.txt
# Expected coverage: 88.0%
```

### What Gets Created

**DCS Lexicon Contents:**
- **179,806** dictionary lemmas with definitions
- **4,700,299** morphology forms (word → lemma mappings)
  - 4,696,600 from DCS CoNLL-U files
  - 3,699 sandhi-enhanced compounds
- **Coverage**: 88.0% on Bhagavad Gita vocabulary

**Sandhi Enhancement:**
- Automatically splits compounds like `अकर्मणश्च` → `अकर्मणः` + `च`
- Uses `sanskrit_parser` library
- Validates components exist in DCS
- Improves coverage from 40% → 88% (+48 percentage points)

---

## Setup

### Virtual Environment (Recommended)

```bash
# Create venv (one time)
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Dependencies

**Required:**
- `indic-transliteration` - IAST ↔ Devanagari conversion

**Optional (for sandhi enhancement):**
- `sanskrit_parser` - Automatic compound splitting

**requirements.txt:**
```
indic-transliteration==2.3.75
sanskrit_parser
```

---

## Data Sources

### Texts

| Source | License | Used For |
|--------|---------|----------|
| Sanskrit Wikisource | CC BY-SA 4.0 | Bhagavad Gita Sanskrit |
| Edwin Arnold (1885) | Public Domain | BG English translation (prose) |
| Annie Besant (1922) | Public Domain | BG English translation (verse) |
| DCS pada-and-analysis.dat | CC BY 4.0 | Rig Veda Sanskrit |
| Ralph T.H. Griffith (1896) | Public Domain | RV English translation |

### Lexicon

| Source | License | Used For |
|--------|---------|----------|
| DCS dictionary.csv | CC BY 4.0 | 179,806 lemmas with definitions |
| DCS CoNLL-U files | CC BY 4.0 | 4.7M morphology mappings |
| sanskrit_parser | MIT | Sandhi compound splitting |

All sources are **commercial-use compatible**.

---

## Database Schema

Same schema as Greek/Latin/Arabic texts:

```sql
-- Authors and works
CREATE TABLE authors (id, name, name_alt, language, has_translations);
CREATE TABLE works (id, author_id, title, title_alt, title_english, type, urn, description);

-- Text structure
CREATE TABLE books (id, work_id, book_number, label, start_line, end_line, line_count);
CREATE TABLE text_lines (id, book_id, line_number, sequence_number, line_text, line_xml, speaker);

-- Word indexing and translations
CREATE TABLE words (id, word, book_id, line_number, sequence_number, word_position);
CREATE TABLE translation_segments (id, book_id, start_line, end_line, sequence_number, translation_text, translator, speaker);
```

**Lexicon Schema:**
```sql
CREATE TABLE dictionary (lemma, language, definition, html_definition, source_name);
CREATE TABLE morphology (word_form, lemma, root, pos, language, confidence, source_name);
CREATE TABLE normalization_rules (search_pattern, replacement, language);
```

---

## Verification

### Texts Database

```bash
# Check database integrity
unzip -t sanskrit_texts.db.zip

# Query database
sqlite3 sanskrit_texts.db "SELECT * FROM authors;"
sqlite3 sanskrit_texts.db "SELECT id, title_english FROM works;"
sqlite3 sanskrit_texts.db "SELECT work_id, COUNT(*) FROM books GROUP BY work_id;"
```

**Expected Output:**
- 2 authors (Vyasa, Various Rishis)
- 2 works (Bhagavad Gita, Rig Veda)
- 28 books (18 + 10)
- 11,251 verses
- ZIP file valid with no errors

### Lexicon

```bash
# Check lexicon integrity
unzip -t dcs_sanskrit_lexicon.zip

# Check coverage
python3 test_dcs_coverage.py
```

**Expected Coverage:**
- Total Bhagavad Gita words: 4,055
- Found in lexicon: 3,569 (88.0%)
- Missing: 486 (12.0%)

---

## Integration with ClassicsViewer

### For App Development

1. **Copy databases to app assets:**
   ```bash
   cp sanskrit_texts.db.zip ../app/src/debug/assets/
   cp dcs_sanskrit_lexicon.zip ../app/src/debug/assets/
   ```

2. **App extracts on first launch:**
   - Texts: `/data/data/.../databases/sanskrit_texts.db`
   - Lexicon: `/data/data/.../databases/dcs_sanskrit_lexicon.db`

3. **User workflow:**
   - Select "Sanskrit" language
   - Browse authors: Ved Vyasa, Various Rishis
   - Select work: Bhagavad Gita or Rig Veda
   - Read text with word lookup enabled
   - Tap any word → see definition from DCS lexicon
   - Swipe to translation view

### Database Sizes

| File | Uncompressed | Compressed |
|------|--------------|------------|
| Texts | 16.47 MB | 4.67 MB |
| Lexicon | ~300 MB | 34.5 MB |
| **Total** | ~316 MB | **39.2 MB** |

---

## Troubleshooting

### Missing Source Files

**Problem:** `Error: Text file not found: data-sources/bhagavad_gita_sanskrit.json`

**Solution:**
```bash
cd data-sources
./download_bhagavad_gita_sanskrit.sh
python3 parse_bhagavad_gita_sanskrit.py
```

### Low Lexicon Coverage (<70%)

**Problem:** Coverage test shows <70%

**Possible causes:**
- `sanskrit_parser` not installed → sandhi enhancement skipped
- Wrong database used for testing

**Solution:**
```bash
pip install sanskrit_parser
python3 extract_dcs_lexicon.py  # Re-run with sandhi
python3 test_dcs_coverage.py
```

### Import Error: indic-transliteration

**Problem:** `ImportError: No module named 'indic_transliteration'`

**Solution:**
```bash
source venv/bin/activate
pip install indic-transliteration
```

### Rig Veda Not Found

**Problem:** `Error: Rig Veda data file not found`

**Check:**
```bash
ls -la ../data-sources/sanskrit/dcs/data/rigveda/pada-and-analysis.dat
ls -la ../data-sources/sanskrit/translations/RV-Griffith.txt
```

These should exist if the DCS repository is properly cloned.

---

## File Outputs

```
sanskrit/
├── sanskrit_texts.db              # Combined texts (16.47 MB)
├── sanskrit_texts.db.zip          # Compressed texts (4.67 MB) ✓ FOR APP
├── rigveda_texts.db               # Rig Veda only (15 MB, if created separately)
├── rigveda_texts.db.zip           # Compressed RV (4.39 MB)
├── dcs_sanskrit_dictionary.csv    # 26 MB
├── dcs_sanskrit_morphology.csv    # 264 MB
├── dcs_sanskrit_lexicon.zip       # 34.5 MB ✓ FOR APP
├── dcs_extraction_stats.json      # Build statistics
├── dcs_missing_words.txt          # Words not in lexicon (12%)
└── dcs_extraction.log             # Build log
```

**Files for App:**
- `sanskrit_texts.db.zip` (4.67 MB)
- `dcs_sanskrit_lexicon.zip` (34.5 MB)

---

## Performance

### Build Times

| Task | Duration |
|------|----------|
| Bhagavad Gita database | ~2 seconds |
| Rig Veda database | ~20 seconds |
| **Combined database** | **~30 seconds** |
| Extract DCS lexicon | ~180 seconds (3 min) |
| Sandhi enhancement | ~40 seconds |
| Create lexicon ZIP | ~5 seconds |
| Test coverage | ~2 seconds |
| **Total workflow** | **~5 minutes** |

### Memory Usage

- DCS extraction: ~2.8 GB peak (loading morphology)
- Sandhi enhancement: ~500 MB
- Text database creation: ~100 MB

---

## Next Steps: Expansion with DCS Translations

### Texts Ready to Implement (Have DCS Translations)

See `DCS_TRANSLATIONS_AVAILABLE.md` for complete list of 16 texts with translations.

**Recommended Priority** (all ready with DCS translations):
1. **Atharvaveda** (Śaunaka) - Complete the four Vedas
2. **Vājasaneyi Saṃhitā** (Yajur Veda) - Major Vedic text
3. **Chāndogyopaniṣad** - Major Upanishad
4. **Aitareyopaniṣad** - Principal Upanishad
5. **Śvetāśvataropaniṣad** - Theistic Upanishad

**Total Effort**: ~2 weeks
**Result**: All 4 Vedas + 3 major Upanishads

### Texts Requiring External Translations

These major texts are in DCS but lack DCS translations:
- Mahābhārata (1,995 files) - Would need external translation
- Rāmāyaṇa (606 files) - Would need external translation
- Yogasūtra (4 files) - Would need external translation
- 250+ other texts

See `DCS_TEXTS_CATALOG.md` for all 268 available texts.

---

**Last Updated**: October 6, 2025
**Version**: 2.0 (Unified Bhagavad Gita + Rig Veda)
