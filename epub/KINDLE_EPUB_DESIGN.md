# Kindle ePub Design Document for Classics Viewer

## Executive Summary

This document outlines the design for creating Kindle-optimized ePub versions of the Classics Viewer content. Unlike the Kiwix version which relies on JavaScript and sidebar navigation, the Kindle ePub must work within severe constraints: **no JavaScript, no sidebars, linear navigation only**.

## Kindle vs Kiwix: Fundamental Differences

| Feature | Kiwix | Kindle ePub |
|---------|-------|-------------|
| JavaScript | Full support | **None** |
| Sidebar navigation | Yes | **No** |
| Word click-to-lookup | JS popup | **Links to dictionary pages** |
| Translation switching | JS dropdown | **Grouped by translator at end** |
| Navigation | Hierarchical + breadcrumbs | **TOC + line navigation links** |
| Font embedding | Full control | **Limited on e-ink** |
| Interactivity | High | **Links only** |
| Content structure | Web pages | **Linear chapters** |

## Design Principles

### 0. Text Only - No Audio
Kindle does not support ePub 3 Media Overlays (synchronized audio/text). Amazon uses proprietary WhisperSync which requires separate Audible distribution. **Audio is out of scope for this project.**

### 1. Embrace Linearity
Kindle is fundamentally a **page-turn device**. The UI must work with sequential reading, not against it.

### 2. Front-load Navigation
All navigation decisions happen at the **beginning** via Table of Contents. Once reading, the user flows linearly.

### 3. Inline Everything
No popups, no overlays, no modals. All supplementary content (glosses, translations) must be **inline or footnoted**.

### 4. Leverage Kindle's Built-in Features
- **Kindle Dictionary**: Create custom MOBI dictionaries for Greek/Latin
- **X-Ray**: Potentially integrate character/term explanations
- **TOC**: Use NCX/NAV for robust navigation

---

## Content Organization

### Core Principle: Interlinear Stays with Text

Interlinear content is **fundamentally tied to specific lines** of the original text. They cannot be separated into different files - the interlinear IS the text with glosses attached.

### Implemented Structure: Unified Work with All Views

Each work is a **single ePub** containing the text with interlinear annotations inline:

```
Iliad_ClassicsViewer.epub (6.4 MB)
├── Title Page
├── License (dynamically loaded from LICENSE.txt)
├── Table of Contents (NAV + NCX)
├── Greek Text with Interlinear
│   ├── Book 1 (lines with glosses, linked words)
│   ├── Book 2
│   └── ... (Books 3-24)
├── Dictionary (76 files by first letter)
│   ├── dict_a.xhtml (α words)
│   ├── dict_b.xhtml (β words)
│   └── ... (all Greek letters)
└── Translations (grouped by translator)
    ├── A.T. Murray translations (Books 1-24)
    └── Samuel Butler translations (Books 1-24)
```

### Chapter Structure: Integrated View

Each chapter shows the Greek text with interlinear glosses **inline**, with words linked to dictionary:

```html
<p class="page-header">Homer — Iliad</p>
<h1>Book 3</h1>

<p class="line-nav">Lines: <a href="#line-100">3.100</a> · <a href="#line-200">3.200</a> · ...</p>

<p class="interlinear-line">
  <span class="line-num">3.1</span>
  <a href="dict_zrE.xhtml#base64id" class="word-link">αὐτὰρ</a>
  <span class="gloss">(but, yet)</span>
  <a href="dict_4byQ.xhtml#base64id" class="word-link">ἐπεὶ</a>
  <span class="gloss">(after that, since, when)</span>
  <!-- ... rest of line ... -->
</p>

<p class="interlinear-line" id="line-100">
  <span class="line-num">3.100</span>
  <!-- Line 100 content with anchor for navigation -->
</p>
```

### Translation Placement Options

Since interlinear gives word-by-word meaning, the full flowing translation can be:

**Option A: End of Each Book (Recommended)**
```
Book 1 (Greek + Interlinear)
  Lines 1-611...
Book 1 Translation
  Flowing English text...
Book 2 (Greek + Interlinear)
  Lines 1-877...
Book 2 Translation
  ...
```

**Option B: Appendix at End**
```
Books 1-24 (Greek + Interlinear)
Appendix: Complete Translation
  Book 1 Translation
  Book 2 Translation
  ...
```

**Option C: Parallel Blocks (within chapter)**
```
Book 1, Lines 1-50 (Greek + Interlinear)
Book 1, Lines 1-50 (Translation)
Book 1, Lines 51-100 (Greek + Interlinear)
Book 1, Lines 51-100 (Translation)
...
```

### Recommendation: Option A (Translation After Each Book)

This keeps related content close together while maintaining the primacy of the Greek+Interlinear reading experience. Users can:
1. Read through Greek with interlinear help
2. Jump to translation for that book via TOC if needed
3. Continue to next book

### Works WITHOUT Interlinear

For works that don't have interlinear data, offer **Greek + Translation** side by side or sequential:

```
Plato's Republic (No Interlinear Available)
├── Book 1 (Greek Text)
├── Book 1 (English Translation)
├── Book 2 (Greek Text)
├── Book 2 (English Translation)
└── ...
```

Or inline glossary for key vocabulary:

