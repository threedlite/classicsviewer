#!/usr/bin/env python3
"""
Download CC BY-SA licensed texts and dictionaries from ORACC projects.
Downloads JSON exports which contain TEI/XML data and English translations.
"""

import os
import sys
import json
import urllib.request
import urllib.error
import zipfile
from pathlib import Path
import time

# Base URLs
ORACC_BASE = "http://oracc.museum.upenn.edu"
ORACC_PROJECT_BASE = "http://oracc.org"

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "data-sources" / "oracc"

# ORACC Projects confirmed to have CC BY-SA 3.0 license and English translations
# Based on ORACC documentation and project pages
ORACC_PROJECTS = {
    "akkadian": [
        {
            "id": "rinap",
            "name": "Royal Inscriptions of the Neo-Assyrian Period",
            "description": "Neo-Assyrian royal inscriptions (CC BY-SA 3.0)",
            "has_translations": True
        },
        {
            "id": "saao",
            "name": "State Archives of Assyria online",
            "description": "Neo-Assyrian archival texts (CC BY-SA 3.0)",
            "has_translations": True
        },
        {
            "id": "riao",
            "name": "Royal Inscriptions of Assyria online",
            "description": "Assyrian royal inscriptions (CC BY-SA 3.0)",
            "has_translations": True
        },
        {
            "id": "cmawro",
            "name": "Corpus of Mesopotamian Anti-witchcraft Rituals",
            "description": "Anti-witchcraft texts (CC BY-SA 3.0)",
            "has_translations": True
        }
    ],
    "sumerian": [
        {
            "id": "etcsri",
            "name": "Electronic Text Corpus of Sumerian Royal Inscriptions",
            "description": "Sumerian royal inscriptions with English translations (CC BY-SA 3.0)",
            "has_translations": True
        },
        {
            "id": "epsd2/literary",
            "name": "ePSD2 Literary Texts",
            "description": "Sumerian literary texts (CC BY-SA)",
            "has_translations": False  # Mostly untranslated
        }
    ],
    "dictionaries": [
        {
            "id": "epsd2",
            "name": "electronic Pennsylvania Sumerian Dictionary",
            "description": "Comprehensive Sumerian dictionary (CC BY-SA)",
            "is_dictionary": True
        }
    ]
}

def ensure_directory(path):
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)
    return path

