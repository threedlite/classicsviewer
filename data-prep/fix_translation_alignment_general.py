#!/usr/bin/env python3
"""
General fix for translation alignment issues.
Handles multiple patterns of misalignment while preserving correctly aligned texts.
"""

import sqlite3
import xml.etree.ElementTree as ET
import os
import shutil
from datetime import datetime
from collections import defaultdict

def create_backup():
    """Create a backup of the database before making changes"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"output/perseus_texts_backup_{timestamp}.db"
    shutil.copy2("output/perseus_texts.db", backup_name)
    print(f"Created backup: {backup_name}")
    return backup_name

def analyze_book_alignment(cur, book_id):
    """Analyze a book to detect alignment issues"""
    
    # Get text line stats
    cur.execute("""
        SELECT 
            COUNT(*) as total_lines,
            MIN(CAST(line_number as INTEGER)) as min_line,
            MAX(CAST(line_number as INTEGER)) as max_line
        FROM text_lines 
        WHERE book_id = ?
    """, (book_id,))
    
    total_lines, min_line, max_line = cur.fetchone()
    
    # Get translation stats
    cur.execute("""
        SELECT 
            COUNT(*) as segment_count,
            MIN(start_line) as min_trans,
            MAX(end_line) as max_trans,
            COUNT(DISTINCT start_line) as unique_starts
        FROM translation_segments 
        WHERE book_id = ?
    """, (book_id,))
    
    segment_count, min_trans, max_trans, unique_starts = cur.fetchone()
    
    if not segment_count:
        return None
    
    # Calculate coverage
    coverage = (max_trans / max_line * 100) if max_line > 0 else 0
    
    # Detect patterns
    alignment_type = "unknown"
    
    # Pattern 1: Already correctly aligned (e.g., Homer)
    # Symptoms: coverage is high (>80%)
    if coverage > 80:
        alignment_type = "correct"
    
    # Pattern 2: Section numbers used as line numbers (e.g., Aeschines)
    # Symptoms: max_trans is much smaller than max_line, and max_trans == segment_count
    elif coverage < 50 and max_trans == segment_count and max_line > max_trans * 2:
        alignment_type = "section_as_line"
    
    # Pattern 3: Partial translations
    # Symptoms: Coverage between 50-80%, but translations are sequential
    elif 50 <= coverage <= 80:
        # Check if translations are mostly sequential
        cur.execute("""
            SELECT COUNT(*) 
            FROM translation_segments 
            WHERE book_id = ? AND end_line = start_line
        """, (book_id,))
        
        single_line_segments = cur.fetchone()[0]
        
        if single_line_segments > segment_count * 0.8:
            alignment_type = "partial_translation"
        else:
            alignment_type = "correct"  # Probably correct, just partial
    
    # Pattern 4: Bekker numbering or other reference systems (e.g., Aristotle)
    # Symptoms: start lines contain non-numeric patterns or very large numbers
    else:
        cur.execute("""
            SELECT start_line 
            FROM translation_segments 
            WHERE book_id = ? 
            LIMIT 5
        """, (book_id,))
        
        sample_starts = [row[0] for row in cur.fetchall()]
        
        # Check for Bekker-style numbering (e.g., "1218-1")
        bekker_pattern = any('-' in str(s) for s in sample_starts)
        
        # Check for very large line numbers that don't match actual line count
        huge_numbers = any(s > max_line * 10 for s in sample_starts if isinstance(s, int))
        
        if bekker_pattern or huge_numbers:
            alignment_type = "reference_system"
        elif coverage < 30:
            # Very low coverage, likely section-as-line but with fewer sections
            alignment_type = "section_as_line"
    
    return {
        'book_id': book_id,
        'total_lines': total_lines,
        'max_line': max_line,
        'segment_count': segment_count,
        'max_trans': max_trans,
        'coverage': coverage,
        'alignment_type': alignment_type
    }

def fix_section_as_line_alignment(cur, book_id, analysis):
    """Fix cases where section numbers were used as line numbers"""
    
    updates = []
    
    # Safety check: only fix if pattern is very clear
    if analysis['coverage'] > 50:
        # Coverage too high, might be correctly aligned
        return updates
    
    # Get all translation segments
    cur.execute("""
        SELECT id, start_line, end_line
        FROM translation_segments 
        WHERE book_id = ?
        ORDER BY start_line
    """, (book_id,))
    
    segments = cur.fetchall()
    
    # Calculate proportional mapping
    max_section = analysis['max_trans']
    max_line = analysis['max_line']
    
    # Another safety check
    if max_section == 0 or max_line == 0:
        return updates
        
    lines_per_section = max_line / max_section
    
    # Only proceed if the ratio makes sense (each section should map to at least 2 lines)
    if lines_per_section < 2:
        return updates
    
    for segment_id, start_line, end_line in segments:
        # Map section numbers to line ranges
        new_start = int((start_line - 1) * lines_per_section) + 1
        new_end = int(end_line * lines_per_section)
        
        # Ensure we don't exceed max lines
        if new_end > max_line:
            new_end = max_line
            
        updates.append((new_start, new_end, segment_id))
    
    return updates

def fix_reference_system_alignment(cur, book_id, analysis):
    """Fix cases with Bekker numbering or other reference systems"""
    
    updates = []
    
    # For these cases, we need to redistribute translations evenly across available lines
    # This is a fallback approach when we can't parse the reference system
    
    segment_count = analysis['segment_count']
    max_line = analysis['max_line']
    
    if segment_count == 0 or max_line == 0:
        return updates
    
    lines_per_segment = max_line / segment_count
    
    # Get all segments ordered by ID (maintaining original order)
    cur.execute("""
        SELECT id
        FROM translation_segments 
        WHERE book_id = ?
        ORDER BY id
    """, (book_id,))
    
    for i, (segment_id,) in enumerate(cur.fetchall()):
        new_start = int(i * lines_per_segment) + 1
        new_end = int((i + 1) * lines_per_segment)
        
        if new_end > max_line:
            new_end = max_line
            
        updates.append((new_start, new_end, segment_id))
    
    return updates

def apply_fixes(apply=False):
    """Main function to fix translation alignments"""
    
    conn = sqlite3.connect('output/perseus_texts.db')
    cur = conn.cursor()
    
    # Get all books with translations
    cur.execute("""
        SELECT DISTINCT b.id, w.title, a.name
        FROM books b
        JOIN works w ON b.work_id = w.id
        JOIN authors a ON w.author_id = a.id
        WHERE EXISTS (
            SELECT 1 FROM translation_segments ts 
            WHERE ts.book_id = b.id
        )
        ORDER BY a.name, w.title
    """)
    
    books = cur.fetchall()
    
    fixes_by_type = defaultdict(list)
    
    print("=== ANALYZING ALL BOOKS ===\n")
    
    for book_id, work_title, author_name in books:
        analysis = analyze_book_alignment(cur, book_id)
        
        if not analysis:
            continue
        
        if analysis['alignment_type'] != 'correct':
            fixes_by_type[analysis['alignment_type']].append({
                'book_id': book_id,
                'author': author_name,
                'work': work_title,
                'analysis': analysis
            })
    
    # Count correct alignments
    correct_count = len(books) - sum(len(b) for b in fixes_by_type.values())
    
    # Report findings
    print(f"Alignment analysis results:")
    print(f"  ✓ Correctly aligned: {correct_count}")
    print(f"  ✗ Section-as-line pattern: {len(fixes_by_type['section_as_line'])}")
    print(f"  ✗ Reference system pattern: {len(fixes_by_type['reference_system'])}")
    print(f"  ℹ Partial translations: {len(fixes_by_type['partial_translation'])}")
    print(f"  ? Unknown pattern: {len(fixes_by_type['unknown'])}")
    
    # Only fix section-as-line and reference_system patterns
    fixable_types = ['section_as_line', 'reference_system']
    total_fixes = sum(len(fixes_by_type[t]) for t in fixable_types)
    print(f"\nTotal books to fix: {total_fixes}")
    
    if total_fixes == 0:
        print("\nNo fixes needed!")
        return
    
    # Show examples
    print("\n=== SAMPLE FIXES ===")
    
    all_updates = []
    
    # Process section-as-line fixes
    if 'section_as_line' in fixes_by_type and fixes_by_type['section_as_line']:
        print("\nSection-as-line fixes (first 3):")
        for book_info in fixes_by_type['section_as_line'][:3]:
            print(f"\n{book_info['author']} - {book_info['work']}")
            print(f"  Current: translations up to line {book_info['analysis']['max_trans']}")
            print(f"  Total lines: {book_info['analysis']['max_line']}")
            print(f"  Fix: Redistribute {book_info['analysis']['segment_count']} sections across all lines")
            
            if apply:
                updates = fix_section_as_line_alignment(cur, book_info['book_id'], book_info['analysis'])
                all_updates.extend([(book_info['book_id'], u) for u in updates])
    
    # Process reference system fixes
    if 'reference_system' in fixes_by_type and fixes_by_type['reference_system']:
        print("\nReference system fixes (first 3):")
        for book_info in fixes_by_type['reference_system'][:3]:
            print(f"\n{book_info['author']} - {book_info['work']}")
            print(f"  Issue: Non-standard line numbering")
            print(f"  Fix: Redistribute {book_info['analysis']['segment_count']} segments evenly")
            
            if apply:
                updates = fix_reference_system_alignment(cur, book_info['book_id'], book_info['analysis'])
                all_updates.extend([(book_info['book_id'], u) for u in updates])
    
    if apply and all_updates:
        print(f"\n=== APPLYING {len(all_updates)} FIXES ===")
        
        # Create backup
        backup_path = create_backup()
        
        try:
            # Apply all updates
            for book_id, (new_start, new_end, segment_id) in all_updates:
                cur.execute("""
                    UPDATE translation_segments 
                    SET start_line = ?, end_line = ?
                    WHERE id = ?
                """, (new_start, new_end, segment_id))
            
            conn.commit()
            print(f"✓ Successfully applied {len(all_updates)} fixes")
            
            # Verify some fixes
            print("\nVerifying fixes...")
            for book_type, books in fixes_by_type.items():
                if books:
                    sample_book = books[0]
                    cur.execute("""
                        SELECT MAX(end_line) 
                        FROM translation_segments 
                        WHERE book_id = ?
                    """, (sample_book['book_id'],))
                    
                    new_max = cur.fetchone()[0]
                    old_max = sample_book['analysis']['max_trans']
                    print(f"{sample_book['author']} - {sample_book['work']}: {old_max} → {new_max}")
            
        except Exception as e:
            print(f"✗ Error applying fixes: {e}")
            print(f"Database backup available at: {backup_path}")
            conn.rollback()
    else:
        print("\n(Dry run - no changes made. Run with apply=True to apply fixes)")
    
    conn.close()

if __name__ == "__main__":
    import sys
    
    print("=== General Translation Alignment Fix ===\n")
    print("This will fix translation alignment issues across all texts")
    print("while preserving correctly aligned texts.\n")
    
    apply = "--apply" in sys.argv
    
    if apply:
        print("WARNING: This will modify the database!")
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
    
    apply_fixes(apply=apply)
    
    if not apply:
        print("\n" + "="*60)
        print("To apply the fixes, run:")
        print("python3 fix_translation_alignment_general.py --apply")