```html
<p class="greek-line">
  <span class="line-num">327a</span>
  κατέβην χθὲς εἰς Πειραιᾶ μετὰ Γλαύκωνος...
</p>
<p class="vocab-note">
  κατέβην: I went down | χθές: yesterday | Πειραιεύς: Piraeus
</p>
```

---

## Navigation Architecture

### Primary Navigation: Table of Contents

The NCX/NAV Table of Contents is the **only reliable navigation** on Kindle.

```xml
<navMap>
  <navPoint id="intro" playOrder="1">
    <navLabel><text>Introduction</text></navLabel>
    <content src="intro.xhtml"/>
  </navPoint>
  <navPoint id="book1" playOrder="2">
    <navLabel><text>Book 1: The Rage of Achilles</text></navLabel>
    <content src="book01.xhtml"/>
    <navPoint id="book1-1" playOrder="3">
      <navLabel><text>Lines 1-50</text></navLabel>
      <content src="book01.xhtml#lines-1-50"/>
    </navPoint>
    <navPoint id="book1-51" playOrder="4">
      <navLabel><text>Lines 51-100</text></navLabel>
      <content src="book01.xhtml#lines-51-100"/>
    </navPoint>
  </navPoint>
  <!-- ... -->
</navMap>
```

### Secondary Navigation: In-Chapter Links

At the **end of each chapter**, provide navigation links:

```html
<div class="chapter-nav">
  <p><a href="book01.xhtml">← Previous: Book 1</a></p>
  <p><a href="toc.xhtml">Table of Contents</a></p>
  <p><a href="book03.xhtml">Next: Book 3 →</a></p>
</div>
```

### No Sidebar, No Header Nav

Kindle strips or ignores fixed-position elements. **Do not rely on:**
- Fixed headers
- Floating navigation
- Persistent sidebars
- Sticky elements

---

## Interlinear Format Design

### Core Principle: Wrapping, Not Scrolling

Kindle has **no horizontal scrolling**. Interlinear word groups must **wrap naturally** to fit any screen width. A single line of Greek poetry will flow across multiple screen lines as needed.

### Layout: Wrapping Word Groups

Word groups use `inline-block` which naturally wraps when the line is too wide:

```html
<div class="interlinear-line">
  <span class="line-num">1</span>
  <span class="word-group">
    <span class="greek">Μῆνιν</span>
    <span class="gloss">wrath</span>
  </span>
  <span class="word-group">
    <span class="greek">ἄειδε</span>
    <span class="gloss">sing!</span>
  </span>
  <span class="word-group">
    <span class="greek">θεά</span>
    <span class="gloss">goddess</span>
  </span>
  <span class="word-group">
    <span class="greek">Πηληϊάδεω</span>
    <span class="gloss">of-Peleus'-son</span>
  </span>
  <span class="word-group">
    <span class="greek">Ἀχιλῆος</span>
    <span class="gloss">of-Achilles</span>
  </span>
</div>
```

### CSS for Wrapping Interlinear

```css
.interlinear-line {
  margin: 1em 0;
  padding-left: 2em;  /* Indent for line number */
  text-indent: -2em;  /* Hanging indent */
}

.line-num {
  display: inline-block;
  width: 1.8em;
  color: #888;
  font-size: 0.8em;
  text-align: right;
  margin-right: 0.5em;
}

.word-group {
  display: inline-block;
  text-align: center;
  margin: 0.2em 0.3em 0.4em 0;
  vertical-align: top;
  /* NO fixed width - allows natural wrapping */
}

.greek {
  font-family: "Gentium Plus", "Gentium", "Times New Roman", serif;
  font-size: 1.1em;
  display: block;
}

.gloss {
  font-size: 0.8em;
  color: #555;
  display: block;
}
```

### Visual Result: Wide Screen

On a tablet or large Kindle, line 1 might fit on one row:

```
1   Μῆνιν     ἄειδε      θεά       Πηληϊάδεω        Ἀχιλῆος
    wrath     sing!     goddess   of-Peleus'-son   of-Achilles
```

### Visual Result: Narrow Screen (e-ink Paperwhite)

On a narrow Kindle screen, the same line wraps naturally:

```
1   Μῆνιν     ἄειδε      θεά
    wrath     sing!     goddess

    Πηληϊάδεω        Ἀχιλῆος
    of-Peleus'-son   of-Achilles
```

### Visual Result: Very Narrow (Phone)

```
1   Μῆνιν     ἄειδε
    wrath     sing!

    θεά       Πηληϊάδεω
    goddess   of-Peleus'-son

    Ἀχιλῆος
    of-Achilles
```

### Line Separation

To make it clear where one line of poetry ends and the next begins:

```css
.interlinear-line {
  margin-bottom: 1.2em;
  padding-bottom: 0.8em;
  border-bottom: 1px dotted #ddd;  /* Visual separator */
}
```

Or use line numbers prominently:

```css
.line-num {
  font-weight: bold;
  color: #666;
  background: #f0f0f0;
  padding: 0.1em 0.3em;
  border-radius: 2px;
}
```

### Alternative: Compact Inline Format

For prose or when space is critical, use parenthetical glosses that wrap naturally:

