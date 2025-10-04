# Hebrew Bible Data Sources - License and Attribution

This directory contains processed Hebrew Bible texts and lexical data from Open Scriptures projects. All materials are used in accordance with their respective licenses.

## Open Scriptures Hebrew Bible (morphhb)

**Source:** Westminster Leningrad Codex with morphological tagging
**Repository:** https://github.com/openscriptures/morphhb
**Website:** https://hb.openscriptures.org/
**License:** Creative Commons Attribution 4.0 International (CC BY 4.0)
**License URL:** https://creativecommons.org/licenses/by/4.0/

### Description

The Open Scriptures Hebrew Bible project provides the complete Hebrew Bible text with comprehensive morphological analysis. This includes:

- **Text Base:** Westminster Leningrad Codex (WLC) version 4.20
- **Format:** OSIS XML with embedded morphological codes
- **Morphology:** Full grammatical tagging for every Hebrew word
  - Part of speech (noun, verb, particle, etc.)
  - Tense/aspect (perfect, imperfect, infinitive, etc.)
  - Person, number, gender
  - State (absolute, construct)
  - Prefix/suffix information

### What We Use

- **Text Data:** Complete Hebrew Bible text (39 books, ~23,000 verses, ~305,000 words)
- **Morphological Codes:** Grammatical analysis for word-level dictionary lookups
- **Lemma Information:** Augmented Strong's numbers linking words to dictionary entries
- **Structure:** OSIS XML format preserving chapter/verse organization

### Attribution

Text Base: Westminster Leningrad Codex 4.20
Morphological Analysis: Open Scriptures Hebrew Bible Project
Contributors: See https://github.com/openscriptures/morphhb/graphs/contributors

### License Terms (CC BY 4.0)

You are free to:
- **Share** — copy and redistribute the material in any medium or format
- **Adapt** — remix, transform, and build upon the material for any purpose, even commercially

Under the following terms:
- **Attribution** — You must give appropriate credit, provide a link to the license, and indicate if changes were made

## Open Scriptures Hebrew Lexicon

**Source:** Strong's Hebrew and Aramaic Dictionary (digital edition)
**Repository:** https://github.com/openscriptures/HebrewLexicon
**License:** Creative Commons Attribution 4.0 International (CC BY 4.0)
**License URL:** https://creativecommons.org/licenses/by/4.0/

### Description

The Open Scriptures Hebrew Lexicon provides digitized lexical data from classical Hebrew lexicons:

- **Strong's Dictionary:** Definitions and etymological information
- **Brown-Driver-Briggs (BDB):** Comprehensive Hebrew and English lexicon
- **Lemma Mapping:** Links morphhb lemma codes to dictionary entries
- **Hebrew Text:** Vocalized lemma forms for dictionary headwords

### What We Use

- **Dictionary Entries:** 8,674 Hebrew/Aramaic lexical entries
- **Strong's Numbers:** H1-H8674 (e.g., H1961 = הָיָה "to be")
- **Definitions:** English meanings and usage notes
- **Morphology Mappings:** 114,142 word form → lemma relationships

### Original Sources

- **Strong, James.** *The Exhaustive Concordance of the Bible.* 1890. (Public Domain)
- **Brown, Francis; Driver, S.R.; Briggs, Charles A.** *A Hebrew and English Lexicon of the Old Testament.* Oxford: Clarendon Press, 1906. (Public Domain)

### Digital Edition Attribution

Digital compilation and XML encoding: Open Scriptures Hebrew Lexicon Project
License: CC BY 4.0

## Processing and Integration

The data from these sources has been processed for integration into the ClassicsViewer app:

1. **Text Processing** (`process_hebrew_complete.py`)
   - Extracts OSIS XML from morphhb repository
   - Maps Bible structure to app database schema
   - Preserves morphological codes and lemma information

2. **Lexicon Processing**
   - Parses HebrewStrong.xml for dictionary entries
   - Creates morphology mappings from word forms to lemmas
   - Packages CSVs for app import

3. **Normalization Rules**
   - Removes nikud (vocalization marks) for lookup matching
   - Normalizes final Hebrew letter forms (ך→כ, ם→מ, ן→נ, ף→פ, ץ→צ)
   - Preserves morpheme boundary markers (/) from source data

## Output Files

This directory contains the following processed files:

- `hebrew_texts.db` / `hebrew_texts.db.zip` — SQLite database with Hebrew Bible text
- `hebrew_lexicon.zip` — Dictionary package containing:
  - `dictionary.csv` — 8,674 lexical entries
  - `morphology.csv` — 114,142 word form mappings
  - `normalization_rules.csv` — Hebrew text normalization patterns

## Usage in ClassicsViewer App

The Hebrew Bible texts and dictionary are integrated into the ClassicsViewer Android app under the same CC BY 4.0 license. The app provides:

- Word-by-word dictionary lookup
- Morphological analysis display
- Original Hebrew text with vocalization
- Cross-referencing via Strong's numbers

## Compliance

This project complies with CC BY 4.0 attribution requirements by:

1. ✅ Providing clear attribution to Open Scriptures projects
2. ✅ Including license text and links
3. ✅ Documenting data sources and processing steps
4. ✅ Maintaining attribution in app UI (LicenseActivity.kt)
5. ✅ Not imposing additional restrictions on the licensed material

## Questions or Issues

For questions about the source data:
- morphhb: https://github.com/openscriptures/morphhb/issues
- HebrewLexicon: https://github.com/openscriptures/HebrewLexicon/issues

For questions about the ClassicsViewer integration:
- https://github.com/threedlite/classicsviewer/issues

---

**Last Updated:** October 4, 2025
**Processing Script Version:** process_hebrew_complete.py (full Hebrew Bible)
**Data Version:** morphhb WLC 4.20, HebrewLexicon (2024)
