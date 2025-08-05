#!/usr/bin/env python3
"""
Patch for create_perseus_database.py to fix translation alignment during import.
This modifies the translation insertion logic to properly map sections to line ranges.
"""

import re

def get_section_line_mapping(cursor, book_id):
    """
    Analyze the text lines to create a mapping from sections to line ranges.
    This is used during translation import to properly align translations with lines.
    """
    
    # Get line count for this book
    cursor.execute("""
        SELECT COUNT(*), MAX(CAST(line_number as INTEGER))
        FROM text_lines 
        WHERE book_id = ?
    """, (book_id,))
    
    line_count, max_line = cursor.fetchone()
    
    if not line_count or line_count == 0:
        return None, None
    
    return line_count, max_line

def insert_translation_segment_with_alignment(cursor, book_id, section_num, text, translator, 
                                            line_count=None, max_line=None):
    """
    Insert a translation segment with proper line alignment.
    
    If line_count and max_line are provided, and section_num appears to be 
    a section number rather than a line number, we'll map it to the appropriate
    line range.
    """
    
    start_line = section_num
    end_line = section_num
    
    # Check if we need to do section-to-line mapping
    if line_count and max_line and isinstance(section_num, int):
        # Heuristic: if section_num is much smaller than max_line, 
        # it's probably a section number, not a line number
        if section_num < max_line / 2:
            # We likely have section numbers that need to be mapped to line ranges
            # First, we need to estimate how many sections there are
            # This is tricky without parsing the full structure, so we'll check
            # if the current section number suggests a reasonable section count
            
            # Estimate total sections (assume sections are sequential)
            # We'll refine this as we see more sections
            estimated_sections = section_num * 1.5  # Add buffer for sections we haven't seen yet
            
            if estimated_sections < max_line / 2:
                # This looks like section numbering
                # Map section to line range proportionally
                lines_per_section = max_line / estimated_sections
                
                start_line = int((section_num - 1) * lines_per_section) + 1
                end_line = int(section_num * lines_per_section)
                
                # Ensure we don't exceed max lines
                if end_line > max_line:
                    end_line = max_line
    
    # Insert the segment
    cursor.execute("""
        INSERT OR IGNORE INTO translation_segments
        (book_id, start_line, end_line, translation_text, translator)
        VALUES (?, ?, ?, ?, ?)
    """, (book_id, start_line, end_line, text, translator))
    
    return cursor.rowcount > 0

def create_enhanced_extract_translation_segments(original_function):
    """
    Create an enhanced version of extract_translation_segments that includes alignment logic.
    """
    
    def enhanced_extract_translation_segments(book_elem, book_id, cursor, translator):
        # First, get line count information for this book
        line_count, max_line = get_section_line_mapping(cursor, book_id)
        
        # Store original insert logic
        original_execute = cursor.execute
        segments_info = {'count': 0, 'max_section': 0}
        
        # Create a wrapper for cursor.execute to intercept translation insertions
        def execute_wrapper(query, params=None):
            if "INSERT OR IGNORE INTO translation_segments" in query and params:
                # Extract the parameters
                book_id_param, start_line, end_line, text, translator_param = params
                
                # Track max section number
                if isinstance(start_line, int) and start_line > segments_info['max_section']:
                    segments_info['max_section'] = start_line
                
                # Use our enhanced insertion
                if line_count and max_line:
                    # Check if this looks like section-based numbering
                    if start_line == end_line and start_line < max_line / 3:
                        # Likely section number, not line number
                        # We'll do a second pass to fix these
                        segments_info['count'] += 1
                
                # Call original for now
                return original_execute(query, params)
            else:
                return original_execute(query, params)
        
        # Temporarily replace execute
        cursor.execute = execute_wrapper
        
        # Call the original function
        result = original_function(book_elem, book_id, cursor, translator)
        
        # Restore original execute
        cursor.execute = original_execute
        
        # If we detected section-based numbering, fix it
        if (segments_info['count'] > 0 and segments_info['max_section'] > 0 and 
            line_count and max_line and segments_info['max_section'] < max_line / 3):
            
            print(f"          → Detected section-based numbering: {segments_info['max_section']} sections for {max_line} lines")
            
            # Update the segments we just inserted
            cursor.execute("""
                SELECT id, start_line, end_line
                FROM translation_segments 
                WHERE book_id = ? AND start_line = end_line
                ORDER BY start_line DESC
                LIMIT ?
            """, (book_id, segments_info['count']))
            
            recent_segments = cursor.fetchall()
            
            # Calculate proper line ranges
            lines_per_section = max_line / segments_info['max_section']
            
            for seg_id, start_line, end_line in recent_segments:
                if start_line <= segments_info['max_section']:
                    new_start = int((start_line - 1) * lines_per_section) + 1
                    new_end = int(start_line * lines_per_section)
                    
                    if new_end > max_line:
                        new_end = max_line
                    
                    cursor.execute("""
                        UPDATE translation_segments 
                        SET start_line = ?, end_line = ?
                        WHERE id = ?
                    """, (new_start, new_end, seg_id))
            
            print(f"          → Realigned {len(recent_segments)} segments")
        
        return result
    
    return enhanced_extract_translation_segments

# Patch function to be called from create_perseus_database.py
def apply_alignment_patch():
    """
    This function should be called from create_perseus_database.py to apply the alignment fixes.
    Add this near the top of create_perseus_database.py:
    
    # Import and apply translation alignment patch
    import translation_alignment_patch
    translation_alignment_patch.apply_alignment_patch()
    """
    
    import sys
    import inspect
    
    # Get the calling module (should be create_perseus_database)
    frame = inspect.currentframe()
    calling_module = inspect.getmodule(frame.f_back)
    
    if calling_module and hasattr(calling_module, 'extract_translation_segments'):
        # Replace the function with our enhanced version
        original_func = calling_module.extract_translation_segments
        calling_module.extract_translation_segments = create_enhanced_extract_translation_segments(original_func)
        print("Translation alignment patch applied successfully!")
        return True
    else:
        print("Warning: Could not apply translation alignment patch - extract_translation_segments not found")
        return False