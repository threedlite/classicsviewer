# Hebrew Language Data Source Integration Plan

## Overview
Add Hebrew language support to the Classics Viewer app, following the existing database schema patterns. This will integrate two CC-BY-SA licensed Hebrew data sources into a SQLite database format compatible with the Android app.

## Key Implementation Points

1. **Use Existing Schema**: Database schema is FIXED - no modifications allowed
2. **Follow New Testament Pattern**: Structure mirrors `process_new_testament_text()` in `create_perseus_database.py`
   - Bible book → author + work
   - Chapter → book entry
   - Verse → text_line entry
3. **Dictionary CSV Import**: Use `custom_dictionary/` CSV pattern for BDB/Strong's lexicon
   - Create `hebrew_lexicon.zip` containing `dictionary.csv` + `morphology.csv`
   - ZIP format matches `custom_dictionary/test_dictionary.zip`
   - User imports via app UI → `dictionary_entries` and `lemma_map` tables
4. **OSIS XML Storage**: Store full morphology in `text_lines.line_xml` field (same as NT Greek)
5. **Separate Deliverables**:
   - `hebrew_texts.db.zip` - Text database
   - `hebrew_lexicon.zip` - Dictionary package (dictionary.csv + morphology.csv)
6. **No External Modifications**: All code stays in `hebrewOT/` folder - cannot modify files outside this directory

## Data Sources

