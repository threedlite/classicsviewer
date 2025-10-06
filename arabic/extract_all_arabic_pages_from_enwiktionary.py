#!/usr/bin/env python3
"""
Extract ALL Arabic pages from English Wiktionary dump into a smaller JSON cache file.
This runs ONCE to create a cache, then all subsequent scripts use the cache.

Similar to extract_all_greek_pages.py for Greek.
"""

import json
import bz2
import xml.etree.ElementTree as ET
import re
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_SOURCES = SCRIPT_DIR.parent / "data-sources"
DUMP_FILE = DATA_SOURCES / "enwiktionary-latest-pages-articles.xml.bz2"
OUTPUT_FILE = SCRIPT_DIR / "all_arabic_enwiktionary_pages.json"

def is_arabic_word(title):
    """Check if title contains Arabic characters"""
    if not title:
        return False
    # Arabic Unicode ranges: 0600-06FF, 0750-077F, 08A0-08FF, FB50-FDFF, FE70-FEFF
    arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
    return bool(arabic_pattern.search(title))

def extract_all_arabic_pages():
    """Extract all Arabic pages from English Wiktionary dump"""

    if not DUMP_FILE.exists():
        print(f"ERROR: English Wiktionary dump not found at {DUMP_FILE}")
        print(f"Download with: wget https://dumps.wikimedia.org/enwiktionary/latest/enwiktionary-latest-pages-articles.xml.bz2")
        raise FileNotFoundError(f"Required dump file: {DUMP_FILE}")

    namespace = {'ns': 'http://www.mediawiki.org/xml/export-0.11/'}
    arabic_pages = {}
    processed_pages = 0
    start_time = time.time()

    print(f"Extracting all Arabic pages from English Wiktionary...")
    print(f"Source: {DUMP_FILE}")
    print(f"Output: {OUTPUT_FILE}")
    print()

    with bz2.open(DUMP_FILE, 'rt', encoding='utf-8', errors='ignore') as f:
        for event, elem in ET.iterparse(f, events=('start', 'end')):
            if event == 'end' and elem.tag.endswith('page'):
                processed_pages += 1

                title_elem = elem.find('.//ns:title', namespace)
                text_elem = elem.find('.//ns:text', namespace)

                if title_elem is not None and text_elem is not None:
                    title = title_elem.text

                    # Skip non-main namespace
                    if title and ':' in title and not title.startswith('Reconstruction:'):
                        elem.clear()
                        continue

                    # Check if Arabic word
                    if title and is_arabic_word(title):
                        text = text_elem.text or ''

                        # Only include pages with Arabic sections
                        if '==Arabic==' in text:
                            arabic_pages[title] = text

                            if len(arabic_pages) % 1000 == 0:
                                elapsed = time.time() - start_time
                                rate = processed_pages / elapsed if elapsed > 0 else 0
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] Progress:")
                                print(f"  Pages processed: {processed_pages:,}")
                                print(f"  Arabic pages found: {len(arabic_pages):,}")
                                print(f"  Rate: {rate:.0f} pages/second")
                                print(f"  Latest: {title}")

                elem.clear()

                # Status update every 100,000 pages
                if processed_pages % 100000 == 0:
                    elapsed = time.time() - start_time
                    rate = processed_pages / elapsed if elapsed > 0 else 0
                    print(f"  Processed {processed_pages:,} Wiktionary pages ({rate:.0f} pages/sec)...")

    # Save results
    print(f"\nSaving {len(arabic_pages):,} Arabic pages to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(arabic_pages, f, ensure_ascii=False, indent=2)

    # Summary
    elapsed_total = time.time() - start_time
    file_size = OUTPUT_FILE.stat().st_size / 1024 / 1024
    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Total time: {elapsed_total/60:.1f} minutes")
    print(f"Pages processed: {processed_pages:,}")
    print(f"Arabic pages extracted: {len(arabic_pages):,}")
    print(f"Processing rate: {processed_pages/elapsed_total:.0f} pages/second")
    print(f"Output file: {OUTPUT_FILE} ({file_size:.1f} MB)")

    return arabic_pages

def main():
    print("="*60)
    print("English Wiktionary Arabic Page Extraction")
    print("="*60)
    print()

    # Check if cache already exists
    if OUTPUT_FILE.exists():
        file_size = OUTPUT_FILE.stat().st_size / 1024 / 1024
        print(f"Cache file already exists: {OUTPUT_FILE}")
        print(f"Size: {file_size:.1f} MB")

        # Load and show stats
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            pages = json.load(f)
        print(f"Pages cached: {len(pages):,}")
        print()
        print("To regenerate, delete the cache file and re-run this script.")
        return pages

    # Extract pages (one-time, takes ~10-15 minutes)
    pages = extract_all_arabic_pages()

    return pages

if __name__ == "__main__":
    main()
