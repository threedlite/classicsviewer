# Kiwix ZIM File Generation for Classics Viewer


Note: To reassemble classicsviewer_full_latin.zim, run:
cat classicsviewer_full_latin.zim.part01 classicsviewer_full_latin.zim.part02 > classicsviewer_full_latin.zim 
This is due to Github LFS size limits.


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

Install the Classics Viewer vim file library (sample or full) into Kiwix using file selector.



### Content Overview

The ZIM file contains:
- **Sample database**: 10 Greek authors + 2 Latin authors (278 works, 705 books)
- **Full database**: 88 Greek authors + 40 Latin authors (999 works, 2,563 books)
- Complete texts with aligned translations
- Advanced translation alignment supporting Bekker numbering, section-based texts, and offset translations
- Comprehensive dictionary with 37,715+ entries from LSJ and Cunliffe
- Morphological information showing grammatical forms
- Hierarchical navigation (Language → Author → Work → Book)
- Responsive HTML with CSS styling optimized for offline reading

## Requirements

- Python 3.8+
- SQLite3
- Perseus database (`perseus_texts_sample.db` or `perseus_texts_full.db`)
- Python libzim library (for ZIM creation)
- ~300MB disk space for sample, ~1.5GB for full database

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
./BUILD_ZIM_SAMPLE.sh
```

This creates `perseus_sample.zim` (~318MB) in about 8-10 minutes.

### Manual Build Steps

**1. Generate HTML content:**
```bash
source venv/bin/activate  # Activate virtual environment
python3 create_zim_content_optimized.py --sample
```
This generates ~260,000 HTML files (one for each word form + text pages) in ~70 seconds.

**2. Create ZIM file:**
```bash
python3 create_zim_optimized.py --input zim_content_optimized --output perseus_sample.zim
```
This packages the HTML files into a compressed ZIM archive in ~7 minutes.

### Full Database Build

For the complete 128 author database:
```bash
# First create the full database (takes ~10 minutes)
cd ../data-prep
python3 create_perseus_database.py full

# Then generate ZIM (takes ~9 minutes total)
cd ../kiwix
./BUILD_ZIM_FULL.sh
```

This creates `perseus_full.zim` (~402MB) containing 88 Greek and 40 Latin authors.

## Features

### Dictionary System
- **37,715+ dictionary entries** from LSJ (Liddell-Scott-Jones) and Cunliffe's Homeric lexicon
- **257,000+ word form pages** - every Greek word form has its own dictionary page
- Click any Greek word to see its dictionary entry with:
  - The clicked word form at the top
  - Expanded morphological information (e.g., "accusative singular" not "acc s")
  - Lemma (dictionary form) if different
  - All dictionary definitions sorted by source (LSJ, Cunliffe, Wiktionary)
- **Elision handling**: Words with apostrophes (μυρί', ἄλγε') automatically map to full forms
- **Grave accent fixes**: καὶ correctly maps to καί (not καὶγάρ)
- Words without dictionary entries are not underlined/linked

### Translation Alignment
The system automatically handles complex translation numbering:
- **Direct alignment**: Line-by-line matching
- **Bekker numbering**: For Aristotle's works (e.g., 1447a8)  
- **Section-based**: Prose works using section numbers instead of lines
- **Offset translations**: Consistent numeric offsets
- **Partial coverage**: Works with incomplete translations

### Performance Optimizations
- **Pre-loaded data**: All database content loaded into memory once
- **Pre-computed paths**: All 257,000+ dictionary links calculated upfront
- **Batch processing**: Efficient handling of 260,000+ files
- **Fast lookups**: Reverse indices for morphological forms

## Generated Structure

```
zim_content_optimized/
├── index.html                    # Main entry page
├── dictionary/
│   └── greek/                    # 257,000+ dictionary pages
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
└── assets/
    └── css/style.css
```

## Features

### Implemented
- ✅ Hierarchical navigation
- ✅ Text and translation display
- ✅ Translation alignment with lookup table
- ✅ Multiple translator support
- ✅ Basic dictionary lookup (click on Greek words)
- ✅ Pagination for long texts
- ✅ Breadcrumb navigation
- ✅ Responsive design

### Planned Enhancements
- 📝 Full-text search
- 📝 Enhanced dictionary with morphology
- 📝 Reading position save/restore
- 📝 Dark mode toggle
- 📝 Font size adjustment

## File Sizes and Performance

### Sample Database (12 authors)
- **HTML files**: 1.4GB uncompressed (260,000+ files)
- **ZIM file**: ~318MB compressed
- **Generation time**: ~70 seconds for HTML, ~7 minutes for ZIM
- **Compression ratio**: ~77% reduction

### Full Database (128 authors)
- **HTML files**: 1.5GB uncompressed (265,809 files)
- **ZIM file**: ~402MB compressed
- **Generation time**: ~81 seconds for HTML, ~7.5 minutes for ZIM, ~9 minutes total
- **Compression ratio**: ~73% reduction
- **Content**: 88 Greek authors, 40 Latin authors, 999 works, 2,563 books, 257,549 dictionary pages

## Testing

### 1. Test generated HTML locally
```bash
cd zim_content_optimized
python3 -m http.server 8000
# Open http://localhost:8000
```

### 2. Test ZIM file in Kiwix
```bash

Mac command to open zim in Kiwix:
open -a Kiwix classicsviewer_sample.zim

 or

# Desktop
kiwix-desktop perseus_sample.zim

# Server mode (for browser testing)
kiwix-serve --port 8080 perseus_sample.zim
# Open http://localhost:8080
```

### 3. Verify key features
- Navigate to Greek → Homer → Iliad → Book 1
- Line 2: Check that μυρί' and ἄλγε' are clickable (elision handling)
- Line 7: Click καὶ - should show both LSJ and CUNLIFFE entries
- Any Greek word: Click to see morphology and dictionary entries

## Troubleshooting

### Database not found
Ensure the Perseus database exists:
```bash
cd ../data-prep
python3 create_perseus_database.py sample
```

### zimwriterfs not found
Install zim-tools package for your platform (see Installation section)

### Out of memory during generation
Use `--sample` mode for testing, or increase system swap space

### Greek text not displaying correctly
Ensure UTF-8 encoding is properly set in HTML headers

## Development

### Adding new features

1. Modify templates in `create_zim_content.py`
2. Test with sample mode first
3. Validate output HTML
4. Generate full content
5. Test in Kiwix reader

### Customizing appearance

Edit the CSS generation in `generate_css()` method

### Adding JavaScript functionality

Modify `generate_javascript()` method - keep it minimal for offline use

## License

Content is from Perseus Digital Library (CC-BY-SA 3.0 license)
and Wikitionary (CC-BY-SA 4.0 license)
Code is provided under MIT license

## Support

For issues or questions:
1. Check existing issues in the main Classics Viewer repository
2. Test with sample mode first
3. Verify database integrity
4. Check Kiwix compatibility
