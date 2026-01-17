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
    --no-tree       Disable CLTK sentence tree analysis (POS, deprel, head) for faster builds

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


def process_work_worker(args: Tuple[int, str, str, str, str, Path, bool]) -> Tuple[int, str, str, bool, str]:
    """
    Worker function that generates interlinear XML for ONE work.

    Args:
        args: (work_index, author, work_title, work_id, db_path, output_dir, no_tree)

    Returns:
        (work_index, author, work_title, success, error_message)
    """
    import sys
    from pathlib import Path

    work_index, author, work_title, work_id, db_path, output_dir, no_tree = args

    # Log work start
    print(f"\n{'='*80}")
    print(f"STARTING WORK #{work_index}: {work_id}")
    print(f"Author: {author}")
    print(f"Title: {work_title}")
    print(f"{'='*80}\n")
    sys.stdout.flush()  # Force flush to see output immediately

    try:
        # Import the generate_interlinear module

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
            work_ids=[work_id],
            no_tree=no_tree
        )

        return (work_index, author, work_title, True, "")

    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        return (work_index, author, work_title, False, error_msg)


def process_worker_chunk(args: Tuple[int, List[Tuple[int, str, str, str]], str, Path, dict, int, int, int, float, dict, bool]) -> List[Tuple[int, str, str, bool, str]]:
    """
    Worker function that processes a chunk of works assigned to one worker.

    Args:
        args: (worker_id, work_list, db_path, output_dir, work_size_lookup, total_works, total_words, total_effective_cost, start_time, completed_tracker, no_tree)
              where work_list is [(work_index, author, work_title, work_id), ...]
              work_size_lookup maps work_id -> (total_words, unique_words, effective_cost)
              completed_tracker is a shared dict to track completed works: work_id -> (total_words, unique_words, effective_cost)
              no_tree: If True, skip CLTK sentence tree analysis

    Returns:
        List of (work_index, author, work_title, success, error_message) for all works processed
    """
    import sys
    import time

    worker_id, work_list, db_path, output_dir, work_size_lookup, total_works, total_words, total_effective_cost, start_time, completed_tracker, no_tree = args
    results = []

    print(f"\n{'='*80}")
    print(f"WORKER {worker_id} STARTING - {len(work_list)} works assigned")
    print(f"{'='*80}\n")
    sys.stdout.flush()

    for i, (work_index, author, work_title, work_id) in enumerate(work_list):
        # Process this work
        result = process_work_worker((work_index, author, work_title, work_id, db_path, output_dir, no_tree))
        results.append(result)

        # Report completion immediately with progress
        success = result[3]
        status = "✓" if success else "✗"

        # Track words for this work: (total_words, unique_words, effective_cost)
        work_counts = work_size_lookup.get(work_id, (0, 0, 0))

        # Mark this work as completed in shared tracker
        completed_tracker[work_id] = work_counts

        # Calculate global progress from shared tracker
        # Use effective cost (unique + 100*elided) for progress since elided words are ~100x slower
        global_words_completed = sum(v[0] for v in completed_tracker.values())
        global_cost_completed = sum(v[2] for v in completed_tracker.values())

        elapsed = time.time() - start_time
        # Progress based on effective cost (accounts for slow elided word processing)
        progress_pct = (global_cost_completed / total_effective_cost * 100) if total_effective_cost > 0 else 0

        # Calculate ETA based on effective cost processing rate
        if global_cost_completed > 0 and progress_pct < 100:
            rate = global_cost_completed / elapsed  # effective cost units per second
            remaining_cost = total_effective_cost - global_cost_completed
            eta_seconds = remaining_cost / rate
            eta_str = f"ETA: {eta_seconds/60:.1f}m"
        else:
            eta_str = ""

        print(f"\n{status} [Worker {worker_id}] {author} - {work_title}")
        print(f"  Progress: {global_words_completed:,}/{total_words:,} words ({progress_pct:.1f}%) | Elapsed: {elapsed/60:.1f}m {eta_str}")
        sys.stdout.flush()

    print(f"\n{'='*80}")
    print(f"WORKER {worker_id} FINISHED - {len(work_list)} works completed")
    print(f"{'='*80}\n")
    sys.stdout.flush()

    return results


