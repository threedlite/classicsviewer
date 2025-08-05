# Wiktionary Extraction Guide

## Overview

This guide documents the optimized process for extracting Greek lemma mappings and definitions from Wiktionary. We achieved a **50x speedup** by pre-caching Greek pages instead of repeatedly scanning the entire dump.

## The Problem

- **Corpus**: 179,325 unique Greek words from classical texts
- **Goal**: Find lemma mappings (inflected form → base form) and definitions
- **Challenge**: Wiktionary dump has 10+ million pages, but only ~1% are Greek

### Initial Approach (Slow)
- Scan entire 10M+ page dump for EACH word lookup
- Processing rate: ~4 mappings/second
- Estimated time: **12+ hours**

### Optimized Approach (Fast)
1. Extract ALL Greek pages once into a cache file
2. Search only the cached Greek pages for our corpus words
- Processing rate: ~6,200 mappings/second
- Total time: **~15 minutes**

## Step-by-Step Process

### 1. Download Wiktionary Dump

```bash
# Download latest English Wiktionary dump (~1.4GB compressed)
wget https://dumps.wikimedia.org/enwiktionary/latest/enwiktionary-latest-pages-articles.xml.bz2
```

### 2. Extract Corpus Words

First, extract all unique words from your corpus:

```bash
python3 extract_unique_words_from_corpus.py
# Creates: all_greek_words_in_corpus.json (179,325 words)
```

### 3. Pre-Extract Greek Pages (KEY OPTIMIZATION)

Instead of scanning 10M pages repeatedly, extract all Greek pages once:

```bash
python3 extract_all_greek_pages.py
```

**What it does:**
- Scans the entire Wiktionary dump ONCE
- Extracts pages with Greek characters in the title
- Filters for pages with Ancient Greek or Greek sections
- Creates `all_greek_wiktionary_pages.json` (~46MB, 124k pages)

**Performance:**
- Time: ~10 minutes
- Rate: ~16,000 pages/second
- Output: 124,116 Greek pages (1.2% of total)

### 4. Extract Inflection Mappings

Now search the cached Greek pages for inflection information:

```bash
python3 extract_inflections_from_cache.py extract
```

**What it does:**
- Loads the 46MB cache (instead of 1.4GB dump)
- Searches for inflected forms in our corpus
- Extracts lemma and morphological information
- Creates `inflection_mappings_final.json`

**Performance:**
- Time: ~2.5 seconds
- Rate: ~6,200 mappings/second
- Found: 15,592 inflection mappings

### 5. Add to Database

```bash
python3 -c "
import json
import sqlite3

with open('inflection_extraction_results/inflection_mappings_final.json', 'r') as f:
    mappings = json.load(f)

conn = sqlite3.connect('../perseus_texts.db')
cursor = conn.cursor()

for norm_form, mapping in mappings.items():
    word_form = mapping['word_form']
    lemma_norm = mapping['lemma_normalized']
    morph_info = ', '.join(mapping['morphology']) if mapping['morphology'] else None
    
    try:
        cursor.execute('''
            INSERT INTO lemma_map (word_form, word_normalized, lemma, confidence, source, morph_info)
            VALUES (?, ?, ?, 0.95, 'wiktionary_inflection', ?)
        ''', (word_form, norm_form, lemma_norm, morph_info))
    except sqlite3.IntegrityError:
        pass  # Already exists

conn.commit()
conn.close()
"
```

## Key Scripts

### extract_all_greek_pages.py
```python
def extract_all_greek_pages(dump_file, output_file):
    """Extract all Greek pages from Wiktionary dump"""
    
    greek_pages = {}
    with bz2.open(dump_file, 'rt', encoding='utf-8') as f:
        for event, elem in ET.iterparse(f, events=('start', 'end')):
            if event == 'end' and elem.tag.endswith('page'):
                title = get_title(elem)
                
                # Check if Greek word
                if is_greek_word(title):
                    text = get_text(elem)
                    
                    # Only include pages with Greek content
                    if '==Ancient Greek==' in text or '==Greek==' in text:
                        greek_pages[title] = text
                
                elem.clear()  # Important: free memory
    
    # Save as JSON for fast loading
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(greek_pages, f, ensure_ascii=False, indent=2)
```

### extract_inflections_from_cache.py
```python
def process_greek_pages_for_corpus(greek_pages_file, corpus_words_file):
    """Process pre-extracted Greek pages to find inflection mappings"""
    
    # Load corpus words
    with open(corpus_words_file, 'r') as f:
        corpus_words = json.load(f)
    
    # Load cached Greek pages (fast!)
    with open(greek_pages_file, 'r') as f:
        greek_pages = json.load(f)
    
    # Now we only search 124k pages instead of 10M+
    for title, text in greek_pages.items():
        normalized_title = normalize_greek(title)
        
        if normalized_title in corpus_words:
            inflection_info = extract_inflection_info(title, text)
            if inflection_info:
                found_mappings[normalized_title] = inflection_info
```

## Why It's Fast

1. **Single Pass Extraction**: We scan the 10M+ pages only ONCE to extract Greek pages
2. **Memory-Efficient Processing**: Using iterparse() with elem.clear() to handle large XML
3. **JSON Cache**: Pre-extracted pages load instantly into memory
4. **Targeted Search**: Only searching relevant pages (124k vs 10M)
5. **Normalized Lookups**: Using normalized Greek for fast set membership tests

## Results

### Performance Comparison
| Metric | Original | Optimized | Improvement |
|--------|----------|-----------|-------------|
| Pages to scan | 10M × 179k words | 10M (once) + 124k | ~1,450x fewer |
| Processing rate | 4 maps/sec | 6,200 maps/sec | 1,550x faster |
| Total time | ~12 hours | ~15 minutes | 48x faster |
| Memory usage | ~200MB | ~250MB | Similar |

### Data Found
- Greek pages in Wiktionary: 124,116 (1.2% of total)
- Inflection mappings found: 15,592 (8.7% of corpus)
- Dictionary entries found: 6,755 (3.8% of corpus)

## Rerunning the Process

To run this process again with a new corpus or updated Wiktionary dump:

```bash
# 1. Prepare corpus words
python3 extract_unique_words_from_corpus.py

# 2. Extract Greek pages (10 min)
python3 extract_all_greek_pages.py

# 3. Find inflection mappings (few seconds)
python3 extract_inflections_from_cache.py extract

# 4. Find dictionary definitions (optional)
python3 extract_definitions_from_cache.py extract

# 5. Add to database
python3 extract_inflections_from_cache.py add
```

## Further Optimizations

1. **Parallel Processing**: Could use multiprocessing for the initial extraction
2. **Streaming JSON**: For very large caches, use JSON streaming
3. **Binary Format**: Store cache in MessagePack or Protocol Buffers for faster I/O
4. **Incremental Updates**: Only process new/changed Wiktionary pages
5. **Language-Specific Dump**: Some Wiktionaries offer language-specific dumps

## Lessons Learned

1. **Profile First**: We found that 99% of time was wasted scanning non-Greek pages
2. **Cache Intermediate Results**: Pre-processing saves enormous time on repeated operations
3. **Choose the Right Data Structure**: JSON is fast enough for 100k+ entries
4. **Memory vs Speed**: Loading 46MB into memory is fine on modern systems
5. **Iterate on Small Samples**: Test extraction logic on known examples first