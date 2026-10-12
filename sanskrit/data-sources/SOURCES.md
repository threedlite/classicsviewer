# Sanskrit Data Sources Documentation

This document lists all source files in this directory and where they were downloaded from.

## Bhagavad Gita

### Sanskrit Text (18 chapters, 700 verses)
**Source**: Sanskrit Wikisource
**Base URL**: https://sa.wikisource.org/wiki/भगवद्गीता
**License**: CC BY-SA 4.0
**Download Date**: October 4, 2025
**Files**: `bhagavad_gita_sa_*.html` (18 files: bhagavad_gita_sa_1.html through bhagavad_gita_sa_18.html)
**Download Script**: `download_bhagavad_gita_sanskrit.sh`
**Parser**: `parse_bhagavad_gita_sanskrit.py`
**Parsed Output**: `bhagavad_gita_sanskrit.json`

**URL Pattern**:
- Chapter 1: https://sa.wikisource.org/wiki/भगवद्गीता/अर्जुनविषादयोगः
- Chapter 2: https://sa.wikisource.org/wiki/भगवद्गीता/साङ्ख्ययोगः
- ...
- Chapter 18: https://sa.wikisource.org/wiki/भगवद्गीता/मोक्षसंन्यासयोगः

### English Translation 1: Arnold (18 chapters, prose format)
**Source**: English Wikisource
**Translator**: Edwin Arnold (1885)
**Base URL**: https://en.wikisource.org/wiki/The_Bhagavad_Gita_(Arnold_translation)
**License**: Public Domain
**Download Date**: October 4, 2025
**Files**: `bhagavad_gita_en_*.html` (18 files: bhagavad_gita_en_1.html through bhagavad_gita_en_18.html)
**Download Script**: `download_bhagavad_gita_english.sh`
**Parser**: `parse_bhagavad_gita_english.py`
**Parsed Output**: `bhagavad_gita_english.json`

**URL Pattern**:
- Chapter 1: https://en.wikisource.org/wiki/The_Bhagavad_Gita_(Arnold_translation)/Chapter_1
- Chapter 2: https://en.wikisource.org/wiki/The_Bhagavad_Gita_(Arnold_translation)/Chapter_2
- ...
- Chapter 18: https://en.wikisource.org/wiki/The_Bhagavad_Gita_(Arnold_translation)/Chapter_18

**Note**: Arnold's translation is in prose format, not verse-by-verse. Each chapter is a continuous narrative.

### English Translation 2: Besant (18 chapters, 700 verses)
**Source**: English Wikisource
**Translator**: Annie Besant (1922, 4th edition)
**Base URL**: https://en.wikisource.org/wiki/Bhagavad-Gita_(Besant_4th)
**License**: Public Domain
**Download Date**: October 4, 2025
**Files**: `bhagavad_gita_besant_*.html` (18 files: bhagavad_gita_besant_1.html through bhagavad_gita_besant_18.html)
**Download Script**: `download_bhagavad_gita_besant.sh`
**Parser**: `parse_bhagavad_gita_besant.py`
**Parsed Output**: `bhagavad_gita_besant.json`

**URL Pattern**:
- Discourse 1: https://en.wikisource.org/wiki/Bhagavad-Gita_(Besant_4th)/Discourse_1
- Discourse 2: https://en.wikisource.org/wiki/Bhagavad-Gita_(Besant_4th)/Discourse_2
- ...
- Discourse 18: https://en.wikisource.org/wiki/Bhagavad-Gita_(Besant_4th)/Discourse_18

**Note**: Besant's translation is verse-by-verse, with each of the 700 verses translated individually.

## Rig Veda

The Sanskrit text is the DCS pada file (`../../data-sources/sanskrit/dcs/data/rigveda/pada-and-analysis.dat`,
CC BY 4.0). This directory holds only the English translation.

### English Translation: Griffith (10 books, 1,028 hymns, stanza by stanza)
**Source**: English Wikisource, *The Hymns of the Rigveda* (2nd ed., 1896)
**Translator**: Ralph T.H. Griffith
**License**: Public Domain translation; Wikisource contributions CC BY-SA
**Base URL**: https://en.wikisource.org/wiki/The_Hymns_of_the_Rigveda
**Files**: `wikisource/rigveda/book<N>_hymn<M>.html` (1,028 rendered pages, fetched through the MediaWiki API)
**Download Script**: `download_rigveda_griffith.py` (discovers the hymn pages with the API; resumes if interrupted)
**Parser**: `parse_rigveda_griffith.py`
**Parsed Output**: `wikisource/rigveda_griffith.txt` (`book.hymn.stanza text`, one line per stanza; `;;; deity` header per hymn)
The build runs download and parse itself when the parsed file is missing;
the folder is git-ignored.

