#!/usr/bin/env python3
"""
Create SQLite database from Perseus Digital Library texts.
This version includes ALL Greek authors dynamically discovered from the canonical-greekLit directory.
"""

import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
import re
import json
from datetime import datetime
import unicodedata
from typing import Dict, List, Tuple, Optional, Set
import subprocess
import sys
import time

# Phase configuration - set to limit number of authors for testing
PHASE = "full"  # Options: "test" (30), "medium" (60), "full" (all)
PHASE_LIMITS = {
    "test": 30,
    "medium": 60, 
    "full": None
}

def normalize_greek(text):
    """Normalize Greek text by removing diacritics, punctuation, and converting to lowercase"""
    # First normalize to NFD (decomposed form)
    text = unicodedata.normalize('NFD', text)
    
    # Remove diacritical marks
    text = ''.join(c for c in text if not unicodedata.combining(c))
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace final sigma
    text = text.replace('ς', 'σ')
    
    # Remove punctuation (including Greek punctuation)
    # Keep only Greek letters
    text = ''.join(c for c in text if c.isalpha() and ('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff'))
    
    return text

def discover_greek_authors(greek_dir: Path) -> Dict[str, str]:
    """Dynamically discover all Greek authors from the canonical-greekLit directory"""
    authors = {}
    failed_authors = []
    
    print("Discovering Greek authors...")
    
    for author_dir in sorted(greek_dir.iterdir()):
        if author_dir.is_dir() and author_dir.name.startswith("tlg"):
            cts_file = author_dir / "__cts__.xml"
            if cts_file.exists():
                try:
                    tree = ET.parse(cts_file)
                    root = tree.getroot()
                    
                    # Find groupname element
                    ns = {'ti': 'http://chs.harvard.edu/xmlns/cts'}
                    groupname_elem = root.find('.//ti:groupname', ns)
                    
                    if groupname_elem is not None and groupname_elem.text:
                        authors[author_dir.name] = groupname_elem.text.strip()
                    else:
                        # Try to get work title as fallback
                        authors[author_dir.name] = f"Author {author_dir.name}"
                        failed_authors.append(author_dir.name)
                except Exception as e:
                    print(f"  Warning: Failed to parse {cts_file}: {e}")
                    authors[author_dir.name] = f"Author {author_dir.name}"
                    failed_authors.append(author_dir.name)
    
    # Apply phase limit if configured
    phase_limit = PHASE_LIMITS.get(PHASE)
    if phase_limit:
        # Get a diverse mix of authors for testing
        # Prioritize well-known authors first
        priority_authors = ["tlg0012", "tlg0085", "tlg0011", "tlg0006", "tlg0019", 
                           "tlg0007", "tlg0016", "tlg0003", "tlg0032", "tlg0059", 
                           "tlg0086", "tlg0020", "tlg0033", "tlg0026"]
        
        selected_authors = {}
        # Add priority authors first
        for auth_id in priority_authors:
            if auth_id in authors and len(selected_authors) < phase_limit:
                selected_authors[auth_id] = authors[auth_id]
        
        # Fill remaining slots with other authors
        for auth_id, name in sorted(authors.items()):
            if auth_id not in selected_authors and len(selected_authors) < phase_limit:
                selected_authors[auth_id] = name
        
        authors = selected_authors
        print(f"\nPhase '{PHASE}': Limited to {len(authors)} authors")
    
    print(f"\nDiscovered {len(authors)} Greek authors")
    if failed_authors:
        print(f"  Warning: {len(failed_authors)} authors without proper names")
    
    return authors

# Import all the parsing functions from original script
from create_perseus_database import (
    LSJParser, GreekLemmatizer, get_text_content,
    extract_translation_segments, process_prose_with_books,
    process_prose_text, process_text_file,
    process_perseus_author, create_lemma_mappings,
    extract_wiktionary_mappings, load_wiktionary_mappings,
    generate_comprehensive_lemmatization, optimize_lemma_map,
    generate_manifest, generate_quality_report
)