### 1. morphhb (Open Scriptures Hebrew Bible)
- **Location**: `data-sources/morphhb/`
- **License**: CC BY 4.0 (lemma/morphology); Public Domain (text)
- **Format**: OSIS XML files in `wlc/` directory
- **Content**:
  - Complete Hebrew Bible (39 books)
  - Vocalized Hebrew text (Westminster Leningrad Codex)
  - Lemma attributes (augmented Strong's numbers)
  - Morphological tagging for every word
  - Unique word IDs for cross-referencing
- **Structure**:
  ```xml
  <w lemma="c/m/6529" morph="HC/R/Ncmsc" id="018xz">הֶחָכְמָה</w>
  ```

### 2. HebrewLexicon (OSHB Hebrew Lexicon)
- **Location**: `data-sources/HebrewLexicon/`
- **License**: CC BY 4.0
- **Format**: XML files
- **Content**:
  - **BrownDriverBriggs.xml**: Comprehensive BDB lexicon entries
  - **HebrewStrong.xml**: Strong's Hebrew Dictionary (corrected)
  - **LexicalIndex.xml**: Mapping between BDB, Strong's, and TWOT numbers
  - **AugIndex.xml**: Maps augmented Strong's to lexical index IDs
- **Purpose**: Dictionary/lexicon lookup for lemmas

## Architecture Pattern (Based on Cuneiform)

### Directory Structure
```
hebrewOT/
├── HEBREW_DATASOURCE_PLAN.md (this file)
├── hebrew_texts.db (SQLite output - text data only)
├── hebrew_texts.db.zip (compressed for distribution)
├── hebrew_texts.csv (intermediate review format)
├── hebrew_dictionary.csv (BDB + Strong's entries - intermediate)
├── hebrew_morphology.csv (word→lemma mappings - intermediate)
├── hebrew_lexicon.zip (packaged CSVs for app import)
│   ├── dictionary.csv (BDB + Strong's entries)
│   └── morphology.csv (word→lemma mappings)
├── process_hebrew_complete.py (main processing script)
├── LICENSE_ADDITIONS.md (attribution requirements)
└── README.md (usage documentation)
```

**Note**: Dictionary CSVs must be packaged in a ZIP file (like `custom_dictionary/test_dictionary.zip`) for app import.

### Database Schema (MUST USE EXISTING SCHEMA - NO CHANGES ALLOWED)

**CRITICAL**: The schema is already defined and used by the Android app. We MUST map Hebrew data to this existing structure:

```sql
-- Authors table: Use one author per Hebrew Bible book
CREATE TABLE authors (
    id TEXT PRIMARY KEY NOT NULL,           -- e.g., "oshb_genesis", "oshb_exodus"
    name TEXT NOT NULL,                     -- e.g., "Genesis (OSHB)", "Exodus (OSHB)"
    name_alt TEXT,                          -- Hebrew book name
    language TEXT NOT NULL,                 -- "hebrew"
    has_translations INTEGER DEFAULT 0      -- 0 (no English translations initially)
);

-- Works table: Each book is a work
CREATE TABLE works (
    id TEXT PRIMARY KEY NOT NULL,           -- e.g., "oshb_genesis_001"
    author_id TEXT NOT NULL,                -- References authors.id
    title TEXT NOT NULL,                    -- English book title
    title_alt TEXT,                         -- Hebrew book title
    title_english TEXT,                     -- English book title (same as title)
    type TEXT,                              -- "biblical_text"
    urn TEXT,                               -- OSHB reference/URL
    description TEXT,                       -- Book description
    FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
);

-- Books table: Each chapter is a "book"
CREATE TABLE books (
    id TEXT PRIMARY KEY NOT NULL,           -- e.g., "oshb_genesis_001_ch01"
    work_id TEXT NOT NULL,                  -- References works.id
    book_number INTEGER NOT NULL,           -- Chapter number (1, 2, 3...)
    label TEXT,                             -- "Chapter 1", "Chapter 2"
    start_line INTEGER,                     -- First verse number
    end_line INTEGER,                       -- Last verse number
    line_count INTEGER,                     -- Total verses in chapter
    FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE
);

-- Text lines table: Each verse is a "line"
CREATE TABLE text_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    book_id TEXT NOT NULL,                  -- References books.id (chapter)
    line_number INTEGER NOT NULL,           -- Verse number
    sequence_number INTEGER NOT NULL,       -- Continuous sequence
    line_text TEXT NOT NULL,                -- Full Hebrew text of verse
    line_xml TEXT,                          -- OSIS XML with morphology (lemma/morph attributes)
    speaker TEXT,                           -- NULL for Hebrew Bible
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

-- Translation segments: Future - English translations if available
CREATE TABLE translation_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    book_id TEXT NOT NULL,
    start_line INTEGER NOT NULL,           -- Starting verse
    end_line INTEGER,                      -- Ending verse (same as start for verse-by-verse)
    sequence_number INTEGER,
    translation_text TEXT NOT NULL,        -- English translation
    translator TEXT,                       -- Version info (e.g., "ESV", "NASB")
    speaker TEXT,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

-- Words table: Individual Hebrew words with morphology
CREATE TABLE words (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    word TEXT NOT NULL,                    -- Hebrew word (vocalized)
    book_id TEXT NOT NULL,                 -- Chapter reference
    line_number INTEGER NOT NULL,          -- Verse number
    sequence_number INTEGER NOT NULL,      -- Global sequence
    word_position INTEGER NOT NULL,        -- Position within verse (1-based)
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

-- Translation lookup: Maps verses to translation segments
CREATE TABLE translation_lookup (
    book_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    segment_id INTEGER NOT NULL,
    PRIMARY KEY (book_id, line_number, segment_id),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (segment_id) REFERENCES translation_segments(id) ON DELETE CASCADE
);

-- Standard indexes (from cuneiform schema)
CREATE INDEX idx_authors_language ON authors(language);
CREATE INDEX idx_works_author ON works(author_id);
CREATE INDEX idx_books_work ON books(work_id);
CREATE INDEX idx_text_lines_book ON text_lines(book_id);
CREATE INDEX idx_text_lines_sequence ON text_lines(book_id, sequence_number);
CREATE INDEX idx_translation_segments_book ON translation_segments(book_id);
CREATE INDEX idx_translation_segments_lines ON translation_segments(book_id, start_line);
CREATE INDEX idx_words_word ON words(word);
CREATE INDEX idx_words_book_line_seq ON words(book_id, line_number, sequence_number);
CREATE INDEX index_translation_lookup_book_id_line_number ON translation_lookup(book_id, line_number);
CREATE INDEX index_translation_lookup_segment_id ON translation_lookup(segment_id);
```

### Mapping Hebrew Concepts to Schema

| Hebrew Concept | Schema Field | Example |
|----------------|--------------|---------|
| Book of Bible | `authors.name` + `works.title` | "Genesis (OSHB)" |
| Chapter | `books` (one per chapter) | Chapter 1 = book_number 1 |
| Verse | `text_lines.line_number` | Verse 1 |
| Hebrew Text | `text_lines.line_text` | "בְּרֵאשִׁית בָּרָא אֱלֹהִים" |
| OSIS XML with lemma/morph | `text_lines.line_xml` | Full `<w lemma="..." morph="...">` XML |
| Individual words | `words.word` | "בְּרֵאשִׁית" |
| Word position | `words.word_position` | 1, 2, 3... |

### Lexicon Data Storage Strategy

Lexicon data uses existing `dictionary_entries` and `lemma_map` tables. The OSIS XML in `line_xml` field contains lemma/morph attributes that reference the dictionary:

```xml
<!-- Example line_xml structure (OSIS format from morphhb) -->
<verse xmlns="..." osisID="Gen.1.1">
  <w lemma="c/b/7225" morph="HR/Ncfsa" id="01abc">בְּרֵאשִׁית</w>
  <w lemma="c/1254a" morph="HVqp3ms" id="01def">בָּרָא</w>
  <w lemma="c/430" morph="HNcmpa" id="01ghi">אֱלֹהִים</w>
</verse>
```

Dictionary lookups:
- Lemma attribute (e.g., "c/1254a") → `lemma_map` table → dictionary entry
- Morph attribute provides grammatical info (Verb Qal perfect 3ms, etc.)

### New Testament Pattern (Reference)

Hebrew Bible structure mirrors the New Testament Greek approach in `process_new_testament_text()`:
- **NT**: Gospel → work, Chapter → book, Verse → text_line
- **OT**: Bible book → work, Chapter → book, Verse → text_line

Both use chapter/verse organization with OSIS XML format in `line_xml` field.

## Implementation Steps

### Phase 1: Text Extraction (process_hebrew_complete.py)

1. **Parse OSIS XML files** from `morphhb/wlc/`
   - Extract book name, chapter, verse structure
   - Parse each `<w>` element for:
     - Hebrew text content
     - `lemma` attribute (augmented Strong's)
     - `morph` attribute (morphological code)
     - `id` attribute (unique word ID)
   - Track word position within each verse

2. **Map to existing schema**:
   - **Authors table**: Create one author entry per book
     - `id`: "oshb_genesis", "oshb_exodus", etc.
     - `name`: "Genesis (OSHB)", "Exodus (OSHB)"
     - `name_alt`: Hebrew book name (e.g., "בְּרֵאשִׁית")
     - `language`: "hebrew"
     - `has_translations`: 0

   - **Works table**: One work per book
     - `id`: "oshb_genesis_001"
     - `author_id`: "oshb_genesis"
     - `title`: English book name
     - `title_alt`: Hebrew book name
     - `type`: "biblical_text"

   - **Books table**: One book per CHAPTER
     - `id`: "oshb_genesis_001_ch01", "oshb_genesis_001_ch02"
     - `work_id`: "oshb_genesis_001"
     - `book_number`: Chapter number (1, 2, 3...)
     - `label`: "Chapter 1", "Chapter 2"
     - `start_line`: First verse number
     - `end_line`: Last verse number
     - `line_count`: Total verses

   - **Text_lines table**: One line per VERSE
     - `book_id`: Chapter reference
     - `line_number`: Verse number
     - `line_text`: Full Hebrew text (concatenated words)
     - `line_xml`: Original OSIS XML with all `<w>` elements and attributes

   - **Words table**: Individual Hebrew words
     - `word`: Hebrew word (vocalized)
     - `book_id`: Chapter reference
     - `line_number`: Verse number
     - `word_position`: Position within verse (1-based)

3. **Generate CSV intermediate format**
   - Columns: book_code, chapter, verse, sequence_number, hebrew_text, xml_content
   - Allow for manual review before database import
   - Similar to cuneiform's `sumerian_texts.csv` / `akkadian_texts.csv`

4. **Populate database tables**
   - Import CSV data into SQLite following existing schema
   - Validate data integrity (no missing lemmas, morphology)

### Phase 2: Lexicon Extraction (Using CSV Import Pattern)

The database already has `dictionary_entries` and `lemma_map` tables (from `load_combined_dictionaries.py`). Create Hebrew lexicon CSVs following the `custom_dictionary/` pattern:

**1. Create intermediate CSV files**:

`hebrew_dictionary.csv` (for BDB + Strong's entries):
```csv
lemma,language,definition,html_definition,source_name
אָב,hebrew,"father, progenitor","<div>father, progenitor</div>","BDB (a.ab.aa)"
אָב,hebrew,"Etymology: fresh, bright; freshness","<div>Etymology: fresh, bright</div>","BDB (a.ab.ab)"
בָּרָא,hebrew,"to create, form, fashion","<div>to create, form, fashion</div>","Strong's H1254"
```

`hebrew_morphology.csv` (morphology mappings):
```csv
word_form,lemma,morph_info,language,confidence,source_name
בְּרֵאשִׁית,רֵאשִׁית,"noun common feminine singular construct",hebrew,1.0,"OSHB morphhb"
בָּרָא,בָּרָא,"verb qal perfect 3ms",hebrew,1.0,"OSHB morphhb"
אֱלֹהִים,אֱלֹהִים,"noun common masculine plural absolute",hebrew,1.0,"OSHB morphhb"
```

**2. Package CSVs into ZIP** (matching `custom_dictionary/test_dictionary.zip` format):
```bash
# Rename files to match expected format
cp hebrew_dictionary.csv dictionary.csv
cp hebrew_morphology.csv morphology.csv

# Create ZIP package
zip hebrew_lexicon.zip dictionary.csv morphology.csv

# Clean up temporary files
rm dictionary.csv morphology.csv
```

**3. Package and Import Process** (following existing pattern):
- Parser extracts from HebrewLexicon XML files → generates CSVs
- CSVs are packaged into `hebrew_lexicon.zip` containing:
  - `dictionary.csv` (BDB + Strong's entries)
  - `morphology.csv` (word→lemma mappings)
- ZIP file follows same format as `custom_dictionary/test_dictionary.zip`
- User imports `hebrew_lexicon.zip` via Android app UI
- Data goes into existing `dictionary_entries` and `lemma_map` tables
- **No files outside hebrewOT/ can be modified!**

### Phase 3: Database Finalization

1. **Create indexes** for efficient lookup (per existing schema - already done by create_perseus_database.py)
2. **Run integrity checks**:
   - Verify all chapters have correct verse counts
   - Check foreign key relationships
   - Validate XML in line_xml field
3. **Compress database** to `.zip` for distribution:
   - `hebrew_texts.db.zip` (text data only - no dictionary)
4. **Package dictionary CSVs** into ZIP for user import:
   - Generate `hebrew_dictionary.csv` and `hebrew_morphology.csv`
   - Create `hebrew_lexicon.zip` containing renamed files:
     - `dictionary.csv` (from hebrew_dictionary.csv)
     - `morphology.csv` (from hebrew_morphology.csv)
   - Format matches `custom_dictionary/test_dictionary.zip`
5. **Generate statistics**:
   - 39 books (authors)
   - ~929 chapters (books)
   - ~23,145 verses (text_lines)
   - ~527,000 words
   - Database size (uncompressed/compressed)
   - CSV row counts (dictionary entries, morphology mappings)

## Key Differences from Cuneiform

### Similarities
- **Exact same database schema** (authors, works, books, text_lines, words, etc.)
- CSV intermediate format for review
- SQLite database output
- Compression for distribution
- Attribution requirements in LICENSE_ADDITIONS.md

### Schema Mapping Differences
1. **Text Structure**:
   - Cuneiform: tablet/column → books table, line → text_lines
   - Hebrew: chapter → books table, verse → text_lines

2. **Granularity**:
   - Cuneiform: Works have sections/tablets (multiple books per work)
   - Hebrew: Each Bible book is one work, chapters are books

3. **Morphology Storage**:
   - Cuneiform: Transliteration in line_text
   - Hebrew: Vocalized Hebrew in line_text, full OSIS XML with lemma/morph in line_xml

4. **Lexicon Integration**:
   - Hebrew lexicon data provided as CSV files
   - User imports via Android app UI (not programmatic)
   - Follows custom_dictionary CSV format
   - Text database and dictionary CSVs are separate deliverables

5. **Multiple Data Sources**:
   - Hebrew integrates 2 repos (morphhb + HebrewLexicon)
   - Cuneiform uses single source per language

## Technical Considerations

### Encoding
- Hebrew text is UTF-8 encoded
- Must preserve vocalization marks (nikud)
- Avoid NFC normalization (per OSHB documentation)
- Test that Android displays Hebrew right-to-left correctly

### Performance
- 39 books × average ~30 chapters × average ~30 verses × average ~15 words ≈ 527,000 words
- Expected database size: ~50-80MB uncompressed, ~15-25MB compressed
- Index all foreign keys and lookup columns

### Data Validation
1. **Required fields**: Every verse must have valid line_text and line_xml
2. **Foreign key integrity**: All book_id references must be valid
3. **Sequence numbers**: Must be continuous and unique
4. **Chapter/verse ranges**: Validate against known book structures (e.g., Genesis has 50 chapters)
5. **XML validation**: line_xml must be well-formed OSIS XML

## Attribution Requirements (LICENSE_ADDITIONS.md)

Must credit:
1. **Open Scriptures Hebrew Bible Project** (morphhb)
   - CC BY 4.0 for lemma and morphology
   - Public Domain for WLC text
   - URL: https://github.com/openscriptures/morphhb

2. **OSHB Hebrew Lexicon Project** (HebrewLexicon)
   - CC BY 4.0 for lexicon work
   - Public Domain for original BDB and Strong's
   - URL: https://github.com/openscriptures/HebrewLexicon

## Testing Strategy

1. **Unit Tests**:
   - XML parsing functions
   - Database insertion/retrieval
   - Lemma lookup resolution

2. **Integration Tests**:
   - Full pipeline from XML to database
   - Lexicon linking validation
   - Query performance benchmarks

3. **Manual Verification**:
   - Check sample verses (Genesis 1:1, Psalm 23:1, Isaiah 53:5)
   - Verify dictionary lookups work for common words
   - Validate Hebrew rendering (right-to-left, vocalization)

## Future Enhancements

1. **Translations**: Add English translations (multiple versions)
2. **Parsing**: Add Hebrew grammar/syntax parsing visualization
3. **Cantillation**: Leverage OSHB cantillation hierarchy data
4. **Cross-references**: Link related verses
5. **Search**: Full-text search in Hebrew and transliteration
6. **Lexical Analysis**: Word frequency, semantic domains

## Success Criteria

- [ ] All 39 Hebrew Bible books imported successfully as authors/works
- [ ] All ~929 chapters imported as books entries
- [ ] All ~23,145 verses imported as text_lines entries
- [ ] All ~527,000 words imported into words table
- [ ] Each text_line has valid line_text (Hebrew) and line_xml (OSIS with morphology)
- [ ] Foreign key relationships validate (authors → works → books → text_lines)
- [ ] Sequence numbers are continuous and correct
- [ ] Database size is reasonable (<100MB uncompressed for text, <50MB for lexicon)
- [ ] CSV intermediate format is human-readable for review
- [ ] Attribution requirements properly documented
- [ ] Database validates on SQLite integrity check
- [ ] Test queries complete in <100ms on modern hardware
- [ ] Hebrew text displays correctly (right-to-left, vocalization preserved)

## References

### Cuneiform Examples
- `cuneiform/process_sumerian_complete.py` - CSV generation and database population
- `cuneiform/process_akkadian_complete.py` - Multi-source text processing
- `cuneiform/README.md` - Documentation pattern

### Hebrew Resources
- morphhb README.md - Data structure documentation
- HebrewLexicon readme.md - Lexicon organization
- OSHB XML Schema files (`.xsd`) - Validation rules

## Timeline Estimate

- **Phase 1** (Text Extraction): 2-3 days
  - Parse morphhb OSIS XML
  - Map to authors/works/books/text_lines schema
  - Generate intermediate CSV
- **Phase 2** (Lexicon Extraction): 2-3 days
  - Parse HebrewLexicon XML files
  - Generate dictionary.csv and morphology.csv
  - Import to dictionary_entries and lemma_map tables
- **Phase 3** (Finalization & Testing): 1-2 days
  - Integrity checks
  - Test on Android
  - Verify Hebrew rendering and dictionary lookups
- **Total**: ~5-8 days for complete implementation

## Implementation Notes

- **No modifications outside hebrewOT/**: Cannot modify any files in data-prep/, app/, or other folders
- **No silent failures**: Script should fail loudly on missing data or parsing errors
- **General solutions only**: No word-specific fixes; handle all cases systematically
- **Standalone implementation**: All code must be in `hebrewOT/` folder
- **Test early**: Validate small samples before processing all 39 books
- **Document assumptions**: XML structure, encoding, required fields
- **Follow NT Greek pattern**: Reference `process_new_testament_text()` at line 3864 in create_perseus_database.py
- **Use custom_dictionary CSV format**: Reference CSV format in custom_dictionary/dictionary.csv and morphology.csv
- **Dictionary import via UI**: CSVs are imported by user through Android app, not programmatically
- **Avoid NFC normalization**: Per OSHB documentation, preserve Hebrew vocalization marks

## Quick Start Guide

1. **Study existing code**:
   - `data-prep/create_perseus_database.py` lines 3864-3942 (NT processing)
   - `custom_dictionary/dictionary.csv` and `morphology.csv` (CSV formats)
   - `cuneiform/process_sumerian_complete.py` (similar workflow pattern)

2. **Create parser**: `hebrewOT/process_hebrew_complete.py`
   - Parse morphhb OSIS XML → CSV → SQLite
   - Parse HebrewLexicon XML → dictionary/morphology CSVs
   - Follow cuneiform pattern for structure

3. **Test with sample book** (e.g., Ruth - short, only 4 chapters)
   - Verify chapter/verse mapping
   - Check OSIS XML in line_xml field
   - Test dictionary lookups

4. **Scale to all 39 books**
   - Process Torah, Prophets, Writings
   - Verify statistics match expectations (~23K verses, ~527K words)
   - Compress database to .zip

5. **Deliver final outputs**:
   - `hebrew_texts.db.zip` - Database with text data
   - `hebrew_lexicon.zip` - Dictionary package for UI import (contains dictionary.csv + morphology.csv)
   - `README.md` - Instructions for importing both database and dictionary via app
   - `LICENSE_ADDITIONS.md` - Attribution requirements
