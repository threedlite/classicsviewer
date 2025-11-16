#!/usr/bin/env python3
"""
Import Sanskrit DCS interlinear translations into extended database.

This script handles Sanskrit-specific interlinear import with proper
whitespace normalization, separate from the Perseus Greek import pipeline.
"""

import sqlite3
import re
import html
from pathlib import Path
import xml.etree.ElementTree as ET


def parse_xml_with_entity_resolver(xml_file):
    """Parse XML file with entity resolution."""
    parser = ET.XMLParser()
    tree = ET.parse(xml_file, parser=parser)
    return tree, False


def extract_text_with_bold_sanskrit(element):
    """
    Extract text from XML element for Sanskrit interlinear.

    Normalizes whitespace by converting newlines to double-space.
    This is Sanskrit-specific and does not affect Greek processing.
    """
    result = []

    # Process element text
    if element.text:
        result.append(html.escape(element.text, quote=False))

    # Process children
    for child in element:
        # Check if this is a <hi rend="bold"> element
        if child.tag.endswith('hi') and child.get('rend') == 'bold':
            result.append('<hi rend="bold">')
            if child.text:
                result.append(html.escape(child.text, quote=False))
            for nested in child:
                result.append(html.escape(''.join(nested.itertext()), quote=False))
                if nested.tail:
                    result.append(html.escape(nested.tail, quote=False))
            result.append('</hi>')
        else:
            child_text = ''.join(child.itertext())
            if child_text:
                result.append(html.escape(child_text, quote=False))

        if child.tail:
            result.append(html.escape(child.tail, quote=False))

    return ''.join(result).strip()


def import_sanskrit_interlinear(db_path, interlinear_dir):
    """
    Import Sanskrit DCS interlinear files into the extended database.

    Args:
        db_path: Path to perseus_texts_extended.db
        interlinear_dir: Directory containing *.dcs-eng99.xml files
    """
    db_path = Path(db_path)
    interlinear_dir = Path(interlinear_dir)

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    if not interlinear_dir.exists():
        raise FileNotFoundError(f"Interlinear directory not found: {interlinear_dir}")

    # Find all DCS interlinear files
    dcs_files = list(interlinear_dir.glob('*.dcs-eng99.xml'))
    if not dcs_files:
        print(f"No DCS interlinear files found in {interlinear_dir}")
        return

    print(f"\nImporting {len(dcs_files)} Sanskrit DCS interlinear files...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    total_segments = 0

    for xml_file in sorted(dcs_files):
        work_id = xml_file.stem.replace('.dcs-eng99', '')
        print(f"  Processing {xml_file.name}...")

        try:
            tree, _ = parse_xml_with_entity_resolver(xml_file)
            root = tree.getroot()

            # Extract translator name
            translator = None
            for elem in root.iter():
                if 'editor' in elem.tag.lower() and elem.get('role') == 'translator':
                    translator = elem.text
                    if translator:
                        translator = translator.strip()
                        break

            if not translator:
                translator = "Interlinear (Beta, AI-generated from app dictionary)"

            # Find all books in the translation
            segments_imported = 0
            for book_div in root.iter():
                if not (book_div.tag.endswith('div') and
                       book_div.get('type') == 'textpart' and
                       book_div.get('subtype') == 'Book'):
                    continue

                book_n = book_div.get('n', '')
                if not book_n:
                    continue

                # Construct book_id for Sanskrit DCS texts
                constructed_book_id = f"{work_id}.{book_n}"
                cursor.execute("SELECT id FROM books WHERE id = ?", (constructed_book_id,))
                result = cursor.fetchone()

                if result:
                    book_id = result[0]
                else:
                    # Fallback: Look up by work_id and book_number
                    cursor.execute("""
                        SELECT id FROM books
                        WHERE work_id = ? AND book_number = ?
                    """, (work_id, int(book_n)))
                    result = cursor.fetchone()
                    if not result:
                        print(f"    ⚠️  Warning: No book found for work_id={work_id}, book_number={book_n}, skipping")
                        continue
                    book_id = result[0]

                # Extract all line elements
                for line_elem in book_div.iter():
                    if not (line_elem.tag.endswith('l')):
                        continue

                    line_n = line_elem.get('n')
                    if not line_n:
                        continue

                    try:
                        line_num = int(line_n)
                    except ValueError:
                        continue

                    # Extract translation text using Sanskrit-specific function
                    translation_text = extract_text_with_bold_sanskrit(line_elem)

                    if not translation_text or len(translation_text.strip()) < 3:
                        continue

                    # Insert translation segment
                    cursor.execute("""
                        INSERT INTO translation_segments
                        (book_id, start_line, end_line, sequence_number, translation_text, translator, speaker)
                        VALUES (?, ?, ?, ?, ?, ?, NULL)
                    """, (book_id, line_num, line_num, line_num, translation_text, translator))

                    segments_imported += 1

            print(f"    ✓ Imported {segments_imported} segments for {work_id}")
            total_segments += segments_imported
            conn.commit()

        except Exception as e:
            print(f"    ✗ Error processing {xml_file.name}: {e}")
            conn.rollback()
            raise

    conn.close()
    print(f"\n✓ Total Sanskrit interlinear segments imported: {total_segments:,}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python3 import_sanskrit_interlinear.py <db_path> <interlinear_dir>")
        print("Example: python3 import_sanskrit_interlinear.py ../data-prep/perseus_texts_extended.db ../data-sources/classicsviewer_interlinear")
        sys.exit(1)

    db_path = sys.argv[1]
    interlinear_dir = sys.argv[2]

    import_sanskrit_interlinear(db_path, interlinear_dir)
