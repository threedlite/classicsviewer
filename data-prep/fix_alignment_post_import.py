#!/usr/bin/env python3
"""
Fix translation alignment after database import.
This is a temporary solution until the import process is debugged.
"""

import sqlite3
import shutil
from datetime import datetime

def fix_alignments():
    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2("output/perseus_texts.db", f"output/perseus_texts_backup_{timestamp}.db")
    print(f"Created backup: output/perseus_texts_backup_{timestamp}.db")
    
    conn = sqlite3.connect("output/perseus_texts.db")
    cur = conn.cursor()
    
    # Find all books with potential alignment issues
    cur.execute("""
        SELECT 
            b.id as book_id,
            (SELECT MAX(CAST(line_number as INTEGER)) FROM text_lines WHERE book_id = b.id) as max_line,
            (SELECT MAX(end_line) FROM translation_segments WHERE book_id = b.id) as max_trans,
            (SELECT COUNT(*) FROM translation_segments WHERE book_id = b.id) as trans_count
        FROM books b
        WHERE EXISTS (SELECT 1 FROM translation_segments WHERE book_id = b.id)
    """)
    
    books = cur.fetchall()
    fixed_count = 0
    
    for book_id, max_line, max_trans, trans_count in books:
        if not max_line or not max_trans:
            continue
            
        coverage = (max_trans / max_line * 100)
        
        # Fix if coverage is low and max_trans equals trans_count (section numbering)
        if coverage < 50 and max_trans == trans_count and max_line > max_trans * 2:
            print(f"\nFixing {book_id}:")
            print(f"  Lines: {max_line}, Translations: {trans_count} (currently up to line {max_trans})")
            
            # Calculate mapping
            lines_per_section = max_line / max_trans
            
            # Update all segments
            cur.execute("""
                SELECT id, start_line, end_line
                FROM translation_segments 
                WHERE book_id = ? AND start_line = end_line
                ORDER BY start_line
            """, (book_id,))
            
            segments = cur.fetchall()
            
            for seg_id, start_line, end_line in segments:
                new_start = int((start_line - 1) * lines_per_section) + 1
                new_end = int(start_line * lines_per_section)
                
                if new_end > max_line:
                    new_end = max_line
                    
                cur.execute("""
                    UPDATE translation_segments 
                    SET start_line = ?, end_line = ?
                    WHERE id = ?
                """, (new_start, new_end, seg_id))
            
            fixed_count += 1
            print(f"  Fixed: {len(segments)} segments now cover lines 1-{max_line}")
    
    if fixed_count > 0:
        conn.commit()
        print(f"\nTotal books fixed: {fixed_count}")
    else:
        print("\nNo alignment issues found!")
    
    conn.close()

if __name__ == "__main__":
    fix_alignments()