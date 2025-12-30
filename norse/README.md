# Old Norse / Old Icelandic for ClassicsViewer

**Status**: Production Ready
**Language**: Old Norse (Old Icelandic)
**License**: CC BY-SA 3.0 + Public Domain (commercial use allowed with attribution)

## Quick Start

```bash
cd norse
python3 create_norse_database.py
```

The script automatically:
1. Clones CLTK Old Norse texts from GitHub
2. Clones Zoega's Old Icelandic Dictionary from GitHub
3. Clones IcePaHC Treebank for morphology from GitHub
4. Downloads English translations from Project Gutenberg
5. Parses all sagas and Eddas
6. Creates SQLite database with dictionary and morphology
7. Compresses to `norse_texts.db.zip`

## Language Notes

Old Icelandic IS Old Norse - specifically the Old West Norse dialect. The terms are used interchangeably because:

1. Most surviving Old Norse literature (sagas, Eddas) was written in Iceland
2. "Old Norse" is the umbrella term; "Old Icelandic" is the specific western dialect
3. Icelandic has changed so little that modern Icelanders can still read the sagas

All resources are compatible and share the same lexicon.

## Contents

### Texts (25 works)
- **Poetic Edda** (Sæmundar-Edda): 25 poems, 1083 stanzas
- **Prose Edda**:
  - Prologus: 5 chapters
  - Gylfaginning: 54 chapters
  - Skáldskaparmál: 89 chapters
  - Háttatal: 102 chapters
- **Sagas**: Grettis saga (93 ch), Völsunga saga (42 ch), Hrólfs saga kraka, Örvar-Odds saga, etc.
- **Þættir**: Norna-Gests þáttr, Þorsteins þáttr, etc.

### Dictionary
- **29,951 entries** from Zoega's Old Icelandic Dictionary (1910)
- **237 glossary entries** from Thorpe's Poetic Edda (proper nouns, mythological terms)

### Morphology
- **66,134 form→lemma mappings** from IcePaHC Treebank
- Examples: `menn` → `maður`, `konungs` → `konungur`

## File Structure

```
norse/
├── create_norse_database.py   # Main build script
├── README.md                   # This file
├── .gitignore
├── data-sources/
│   ├── non_texts/             # CLTK texts (gitignored)
│   ├── zoega-dictionary/      # Zoega JSON (gitignored)
│   └── icepahc/               # IcePaHC treebank (gitignored)
├── norse_texts.db             # Generated database
└── norse_texts.db.zip         # Compressed database
```

## Data Sources

All sources are downloaded automatically by the build script.

### Old Norse Texts
| Source | Repository | License |
|--------|------------|---------|
| CLTK Old Norse | https://github.com/cltk/non_texts | CC BY-SA 3.0 + Public Domain |

### Dictionary
| Source | Repository | License |
|--------|------------|---------|
| Zoega's Old Icelandic Dictionary (1910) | https://github.com/stscoundrel/old-icelandic-zoega | Public Domain + MIT |

### Morphology
| Source | Repository | License |
|--------|------------|---------|
| IcePaHC Treebank | https://github.com/UniversalDependencies/UD_Icelandic-IcePaHC | CC BY-SA 4.0 |

### English Translations (Project Gutenberg)

| Work | Translator | Year | Gutenberg ID | Coverage |
|------|------------|------|--------------|----------|
| Poetic Edda + Prose Edda (Gylfaginning, Prologus) | Benjamin Thorpe | 1866 | [14726](https://www.gutenberg.org/ebooks/14726) | 1042/1083 stanzas, 59/59 chapters |
| Völsunga saga | Eiríkr Magnússon & William Morris | 1888 | [1152](https://www.gutenberg.org/ebooks/1152) | 42/42 chapters |
| Grettis saga | George Ainslie Hight | 1914 | [347](https://www.gutenberg.org/ebooks/347) | 93/93 chapters |

**Not translated**: Skáldskaparmál and Háttatal are available in Old Norse only.

## Technical Notes

### Display Constraints
- **MAX_LINE_SIZE**: 2000 characters - lines longer than this won't render in the app
- Long prose paragraphs are automatically split at sentence boundaries
- All chapters use sequential 1-based line numbers for consistent display

### Speaker Detection
The Poetic Edda includes speaker tags (e.g., "Völundr kvað:", "Níðuðr kvað:") which are parsed and stored separately. Speakers appear in both Old Norse and English translations for dialogue poems like Alvíssmál and Völundarkviða.

### Prose Edda Structure
Chapter counts verified against [voluspa.org](https://www.voluspa.org/proseedda.htm):
- Prologus: 5 chapters
- Gylfaginning: 54 chapters
- Skáldskaparmál: 89 chapters
- Háttatal: 102 chapters

### Verse Citations
Gylfaginning and other Prose Edda sections contain embedded verse numbers (e.g., "8. Ór Élivágum...") that reference quotes from the Poetic Edda. These are preserved in the text for scholarly reference.

## License

- **Texts**: CC BY-SA 3.0 / Public Domain
- **Dictionary**: Public Domain

Commercial use is permitted with attribution.

### Attribution
```
Old Norse texts: Classical Language Toolkit (github.com/cltk/non_texts) - CC BY-SA 3.0 + Public Domain
Dictionary: "A Concise Dictionary of Old Icelandic" by Geir Zoëga (1910) - Public Domain + MIT
Morphology: IcePaHC Treebank (github.com/UniversalDependencies/UD_Icelandic-IcePaHC) - CC BY-SA 4.0
Translations: Project Gutenberg (gutenberg.org) - Public Domain
```

---

**Last Updated**: December 30, 2025
