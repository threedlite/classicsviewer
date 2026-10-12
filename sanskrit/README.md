# Sanskrit for ClassicsViewer

**Status**: ✅ Production Ready
**Texts**: 272 works (Bhagavad Gītā, Rig Veda, all 270 DCS works; 495K verse lines, 5.9M words)
**Lexicon Coverage**: 99.8% dictionary lookup success
**Build Time**: ~3 h 45 min (fully automated)
**License**: CC BY 4.0, CC BY-SA 4.0, Public Domain (all commercial-use compatible)

## Overview

This implementation provides complete Sanskrit support for ClassicsViewer with:
1. **Sanskrit Texts Database** - 272 works with interlinear translations
   - Bhagavad Gita (18 chapters, Wikisource with Arnold/Besant translations)
   - Rig Veda (10 maṇḍalas, Griffith translation)
   - 270 DCS works (Mahabharata, Ramayana, Upanishads, Vedas, philosophical texts, etc.)
2. **DCS Lexicon** - 179,806 dictionary entries, 4.7M morphology forms
3. **Stanza NLP Morph Data** - Case/number/gender, POS tags, dependency relations

---

## Quick Start

**See [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) for complete details.**

```bash
cd sanskrit

# Single command - builds everything automatically!
./run_build.sh

# Output: sanskrit_texts.db.zip (~486MB)
```

**CRITICAL**: Always use `./run_build.sh` or `./venv/bin/python3` directly. Do NOT use `source venv/bin/activate` because multiprocessing workers spawn with system Python, not the activated venv.

---

## What You Get

**272 Works Including:**
- **Bhagavad Gita**: 18 chapters, 700 verses, 2 English translations (Arnold + Besant)
- **Rig Veda**: 10 maṇḍalas, 10,551 verses, Griffith translation
- **Mahabharata**: 18 parvans, 73,214 verse lines, Ganguli translation (2,106 sections)
- **Ramayana**: 7 kāṇḍas, 18,717 verse lines, Dutt translation (537 sargas; approximate in four kāṇḍas, see below)
- **270 DCS works**: Upanishads, Vedas, epics, philosophical texts, and more

**Database Statistics:**
- **272 works**, 2,227 books (494,931 verse lines, one line per DCS verse)
- **5.86 million words** (314K unique)
- **179,806 dictionary entries**
- **4.7 million morphology forms**
- **494,931 interlinear segments** (208,185 from the DCS treebank, 286,746 from Stanza NLP)
- **14,882 human-translation segments** in 17 works
- **Database**: ~2.35GB uncompressed, ~486MB compressed

**Morph Data (via Stanza NLP):**
- Case/number/gender (e.g., "acc s m" = accusative singular masculine)
- POS tags (NOUN, VERB, ADJ, PART, etc.)
- Dependency relations (nsubj, obj, compound:coord, etc.)

### Implementation Details

The main script `create_sanskrit_database_interlinear.py` (called via `run_build.sh`) uses:
1. **Direct JSON loading** for Bhagavad Gita (from Wikisource)
2. **DCS pada-and-analysis.dat** for Rig Veda (special TSV format)
3. **Parallel DCS CoNLL-U parser** for 268 other texts (8 workers)
4. **Stanza NLP** for morphological analysis during interlinear generation

The build pipeline automatically handles:
- Parallel processing with 8 workers for DCS text loading (~75 min)
- IAST to Devanagari conversion for all text
- Pre-built lexicon import from `dcs_sanskrit_lexicon.zip`
- Interlinear generation with Stanza NLP (~20 min)
- Stanza models downloaded and verified once by the main process; workers
  load them with `download_method=None`, and a model that fails to load
  stops the build (see BUILD_INSTRUCTIONS.md, "Stanza models")
- Import of interlinear segments into database
- Compression to final ZIP file

---

## DCS Sanskrit Lexicon

The lexicon is pre-built and included in the repository as `dcs_sanskrit_lexicon.zip` (35 MB).

**Contents:**
- **179,806** dictionary lemmas with definitions
- **4.7 million** morphology forms (word → lemma mappings)
- **3,699** sandhi-split compound forms (automatic enhancement)
- **99.8% coverage** on Sanskrit texts

**Regeneration** (only if needed):
```bash
python3 extract_dcs_lexicon.py    # Extract from DCS corpus (~5 min)
python3 create_dcs_lexicon.py     # Package ZIP (~10 sec)
```

---

## Data Sources

### Texts

1. **Bhagavad Gita Sanskrit** - Sanskrit Wikisource (CC BY-SA 4.0)
2. **Bhagavad Gita English (Arnold)** - Public Domain (1885)
3. **Bhagavad Gita English (Besant)** - Public Domain (1922)
4. **Rig Veda Sanskrit** - DCS pada-and-analysis.dat (CC BY 4.0, Oliver Hellwig)
5. **Rig Veda English (Griffith)** - Public Domain (1896), English Wikisource
   transcription, stanza by stanza
6. **270 DCS Works** - All CoNLL-U files from DCS corpus (CC BY 4.0)
   - Includes Mahabharata, Ramayana, Upanishads, Vedas, philosophical texts
7. **Mahabharata English (Ganguli)** - Public Domain (1883–1896), Project
   Gutenberg 15474–15477, attached chapter by chapter through the
   Brodbeck & Black critical-edition/Ganguli concordance
   (`mahabharata_ganguli.py`, `data-sources/SOURCES.md`)
8. **Chāndogya Upaniṣad English (Müller)** - Public Domain (1879), English
   Wikisource transcription of Sacred Books of the East vol. 1, one segment
   per khaṇḍa
