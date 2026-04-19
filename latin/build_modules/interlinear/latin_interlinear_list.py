#!/usr/bin/env python3
"""
Parallel Latin Interlinear Generator from Author/Work CSV
=========================================================

Generates interlinear translation XML files for Latin works listed in a CSV file,
using multi-threading to process works in parallel.

⚠️  IMPORTANT: Process Management
---------------------------------
This script uses multiprocessing with 'spawn' method, creating multiple worker processes.

**BEFORE RESTARTING OR MODIFYING CODE:**
1. Kill ALL related Python processes (not just the main script!)
2. Clear Python bytecode cache (__pycache__, *.pyc files)
3. Verify no workers are still running

Commands to ensure clean restart:

    # Clear Python cache
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} +

    # Verify no processes remain
    ps aux | grep python

⚠️  If you don't kill worker processes, they will continue running with OLD CODE
    even after you modify and restart the main script! This causes corrupted output.

Usage:
    python3 latin_interlinear_list.py <input_csv> <database_path> [options]

Options:
    --workers N     Number of parallel workers (default: 4)
    --output DIR    Output directory for XML files (default: ../../interlinear_output)

Input CSV format (Author,Work,WorkID):
    Author,Work,WorkID
    Cicero,Pro P. Quinctio,phi0474.phi001
    Virgil,Aeneid,phi0690.phi003

Outputs:
    <output_dir>/<work_id>.perseus-eng99.xml for each work
    <output_dir>/<work_id>.interlinear.txt for each work

Examples:
    # Generate interlinear for all Latin works
    python3 latin_interlinear_list.py INTERLINEAR_ALL_LATIN_WITH_IDS.csv ../../perseus_texts_full.db --workers 8
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
        work_id (e.g., 'phi0690.phi003') or None if not found
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
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

    Supports two CSV formats:
    1. With WorkID column: Uses work_id directly (no database lookup needed)
    2. Without WorkID column: Looks up work_id from Author/Work (legacy format)

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

            # Check if CSV has WorkID column (preferred method)
            if 'WorkID' in row and row['WorkID'].strip():
                work_id = row['WorkID'].strip()
                works.append((author, work_title, work_id))
            else:
                # Legacy format: Look up work_id in database
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
    Worker function that generates Latin interlinear XML for ONE work.

    Args:
        args: (work_index, author, work_title, work_id, db_path, output_dir)

    Returns:
        (work_index, author, work_title, success, error_message)
    """
    import sys
    from pathlib import Path

    work_index, author, work_title, work_id, db_path, output_dir = args

    # Log work start
    print(f"\n{'='*80}")
    print(f"STARTING LATIN WORK #{work_index}: {work_id}")
    print(f"Author: {author}")
    print(f"Title: {work_title}")
    print(f"{'='*80}\n")
    sys.stdout.flush()  # Force flush to see output immediately

    try:
        # Import the generate_latin_interlinear module (co-located in the
        # same directory in the Latin module layout).
        script_dir = Path(__file__).parent.resolve()
        if str(script_dir) not in sys.path:
            sys.path.insert(0, str(script_dir))
        from generate_latin_interlinear import generate_latin_interlinear_translations

        # Generate interlinear for this work
        generate_latin_interlinear_translations(
            db_path=Path(db_path),
            output_dir=output_dir,
            work_ids=[work_id]
        )

        return (work_index, author, work_title, True, "")

    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        return (work_index, author, work_title, False, error_msg)


