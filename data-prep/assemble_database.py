#!/usr/bin/env python3
"""assemble_database.py — Phase 3 assembly script.

Given pre-built per-language module DBs (greek/greek_texts.db,
latin/latin_texts.db, and extended-mode peers), create an empty DB with
the canonical schema, merge all language DBs into it, run the remaining
post-merge passes (OGA lemma enrichment, lexicon imports, quality report,
build metadata), compress to a ZIP, and copy to the APK assets.

This script does NO author processing — that is the module's job. It's
assembly-only, and will replace create_perseus_database.py's orchestration
role in Phase 4.

Prerequisites (build in advance):
  - greek/greek_texts.db  (via greek/run_build.sh <mode>)
  - latin/latin_texts.db  (via latin/run_build.sh <mode>)
  - extended mode also needs: arabic, hebrewOT, persian, sanskrit,
    cuneiform (sumerian+akkadian), dante, syriac, coptic, pali, norse,
    chinese, old_english module DBs.

Usage:
  python3 data-prep/assemble_database.py [sample|full|extended] [--skip-oga]
"""

import argparse
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

# Shared canonical schema.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from shared.database_schema import create_schema, diff_against_canonical  # noqa: E402

# Build utilities live in the Greek module's vendored monolith_fn.py. Assembly
# merges greek + latin + others, so depending on the Greek module is expected
# (the language modules are leaves in the dependency graph; assembly is the
# root that pulls them all together).
_GREEK_BUILD_MODULES = REPO_ROOT / "greek" / "build_modules"
if str(_GREEK_BUILD_MODULES) not in sys.path:
    sys.path.insert(0, str(_GREEK_BUILD_MODULES))
from monolith_fn import (  # noqa: E402
    acquire_lock,
    release_lock,
    generate_quality_report_final,
    insert_oga_lemmas,
    import_lexicons_for_languages,
    compress_and_copy_database,
    create_translation_lookup_table,
)


# ---------------------------------------------------------------------------
# Merge rules. Greek + Latin are merged for every mode. Other language DBs
# are merged only for full/extended per the monolith's historical behavior.
# Keep Greek first — it provides most of dictionary_entries/lemma_map, and
# lexicon imports later key off language names.
# ---------------------------------------------------------------------------

_GREEK_LATIN = [
    ("greek/greek_texts.db", "Greek"),
    ("latin/latin_texts.db", "Latin"),
]

MERGE_RULES = {
    "sample": _GREEK_LATIN,
    "full": _GREEK_LATIN + [
        ("cuneiform/sumerian_texts.db", "Sumerian"),
        ("cuneiform/akkadian_texts.db", "Akkadian"),
        ("dante/dante_texts.db", "italian"),
        ("old_english/old_english_texts.db", "old_english"),
    ],
    "extended": _GREEK_LATIN + [
        ("arabic/arabic_texts.db", "Arabic"),
        ("hebrewOT/hebrew_texts.db", "Hebrew"),
        ("persian/persian_texts.db", "Persian"),
        ("sanskrit/sanskrit_texts.db", "Sanskrit"),
        ("cuneiform/sumerian_texts.db", "Sumerian"),
        ("cuneiform/akkadian_texts.db", "Akkadian"),
        ("dante/dante_texts.db", "italian"),
        ("syriac/syriac_texts.db", "syriac"),
        ("coptic/coptic_texts.db", "coptic"),
        ("pali/pali_texts.db", "pali"),
        ("norse/norse_texts.db", "norse"),
        ("chinese/chinese_texts.db", "chinese"),
        ("old_english/old_english_texts.db", "old_english"),
    ],
}

LEXICON_PATHS = {
    "Arabic": "../arabic/arabic_lexicon.zip",
    "Hebrew": "../hebrewOT/hebrew_lexicon.zip",
    "Sanskrit": "../sanskrit/dcs_sanskrit_lexicon.zip",
    "Sumerian": "../cuneiform/sumerian_lexicon.zip",
    "Akkadian": "../cuneiform/akkadian_lexicon.zip",
    # Greek/Latin lexicons ship inside their own module DBs → no separate zip.
    # Persian: no lexicon available.
}