```html
<p class="interlinear-inline">
  <span class="line-num">1</span>
  <span class="greek">Μῆνιν</span> <span class="gloss">(wrath)</span>
  <span class="greek">ἄειδε</span> <span class="gloss">(sing!)</span>
  <span class="greek">θεά</span> <span class="gloss">(goddess)</span>
  <span class="greek">Πηληϊάδεω</span> <span class="gloss">(of-Peleus'-son)</span>
  <span class="greek">Ἀχιλῆος</span> <span class="gloss">(of-Achilles)</span>
</p>
```

Renders as flowing text that wraps:

```
1 Μῆνιν (wrath) ἄειδε (sing!) θεά (goddess)
Πηληϊάδεω (of-Peleus'-son) Ἀχιλῆος
(of-Achilles)
```

### Recommendation

Use **stacked word groups** (Greek above, gloss below) as the default - it's more readable for language learners. The inline format is a fallback for very long lines or prose texts.

---

## Dictionary Integration

### Option 1: Kindle Custom Dictionary (Recommended)

Create a **separate MOBI dictionary** that Kindle's built-in lookup uses:

```
classicsviewer_greek_dictionary.mobi
├── α entries (ἀγαθός, ἄγω, etc.)
├── β entries
└── ...
```

**User Experience:**
1. User long-presses a Greek word
2. Kindle's native dictionary popup appears
3. Shows lemma, definition, morphology

**Implementation:**
- Use `kindlegen` or Calibre to create dictionary
- Format: MOBI with `<idx:entry>` tags
- Must be sideloaded (not from Kindle Store)

```html
<!-- Dictionary entry format -->
<idx:entry name="default" scriptable="yes">
  <idx:orth>μῆνις</idx:orth>
  <idx:infl>
    <idx:iform value="μῆνιν"/>
    <idx:iform value="μήνιος"/>
    <idx:iform value="μῆνι"/>
  </idx:infl>
  <p><b>μῆνις, -ιος, ἡ</b></p>
  <p>wrath, anger (especially of gods); lasting anger, grudge</p>
  <p><i>Source: LSJ</i></p>
</idx:entry>
```

### Option 2: End-of-Chapter Glossary

Append vocabulary to each chapter:

```html
<section class="glossary">
  <h2>Vocabulary: Book 1, Lines 1-50</h2>
  <dl>
    <dt>μῆνις, -ιος, ἡ</dt>
    <dd>wrath, anger (especially divine)</dd>

    <dt>ἀείδω</dt>
    <dd>to sing (poetic); sing of, celebrate</dd>
  </dl>
</section>
```

### Option 3: Footnotes

Use ePub footnotes for definitions:

```html
<p>
  <span class="greek">μῆνιν</span><a href="#fn1" epub:type="noteref">1</a>
  <span class="greek">ἄειδε</span><a href="#fn2" epub:type="noteref">2</a>
</p>

<aside id="fn1" epub:type="footnote">
  <p>μῆνις, -ιος, ἡ: wrath, anger</p>
</aside>
```

**Note:** Kindle handles footnotes as popup-style on newer devices, inline on older ones.

### Recommendation

**Primary:** Custom Kindle Dictionary (works natively)
**Fallback:** End-of-chapter glossary (always works)

---

## Greek Font Handling

### The Problem

Kindle e-ink devices have **inconsistent Greek support**:
- Newer Paperwhite/Oasis: Good Unicode support
- Older Kindles: May show boxes or wrong glyphs
- Kindle Fire: Full support (Android-based)

### Solution: Embedded Fonts + Fallback

```css
@font-face {
  font-family: "ClassicsGreek";
  src: url("fonts/GentiumPlus-Regular.ttf");
  font-weight: normal;
}

@font-face {
  font-family: "ClassicsGreek";
  src: url("fonts/GentiumPlus-Bold.ttf");
  font-weight: bold;
}

.greek {
  font-family: "ClassicsGreek", "Gentium Plus", "Gentium",
               "Times New Roman", "Noto Serif", serif;
}
```

### Font Embedding in ePub

```
OEBPS/
├── fonts/
│   ├── GentiumPlus-Regular.ttf
│   └── GentiumPlus-Bold.ttf
├── content.opf (declares fonts)
└── chapters/
```

### Content.opf Font Declaration

```xml
<manifest>
  <item id="font-gentium" href="fonts/GentiumPlus-Regular.ttf"
        media-type="application/x-font-ttf"/>
  <item id="font-gentium-bold" href="fonts/GentiumPlus-Bold.ttf"
        media-type="application/x-font-ttf"/>
</manifest>
```

### Testing Required

Must test on:
- [ ] Kindle Paperwhite (2021+)
- [ ] Kindle Oasis (2019+)
- [ ] Kindle Scribe
- [ ] Kindle Fire tablets
- [ ] Kindle iOS app
- [ ] Kindle Android app
- [ ] Older Paperwhite (2018 and earlier)

---

## File Structure

### ePub Package Structure

```
ClassicsViewer_Iliad_Greek.epub
├── mimetype
├── META-INF/
│   └── container.xml
├── OEBPS/
│   ├── content.opf          # Package manifest
│   ├── toc.ncx              # NCX TOC (legacy)
│   ├── toc.xhtml            # NAV TOC (ePub3)
│   ├── styles/
│   │   ├── main.css
│   │   └── interlinear.css
│   ├── fonts/
│   │   └── GentiumPlus-Regular.ttf
│   ├── images/
│   │   └── cover.jpg
│   ├── front/
│   │   ├── cover.xhtml
│   │   ├── title.xhtml
│   │   └── intro.xhtml
│   ├── text/
│   │   ├── book01.xhtml
│   │   ├── book02.xhtml
│   │   └── ...
│   └── back/
│       ├── glossary.xhtml
│       └── about.xhtml
└──
```

