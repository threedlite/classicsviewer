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
3. Parses all sagas and Eddas
4. Creates SQLite database with dictionary
5. Compresses to `norse_texts.db.zip`

## Language Notes

Old Icelandic IS Old Norse - specifically the Old West Norse dialect. The terms are used interchangeably because:

1. Most surviving Old Norse literature (sagas, Eddas) was written in Iceland
2. "Old Norse" is the umbrella term; "Old Icelandic" is the specific western dialect
3. Icelandic has changed so little that modern Icelanders can still read the sagas

All resources are compatible and share the same lexicon.

## Contents

### Texts

| Source | License | Content |
|--------|---------|---------|
| [CLTK Old Norse texts](https://github.com/cltk/non_texts) | CC BY-SA 3.0 + public domain | Eddas, 30+ sagas |

**Included works:**
- **Poetic Edda** (Sæmundar-Edda): Voluspa, Havamal, Lokasenna, Grimnismal, etc.
- **Prose Edda** (Snorra-Edda): Snorri Sturluson's masterwork
- **Major Sagas**: Grettis saga, Volsunga saga, Hrolf Kraki, Ragnar Lothbrok, etc.
- **Þættir**: Short tales (Norna-Gest, etc.)

### Dictionary

| Source | License | Entries |
|--------|---------|---------|
| [Zoega's Old Icelandic Dictionary](https://github.com/stscoundrel/old-icelandic-zoega) | Public domain (1910) + MIT | 29,951 |

"A Concise Dictionary of Old Icelandic" by Geir Zoëga (1910) - the standard reference dictionary, loved by Tolkien and Lewis.

### Morphology (Treebank)

| Source | License | Mappings |
|--------|---------|----------|
| [IcePaHC Treebank](https://github.com/UniversalDependencies/UD_Icelandic-IcePaHC) | CC BY-SA 4.0 | 65,793 |

Form→lemma mappings with morphological features (case, number, gender, definiteness). Examples:
- `menn` → `maður` (Nom Plural)
- `konungs` → `konungur` (Gen Sing)
- `konungana` → `konungur` (Acc Plural Definite)

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

### Texts
- **Repository**: https://github.com/cltk/non_texts
- **License**: CC BY-SA 3.0 (Perseus texts) + Public Domain (Heimskringla texts)
- **Format**: Plain text files organized by work/chapter

### Dictionary
- **Repository**: https://github.com/stscoundrel/old-icelandic-zoega
- **Original**: "A Concise Dictionary of Old Icelandic" (1910)
- **License**: Public Domain (original) + MIT (JSON conversion)
- **Format**: JSON with `{word, definitions}` structure

## No Translations

Unlike Greek/Latin/Pali, the Old Norse texts do not include aligned English translations. The texts are in original Old Norse only.

Potential future addition:
- Some sagas have public domain English translations that could be aligned

## License

- **Texts**: CC BY-SA 3.0 / Public Domain
- **Dictionary**: Public Domain

Commercial use is permitted with attribution.

### Attribution
```
Old Norse texts: Classical Language Toolkit (cltk.org)
Dictionary: "A Concise Dictionary of Old Icelandic" by Geir Zoëga (1910)
```

---

**Last Updated**: December 2025
