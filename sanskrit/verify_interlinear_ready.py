#!/usr/bin/env python3
"""
Verify that Sanskrit database and interlinear files are ready for import.
Checks that work IDs and book IDs will match correctly.
"""

import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

def main():
    import sys
    db_path = Path('sanskrit_texts.db')

    # Accept interlinear directory as argument, default to shared location
    if len(sys.argv) > 1:
        interlinear_dir = Path(sys.argv[1])
    else:
        interlinear_dir = Path('../data-sources/classicsviewer_interlinear')

    if not db_path.exists():
        print("❌ sanskrit_texts.db not found")
        return False

    # Get all works from database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id, title_english FROM works ORDER BY id")
    works = cursor.fetchall()
    print(f"✓ Found {len(works)} works in database")

    # Get all books from database
    cursor.execute("SELECT id, work_id, book_number FROM books ORDER BY work_id, book_number")
    books = cursor.fetchall()
    print(f"✓ Found {len(books)} books in database")

    # Check XML files exist
    xml_files = list(interlinear_dir.glob('*.dcs-eng99.xml'))
    print(f"✓ Found {len(xml_files)} interlinear XML files")

    if len(xml_files) != len(works):
        print(f"⚠️  Warning: {len(works)} works but {len(xml_files)} XML files")

    # Sample verification: Check first 5 works
    print("\n📋 Sample verification (first 5 works):")
    mismatches = []

    for work_id, title in works[:5]:
        xml_file = interlinear_dir / f"{work_id}.dcs-eng99.xml"

        if not xml_file.exists():
            print(f"  ❌ {work_id}: No XML file")
            mismatches.append(work_id)
            continue

        # Parse XML and check book numbers
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            # Find book divs
            xml_books = []
            for div in root.iter():
                if (div.tag.endswith('div') and
                    div.get('type') == 'textpart' and
                    div.get('subtype') == 'Book'):
                    book_n = div.get('n')
                    if book_n:
                        xml_books.append(book_n)

            # Get database books for this work
            cursor.execute("SELECT book_number FROM books WHERE work_id = ? ORDER BY book_number", (work_id,))
            db_books = [str(row[0]) for row in cursor.fetchall()]

            # Check if they match
            if set(xml_books) == set(db_books):
                print(f"  ✅ {work_id}: {len(db_books)} books match")
            else:
                print(f"  ⚠️  {work_id}: DB has {db_books[:3]}..., XML has {xml_books[:3]}...")
                mismatches.append(work_id)

        except Exception as e:
            print(f"  ❌ {work_id}: XML parse error: {e}")
            mismatches.append(work_id)

    conn.close()

    if mismatches:
        print(f"\n⚠️  Found {len(mismatches)} potential issues in sample")
        return False
    else:
        print(f"\n✅ All sampled works verified - interlinear import should work!")
        return True

if __name__ == '__main__':
    main()