### Chapter XHTML Structure

```html
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:epub="http://www.idpf.org/2007/ops"
      xml:lang="grc">
<head>
  <title>Iliad Book 1</title>
  <link rel="stylesheet" type="text/css" href="../styles/main.css"/>
</head>
<body>
  <section epub:type="chapter" id="book1">
    <h1>Book 1: The Rage of Achilles</h1>

    <div class="text-block" id="lines-1-50">
      <p class="line" data-line="1">
        <span class="line-num">1</span>
        <span class="greek">Μῆνιν ἄειδε θεὰ Πηληϊάδεω Ἀχιλῆος</span>
      </p>
      <p class="line" data-line="2">
        <span class="line-num">2</span>
        <span class="greek">οὐλομένην, ἣ μυρί᾽ Ἀχαιοῖς ἄλγε᾽ ἔθηκε,</span>
      </p>
      <!-- ... -->
    </div>

    <nav class="chapter-nav">
      <a href="toc.xhtml">Contents</a> |
      <a href="book02.xhtml">Book 2 →</a>
    </nav>
  </section>
</body>
</html>
```

---

## Product Line (All Free)

### Priority 1: Essential Works (Launch)

High-demand texts with interlinear where available:

| Work | Content | Est. Size |
|------|---------|-----------|
| Homer - Iliad | Greek + Interlinear + Translation | 15-20 MB |
| Homer - Odyssey | Greek + Interlinear + Translation | 12-18 MB |
| Virgil - Aeneid | Latin + Translation | 8-12 MB |
| Greek New Testament | Greek + Interlinear | 8-12 MB |
| Sophocles - Oedipus Tyrannus | Greek + Translation | 2-4 MB |
| Plato - Republic | Greek + Translation | 4-6 MB |

### Priority 2: Author Collections

Bundled works by author (single ePub per author):

| Collection | Contents | Est. Size |
|------------|----------|-----------|
| Complete Homer | Iliad + Odyssey + Hymns (all with interlinear) | ~40 MB |
| Complete Virgil | Aeneid + Eclogues + Georgics | 15-20 MB |
| Greek Tragedians | Aeschylus, Sophocles, Euripides complete | 30-40 MB |
| Attic Orators | Demosthenes, Lysias, Aeschines, etc. | 25-35 MB |

### Priority 3: Full Corpus

Complete library (split into 50MB chunks for Send to Kindle):

| Collection | Works | Strategy |
|------------|-------|----------|
| All Greek Poetry | ~200 works | 3-4 volumes |
| All Greek Prose | ~300 works | 4-5 volumes |
| All Latin Literature | ~230 works | 2-3 volumes |

**Note:** Large collections split alphabetically by author or by genre.

---

## Generation Pipeline

### Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Perseus DB     │────▶│  Python Generator │────▶│  ePub Files     │
│  (SQLite)       │     │  create_epub.py   │     │  (.epub)        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌──────────────────┐
                        │  Calibre/KindleGen│
                        │  (MOBI conversion)│
                        └──────────────────┘
                                │
                                ▼
                        ┌──────────────────┐
                        │  .mobi / .azw3   │
                        │  (Kindle format) │
                        └──────────────────┘
```

### Python Generator Module

```python
# epub/create_epub.py

from ebooklib import epub
import sqlite3

class KindleEpubGenerator:
    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path)
        self.book = epub.EpubBook()

    def generate_work(self, work_id: str, format: str = 'text'):
        """
        Generate ePub for a single work.

        Args:
            work_id: Database work ID
            format: 'text', 'translation', or 'interlinear'
        """
        work = self.get_work(work_id)

        # Set metadata
        self.book.set_identifier(f'classicsviewer-{work_id}-{format}')
        self.book.set_title(f"{work['title']} ({format.title()})")
        self.book.set_language('grc' if format != 'translation' else 'en')
        self.book.add_author(work['author_name'])

        # Add styles
        self.add_styles()

        # Add fonts
        self.add_fonts()

        # Generate chapters
        chapters = []
        for book in self.get_books(work_id):
            chapter = self.generate_chapter(book, format)
            chapters.append(chapter)
            self.book.add_item(chapter)

        # Create TOC
        self.book.toc = chapters
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())

        # Set spine
        self.book.spine = ['nav'] + chapters

        return self.book

    def generate_chapter(self, book: dict, format: str) -> epub.EpubHtml:
        """Generate a single chapter."""
        lines = self.get_text_lines(book['id'])

        if format == 'interlinear':
            content = self.render_interlinear(lines, book['id'])
        elif format == 'translation':
            content = self.render_translation(book['id'])
        else:
            content = self.render_greek_text(lines)

        chapter = epub.EpubHtml(
            title=book['label'],
            file_name=f"book{book['book_number']:02d}.xhtml",
            content=content
        )
        chapter.add_link(href='styles/main.css', rel='stylesheet', type='text/css')

        return chapter

    def render_interlinear(self, lines: list, book_id: str) -> str:
        """Render interlinear format with word-by-word glosses."""
        html = ['<section class="interlinear">']

        for line in lines:
            interlinear_data = self.get_interlinear(book_id, line['line_number'])
            html.append(f'<div class="interlinear-line" id="line-{line["line_number"]}">')
            html.append(f'<span class="line-num">{line["line_number"]}</span>')

            for word_data in interlinear_data:
                html.append(f'''
                <span class="word-group">
                    <span class="greek">{word_data['word']}</span>
                    <span class="gloss">{word_data['gloss']}</span>
                    <span class="morph">{word_data['morph']}</span>
                </span>''')

            html.append('</div>')

        html.append('</section>')
        return '\n'.join(html)
