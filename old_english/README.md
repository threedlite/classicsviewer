# Old English (Anglo-Saxon) for ClassicsViewer

**Status**: Production Ready
**Language**: Old English (Anglo-Saxon)
**License**: Public Domain (commercial use allowed)

## Quick Start

```bash
cd old_english
python3 create_old_english_database.py
```

The script automatically:
1. Downloads Beowulf from Project Gutenberg
2. Downloads Bosworth-Toller dictionary from Germanic Lexicon Project
3. Parses the Old English text
4. Creates SQLite database with dictionary
5. Compresses to `old_english_texts.db.zip`

## Contents

### Texts

| Source | License | Content |
|--------|---------|---------|
| [Project Gutenberg #16328](https://www.gutenberg.org/ebooks/16328) | Public Domain | Beowulf (3,182 lines) |

**Beowulf**: The greatest surviving Old English poem, composed between 700-1000 CE. The only manuscript (Cotton MS Vitellius A.XV) nearly perished in a fire in 1731.

### Dictionary

| Source | License | Entries |
|--------|---------|---------|
| [Bosworth-Toller Anglo-Saxon Dictionary](https://bosworthtoller.com/) | Public Domain | ~42,000 |

The standard reference dictionary of Old English:
- Main Volume (1898) by Joseph Bosworth & T. Northcote Toller
- Supplement (1921) by T. Northcote Toller
- Digitized by Sean Crist's Germanic Lexicon Project

Note: Alistair Campbell's 1972 addenda are NOT public domain and are excluded.

## File Structure

```
old_english/
├── create_old_english_database.py   # Main build script
├── README.md                         # This file
├── .gitignore
├── data-sources/
│   ├── beowulf.txt                  # Gutenberg text (gitignored)
│   └── bosworth-toller/             # Dictionary data (gitignored)
├── old_english_texts.db             # Generated database
└── old_english_texts.db.zip         # Compressed database
```

## Data Sources

### Text
- **Source**: Project Gutenberg eBook #16328
- **URL**: https://www.gutenberg.org/ebooks/16328
- **License**: Public Domain in USA
- **Format**: Plain text Old English with glossary

### Dictionary
- **Source**: Germanic Lexicon Project
- **URL**: http://lexicon.ff.cuni.cz
- **Original**: Bosworth & Toller (1898/1921)
- **License**: Public Domain (copyright expired)
- **Format**: Custom markup text file

## No Translations

The current version includes only the original Old English text. Future versions may add:
- Seamus Heaney's translation (copyrighted)
- Other public domain translations

## Language Notes

Old English (Anglo-Saxon) was spoken in England from ~450-1100 CE. Key features:
- Germanic language, ancestor of Modern English
- Four cases (nominative, accusative, genitive, dative)
- Three genders (masculine, feminine, neuter)
- Special letters: þ (thorn), ð (eth), æ (ash), ƿ (wynn)

## License

- **Text**: Public Domain
- **Dictionary**: Public Domain

Commercial use is permitted without restriction.

### Attribution (requested but not required)
```
Text: Project Gutenberg
Dictionary: Bosworth-Toller Anglo-Saxon Dictionary, digitized by the Germanic Lexicon Project
```

---

**Last Updated**: December 2025
