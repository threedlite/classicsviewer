#!/usr/bin/env python3
"""
Analyze the pattern of alignment issues to understand the root cause
"""

import sqlite3
import xml.etree.ElementTree as ET
import os

def analyze_pattern():
    conn = sqlite3.connect('output/perseus_texts.db')
    cur = conn.cursor()
    
    # Check a few specific cases
    test_cases = [
        ('tlg0026.tlg001.001', 'Aeschines - Against Timarchus'),  # Known issue
        ('tlg0012.tlg001.001', 'Homer - Iliad Book 1'),  # Should be OK
        ('tlg0086.tlg009.001', 'Aristotle - Eudemian Ethics Book 1'),  # Potential issue
    ]
    
    print("=== ANALYZING SPECIFIC CASES ===\n")
    
    for book_id, description in test_cases:
        print(f"\n{description} ({book_id}):")
        print("-" * 60)
        
        # Get text line info
        cur.execute("""
            SELECT 
                COUNT(*) as total_lines,
                MIN(line_number) as first_line,
                MAX(line_number) as last_line
            FROM text_lines 
            WHERE book_id = ?
        """, (book_id,))
        
        total_lines, first_line, last_line = cur.fetchone()
        print(f"Text lines: {total_lines} (from {first_line} to {last_line})")
        
        # Get translation info
        cur.execute("""
            SELECT 
                COUNT(*) as segments,
                MIN(start_line) as first_trans,
                MAX(end_line) as last_trans,
                SUM(CASE WHEN end_line IS NULL THEN 1 ELSE 0 END) as null_ends
            FROM translation_segments 
            WHERE book_id = ?
        """, (book_id,))
        
        segments, first_trans, last_trans, null_ends = cur.fetchone()
        if segments:
            print(f"Translation segments: {segments}")
            print(f"Translation range: {first_trans} to {last_trans}")
            print(f"Segments with NULL end_line: {null_ends}")
        else:
            print("No translations found")
        
        # Check if file exists and analyze structure
        work_id = book_id.rsplit('.', 1)[0]
        author_id = work_id.split('.')[0]
        
        # Try to find the Greek XML file
        greek_path = f"../data-sources/canonical-greekLit/data/{author_id}/{work_id.split('.')[1]}/{work_id}.perseus-grc2.xml"
        if os.path.exists(greek_path):
            tree = ET.parse(greek_path)
            root = tree.getroot()
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
            sections = root.findall('.//tei:div[@type="textpart"][@subtype="section"]', ns)
            print(f"XML sections: {len(sections)}")
            
            # Check if number of sections matches translation end line
            if len(sections) > 0 and last_trans and len(sections) == last_trans:
                print("⚠️  LIKELY ISSUE: Translation end line matches section count!")
        
        # Sample some translation segments
        cur.execute("""
            SELECT start_line, end_line, SUBSTR(translation_text, 1, 50)
            FROM translation_segments 
            WHERE book_id = ?
            ORDER BY start_line DESC
            LIMIT 3
        """, (book_id,))
        
        print("\nLast 3 translation segments:")
        for start, end, text in cur.fetchall():
            print(f"  Lines {start}-{end}: {text}...")
    
    conn.close()

if __name__ == "__main__":
    analyze_pattern()