```

### Build Commands

```bash
# Generate single work
cd epub
python3 create_epub.py --work tlg0012.tlg001 --format interlinear

# Generate author collection
python3 create_epub.py --author homer --formats text,translation,interlinear

# Generate all essential works
python3 create_epub.py --tier essential

# Convert to Kindle format
calibre-convert output/iliad_interlinear.epub output/iliad_interlinear.mobi

# Or use Amazon's tool
kindlegen output/iliad_interlinear.epub
```

---

## CSS Considerations for Kindle

### What Works

```css
/* Safe CSS for Kindle */
body {
  margin: 5%;
  font-family: serif;
  line-height: 1.5;
}

p {
  text-indent: 1.5em;
  margin: 0;
}

h1, h2, h3 {
  text-align: center;
  margin: 1em 0;
}

.line-num {
  color: #888;
  font-size: 0.8em;
  margin-right: 0.5em;
}

/* inline-block works for word groups */
.word-group {
  display: inline-block;
  margin: 0.2em;
}
```

### What Doesn't Work

```css
/* AVOID on Kindle */
position: fixed;      /* Ignored */
position: sticky;     /* Ignored */
float: right;         /* Unreliable */
display: flex;        /* Partial support */
display: grid;        /* No support on e-ink */
column-count: 2;      /* Unreliable */
@media queries;       /* Limited support */
::before, ::after;    /* Inconsistent */
```

### Kindle-Specific Hacks

```css
/* Force page break before chapters */
section.chapter {
  page-break-before: always;
}

/* Prevent orphan lines */
p {
  orphans: 2;
  widows: 2;
}

/* Kindle tends to ignore small fonts */
.small {
  font-size: 0.9em; /* Don't go below 0.8em */
}
```

---

## Testing Checklist

### Pre-Publication Testing

- [ ] Greek characters render correctly (all diacritics)
- [ ] Line numbers display properly
- [ ] Interlinear alignment looks correct
- [ ] TOC navigation works
- [ ] Chapter-to-chapter links work
- [ ] Embedded fonts load
- [ ] File size under 650MB
- [ ] No JavaScript errors (should be none)
- [ ] Custom dictionary works (if implemented)

### Device Testing Matrix

| Device | Priority | Greek Support | Notes |
|--------|----------|---------------|-------|
| Kindle Paperwhite 5 | High | Good | Primary target |
| Kindle Oasis 3 | High | Good | Premium users |
| Kindle Scribe | Medium | Good | Larger screen |
| Kindle Fire HD | Medium | Excellent | Android-based |
| Kindle iOS App | High | Excellent | Large user base |
| Kindle Android App | High | Excellent | Large user base |
| Older Paperwhite | Low | Variable | May need fallback |

### Tools

- **Kindle Previewer**: Amazon's official testing tool
- **Calibre**: ePub validation and conversion
- **EPUBCheck**: W3C validator
- **Sigil**: ePub editor for fixes

---

## File Size Constraints

### Relevant File Size Limits

| Limit | Value | Notes |
|-------|-------|-------|
| **Send to Kindle max** | 50 MB | Per-file limit for email/app |
| **Recommended size** | < 30 MB | Faster downloads, quick delivery |
| **USB sideload** | Unlimited | No restrictions |

### Send to Kindle Limits (Primary Distribution)

Since we're distributing for **free via Send to Kindle**, the relevant limits are:

| Method | File Limit | Notes |
|--------|------------|-------|
| Email to @kindle.com | **50 MB** | Most common method |
| Send to Kindle app | **50 MB** | Desktop drag-and-drop |
| Send to Kindle website | **50 MB** | Browser upload |
| USB sideload | **Unlimited** | Manual transfer |

**Good news:** 50 MB is generous enough for complete interlinear works as single files.

### Size Estimates by Content Type

| Content Type | Lines | Est. Size | Notes |
|--------------|-------|-----------|-------|
| **Plain Greek text** | 1,000 | 50-80 KB | Just text, minimal markup |
| **Greek + line numbers** | 1,000 | 80-120 KB | Slight overhead |
| **Greek + translation** | 1,000 | 150-250 KB | Two text streams |
| **Interlinear (basic)** | 1,000 | 400-600 KB | Word + gloss |
| **Interlinear (full)** | 1,000 | 800 KB - 1.2 MB | Word + gloss + morph |
| **Embedded font** | - | 200-400 KB | Per font file |

### Projected File Sizes for Key Works

| Work | Lines | Greek Only | Translation | Interlinear | Full (all 3) |
|------|-------|------------|-------------|-------------|--------------|
| Iliad | 15,693 | 1.2 MB | 1.5 MB | **12-18 MB** | 15-22 MB |
| Odyssey | 12,110 | 1.0 MB | 1.2 MB | **10-15 MB** | 12-18 MB |
| Aeneid | 9,896 | 0.8 MB | 1.0 MB | 8-12 MB | 10-14 MB |
| Republic | 5,200 | 0.4 MB | 0.5 MB | 4-6 MB | 5-7 MB |
| NT Greek | 7,957 | 0.6 MB | 0.8 MB | 6-10 MB | 8-12 MB |
| **Full Greek corpus** | 3.8M | ~300 MB | ~400 MB | **3-4 GB** | N/A |

**Key insight:** Interlinear format is **10-15x larger** than plain text.

### Size Reduction Strategies

#### 1. Split by Format (Recommended)

Separate volumes for each format:
```
Homer_Iliad_Greek.epub        (1.2 MB)  ← Under delivery fee threshold
Homer_Iliad_Translation.epub  (1.5 MB)  ← Under delivery fee threshold
Homer_Iliad_Interlinear.epub  (15 MB)   ← Use 35% royalty
```

#### 2. Split by Book/Section

For large interlinear works:
```
Homer_Iliad_Interlinear_Books_1-8.epub   (6 MB)
Homer_Iliad_Interlinear_Books_9-16.epub  (6 MB)
Homer_Iliad_Interlinear_Books_17-24.epub (6 MB)
```

#### 3. Reduce Interlinear Detail

**Full detail (largest):**
```html
<span class="word-group">
  <span class="greek">μῆνιν</span>
  <span class="gloss">wrath</span>
  <span class="morph">noun, accusative, singular, feminine</span>
  <span class="lemma">μῆνις</span>
