#!/usr/bin/env python3
"""
Simple, safe fix for Aeschines translation alignment.
Only fixes the specific case where translations are mapped to section numbers (1-196)
instead of line numbers (1-866).
"""

import sqlite3
import shutil
from datetime import datetime

def create_backup():
    """Create a backup of the database before making changes"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"output/perseus_texts_backup_{timestamp}.db"
    shutil.copy2("output/perseus_texts.db", backup_name)
    print(f"Created backup: {backup_name}")
    return backup_name

def fix_aeschines_simple(apply_fix=False):
    """
    Fix only Aeschines texts where we have clear evidence of section-to-line mismapping.
    
    The issue: Translations are mapped to section numbers (1-196) but should be
    distributed across all lines (1-866).
    
    The fix: Create a proportional mapping from sections to lines.
    """
    
    conn = sqlite3.connect('output/perseus_texts.db')
    cur = conn.cursor()
    
    # Only fix Aeschines Against Timarchus for now (we can extend later)
    book_id = 'tlg0026.tlg001.001'
    
    print(f"Analyzing {book_id} (Aeschines - Against Timarchus)...")
    
    # Get total lines
    cur.execute("""
        SELECT COUNT(*), MAX(CAST(line_number as INTEGER))
        FROM text_lines 
        WHERE book_id = ?
    """, (book_id,))
    
    total_lines, max_line = cur.fetchone()
    print(f"Total lines in Greek text: {total_lines} (max: {max_line})")
    
    # Get translation info
    cur.execute("""
        SELECT COUNT(*), MAX(end_line)
        FROM translation_segments 
        WHERE book_id = ?
    """, (book_id,))
    
    total_segments, max_translated = cur.fetchone()
    print(f"Translation segments: {total_segments} (max line: {max_translated})")
    
    # Check if this matches the problematic pattern
    if max_translated == 196 and max_line == 866:
        print("\n✓ Confirmed: This text has the section-to-line mapping issue")
        
        # Calculate proportional mapping
        # We'll distribute the 196 sections across 866 lines proportionally
        lines_per_section = max_line / max_translated
        print(f"Average lines per section: {lines_per_section:.2f}")
        
        # Get all translation segments
        cur.execute("""
            SELECT id, start_line, end_line, SUBSTR(translation_text, 1, 50)
            FROM translation_segments 
            WHERE book_id = ?
            ORDER BY start_line
        """, (book_id,))
        
        segments = cur.fetchall()
        
        # Calculate new line ranges
        updates = []
        for segment_id, start_line, end_line, text_preview in segments:
            # For single-line segments (most common case)
            if start_line == end_line:
                # Map section number to line range
                new_start = int((start_line - 1) * lines_per_section) + 1
                new_end = int(start_line * lines_per_section)
                
                # Ensure we don't exceed max lines
                if new_end > max_line:
                    new_end = max_line
                    
                updates.append({
                    'id': segment_id,
                    'old_start': start_line,
                    'old_end': end_line,
                    'new_start': new_start,
                    'new_end': new_end,
                    'text': text_preview
                })
        
        # Show proposed changes
        print(f"\nProposed fixes: {len(updates)} segments")
        print("\nSample fixes (first 5 and last 5):")
        
        samples = updates[:5] + updates[-5:]
        for update in samples:
            print(f"\nSegment {update['id']}: '{update['text']}...'")
            print(f"  Current: line {update['old_start']}")
            print(f"  Fixed:   lines {update['new_start']}-{update['new_end']}")
        
        if apply_fix:
            print("\n=== APPLYING FIX ===")
            
            # Create backup first
            backup_path = create_backup()
            
            try:
                # Apply updates
                for update in updates:
                    cur.execute("""
                        UPDATE translation_segments 
                        SET start_line = ?, end_line = ?
                        WHERE id = ?
                    """, (update['new_start'], update['new_end'], update['id']))
                
                conn.commit()
                print(f"✓ Successfully updated {len(updates)} segments")
                
                # Verify the fix
                cur.execute("""
                    SELECT MAX(end_line) 
                    FROM translation_segments 
                    WHERE book_id = ?
                """, (book_id,))
                
                new_max = cur.fetchone()[0]
                print(f"✓ Translations now cover up to line {new_max} (was {max_translated})")
                
            except Exception as e:
                print(f"✗ Error applying fix: {e}")
                print(f"Database backup available at: {backup_path}")
                conn.rollback()
        else:
            print("\n(Dry run - no changes made. Run with apply_fix=True to apply)")
    else:
        print("\n✗ This text doesn't match the expected pattern. Not fixing.")
    
    conn.close()

if __name__ == "__main__":
    print("=== Aeschines Translation Alignment Fix ===\n")
    print("This will fix the translation alignment for Aeschines' Against Timarchus")
    print("where translations are incorrectly mapped to section numbers instead of lines.\n")
    
    # First do a dry run
    fix_aeschines_simple(apply_fix=False)
    
    print("\n" + "="*60)
    print("To apply the fix, run:")
    print("python3 fix_aeschines_simple.py --apply")