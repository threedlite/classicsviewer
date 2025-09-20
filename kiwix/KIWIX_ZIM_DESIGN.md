# Kiwix ZIM File Design for Classics Viewer

## Overview
This document outlines the design for creating a Kiwix ZIM file that captures the Perseus Digital Library classical texts content and functionality from the Classics Viewer web app. The ZIM file will provide offline access to ~100 Greek and ~95 Latin authors with their works and translations.

## Content Structure

### 1. Hierarchical Organization
```
/
├── index.html (Main entry - language selection)
├── greek/
│   ├── index.html (Greek authors list)
│   ├── authors/
│   │   ├── homer/
│   │   │   ├── index.html (Works list)
│   │   │   ├── iliad/
│   │   │   │   ├── index.html (Book selector)
│   │   │   │   ├── book-1.html (Text + translation)
│   │   │   │   ├── book-2.html
│   │   │   │   └── ...
│   │   │   └── odyssey/
│   │   │       └── ...
│   │   └── plato/
│   │       └── ...
├── latin/
│   ├── index.html (Latin authors list)
│   ├── authors/
│   │   ├── virgil/
│   │   │   └── ...
│   │   └── cicero/
│   │       └── ...
├── assets/
│   ├── css/
│   │   ├── style.css
│   │   └── bootstrap.min.css
│   ├── js/
│   │   └── navigation.js
│   └── fonts/
│       └── greek-fonts.woff2
├── dictionary/
│   ├── greek/
│   │   └── entries/ (JSON dictionary data)
│   └── latin/
│       └── entries/
└── metadata/
    ├── authors.json
    ├── works.json
    └── translations.json
```

### 2. Page Types

#### A. Index Pages
- **Main Index**: Language selection (Greek/Latin)
- **Language Index**: List of all authors for selected language
- **Author Index**: List of works by author
- **Work Index**: List of books/chapters with navigation

#### B. Content Pages
Each book/chapter page will contain:
- **Dual-column layout**: Original text | Translation
- **Line numbers** for reference
- **Multiple translations** when available (with selector)
- **Basic dictionary lookup** (inline popups)
- **Navigation**: Previous/Next book links

#### C. Dictionary Pages
- Standalone dictionary entries linked from words
- Morphological information when available
- Lemma relationships

### 3. Static Generation Approach

Since ZIM files are static, we'll pre-generate all HTML pages:

```python
# Pseudo-code for generation
for language in ['greek', 'latin']:
    for author in get_authors(language):
        for work in get_works(author):
            for book in get_books(work):
                generate_book_page(book, translations)
```

## Key Features to Preserve

### Essential Features (Must Have)
1. **Text Display**
   - Original Greek/Latin text with proper fonts
   - Line-by-line display with numbers
   - Proper Unicode support for polytonic Greek

2. **Translation Alignment**
   - Side-by-side or toggle view
   - Handle section-based translations (Bekker numbering, etc.)
   - Multiple translator support

3. **Navigation**
   - Hierarchical browsing (Author → Work → Book)
   - Direct navigation via table of contents
   - Previous/Next navigation within works

4. **Enhanced Dictionary** (Matches Android App)
   - Click-to-lookup with punctuation stripping
   - Display ALL dictionary entries from ALL sources
   - Multiple entries from same source numbered (e.g., LSJ [1], LSJ [2])
   - Morphological information where available
   - Support for crasis forms and variants

### Nice-to-Have Features
1. **Search**
   - Full-text search across all texts
   - Search within specific authors/works
   - Greek normalization for search

2. **Reading Position**
   - JavaScript-based position saving in localStorage
   - Resume reading functionality

3. **Display Options**
   - Font size adjustment (CSS + JS)
   - Dark/light mode toggle
   - Text/translation view toggle

### Features Not Feasible in ZIM
1. **Dynamic Occurrence Search** - Would require server-side processing
2. **User Bookmarks** - No persistent storage beyond localStorage
3. **Complex Morphological Analysis** - Too computation-heavy for static files

## Technical Implementation

### 1. Database to Static HTML Pipeline