</span>
```

**Minimal detail (smallest):**
```html
<span class="greek">μῆνιν</span> <span class="gloss">(wrath)</span>
```

Size reduction: **40-60%** by dropping morph/lemma.

#### 4. Font Optimization

| Strategy | Savings |
|----------|---------|
| Subset font (Greek only) | 60-70% |
| WOFF2 compression | 30-40% |
| Single weight only | 50% |
| System font fallback | 100% (risky) |

**Recommended:** Subset Gentium Plus to Greek + basic Latin (~100KB vs 400KB).

#### 5. HTML Minification

Remove whitespace, use short class names:
```html
<!-- Before: 180 bytes -->
<span class="word-group">
  <span class="greek">μῆνιν</span>
  <span class="gloss">wrath</span>
</span>

<!-- After: 55 bytes -->
<b class=w><i class=g>μῆνιν</i><i class=e>wrath</i></b>
```

Savings: **50-70%** on HTML content.

### Size Budget for Free Distribution

**Target:** Keep files under 50 MB for Send to Kindle compatibility.

| Product | Target Size | Strategy |
|---------|-------------|----------|
| Single work (Greek text) | < 5 MB | Single file |
| Single work (translation) | < 5 MB | Single file |
| Single work (interlinear) | < 20 MB | Single file |
| Author collection | < 50 MB | Single file |
| Large corpus | Multiple 50 MB volumes | Split by author/genre |

**Benefit of free distribution:** No file size/pricing tradeoffs. Can offer complete works.

### Compression Notes

ePub is already ZIP-compressed, but:
- Greek text compresses well (~70% reduction)
- Repetitive HTML structure compresses well
- Fonts don't compress much (already optimized)
- Images should be JPEG, not PNG

**Final ePub size ≈ 30-40% of uncompressed content.**

---

## Distribution Strategy

### Option 1: Send to Kindle (Recommended for Free Distribution)

Amazon's **Send to Kindle** service allows users to send personal documents directly to their Kindle devices.

**How it works:**
1. User downloads ePub from Classics Viewer website
2. User sends to their `@kindle.com` email address
3. Amazon converts and delivers to device
4. Syncs across all user's Kindle apps/devices

**Methods:**
| Method | File Limit | Notes |
|--------|------------|-------|
| Email attachment | 50 MB | Send to `username@kindle.com` |
| Send to Kindle app (desktop) | 50 MB | Drag and drop |
| Send to Kindle website | 50 MB | Browser upload |
| Kindle mobile app | 50 MB | Share sheet integration |

**Pros:**
- **No delivery fees** - Amazon delivers for free
- **No file size royalty impact** - 50MB limit is generous
- **No KDP review process** - Instant delivery
- **Custom dictionary works** - Users can sideload dictionaries
- **Free distribution** - No cost to us or users
- **Automatic conversion** - Amazon converts ePub → AZW3
- **Cloud sync** - Document syncs across devices
- **Whispersync** - Reading position synced

**Cons:**
- No discoverability (users must find our website)
- No revenue (unless we charge for download)
- Users need to know their Kindle email
- 50 MB limit per file (still need to split large works)

**Implementation:**
```
Website: classicsviewer.com/kindle/

