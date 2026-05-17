#!/usr/bin/env python3
"""
create_latin_database.py — standalone builder for the Latin portion of the
Classics Viewer text corpus.

This is slice 4a of the Latin-module extraction (see GREEK_LATIN_MODULE_ANALYSIS.md
and FIX_PLAN.md). It produces `latin/latin_texts.db` containing:
  - Latin authors, works, books, text_lines, words
  - Latin translation_segments + translation_lookup
  - Whitaker's Latin dictionary entries + lemma_map
  - Latin prefix_assimilation_rules
  - milestone_line_ranges for Latin works

The final assembled classics-viewer database is produced by the monolith
(data-prep/create_perseus_database.py), which in slice 4b will skip Latin
author processing and instead merge the output of this script via
merge_database.py.

Strategy: wrap the monolith's processing functions via sys.path so that the
behaviour of Latin-author processing is bit-for-bit identical to the monolith's
current Latin handling. This avoids duplicating 1000+ lines of XML parsing
logic and keeps the monolith as the single source of truth for Latin-author
processing until a separate, deliberate refactor rewrites the Latin processing
independently.

Modes:
  sample   LATIN_SAMPLE.csv — **RELEASE** content for the Play Store sample
           APK. Output must stay bit-for-bit identical to the pre-cutover
           monolith sample so users see no change from this extraction.
           (Horace + Virgil, ~60s, Whitaker's omitted, Aeneid-only interlinear.)
  full     Every phi* author discovered under data-sources/canonical-latinLit/
           — no CSV filter. Matches the monolith's pre-cutover full build.
  extended Currently identical to `full` (same canonical-latinLit scan, no
           CSV filter). Kept as a distinct mode so Latin extended can diverge
           later (e.g. pick up Patristic Latin, medieval Latin, or additional
           aligned translations) without a code-level mode change.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared.venv_check import assert_libs  # noqa: E402
assert_libs("latin_build")
import argparse
import csv
import sqlite3
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Standalone Latin build: all processing code lives under latin/.
#
# monolith_fn.py is a vendored subset of data-prep/create_perseus_database.py
# (XML helpers, CTS parsers, process_perseus_author / process_text_file, the
# prose processors, translations, interlinear import, translation_lookup)
# with the Latin-specific get_paragraphs_for_div fix applied at the bottom.
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
DATA_SOURCES_DIR = REPO_ROOT / "data-sources"

if str(SCRIPT_DIR / "build_modules") not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR / "build_modules"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from monolith_fn import (  # noqa: E402
    process_perseus_author,
    create_translation_lookup_table,
    import_interlinear_translations,
    write_xml_patterns_file,
)
from load_whitakers_latin import load_whitakers_latin  # noqa: E402
from shared.database_schema import create_schema  # noqa: E402


# ---------------------------------------------------------------------------
# Author discovery and filtering
# ---------------------------------------------------------------------------

def discover_latin_authors(latin_dir: Path) -> dict:
    """Return {author_id: author_name} for every `phi*` author directory."""
    authors = {}
    for author_dir in sorted(latin_dir.iterdir()):
        if not (author_dir.is_dir() and author_dir.name.startswith("phi")):
            continue
        cts_file = author_dir / "__cts__.xml"
        name = f"Author {author_dir.name}"
        if cts_file.exists():
            try:
                root = ET.parse(cts_file).getroot()
                ns = {"ti": "http://chs.harvard.edu/xmlns/cts"}
                groupname = root.find(".//ti:groupname", ns)
                if groupname is not None and groupname.text:
                    name = groupname.text.strip()
            except Exception as e:
                print(f"  Warning: Failed to parse {cts_file}: {e}")
        authors[author_dir.name] = name
    return authors


def load_work_csv(csv_path: Path) -> tuple:
    """Return (author_names_set, author_to_works_dict) from a CSV."""
    authors = set()
    works: dict = {}
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            a = row["Author"]
            w = row.get("Work", "")
            authors.add(a)
            works.setdefault(a, set())
            if w:
                works[a].add(w)
    return authors, works


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def load_latin_prefix_assimilation_rules(cursor: sqlite3.Cursor):
    rules_file = SCRIPT_DIR / "data" / "latin_prefix_assimilation_rules.csv"
    if not rules_file.exists():
        print(f"  ! prefix_assimilation_rules CSV not found: {rules_file}")
        return
    n = 0
    with open(rules_file) as f:
        for row in csv.DictReader(f):
            cursor.execute("""
                INSERT INTO prefix_assimilation_rules
                (language, base_prefix, assimilated_form, meaning,
                 phonological_rule, priority, examples)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                row["language"], row["base_prefix"], row["assimilated_form"],
                row.get("meaning", ""), row.get("phonological_rule", ""),
                int(row["priority"]), row.get("examples", ""),
            ))
            n += 1
    print(f"  ✓ {n} Latin prefix assimilation rules imported")


