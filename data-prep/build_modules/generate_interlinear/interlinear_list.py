#!/usr/bin/env python3
"""
Parallel Interlinear Generator from Author/Work CSV
====================================================

Generates interlinear translation XML files for works listed in a CSV file,
using multi-threading to process works in parallel.

⚠️  IMPORTANT: Process Management
---------------------------------
This script uses multiprocessing with 'spawn' method, creating multiple worker processes.

**BEFORE RESTARTING OR MODIFYING CODE:**
1. Kill ALL related Python processes (not just the main script!)
2. Clear Python bytecode cache (__pycache__, *.pyc files)
3. Verify no workers are still running

Commands to ensure clean restart:
    # Kill all Python processes
    pkill -9 python

    # Or kill specific interlinear processes
    pkill -9 -f interlinear_list.py

    # Clear Python cache
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} +

    # Verify no processes remain
    ps aux | grep python

⚠️  If you don't kill worker processes, they will continue running with OLD CODE
    even after you modify and restart the main script! This causes corrupted output.

Usage:
    python3 interlinear_list.py <input_csv> <database_path> [options]

Options:
    --workers N     Number of parallel workers (default: 4)
    --output DIR    Output directory for XML files (default: ./build_modules/generate_interlinear)

Input CSV format (Author,Work pairs like SAMPLE_AUTHORS_GREEK_ONLY.csv):
    Author,Work
    Homer,Iliad
    Homer,Odyssey
    Sophocles,Ajax

Outputs:
    <output_dir>/<work_id>.perseus-eng99.xml for each work

Examples:
    # Generate interlinear for works in SAMPLE_AUTHORS_GREEK_ONLY.csv with 4 workers
    python3 interlinear_list.py ../cltk_poc/SAMPLE_AUTHORS_GREEK_ONLY.csv perseus_texts.db

    # Use 8 workers for faster processing
    python3 interlinear_list.py works.csv perseus_texts.db --workers 8

    # Specify custom output directory
    python3 interlinear_list.py works.csv perseus_texts.db --output /tmp/interlinear
"""

import csv
import sys
import time
import sqlite3
import multiprocessing as mp
import logging
from pathlib import Path
from typing import List, Tuple, Optional

# Set up minimal logging
logging.basicConfig(level=logging.WARNING)

