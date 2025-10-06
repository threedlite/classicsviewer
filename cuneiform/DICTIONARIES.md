# Cuneiform Dictionary Build Process

## Overview

This directory contains scripts to build Sumerian and Akkadian dictionary packages from ORACC (Open Richly Annotated Cuneiform Corpus) data sources.

## Quick Start

```bash
# Build both lexicons (Sumerian + Akkadian)
python3 create_cuneiform_lexicons.py

# Build only Sumerian
python3 create_cuneiform_lexicons.py sumerian

# Build only Akkadian
python3 create_cuneiform_lexicons.py akkadian

# Download fresh data from ORACC first
python3 create_cuneiform_lexicons.py --download
```

## Output Files

**Sumerian Lexicon**: `sumerian_lexicon.zip` (1.0 MB)
- 14,817 dictionary entries
- 199,866 morphological forms
- Source: ePSD2 (electronic Pennsylvania Sumerian Dictionary)

**Akkadian Lexicon**: `akkadian_lexicon.zip` (199 KB)
- 3,651 dictionary entries
- 28,967 morphological forms
- Source: RINAP (Royal Inscriptions of the Neo-Assyrian Period)

## Data Sources

### ePSD2 (Sumerian)
- **URL**: http://oracc.museum.upenn.edu/json/epsd2.zip (~203 MB)
- **License**: CC BY-SA 3.0
- **Copyright**: The Pennsylvania Sumerian Dictionary Project, 2017-
- **Entries**: 15,940 Sumerian words with meanings and morphology
- **Download Location**: `../data-sources/epsd2.zip`
- **Extracted Glossary**: `../data-sources/epsd2/gloss-sux.json` (1.8 GB)

### RINAP (Akkadian)
- **URL**: http://oracc.museum.upenn.edu/json/rinap.zip (~24 MB)
- **License**: CC BY-SA 3.0
- **Copyright**: RINAP Project, 2011-2022
- **Entries**: 3,651 Akkadian words from Neo-Assyrian royal inscriptions
- **Download Location**: `../data-sources/rinap.zip`
- **Extracted Glossary**: `../data-sources/rinap/gloss-akk.json` (69 MB)

## Build Scripts

### Individual Language Scripts

**`create_sumerian_lexicon.py`**:
- Downloads or uses cached ePSD2 data
- Converts JSON glossary to CSV format
- Creates `sumerian_lexicon.zip` with:
  - `sumerian_dictionary.csv` - Dictionary entries (word, meaning, POS)
  - `sumerian_morphology.csv` - Word forms → lemma mappings

**`create_akkadian_lexicon.py`**:
- Downloads or uses cached RINAP data
- Converts JSON glossary to CSV format
- Creates `akkadian_lexicon.zip` with:
  - `akkadian_dictionary.csv` - Dictionary entries
  - `akkadian_morphology.csv` - Word forms → lemma mappings

### Unified Build Script

**`create_cuneiform_lexicons.py`**:
- Orchestrates both Sumerian and Akkadian builds
- Supports building individual or both lexicons
- Handles download coordination
- Reports on build success/failure

## CSV Format

### Dictionary CSV
```csv
word,meaning,pos,headword
a,arm,N,a[arm]N
bala,cross,V,bala[cross]V
```

### Morphology CSV
```csv
form,lemma,lemma_meaning,lemma_pos
a-na,a,arm,N
ba-la,bala,cross,V
```

## ORACC JSON Structure

The ORACC JSON glossaries have this structure:

```json
{
  "type": "glossary",
  "project": "epsd2",
  "license": "CC BY-SA",
  "lang": "sux",
  "entries": [
    {
      "headword": "a[arm]N",
      "cf": "a",
      "gw": "arm",
      "pos": "N",
      "forms": [
        {"n": "a-na", "icount": "123"}
      ],
      "norms": [
        {"n": "ana", "icount": "45"}
      ]
    }
  ]
}
```