def process_worker_chunk(args: Tuple[int, List[Tuple[int, str, str, str]], str, Path, dict, int, int, float, dict]) -> List[Tuple[int, str, str, bool, str]]:
    """
    Worker function that processes a chunk of works assigned to one worker.

    Args:
        args: (worker_id, work_list, db_path, output_dir, work_size_lookup, total_works, total_lines, start_time, completed_tracker)
              where work_list is [(work_index, author, work_title, work_id), ...]
              completed_tracker is a shared dict to track completed lines

    Returns:
        List of (work_index, author, work_title, success, error_message) for all works processed
    """
    import sys
    import time

    worker_id, work_list, db_path, output_dir, work_size_lookup, total_works, total_lines, start_time, completed_tracker = args
    results = []

    print(f"\n{'='*80}")
    print(f"WORKER {worker_id} STARTING - {len(work_list)} Latin works assigned")
    print(f"{'='*80}\n")
    sys.stdout.flush()

    for i, (work_index, author, work_title, work_id) in enumerate(work_list):
        # Process this work
        result = process_work_worker((work_index, author, work_title, work_id, db_path, output_dir))
        results.append(result)

        # Report completion immediately with progress
        success = result[3]
        status = "✓" if success else "✗"

        # Track actual lines for this work
        lines_in_work = work_size_lookup.get(work_id, 0)

        # Mark this work as completed in shared tracker
        completed_tracker[work_id] = lines_in_work

        # Calculate global lines completed from shared tracker
        global_lines_completed = sum(completed_tracker.values())

        elapsed = time.time() - start_time
        progress_pct = (global_lines_completed / total_lines * 100) if total_lines > 0 else 0

        print(f"\n{status} [Worker {worker_id}] {author} - {work_title}")
        print(f"  Progress: {global_lines_completed:,}/{total_lines:,} lines ({progress_pct:.1f}%) | Elapsed: {elapsed/60:.1f}m")
        sys.stdout.flush()

    print(f"\n{'='*80}")
    print(f"WORKER {worker_id} FINISHED - {len(work_list)} Latin works completed")
    print(f"{'='*80}\n")
    sys.stdout.flush()

    return results


