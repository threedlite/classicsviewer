#!/usr/bin/env python3
"""
Download Stephen Langdon's Sumerian texts from public domain sources.
These are early 20th century publications now in public domain.
"""

import urllib.request
import json
from pathlib import Path

def download_sumerian_texts():
    """Download Langdon's Sumerian Liturgies and Psalms from Project Gutenberg."""

    data_dir = Path("data-sources/langdon_sumerian")
    data_dir.mkdir(parents=True, exist_ok=True)

    texts_to_download = [
        {
            'name': 'Sumerian Liturgies and Psalms',
            'url': 'https://www.gutenberg.org/files/31935/31935-0.txt',
            'filename': 'sumerian_liturgies_psalms.txt',
            'author': 'Stephen Langdon',
            'year': 1919,
            'source': 'Project Gutenberg #31935'
        }
    ]

    for text_info in texts_to_download:
        print(f"Downloading {text_info['name']}...")

        try:
            request = urllib.request.Request(text_info['url'], headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })

            with urllib.request.urlopen(request) as response:
                content = response.read().decode('utf-8')

                # Save the text
                text_file = data_dir / text_info['filename']
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                print(f"  ✓ Saved to {text_file} ({len(content)} bytes)")

        except Exception as e:
            print(f"  ✗ Error downloading {text_info['name']}: {e}")

    # Save metadata
    metadata = {
        'source': 'Project Gutenberg',
        'texts': texts_to_download,
        'license': 'Public Domain',
        'notes': 'Stephen Langdon publications from 1919, over 100 years old'
    }

    metadata_file = data_dir / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

    print(f"\n✓ Metadata saved to {metadata_file}")
    print(f"✓ Downloaded Sumerian texts to {data_dir}")

if __name__ == '__main__':
    download_sumerian_texts()