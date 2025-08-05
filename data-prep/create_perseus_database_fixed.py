#!/usr/bin/env python3
"""
Enhanced version of create_perseus_database.py with proper translation alignment.
This fixes the issue where section numbers are used as line numbers.
"""

import os
import sys

# First, let's create a mapping function that can be integrated
def create_section_to_line_mapping(cursor, book_id):
    """
    Create a mapping from section numbers to line ranges for proper translation alignment.
    Returns a dict mapping section numbers to (start_line, end_line) tuples.
    """
    
    # Get all lines for this book with their section info
    cursor.execute("""
        SELECT line_number, line_text 
        FROM text_lines 
        WHERE book_id = ?
        ORDER BY CAST(line_number as INTEGER)
    """, (book_id,))
    
    lines = cursor.fetchall()
    if not lines:
        return {}
    
    # Get the total number of lines
    total_lines = len(lines)
    
    # Check if we can find section markers in the text
    # This would require parsing the original XML to get section boundaries
    # For now, we'll use a proportional mapping approach
    
    # Get the expected number of sections from translations
    cursor.execute("""
        SELECT MAX(start_line) 
        FROM translation_segments 
        WHERE book_id = ? AND start_line = end_line
    """, (book_id,))
    
    max_section = cursor.fetchone()[0]
    if not max_section or max_section == 0:
        return {}
    
    # Create proportional mapping
    section_map = {}
    lines_per_section = total_lines / max_section
    
    for section_num in range(1, max_section + 1):
        start_line = int((section_num - 1) * lines_per_section) + 1
        end_line = int(section_num * lines_per_section)
        
        # Ensure we don't exceed total lines
        if end_line > total_lines:
            end_line = total_lines
            
        section_map[section_num] = (start_line, end_line)
    
    return section_map

def fix_translation_alignment(cursor, book_id):
    """
    Fix translation alignment for a specific book after initial import.
    This should be called after both text lines and translations are imported.
    """
    
    # Check if this book has the section-as-line problem
    cursor.execute("""
        SELECT 
            (SELECT MAX(CAST(line_number as INTEGER)) FROM text_lines WHERE book_id = ?) as max_line,
            (SELECT MAX(end_line) FROM translation_segments WHERE book_id = ?) as max_trans,
            (SELECT COUNT(*) FROM translation_segments WHERE book_id = ?) as trans_count
    """, (book_id, book_id, book_id))
    
    max_line, max_trans, trans_count = cursor.fetchone()
    
    if not max_line or not max_trans or not trans_count:
        return 0
    
    # Check if alignment is needed
    coverage = (max_trans / max_line * 100) if max_line > 0 else 0
    
    # Only fix if:
    # 1. Coverage is low (< 50%)
    # 2. Max translated line equals translation count (section numbers used as lines)
    # 3. We have significantly more lines than sections
    if coverage < 50 and max_trans == trans_count and max_line > max_trans * 2:
        print(f"          → Fixing alignment: {trans_count} sections across {max_line} lines")
        
        # Create section to line mapping
        section_map = create_section_to_line_mapping(cursor, book_id)
        
        if not section_map:
            return 0
        
        # Update translation segments with proper line ranges
        cursor.execute("""
            SELECT id, start_line, end_line
            FROM translation_segments 
            WHERE book_id = ? AND start_line = end_line
            ORDER BY start_line
        """, (book_id,))
        
        updates = []
        for seg_id, start_line, end_line in cursor.fetchall():
            if start_line in section_map:
                new_start, new_end = section_map[start_line]
                updates.append((new_start, new_end, seg_id))
        
        # Apply updates
        for new_start, new_end, seg_id in updates:
            cursor.execute("""
                UPDATE translation_segments 
                SET start_line = ?, end_line = ?
                WHERE id = ?
            """, (new_start, new_end, seg_id))
        
        return len(updates)
    
    return 0

# Now let's create a wrapper that imports the original script and adds our fixes
def main():
    # Import the original create_perseus_database module
    import importlib.util
    spec = importlib.util.spec_from_file_location("create_perseus_database", 
                                                  "create_perseus_database.py")
    original_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original_module)
    
    # Monkey-patch the process_translations function to add alignment fixes
    original_process_translations = original_module.process_translations
    
    def process_translations_with_fixes(cursor):
        """Enhanced version that fixes alignment after importing translations"""
        
        # First run the original translation import
        original_process_translations(cursor)
        
        # Now fix alignment issues
        print("\n=== FIXING TRANSLATION ALIGNMENTS ===")
        
        # Get all books with translations
        cursor.execute("""
            SELECT DISTINCT book_id 
            FROM translation_segments
        """)
        
        books = cursor.fetchall()
        total_fixed = 0
        
        for (book_id,) in books:
            fixed = fix_translation_alignment(cursor, book_id)
            if fixed > 0:
                total_fixed += fixed
                print(f"    Fixed {book_id}: {fixed} segments realigned")
        
        if total_fixed > 0:
            print(f"\nTotal segments realigned: {total_fixed}")
        else:
            print("\nNo alignment issues found!")
    
    # Replace the function
    original_module.process_translations = process_translations_with_fixes
    
    # Run the main function
    original_module.main()

if __name__ == "__main__":
    main()