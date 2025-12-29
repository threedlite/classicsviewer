# Syriac Database

This module creates a SQLite database of Syriac texts for use in ClassicsViewer.

## Data Source

**Patristic Text Archive (PTA)**: https://pta.bbaw.de

**Digital Syriac Corpus**: https://syriaccorpus.org

The texts are obtained from the PTA repository which hosts TEI XML editions of Syriac texts from the Digital Syriac Corpus.

## License Compliance

Only **CC-BY 4.0** and **CC-BY-SA 4.0** licensed texts are included.

### Excluded - Non-Commercial License (CC-BY-NC 4.0)
The following are **excluded** due to non-commercial license restrictions:
- ETCBC Peshitta texts (65 files) - Old Testament in Syriac

### Included Texts (CC-BY 4.0 / CC-BY-SA 4.0)

#### Syriac New Testament (Digital Syriac Corpus) - CC-BY 4.0
All 27 books of the New Testament in Syriac (Peshitta):
- **Gospels**: Matthew, Mark, Luke, John
- **Acts**: Acts of the Apostles
- **Pauline Epistles**: Romans, 1-2 Corinthians, Galatians, Ephesians, Philippians, Colossians, 1-2 Thessalonians, 1-2 Timothy, Titus, Philemon, Hebrews
- **General Epistles**: James, 1-2 Peter, 1-3 John, Jude
- **Apocalyptic**: Revelation

## Usage

```bash
# Ensure PTA data is cloned to data-sources/pta_data/
cd ../data-sources
git clone https://github.com/PatristicTextArchive/pta_data.git

# Run the database creation script
cd ../syriac
python3 create_syriac_database.py
```

## Output

| File | Size | Description |
|------|------|-------------|
| `syriac_texts.db` | ~23 MB | SQLite database |
| `syriac_texts.db.zip` | ~4 MB | Compressed database |

## Database Statistics

| Metric | Count |
|--------|-------|
| Authors | 3 |
| Works | 27 |
| Books/Chapters | 260 |
| Text lines (verses) | 7,958 |
| Words | 123,157 |

## Content Details

### Syriac New Testament Structure
- **Matthew**: 28 chapters
- **Mark**: 16 chapters
- **Luke**: 24 chapters
- **John**: 21 chapters
- **Acts**: 28 chapters
- **Romans**: 16 chapters
- **1 Corinthians**: 16 chapters
- **2 Corinthians**: 13 chapters
- **Galatians**: 6 chapters
- **Ephesians**: 6 chapters
- **Philippians**: 4 chapters
- **Colossians**: 4 chapters
- **1 Thessalonians**: 5 chapters
- **2 Thessalonians**: 3 chapters
- **1 Timothy**: 6 chapters
- **2 Timothy**: 4 chapters
- **Titus**: 3 chapters
- **Philemon**: 1 chapter
- **Hebrews**: 13 chapters
- **James**: 5 chapters
- **1 Peter**: 5 chapters
- **2 Peter**: 3 chapters
- **1 John**: 5 chapters
- **2 John**: 1 chapter
- **3 John**: 1 chapter
- **Jude**: 1 chapter
- **Revelation**: 22 chapters

## Database Schema

The database uses the same schema as other ClassicsViewer language databases (Greek, Latin, Coptic, Dante):

- `authors` - Author information
- `works` - Work metadata
- `books` - Chapters
- `text_lines` - Syriac text (verses)
- `words` - Individual words with positions
- `translation_segments` - Translations (if available)
- `lemma_map` - Word form to lemma mappings

## TEI XML Format

The script parses TEI XML files with the following structure:
- `<div type="edition" xml:lang="syc">` - Syriac text
- `<div subtype="chapter" n="1">` - Chapter divisions
- `<div subtype="verse" n="1">` - Verse divisions
- `<p>` - Verse text content

## Credits

- **Digital Syriac Corpus**: https://syriaccorpus.org
- **Patristic Text Archive**: https://pta.bbaw.de
- **Editor**: James E. Walters (TEI XML edition)
- **Source**: The Peshitta New Testament

## Syriac Lexicon Status

**No Syriac lexicon is currently included** due to licensing restrictions.

### Available Syriac Lexicons

| Resource | Format | License | Status |
|----------|--------|---------|--------|
| **SEDRA III** | Text files | Academic/non-commercial only | Not compatible |
| **SEDRA IV** | API only | Apache 2.0 | No downloadable files |
| **Payne Smith Thesaurus Syriacus** (1879-1901) | Scanned images | Public domain | Would require OCR |
| **Compendious Syriac Dictionary** (1903) | Scanned images | Public domain | Would require OCR |

### Details

- **SEDRA (Syriac Electronic Data Research Archive)**: The primary Syriac linguistic database with 3,465 roots, 35,812 lexemes, and 64,922 words. However, SEDRA III has a restrictive license: "personal and academic purposes only, no redistribution for profit." SEDRA IV is available via API (Apache 2.0) but not as downloadable files.
  - Website: https://sedra.bethmardutho.org/
  - GitHub (JS conversion): https://github.com/peshitta/sedrajs

- **Payne Smith's Thesaurus Syriacus**: The classic Syriac-Latin dictionary (1879-1901) is public domain but only available as scanned images on Internet Archive. Converting to machine-readable format would require significant OCR work.
  - Internet Archive: https://archive.org/details/Thesaurus-Syriacus

- **Compendious Syriac Dictionary** (1903): An abridged English version of Payne Smith, also public domain but image-only.
  - Internet Archive: https://archive.org/details/CompendiousSyriacDictionary1903

### Future Options

1. **SEDRA IV API**: Could potentially fetch lexicon data via API during build (Apache 2.0 licensed)
2. **OCR Payne Smith**: Digitize the public domain dictionary (significant project)
3. **Community contribution**: Wait for openly-licensed Syriac lexicon data

## Notes

The syriaca-data repository (`data-sources/syriaca-data`) contains metadata about Syriac literature (bibliography, persons, places, works catalog) but not actual text content. The actual Syriac texts are obtained from the PTA repository.