**Structure**: most pages are plain transcriptions (a `<pre>` block or
paragraphs, each stanza starting with its number); four are proofread
transclusions (`ws-poem-stanza` blocks with `ws-poem-versenum`). Footnote
markers and the footnote list are dropped. Griffith prints the eleven
Vālakhilya hymns as an appendix after 8.92; the parser renumbers them
8.49–8.59 and shifts 8.49–8.92 to 8.60–8.103, the numbering the DCS uses.
Stanzas Griffith left untranslated (5.55.8, 8.82.29, 10.48.7, 10.61.5–9,
10.86.16–17, 10.132.5) and hymn 1.179 (editorial note only) have no
translation; misprinted stanza numbers (1.91, 5.44) are read as the expected
number. The parser reports each case and fails if a book's hymn numbers have
gaps or a stanza number runs backwards. Result: 10,504 stanzas; 48 of the
10,551 DCS stanzas are without translation, mostly where Griffith counts
the dvipadā hymns 1.65–1.70 as five stanzas each against the DCS's ten.

## Chāndogya Upaniṣad

The Sanskrit text is the DCS Chāndogyopaniṣad (CC BY 4.0). This directory
holds only the English translation.

### English Translation: Müller (8 prapāṭhakas, 153 khaṇḍas, 619 verses)
**Source**: English Wikisource, *Sacred Books of the East*, vol. 1 (1879), Khândogya-upanishad
**Translator**: F. Max Müller
**License**: Public Domain translation; Wikisource contributions CC BY-SA
**Base URL**: https://en.wikisource.org/wiki/Sacred_Books_of_the_East/Volume_1/Khândogya-upanishad
**Files**: `mueller/chandogya_<1-8>.html` (one rendered page per prapāṭhaka)
**Download Script**: `download_chandogya_mueller.sh`
**Parser**: `parse_chandogya_mueller.py`
**Parsed Output**: `mueller/chandogya_mueller.txt` (`prapathaka.khanda.verse text`; a verse range Müller
renders as one unit keeps its label, e.g. `2.13.1-2`)
The build runs download and parse itself when the parsed file is missing;
the folder is git-ignored.

**Structure**: khaṇḍas begin at `<span id="KhandaN">` anchors; verses are
paragraphs beginning `N.`; footnote markers and the footnote list are
dropped. The parser fails on any gap in khaṇḍa or verse numbering. Müller's
khaṇḍa 7.26 has no DCS counterpart (the DCS has 25 khaṇḍas in prapāṭhaka 7)
and is reported by the build as unwritten.

## Translations registered in `translation_sources.py`

`translation_sources.py` holds one entry per DCS work: where the English
translation comes from (Project Gutenberg or English Wikisource), its
translator and licence, and a parser that turns the fetched text into rows
`book<TAB>chapter<TAB>verse<TAB>text` using the DCS labels of that work.
The build fetches and parses each registered work it includes when the
parsed file is missing; fetched pages are cached under `generated/` (git-
ignored), and `python3 translation_sources.py --check` compares every
parser's keys with the DCS chapter labels without touching the database.
One segment is written per DCS chapter whose label the translation names.

