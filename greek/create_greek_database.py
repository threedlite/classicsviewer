#!/usr/bin/env python3
"""Greek module entry point — builds greek/greek_texts.db.

Runs the Greek-author processing pipeline (Perseus + First1K + PTA +
Wiktionary + GreekLemmatizer + interlinear), writes the result to
greek/greek_texts.db with canonical schema. Skips merge + compress +
APK-asset copy; those are the assembly script's responsibility
(data-prep/assemble_database.py).

Post-vendoring: all Greek processing code lives under greek/build_modules/;
no dependency on data-prep/create_perseus_database.py. The monolith has
been fully retired and moved here as greek/build_modules/monolith_fn.py.

Build modes:
    sample   — SAMPLE_AUTHORS.csv curated authors, Homer interlinear only
    full     — all Perseus Greek authors, every available Greek XML
    extended — Perseus + First1K + PTA, every available Greek XML
    ios      — curated iOS subset (IOS_SAMPLE_AUTHORS.csv), import
               interlinear for any work whose XML is available

Usage:
    ./run_build.sh [sample|full|extended|ios]
or
    venv/bin/python3 greek/create_greek_database.py [sample|full|extended|ios]
"""

import argparse
import os
import shutil
import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
BUILD_MODULES = SCRIPT_DIR / "build_modules"
DATA_DIR = SCRIPT_DIR / "data"


def _output_db_for(mode: str) -> Path:
    """Each mode gets its own output file so builds don't clobber each other."""
    return SCRIPT_DIR / f"greek_texts_{mode}.db"

# Make greek/build_modules importable so `monolith_fn` resolves.
if str(BUILD_MODULES) not in sys.path:
    sys.path.insert(0, str(BUILD_MODULES))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _install_noop_overrides(monolith):
    """Replace monolith_fn functions that do assembly-level work with no-ops.

    The Greek module only produces a single-language DB. Merging external
    language DBs and compressing/deploying to APK assets are the assembly
    script's responsibility.
    """
    def _skip_merge(db_filename, mode="sample"):
        print(f"[greek] Skipping merge_external_databases({db_filename!r}, mode={mode!r})")

    def _skip_compress(db_filename, is_sample=False, suffix="", output_name=None):
        print(f"[greek] Skipping compress_and_copy_database({db_filename!r})")

    monolith.merge_external_databases = _skip_merge
    monolith.compress_and_copy_database = _skip_compress


def _select_work_ids(mode, intermediate_db_path, interlinear_dir):
    """Return the list of Greek work_ids whose interlinear XML should be
    imported for this build mode. Mirrors the monolith's per-mode logic."""
    if mode == "sample":
        # Historic curation: Homer triple only. Aeneid is Latin (handled by
        # latin module) so we do not list it here.
        return [
            "tlg0012.tlg001",  # Homer - Iliad
            "tlg0012.tlg002",  # Homer - Odyssey
            "tlg0012.tlg003",  # Homer - Epigrams
        ]

    if mode == "ios":
        # Old monolith: scan every work in the iOS DB, include it if an XML
        # exists (with or without _OGL suffix). This maximises interlinear
        # coverage on the smaller iOS corpus.
        conn = sqlite3.connect(intermediate_db_path)
        try:
            all_work_ids = [row[0] for row in conn.execute("SELECT id FROM works")]
        finally:
            conn.close()
        work_ids = []
        for work_id in all_work_ids:
            xml = interlinear_dir / f"{work_id}.perseus-eng99.xml"
            xml_ogl = interlinear_dir / f"{work_id}_OGL.perseus-eng99.xml"
            if xml.exists() or xml_ogl.exists():
                work_ids.append(work_id)
        print(f"[greek] iOS mode: {len(work_ids)}/{len(all_work_ids)} "
              "works have interlinear XML available")
        return work_ids

    # full / extended: every Greek XML that exists. Latin phi* files are
    # owned by latin/ module and imported into latin_texts.db.
    return sorted(
        xml.stem.replace(".perseus-eng99", "")
        for xml in interlinear_dir.glob("*.perseus-eng99.xml")
        if not xml.name.startswith("phi")
    )


