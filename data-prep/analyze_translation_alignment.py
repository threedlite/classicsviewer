#!/usr/bin/env python3
"""
Analyze translation alignment issues for Aeschines Against Timarchus
"""

import sqlite3
import xml.etree.ElementTree as ET

def analyze_alignment():
    # Connect to database
    conn = sqlite3.connect('output/perseus_texts.db')
    cur = conn.cursor()
    
    # Get Greek text structure
    print("=== GREEK TEXT STRUCTURE ===")
    cur.execute("""
        SELECT line_number, line_text 
        FROM text_lines 
        WHERE book_id = 'tlg0026.tlg001.001' 
        AND line_number IN ('1', '2', '195', '196', '860', '861', '865', '866')
    """)
    
    for line_num, text in cur.fetchall():
        print(f"Line {line_num}: {text[:60]}...")
    
    # Analyze the XML structure
    print("\n=== XML STRUCTURE ANALYSIS ===")
    
    # Parse Greek XML
    greek_file = '../data-sources/canonical-greekLit/data/tlg0026/tlg001/tlg0026.tlg001.perseus-grc2.xml'
    tree = ET.parse(greek_file)
    root = tree.getroot()
    
    # Find namespace
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    
    # Count sections and lines
    sections = root.findall('.//tei:div[@type="textpart"][@subtype="section"]', ns)
    print(f"Total sections in Greek XML: {len(sections)}")
    
    # Check how lines are structured in section 196
    section_196 = None
    for section in sections:
        if section.get('n') == '196':
            section_196 = section
            break
    
    if section_196:
        text_content = ''.join(section_196.itertext()).strip()
        print(f"\nSection 196 content length: {len(text_content)} chars")
        print(f"First 200 chars: {text_content[:200]}...")
    
    # Check translation coverage
    print("\n=== TRANSLATION COVERAGE ===")
    cur.execute("""
        SELECT 
            COUNT(DISTINCT start_line) as sections_with_translation,
            MIN(start_line) as first_translated,
            MAX(end_line) as last_translated
        FROM translation_segments 
        WHERE book_id = 'tlg0026.tlg001.001'
    """)
    
    result = cur.fetchone()
    print(f"Sections with translation: {result[0]}")
    print(f"Translation range: {result[1]} - {result[2]}")
    
    # The issue: section numbers were used as line numbers
    print("\n=== THE PROBLEM ===")
    print("The import process treated XML section numbers (1-196) as line numbers,")
    print("but the actual text has 866 lines. This means only the first 196 lines")
    print("out of 866 have translations assigned.")
    
    conn.close()

if __name__ == "__main__":
    analyze_alignment()