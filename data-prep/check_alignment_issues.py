#!/usr/bin/env python3
"""
Check for translation alignment issues across all texts
"""

import sqlite3

def check_alignment_issues():
    conn = sqlite3.connect('output/perseus_texts.db')
    cur = conn.cursor()
    
    print("=== CHECKING FOR ALIGNMENT ISSUES ===\n")
    
    # Get all books with translations
    cur.execute("""
        SELECT DISTINCT 
            b.id,
            b.label,
            w.title,
            a.name
        FROM books b
        JOIN works w ON b.work_id = w.id
        JOIN authors a ON w.author_id = a.id
        WHERE EXISTS (
            SELECT 1 FROM translation_segments ts 
            WHERE ts.book_id = b.id
        )
        ORDER BY a.name, w.title
    """)
    
    books_with_issues = []
    books_ok = []
    
    for book_id, book_label, work_title, author_name in cur.fetchall():
        # Get max line number in text
        cur.execute("""
            SELECT MAX(CAST(line_number as INTEGER)) 
            FROM text_lines 
            WHERE book_id = ?
        """, (book_id,))
        max_line = cur.fetchone()[0] or 0
        
        # Get max translated line
        cur.execute("""
            SELECT MAX(end_line) 
            FROM translation_segments 
            WHERE book_id = ?
        """, (book_id,))
        max_translated = cur.fetchone()[0] or 0
        
        # Check if there's a significant gap
        if max_line > 0 and max_translated > 0:
            coverage = (max_translated / max_line) * 100
            
            if coverage < 50:  # Less than 50% coverage suggests alignment issue
                books_with_issues.append({
                    'book_id': book_id,
                    'author': author_name,
                    'work': work_title,
                    'book_label': book_label,
                    'max_line': max_line,
                    'max_translated': max_translated,
                    'coverage': coverage
                })
            else:
                books_ok.append({
                    'book_id': book_id,
                    'author': author_name,
                    'work': work_title,
                    'coverage': coverage
                })
    
    # Report findings
    print(f"Books with potential alignment issues ({len(books_with_issues)}):")
    print("-" * 80)
    for book in books_with_issues:
        print(f"{book['author']} - {book['work']} ({book['book_label']})")
        print(f"  Book ID: {book['book_id']}")
        print(f"  Total lines: {book['max_line']}, Translated up to: {book['max_translated']}")
        print(f"  Coverage: {book['coverage']:.1f}%")
        print()
    
    print(f"\nBooks that appear OK ({len(books_ok)}):")
    print("-" * 80)
    sample_ok = books_ok[:5]  # Show first 5 as examples
    for book in sample_ok:
        print(f"{book['author']} - {book['work']} (Coverage: {book['coverage']:.1f}%)")
    if len(books_ok) > 5:
        print(f"... and {len(books_ok) - 5} more")
    
    # Check specific pattern: section-based numbering
    print("\n=== CHECKING FOR SECTION-BASED NUMBERING PATTERN ===")
    print("(Where max translated line is suspiciously round like 100, 200, etc)")
    print("-" * 80)
    
    for book in books_with_issues:
        if book['max_translated'] % 10 == 0 or book['max_translated'] in [196, 296, 396]:
            print(f"{book['author']} - {book['work']}: max translated = {book['max_translated']}")
    
    conn.close()
    
    return books_with_issues

if __name__ == "__main__":
    issues = check_alignment_issues()