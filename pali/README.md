# Pali Canon for ClassicsViewer

**Status**: Texts Ready, No Dictionary
**Language**: Pali
**License**: CC0 (Public Domain - commercial use allowed)

## Quick Start

```bash
cd pali
python3 create_pali_database.py
```

The script automatically:
1. Clones bilara-data from SuttaCentral (published branch)
2. Parses all suttas with segment-aligned translations
3. Creates SQLite database
4. Compresses to `pali_texts.db.zip`

## Contents

| Nikaya | Pali Name | English Name |
|--------|-----------|--------------|
| DN | Dīgha Nikāya | Long Discourses |
| MN | Majjhima Nikāya | Middle-Length Discourses |
| SN | Saṁyutta Nikāya | Connected Discourses |
| AN | Aṅguttara Nikāya | Numerical Discourses |
| KN | Khuddaka Nikāya | Minor Collection (Dhammapada, Udāna, Sutta Nipāta, etc.) |

## Data Sources

### Texts & Translations

| Source | License | Content |
|--------|---------|---------|
| [SuttaCentral bilara-data](https://github.com/suttacentral/bilara-data) | CC0 (Public Domain) | Full Pali Canon with translations |

- **Pali root texts**: Mahāsaṅgīti edition
- **English translations**: Bhikkhu Sujato (CC0)
- **Format**: JSON with segment IDs for perfect alignment

### Dictionary - NONE (Blocker)

| Source | License | Issue |
|--------|---------|-------|
| [Digital Pali Dictionary](https://github.com/digitalpalidictionary/dpd-db) | CC BY-NC-SA 4.0 | **NC restriction - not usable** |
| PTS Pali-English Dictionary (1921-25) | Probably public domain | No structured JSON format |

### Morphology

| Source | License | Notes |
|--------|---------|-------|
| [PaliNLP](https://github.com/daalft/PaliNLP) | Unknown | Morphological analyzer (Java) |

No Universal Dependencies treebank exists for Pali.

## File Structure

```
pali/
├── create_pali_database.py   # Main build script
├── README.md                  # This file
├── .gitignore
├── data-sources/
│   └── bilara-data/          # Cloned from SuttaCentral (gitignored)
├── pali_texts.db             # Generated database
└── pali_texts.db.zip         # Compressed database
```

## Translation Alignment

SuttaCentral uses segment IDs shared between Pali and translations:

**Pali root** (`mn1_root-pli-ms.json`):
```json
"mn1:1.1": "Evaṁ me sutaṁ—"
"mn1:26.4": "'Apariññātaṁ tassā'ti vadāmi."
```

**English translation** (`mn1_translation-en-sujato.json`):
```json
"mn1:1.1": "So I have heard."
"mn1:26.4": "Because they haven't completely understood it, I say."
```

Same segment IDs = direct 1:1 alignment. Cleaner than Greek/Latin line mapping.

## URLs

- Texts: https://github.com/suttacentral/bilara-data
- PaliNLP: https://github.com/daalft/PaliNLP
- PTS Dictionary (web): https://dsal.uchicago.edu/dictionaries/pali/
- PTS Dictionary (archive): https://archive.org/details/PTSPaliEnglishDictionary

## License

All texts are **CC0 (Public Domain)**. Commercial use is permitted.

### Attribution (optional but appreciated)
```
Pali text: Mahāsaṅgīti Tipiṭaka Buddhavasse 2500
English translation: Bhikkhu Sujato
Source: SuttaCentral (suttacentral.net)
```

---

**Last Updated**: December 2025
