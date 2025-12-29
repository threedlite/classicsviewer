# Coptic Scriptorium Database

This module creates a SQLite database of Coptic texts from the Coptic SCRIPTORIUM corpus for use in ClassicsViewer.

## Data Source

**Coptic SCRIPTORIUM**: https://copticscriptorium.org

Repository: https://github.com/CopticScriptorium/corpora.git

The corpus contains Sahidic and Bohairic Coptic texts with:
- Morphological annotations (lemmas, parts of speech)
- English translations
- Named entity annotations
- Syntactic parsing

## License Compliance

Most documents are licensed **CC-BY 3.0/4.0**. The following corpora are **excluded** due to incompatible licenses:

### Excluded - Restricted License (J Warren Wells)
These use a restricted "for academic use only" license:
- `sahidica.nt` - Sahidica New Testament
- `sahidica.mark` - Gospel of Mark (Sahidic)
- `sahidica.1corinthians` - 1 Corinthians (Sahidic)
- `coptic-treebank` - Contains duplicates from above

### Excluded - Non-Commercial License (CC-BY-NC)
- `life-aphou`
- `life-longinus-lucius`
- `life-paul-tamma`
- `life-phib`

### Included Licenses
All included corpora use one of:
- CC-BY 3.0
- CC-BY 4.0
- CC-BY-SA 3.0 (Canons of Apa Johannes)
- CC-BY-SA 4.0 (Sahidic Old Testament)

## Usage

```bash
# Ensure the corpus is cloned to data-sources/corpora/
cd ../data-sources
git clone https://github.com/CopticScriptorium/corpora.git

# Run the database creation script
cd ../coptic
python3 create_coptic_database.py
```

## Output

| File | Size | Description |
|------|------|-------------|
| `coptic_texts.db` | ~95 MB | SQLite database |
| `coptic_texts.db.zip` | ~22 MB | Compressed database |

## Database Statistics

| Metric | Count |
|--------|-------|
| Authors | 30 |
| Works | 60 |
| Books/Chapters | 409 |
| Text lines | 76,115 |
| Words | 655,809 |
| Translations | 18,604 |
| Dictionary entries | 11,284 |
| Lemma mappings | 43,524 |

## Included Content

### Major Authors/Collections
- **Shenoute** - 17 works (sermons, letters)
- **Apophthegmata Patrum** - 126 sayings of the Desert Fathers
- **Pistis Sophia** - 28 chapters of the Gnostic text
- **Besa** - Letters and exhortations
- **Pachomius** - Monastic instructions

### Biblical Texts (CC-BY-SA compatible)
- **Sahidic**: Jonah, Ruth
- **Bohairic**: Mark, 1 Corinthians, Habakkuk

### Hagiographies
- Life of Onnophrius
- Life of Pisentius
- Life of Cyrus
- Life of John Kalybites
- Life of Eustathius and Theopiste
- Martyrdom of Victor

### Other Texts
- Gospel of Thomas
- Acts of Pilate
- Book of Bartholomew
- Dormition of John
- Mysteries of John
- Lament of Mary
- Various pseudo-epigraphical homilies

## Database Schema

The database uses the same schema as other ClassicsViewer language databases (Greek, Latin, Sanskrit, Dante):

- `authors` - Author information
- `works` - Work metadata
- `books` - Chapters/sections
- `text_lines` - Coptic text lines
- `words` - Individual words with positions
- `translation_segments` - English translations
- `dictionary_entries` - Coptic lexicon entries with definitions
- `lemma_map` - Word form to lemma mappings
- `translation_lookup` - Line-to-translation mapping

## TT File Format

The script parses TreeTagger SGML (`.tt`) files which contain:
- `<meta>` - Document metadata (author, title, license, etc.)
- `<verse_n>` - Verse/section markers
- `<translation>` - English translations
- `<norm>` - Normalized word forms with lemma and POS attributes

## Coptic Lexicon

**The Comprehensive Coptic Lexicon is integrated** into the database (CC-BY-SA 4.0 license).

### Comprehensive Coptic Lexicon

| Resource | Format | License | Status |
|----------|--------|---------|--------|
| **Comprehensive Coptic Lexicon v1.2** | TEI XML | CC-BY-SA 4.0 | **Integrated** |

### Details

The **Comprehensive Coptic Lexicon** is a combination of:
- **BBAW Lexicon of Coptic Egyptian** - Egyptian-origin Coptic words from Berlin-Brandenburgische Akademie der Wissenschaften
- **DDGLC Lexicon of Greek Loanwords in Coptic** - Greek loanwords from Freie Universität Berlin

### Content
- **11,284 entries** with definitions in English, French, and German
- **15,735 word forms** mapped to lemmas
- Includes ~8,000 Egyptian-Coptic lemmata and ~3,250 Greek-Coptic lemmata
- Morphological information and etymologies
- Linked to Thesaurus Linguae Aegyptiae (TLA) IDs

### Data Sources
- **Local file**: `data-sources/Comprehensive_Coptic_Lexicon-v1.2-2020.xml` (~12 MB TEI XML)
- **GitHub Repository**: https://github.com/KELLIA/dictionary
- **Online Dictionary**: https://coptic-dictionary.org/
- **DOI**: 10.17169/refubium-2333

### Project Partners (KELLIA)
- Berlin-Brandenburg Academy of Sciences (BBAW)
- Georgetown University
- University of Göttingen
- University of Münster
- University of the Pacific

## Credits

- **Coptic SCRIPTORIUM Project**: https://copticscriptorium.org
- **Coptic Dictionary Online**: https://coptic-dictionary.org/ (KELLIA project)
- **Annotations**: Various scholars (see individual file metadata)
- **Translations**: World English Bible (biblical texts), various scholars (other texts)