**Key fields**:
- `cf`: Citation form (lemma/dictionary headword)
- `gw`: Guide word (English meaning)
- `pos`: Part of speech (N=noun, V=verb, etc.)
- `forms`: Attested cuneiform forms in texts
- `norms`: Normalized transliterations

## Integration with Main Build

These lexicons are designed to be merged into the main database build process:

1. **Build lexicons**: Run `create_cuneiform_lexicons.py`
2. **Copy to assets**: Lexicon ZIPs go to app assets folder
3. **App imports**: App loads dictionaries on first launch
4. **Dictionary lookup**: Words in cuneiform texts link to dictionary entries

## Comparison: ORACC vs Wiktionary

| Source | Sumerian | Akkadian | Morphology | License |
|--------|----------|----------|------------|---------|
| **ORACC** | **15,940** | **3,651** | ✅ 200K+ forms | CC BY-SA |
| Wiktionary | 844 | 716 | ⚠️ Limited | CC BY-SA |

**ORACC provides 19x more Sumerian entries and 5x more Akkadian entries than Wiktionary.**

## Format Advantages

- **Romanization**: Matches text transliteration format
- **No script conversion**: Texts already in romanized form
- **Rich morphology**: Comprehensive form → lemma mappings
- **Corpus-based**: Entries reflect actual usage in cuneiform texts
- **Scholarly quality**: Maintained by academic cuneiform projects

## License Compliance

Both dictionaries are released under CC BY-SA 3.0, which requires:
1. **Attribution**: Credit ORACC, ePSD2, and RINAP projects
2. **ShareAlike**: Derivatives must use same CC BY-SA license

Full attributions are included in the Android app's License Activity.

## Troubleshooting

**Error: ePSD2 glossary not found**
```bash
python3 create_sumerian_lexicon.py --download
```

**Error: RINAP glossary not found**
```bash
python3 create_akkadian_lexicon.py --download
```

**Download timeout**
- ORACC servers may be slow
- epsd2.zip is large (203 MB)
- Use `wget --continue` to resume interrupted downloads

**No morphology data**
- Check that JSON has "forms" and "norms" arrays
- Some entries may lack morphological data
- This is expected and not an error

## File Organization

```
cuneiform/
├── create_sumerian_lexicon.py       # Sumerian build script
├── create_akkadian_lexicon.py       # Akkadian build script
├── create_cuneiform_lexicons.py     # Unified build script
├── DICTIONARIES.md                  # This file
├── sumerian_dictionary.csv          # Generated dictionary
├── sumerian_morphology.csv          # Generated morphology
├── sumerian_lexicon.zip             # Final package
├── akkadian_dictionary.csv          # Generated dictionary
├── akkadian_morphology.csv          # Generated morphology
└── akkadian_lexicon.zip             # Final package

data-sources/
├── epsd2.zip                        # Downloaded ePSD2 (203 MB)
├── epsd2/gloss-sux.json            # Extracted Sumerian glossary (1.8 GB)
├── rinap.zip                        # Downloaded RINAP (24 MB)
└── rinap/gloss-akk.json            # Extracted Akkadian glossary (69 MB)
```

## Future Enhancements

Potential additions if more coverage is needed:

1. **Additional ORACC projects**: SAAo, RIAo, CMAwRo have Akkadian glossaries
2. **ePSD2 subprojects**: Administrative, literary, royal corpus glossaries
3. **Combined glossaries**: Merge multiple ORACC projects for broader coverage
4. **Wiktionary supplement**: Add Wiktionary entries for modern vocabulary

## References

- **ORACC**: http://oracc.museum.upenn.edu/
- **ePSD2**: http://oracc.museum.upenn.edu/epsd2/
- **RINAP**: http://oracc.museum.upenn.edu/rinap/
- **ORACC JSON Documentation**: http://oracc.museum.upenn.edu/doc/opendata/json/
- **License Information**: https://creativecommons.org/licenses/by-sa/3.0/