```python
# create_zim_content.py
import sqlite3
from jinja2 import Template
import os
import json

class ZimContentGenerator:
    def __init__(self, db_path, output_dir):
        self.db = sqlite3.connect(db_path)
        self.output_dir = output_dir
        
    def generate_all(self):
        # Generate index pages
        self.generate_main_index()
        
        # Generate author pages
        for language in ['greek', 'latin']:
            self.generate_language_index(language)
            authors = self.get_authors(language)
            
            for author in authors:
                self.generate_author_page(author)
                works = self.get_works(author['id'])
                
                for work in works:
                    self.generate_work_page(work)
                    books = self.get_books(work['id'])
                    
                    for book in books:
                        self.generate_book_page(book)
    
    def generate_book_page(self, book):
        # Get text lines
        text_lines = self.get_text_lines(book['id'])
        
        # Get translations using lookup table
        translations = self.get_translations_with_lookup(book['id'])
        
        # Apply template
        html = self.render_template('book.html', {
            'book': book,
            'text_lines': text_lines,
            'translations': translations
        })
        
        # Save to file
        self.save_html(book['path'], html)
```

### 2. Translation Alignment Strategy

Preserve the translation_lookup table logic:
```sql
-- Include both range-based and lookup-based translations
SELECT DISTINCT ts.* FROM translation_segments ts
WHERE ts.book_id = :bookId 
AND (
    (ts.start_line <= :endLine AND ts.end_line >= :startLine)
    OR EXISTS (
        SELECT 1 FROM translation_lookup tl 
        WHERE tl.book_id = :bookId 
        AND tl.segment_id = ts.id
        AND tl.line_number BETWEEN :startLine AND :endLine
    )
)
```

### 3. Dictionary Integration

Pre-generate comprehensive dictionary JSON with multiple entries support:
```javascript
// Embedded in each page
const dictionary = {
    'καί': {
        'lemma': 'καί',
        'morph': 'conjunction',
        'all_entries': [
            {
                'headword': 'καί',
                'source': 'lsj',
                'text': 'and; also, even...'
            },
            {
                'headword': 'καί',
                'source': 'lsj',
                'text': 'but (after negative)...'
            },
            {
                'headword': 'καί',
                'source': 'cunliffe',
                'text': 'Connecting particle...'
            }
        ]
    }
};

function lookupWord(word) {
    // Strip punctuation first (match Android behavior)
    const cleanedWord = word.replace(/[,;.·:!?᾽]/g, '');
    // Normalize and lookup
    return dictionary[cleanedWord] || dictionary[word];
}
```

### 4. ZIM Creation

Using `zimwriterfs` or Python `libzim`:
```bash
# After generating all HTML content
zimwriterfs --welcome=index.html \
    --favicon=favicon.ico \
    --language=mul \
    --title="Perseus Classical Library" \
    --description="Greek and Latin texts with translations" \
    --creator="Perseus Digital Library" \
    --publisher="Classics Viewer" \
    ./output/ \
    perseus-classics.zim
```

## Resource Optimization

### 1. File Size Considerations
- **Full database**: ~1.4GB uncompressed
- **Target ZIM size**: ~500MB compressed
- **Optimization strategies**:
  - Share CSS/JS across all pages
  - Compress repetitive HTML structures
  - Use ZIM's built-in compression

### 2. Performance Optimizations
- Paginate long texts (30-50 lines per page)
- Lazy-load translations on demand
- Minimize JavaScript functionality
- Use efficient CSS selectors

### 3. Content Prioritization
If size becomes an issue, prioritize:
1. Core texts (without apparatus)
2. Primary translations only
3. Essential dictionary entries
4. Simplified formatting

## Development Status (August 25, 2025)

### Completed Features
- [x] Python generation pipeline (`create_zim_content.py`)
- [x] HTML generation for all page types
- [x] Translation alignment with lookup table support
- [x] Dictionary integration with multiple entries per word
- [x] Punctuation stripping for dictionary lookups
- [x] Navigation between pages (breadcrumbs, prev/next)
- [x] Multiple translator support with dropdown
- [x] ~~Inline dictionary popups on word click~~ → Separate dictionary pages
- [x] CSS styling with responsive design
- [x] JavaScript for interactive features
- [x] Sample database generation (12 authors)
- [x] ZIM file creation with Python libzim

