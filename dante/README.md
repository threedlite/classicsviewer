# Dante's Divine Comedy for ClassicsViewer

**Status**: Production Ready
**Language**: Italian
**Lines**: 14,233 verses (tercets)
**Translation**: Longfellow (1867)
**License**: Public Domain

## Overview

This module provides Dante's Divine Comedy in Italian with Longfellow's English translation for ClassicsViewer.

### Contents

- **Inferno** - 34 cantos (Hell)
- **Purgatorio** - 33 cantos (Purgatory)
- **Paradiso** - 33 cantos (Paradise)
- **Total**: 100 cantos, 14,233 verses

## Quick Start

```bash
cd dante
python3 create_dante_database.py
```

The script automatically:
1. Downloads Italian text from Project Gutenberg (ebook #1000)
2. Downloads English translation from Project Gutenberg (ebook #1004)
3. Parses and aligns all 100 cantos
4. Creates SQLite database
5. Compresses to `dante_texts.db.zip` (3.3 MB)

No manual downloads required.

## Data Sources

### Italian Text
- **Source**: Project Gutenberg ebook #1000
- **URL**: https://www.gutenberg.org/ebooks/1000
- **License**: Public Domain

### English Translation
- **Translator**: Henry Wadsworth Longfellow (1807-1882)
- **Source**: Project Gutenberg ebook #1004
- **URL**: https://www.gutenberg.org/ebooks/1004
- **License**: Public Domain (translation published 1867)

## Database Statistics

| Metric | Count |
|--------|-------|
| Authors | 1 |
| Works | 1 |
| Cantos (Books) | 100 |
| Italian Lines | 14,233 |
| English Translations | 14,243 |
| Words | 101,601 |
| Database Size | 14.88 MB |
| Compressed Size | 3.30 MB |

## File Structure

```
dante/
├── create_dante_database.py   # Main build script
├── README.md                  # This file
├── .gitignore
├── data-sources/
│   ├── divina_commedia_italian.txt    # Italian text (Project Gutenberg)
│   └── divine_comedy_longfellow.txt   # English translation
├── dante_texts.db             # Generated database
└── dante_texts.db.zip         # Compressed database
```

## Notes

### Line Alignment
The Italian and English texts are aligned line-by-line. Longfellow's translation preserves Dante's tercet structure (terza rima), so each Italian line corresponds to one English line.

A few cantos have minor line count differences (1-8 lines) due to formatting variations in the source texts:
- Inferno XXXIV: 139 IT / 140 EN
- Purgatorio XXVI: 148 IT / 156 EN (includes Italian quotes from Dante's original)
- Purgatorio XXXIII: 145 IT / 146 EN

### No Dictionary (Future Addition)
Unlike Greek/Latin/Sanskrit, there is currently no Italian dictionary included.

Potential sources for future integration:
- [Italian Wiktionary Parser](https://github.com/snizio/italian-wiktionary-parser/) - 370K entries, CC BY-SA 3.0
- [Kaikki.org Wiktionary Extracts](https://kaikki.org/dictionary/) - Pre-extracted, CC BY-SA 3.0
- [FreeLing Italian WordNet](https://nlp.lsi.upc.edu/freeling/node/12) - 360K forms, CC BY

## License

All texts are in the **Public Domain**. Commercial use is permitted.

### Attribution (optional but appreciated)
```
Italian text: La Divina Commedia by Dante Alighieri
English translation: Henry Wadsworth Longfellow (1867)
Source: Project Gutenberg (www.gutenberg.org)
```

---

**Last Updated**: December 2025
**Version**: 1.0