def generate_interlinear_parallel(
    works: List[Tuple[str, str, str]],
    db_path: str,
    output_dir: Path,
    num_workers: int = 4,
    no_tree: bool = False
) -> Tuple[int, int]:
    """
    Generate interlinear XML files in parallel for multiple works.

    Args:
        works: List of (author, work_title, work_id) tuples
        db_path: Path to database file
        output_dir: Output directory for XML files
        num_workers: Number of parallel workers
        no_tree: If True, skip CLTK sentence tree analysis (faster)

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
    print(f"Tree analysis: {'DISABLED' if no_tree else 'ENABLED'}")
    print(f"{'='*80}\n")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get work sizes using efficient batch queries with temporary table
    # (IN clause has ~999 parameter limit, so we use a temp table for large lists)
    # Use in-memory db for temp table, ATTACH main db as read-only for speed
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute(f"ATTACH DATABASE 'file:{db_path}?mode=ro' AS perseus")

    # Extract work_ids and build lookup
    work_ids = [work_id for _, _, work_id in works]
    work_info = {work_id: (author, work_title) for author, work_title, work_id in works}

    # Create temporary table with work_ids for efficient joining
    cursor.execute("CREATE TABLE temp_work_ids (work_id TEXT PRIMARY KEY)")
    cursor.executemany("INSERT INTO temp_work_ids VALUES (?)", [(wid,) for wid in work_ids])

    # Batch query for book counts using temp table join
    cursor.execute("""
        SELECT b.work_id, COUNT(*) as book_count
        FROM perseus.books b
        INNER JOIN temp_work_ids t ON b.work_id = t.work_id
        GROUP BY b.work_id
    """)
    book_counts = {row[0]: row[1] for row in cursor.fetchall()}

    # Batch query for word counts (total, unique, and elided) - single efficient query
    # Elided words (ending in apostrophe) trigger expensive LIKE queries (~1s each vs 0.04ms for exact match)
    print("Querying word counts (this may take a few seconds for large databases)...")
    query_start = time.time()
    # Apostrophe variants used in Greek texts:
    apos_curly = "%\u2019"   # ' RIGHT SINGLE QUOTATION MARK (U+2019)
    apos_straight = "%\u0027"  # ' APOSTROPHE (U+0027)
    apos_modifier = "%\u02BC"  # ʼ MODIFIER LETTER APOSTROPHE (U+02BC)
    cursor.execute("""
        SELECT b.work_id,
               COUNT(*) as total_words,
               COUNT(DISTINCT w.word) as unique_words,
               COUNT(DISTINCT CASE WHEN w.word LIKE ? OR w.word LIKE ? OR w.word LIKE ? THEN w.word END) as elided_words
        FROM perseus.words w
        INNER JOIN perseus.books b ON w.book_id = b.id
        INNER JOIN temp_work_ids t ON b.work_id = t.work_id
        GROUP BY b.work_id
    """, (apos_curly, apos_straight, apos_modifier))
    word_counts = {row[0]: (row[1], row[2], row[3] or 0) for row in cursor.fetchall()}
    print(f"  Word count query completed in {time.time() - query_start:.1f}s")

    conn.close()

    # Build work_sizes list from batch query results
    # Elided words are ~100x more expensive than normal words (LIKE query vs exact match)
    ELIDED_WORD_COST_MULTIPLIER = 100
    work_sizes = []
    for work_id in work_ids:
        author, work_title = work_info[work_id]
        book_count = book_counts.get(work_id, 0)
        word_count, unique_word_count, elided_word_count = word_counts.get(work_id, (0, 0, 0))
        # Effective cost = unique words + (elided words * 100) since LIKE queries are ~100x slower
        effective_cost = unique_word_count + (elided_word_count * ELIDED_WORD_COST_MULTIPLIER)
        work_sizes.append((author, work_title, work_id, book_count, word_count, unique_word_count, elided_word_count, effective_cost))

    # Sort by effective_cost descending (most expensive works first)
    # This accounts for both unique words and expensive elided word LIKE queries
    work_sizes.sort(key=lambda x: x[7], reverse=True)

    # Calculate totals for progress tracking
    # Use effective cost (unique + 100*elided) for ETA since elided words are much slower
    total_words = sum(size[4] for size in work_sizes)
    total_unique_words = sum(size[5] for size in work_sizes)
    total_elided_words = sum(size[6] for size in work_sizes)
    total_effective_cost = sum(size[7] for size in work_sizes)
    total_books = sum(size[3] for size in work_sizes)

    print(f"\nWork size distribution:")
    print(f"  Total words: {total_words:,}")
    print(f"  Total unique words: {total_unique_words:,} ({total_unique_words/total_words*100:.1f}% of total)")
    print(f"  Total elided words: {total_elided_words:,} ({total_elided_words/total_unique_words*100:.1f}% of unique)")
    print(f"  Total effective cost: {total_effective_cost:,} (unique + 100×elided)")
    print(f"  Total books: {total_books:,}")
    print(f"  Most expensive work: {work_sizes[0][5]:,} unique, {work_sizes[0][6]:,} elided, cost={work_sizes[0][7]:,} ({work_sizes[0][1]})")
    if len(work_sizes) > 1:
        print(f"  Second most expensive: {work_sizes[1][5]:,} unique, {work_sizes[1][6]:,} elided, cost={work_sizes[1][7]:,} ({work_sizes[1][1]})")
    print(f"  Least expensive work: {work_sizes[-1][5]:,} unique, {work_sizes[-1][6]:,} elided, cost={work_sizes[-1][7]:,} ({work_sizes[-1][1]})")
    print(f"  Sorted works by effective cost (largest first) for load balancing\n")

    # Prepare work batches with indices for ordering
    work_args = [
        (i, author, work_title, work_id, db_path, output_dir, no_tree)
        for i, (author, work_title, work_id, _, _, _, _, _) in enumerate(work_sizes)
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
        # This balances effective cost per worker (unique + 100×elided, since LIKE queries are ~100x slower)
        worker_chunks = [[] for _ in range(num_workers)]
        worker_loads = [0] * num_workers  # Track effective cost per worker

        for work_index, author, work_title, work_id, _, _, _ in work_args:
            # Find worker with minimum load
            min_worker = worker_loads.index(min(worker_loads))
            worker_chunks[min_worker].append((work_index, author, work_title, work_id))
            # Update load with this work's effective cost (unique + 100×elided)
            worker_loads[min_worker] += work_sizes[work_index][7]

        # Show worker assignments with total load
        print("Worker assignments (load-balanced by effective cost = unique + 100×elided):")
        for worker_id in range(num_workers):
            chunk_size = len(worker_chunks[worker_id])
            total_load = worker_loads[worker_id]
            if chunk_size > 0:
                first_work = worker_chunks[worker_id][0]
                work_idx, author, title, work_id = first_work
                effective_cost = work_sizes[work_idx][7]
                elided_count = work_sizes[work_idx][6]
                print(f"  Worker {worker_id}: {chunk_size} works, cost={total_load:,}, first = {work_id} (cost={effective_cost:,}, {elided_count} elided)")
        print()

        # Create lookup dicts for work sizes (must be before worker_args uses it)
        # work_size_lookup: work_id -> (total_words, unique_words, effective_cost)
        work_size_lookup = {work_sizes[i][2]: (work_sizes[i][4], work_sizes[i][5], work_sizes[i][7]) for i in range(len(work_sizes))}

        # Create a shared dict to track completed works across all workers
        manager = mp.Manager()
        completed_tracker = manager.dict()  # work_id -> (total_words, unique_words, effective_cost)

        # Create worker arguments with additional context for ETA calculation
        # Use total_effective_cost for progress tracking since it accounts for elided word overhead
        worker_args = [
            (worker_id, worker_chunks[worker_id], db_path, output_dir, work_size_lookup, len(works), total_words, total_effective_cost, start_time, completed_tracker, no_tree)
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
    no_tree = False  # Default: generate tree data
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
        elif sys.argv[i] == '--no-tree':
            no_tree = True
            i += 1
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
        num_workers=num_workers,
        no_tree=no_tree
    )

    # Exit with appropriate code
    sys.exit(0 if num_failures == 0 else 1)


if __name__ == '__main__':
    # Set multiprocessing start method for compatibility
    mp.set_start_method('spawn', force=True)
    main()
