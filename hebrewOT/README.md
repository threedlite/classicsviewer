# Hebrew Old Testament Lexicon for ClassicsViewer

This directory contains tools and data for creating a Hebrew lexicon package for the ClassicsViewer Android app.

## Generated Files

### hebrew_lexicon.zip (1.93 MB)
**Ready-to-import** lexicon package for ClassicsViewer app. Contains:
- `dictionary.csv`: 20,518 dictionary entries (BDB + Strong's)
- `morphology.csv`: 111,948 unique Hebrew word forms with lemma mappings
- `normalization_rules.csv`: Text normalization rules for matching vocalized Hebrew

### Intermediate Files
- `hebrew_dictionary.csv`: Dictionary entries before packaging
- `hebrew_morphology.csv`: Morphology mappings before packaging

## Data Sources

### 1. HebrewLexicon (OSHB Hebrew Lexicon)
**Location**: `../data-sources/HebrewLexicon/`
**License**: CC BY 4.0

Contains:
- **BrownDriverBriggs.xml**: Comprehensive BDB lexicon (11,845 entries)
- **HebrewStrong.xml**: Strong's Hebrew Dictionary (8,673 entries)
- **LexicalIndex.xml**: Cross-reference mappings
- **AugIndex.xml**: Augmented Strong's index

**Source**: https://github.com/openscriptures/HebrewLexicon

### 2. morphhb (Open Scriptures Hebrew Bible)
**Location**: `../data-sources/morphhb/wlc/`
**License**: CC BY 4.0 (morphology); Public Domain (WLC text)

Contains:
- 39 OSIS XML files (one per Hebrew Bible book)
- Complete morphological tagging for ~527,000 words
- Lemma attributes with augmented Strong's numbers
- Westminster Leningrad Codex vocalized text

**Source**: https://github.com/openscriptures/morphhb

## Usage

### To Generate the Lexicon Package

```bash
cd hebrewOT
python3 create_hebrew_lexicon.py
```

This will:
1. Parse Strong's Hebrew Dictionary (HebrewStrong.xml)
2. Parse Brown-Driver-Briggs Lexicon (BrownDriverBriggs.xml)
3. Extract morphology from all 39 Hebrew Bible books
4. Generate `hebrew_dictionary.csv` and `hebrew_morphology.csv`
5. Package into `hebrew_lexicon.zip`

### To Import into ClassicsViewer App

1. **Copy** `hebrew_lexicon.zip` to your Android device
2. **Open** ClassicsViewer app
3. **Navigate** to Settings → Dictionary Import
4. **Select** `hebrew_lexicon.zip`
5. **Import** - data populates `dictionary_entries`, `lemma_map`, and `normalization_patterns` tables

## Normalization Rules

The package includes normalization rules to enable dictionary lookups even when Hebrew text contains vocalization marks (nikud) or uses final letter forms.

### What It Does

When you click on a Hebrew word in the text:
1. **Text has vocalization**: "דָּבָר" (with nikud)
2. **App applies normalization**: Removes nikud → "דבר"
3. **Dictionary lookup**: Finds "דבר" = "word, thing" ✅

### Rules Applied

1. **Remove nikud** (priority 1): Strips all vocalization marks (`\u0591-\u05C7`)
2. **Normalize final forms** (priority 2-6):
   - ך → כ (final kaf to regular kaf)
   - ם → מ (final mem to regular mem)
   - ן → נ (final nun to regular nun)
   - ף → פ (final pe to regular pe)
   - ץ → צ (final tsadi to regular tsadi)

This allows dictionary entries stored in unvocalized form to match vocalized text from Hebrew Bible sources.

## CSV Format

### dictionary.csv
```csv
lemma,language,definition,html_definition,source_name
אָב,hebrew,"father, in a literal and immediate...",,Strong's H1
בָּרָא,hebrew,"to create, form, fashion...",,BDB (a.ac.ab)
```

Fields:
- **lemma**: Hebrew word (vocalized)
- **language**: Always "hebrew"
- **definition**: Plain text definition
- **html_definition**: HTML-formatted definition (optional)
- **source_name**: "Strong's H####" or "BDB (entry.id)"

### morphology.csv
```csv
word_form,lemma,morph_info,language,confidence,source_name
בְּרֵאשִׁית,7225,HR/Ncfsa,hebrew,1.0,OSHB morphhb
בָּרָא,1254 a,HVqp3ms,hebrew,1.0,OSHB morphhb
```

Fields:
- **word_form**: Hebrew word as it appears in text (vocalized)
- **lemma**: Strong's number or lexical reference
- **morph_info**: Morphological code (H=Hebrew, V=Verb, N=Noun, etc.)
- **language**: Always "hebrew"
- **confidence**: 1.0 (high confidence from OSHB)
- **source_name**: Always "OSHB morphhb"

## Statistics

- **Dictionary Entries**: 20,518 total
  - Strong's Hebrew Dictionary: 8,673 entries
  - Brown-Driver-Briggs: 11,845 entries
- **Morphology Mappings**: 111,948 unique word forms
- **Package Size**: 1.93 MB compressed
- **Uncompressed Size**: ~8.6 MB

## Morphology Code Reference

The `morph_info` field uses morphhb morphological codes:

**First Letter (Language)**:
- `H` = Hebrew
- `A` = Aramaic

**Second Letter (Part of Speech)**:
- `V` = Verb
- `N` = Noun
- `A` = Adjective
- `R` = Preposition
- `C` = Conjunction
- `T` = Particle
- `D` = Adverb

**Additional Codes** (varies by POS):
- Verb: stem (q=Qal, p=Piel, h=Hiphil), tense, person, number, gender
- Noun: type, gender, number, state (a=absolute, c=construct)

**Example**: `HVqp3ms`
- H = Hebrew
- V = Verb
- q = Qal stem
- p = Perfect tense
- 3 = 3rd person
- m = Masculine
- s = Singular

## Attribution

This lexicon data is derived from:

1. **Open Scriptures Hebrew Bible Project** (morphhb)
   - CC BY 4.0 for lemma and morphology
   - Public Domain for Westminster Leningrad Codex text
   - https://github.com/openscriptures/morphhb

2. **OSHB Hebrew Lexicon Project** (HebrewLexicon)
   - CC BY 4.0 for lexicon compilation
   - Public Domain for original BDB and Strong's content
   - https://github.com/openscriptures/HebrewLexicon

## Technical Notes

### Encoding
- All files use UTF-8 encoding
- Hebrew text includes full vocalization (nikud)
- Right-to-left text rendering required in app

### Deduplication
- Morphology mappings are deduplicated across all 39 books
- Same word form appearing in multiple verses is stored once

### Lemma Format
- Strong's numbers used as lemma identifiers
- Augmented Strong's (e.g., "1254 a") for disambiguation
- Prefixes/suffixes stripped to get base lemma

### Limitations
- Morphology codes are stored as-is (not fully decoded)
- BDB definitions truncated to 500 characters (very long entries)
- Some rare forms may have generic morphology tags

## Future Enhancements

- [ ] Decode morphology codes into human-readable descriptions
- [ ] Add transliteration (Hebrew → Latin characters)
- [ ] Include semantic domain classifications
- [ ] Add Hebrew grammar parsing information
- [ ] Link related lemmas (synonyms, antonyms)
- [ ] Include root etymology information
- [ ] Add usage frequency statistics