1. User selects work + format (Greek/Translation/Interlinear)
2. User downloads .epub file
3. Instructions shown for Send to Kindle
4. Optional: Direct "Send to Kindle" button (requires API integration)
```

### Option 2: Direct USB Sideloading

For users who prefer manual transfer.

**Pros:**
- No Amazon account required
- Works on any Kindle
- Custom dictionary guaranteed to work
- No file size limits

**Cons:**
- Requires USB cable
- Technical barrier for some users
- No cloud sync
- Manual for each device

### Option 3: Calibre Integration

Many Kindle users use Calibre for library management.

**Implementation:**
- Provide ePub downloads compatible with Calibre
- Include Calibre conversion instructions
- Calibre can send directly to Kindle via email or USB

### Recommended Distribution Approach

All content distributed **free** via website downloads:

| Content | Primary Method | Backup Method |
|---------|----------------|---------------|
| **Individual works** | Send to Kindle | Direct download |
| **Author collections** | Send to Kindle | Calibre |
| **Full corpus** | Send to Kindle (split by 50MB) | USB sideload |
| **Custom Greek dictionary** | Direct download + USB sideload | Required for lookup |

**Simple user flow:**
1. User visits website
2. Selects work(s) to download
3. Downloads ePub file(s)
4. Sends to Kindle via email or app
5. Reads on Kindle with interlinear glosses

### Send to Kindle Integration Options

#### Basic: Download + Instructions
```
┌─────────────────────────────────────────────────────┐
│  Homer's Iliad (Interlinear)                        │
│                                                     │
│  [Download ePub]                                    │
│                                                     │
│  To send to your Kindle:                            │
│  1. Email this file to yourname@kindle.com          │
│  2. Or use the Send to Kindle app                   │
│  3. Or drag to Calibre                              │
└─────────────────────────────────────────────────────┘
```

#### Advanced: Direct Send to Kindle Button

Amazon provides a "Send to Kindle" button for websites:

```html
<!-- Amazon's Send to Kindle button -->
<script src="https://d1xnn692s7u6t6.cloudfront.net/widget.js"></script>
<script>
  var defined = STK.Widget.Defined;
  STK.Widget.Create({
    file: 'https://classicsviewer.com/kindle/iliad_interlinear.epub',
    title: "Homer's Iliad (Interlinear)",
    author: 'Homer'
  });
</script>
```

**Note:** This requires Amazon approval and HTTPS hosting.

### File Size Strategy

With Send to Kindle's **50 MB limit**, we can offer complete works:

| Product | Estimated Size | Strategy |
|---------|----------------|----------|
| Single work (Greek + Interlinear) | 5-20 MB | Single file |
| Homer Complete (Iliad + Odyssey) | ~40 MB | Single file |
| Author collection | < 50 MB | Single file |
| Large corpus | 50 MB chunks | Split by author/genre |

**Key insight:** 50 MB is generous enough for complete interlinear works as single files.

---

## Current Implementation Status (December 2025)

### Completed Features

The ePub generator (`create_kindle_epub.py`) is fully functional with the following features:

#### Structure
- **Title page** with work title, author, and line count
- **License page** dynamically loaded from `LICENSE.txt` with source URL and retrieval date
- **Table of Contents** (both NAV for ePub3 and NCX for legacy readers)
- **Greek text chapters** (24 books for Iliad) with interlinear glosses
- **Dictionary** split into 76 files by first letter for fast loading
- **Translations** grouped by translator (e.g., all Murray books, then all Butler books)

#### Interlinear Format
- Inline glosses: `ἄνδρα (man) μοι (to-me) ἔννεπε (tell)`
- Words link to full dictionary definitions
- Line numbers include book prefix: `3.114`, `5.200`
- Line navigation links at chapter start: `Lines: 3.100 · 3.200 · 3.300`

#### Dictionary Integration
- Full entries from LSJ, Cunliffe, and Wiktionary
- Morphology information where available
- Base64 URL-safe encoding for Greek word IDs
- Preloaded lemma mappings (643K entries) for accurate lookups

#### Translations
- Multiple translators supported per work
- Grouped by translator in TOC and spine
- Line references with book prefix: `[5.460-5.510]`
- Title format: "Book 1 (Translation by Samuel Butler)"

#### Page Headers
- Shows "Author — Work" on each page (e.g., "Homer — Iliad")
- Book number in h1 heading

### Sample Output

**Iliad_ClassicsViewer.epub** (6.4 MB):
- 24 Greek chapters with interlinear
- 76 dictionary files (21,496 entries)
- 48 translation chapters (2 translators × 24 books)
- 15,687 lines of Greek text

### Usage

**Single work mode:**
```bash
cd epub
python3 create_kindle_epub.py \
    --db ../data-prep/perseus_texts_sample.db \
    --work tlg0012.tlg001 \
    --output-name Iliad_ClassicsViewer.epub
```

**Batch mode (CSV input):**
```bash
# CSV format: Author,Work (same as SAMPLE_AUTHORS.csv)
python3 create_kindle_epub.py \
    --db ../data-prep/perseus_texts_sample.db \
    --csv ../data-prep/SAMPLE_AUTHORS.csv
```

**iOS sample list (41 works including NT, philosophy, poetry):**
```bash
python3 create_kindle_epub.py \
    --db ../data-prep/perseus_texts_ios.db \
    --csv ../data-prep/IOS_SAMPLE_AUTHORS.csv
