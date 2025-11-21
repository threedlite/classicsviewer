# Kiwix ZIM File Generation for Classics Viewer

## What is Kiwix?

Kiwix is an offline reader for web content, designed to make knowledge available to people with limited or no internet access. It reads ZIM files, which are highly compressed archives containing websites or other content. Kiwix is widely used for:
- Wikipedia offline access
- Educational content in remote areas
- Digital libraries and archives
- Emergency preparedness resources

The Kiwix ecosystem includes:
- **Kiwix readers**: Available for Windows, macOS, Linux, Android, and iOS
- **Kiwix Serve**: A local web server to share ZIM content on a network
- **ZIM format**: An open, standardized file format for storing compressed web content

Learn more at [kiwix.org](https://www.kiwix.org)

## Classical Viewer Library ZIM

This directory contains tools to create a Kiwix ZIM file from the Perseus Classical Library database, providing offline access to ancient Greek and Latin texts with translations and dictionary lookups, including LSJ, Cunliffe and Wiktionary.

Installation:

Install Kiwix app first https://kiwix.org/en/.

For mobile, install from App Store (Apple or Google). Copy the zim file to the phone in the existing Kiwix folder which should be in internal storage. For Android it might something like /storage/emulated/0/Android/media/org.kiwix.kiwixmobile/

Install the Classics Viewer zim file library (sample or full) into Kiwix using file selector.

### Content Overview

The ZIM file contains:
- **Sample database**: 10 Greek authors + 2 Latin authors (278 works, 705 books)
- **Full database**: 88 Greek authors + 40 Latin authors (999 works, 2,563 books)
- **Extended database**: All Perseus + 991 non-duplicate First1KGreek works
- Complete texts with aligned translations
- **Interlinear translations**: Word-by-word translations with morphology for Homer's Iliad and Odyssey
- Advanced translation alignment supporting Bekker numbering, section-based texts, and offset translations
- Comprehensive dictionary with 61,070+ entries from LSJ, Cunliffe, and Wiktionary
- Morphological information showing grammatical forms
- Hierarchical navigation (Language → Author → Work → Book)
- Responsive HTML with CSS styling optimized for offline reading
- Multi-script support (Greek, Latin, Sanskrit, Arabic, Hebrew, Persian, Akkadian, Sumerian)

## Requirements

- Python 3.8+
- SQLite3
- Perseus database (`perseus_texts_sample.db`, `perseus_texts_full.db`, or `perseus_texts_extended.db`)
- Python libzim library (for ZIM creation)
- ~300MB disk space for sample, ~1.5GB for full database, ~5GB for extended

## Installation

### 1. Set up Python virtual environment
```bash
cd kiwix
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Python dependencies
```bash
pip install libzim
```

## Usage

### Quick Build (Sample Database)

```bash
cd kiwix
./build_sample_clean.sh
```

This creates `classicsviewer_sample.zim` (~951MB) containing:
- 12 authors (10 Greek, 2 Latin)
- 913,993 dictionary entries
- 1,711 text pages
- Interlinear translations for Homer's Iliad and Odyssey

Build time: ~15 minutes total (3.7 min content generation + 11 min ZIM packaging)

### Full Database Build

For the complete 128 author database:
```bash
cd kiwix
./build_full_clean.sh
```

This creates `classicsviewer_full.zim` containing 88 Greek and 40 Latin authors.

### Extended Database Build

For Perseus + First1KGreek (991 additional works):
```bash
cd kiwix
./build_extended_clean.sh
```

This creates `classicsviewer_extended.zim` containing 391 total authors and 1,849 works.

### Language-Specific Builds

To create smaller ZIM files for individual languages from the extended database:

```bash
cd kiwix
./build_by_language.sh <language>
```

Available languages:
- `greek` - Greek texts only (Perseus + First1K Greek authors)
- `latin` - Latin texts only (Perseus Latin authors)
- `sanskrit` - Sanskrit texts only
- `arabic` - Arabic texts only
- `hebrew` - Hebrew texts only
- `persian` - Persian texts only
- `akkadian` - Akkadian texts only
- `sumerian` - Sumerian texts only
- `all` - Build all language ZIMs sequentially

Example:
```bash
./build_by_language.sh greek
```

This creates `classicsviewer_greek.zim` containing only Greek texts, translations, and dictionary entries.

## Features

### Interlinear Translations

The ZIM files include word-by-word interlinear translations for select works:
- **Homer's Iliad**: All 24 books with word/gloss/morphology
- **Homer's Odyssey**: All 24 books with word/gloss/morphology
- More works being added

Access interlinear via the translation dropdown:
1. Navigate to a work with interlinear data (e.g., Homer → Iliad → Book 1)
2. In the translation panel, select "Interlinear (Beta, AI-generated from app dictionary)"
3. View word-by-word breakdowns with:
   - **Word**: The Greek word in its original form
   - **Gloss**: English translation/meaning
   - **Morph**: Grammatical information (case, number, gender, tense, etc.)

### Dictionary System
- **61,070+ dictionary entries** from LSJ (Liddell-Scott-Jones), Cunliffe's Homeric lexicon, and Wiktionary
- **643,399+ word form pages** - every Greek/Latin word form has its own dictionary page
- Click any Greek word to see its dictionary entry with:
  - The clicked word form at the top
  - Expanded morphological information (e.g., "accusative singular" not "acc s")
  - Lemma (dictionary form) if different
  - All dictionary definitions sorted by source (LSJ, Cunliffe, Wiktionary)
- **Elision handling**: Words with apostrophes (μυρί', ἄλγε') automatically map to full forms
- **Grave accent fixes**: καὶ correctly maps to καί
- Words without dictionary entries are not underlined/linked

### Translation Alignment
The system automatically handles complex translation numbering:
- **Direct alignment**: Line-by-line matching
- **Bekker numbering**: For Aristotle's works (e.g., 1447a8)
- **Section-based**: Prose works using section numbers instead of lines
- **Offset translations**: Consistent numeric offsets
- **Partial coverage**: Works with incomplete translations

### Multi-Language Support
Extended database includes:
- **Sanskrit** texts with Devanagari script support
- **Arabic** texts with right-to-left rendering
- **Hebrew** texts with right-to-left rendering
- **Persian** texts with Naskh script
- **Akkadian** cuneiform texts
- **Sumerian** cuneiform texts

All languages have proper font stack and CSS styling.

### Performance Optimizations
- **Pre-loaded data**: All database content loaded into memory once
- **Pre-computed paths**: All 643,399+ dictionary links calculated upfront
- **Batch processing**: Efficient handling of 764,651+ files
- **Fast lookups**: Reverse indices for morphological forms

## Build Process

The build scripts follow this process:

1. **Clean environment**: Remove old build artifacts
2. **Generate HTML content**: Create all HTML pages from database (~70 seconds)
3. **Copy assets**: Include CSS stylesheets
4. **Create ZIM file**: Package HTML into compressed ZIM format (~7 minutes)
5. **Cleanup**: Remove temporary HTML files

### Build Scripts

- `build_sample_clean.sh`: Sample database (12 authors)
- `build_full_clean.sh`: Full database (128 authors)
- `build_extended_clean.sh`: Extended database (391 authors)

Each script:
- Sources the Python virtual environment
- Runs `create_zim_content_optimized.py` with appropriate database
- Packages content with `create_zim_optimized.py`
- Reports statistics and file size

## Generated Structure

```
zim_content_optimized/
├── index.html                    # Main entry page with language selection
├── dictionary/
│   └── greek/                    # 643,399+ dictionary pages
│       ├── zrrOsc6v.html         # καί entry
│       ├── zrrOseG9tg.html       # καὶ entry (maps to καί)
│       └── ... (one file per word form)
├── greek/
│   ├── index.html                # Greek authors list
│   └── authors/
│       ├── tlg0012/              # Homer
│       │   ├── index.html        # Works list
│       │   └── tlg0012.tlg001/   # Iliad
│       │       ├── index.html    # Books list
│       │       ├── book-1.html   # Book 1 (lines 1-200)
│       │       ├── book-1-p2.html # Book 1 (lines 201-400)
│       │       └── ...
│       └── ...
├── latin/
│   └── ... (similar structure)
├── sanskrit/
│   └── ... (similar structure, extended only)
├── arabic/
│   └── ... (similar structure, extended only)
└── assets/
    └── css/style.css             # Unified stylesheet with multi-script support
```

## File Sizes and Performance

### Sample Database (12 authors)
- **Source DB**: 650MB uncompressed
- **HTML files**: ~1.4GB uncompressed (915,526 files)
- **ZIM file**: ~951MB compressed
- **Generation time**: ~15 minutes total (3.7 min content + 11 min packaging)
- **Content**: 1,711 text pages, 913,993 dictionary entries
- **Authors**: 10 Greek, 2 Latin

### Full Database (128 authors)
- **Source DB**: 1.4GB uncompressed
- **HTML files**: ~1.5GB uncompressed (765,000+ files)
- **ZIM file**: ~1.2GB compressed (estimated)
- **Content**: 88 Greek authors, 40 Latin authors, 999 works, 2,563 books

### Extended Database (391 authors)
- **Source DB**: 5.5GB uncompressed, 1.3GB compressed
- **HTML files**: ~5GB uncompressed (estimated)
- **ZIM file**: ~3GB compressed (estimated)
- **Content**: Perseus + 991 First1KGreek works, 1,849 total works
- **Languages**: Greek, Latin, Sanskrit, Arabic, Hebrew, Persian, Akkadian, Sumerian