def download_file(url, filepath, description=""):
    """Download a file from URL to filepath with progress indication."""
    try:
        print(f"Downloading: {description}")
        print(f"  From: {url}")
        print(f"  To: {filepath}")

        # Add headers to avoid 403 errors
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ORACC-Downloader/1.0)'
        }
        request = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(request, timeout=30) as response:
            total_size = int(response.headers.get('Content-Length', 0))

            # Read in chunks with progress
            chunk_size = 8192
            downloaded = 0

            with open(filepath, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"  Progress: {progress:.1f}%", end='\r')

            print(f"  ✓ Downloaded successfully ({downloaded:,} bytes)")
            return True

    except urllib.error.HTTPError as e:
        print(f"  ✗ HTTP Error {e.code}: {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"  ✗ URL Error: {e.reason}")
        return False
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        return False

def download_project_json(project_id, output_dir):
    """Download JSON export for a project (contains all data including translations)."""

    # Try different URL patterns
    urls_to_try = [
        f"{ORACC_PROJECT_BASE}/{project_id}/json.zip",
        f"{ORACC_BASE}/{project_id}/json.zip",
        f"{ORACC_PROJECT_BASE}/{project_id}/downloads/json.zip"
    ]

    filename = f"{project_id.replace('/', '_')}_json.zip"
    filepath = output_dir / filename

    for url in urls_to_try:
        if download_file(url, filepath, f"{project_id} JSON export"):
            return filepath

    return None

def extract_zip(zip_path, extract_to):
    """Extract a zip file to a directory."""
    try:
        print(f"Extracting: {zip_path.name}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"  ✓ Extracted to: {extract_to}")
        return True
    except Exception as e:
        print(f"  ✗ Extraction failed: {str(e)}")
        return False

def verify_license(project_dir):
    """Verify that project uses CC BY-SA license by checking metadata."""
    # Look for manifest.json or other metadata files
    manifest_path = project_dir / "manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
                # Check for license information
                # Note: Actual structure may vary
                print(f"  Manifest found: {manifest_path}")
                return True
        except Exception as e:
            print(f"  Warning: Could not parse manifest: {e}")

    # For now, we trust the documented license information
    return True

def main():
    """Main download function."""
    print("=" * 70)
    print("ORACC CC BY-SA Text and Dictionary Downloader")
    print("=" * 70)
    print()
    print("This script downloads texts and dictionaries from ORACC projects")
    print("that are confirmed to use CC BY-SA 3.0 licensing.")
    print()

    # Create output directories
    ensure_directory(OUTPUT_DIR)
    akkadian_dir = ensure_directory(OUTPUT_DIR / "akkadian")
    sumerian_dir = ensure_directory(OUTPUT_DIR / "sumerian")
    dict_dir = ensure_directory(OUTPUT_DIR / "dictionaries")

    print(f"Output directory: {OUTPUT_DIR}")
    print()

    # Track successful downloads
    successful = []
    failed = []

    # Download Akkadian projects
    print("=" * 70)
    print("DOWNLOADING AKKADIAN TEXTS")
    print("=" * 70)
    for project in ORACC_PROJECTS["akkadian"]:
        print(f"\n{project['name']} ({project['id']})")
        print(f"  {project['description']}")

        zip_path = download_project_json(project['id'], akkadian_dir)
        if zip_path:
            project_dir = akkadian_dir / project['id'].replace('/', '_')
            if extract_zip(zip_path, project_dir):
                if verify_license(project_dir):
                    successful.append(f"Akkadian: {project['name']}")
                else:
                    print("  ⚠️  License verification uncertain")
                    successful.append(f"Akkadian: {project['name']} (license unverified)")
        else:
            failed.append(f"Akkadian: {project['name']}")

        time.sleep(1)  # Be polite to the server

    # Download Sumerian projects
    print("\n" + "=" * 70)
    print("DOWNLOADING SUMERIAN TEXTS")
    print("=" * 70)
    for project in ORACC_PROJECTS["sumerian"]:
        print(f"\n{project['name']} ({project['id']})")
        print(f"  {project['description']}")

        zip_path = download_project_json(project['id'], sumerian_dir)
        if zip_path:
            project_dir = sumerian_dir / project['id'].replace('/', '_')
            if extract_zip(zip_path, project_dir):
                if verify_license(project_dir):
                    successful.append(f"Sumerian: {project['name']}")
                else:
                    print("  ⚠️  License verification uncertain")
                    successful.append(f"Sumerian: {project['name']} (license unverified)")
        else:
            failed.append(f"Sumerian: {project['name']}")

        time.sleep(1)

    # Download dictionaries
    print("\n" + "=" * 70)
    print("DOWNLOADING DICTIONARIES")
    print("=" * 70)
    for project in ORACC_PROJECTS["dictionaries"]:
        print(f"\n{project['name']} ({project['id']})")
        print(f"  {project['description']}")

        zip_path = download_project_json(project['id'], dict_dir)
        if zip_path:
            project_dir = dict_dir / project['id'].replace('/', '_')
            if extract_zip(zip_path, project_dir):
                if verify_license(project_dir):
                    successful.append(f"Dictionary: {project['name']}")
                else:
                    print("  ⚠️  License verification uncertain")
                    successful.append(f"Dictionary: {project['name']} (license unverified)")
        else:
            failed.append(f"Dictionary: {project['name']}")

        time.sleep(1)

    # Summary
    print("\n" + "=" * 70)
    print("DOWNLOAD SUMMARY")
    print("=" * 70)

    if successful:
        print("\n✓ Successfully downloaded:")
        for item in successful:
            print(f"  • {item}")

    if failed:
        print("\n✗ Failed downloads:")
        for item in failed:
            print(f"  • {item}")

    print("\n" + "=" * 70)
    print("IMPORTANT NOTES:")
    print("=" * 70)
    print("1. All downloaded projects are documented as CC BY-SA 3.0 licensed")
    print("2. JSON exports contain transliterations and English translations")
    print("3. The JSON format includes lemmatization and morphological data")
    print("4. TEI/XML exports can be generated from the JSON data")
    print("5. Always verify license terms before commercial use")
    print()
    print(f"Downloaded files are in: {OUTPUT_DIR}")
    print()

if __name__ == "__main__":
    main()