| DCS work | Translation | Source | Alignment | Coverage |
|---|---|---|---|---|
| Rāmāyaṇa | Manmatha Nath Dutt, prose (1891–94) | Gutenberg 57265, 57826, 60188, 62496 | Per sarga, via `ramayana_dutt.py`: each critical-edition sarga is paired with the vulgate sarga (Sanskrit Wikisource रामायणम्) that shares its first verse (similarity ≥ 0.85 on the normalised first 40 characters, largest monotonic matching); Dutt's section n is the vulgate's sarga n in the kāṇḍas where his section count equals the vulgate's sarga count; elsewhere the section at the same proportional position, round(v·D/V) | Bāla, Araṇya, Kiṣkindhā (counts equal): 194 sargas, exact. Ayodhyā, Sundara, Yuddha, Uttara: Dutt's counts (118, 67, 130, 124) differ from the vulgate's (119, 68, 128, 111), so the section is chosen by proportional position and every English segment in these kāṇḍas begins with a note saying the alignment is approximate and why |
| Viṣṇupurāṇa | M. N. Dutt after Wilson | Gutenberg 66208 | Part and section = DCS book and chapter | 126 of 126 chapters |
| Saddharmapuṇḍarīkasūtra | Hendrik Kern, SBE 21 (1884) | Wikisource | Chapter = DCS book | 18 of 18 DCS chapters (Kern has 27) |
| Atharvaveda (Śaunaka) | W. D. Whitney (1905) | Wikisource, 588 hymn and paryāya pages | Book, hymn, stanza = DCS labels (Whitney's numbering, with his vulgate numbers in parentheses in Book VII; the title line of each hymn is skipped) | 518 of 519 DCS hymns; the page for 7.109 was never transcribed; of Whitney's book 19 the DCS has three hymns, and none of book 20 |
| Kathāsaritsāgara | C. H. Tawney (1880–84) | Wikisource, 124 chapter pages | Tawney's continuous chapters are renumbered within each lambaka from his BOOK headings, matching the DCS taraṅga labels | 44 of 44 DCS chapters (the DCS has 44 of 124) |
| Arthaśāstra | R. Shamasastry (1915) | Wikisource, 15 book pages | Book and chapter; a combined heading ("CHAPTER I & II") serves both chapters | 60 of 60 DCS chapters matched; 59 written, chapter 1.1 having no DCS lines |
| Kāmasūtra | Burton and Arbuthnot (1883) | Wikisource | Part and chapter = DCS book and chapter | 36 of 36 |
| Suśrutasaṃhitā | K. L. Bhishagratna (1907–16) | Wikisource, 42 chapter pages | Volume's section name = DCS section label (Sū., Utt.) | 42 of 186 (what Wikisource has) |
| Yogasūtra | Charles Johnston (1912) | Gutenberg 2526 | Book; numbered sūtras, Johnston's commentary paragraphs dropped | 4 of 4 books, 193 sūtras |
| Kumārasaṃbhava | R. T. H. Griffith (1853) | Gutenberg 31968 | Canto, unnumbered stanzas | 7 of 8 cantos |
| Gītagovinda | Edwin Arnold (adaptation) | Gutenberg 25965 | Sarga, from the body headings in capitals | 11 of 12 sargas |
| Sarvadarśanasaṃgraha | Cowell and Gough (1882) | Gutenberg 34125 | Cowell's chapter IX = the DCS's single chapter (Rāseśvaradarśana) | 1 of 1 |
| Hitopadeśa | Edwin Arnold, abridged | Gutenberg 13268 | Introduction and four books in order = DCS books 0–4 | 5 of 5 |

Works surveyed and not registered: Harivaṃśa (Dutt's 300-odd vulgate
chapters have no mechanical correspondence to the 118 critical-edition
adhyāyas), Meghadūta (Ouvry's 115 stanzas against the DCS's 122, with no
marked Pūrva/Uttara split), Daśakumāracarita (Jacob's stories are not the
ucchvāsa division), Vetālapañcaviṃśatikā (the DCS has only the introduction),
Yājñavalkyasmṛti (Montriou covers one book with commentary interleaved).

## Mahabharata

The Sanskrit text is the DCS Mahābhārata (critical-edition numbering, CC BY
4.0), loaded like every other DCS work. This directory holds only the
English translation and the table that attaches it to the Sanskrit.

### English Translation: Ganguli (18 books, 2,106 section units)
**Source**: Project Gutenberg
**Translator**: Kisari Mohan Ganguli (1883–1896), prose
**License**: Public Domain (translator died 1908; Gutenberg marks the texts "Public domain in the USA")
**Download Date**: October 9, 2026
**Files**: `ganguli/pg15474.txt` (Books 1–3), `ganguli/pg15475.txt` (Books 4–7),
`ganguli/pg15476.txt` (Books 8–12), `ganguli/pg15477.txt` (Books 13–18); 15.3 MB
**Download Script**: `download_ganguli.sh` — the build runs it itself when the
files are missing, so they are not checked in (`sanskrit/.gitignore`)
**Parser**: `../mahabharata_ganguli.py` (imported by the build, not a script)

**URLs**:
- https://www.gutenberg.org/cache/epub/15474/pg15474.txt
- https://www.gutenberg.org/cache/epub/15475/pg15475.txt
- https://www.gutenberg.org/cache/epub/15476/pg15476.txt
- https://www.gutenberg.org/cache/epub/15477/pg15477.txt

**Verification**: the build keeps only the text between the `*** START OF`
and `*** END OF` lines (Project Gutenberg's terms require removing its
header, licence and name) and checks a SHA-256 of that text against the
value recorded in `mahabharata_ganguli.py`. A changed Gutenberg file fails
the build until the hash is re-checked and updated.

**Structure found in the files**: `BOOK n` headings for Books 1–18;
`SECTION <roman>` headings in Books 1–7 and 12–15, a bare arabic number on
its own line in Books 8–11 and 16–18; footnotes numbered per book, cited
inline as `[n]` and listed after `FOOTNOTES` at the end of the book. Eight
section headings are missing from the transcription (1.177, 2.67, 7.54,
7.55, 7.189, 12.34, 12.35, 12.364); their text stays with the preceding
section, which is then attached to the chapters of both numerals.

### Concordance: critical edition → Ganguli section
**Source**: "Appendix: Concordance of Critical Edition and Ganguli/Roy
translation", in S. Brodbeck and B. Black (eds), *Gender and Narrative in the
Mahābhārata*, Routledge 2007, pp. 279–284. The PDF of the appendix was
posted to the INDOLOGY list on 2019-07-02:
https://list.indology.info/pipermail/indology/attachments/20190702/f7d5e428/attachment.pdf
**File**: `mbh_ce_ganguli_concordance.csv` (checked in; 397 rows, 189 of
them verse-level, 3 marked `?` by the authors)
**Script**: `extract_mbh_concordance.py` — reads the PDF with its page
coordinates, assigns each row to the left or right column, recovers the
spacing the extraction loses in 25 rows from the only reading that keeps the
critical-edition chapters contiguous, and verifies that every book is
covered from chapter 1 to its last chapter. Rerun it only to regenerate the
CSV; the PDF is not stored in the repository.

**How the table is used** (`../mahabharata_ganguli.py`): a section is
attached to the chapters the table pairs it with; a section the table pairs
with a verse range of a chapter is attached to that whole chapter, so a
section straddling two chapters is attached to both; a section the table
does not mention is attached to the run of chapters between its nearest
mentioned neighbours; a chapter no section is attached to is covered by
extending the neighbouring sections to it. One row (13.99 → 58) is out of
order in the printed table and is not used.

## License Summary

All sources used are properly licensed for commercial use:

| Source | License | Commercial Use | Attribution |
|--------|---------|----------------|-------------|
| Sanskrit Wikisource - Bhagavad Gita | CC BY-SA 4.0 | ✅ Yes | Ancient text |
| English Wikisource - Arnold Translation | Public Domain | ✅ Yes | Edwin Arnold (1885) |
| English Wikisource - Besant Translation | Public Domain | ✅ Yes | Annie Besant (1922) |
| English Wikisource - Griffith Rig Veda | Public Domain | ✅ Yes | Ralph T.H. Griffith (1896) |
| English Wikisource - Müller Chāndogya Upaniṣad | Public Domain | ✅ Yes | F. Max Müller (1879) |
| Project Gutenberg - Ganguli Mahabharata | Public Domain | ✅ Yes | Kisari Mohan Ganguli (1883–1896) |
| Project Gutenberg - Dutt (Rāmāyaṇa, Viṣṇupurāṇa), Johnston, Griffith (Kumārasaṃbhava), Arnold (Gītagovinda, Hitopadeśa), Cowell & Gough | Public Domain | ✅ Yes | per `translation_sources.py` |
| English Wikisource - Kern, Whitney, Tawney, Shamasastry, Burton & Arbuthnot, Bhishagratna | Public Domain | ✅ Yes | per `translation_sources.py` |
| Sanskrit Wikisource - रामायणम् (vulgate, used only to pair sargas) | CC BY-SA | ✅ Yes | — |
| Brodbeck & Black concordance (chapter correspondences, as data) | factual table | ✅ Yes | cite the appendix |

## Statistics

**Tracked files**: 14 scripts and modules (download, parse, extract, `translation_sources.py`, `ramayana_dutt.py`), the concordance CSV, and this document.

**Downloaded (git-ignored) files**:
- Bhagavad Gita HTML: 18 Sanskrit + 18 Arnold + 18 Besant, and 3 parsed JSON files
- Ganguli Mahabharata text: 4 Gutenberg files in `ganguli/`
- Griffith Rig Veda: 1,028 hymn pages in `wikisource/rigveda/` and `wikisource/rigveda_griffith.txt`
- Müller Chāndogya: 8 pages in `mueller/` and `mueller/chandogya_mueller.txt`
- Registry translations: Gutenberg texts and Wikisource pages under `generated/`, parsed files `generated/<work>.tsv`, vulgate Rāmāyaṇa pages under `generated/ramayana/`

**Content**:
- Bhagavad Gita: 700 Sanskrit verses; Arnold prose (18 chapters); Besant verse by verse (700)
- Rig Veda: Griffith, 1,028 hymns, 10,504 stanzas (10,503 attached; one has no DCS stanza)
- Chāndogya Upaniṣad: Müller, 619 verses in 153 khaṇḍas; 151 segments written (DCS khaṇḍas 2.13 and 2.14 have no lines, Müller's 7.16 has no DCS counterpart)
- Mahabharata: Ganguli, 2,106 section units attached to the critical-edition chapters

## Notes

This folder contains the non-DCS source data for the Sanskrit text database (translations and the Gita text). For Sanskrit dictionary and morphology data, see the DCS (Digital Corpus of Sanskrit) lexicon in the parent directory:

- **Dictionary source**: `../dcs_sanskrit_lexicon.zip` (34 MB)
- **Coverage**: 88.0% on Bhagavad Gita vocabulary
- **License**: CC BY 4.0
- **Documentation**: See `../README.md` and `../DCS_LEXICON_DOCUMENTATION.md`