def build(mode: str, output_db: Path, csv_path: Path = None):
    t0 = time.time()
    print(f"\n=== LATIN DATABASE BUILD (mode={mode}) ===")
    print(f"Output: {output_db}")

    latin_dir = DATA_SOURCES_DIR / "canonical-latinLit" / "data"
    if not latin_dir.exists():
        sys.exit(f"ERROR: Latin source directory not found: {latin_dir}")
    whitakers_dir = DATA_SOURCES_DIR / "whitakers-words"
    if not whitakers_dir.exists():
        sys.exit(f"ERROR: whitakers-words not found: {whitakers_dir}\n"
                 f"Clone it first: cd data-sources && git clone https://github.com/mk270/whitakers-words.git")

    # Author filter.
    # - `sample` uses LATIN_SAMPLE.csv (release-pinned list).
    # - `full` and `extended` scan every phi* author under canonical-latinLit/
    #   and process them all (no CSV), matching pre-cutover monolith behaviour.
    # --csv overrides the default in any mode.
    sample_authors = None
    sample_works = None
    if csv_path is None and mode == "sample":
        csv_path = SCRIPT_DIR / "LATIN_SAMPLE.csv"
    if csv_path is not None:
        if not csv_path.exists():
            sys.exit(f"ERROR: CSV not found: {csv_path}")
        sample_authors, sample_works = load_work_csv(csv_path)
        print(f"Filter: {len(sample_authors)} author(s), "
              f"{sum(len(w) for w in sample_works.values())} work(s) from {csv_path.name}")
    else:
        print(f"No CSV filter (mode={mode}): processing every discovered Latin author")
        if mode == "extended":
            print("  (mode=extended is currently equivalent to full)")

    # Fresh output DB
    if output_db.exists():
        output_db.unlink()
    conn = sqlite3.connect(str(output_db))
    conn.execute("PRAGMA foreign_keys = OFF")  # matches monolith behaviour
    cur = conn.cursor()
    create_schema(conn)
    print("✓ Schema created")

    # Discover authors
    all_latin = discover_latin_authors(latin_dir)
    print(f"\nDiscovered {len(all_latin)} Latin authors under {latin_dir}")

    if sample_authors is not None:
        authors_to_process = {
            aid: name for aid, name in all_latin.items() if name in sample_authors
        }
        print(f"Filtered to {len(authors_to_process)} matching authors")
    else:
        authors_to_process = all_latin

    # Process each author via the monolith's function. Keeps behaviour
    # identical to the current Latin build path.
    print("\n=== PROCESSING LATIN AUTHORS ===")
    failed = []
    for idx, (aid, name) in enumerate(sorted(authors_to_process.items()), 1):
        apath = latin_dir / aid
        if not apath.exists():
            print(f"  [{idx}/{len(authors_to_process)}] MISSING: {name} ({aid})")
            failed.append((aid, name, "directory missing"))
            continue
        print(f"  [{idx}/{len(authors_to_process)}] {name} ({aid})")
        try:
            process_perseus_author(
                apath, "latin", cur,
                sample_works=sample_works if sample_authors is not None else None,
            )
            if idx % 5 == 0:
                conn.commit()
        except SystemExit:
            raise
        except Exception as e:
            print(f"    ERROR: {e}")
            failed.append((aid, name, str(e)))

    conn.commit()

    if failed:
        print(f"\n!! {len(failed)} author(s) failed:")
        for aid, name, err in failed:
            print(f"   {aid}: {name} — {err}")

    # Dictionary: Whitaker's. Matches the monolith's original behaviour —
    # the pre-cutover sample build deliberately omitted Whitaker's to keep the
    # sample APK small. Full and extended include the full dictionary.
    if mode in ("full", "extended"):
        print("\n=== LOADING WHITAKER'S LATIN DICTIONARY ===")
        load_whitakers_latin(cur, include_full_morphology=True)
        conn.commit()
    else:
        print(f"\n=== SKIPPING WHITAKER'S (mode={mode} matches monolith sample) ===")

    # Prefix assimilation rules
    print("\n=== LOADING LATIN PREFIX ASSIMILATION RULES ===")
    load_latin_prefix_assimilation_rules(cur)
    conn.commit()

    # Import interlinear translations — adds translation_segments from
    # latin/interlinear_output/phi*.perseus-eng99.xml. This is a separate pass
    # in the monolith (import_interlinear_translations) run after the main
    # text build. Must run before translation_lookup so the lookup includes
    # interlinear-derived segments.
    #
    # Sample-mode parity: the pre-cutover monolith's sample build imported
    # interlinear translations for only 4 hard-coded works — Iliad, Odyssey,
    # Epigrams (Greek), and Aeneid (Latin). To keep sample DB content
    # bit-for-bit identical, we restrict the Latin-module sample build to
    # Aeneid only. Full mode imports every Latin work that has an XML.
    print("\n=== IMPORTING INTERLINEAR TRANSLATIONS ===")
    interlinear_dir = SCRIPT_DIR / "interlinear_output"
    if interlinear_dir.exists():
        latin_work_ids = [r[0] for r in cur.execute("SELECT id FROM works").fetchall()]
        if mode == "sample":
            sample_interlinear_allowlist = {"phi0690.phi003"}  # Aeneid
            candidate_ids = [w for w in latin_work_ids if w in sample_interlinear_allowlist]
        else:
            candidate_ids = latin_work_ids
        available = [
            wid for wid in candidate_ids
            if (interlinear_dir / f"{wid}.perseus-eng99.xml").exists()
        ]
        print(f"  Importing {len(available)} interlinear XML(s) "
              f"(mode={mode}, from {len(candidate_ids)} candidate / {len(latin_work_ids)} total)")
        if mode in ("full", "extended") and len(available) < 50:
            sys.exit(f"ERROR: {mode} mode has only {len(available)} Latin interlinear XMLs "
                     f"(expected ~200+). Run Latin interlinear generation first (BUILD.md Step 5).")
        if available:
            conn.commit()
            conn.close()
            import_interlinear_translations(
                str(output_db), work_ids=available,
                interlinear_dir=interlinear_dir, mode="extended",
            )
            # Re-open for subsequent steps.
            conn = sqlite3.connect(str(output_db))
            cur = conn.cursor()
    else:
        print(f"  ! interlinear_output dir missing: {interlinear_dir}")

    # Update has_translations flag for authors whose translation_segments
    # include non-interlinear translator entries (matches monolith logic).
    print("\n=== UPDATING has_translations FLAG ===")
    cur.execute("""
        UPDATE authors
        SET has_translations = 1
        WHERE id IN (
            SELECT DISTINCT a.id
            FROM authors a
            JOIN works w ON a.id = w.author_id
            JOIN books b ON w.id = b.work_id
            JOIN translation_segments ts ON b.id = ts.book_id
            WHERE ts.translation_text IS NOT NULL
              AND LENGTH(TRIM(ts.translation_text)) > 10
              AND (ts.translator IS NULL OR ts.translator NOT LIKE '%Interlinear%')
        )
    """)
    updated = cur.execute("SELECT COUNT(*) FROM authors WHERE has_translations=1").fetchone()[0]
    conn.commit()
    print(f"  {updated} authors now flagged has_translations=1")

    # Translation lookup table (Latin-only books)
    print("\n=== CREATING TRANSLATION_LOOKUP ===")
    create_translation_lookup_table(conn)
    conn.commit()

    # Write a Latin-only XML pattern inventory. process_perseus_author registers
    # each work's XML structural pattern during processing, populating the
    # monolith's XML_PATTERNS_BY_WORK global. Since the monolith no longer
    # builds Latin after the cutover, this file is the canonical record of
    # Latin XML patterns per work.
    patterns_out = SCRIPT_DIR / "XML_PATTERNS_BY_WORK_LATIN.txt"
    print(f"\n=== WRITING LATIN XML PATTERNS FILE ===\n  {patterns_out}")
    write_xml_patterns_file(output_path=patterns_out)

    # Summary
    summary = {
        "authors":              cur.execute("SELECT COUNT(*) FROM authors").fetchone()[0],
        "works":                cur.execute("SELECT COUNT(*) FROM works").fetchone()[0],
        "books":                cur.execute("SELECT COUNT(*) FROM books").fetchone()[0],
        "text_lines":           cur.execute("SELECT COUNT(*) FROM text_lines").fetchone()[0],
        "words":                cur.execute("SELECT COUNT(*) FROM words").fetchone()[0],
        "translation_segments": cur.execute("SELECT COUNT(*) FROM translation_segments").fetchone()[0],
        "translation_lookup":   cur.execute("SELECT COUNT(*) FROM translation_lookup").fetchone()[0],
        "dictionary_entries":   cur.execute("SELECT COUNT(*) FROM dictionary_entries").fetchone()[0],
        "lemma_map":            cur.execute("SELECT COUNT(*) FROM lemma_map").fetchone()[0],
        "prefix_assimilation":  cur.execute("SELECT COUNT(*) FROM prefix_assimilation_rules").fetchone()[0],
        "milestone_ranges":     cur.execute("SELECT COUNT(*) FROM milestone_line_ranges").fetchone()[0],
    }

    conn.close()

    elapsed = (time.time() - t0) / 60
    print(f"\n=== BUILD SUMMARY (mode={mode}, {elapsed:.1f} min) ===")
    for k, v in summary.items():
        print(f"  {k:24s} {v:>12,}")

    # Compress
    zip_path = output_db.with_suffix(".db.zip")
    print(f"\nCompressing to {zip_path}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(output_db, arcname=output_db.name)
    db_mb = output_db.stat().st_size / (1024 * 1024)
    zip_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"  {db_mb:.1f}MB → {zip_mb:.1f}MB ({100 * zip_mb / db_mb:.1f}%)")

    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("mode", choices=["sample", "full", "extended"], nargs="?", default="full")
    ap.add_argument("--csv", type=Path, help="custom author CSV (overrides mode default)")
    ap.add_argument("--output", type=Path, default=None,
                    help="output DB path (default: latin/latin_texts_<mode>.db)")
    args = ap.parse_args()
    if args.output is None:
        args.output = SCRIPT_DIR / f"latin_texts_{args.mode}.db"

    # Readers-writers build mutex. Latin can run alongside other modules
    # (e.g. Greek) but not alongside assembly, and not alongside another
    # Latin build in a different mode.
    from monolith_fn import acquire_module_lock, release_locks  # noqa: E402
    if not acquire_module_lock("latin"):
        print("ERROR: Could not acquire Latin build lock; see above for "
              "holder PID. Aborting.", file=sys.stderr)
        sys.exit(1)
    try:
        build(args.mode, args.output, args.csv)
    finally:
        release_locks()


if __name__ == "__main__":
    main()
