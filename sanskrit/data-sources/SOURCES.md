# Sanskrit Data Sources Documentation

This document lists all source files in this directory and where they were downloaded from.

## Bhagavad Gita

### Sanskrit Text (18 chapters, 700 verses)
**Source**: Sanskrit Wikisource
**Base URL**: https://sa.wikisource.org/wiki/भगवद्गीता
**License**: CC BY-SA 4.0
**Download Date**: October 4, 2025
**Files**: `bhagavad_gita_sa_*.html` (18 files: bhagavad_gita_sa_1.html through bhagavad_gita_sa_18.html)
**Download Script**: `download_bhagavad_gita_sanskrit.sh`
**Parser**: `parse_bhagavad_gita_sanskrit.py`
**Parsed Output**: `bhagavad_gita_sanskrit.json`

**URL Pattern**:
- Chapter 1: https://sa.wikisource.org/wiki/भगवद्गीता/अर्जुनविषादयोगः
- Chapter 2: https://sa.wikisource.org/wiki/भगवद्गीता/साङ्ख्ययोगः
- ...
- Chapter 18: https://sa.wikisource.org/wiki/भगवद्गीता/मोक्षसंन्यासयोगः

### English Translation 1: Arnold (18 chapters, prose format)
**Source**: English Wikisource
**Translator**: Edwin Arnold (1885)
**Base URL**: https://en.wikisource.org/wiki/The_Bhagavad_Gita_(Arnold_translation)
**License**: Public Domain
**Download Date**: October 4, 2025
**Files**: `bhagavad_gita_en_*.html` (18 files: bhagavad_gita_en_1.html through bhagavad_gita_en_18.html)
**Download Script**: `download_bhagavad_gita_english.sh`
**Parser**: `parse_bhagavad_gita_english.py`
**Parsed Output**: `bhagavad_gita_english.json`

**URL Pattern**:
- Chapter 1: https://en.wikisource.org/wiki/The_Bhagavad_Gita_(Arnold_translation)/Chapter_1
- Chapter 2: https://en.wikisource.org/wiki/The_Bhagavad_Gita_(Arnold_translation)/Chapter_2
- ...
- Chapter 18: https://en.wikisource.org/wiki/The_Bhagavad_Gita_(Arnold_translation)/Chapter_18

**Note**: Arnold's translation is in prose format, not verse-by-verse. Each chapter is a continuous narrative.

### English Translation 2: Besant (18 chapters, 700 verses)
**Source**: English Wikisource
**Translator**: Annie Besant (1922, 4th edition)
**Base URL**: https://en.wikisource.org/wiki/Bhagavad-Gita_(Besant_4th)
**License**: Public Domain
**Download Date**: October 4, 2025
**Files**: `bhagavad_gita_besant_*.html` (18 files: bhagavad_gita_besant_1.html through bhagavad_gita_besant_18.html)
**Download Script**: `download_bhagavad_gita_besant.sh`
**Parser**: `parse_bhagavad_gita_besant.py`
**Parsed Output**: `bhagavad_gita_besant.json`

**URL Pattern**:
- Discourse 1: https://en.wikisource.org/wiki/Bhagavad-Gita_(Besant_4th)/Discourse_1
- Discourse 2: https://en.wikisource.org/wiki/Bhagavad-Gita_(Besant_4th)/Discourse_2
- ...
- Discourse 18: https://en.wikisource.org/wiki/Bhagavad-Gita_(Besant_4th)/Discourse_18

**Note**: Besant's translation is verse-by-verse, with each of the 700 verses translated individually.

## License Summary

All sources used are properly licensed for commercial use:

| Source | License | Commercial Use | Attribution |
|--------|---------|----------------|-------------|
| Sanskrit Wikisource - Bhagavad Gita | CC BY-SA 4.0 | ✅ Yes | Ancient text |
| English Wikisource - Arnold Translation | Public Domain | ✅ Yes | Edwin Arnold (1885) |
| English Wikisource - Besant Translation | Public Domain | ✅ Yes | Annie Besant (1922) |

## Statistics

**Total Files**: 58
- Bhagavad Gita Sanskrit HTML: 18 files
- Bhagavad Gita English (Arnold) HTML: 18 files
- Bhagavad Gita English (Besant) HTML: 18 files
- JSON (parsed data): 3 files
- Scripts (download + parse): 6 files
- Documentation: 1 file (this file)

**Content**:
- Sanskrit verses: 700 (across 18 chapters)
- Arnold English translation: ~110,000 characters (prose, 18 chapters)
- Besant English translation: 700 verses (verse-by-verse, 18 chapters)

**Database Output**:
- `../sanskrit_texts.db` (1.0 MB)
- `../sanskrit_texts.db.zip` (289 KB)

## Notes

This folder contains source data for the Bhagavad Gita text database. For Sanskrit dictionary and morphology data, see the DCS (Digital Corpus of Sanskrit) lexicon in the parent directory:

- **Dictionary source**: `../dcs_sanskrit_lexicon.zip` (34 MB)
- **Coverage**: 88.0% on Bhagavad Gita vocabulary
- **License**: CC BY 4.0
- **Documentation**: See `../README.md` and `../DCS_LEXICON_DOCUMENTATION.md`
