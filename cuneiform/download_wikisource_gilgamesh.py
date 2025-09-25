#!/usr/bin/env python3
"""
Download all Epic of Gilgamesh pages from Wikisource and save locally.
This is Stephen Langdon's 1917 edition (public domain).
"""

import urllib.request
import time
import json
from pathlib import Path

def download_all_pages():
    """Download all pages of Gilgamesh transliteration from Wikisource."""

    data_dir = Path("data-sources/wikisource_gilgamesh")
    data_dir.mkdir(parents=True, exist_ok=True)

    all_pages = {}

    # Pages 7-16 contain the transliteration according to the index
    for page_num in range(7, 17):
        url = f"https://en.wikisource.org/wiki/Page:The_Epic_of_Gilgamesh_(Langdon_1917).djvu/{page_num}?action=raw"

        print(f"Downloading page {page_num}...")

        try:
            # Add user agent to avoid 403 error
            request = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })

            with urllib.request.urlopen(request) as response:
                content = response.read().decode('utf-8')

                # Save individual page
                page_file = data_dir / f"page_{page_num:03d}.txt"
                with open(page_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                all_pages[page_num] = content
                print(f"  ✓ Saved page {page_num} ({len(content)} bytes)")

            # Add delay to avoid rate limiting
            if page_num < 16:
                print("  Waiting 2 seconds...")
                time.sleep(2)

        except Exception as e:
            print(f"  ✗ Error downloading page {page_num}: {e}")
            # Try to continue with remaining pages
            print("  Waiting 5 seconds before continuing...")
            time.sleep(5)

    # Save metadata
    metadata = {
        'source': 'Wikisource',
        'work': 'The Epic of Gilgamesh',
        'translator': 'Stephen Langdon',
        'year': 1917,
        'license': 'Public Domain',
        'pages_downloaded': list(all_pages.keys()),
        'total_pages': len(all_pages),
        'url_pattern': 'https://en.wikisource.org/wiki/Page:The_Epic_of_Gilgamesh_(Langdon_1917).djvu/{page_num}'
    }

    metadata_file = data_dir / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

    print(f"\n✓ Downloaded {len(all_pages)} pages to {data_dir}")
    print(f"✓ Metadata saved to {metadata_file}")

    return all_pages

if __name__ == '__main__':
    download_all_pages()