```

Output filenames are auto-generated as `{WorkTitle}_ClassicsViewer.epub`

#### Title Matching

The script matches works by both `title` and `title_english` columns, so CSVs can use either:
- Original titles: "Ἐγχειρίδιον", "Elementa", "De musica"
- English titles: "The Enchiridion", "The Thirteen Books of Euclid's Elements", "Concerning music"

Output filenames prefer the English title when available.

---

## Implementation Phases

### Phase 1: Foundation (MVP) ✅ COMPLETE

**Goal:** Validate Greek rendering and interlinear layout on Kindle

**Deliverables:**
- [x] ePub generator script (`create_kindle_epub.py`)
- [x] Full Iliad with interlinear glosses
- [x] CSS stylesheet optimized for Kindle
- [x] Dictionary with full LSJ/Cunliffe/Wiktionary entries

**Acceptance Criteria:**
- [x] Greek displays correctly with diacritics
- [x] Interlinear layout readable (inline format)
- [x] Navigation works (TOC, line links)
- [x] Dictionary lookups functional

### Phase 2: Essential Works (In Progress)

**Goal:** Publish high-demand works

**Deliverables:**
- [x] Full Iliad (Greek + Interlinear + Dictionary + Translations)
- [ ] Full Odyssey
- [ ] Aeneid (Latin)
- [ ] Greek New Testament
- [ ] Plato's Republic

### Phase 3: Automation

**Goal:** Scalable generation for full corpus

**Deliverables:**
- [x] Automated pipeline from database to ePub
- [ ] Batch generation for multiple works
- [ ] Quality validation tools
- [ ] Author collections (Complete Homer, etc.)

### Phase 4: Full Corpus

**Goal:** Complete Classics Viewer content as ePubs

**Deliverables:**
- [ ] All Greek works (~1,855)
- [ ] All Latin works (~230)
- [ ] Organized collections (split by 50MB for Send to Kindle)
- [ ] Website download page with instructions

---

## Resolved Questions

1. **Interlinear density:** Inline format with parenthetical glosses works well on all screen sizes
2. **Morphology display:** Included in dictionary entries, not inline (keeps text readable)
3. **Translation selection:** Include all available translators, grouped separately
4. **Dictionary approach:** Embedded dictionary pages (not custom MOBI) - words link to definitions
5. **Line numbering:** Include book prefix for clarity (3.114 not just 114)
6. **License:** Dynamically loaded from LICENSE.txt with source attribution

## Open Questions

1. **Updates:** How to handle corrections/updates to published ePubs?
2. **Website hosting:** Where to host download files? (GitHub releases, S3, etc.)
3. **Latin support:** Whitaker's Words dictionary integration for Latin works

---

## Appendix: Sample Content

### Sample Interlinear Page (Iliad 1.1-3) - Kindle Paperwhite Width

Shows how content wraps on a typical e-ink Kindle screen (~600px):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Book 1: The Rage of Achilles
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1   Μῆνιν     ἄειδε      θεά
    wrath     sing!     goddess

    Πηληϊάδεω        Ἀχιλῆος
    of-Peleus'-son   of-Achilles
.......................................

2   οὐλομένην    ἣ        μυρί᾽
    accursed    which    countless

    Ἀχαιοῖς        ἄλγε᾽     ἔθηκε
    to-Achaeans    pains     caused
.......................................

3   πολλὰς      δ᾽       ἰφθίμους
    many        and      mighty

    ψυχὰς      Ἄϊδι       προΐαψεν
    souls      to-Hades   sent-forth

    ἡρώων
    of-heroes
.......................................
```

### Same Content on Kindle Fire/Tablet (wider)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Book 1: The Rage of Achilles
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1   Μῆνιν   ἄειδε   θεά      Πηληϊάδεω        Ἀχιλῆος
    wrath   sing!   goddess  of-Peleus'-son   of-Achilles
................................................................

2   οὐλομένην   ἣ      μυρί᾽      Ἀχαιοῖς       ἄλγε᾽   ἔθηκε
    accursed    which  countless  to-Achaeans   pains   caused
................................................................

3   πολλὰς   δ᾽    ἰφθίμους   ψυχὰς    Ἄϊδι      προΐαψεν   ἡρώων
    many     and   mighty     souls    to-Hades  sent-forth of-heroes
................................................................
```

### Compact Inline Format (Alternative)

For denser display or prose works:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Book 1: The Rage of Achilles
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1  Μῆνιν (wrath) ἄειδε (sing!) θεά
(goddess) Πηληϊάδεω (of-Peleus'-son)
Ἀχιλῆος (of-Achilles)

2  οὐλομένην (accursed) ἣ (which)
μυρί᾽ (countless) Ἀχαιοῖς (to-
Achaeans) ἄλγε᾽ (pains) ἔθηκε
(caused)

3  πολλὰς (many) δ᾽ (and) ἰφθίμους
(mighty) ψυχὰς (souls) Ἄϊδι (to-
Hades) προΐαψεν (sent-forth) ἡρώων
(of-heroes)
```

---

## References

- [Kindle Publishing Guidelines](https://kdp.amazon.com/en_US/help/topic/G200645680)
- [ePub 3.0 Specification](https://www.w3.org/publishing/epub3/)
- [Kindle Format 8 (KF8)](https://www.amazon.com/gp/feature.html?docId=1000729511)
- [Calibre Documentation](https://manual.calibre-ebook.com/)
- [Gentium Plus Font](https://software.sil.org/gentium/)

---

*Document Version: 2.1*
*Created: December 2025*
*Updated: December 12, 2025*
*Status: Phase 2 In Progress - iOS sample list (41 works) generated*
