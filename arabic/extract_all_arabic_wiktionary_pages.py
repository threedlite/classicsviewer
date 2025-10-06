#!/usr/bin/env python3
"""
Extract all Arabic language pages from Arabic Wiktionary dump.
Creates a cache file for faster subsequent processing.
"""

import bz2
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

SCRIPT_DIR = Path(__file__).parent
DUMP_FILE = SCRIPT_DIR.parent / "data-sources" / "arwiktionary-latest-pages-articles.xml.bz2"
OUTPUT_FILE = SCRIPT_DIR / "all_arabic_wiktionary_pages.json"

def is_content_page(title):
    """Check if this is a content page (not a MediaWiki system page)"""
    # Skip MediaWiki namespace pages (start with specific prefixes)
    skip_prefixes = [
        'ميدياويكي:',    # MediaWiki: namespace
        'قالب:',          # Template: namespace
        'ويكاموس:',       # Wiktionary: namespace
        'نقاش:',          # Talk: namespace
        'مستخدم:',        # User: namespace
        'تصنيف:',         # Category: namespace
        'مساعدة:',        # Help: namespace
        'ملف:',           # File: namespace
    ]
    return not any(title.startswith(prefix) for prefix in skip_prefixes)

def extract_pages_from_dump():
    """Extract all Arabic language pages from the dump"""

    if not DUMP_FILE.exists():
        print(f"ERROR: Dump file not found at {DUMP_FILE}")
        print(f"Download it first with:")
        print(f"  cd {DUMP_FILE.parent}")
        print(f"  wget https://dumps.wikimedia.org/arwiktionary/latest/arwiktionary-latest-pages-articles.xml.bz2")
        raise FileNotFoundError(f"Required dump file: {DUMP_FILE}")

    print(f"Reading dump: {DUMP_FILE}")
    print(f"File size: {DUMP_FILE.stat().st_size / 1024 / 1024:.1f} MB")
    print()
    print("This will take 2-3 minutes...")
    print()

    pages = []
    page_count = 0
    arabic_page_count = 0

    # MediaWiki XML namespace
    ns = {'mw': 'http://www.mediawiki.org/xml/export-0.11/'}

    # Parse compressed XML
    with bz2.open(DUMP_FILE, 'rt', encoding='utf-8') as f:
        # Use iterparse for memory efficiency
        context = ET.iterparse(f, events=('end',))

        for event, elem in context:
            if elem.tag == '{http://www.mediawiki.org/xml/export-0.11/}page':
                page_count += 1

                # Extract title and text
                title_elem = elem.find('mw:title', ns)
                revision_elem = elem.find('mw:revision', ns)

                if title_elem is not None and revision_elem is not None:
                    title = title_elem.text
                    text_elem = revision_elem.find('mw:text', ns)
                    text = text_elem.text if text_elem is not None else ''

                    # Check if this is a content page (skip system/meta pages)
                    if title and text and is_content_page(title):
                        pages.append({
                            'title': title,
                            'text': text
                        })
                        arabic_page_count += 1

                # Progress update
                if page_count % 10000 == 0:
                    print(f"Processed {page_count:,} pages, found {arabic_page_count:,} Arabic pages...")

                # Clear element to free memory
                elem.clear()

    print(f"\n✅ Extraction complete:")
    print(f"   Total pages processed: {page_count:,}")
    print(f"   Content pages found: {arabic_page_count:,}")

    return pages

def main():
    print("="*60)
    print("Extract Arabic Language Pages from Arabic Wiktionary")
    print("="*60)
    print()

    # Extract pages
    pages = extract_pages_from_dump()

    # Save to cache file
    print(f"\nSaving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)

    file_size = OUTPUT_FILE.stat().st_size / 1024 / 1024
    print(f"✅ Saved {len(pages):,} pages ({file_size:.1f} MB)")
    print()
    print("Cache file ready for pattern extraction:")
    print(f"  {OUTPUT_FILE}")
    print()
    print("Next step: Run extract_arabic_wiktionary_patterns.py")

if __name__ == "__main__":
    main()
