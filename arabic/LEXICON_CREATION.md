# Lane's Arabic-English Lexicon Processing

## Overview

This directory contains the script to convert Lane's Arabic-English Lexicon from Perseus TEI XML format into ClassicsViewer's custom dictionary format.

## Script

**File:** `create_arabic_lexicon.py`

**Purpose:** Parse Lane's Lexicon XML files and create a CSV dictionary compatible with ClassicsViewer's database schema.

## Usage

```bash
cd arabic
python3 create_arabic_lexicon.py
```

## Output

**File:** `arabic_dictionary.csv`
**Format:** CSV with columns:
- `lemma`: Arabic headword (root form)
- `language`: "arabic"
- `definition`: Plain text definition (truncated to 500 chars)
- `html_definition`: HTML formatted definition with Arabic text preserved
- `source_name`: "Lane's Lexicon"

**Statistics:**
- Total entries: **43,940**
- File size: **26 MB**
- Source: 36 XML files from Lane's Lexicon

## Input Data

**Source:** `data-sources/arabic_text_perseus/Lane/opensource/*.xml`
**License:** CC BY-SA 3.0 (Perseus Digital Library)
**Original:** Lane's Arabic-English Lexicon (8 volumes, 1863-1893)

## Processing Details

### XML Structure
Lane's Lexicon uses TEI XML format with:
- `<entryFree type="main">` - Main dictionary entries
- `<orth lang="ar">` - Arabic headwords (lemmas)
- `<foreign lang="ar">` - Arabic text within definitions
- `<hi rend="ital">` - Italicized English text

### Extraction Logic

1. **Headword Extraction**
   - Finds `<orth lang="ar">` tags within each entry
   - Skips placeholder entries (marked with `*`)
   - Uses first valid Arabic headword as lemma

2. **Definition Extraction**
   - **Plain text**: Strips all XML tags, extracts pure text
   - **HTML**: Converts TEI formatting to HTML
     - `<hi rend="ital">` → `<i>`
     - `<foreign lang="ar">` → `<span class='arabic'>`
   - Truncates both to 500 characters to avoid extremely long entries

3. **Deduplication**
   - Removes duplicate lemmas (keeps first occurrence)
   - 44,828 raw entries → 43,940 unique entries

## Sample Entries

```csv
lemma,language,definition,html_definition,source_name
ماء,arabic,"Water; salt water...",<div>Water; <i>salt water...</i></div>,Lane's Lexicon
```

## Known Issues

1. **Transliteration in Headwords**: Some headwords use transliteration (e.g., `$uw^obuwbN`) instead of Arabic script. This is how Perseus encoded the lexicon.

2. **Definition Length**: Entries are truncated to 500 chars to keep database size manageable. Full definitions available in original XML files.

3. **HTML Formatting**: Simple conversion - advanced formatting like tables, cross-references may not render perfectly.

## Integration with Database

This CSV file will be imported during database creation:

1. Load `arabic_dictionary.csv`
2. Apply normalization rules from `custom_dictionary/normalization_rules_arabic.csv`
3. Insert into `custom_dictionaries` table
4. Create lookup indexes for word matching

## License

**Script:** MIT License (part of ClassicsViewer)
**Data:** CC BY-SA 3.0 (Perseus Digital Library)
- Must credit Perseus Digital Library
- Must credit U.S. Department of Education and Max Planck Society
- Must offer Perseus any modifications

## Next Steps

- [ ] Test dictionary integration with database build
- [ ] Verify word lookup functionality with Arabic text
- [ ] Add Arabic text parser for Mu'allaqa poem
- [ ] Test end-to-end: text → word → dictionary lookup