def lookup_work_id(db_path: str, author: str, work_title: str) -> Optional[str]:
    """
    Look up work_id from database given author and work title.

    Returns:
        work_id (e.g., 'tlg0012.tlg001') or None if not found
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Try exact match on title first (trim whitespace in comparison)
    cursor.execute("""
        SELECT w.id
        FROM works w
        JOIN authors a ON w.author_id = a.id
        WHERE trim(a.name) = ? AND trim(w.title) = ?
        LIMIT 1
    """, (author, work_title))

    result = cursor.fetchone()
    if result:
        conn.close()
        return result[0]

    # Try exact match on title_english (trim whitespace in comparison)
    cursor.execute("""
        SELECT w.id
        FROM works w
        JOIN authors a ON w.author_id = a.id
        WHERE trim(a.name) = ? AND trim(w.title_english) = ?
        LIMIT 1
    """, (author, work_title))

    result = cursor.fetchone()
    if result:
        conn.close()
        return result[0]

    conn.close()
    return None


def load_works_from_csv(csv_path: Path, db_path: str) -> List[Tuple[str, str, str]]:
    """
    Load works from CSV file and resolve to work_ids.

    Returns:
        List of (author, work_title, work_id) tuples
    """
    works = []
    not_found = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            author = row.get('Author', '').strip()
            work_title = row.get('Work', '').strip()

            if not author or not work_title:
                continue

            # Look up work_id in database
            work_id = lookup_work_id(db_path, author, work_title)

            if work_id:
                works.append((author, work_title, work_id))
            else:
                not_found.append((author, work_title))

    if not_found:
        print(f"\n⚠ Warning: {len(not_found)} works not found in database:")
        for author, work_title in not_found[:10]:  # Show first 10
            print(f"  - {author}, {work_title}")
        if len(not_found) > 10:
            print(f"  ... and {len(not_found) - 10} more")

    return works


def process_work_worker(args: Tuple[int, str, str, str, str, Path]) -> Tuple[int, str, str, bool, str]:
    """
    Worker function that generates interlinear XML for ONE work.

    Args:
        args: (work_index, author, work_title, work_id, db_path, output_dir)

    Returns:
        (work_index, author, work_title, success, error_message)
    """
    work_index, author, work_title, work_id, db_path, output_dir = args

    try:
        # Import the generate_interlinear module
        import sys
        from pathlib import Path

        # Get the directory containing this script and its parent (build_modules)
        script_dir = Path(__file__).parent.resolve()
        build_modules_dir = script_dir.parent

        # Add build_modules to path so we can import as a package
        if str(build_modules_dir) not in sys.path:
            sys.path.insert(0, str(build_modules_dir))

        # Import as package to preserve relative imports
        from generate_interlinear.generate_interlinear import generate_interlinear_translations

        # Generate interlinear for this work
        # generate_interlinear_translations expects a db_path and output_dir
        generate_interlinear_translations(
            db_path=Path(db_path),
            output_dir=output_dir,
            work_ids=[work_id]
        )

        return (work_index, author, work_title, True, "")

    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        return (work_index, author, work_title, False, error_msg)


def generate_interlinear_parallel(
    works: List[Tuple[str, str, str]],
    db_path: str,
    output_dir: Path,
    num_workers: int = 4
) -> Tuple[int, int]:
    """
    Generate interlinear XML files in parallel for multiple works.

    Args:
        works: List of (author, work_title, work_id) tuples
        db_path: Path to database file
        output_dir: Output directory for XML files
        num_workers: Number of parallel workers

    Returns:
        (num_success, num_failures)
    """
    print(f"\n{'='*80}")
    print(f"Parallel Interlinear Generation")
    print(f"{'='*80}")
    print(f"Works to process: {len(works)}")
    print(f"Database: {db_path}")
    print(f"Output directory: {output_dir}")
    print(f"Workers: {num_workers}")
    print(f"{'='*80}\n")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Prepare work batches with indices for ordering
    work_args = [
        (i, author, work_title, work_id, db_path, output_dir)
        for i, (author, work_title, work_id) in enumerate(works)
    ]

    start_time = time.time()

    # Process works in parallel
    if num_workers == 1:
        # Serial processing for debugging
        print("Running in SERIAL mode (1 worker)")
        results = []
        for args in work_args:
            results.append(process_work_worker(args))
    else:
        # Parallel processing
        print(f"Running in PARALLEL mode ({num_workers} workers)")
        with mp.Pool(num_workers) as pool:
            results = pool.map(process_work_worker, work_args)

    # Sort results by work index to maintain order
    results.sort(key=lambda x: x[0])

    # Count successes and failures
    num_success = sum(1 for _, _, _, success, _ in results if success)
    num_failures = len(results) - num_success

    # Display results
    print(f"\n{'='*80}")
    print(f"RESULTS")
    print(f"{'='*80}")

    for work_idx, author, work_title, success, error_msg in results:
        if success:
            print(f"✓ [{work_idx+1}/{len(works)}] {author} - {work_title}")
        else:
            print(f"✗ [{work_idx+1}/{len(works)}] {author} - {work_title} FAILED")
            if error_msg:
                # Print first line of error
                first_line = error_msg.split('\n')[0]
                print(f"    Error: {first_line}")

    elapsed_time = time.time() - start_time

    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total works: {len(works)}")
    print(f"Successful: {num_success}")
    print(f"Failed: {num_failures}")
    print(f"Time elapsed: {elapsed_time:.1f} seconds")
    if len(works) > 0:
        print(f"Average time per work: {elapsed_time/len(works):.1f} seconds")
    print(f"{'='*80}\n")

    return num_success, num_failures


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    # Parse arguments
    csv_path = Path(sys.argv[1])
    db_path = sys.argv[2]

    # Parse options
    num_workers = 4
    # Default output: go up to data-prep, then to data-sources/classicsviewer_interlinear
    script_dir = Path(__file__).parent.resolve()
    build_modules_dir = script_dir.parent
    data_prep_dir = build_modules_dir.parent
    output_dir = data_prep_dir.parent / 'data-sources' / 'classicsviewer_interlinear'

    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == '--workers' and i + 1 < len(sys.argv):
            num_workers = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--output' and i + 1 < len(sys.argv):
            output_dir = Path(sys.argv[i + 1])
            i += 2
        else:
            print(f"Unknown option: {sys.argv[i]}")
            print(__doc__)
            sys.exit(1)

    # Validate inputs
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)

    if not Path(db_path).exists():
        print(f"Error: Database not found: {db_path}")
        sys.exit(1)

    # Load works from CSV and resolve to work_ids
    print(f"Loading works from {csv_path}...")
    works = load_works_from_csv(csv_path, db_path)

    if not works:
        print("Error: No works found/resolved in CSV")
        sys.exit(1)

    print(f"Resolved {len(works)} works to work_ids")

    # Generate interlinear translations in parallel
    num_success, num_failures = generate_interlinear_parallel(
        works=works,
        db_path=db_path,
        output_dir=output_dir,
        num_workers=num_workers
    )

    # Exit with appropriate code
    sys.exit(0 if num_failures == 0 else 1)


if __name__ == '__main__':
    # Set multiprocessing start method for compatibility
    mp.set_start_method('spawn', force=True)
    main()
