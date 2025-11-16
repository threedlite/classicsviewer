#!/usr/bin/env python3
"""
Batch Sanskrit Interlinear and TEI XML Generation

Unified script for batch processing Sanskrit works.

Features:
- Generate interlinear text files (.interlinear.txt)
- Generate TEI XML files (.dcs-eng99.xml) with translations
- Single-threaded or parallel processing
- Multiple modes: all works, only DCS, only with translations

Usage:
  python3 batch_generate_interlinear.py <database> [options]

Options:
  --mode <mode>        Selection mode (default: translations)
                       - translations: Works with translations only
                       - dcs: DCS texts only (excludes BG, RV)
                       - all: All works
  --parallel <N>       Use N parallel workers (default: 1 = sequential)
  --tei                Also generate TEI XML files
  --output <dir>       Output directory (default: ./interlinear)

Examples:
  # Generate interlinear for works with translations (sequential)
  python3 batch_generate_interlinear.py sanskrit_texts.db

  # Generate both interlinear and TEI for works with translations
  python3 batch_generate_interlinear.py sanskrit_texts.db --tei

  # Generate all DCS works in parallel with 8 workers
  python3 batch_generate_interlinear.py sanskrit_texts_full.db --mode dcs --parallel 8

  # Generate everything with TEI in parallel
  python3 batch_generate_interlinear.py sanskrit_texts_full.db --mode all --parallel 8 --tei
"""

import sqlite3
import time
import argparse
import multiprocessing as mp
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from generate_sanskrit_interlinear import SanskritInterlinearGenerator