MODE_TO_DB_NAME = {
    "sample": "perseus_texts_sample.db",
    "full": "perseus_texts_full.db",
    "extended": "perseus_texts_extended.db",
    "ios": "perseus_texts_ios.db",
}

# iOS is a curated-sample assembly that merges only Greek + Latin
# (no other language modules) and lands the ZIP in ios/ClassicsViewer/
# Resources/ via compress_and_copy_database's output_name='ios' branch.
# Uses iOS-specific module DBs (see greek/run_build.sh ios and the latin
# --csv / --output flags) so it doesn't stomp on the sample/full/extended
# canonical module DBs.
MERGE_RULES["ios"] = [
    ("greek/greek_texts_ios.db", "Greek"),
    ("latin/latin_texts_ios.db", "Latin"),
]


def _checkpoint_wal(db_path: Path) -> None:
    """Flush the WAL journal into the main DB file.

    Per CLAUDE.md, compressing a DB with an un-flushed WAL can produce a
    corrupted ZIP. The monolith called this between every pipeline stage;
    assembly has to as well.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()


def _merge_one(source_db: str, description: str, target: str) -> None:
    """Shell out to merge_database.py for one module DB. Runs from data-prep/.

    Per CLAUDE.md "no silent failures": if the module DB is missing, abort
    the build — merging a subset of the expected modules would ship a DB
    with silently-absent content. The caller must build every module DB
    listed in MERGE_RULES[mode] before invoking assembly.
    """
    source_path = os.path.join("..", source_db)
    if not os.path.exists(source_path):
        raise FileNotFoundError(
            f"CRITICAL: required module database missing: {source_db}\n"
            f"  Expected at: {os.path.abspath(source_path)}\n"
            f"  Language:    {description}\n"
            f"  Fix: build the missing module before running assembly.\n"
            f"       See BUILD.md Step 6 for the per-module build commands."
        )

    print(f"\nMerging {description}...")
    print(f"  Source: {source_path}")
    print(f"  Target: {target}")

    result = subprocess.run(
        ["python3", "../merge_database.py", source_path, target],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"❌ Error merging {description}:")
        print(result.stderr)
        raise RuntimeError(f"Failed to merge {source_db}")

    print(f"✓ Successfully merged {description}")
    for line in result.stdout.strip().split("\n")[-5:]:
        if line.strip():
            print(f"  {line}")
    return description


def assemble(mode: str, skip_oga: bool = False) -> None:
    """Build perseus_texts_{mode}.db by merging module DBs + post-passes."""
    if mode not in MODE_TO_DB_NAME:
        raise ValueError(f"unknown mode: {mode!r}")

    start_time = time.time()
    db_name = MODE_TO_DB_NAME[mode]
    db_path = SCRIPT_DIR / db_name

    os.chdir(SCRIPT_DIR)  # merge_database.py and lexicon paths are relative.

    print(f"{'=' * 60}")
    print(f"ASSEMBLING {db_name} ({mode} mode)")
    print(f"{'=' * 60}\n")

    # Upfront OGA check — fail immediately, not 20 minutes into the build.
    if not skip_oga:
        oga_corpus = SCRIPT_DIR.parent / "data-sources" / "opera_graeca_adnotata_v0.2.0" / "workspace" / "oga.zip"
        if not oga_corpus.exists():
            print(f"ERROR: OGA corpus not found at {oga_corpus}")
            print("Download and extract it first (see BUILD.md Step 2):")
            print("  cd data-sources")
            print("  curl -L -O https://zenodo.org/records/14206061/files/opera_graeca_adnotata_v0.2.0.zip")
            print("  ditto -x -k opera_graeca_adnotata_v0.2.0.zip .")
            print("\nOr pass --skip-oga for dev-only builds (not for release).")
            raise FileNotFoundError(f"Required OGA corpus not found at {oga_corpus}")
        print(f"OGA corpus: {oga_corpus} ✓")

    if db_path.exists():
        print(f"Removing existing {db_path}")
        db_path.unlink()

    # 1. Empty DB with canonical schema.
    print("Creating empty DB with canonical schema...")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = -64000")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA mmap_size = 268435456")
    create_schema(conn)

    conn.close()
    # Build metadata row rides in from greek/greek_texts.db via merge; the
    # monolith inserts it in create_database(), so Greek module DBs always
    # carry one. No need to add another here.

    # 3. Merge per-mode module DBs.
    print(f"\n{'=' * 60}")
    print(f"MERGING MODULE DATABASES ({mode} mode)")
    print(f"{'=' * 60}")
    merged_languages = []
    for source_db, description in MERGE_RULES[mode]:
        result = _merge_one(source_db, description, db_name)
        if result is not None:
            merged_languages.append(result)

    # Checkpoint WAL after merges — required per CLAUDE.md to avoid
    # corrupted ZIPs when compress runs before the journal flushes.
    _checkpoint_wal(db_path)

    # 4. OGA lemma enrichment (Greek). Skippable — requires 8.6GB corpus.
    if not skip_oga:
        insert_oga_lemmas(db_name)
        _checkpoint_wal(db_path)
    else:
        print("\nSkipping OGA lemma import (--skip-oga).")

    # 5. Lexicon imports for merged non-Greek/Latin modules.
    #    Greek/Latin lexicons ride inside their module DBs; only the others
    #    publish separate lexicon ZIPs.
    import_lexicons_for_languages(db_name, merged_languages, LEXICON_PATHS)
    _checkpoint_wal(db_path)

    # 6. Rebuild translation_lookup across the whole merged DB. Some module
    #    DBs ship their table sparsely populated or empty (pali, dante,
    #    arabic, most of sanskrit); merging copies whatever's there but
    #    won't synthesize missing lookups. The monolith used to hide this
    #    because import_interlinear_translations (called post-merge) ran
    #    create_translation_lookup_table at the end. We call it directly.
    print(f"\n{'=' * 60}")
    print("REGENERATING translation_lookup ACROSS MERGED DB")
    print(f"{'=' * 60}")
    conn = sqlite3.connect(db_path)
    create_translation_lookup_table(conn)
    conn.close()
    _checkpoint_wal(db_path)

    # 6. Schema drift check before compression.
    check_conn = sqlite3.connect(db_path)
    diffs = diff_against_canonical(check_conn)
    check_conn.close()
    if diffs:
        print("❌ Schema drift detected after assembly:")
        for d in diffs:
            print(f"  {d}")
        raise RuntimeError("Assembled DB does not match canonical schema")
    print("\n✓ Assembled DB matches canonical schema")

    # 7. Compress + copy to APK assets.
    #    iOS mode: pass output_name='ios' so compress_and_copy_database takes
    #    its iOS-only branch (writes perseus_texts_ios.db.zip, copies to
    #    ios/ClassicsViewer/Resources/, does NOT touch APK assets). Other
    #    modes use the default branch (APK debug/main + iOS OnDemand copies
    #    for extended).
    is_sample = (mode == "sample")
    if mode == "ios":
        compress_and_copy_database(db_name, is_sample=True, output_name="ios")
    else:
        compress_and_copy_database(db_name, is_sample=is_sample)

    # 8. Quality report.
    report_name = "ios" if mode == "ios" else None
    # iOS mode reports under mode='sample' since that's the underlying
    # build; a distinct report_name keeps the file separate on disk.
    effective_mode = "sample" if mode == "ios" else mode
    generate_quality_report_final(
        db_name, mode=effective_mode,
        build_start_time=start_time, report_name=report_name,
    )

    elapsed = (time.time() - start_time) / 60
    print(f"\n{'=' * 60}")
    print(f"ASSEMBLY COMPLETE ({mode} mode, {elapsed:.1f} min)")
    print(f"Output: {db_path}")
    print(f"{'=' * 60}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=list(MODE_TO_DB_NAME.keys()))
    ap.add_argument(
        "--skip-oga",
        action="store_true",
        help="Skip OGA lemma enrichment (sample mode's OGA pass takes ~5 min).",
    )
    args = ap.parse_args()

    # Concurrent-build mutex, carried over from the monolith's old __main__.
    # Aborts immediately if another build/assembly is running.
    if not acquire_lock():
        print("Could not acquire build lock; another instance is running. "
              "See above for PID. Aborting.", file=sys.stderr)
        sys.exit(1)
    try:
        assemble(args.mode, skip_oga=args.skip_oga)
    finally:
        release_lock()


if __name__ == "__main__":
    main()