### Major Architecture Change (August 25, 2025)
- **Redesigned dictionary system**: Moved from embedded dictionaries to separate pages
- **Base64 URL-safe filenames**: Handle all Unicode characters properly
- **Performance optimization**: Added caching for word→dictionary path mapping
- **Result**: ~30-50% faster generation with cleaner architecture

### Recent Improvements
- [x] Separate dictionary pages instead of embedded (cleaner design)
- [x] Base64 URL-safe encoding for dictionary filenames
- [x] Caching optimization for repeated word lookups
- [x] Back navigation from dictionary to text
- [x] All 37,715 dictionary pages pre-generated
- [x] Fixed καί showing all entries (LSJ + Cunliffe)
- [x] Fixed ἀείδω being found properly

### Current Status
- Sample ZIM with 10 Greek + Latin authors in progress
- Dictionary pages: 37,715 generated with base64 filenames
- Generation time: ~1 hour estimated (down from 3-4 hours)
- Progress: ~1% of 278 total works completed
- Dictionary now uses separate pages like traditional reference works

## Testing Strategy

### 1. Content Validation
- Verify all texts are present
- Check translation alignment accuracy
- Validate dictionary lookups
- Test special cases (Bekker numbering, etc.)

### 2. Navigation Testing
- Test all navigation paths
- Verify previous/next links
- Check breadcrumb trails
- Test table of contents

### 3. Cross-Platform Testing
- Kiwix Desktop (Windows, Mac, Linux)
- Kiwix Mobile (Android, iOS)
- Kiwix JS (Browser-based)
- Kiwix Server deployment

## Metadata Structure

### ZIM Metadata
```xml
<metadata>
    <title>Perseus Classical Library</title>
    <language>mul</language> <!-- Multiple languages -->
    <creator>Perseus Digital Library</creator>
    <publisher>Classics Viewer Project</publisher>
    <date>2024-08</date>
    <description>Complete collection of Greek and Latin classical texts with translations</description>
    <longDescription>
        Access the complete Perseus Digital Library collection offline.
        Includes ~100 Greek authors and ~95 Latin authors with their complete works.
        Features aligned translations, dictionary lookups, and morphological analysis.
    </longDescription>
    <licence>CC-BY-SA</licence>
    <tags>classics;greek;latin;literature;perseus;texts;translations</tags>
</metadata>
```

## File Naming Conventions

- Authors: `/[language]/authors/[author-id]/index.html`
- Works: `/[language]/authors/[author-id]/[work-id]/index.html`  
- Books: `/[language]/authors/[author-id]/[work-id]/book-[n].html`
- Dictionary: `/dictionary/[language]/[first-letter]/[word].json`

## Success Metrics

1. **Completeness**: All texts and translations accessible
2. **Size**: Final ZIM under 600MB
3. **Performance**: Pages load in <2 seconds
4. **Usability**: Navigation intuitive and functional
5. **Compatibility**: Works on all major Kiwix platforms

## Next Steps

1. ~~Create proof-of-concept with single author~~ ✓ Complete
2. ~~Develop template system~~ ✓ Complete (inline generation)
3. ~~Build generation pipeline~~ ✓ Complete (`create_zim_content.py`)
4. ~~Test with Kiwix readers~~ ✓ In progress
5. ~~Fix dictionary functionality~~ ✓ Complete (August 24, 2025)
6. Generate full ZIM file with all ~195 authors (pending)

## Known Issues and Solutions

### Fixed Issues (August 24, 2025)
1. **Dictionary not finding entries with punctuation**
   - Solution: Strip punctuation before lookup in both Python and JavaScript
   
2. **Only showing one dictionary entry when multiple exist**
   - Solution: Store all entries in `all_entries` array
   - Display with source numbering (e.g., LSJ [1], LSJ [2])

3. **Thermal throttling with multiple processes**
   - Solution: Run single process only to avoid M4 overheating

### Performance Notes
- Dictionary pages generation: ~37,715 pages in first pass
- With caching optimization: ~30-50% speed improvement
- Estimated full generation (278 works): ~1 hour with optimizations
- Base64 filenames handle all Unicode characters properly
- Single-threaded to avoid thermal issues on M4 Macs