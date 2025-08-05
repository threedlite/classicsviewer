#!/usr/bin/env python3
"""
Fix translation alignment specifically for Aeschines texts.
This is a targeted fix that won't affect other authors.
"""

import sqlite3
import xml.etree.ElementTree as ET
import os
from collections import defaultdict

def fix_aeschines_alignment(dry_run=True):
    """
    Fix alignment for Aeschines texts only.
    These texts have the specific issue where section numbers were used as line numbers.
    """
    
    conn = sqlite3.connect('output/perseus_texts.db')
    cur = conn.cursor()
    
    # Only fix Aeschines texts (tlg0026)
    aeschines_books = [
        'tlg0026.tlg001.001',  # Against Timarchus
        'tlg0026.tlg002.001',  # On the Embassy
        'tlg0026.tlg003.001',  # Against Ctesiphon
    ]
    
    fixes_to_apply = []
    
    for book_id in aeschines_books:
        print(f"\nAnalyzing {book_id}...")
        
        # Get all text lines
        cur.execute("""
            SELECT line_number, line_text 
            FROM text_lines 
            WHERE book_id = ?
            ORDER BY CAST(line_number as INTEGER)
        """, (book_id,))
        
        lines = [(int(num), text) for num, text in cur.fetchall()]
        
        # Parse XML to get section boundaries
        work_id = book_id.rsplit('.', 1)[0]
        greek_path = f"../data-sources/canonical-greekLit/data/tlg0026/{work_id.split('.')[1]}/{work_id}.perseus-grc2.xml"
        
        if not os.path.exists(greek_path):
            print(f"  WARNING: Greek XML not found at {greek_path}")
            continue
            
        tree = ET.parse(greek_path)
        root = tree.getroot()
        ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
        
        # Build section-to-lines mapping using a simpler approach
        # First, create a full text string with line number markers
        line_positions = {}
        full_text = ""
        for line_num, line_text in lines:
            line_positions[len(full_text)] = line_num
            full_text += line_text + " "
        
        section_lines = {}
        
        # Find all sections
        sections = root.findall('.//tei:div[@type="textpart"][@subtype="section"]', ns)
        print(f"  Found {len(sections)} sections in XML")
        
        for i, section in enumerate(sections):
            section_num = section.get('n')
            if not section_num:
                continue
                
            try:
                section_num = int(section_num)
            except ValueError:
                continue
                
            # Get section text
            section_text = ''.join(section.itertext()).strip()
            if not section_text:
                continue
            
            # Get first few words to find position
            first_words = ' '.join(section_text.split()[:5])
            
            # Find where this section starts in the full text
            start_pos = full_text.find(first_words)
            if start_pos == -1:
                # Try with fewer words
                first_words = ' '.join(section_text.split()[:3])
                start_pos = full_text.find(first_words)
            
            if start_pos >= 0:
                # Find which line this position corresponds to
                start_line = None
                for pos, line_num in sorted(line_positions.items()):
                    if pos <= start_pos:
                        start_line = line_num
                    else:
                        break
                
                # Find end position (start of next section or end of text)
                if i < len(sections) - 1:
                    next_section = sections[i + 1]
                    next_text = ''.join(next_section.itertext()).strip()
                    if next_text:
                        next_words = ' '.join(next_text.split()[:5])
                        end_pos = full_text.find(next_words, start_pos + 1)
                        if end_pos == -1:
                            end_pos = len(full_text)
                    else:
                        end_pos = len(full_text)
                else:
                    end_pos = len(full_text)
                
                # Find all lines in this range
                section_line_nums = []
                for pos, line_num in sorted(line_positions.items()):
                    if start_pos <= pos < end_pos:
                        section_line_nums.append(line_num)
                
                if section_line_nums:
                    section_lines[section_num] = section_line_nums
                elif start_line:
                    # At least include the start line
                    section_lines[section_num] = [start_line]
            
        # Now we have the mapping, let's prepare the fixes
        cur.execute("""
            SELECT id, start_line, end_line, translation_text, translator
            FROM translation_segments 
            WHERE book_id = ?
            ORDER BY start_line
        """, (book_id,))
        
        translations = cur.fetchall()
        
        for trans_id, start_line, end_line, trans_text, translator in translations:
            # If start_line and end_line are the same and match a section number
            if start_line == end_line and start_line in section_lines:
                actual_lines = section_lines[start_line]
                if actual_lines:
                    new_start = min(actual_lines)
                    new_end = max(actual_lines)
                    
                    fixes_to_apply.append({
                        'book_id': book_id,
                        'trans_id': trans_id,
                        'old_start': start_line,
                        'old_end': end_line,
                        'new_start': new_start,
                        'new_end': new_end,
                        'preview': trans_text[:50] + '...'
                    })
        
        # Report findings
        print(f"  Found {len(section_lines)} sections")
        print(f"  Found {len(fixes_to_apply)} translations to fix")
    
    # Show what would be fixed
    print("\n=== PROPOSED FIXES ===")
    for fix in fixes_to_apply[:5]:  # Show first 5 as examples
        print(f"\n{fix['book_id']} - Translation ID {fix['trans_id']}:")
        print(f"  '{fix['preview']}'")
        print(f"  Current: lines {fix['old_start']}-{fix['old_end']}")
        print(f"  Fixed:   lines {fix['new_start']}-{fix['new_end']}")
    
    if len(fixes_to_apply) > 5:
        print(f"\n... and {len(fixes_to_apply) - 5} more fixes")
    
    if not dry_run and fixes_to_apply:
        print("\n=== APPLYING FIXES ===")
        for fix in fixes_to_apply:
            cur.execute("""
                UPDATE translation_segments 
                SET start_line = ?, end_line = ?
                WHERE id = ?
            """, (fix['new_start'], fix['new_end'], fix['trans_id']))
        
        conn.commit()
        print(f"Applied {len(fixes_to_apply)} fixes")
    else:
        print("\n(Dry run - no changes made. Run with dry_run=False to apply)")
    
    conn.close()

if __name__ == "__main__":
    # First do a dry run
    print("=== DRY RUN - Checking what would be fixed ===")
    fix_aeschines_alignment(dry_run=True)