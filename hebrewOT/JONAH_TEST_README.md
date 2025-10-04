# Hebrew Old Testament Test Database - Book of Jonah

This is a test implementation containing only the book of Jonah (4 chapters, 48 verses) from the Open Scriptures Hebrew Bible (OSHB).

## Output Files

### 1. Hebrew Text Database
- **`hebrew_texts.db`** (300 KB) - Uncompressed SQLite database
- **`hebrew_texts.db.zip`** (45 KB) - Compressed for distribution
- **Compression ratio:** 84.9%

### 2. Hebrew Lexicon Package
- **`hebrew_lexicon.zip`** (160 KB) - Dictionary and morphology data for app import
  - Contains `dictionary.csv` (8,674 entries from Strong's Hebrew Dictionary)
  - Contains `morphology.csv` (554 unique word forms from Jonah)

### 3. Intermediate Files (for review)
- **`hebrew_texts.csv`** - Human-readable text data (750 lines)
- **`hebrew_dictionary.csv`** - Dictionary entries before packaging
- **`hebrew_morphology.csv`** - Morphology mappings before packaging

## Database Contents

### Statistics
- **Authors (Bible books):** 1 (Jonah)
- **Works:** 1
- **Books (chapters):** 4
  - Chapter 1: 16 verses
  - Chapter 2: 11 verses
  - Chapter 3: 10 verses
  - Chapter 4: 11 verses
- **Text lines (verses):** 48
- **Individual words:** 688
- **Unique word forms:** 554

### Schema
The database follows the exact same schema as the main Perseus database:
- `authors` - One entry per Bible book
- `works` - One work per Bible book
- `books` - One entry per chapter
- `text_lines` - One entry per verse (includes Hebrew text and OSIS XML)
- `words` - Individual Hebrew words with positions
- `translation_segments` - (empty for now, reserved for future English translations)
- `translation_lookup` - (empty for now)

### Sample Data
**Jonah 1:1** (וַֽיְהִי֙ דְּבַר־יְהוָ֔ה אֶל־יוֹנָ֥ה)
- Hebrew text: "Now the word of the LORD came to Jonah"
- Contains full OSIS XML with lemma and morphology attributes for each word

## Data Sources

### 1. morphhb (Text & Morphology)
- **Source:** Open Scriptures Hebrew Bible
- **License:** CC BY 4.0 (morphology); Public Domain (WLC text)
- **URL:** https://github.com/openscriptures/morphhb
- **Content:**
  - Westminster Leningrad Codex (vocalized Hebrew text)
  - Word-by-word lemma tags (augmented Strong's numbers)
  - Morphological analysis (verb stems, noun forms, etc.)

### 2. HebrewLexicon (Dictionary)
- **Source:** OSHB Hebrew Lexicon Project
- **License:** CC BY 4.0
- **URL:** https://github.com/openscriptures/HebrewLexicon
- **Content:**
  - Strong's Hebrew Dictionary (8,674 entries)
  - Definitions and usage information

## Testing in Android App

### Option 1: Replace Main Database (Testing Only)
```bash
# NOT RECOMMENDED - This will replace your main database
cp hebrew_texts.db.zip app/src/debug/assets/perseus_texts.db.zip
```

### Option 2: Separate Hebrew Database (Recommended)
The app would need modification to support multiple databases. For now, this is a standalone test database that can be examined with SQLite tools.

### View Database Contents
```bash
# Extract database
unzip hebrew_texts.db.zip

# Query with sqlite3
sqlite3 hebrew_texts.db "SELECT * FROM authors"
sqlite3 hebrew_texts.db "SELECT line_number, line_text FROM text_lines WHERE book_id='oshb_jonah_001_ch01' LIMIT 5"
sqlite3 hebrew_texts.db "SELECT COUNT(*) FROM words"
```

## Importing Lexicon Data

The `hebrew_lexicon.zip` file follows the same format as `custom_dictionary/test_dictionary.zip` and can be imported via the Android app UI:

1. Copy `hebrew_lexicon.zip` to device
2. Open Classics Viewer app
3. Navigate to Dictionary Import
4. Select `hebrew_lexicon.zip`
5. Data will be imported into `dictionary_entries` and `lemma_map` tables

## Processing Script

**`process_hebrew_complete.py`** - Main script that:
1. Parses OSIS XML from morphhb
2. Extracts Hebrew text, lemmas, and morphology
3. Creates SQLite database following existing schema
4. Extracts dictionary entries from HebrewLexicon XML
5. Generates morphology mappings
6. Packages CSVs into ZIP for app import
7. Compresses database for distribution

### Usage
```bash
# Process only Jonah (this test)
python3 process_hebrew_complete.py Jonah

# Process all 39 books (future)
python3 process_hebrew_complete.py
```

## Data Mapping

| Hebrew Concept | Database Field | Example |
|----------------|----------------|---------|
| Book (Jonah) | `authors.name` + `works.title` | "Jonah (OSHB)" |
| Chapter | `books.book_number` | 1, 2, 3, 4 |
| Verse | `text_lines.line_number` | 1, 2, 3... |
| Hebrew text | `text_lines.line_text` | "וַֽיְהִי֙ דְּבַר־יְהוָ֔ה" |
| OSIS XML | `text_lines.line_xml` | Full XML with lemma/morph |
| Word | `words.word` | "וַֽיְהִי֙" |
| Word position | `words.word_position` | 1, 2, 3... |

## Verification

All outputs have been verified:
- ✅ Database integrity check: PASSED
- ✅ ZIP file integrity: PASSED
- ✅ CSV format: Valid UTF-8
- ✅ Hebrew text rendering: Preserved vocalization (nikud)
- ✅ Chapter/verse counts: Match expected (48 verses total)
- ✅ Foreign key relationships: Valid
- ✅ Sequence numbers: Continuous

## Next Steps

1. ✅ Test database created with Jonah only
2. ⏭️ Test in Android app (requires app modification for separate Hebrew DB)
3. ⏭️ Process remaining 38 books
4. ⏭️ Add English translations (ESV, NASB, etc.)
5. ⏭️ Integrate with main app database selection

## Attribution

When using this data, please include attribution:

**Text and Morphology:**
- Open Scriptures Hebrew Bible Project
- License: CC BY 4.0 (morphology), Public Domain (WLC text)
- URL: https://github.com/openscriptures/morphhb

**Dictionary:**
- OSHB Hebrew Lexicon Project
- License: CC BY 4.0
- URL: https://github.com/openscriptures/HebrewLexicon