9. **Thirteen further translations** registered in
   `data-sources/translation_sources.py` (Rāmāyaṇa by Dutt, Viṣṇupurāṇa,
   Lotus Sūtra, Atharvaveda, Kathāsaritsāgara, Arthaśāstra, Kāmasūtra,
   Suśruta, Yogasūtra, Kumārasaṃbhava, Gītagovinda, Sarvadarśanasaṃgraha,
   Hitopadeśa) - all Public Domain, from Project Gutenberg and English
   Wikisource; see `data-sources/SOURCES.md` for alignment and coverage

### Lexicon

**Digital Corpus of Sanskrit (DCS)** by Oliver Hellwig
- **Repository**: https://github.com/OliverHellwig/sanskrit
- **Website**: http://www.sanskrit-linguistics.org/dcs/
- **License**: Creative Commons Attribution 4.0 International
- **Corpus**: 5.5 million words from 268 classical texts

### NLP Models

**Stanza Sanskrit Models** by Stanford NLP Group
- Used for morphological analysis (case, number, gender, POS, dependencies)
- Pre-loaded before multiprocessing to share across workers

---

## Available Texts

All **272 works** are included (Bhagavad Gītā, Rig Veda, all 270 DCS works):
- **Bhagavad Gita** (700 verses) - With Arnold + Besant translations
- **Rig Veda** (10,551 verses) - With Griffith translation
- **Mahabharata** (18 parvans, ~73K verse lines) - With Ganguli translation
  per chapter (2,106 sections) plus interlinear glosses
- **Ramayana** (7 kandas, ~18.7K verse lines) - Dutt translation per sarga: exact in Bāla, Araṇya and Kiṣkindhā (194 sargas), approximate in Ayodhyā, Sundara, Yuddha and Uttara (each segment says so and why); interlinear glosses throughout
- **Upanishads** - Multiple (Chāndogya with Müller translation)
- **Vedas** - Atharvaveda, Yajur Veda, etc.
- **Philosophical texts** - Yogasutra, Nyayasutra, etc.
- **Poetry** - Meghaduta, Kumarasambhava, etc.
- And 250+ more works

See `DCS_TEXTS_CATALOG.md` for the complete list.

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
- Ralph T.H. Griffith translation of the Rig Veda (1896), from Wikisource
- F. Max Müller translation of the Chāndogya Upaniṣad (1879), from Wikisource
- Kisari Mohan Ganguli translation of the Mahabharata (1883–1896), from
  Project Gutenberg; the build strips the Gutenberg header, licence and name
  as its terms require
- Dutt, Kern, Whitney, Tawney, Shamasastry, Burton & Arbuthnot,
  Bhishagratna, Johnston, Griffith, Arnold, Cowell & Gough for the works
  listed in `data-sources/SOURCES.md`

Sources with a NonCommercial clause are not used (app-store distribution
may count as commercial use); OCR text is never used. See
`LICENSE_COMPLIANCE.md`.

### Sanskrit Parser: MIT License
Used for sandhi splitting enhancement (build-time only).

### Stanza NLP: Apache 2.0
Used for morphological analysis during interlinear generation.

See `LICENSE_COMPLIANCE.md` for complete details.

---

## Dependencies

Install via requirements.txt:
```bash
pip install -r requirements.txt
```

Key dependencies:
- `indic-transliteration` - IAST ↔ Devanagari conversion
- `stanza` - Sanskrit NLP for morphological analysis
- `sanskrit_parser` - Optional, for sandhi splitting

---

## Documentation

- **BUILD_INSTRUCTIONS.md** - **Primary build guide** (start here!)
- **README.md** - This file (overview)
- **WORKFLOW.md** - Historical workflow (deprecated, see BUILD_INSTRUCTIONS.md)
- **DCS_LEXICON_DOCUMENTATION.md** - Complete lexicon technical docs
- **DCS_TEXTS_CATALOG.md** - All 268 available texts in DCS
- **LICENSE_COMPLIANCE.md** - License details and attribution

---

## File Structure

```
sanskrit/
├── run_build.sh                           # Main build script - RUN THIS!
├── create_sanskrit_database_interlinear.py # Complete automated pipeline
├── batch_generate_interlinear.py          # Parallel interlinear generation
├── generate_sanskrit_interlinear.py       # Per-work interlinear generator
├── sanskrit_dictionary_lookup.py          # Dictionary lookup with sandhi
├── extract_dcs_lexicon.py                 # Extract DCS lexicon (one-time)
├── create_dcs_lexicon.py                  # Package lexicon ZIP (one-time)
├── dcs_sanskrit_lexicon.zip               # Pre-built lexicon (35 MB)
├── normalization_rules_sanskrit.csv
├── requirements.txt
├── venv/                                  # Python virtual environment
├── data-sources/                          # Downloaded source data
│   ├── bhagavad_gita_sanskrit.json
│   ├── bhagavad_gita_english.json
│   ├── bhagavad_gita_besant.json
│   └── SOURCES.md
├── interlinear_output/                    # Generated interlinear files
│   ├── *.interlinear.txt                  # Plain text glosses
│   ├── *.dcs-eng99.xml                    # TEI XML with morph data
│   └── generation_report.txt              # Build statistics
├── sanskrit_texts.db                      # Output database (~2.35 GB)
└── sanskrit_texts.db.zip                  # Compressed output (~486 MB)
```

---

**Last Updated**: October 2026
**Version**: 4.0 (Full DCS Corpus + Stanza NLP)
**Texts**: 272 works (Bhagavad Gita, Rig Veda, Mahabharata, Ramayana, 268 more)
**Interlinear Coverage**: 99.8%
**Total Verse Lines**: 494,931
**Total Words**: 5.86 million
**Database Size**: ~2.35 GB (~486 MB compressed)