def main():
    parser = argparse.ArgumentParser(description="Build Greek-only database")
    parser.add_argument(
        "mode",
        nargs="?",
        default="sample",
        choices=["sample", "full", "extended", "ios"],
        help="Build mode (default: sample)",
    )
    parser.add_argument(
        "custom_csv",
        nargs="?",
        default=None,
        help="Optional custom CSV path (overrides the mode's default CSV)",
    )
    args = parser.parse_args()

    # monolith_fn hard-codes many Path(__file__)-based paths and uses a few
    # `../relative` ones that historically resolved against data-prep/ CWD.
    # Since all Greek-owned state has been vendored into greek/build_modules/,
    # the Path(__file__)-based lookups now resolve correctly from there. We
    # still cd into greek/build_modules/ so any stale relative writes land
    # alongside the intermediate DB rather than polluting the repo root.
    original_cwd = os.getcwd()
    os.chdir(BUILD_MODULES)
    try:
        import monolith_fn  # noqa: E402

        # Readers-writers build mutex. Greek can run alongside other
        # modules (e.g. Latin) but not alongside assembly, and not
        # alongside another Greek build in a different mode.
        if not monolith_fn.acquire_module_lock("greek"):
            print("[greek] Could not acquire build lock; see above for "
                  "holder PID. Aborting.", file=sys.stderr)
            sys.exit(1)

        _install_noop_overrides(monolith_fn)

        # Resolve CSV filter. iOS has a dedicated curated CSV; sample uses
        # SAMPLE_AUTHORS.csv by default; full/extended ignore the CSV.
        if args.custom_csv is not None:
            custom_csv_path = str(Path(args.custom_csv).resolve())
        elif args.mode == "ios":
            custom_csv_path = str(DATA_DIR / "IOS_SAMPLE_AUTHORS.csv")
        elif args.mode == "sample":
            custom_csv_path = str(DATA_DIR / "SAMPLE_AUTHORS.csv")
        else:
            custom_csv_path = None

        # iOS is a curated sample at the monolith level — share the sample
        # build code path, just with a different CSV. The "ios" mode name
        # also signals that downstream assembly should use output_name='ios'.
        underlying_mode = "sample" if args.mode == "ios" else args.mode

        # Intermediate DB lands at greek/build_modules/perseus_texts_<name>.db
        # (where monolith_fn.create_database writes it). We rename at the end.
        intermediate_name = f"greek_build_{args.mode}"
        print(f"[greek] Building Greek-only DB, mode={args.mode} "
              f"(underlying={underlying_mode})")
        monolith_fn.create_database(
            mode=underlying_mode,
            custom_csv_path=custom_csv_path,
            output_name=intermediate_name,
        )

        src_name = f"perseus_texts_{intermediate_name}.db"
        src = BUILD_MODULES / src_name
        if not src.exists():
            print(f"[greek] ERROR: expected {src} after build")
            sys.exit(1)

        interlinear_dir = SCRIPT_DIR / "interlinear_output"
        work_ids = _select_work_ids(args.mode, src, interlinear_dir)

        print(f"[greek] Importing interlinear for {len(work_ids)} Greek works")
        if args.mode == "extended" and len(work_ids) < 100:
            print(f"[greek] ERROR: Extended mode has only {len(work_ids)} interlinear XMLs "
                  f"(expected ~1,900+). Run Greek interlinear generation first (BUILD.md Step 5).")
            sys.exit(1)
        monolith_fn.import_interlinear_translations(
            src_name,
            work_ids=work_ids,
            interlinear_dir=interlinear_dir,
            mode="extended" if args.mode == "extended" else "full",
        )

        # Dump the XML-pattern diagnostic file. The old monolith did this at
        # the tail of its __main__; after the split, it's the greek module's
        # job since all Greek XML parsing runs through here.
        monolith_fn.write_xml_patterns_file()

        # Checkpoint WAL so the file is self-contained before the move.
        chk = sqlite3.connect(src)
        chk.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        chk.close()

        output_db = _output_db_for(args.mode)
        if output_db.exists():
            output_db.unlink()
        shutil.move(str(src), str(output_db))
        size_mb = output_db.stat().st_size / (1024 * 1024)
        print(f"[greek] Wrote {output_db} ({size_mb:.1f} MB)")

    finally:
        os.chdir(original_cwd)
        # release_locks is already wired to atexit inside shared.build_lock,
        # but call it explicitly here too so anything waiting on the lock
        # can proceed even if Python exits via sys.exit or uncaught exception.
        try:
            import monolith_fn as _m  # type: ignore
            _m.release_locks()
        except Exception:
            pass


if __name__ == "__main__":
    main()
