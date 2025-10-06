# DCS Sanskrit Lexicon for ClassicsViewer

**Status**: ✅ Production Ready  
**Coverage**: 88.0% on Bhagavad Gita  
**License**: CC BY 4.0 (attribution required)

## Quick Start

```bash
# Complete workflow (4 minutes total)
python3 extract_dcs_lexicon.py    # Extract + enhance (4 min)
python3 create_dcs_lexicon.py     # Package ZIP (5 sec)
python3 test_dcs_coverage.py      # Test coverage (2 sec)

# Output: dcs_sanskrit_lexicon.zip (34.5 MB)
```

## What You Get

- **179,806** dictionary lemmas with definitions
- **4.7 million** morphology forms (word → lemma mappings)
- **3,699** sandhi-split compound forms
- **88.0% coverage** on classical Sanskrit texts
- **Ready for app import** - one ZIP file

## Data Source

**Digital Corpus of Sanskrit (DCS)** by Oliver Hellwig
- **Repository**: https://github.com/OliverHellwig/sanskrit
- **Website**: http://www.sanskrit-linguistics.org/dcs/
- **License**: Creative Commons Attribution 4.0 International
- **Corpus**: 5.5 million words from classical texts

## Coverage Results

| Category | Words | Percentage |
|----------|-------|------------|
| **Total BG vocabulary** | 4,055 | 100% |
| Found in dictionary | 658 | 16.2% |
| Found in morphology | 3,197 | 78.8% |
| **Total found** | **3,569** | **88.0%** |
| Missing | 486 | 12.0% |

**Improvement from sandhi splitting**: 40% → 88% (+48 percentage points)

## License Compliance

### DCS Data: CC BY 4.0

**Attribution** (included in app license screen):
```
Digital Corpus of Sanskrit (DCS)
Author: Oliver Hellwig
License: CC BY 4.0
Source: http://www.sanskrit-linguistics.org/dcs/
```

### Sanskrit Parser: MIT License

Used for sandhi splitting enhancement.

## Documentation

- **README.md** - This file (quick start)
- **WORKFLOW.md** - Detailed workflow
- **DCS_LEXICON_DOCUMENTATION.md** - Complete technical docs
- **LICENSE_COMPLIANCE.md** - License details

## Dependencies

```bash
pip install indic-transliteration sanskrit_parser
```

---

**Last Updated**: October 5, 2025 | **Version**: 1.0 | **Coverage**: 88.0%