def create_database():
    """Create database from Perseus data with ALL Greek authors"""
    start_time = time.time()
    
    # Paths
    script_dir = Path(__file__).parent
    db_suffix = "" if PHASE == "full" else f"_{PHASE}"
    db_path = script_dir / f"perseus_texts{db_suffix}.db"
    data_sources = script_dir.parent / "data-sources"
    
    # Check paths
    print("Checking data sources...")
    greek_dir = data_sources / "canonical-greekLit" / "data"
    latin_dir = data_sources / "canonical-latinLit" / "data"
    
    if not greek_dir.exists():
        print(f"Error: Greek texts directory not found at {greek_dir}")
        return
    
    # Create/open database
    print(f"\nCreating database at {db_path}")
    print(f"Build phase: {PHASE}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables (same as original)
    print("Creating database schema...")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS authors (
            id TEXT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL,
            name_alt TEXT,
            language TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS works (
            id TEXT PRIMARY KEY NOT NULL,
            author_id TEXT NOT NULL,
            title TEXT,
            title_english TEXT,
            work_type TEXT,
            FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_works_author 
        ON works(author_id)
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY NOT NULL,
            work_id TEXT NOT NULL,
            book_number INTEGER,
            label TEXT,
            start_line INTEGER,
            end_line INTEGER,
            line_count INTEGER,
            FOREIGN KEY (work_id) REFERENCES works(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_books_work 
        ON books(work_id)
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS text_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            line_text TEXT NOT NULL,
            line_xml TEXT,
            speaker TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS translation_segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            book_id TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER,
            translation_text TEXT NOT NULL,
            translator TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_text_lines_book 
        ON text_lines(book_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_translation_segments_book 
        ON translation_segments(book_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_translation_segments_lines 
        ON translation_segments(book_id, start_line)
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS word_forms (
            word TEXT NOT NULL,
            word_normalized TEXT NOT NULL,
            book_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            word_position INTEGER NOT NULL,
            char_start INTEGER NOT NULL,
            char_end INTEGER NOT NULL,
            PRIMARY KEY (book_id, line_number, word_position),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_word_forms_book_line 
        ON word_forms(book_id, line_number)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_word_forms_normalized 
        ON word_forms(word_normalized)
    """)
    
    # Enable WAL mode for better concurrent performance
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=10000")  # 10MB cache
    cursor.execute("PRAGMA temp_store=MEMORY")
    
    # Process Greek authors - DYNAMIC DISCOVERY
    print("\n=== PROCESSING GREEK AUTHORS ===")
    
    # Discover all Greek authors
    greek_authors = discover_greek_authors(greek_dir)
    
    # Track progress
    total_authors = len(greek_authors)
    processed_authors = 0
    failed_authors = []
    
    # Process each Greek author with progress tracking
    for author_id, author_name in sorted(greek_authors.items()):
        processed_authors += 1
        author_path = greek_dir / author_id
        
        if author_path.exists():
            print(f"\n[{processed_authors}/{total_authors}] Processing {author_name} ({author_id})")
            
            try:
                # Add progress tracking within author processing
                process_perseus_author(author_path, "greek", cursor)
                
                # Commit after each author to avoid losing progress
                if processed_authors % 5 == 0:
                    conn.commit()
                    print(f"  Progress saved ({processed_authors}/{total_authors} authors)")
                    
            except Exception as e:
                print(f"  ERROR processing {author_name}: {e}")
                failed_authors.append((author_id, author_name, str(e)))
                # Continue with next author
                continue
        else:
            print(f"\n[{processed_authors}/{total_authors}] Warning: {author_name} ({author_id}) directory not found")
    
    # Report any failures
    if failed_authors:
        print(f"\n=== FAILED AUTHORS ({len(failed_authors)}) ===")
        for auth_id, name, error in failed_authors:
            print(f"  {name} ({auth_id}): {error}")
    
    # Process Latin authors (keeping original selection for now)
    print("\n=== PROCESSING LATIN AUTHORS ===")
    
    latin_authors = {
        "phi0959": "Ovid",
        "phi0690": "Virgil",
        "phi0893": "Horace"
    }
    
    for author_id, author_name in latin_authors.items():
        author_path = latin_dir / author_id
        if author_path.exists():
            print(f"\nProcessing {author_name} ({author_id})")
            process_perseus_author(author_path, "latin", cursor)
        else:
            print(f"\nWarning: {author_name} ({author_id}) not found")
    
    # Import LSJ dictionary (same as original)
    print("\n=== PROCESSING LSJ DICTIONARY ===")
    lsj_path = data_sources / "canonical-pdlrefwk" / "data" / "viaf66541464" / "001" / "viaf66541464.001.perseus-eng1.xml"
    
    if lsj_path.exists():
        # Create dictionary tables
        print("Creating dictionary tables...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dictionary_entries (
                id INTEGER PRIMARY KEY NOT NULL,
                headword TEXT NOT NULL,
                headword_normalized TEXT NOT NULL,
                language TEXT NOT NULL,
                entry_xml TEXT,
                entry_html TEXT,
                entry_plain TEXT,
                source TEXT,
                CHECK (language IN ('greek', 'latin'))
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_dictionary_headword_normalized 
            ON dictionary_entries(headword_normalized, language)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lemma_map (
                word_form TEXT NOT NULL,
                word_normalized TEXT NOT NULL,
                lemma TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                source TEXT,
                morph_info TEXT,
                PRIMARY KEY (word_form, lemma)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lemma_map_normalized 
            ON lemma_map(word_normalized)
        """)
        
        # Parse and import LSJ
        parser = LSJParser()
        lsj_entries = parser.parse_lsj_xml(str(lsj_path))
        
        if lsj_entries:
            print(f"Importing {len(lsj_entries)} LSJ entries...")
            
            # Batch insert for better performance
            dictionary_data = []
            for entry in lsj_entries:
                dictionary_data.append((
                    entry['headword'],
                    entry['headword_normalized'], 
                    entry['language'],
                    entry['entry_xml'],
                    entry['entry_html'],
                    entry['entry_plain'],
                    entry['source']
                ))
            
            cursor.executemany("""
                INSERT INTO dictionary_entries 
                (headword, headword_normalized, language, entry_xml, entry_html, entry_plain, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, dictionary_data)
            
            print("✓ LSJ dictionary entries imported successfully")
            
            # Generate and import lemma mappings
            print("Generating lemma mappings...")
            lemma_mappings = create_lemma_mappings(lsj_entries)
            
            if lemma_mappings:
                print(f"Importing {len(lemma_mappings)} lemma mappings...")
                
                # Batch insert
                lemma_data = []
                for mapping in lemma_mappings:
                    lemma_data.append((
                        mapping['word_form'],
                        mapping['word_normalized'],
                        mapping['lemma'],
                        mapping['confidence'],
                        mapping['source']
                    ))
                
                cursor.executemany("""
                    INSERT OR IGNORE INTO lemma_map
                    (word_form, word_normalized, lemma, confidence, source)
                    VALUES (?, ?, ?, ?, ?)
                """, lemma_data)
                
                print("✓ Lemma mappings imported successfully")
            else:
                print("Warning: No lemma mappings generated")
        else:
            print("Warning: No LSJ entries found")
    else:
        print(f"Warning: LSJ file not found at {lsj_path}")
    
    # Extract Wiktionary mappings if needed
    extract_wiktionary_mappings()
    
    # Load Wiktionary morphological mappings
    load_wiktionary_mappings(cursor)
    
    # Generate comprehensive mappings for all words in texts
    print("\n=== GENERATING COMPREHENSIVE LEMMATIZATION ===")
    print("Note: This may take longer with expanded vocabulary...")
    generate_comprehensive_lemmatization(cursor)
    
    # Optimize lemma map to only include words in texts
    optimize_lemma_map(cursor)
    
    # Commit
    conn.commit()
    
    # Show statistics
    print("\n=== DATABASE STATISTICS ===")
    
    cursor.execute("SELECT COUNT(*) FROM authors")
    print(f"Authors: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM works")
    print(f"Works: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM books")
    print(f"Books: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM text_lines")
    print(f"Text lines: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM word_forms")
    print(f"Word forms: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(DISTINCT word_normalized) FROM word_forms")
    print(f"Unique words: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM translation_segments")
    print(f"Translation segments: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM dictionary_entries")
    dict_count = cursor.fetchone()[0]
    if dict_count > 0:
        print(f"Dictionary entries: {dict_count}")
    
    cursor.execute("SELECT COUNT(*) FROM lemma_map")  
    lemma_count = cursor.fetchone()[0]
    if lemma_count > 0:
        print(f"Lemma mappings: {lemma_count}")
    
    # Show author summary with line counts
    print("\n=== AUTHOR SUMMARY ===")
    cursor.execute("""
        SELECT a.name, 
               COUNT(DISTINCT w.id) as work_count,
               COUNT(DISTINCT b.id) as book_count,
               SUM(b.line_count) as total_lines
        FROM authors a
        LEFT JOIN works w ON a.id = w.author_id
        LEFT JOIN books b ON w.id = b.work_id
        GROUP BY a.id
        ORDER BY total_lines DESC
        LIMIT 20
    """)
    
    print(f"{'Author':<25} {'Works':>8} {'Books':>8} {'Lines':>10}")
    print("-" * 55)
    for row in cursor.fetchall():
        print(f"{row[0]:<25} {row[1]:>8} {row[2]:>8} {row[3] or 0:>10,}")
    
    # Show largest works
    print("\n=== LARGEST WORKS ===")
    cursor.execute("""
        SELECT a.name, w.title_english, 
               COUNT(b.id) as book_count,
               SUM(b.line_count) as total_lines
        FROM authors a
        JOIN works w ON a.id = w.author_id
        JOIN books b ON w.id = b.work_id
        GROUP BY w.id
        ORDER BY total_lines DESC
        LIMIT 15
    """)
    
    print(f"{'Author':<25} {'Work':<35} {'Books':>8} {'Lines':>10}")
    print("-" * 80)
    for row in cursor.fetchall():
        work_title = row[1][:33] + '..' if len(row[1]) > 35 else row[1]
        print(f"{row[0]:<25} {work_title:<35} {row[2]:>8} {row[3]:>10,}")
    
    # Generate manifest file
    generate_manifest(cursor)
    
    # Generate quality report
    generate_quality_report(cursor)
    
    # Print translation coverage
    cursor.execute("""
        SELECT COUNT(DISTINCT w.id) as total_works,
               COUNT(DISTINCT CASE WHEN ts.id IS NOT NULL THEN w.id END) as works_with_trans
        FROM works w
        LEFT JOIN books b ON w.id = b.work_id
        LEFT JOIN translation_segments ts ON b.id = ts.book_id
    """)
    total_works, works_with_trans = cursor.fetchone()
    coverage = (works_with_trans / total_works * 100) if total_works > 0 else 0
    print(f"\n=== TRANSLATION COVERAGE ===")
    print(f"Works with translations: {works_with_trans}/{total_works} ({coverage:.1f}%)")
    
    conn.close()
    
    # Calculate build time
    build_time = time.time() - start_time
    print(f"\n✓ Database created successfully in {build_time/60:.1f} minutes!")
    
    # Copy and compress database to asset pack location for Play Asset Delivery
    import shutil
    import os
    import zipfile
    asset_pack_dir = "../perseus_database/src/main/assets"
    os.makedirs(asset_pack_dir, exist_ok=True)
    if os.path.exists(db_path):
        # Create compressed version
        zip_path = os.path.join(asset_pack_dir, f"perseus_texts{db_suffix}.db.zip")
        print(f"\nCompressing database to {zip_path}...")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            zf.write(db_path, f"perseus_texts{db_suffix}.db")
        
        # Get file sizes
        original_size = os.path.getsize(db_path) / (1024 * 1024)
        compressed_size = os.path.getsize(zip_path) / (1024 * 1024)
        
        print(f"Original size: {original_size:.1f}MB")
        print(f"Compressed size: {compressed_size:.1f}MB ({compressed_size/original_size*100:.1f}%)")
        
        # For testing phases, also create debug asset
        if PHASE != "full":
            debug_asset_dir = "../app/src/debug/assets"
            os.makedirs(debug_asset_dir, exist_ok=True)
            shutil.copy(zip_path, debug_asset_dir)
            print(f"Also copied to debug assets: {debug_asset_dir}")
    else:
        print(f"Error: Database file not created at {db_path}")

if __name__ == "__main__":
    # Allow phase override from command line
    if len(sys.argv) > 1:
        if sys.argv[1] in PHASE_LIMITS:
            PHASE = sys.argv[1]
        else:
            print(f"Invalid phase: {sys.argv[1]}")
            print(f"Valid phases: {', '.join(PHASE_LIMITS.keys())}")
            sys.exit(1)
    
    create_database()