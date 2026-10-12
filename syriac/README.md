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

#### Patristic Text Archive Syriac editions - CC-BY-SA 4.0
- John of Ephesus, *Ecclesiastical History*, Part 3 (Books 1-6; English
  translation of Book 1, chapters 3-42)
- Michael the Syrian, *Testimonies to John of Ephesus's Ecclesiastical
  History* (English translation of 8 testimonia)
- Anonymous, *Testimonies ... from the Chronicle of 1234*
- Severianus of Gabala, *In theophaniam* and *Homilia de nativitate* (Syriac
  versions; the PTA's English translation of *In theophaniam* renders the
  Church Slavonic version, and the Syriac has only a German translation, so
  neither is imported)
- Eusebius of Caesarea, *Prologi varii* (Syriac version)

The English translations are by Philip Michael Forness, Silvio Roggo,
Hartmut Leppin and Nikolai Kiel (PTA, CC BY-SA 4.0).

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
| `syriac_texts.db` | ~30 MB | SQLite database |
| `syriac_texts.db.zip` | ~7 MB | Compressed database |

## Database Statistics

| Metric | Count |
|--------|-------|
| Authors | 6 |
| Works | 33 |
| Books/Chapters | 568 |
| Text lines (verses / sentences) | 13,056 |
| Words | 190,459 |
| Translation segments (PTA English) | 45 |

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

Biblical files (chapters with `verse` divs) give one book per chapter and one
line per verse. Prose editions give one book per **leaf textpart div** (a
chapter, section or testimonium); the book id and label carry the whole
path, e.g. `john_of_ephesus_pta0200_pta001.3_1_3` / "Part 3 Book 1 Chapter
3", so that the same chapter number in different books cannot collide (until
2026-10-12 it did, and John of Ephesus lost 59% of his paragraphs). The
paragraphs of a leaf are split into sentence lines at a full stop or the
Syriac end-of-paragraph mark.

Running text keeps the accepted apparatus reading (`<lem>`) and drops
rejected readings (`<rdg>`), notes and erased text (`<del>`); `<ref>` and
`<bibl>` stay because the PTA files put quoted scripture and work titles
inside them.

### PTA translations

Each PTA work directory has a `__cts__.xml` that lists its translations with
a `dct:relation` naming the edition translated. For every Syriac edition the
build imports the English (`eng`/`en`) translations related to it that are
under CC BY / CC BY-SA, as one `translation_segments` row per translated
leaf div covering all lines of the matching Syriac book (matched by the same
path), plus `translation_lookup` rows. A translated passage with no matching
Syriac book fails the build. Authors with a translation get
`has_translations = 1`. Translations in other languages are not imported.

## Credits

- **Digital Syriac Corpus**: https://syriaccorpus.org
- **Patristic Text Archive**: https://pta.bbaw.de
- **Editor**: James E. Walters (TEI XML edition)
- **Source**: The Peshitta New Testament

## Syriac Lexicon

The build imports the **Classical Syriac entries of the English Wiktionary**
(CC BY-SA 3.0) into `dictionary_entries` and `lemma_map`, source
`Wiktionary (syc)`. As of the April 2026 dump Wiktionary has about 2,600
Classical Syriac lemmas and 240 non-lemma forms, so coverage of the corpus is
partial; it is the only openly licensed machine-readable Syriac lexicon found
(see "Other Syriac lexicons" below).

### How it is built (all inside `create_syriac_database.py`)

1. **Dump scan.** `data-sources/enwiktionary-latest-pages-articles.xml.bz2`
   is scanned once for pages with a Syriac-script title and a
   `==Classical Syriac==` section; they are cached in
   `all_syriac_enwiktionary_pages.json` (git-ignored, about 5 minutes to create,
   skipped when present). The build fails if neither the cache nor the dump
   exists, or if the scan finds nothing.
2. **Parsing.** Each Classical Syriac section is split into part-of-speech
   senses (`===Noun===`, `====Verb====` under an etymology, …). The headword
   template gives gender and transliteration (`tr=`) and any `pl=` / `f=`
   forms; `#` lines become numbered definitions with templates rendered
   (`{{lb}}` labels in parentheses, `{{l}}`/`{{m}}` links as words,
   `{{inflection of}}` and `alternative form of` as cross-references);
   `===References===` lines become a "References" line (Payne Smith 1902,
   Sokoloff 2009, Costaz 1963, CAL, …).
3. **Dictionary rows.** One `dictionary_entries` row per page that has at
   least one real definition (`entry_html` and `entry_plain`;
   `headword_normalized_ultra` is the consonantal skeleton).
4. **Lemma map.** Rows for the headword itself, for `pl=`/`f=` forms, for
   every `{{inflection of}}` / alternative-form page, and then for **every
   distinct word form in the corpus** whose skeleton (vowel points, reading
   marks and punctuation removed) matches a headword or a cross-referenced
   form (confidence 0.9 / 0.85). Forms that only match after removing a
   proclitic (ܘ, ܕ, ܒ, ܠ and their combinations) are mapped with
   confidence 0.7 and `morph_info` "with proclitic ܘ-". The corpus mapping is
   what makes vowel-pointed text resolve: the app looks up `lemma_map` by the
   exact word form, and most forms in the Peshitta texts carry vowel points.
5. The build prints the entry, definition and lemma-map counts and the share
   of corpus word tokens that resolve to an entry.

### Other Syriac lexicons (checked 2026-10-11, none usable)

| Resource | Format | License | Status |
|----------|--------|---------|--------|
| **SEDRA III** | Text files | Personal/academic use; no redistribution of altered versions | Not compatible (import is an altered version) |
| **SEDRA IV** | API only | API spec Apache 2.0; data licence not stated | No downloadable files |
| **Payne Smith Thesaurus Syriacus** (1879-1901) | Scanned images | Public domain | OCR is not used in this project |
| **Compendious Syriac Dictionary** (1903) | Scanned images | Public domain | OCR is not used; the Digital Syriac Corpus has an unpublished electronic edition |
| **Comprehensive Aramaic Lexicon (CAL)** | Online | Not stated | No download |

- SEDRA: https://sedra.bethmardutho.org/ (licence text in https://github.com/peshitta/sedrajs/blob/master/LICENSE)
- Payne Smith: https://archive.org/details/Thesaurus-Syriacus, https://archive.org/details/CompendiousSyriacDictionary1903

## Notes

The syriaca-data repository (`data-sources/syriaca-data`) contains metadata about Syriac literature (bibliography, persons, places, works catalog) but not actual text content. The actual Syriac texts are obtained from the PTA repository.
