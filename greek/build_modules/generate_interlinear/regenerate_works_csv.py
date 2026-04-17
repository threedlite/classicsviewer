#!/usr/bin/env python3
"""Regenerate INTERLINEAR_ALL_GREEK_WITH_IDS.csv from a freshly built DB.

After a Perseus/First1K/PTA update, the Greek works table may have gained
or lost entries. The interlinear generator reads its work list from
INTERLINEAR_ALL_GREEK_WITH_IDS.csv — if that CSV is stale, new works get
no interlinear and deleted works leave orphan generation attempts.

This script rebuilds the CSV from the canonical source (the fresh Greek
DB's works table), so the interlinear pass always sees the current corpus.

Usage:
    regenerate_works_csv.py <greek_texts.db> [<output_csv>]

Default output path is this script's sibling
INTERLINEAR_ALL_GREEK_WITH_IDS.csv, matching what
`run_interlinear_no_sleep.sh` expects.
"""

import csv
import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_CSV = SCRIPT_DIR / "INTERLINEAR_ALL_GREEK_WITH_IDS.csv"


def regenerate(db_path: Path, csv_path: Path) -> int:
    """Write every Greek work to csv_path. Returns row count."""
    if not db_path.exists():
        raise FileNotFoundError(
            f"CRITICAL: Greek DB not found: {db_path}\n"
            f"  Build it first with: cd greek && ./run_build.sh extended"
        )

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        # Pull every Greek work. Prefer English title for the Work column;
        # fall back to the primary title if English is absent (some First1K
        # entries have only a Latin/Greek title).
        rows = conn.execute("""
            SELECT a.name                                 AS author,
                   COALESCE(w.title_english, w.title)     AS work,
                   w.id                                   AS work_id
            FROM works w
            JOIN authors a ON w.author_id = a.id
            WHERE a.language = 'greek'
            ORDER BY a.name COLLATE NOCASE, work COLLATE NOCASE, w.id
        """).fetchall()
    finally:
        conn.close()

    if not rows:
        raise RuntimeError(
            f"CRITICAL: no Greek works found in {db_path}. Build is empty or "
            f"language-filter SQL is broken; aborting CSV regeneration."
        )

    # Write atomically: temp file + os.replace. Matches the interlinear
    # generator's own atomic-write discipline so a kill mid-write never
    # leaves a partial CSV on disk.
    tmp_path = csv_path.with_suffix(csv_path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(["Author", "Work", "WorkID"])
        for author, work, work_id in rows:
            writer.writerow([author or "", work or work_id, work_id])
    import os
    os.replace(tmp_path, csv_path)

    return len(rows)


def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(__doc__.rstrip(), file=sys.stderr)
        sys.exit(2)

    db_path = Path(sys.argv[1]).resolve()
    csv_path = Path(sys.argv[2]).resolve() if len(sys.argv) == 3 else DEFAULT_CSV

    n = regenerate(db_path, csv_path)
    print(f"[regenerate_works_csv] wrote {n:,} Greek works to {csv_path}")


if __name__ == "__main__":
    main()