def get_works(db_path: str) -> List[Dict]:
    """
    Get all works from the database.

    Args:
        db_path: Path to Sanskrit database

    Returns:
        List of work dictionaries with id, title, author
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all works
    cursor.execute("""
        SELECT w.id, w.title, w.title_english, a.name as author_name
        FROM works w
        JOIN authors a ON w.author_id = a.id
        ORDER BY w.title_english
    """)

    works = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return works


def process_work_sequential(db_path: str, work_info: Dict, output_dir: Path) -> Dict:
    """
    Process a single work sequentially (main thread).

    Always generates:
    1. Interlinear text file (word-by-word glosses)
    2. TEI XML file (with translations if available)

    Args:
        db_path: Path to database
        work_info: Work information dictionary
        output_dir: Output directory

    Returns:
        Dictionary with statistics
    """
    work_id = work_info['id']
    title = work_info['title_english']

    print(f"\n{title}")
    print("-" * 70)

    start_time = time.time()
    stats = {
        'work_id': work_id,
        'title': title,
        'success': False,
        'lines': 0,
        'words_total': 0,
        'words_found': 0,
        'duration': 0,
        'error': None,
        'tei_generated': False
    }

    try:
        # Generate both interlinear text and TEI XML with single generator instance
        interlinear_file = output_dir / f"{work_id}.interlinear.txt"
        tei_file = output_dir / f"{work_id}.dcs-eng99.xml"

        with SanskritInterlinearGenerator(db_path) as gen:
            gen.write_interlinear_file(work_id, interlinear_file)
            gen.write_tei_file(work_id, tei_file)
            print(f"  ✓ Created TEI XML: {tei_file.name}")

            stats['lines'] = gen.stats['lines_processed']
            stats['words_total'] = gen.stats['words_total']
            stats['words_found'] = gen.stats['words_found']
            stats['tei_generated'] = True

        stats['success'] = True
        stats['duration'] = time.time() - start_time

    except Exception as e:
        stats['error'] = str(e)
        stats['duration'] = time.time() - start_time
        print(f"  ✗ Error: {e}")

    return stats


def process_work_parallel(args: Tuple[str, Dict, Path]) -> Dict:
    """
    Process a single work (worker function for multiprocessing).

    Always generates:
    1. Interlinear text file (word-by-word glosses)
    2. TEI XML file (with translations if available)

    Args:
        args: Tuple of (db_path, work_info, output_dir)

    Returns:
        Dictionary with statistics
    """
    db_path, work_info, output_dir = args
    work_id = work_info['id']
    title = work_info['title_english']

    start_time = time.time()
    stats = {
        'work_id': work_id,
        'title': title,
        'success': False,
        'lines': 0,
        'words_total': 0,
        'words_found': 0,
        'duration': 0,
        'error': None,
        'tei_generated': False
    }

    try:
        # Generate both interlinear text and TEI XML with single generator instance
        interlinear_file = output_dir / f"{work_id}.interlinear.txt"
        tei_file = output_dir / f"{work_id}.dcs-eng99.xml"

        with SanskritInterlinearGenerator(db_path) as gen:
            gen.write_interlinear_file(work_id, interlinear_file)
            gen.write_tei_file(work_id, tei_file)

            stats['lines'] = gen.stats['lines_processed']
            stats['words_total'] = gen.stats['words_total']
            stats['words_found'] = gen.stats['words_found']
            stats['tei_generated'] = True

        stats['success'] = True
        stats['duration'] = time.time() - start_time

    except Exception as e:
        stats['error'] = str(e)
        stats['duration'] = time.time() - start_time
        print(f"  ✗ Error processing {title}: {e}")

    return stats


def batch_generate(db_path: str, output_dir: Path, num_workers: int = 1):
    """
    Generate interlinear and TEI for all works in database.

    Always generates for each work:
    1. Interlinear text file (word-by-word glosses)
    2. TEI XML file (includes translations if available in database)

    Args:
        db_path: Path to Sanskrit database
        output_dir: Directory for output files
        num_workers: Number of parallel workers (1 = sequential)
    """
    print("=" * 70)
    print("Sanskrit Batch Generation")
    print("=" * 70)
    print(f"Database: {db_path}")
    print(f"Output: {output_dir}")
    print(f"Workers: {num_workers} ({'parallel' if num_workers > 1 else 'sequential'})")
    print()

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all works to process
    works = get_works(db_path)
    print(f"Found {len(works)} works to process")
    print("Generating for each work:")
    print("  - Interlinear text file (word-by-word glosses)")
    print("  - TEI XML file (with translations if available)\n")

    start_time = time.time()

    # Process works
    if num_workers > 1:
        # Parallel processing
        work_args = [(db_path, work, output_dir) for work in works]
        with mp.Pool(processes=num_workers) as pool:
            results = pool.map(process_work_parallel, work_args)
    else:
        # Sequential processing
        results = [process_work_sequential(db_path, work, output_dir)
                   for work in works]

    total_duration = time.time() - start_time

    # Aggregate statistics
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    total_lines = sum(r['lines'] for r in successful)
    total_words = sum(r['words_total'] for r in successful)
    total_found = sum(r['words_found'] for r in successful)
    tei_generated = sum(1 for r in successful if r['tei_generated'])

    # Print summary
    print("\n" + "=" * 70)
    print("Batch Generation Complete")
    print("=" * 70)
    print(f"Works processed: {len(works)}")
    print(f"  Successful: {len(successful)}")
    print(f"  Failed: {len(failed)}")
    print()
    print(f"Total lines: {total_lines:,}")
    print(f"Total words: {total_words:,}")
    if total_words > 0:
        print(f"  Found in dictionary: {total_found:,} ({100*total_found/total_words:.1f}%)")
        print(f"  Missing: {total_words - total_found:,} ({100*(total_words-total_found)/total_words:.1f}%)")
    print()
    print(f"Total duration: {total_duration:.1f}s")
    if len(works) > 0:
        print(f"Average per work: {total_duration/len(works):.1f}s")
    print()
    print("Files generated:")
    print(f"  - {len(successful)} interlinear text files (.interlinear.txt)")
    print(f"  - {tei_generated} TEI XML files (.dcs-eng99.xml)")

    # Print failures if any
    if failed:
        print("\nFailed works:")
        for r in failed:
            print(f"  ✗ {r['title']}: {r['error']}")

    # Write summary report
    report_path = output_dir / "generation_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("Sanskrit Batch Generation Report\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Database: {db_path}\n")
        f.write(f"Workers: {num_workers}\n\n")

        f.write(f"Works processed: {len(works)}\n")
        f.write(f"  Successful: {len(successful)}\n")
        f.write(f"  Failed: {len(failed)}\n\n")

        f.write(f"Total lines: {total_lines:,}\n")
        f.write(f"Total words: {total_words:,}\n")
        if total_words > 0:
            f.write(f"  Found: {total_found:,} ({100*total_found/total_words:.1f}%)\n")
            f.write(f"  Missing: {total_words - total_found:,} ({100*(total_words-total_found)/total_words:.1f}%)\n\n")

        f.write(f"Duration: {total_duration:.1f}s\n")
        if len(works) > 0:
            f.write(f"Average per work: {total_duration/len(works):.1f}s\n\n")

        if successful:
            f.write("\nSuccessful works:\n")
            f.write("-" * 70 + "\n")
            for r in sorted(successful, key=lambda x: x['title']):
                coverage = 100 * r['words_found'] / r['words_total'] if r['words_total'] > 0 else 0
                f.write(f"{r['title']}\n")
                f.write(f"  Lines: {r['lines']:,} | Words: {r['words_total']:,} | Coverage: {coverage:.1f}%")
                if r['tei_generated']:
                    f.write(" | TEI: yes")
                f.write("\n")

        if failed:
            f.write("\n\nFailed works:\n")
            f.write("-" * 70 + "\n")
            for r in sorted(failed, key=lambda x: x['title']):
                f.write(f"{r['title']}: {r['error']}\n")

    print(f"\nReport written to: {report_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Batch generate Sanskrit interlinear and TEI XML files for all works',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Generates both .interlinear.txt and .dcs-eng99.xml files for every work in the database.

Examples:
  # Generate all works (sequential)
  %(prog)s sanskrit_texts.db

  # Generate all works in parallel with 8 workers
  %(prog)s sanskrit_texts_full.db --parallel 8

  # Custom output directory
  %(prog)s sanskrit_texts.db --output /path/to/output
        """
    )

    parser.add_argument('database', help='Path to Sanskrit database')
    parser.add_argument('--parallel', type=int, default=1, metavar='N',
                       help='Number of parallel workers (default: 1 = sequential)')
    parser.add_argument('--output', type=Path, default=Path('../data-sources/classicsviewer_interlinear'),
                       help='Output directory (default: ../data-sources/classicsviewer_interlinear)')

    args = parser.parse_args()

    batch_generate(
        db_path=args.database,
        output_dir=args.output,
        num_workers=args.parallel
    )


if __name__ == '__main__':
    main()