def generate_interlinear_parallel(
    works: List[Tuple[str, str, str]],
    db_path: str,
    output_dir: Path,
    num_workers: int = 4
) -> Tuple[int, int]:
    """
    Generate Latin interlinear XML files in parallel for multiple works.

    Args:
        works: List of (author, work_title, work_id) tuples
        db_path: Path to database file
        output_dir: Output directory for XML files
        num_workers: Number of parallel workers

    Returns:
        (num_success, num_failures)
    """
    print(f"\n{'='*80}")
    print(f"Parallel Latin Interlinear Generation")
    print(f"{'='*80}")
    print(f"Works to process: {len(works)}")
    print(f"Database: {db_path}")
    print(f"Output directory: {output_dir}")
    print(f"Workers: {num_workers}")
    print(f"{'='*80}\n")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get work sizes (number of lines) and sort by size descending
    # This ensures largest works are distributed evenly across workers
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cursor = conn.cursor()

    work_sizes = []
    for author, work_title, work_id in works:
        cursor.execute("SELECT COUNT(*) FROM books WHERE work_id = ?", (work_id,))
        book_count = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(line_count) FROM books WHERE work_id = ?", (work_id,))
        line_count = cursor.fetchone()[0] or 0
        work_sizes.append((author, work_title, work_id, book_count, line_count))

    conn.close()

    # Sort by line_count descending (largest works first)
    work_sizes.sort(key=lambda x: x[4], reverse=True)

    # Calculate total lines for accurate ETA
    total_lines = sum(size[4] for size in work_sizes)
    total_books = sum(size[3] for size in work_sizes)

    print(f"\nWork size distribution:")
    print(f"  Total lines: {total_lines:,}")
    print(f"  Total books: {total_books:,}")
    print(f"  Largest work: {work_sizes[0][4]:,} lines, {work_sizes[0][3]} books ({work_sizes[0][1]} - {work_sizes[0][2]})")
    if len(work_sizes) > 1:
        print(f"  Second largest: {work_sizes[1][4]:,} lines, {work_sizes[1][3]} books ({work_sizes[1][1]} - {work_sizes[1][2]})")
    print(f"  Smallest work: {work_sizes[-1][4]:,} lines, {work_sizes[-1][3]} books ({work_sizes[-1][1]})")
    print(f"  Sorted works by size (largest first) with round-robin distribution\n")

    # Prepare work batches with indices for ordering
    work_args = [
        (i, author, work_title, work_id, db_path, output_dir)
        for i, (author, work_title, work_id, _, _) in enumerate(work_sizes)
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
        # Parallel processing with pre-assigned chunks (greedy load balancing)
        print(f"Running in PARALLEL mode ({num_workers} workers)")
        print("Using GREEDY LOAD BALANCING: each work assigned to least-loaded worker")
        print()

        # Distribute works using greedy "least loaded" algorithm (LPT)
        # This balances total lines per worker, not just work count
        worker_chunks = [[] for _ in range(num_workers)]
        worker_loads = [0] * num_workers  # Track total lines per worker

        for work_index, author, work_title, work_id, _, _ in work_args:
            # Find worker with minimum load
            min_worker = worker_loads.index(min(worker_loads))
            worker_chunks[min_worker].append((work_index, author, work_title, work_id))
            # Update load with this work's line count
            worker_loads[min_worker] += work_sizes[work_index][4]

        # Show worker assignments with total load
        print("Worker assignments (load-balanced):")
        for worker_id in range(num_workers):
            chunk_size = len(worker_chunks[worker_id])
            total_load = worker_loads[worker_id]
            if chunk_size > 0:
                first_work = worker_chunks[worker_id][0]
                work_idx, author, title, work_id = first_work
                line_count = work_sizes[work_idx][4]
                print(f"  Worker {worker_id}: {chunk_size} works, {total_load:,} total lines, first = {work_id} ({line_count:,} lines)")
        print()

        # Create a lookup dict for work sizes by lines (must be before worker_args uses it)
        work_size_lookup = {work_sizes[i][2]: work_sizes[i][4] for i in range(len(work_sizes))}

        # Create a shared dict to track completed works across all workers
        manager = mp.Manager()
        completed_tracker = manager.dict()

        # Create worker arguments with additional context for ETA calculation
        worker_args = [
            (worker_id, worker_chunks[worker_id], db_path, output_dir, work_size_lookup, len(works), total_lines, start_time, completed_tracker)
            for worker_id in range(num_workers)
            if len(worker_chunks[worker_id]) > 0
        ]

        # Track results
        results = []

        with mp.Pool(num_workers) as pool:
            # Submit each worker's chunk as a separate task
            async_results = []
            for worker_arg in worker_args:
                async_result = pool.apply_async(process_worker_chunk, args=(worker_arg,))
                async_results.append(async_result)

            # Workers will report their own progress in real-time
            # Just wait for all workers to finish (no need to process results here)
            print("\nWorkers are processing... Progress will be logged by workers.\n")
            sys.stdout.flush()

            # Wait for all async results to complete
            for async_result in async_results:
                async_result.wait()  # Just wait, don't get results

            # Now collect all results for final summary
            for async_result in async_results:
                worker_results = async_result.get()
                for result in worker_results:
                    results.append(result)

        print("\n\nAll workers completed!")

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
    print(f"Total Latin works: {len(works)}")
    print(f"Successful: {num_success}")
    print(f"Failed: {num_failures}")
    print(f"Time elapsed: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")
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
    # Default output: latin/interlinear_output/ (Latin module is self-contained).
    # Path: latin/build_modules/interlinear/ → latin/build_modules/ → latin/.
    script_dir = Path(__file__).parent.resolve()
    latin_root = script_dir.parent.parent
    output_dir = latin_root / 'interlinear_output'

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

    # Verify the database has OGA lemmas — interlinear glosses will be
    # incomplete without them.  The assembled DB from assemble_database.py
    # includes OGA; a raw module DB does not.
    import sqlite3 as _sql
    _conn = _sql.connect(db_path)
    _oga_count = _conn.execute(
        "SELECT COUNT(*) FROM lemma_map WHERE source = 'oga'"
    ).fetchone()[0]
    _conn.close()
    if _oga_count == 0:
        print(f"ERROR: Database has 0 OGA lemma entries: {db_path}")
        print("Interlinear generation requires the assembled DB (from assemble_database.py)")
        print("with OGA lemmas. Do NOT use a raw module DB. See BUILD.md build sequence.")
        sys.exit(1)
    print(f"OGA lemma check: {_oga_count:,} entries ✓")

    # Load works from CSV and resolve to work_ids
    print(f"Loading Latin works from {csv_path}...")
    works = load_works_from_csv(csv_path, db_path)

    if not works:
        print("Error: No Latin works found/resolved in CSV")
        sys.exit(1)

    print(f"Resolved {len(works)} Latin works to work_ids")

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
