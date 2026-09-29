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
from shared.venv_check import assert_libs  # noqa: E402
assert_libs("assemble")
from shared.database_schema import (  # noqa: E402
    create_schema, diff_against_canonical, TABLE_DDL, INDEX_DDL,
)
from shared import pack_layout  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402

# Build utilities live in the Greek module's vendored monolith_fn.py. Assembly
# merges greek + latin + others, so depending on the Greek module is expected
# (the language modules are leaves in the dependency graph; assembly is the
# root that pulls them all together).
_GREEK_BUILD_MODULES = REPO_ROOT / "greek" / "build_modules"
if str(_GREEK_BUILD_MODULES) not in sys.path:
    sys.path.insert(0, str(_GREEK_BUILD_MODULES))
from monolith_fn import (  # noqa: E402
    acquire_assembly_lock,
    release_locks,
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

def _greek_latin(mode: str):
    """Return Greek+Latin DB paths for a given mode.
    Each mode builds to a separate file so they don't clobber each other."""
    return [
        (f"greek/greek_texts_{mode}.db", "Greek"),
        (f"latin/latin_texts_{mode}.db", "Latin"),
    ]

_OTHER_FULL = [
    ("cuneiform/sumerian_texts.db", "Sumerian"),
    ("cuneiform/akkadian_texts.db", "Akkadian"),
    ("dante/dante_texts.db", "italian"),
    ("old_english/old_english_texts.db", "old_english"),
]

_OTHER_EXTENDED = _OTHER_FULL + [
    ("arabic/arabic_texts.db", "Arabic"),
    ("hebrewOT/hebrew_texts.db", "Hebrew"),
    ("persian/persian_texts.db", "Persian"),
    ("sanskrit/sanskrit_texts.db", "Sanskrit"),
    ("syriac/syriac_texts.db", "syriac"),
    ("coptic/coptic_texts.db", "coptic"),
    ("pali/pali_texts.db", "pali"),
    ("norse/norse_texts.db", "norse"),
    ("chinese/chinese_texts.db", "chinese"),
]

MERGE_RULES = {
    "sample": _greek_latin("sample"),
    "full": _greek_latin("full") + _OTHER_FULL,
    "extended": _greek_latin("extended") + _OTHER_EXTENDED,
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
MERGE_RULES["ios"] = _greek_latin("ios")


def _checkpoint_wal(db_path: Path) -> None:
    """Flush the WAL journal into the main DB file.

    Per CLAUDE.md, compressing a DB with an un-flushed WAL can produce a
    corrupted ZIP. The monolith called this between every pipeline stage;
    assembly has to as well.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()


def _vacuum(db_path: Path) -> None:
    """Rewrite the file with every page packed. Done in rollback-journal
    mode so the copy does not go through a WAL the size of the database,
    then the file is put back into WAL mode, which is how the shipped
    databases have always been written."""
    print("  VACUUM...")
    t0 = time.time()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode = DELETE")
        conn.execute("VACUUM")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()
    print(f"  VACUUM done ({time.time() - t0:.0f}s, {db_path.stat().st_size / 1e9:.2f} GB)")


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

    # Use sys.executable to ensure the subprocess inherits the same Python
    # interpreter (the project venv, per BUILD.md Step 4). Bare "python3" here
    # would silently fall back to PATH lookup, bypassing venv pinning.
    result = subprocess.run(
        [sys.executable, "../merge_database.py", source_path, target],
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

    if mode == "full":
        # Decided 2026-09-27: the full DB is a filter over the assembled
        # extended DB of the same release, ids preserved. It is never
        # assembled from its own module builds any more.
        _assemble_full_by_filter(db_name, db_path, start_time)
        return

    recorder = _LexiconRangeRecorder(db_path) if mode == "extended" else None

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
        if recorder:
            recorder.begin(pack_layout.normalize_language(description))
        result = _merge_one(source_db, description, db_name)
        if recorder:
            recorder.end()
        if result is not None:
            merged_languages.append(result)

    # Checkpoint WAL after merges — required per CLAUDE.md to avoid
    # corrupted ZIPs when compress runs before the journal flushes.
    _checkpoint_wal(db_path)

    # 4. OGA lemma enrichment (Greek). Skippable — requires 8.6GB corpus.
    if not skip_oga:
        if recorder:
            recorder.begin("greek")
        insert_oga_lemmas(db_name)
        if recorder:
            recorder.end()
        _checkpoint_wal(db_path)
    else:
        print("\nSkipping OGA lemma import (--skip-oga).")

    # 5. Lexicon imports for merged non-Greek/Latin modules.
    #    Greek/Latin lexicons ride inside their module DBs; only the others
    #    publish separate lexicon ZIPs. One call per language so the id
    #    range each language's rows occupy can be recorded (extended mode).
    for language in merged_languages:
        if language not in LEXICON_PATHS:
            continue
        if recorder:
            recorder.begin(pack_layout.normalize_language(language))
        import_lexicons_for_languages(db_name, [language], LEXICON_PATHS)
        if recorder:
            recorder.end()
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

    # 6b. Stamp THIS assembly's build time over any module's inherited row.
    _stamp_build_time(db_path, mode)
    _checkpoint_wal(db_path)

    # 6c. Extended only: the lexicon id ranges the full filter and the
    #     delta cutter consume, plus the two hard checks that make the
    #     id-preserving design safe (proposal sections 6 and 9).
    if recorder:
        ranges_path = _lexicon_ranges_path(db_path)
        recorder.write(ranges_path)
        _assert_lexicon_ranges(db_path, recorder.ranges)
        _assert_ids_below_limit(db_path)

    # 6d. Compact before compression. Every stage above inserts into tables
    #     and indexes that already hold data, which leaves pages partly
    #     filled; VACUUM rewrites them packed. Rows and ids are untouched.
    #     Measured on the full DB 2026-09-27: 3 percent fewer pages, 11
    #     percent smaller zip.
    _vacuum(db_path)

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


def _stamp_build_time(db_path: str, mode: str) -> None:
    """Record when THIS assembly ran, replacing any row inherited from a module.

    `build_time` is written by each module build, so the assembled DB simply
    kept whichever module happened to supply it — in practice Greek's. A
    database assembled on 9 September reported "Build Time:
    2026-08-21T15:50:05", the date of the Greek module it merged, and the
    released extended DB reports 2026-05-21 for the same reason.

    That is the field anyone reaches for to ask which build a file is, so it
    has to describe the assembly, not one of its inputs. Written after the
    schema check and before compression, so the zip carries it.
    """
    from datetime import datetime
    ts = datetime.now().isoformat()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DELETE FROM dictionary_entries "
                     "WHERE language = 'system' AND headword = 'build_time'")
        conn.execute(
            "INSERT INTO dictionary_entries (headword, headword_normalized_ultra,"
            " language, entry_xml, entry_html, entry_plain, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ('build_time', None, 'system',
             f'<entry><timestamp>{ts}</timestamp><mode>{mode}</mode></entry>',
             f'Build Time: {ts}<br>Mode: {mode}',
             f'Build Time: {ts}\nMode: {mode}',
             'database_build_metadata'))
        conn.commit()
    finally:
        conn.close()
    print(f"✓ Build time stamped: {ts} (mode: {mode})")


# ---------------------------------------------------------------------------
# Lexicon id ranges (extended mode). Proposal section 6.
#
# lemma_map has no language column. Every stage that inserts lexicon rows
# (each module merge, the OGA pass, each language's lexicon import) appends
# rows with AUTOINCREMENT ids, so the rows a stage wrote are exactly the ids
# in (max_before, max_after]. Recording that per stage attributes every
# lexicon row to a language with arithmetic only. The `source` column is the
# cross-check (pack_layout.SOURCE_LANGUAGE).
# ---------------------------------------------------------------------------

def _lexicon_ranges_path(db_path: Path) -> Path:
    return db_path.with_name(db_path.stem + ".lexicon_ranges.json")


class _LexiconRangeRecorder:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.ranges: list = []
        self._stage = None

    def _max_ids(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        try:
            return {
                t: conn.execute(f"SELECT COALESCE(MAX(id), 0) FROM {t}").fetchone()[0]
                for t in pack_layout.LEXICON_TABLES
            }
        finally:
            conn.close()

    def begin(self, language: str) -> None:
        if self._stage is not None:
            raise RuntimeError("lexicon range stage already open")
        self._stage = (language, self._max_ids())

    def end(self) -> None:
        language, before = self._stage
        after = self._max_ids()
        conn = sqlite3.connect(self.db_path)
        try:
            for t in pack_layout.LEXICON_TABLES:
                lo, hi = before[t] + 1, after[t]
                if hi < lo:
                    continue
                rows = conn.execute(
                    f"SELECT COUNT(*) FROM {t} WHERE id BETWEEN ? AND ?", (lo, hi)
                ).fetchone()[0]
                if rows != hi - lo + 1:
                    raise RuntimeError(
                        f"lexicon range gap: {t} ids {lo}..{hi} hold {rows} rows "
                        f"for {language}; expected {hi - lo + 1}"
                    )
                self.ranges.append(
                    {"language": language, "table": t, "lo": lo, "hi": hi, "rows": rows}
                )
                print(f"  [ranges] {t}: {language} ids {lo:,}..{hi:,} ({rows:,} rows)")
        finally:
            conn.close()
        self._stage = None

    def write(self, path: Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"db": self.db_path.name, "ranges": self.ranges}, f, indent=1)
        print(f"✓ Lexicon ranges written: {path} ({len(self.ranges)} ranges)")


def _load_lexicon_ranges(path: Path) -> list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)["ranges"]


def _ranges_for(ranges: list, table: str, languages=None) -> list:
    return [
        r for r in ranges
        if r["table"] == table and (languages is None or r["language"] in languages)
    ]


def _between_sql(ranges: list, column: str = "id") -> str:
    """OR-joined BETWEEN predicate for a list of ranges; '0' if empty."""
    if not ranges:
        return "0"
    return "(" + " OR ".join(
        f"{column} BETWEEN {r['lo']} AND {r['hi']}" for r in ranges
    ) + ")"


def _assert_lexicon_ranges(db_path: Path, ranges: list) -> None:
    """Hard checks: every lexicon row is inside exactly one recorded range,
    and its language agrees with the range (by `language` column where the
    table has one, by registered `source` for lemma_map)."""
    conn = sqlite3.connect(db_path)
    errors = []
    try:
        for t in pack_layout.LEXICON_TABLES:
            trs = sorted(_ranges_for(ranges, t), key=lambda r: r["lo"])
            for a, b in zip(trs, trs[1:]):
                if b["lo"] <= a["hi"]:
                    errors.append(f"{t}: overlapping ranges {a} / {b}")
            total = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            covered = sum(
                conn.execute(
                    f"SELECT COUNT(*) FROM {t} WHERE id BETWEEN ? AND ?",
                    (r["lo"], r["hi"]),
                ).fetchone()[0]
                for r in trs
            )
            outside = total - covered
            if t == "dictionary_entries":
                system_rows = conn.execute(
                    f"SELECT COUNT(*) FROM {t} WHERE language = 'system' "
                    f"AND NOT {_between_sql(trs)}"
                ).fetchone()[0]
                if outside != system_rows:
                    errors.append(
                        f"{t}: {outside - system_rows} non-system rows outside every range"
                    )
            elif outside:
                errors.append(f"{t}: {outside} rows outside every range")

            for r in trs:
                if t == "lemma_map":
                    for source, n in conn.execute(
                        f"SELECT COALESCE(source, '<NULL>'), COUNT(*) FROM {t} "
                        f"WHERE id BETWEEN ? AND ? GROUP BY 1", (r["lo"], r["hi"])
                    ):
                        lang = pack_layout.SOURCE_LANGUAGE.get(source)
                        if lang is None:
                            errors.append(
                                f"lemma_map: source {source!r} ({n:,} rows in the "
                                f"{r['language']} range {r['lo']}..{r['hi']}) is not "
                                f"registered in shared/pack_layout.py"
                            )
                        elif lang != r["language"]:
                            errors.append(
                                f"lemma_map: source {source!r} is registered to {lang} "
                                f"but {n:,} rows sit in the {r['language']} range "
                                f"{r['lo']}..{r['hi']}"
                            )
                else:
                    for lang, n in conn.execute(
                        f"SELECT LOWER(language), COUNT(*) FROM {t} "
                        f"WHERE id BETWEEN ? AND ? GROUP BY 1", (r["lo"], r["hi"])
                    ):
                        if lang not in (r["language"], "system"):
                            errors.append(
                                f"{t}: {n:,} rows of language {lang!r} in the "
                                f"{r['language']} range {r['lo']}..{r['hi']}"
                            )
    finally:
        conn.close()
    if errors:
        print("❌ Lexicon range check failed:")
        for e in errors:
            print(f"  {e}")
        raise RuntimeError("lexicon id ranges do not attribute every row to a language")
    print("✓ Lexicon ranges attribute every row; sources agree with the registry")


def _assert_ids_below_limit(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        for t in pack_layout.AUTOINCREMENT_TABLES:
            mx = conn.execute(f"SELECT COALESCE(MAX(id), 0) FROM {t}").fetchone()[0]
            if mx >= pack_layout.MAX_ID_EXCLUSIVE:
                raise RuntimeError(
                    f"{t}: max id {mx:,} is at or above 2^31; three Room entity "
                    f"fields are Int and would truncate"
                )
            print(f"  [ids] {t}: max id {mx:,}")
    finally:
        conn.close()
    print("✓ All AUTOINCREMENT ids below 2^31")


# ---------------------------------------------------------------------------
# Full = filter(extended). Proposal section 9.
# ---------------------------------------------------------------------------

# translation_segments carries rows whose book_id has no books row: a
# translation split into parts the text does not have (e.g. the Verrines,
# one "Complete Text" book, translated as 002..005). The app cannot reach
# them, but today's full DB carries the ones for its works, and the filter
# reproduces today's full DB exactly, so they are kept by the work their
# book id names. Verified 2026-09-27: 934 such rows in the full scope, all
# present in the previous full DB; every orphan in the extended DB names
# an existing work.
_SEGMENT_SCOPE_SQL = (
    "(book_id IN (SELECT id FROM full_books) OR "
    "(book_id NOT IN (SELECT id FROM ext.books) AND EXISTS ("
    "SELECT 1 FROM full_works fw "
    "WHERE substr(book_id, 1, length(fw.id) + 1) = fw.id || '.')))"
)


def _table_columns(conn: sqlite3.Connection, schema: str, table: str) -> list:
    return [row[1] for row in conn.execute(f"PRAGMA {schema}.table_info({table})")]


def _read_build_time(conn: sqlite3.Connection, schema: str) -> str:
    row = conn.execute(
        f"SELECT entry_plain FROM {schema}.dictionary_entries "
        f"WHERE language = 'system' AND headword = 'build_time'"
    ).fetchone()
    if not row:
        raise RuntimeError(f"{schema}: no build_time row in dictionary_entries")
    import re
    m = re.match(r"Build Time: (\S+)", row[0] or "")
    if not m:
        raise RuntimeError(f"{schema}: unparseable build_time row: {row[0]!r}")
    return m.group(1)


def _assemble_full_by_filter(db_name: str, db_path: Path, start_time: float) -> None:
    """Cut perseus_texts_full.db out of perseus_texts_extended.db.

    Ids are preserved, so the full DB and the extended delta partition the
    extended DB's rows. Nothing is added, removed or altered; rows are
    copied. The only row that differs from the extended DB afterwards is
    the build_time marker, which keeps the extended timestamp (the release
    identity) and says mode=full.
    """
    ext_path = SCRIPT_DIR / MODE_TO_DB_NAME["extended"]
    ranges_path = _lexicon_ranges_path(ext_path)
    for p in (ext_path, ranges_path):
        if not p.exists():
            raise FileNotFoundError(
                f"CRITICAL: {p} is required to build the full DB.\n"
                f"  The full DB is a filter over the extended DB of the same "
                f"release; run `assemble_database.py extended` first."
            )
    ext_mtime = ext_path.stat().st_mtime
    for source_db, description in MERGE_RULES["extended"]:
        mp = SCRIPT_DIR.parent / source_db
        if mp.exists() and mp.stat().st_mtime > ext_mtime:
            raise RuntimeError(
                f"CRITICAL: {source_db} ({description}) is newer than "
                f"{ext_path.name}; re-run `assemble_database.py extended` first."
            )
    ranges = _load_lexicon_ranges(ranges_path)
    lex_langs = pack_layout.FULL_LEXICON_LANGUAGES
    lemma_pred = _between_sql(_ranges_for(ranges, "lemma_map", lex_langs))
    lang_list = ", ".join(f"'{l}'" for l in sorted(lex_langs))

    if db_path.exists():
        print(f"Removing existing {db_path}")
        db_path.unlink()
    for suffix in ("-wal", "-shm", "-journal"):
        p = Path(str(db_path) + suffix)
        if p.exists():
            p.unlink()

    print(f"Filtering {ext_path.name} -> {db_name}")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = OFF")
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("PRAGMA cache_size = -512000")
    conn.execute("PRAGMA temp_store = MEMORY")
    for ddl in TABLE_DDL:
        conn.execute(ddl)
    conn.execute("ATTACH DATABASE ? AS ext", (str(ext_path),))

    # The full work set, from the registry rule.
    where = pack_layout.full_works_where_sql("w", "a")
    conn.execute(
        "CREATE TEMP TABLE full_works AS SELECT w.id AS id FROM ext.works w "
        f"JOIN ext.authors a ON a.id = w.author_id WHERE {where}"
    )
    conn.execute("CREATE INDEX temp.ix_full_works ON full_works(id)")
    conn.execute(
        "CREATE TEMP TABLE full_books AS SELECT id FROM ext.books "
        "WHERE work_id IN (SELECT id FROM full_works)"
    )
    conn.execute("CREATE INDEX temp.ix_full_books ON full_books(id)")
    conn.execute(
        "CREATE TEMP TABLE full_authors AS SELECT DISTINCT author_id AS id FROM ext.works "
        "WHERE id IN (SELECT id FROM full_works)"
    )
    n_w, n_b, n_a = (
        conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("full_works", "full_books", "full_authors")
    )
    print(f"  full set: {n_a:,} authors, {n_w:,} works, {n_b:,} books")

    predicates = {
        "authors": "id IN (SELECT id FROM full_authors)",
        "works": "id IN (SELECT id FROM full_works)",
        "books": "work_id IN (SELECT id FROM full_works)",
        "text_lines": "book_id IN (SELECT id FROM full_books)",
        "translation_segments": _SEGMENT_SCOPE_SQL,
        "words": "book_id IN (SELECT id FROM full_books)",
        "translation_lookup": "book_id IN (SELECT id FROM full_books)",
        "milestone_line_ranges": "work_id IN (SELECT id FROM full_works)",
        "dictionary_entries": f"(LOWER(language) IN ({lang_list}) OR language = 'system')",
        "normalization_patterns": f"LOWER(language) IN ({lang_list})",
        "prefix_assimilation_rules": f"LOWER(language) IN ({lang_list})",
        "lemma_map": lemma_pred,
    }
    from shared.database_schema import _table_names
    tables = _table_names()
    missing = set(tables) ^ set(predicates)
    if missing:
        raise RuntimeError(f"filter predicates out of step with schema: {missing}")

    counts = {}
    for t in tables:  # FK-safe order from the canonical DDL
        cols = _table_columns(conn, "ext", t)
        if cols != _table_columns(conn, "main", t):
            raise RuntimeError(f"{t}: column mismatch between extended and canonical")
        col_sql = ", ".join(cols)
        t0 = time.time()
        conn.execute(
            f"INSERT INTO main.{t} ({col_sql}) SELECT {col_sql} FROM ext.{t} "
            f"WHERE {predicates[t]}"
        )
        counts[t] = conn.execute(f"SELECT COUNT(*) FROM main.{t}").fetchone()[0]
        print(f"  {t}: {counts[t]:,} rows ({time.time() - t0:.0f}s)")
    conn.commit()

    # Derived flag, recomputed with the module builds' own statement.
    conn.execute("UPDATE authors SET has_translations = 0")
    conn.execute(pack_layout.HAS_TRANSLATIONS_UPDATE_SQL)
    flagged = conn.execute(
        "SELECT COUNT(*) FROM authors WHERE has_translations = 1"
    ).fetchone()[0]
    print(f"  has_translations recomputed: {flagged:,} authors flagged")

    # AUTOINCREMENT counters as in extended (nothing on the device inserts).
    conn.execute("DELETE FROM main.sqlite_sequence")
    conn.execute(
        "INSERT INTO main.sqlite_sequence (name, seq) SELECT name, seq FROM ext.sqlite_sequence"
    )

    # Release identity: keep the extended timestamp and the row's id; only
    # the mode text changes. _stamp_build_time() must NOT run here.
    ts = _read_build_time(conn, "ext")
    conn.execute(
        "UPDATE main.dictionary_entries SET entry_xml = ?, entry_html = ?, entry_plain = ? "
        "WHERE language = 'system' AND headword = 'build_time'",
        (f'<entry><timestamp>{ts}</timestamp><mode>full</mode></entry>',
         f'Build Time: {ts}<br>Mode: full',
         f'Build Time: {ts}\nMode: full'),
    )
    conn.commit()
    print(f"  build_time kept from extended: {ts}")

    print("  creating indexes...")
    t0 = time.time()
    for ddl in INDEX_DDL:
        conn.execute(ddl)
    conn.commit()
    print(f"  indexes created ({time.time() - t0:.0f}s)")

    _verify_full_subset(conn, ranges, counts)

    conn.execute("DETACH DATABASE ext")
    conn.close()
    _vacuum(db_path)
    conn = sqlite3.connect(db_path)
    diffs = diff_against_canonical(conn)
    conn.close()
    if diffs:
        print("❌ Schema drift detected in filtered full DB:")
        for d in diffs:
            print(f"  {d}")
        raise RuntimeError("Filtered full DB does not match canonical schema")
    print("✓ Filtered full DB matches canonical schema")
    _assert_ids_below_limit(db_path)

    generate_quality_report_final(db_name, mode="full", build_start_time=start_time)
    compress_and_copy_database(db_name, is_sample=False)
    _write_full_sidecar(db_path, ts, counts)
    emit_extended_delta(db_path, ext_path, ranges, ts)

    elapsed = (time.time() - start_time) / 60
    print(f"\n{'=' * 60}")
    print(f"ASSEMBLY COMPLETE (full mode, filtered from extended, {elapsed:.1f} min)")
    print(f"Output: {db_path}")
    print(f"{'=' * 60}")


def _verify_full_subset(conn: sqlite3.Connection, ranges: list, counts: dict) -> None:
    """Hard check that main == ext restricted to the full scope, ids included.

    Two counts per table: (a) rows of main that have an identical row with
    the same primary key in ext, and (b) rows of ext inside the full scope.
    Both must equal the row count of main. Together they say every main
    row came from ext unchanged and nothing in scope was left behind.
    """
    from shared.database_schema import _table_names
    lex_langs = pack_layout.FULL_LEXICON_LANGUAGES
    lang_list = ", ".join(f"'{l}'" for l in sorted(lex_langs))
    lemma_pred = _between_sql(_ranges_for(ranges, "lemma_map", lex_langs), "id")
    scope = {
        "authors": "id IN (SELECT id FROM full_authors)",
        "works": "id IN (SELECT id FROM full_works)",
        "books": "work_id IN (SELECT id FROM full_works)",
        "text_lines": "book_id IN (SELECT id FROM full_books)",
        "translation_segments": _SEGMENT_SCOPE_SQL,
        "words": "book_id IN (SELECT id FROM full_books)",
        "translation_lookup": "book_id IN (SELECT id FROM full_books)",
        "milestone_line_ranges": "work_id IN (SELECT id FROM full_works)",
        "dictionary_entries": f"(LOWER(language) IN ({lang_list}) OR language = 'system')",
        "normalization_patterns": f"LOWER(language) IN ({lang_list})",
        "prefix_assimilation_rules": f"LOWER(language) IN ({lang_list})",
        "lemma_map": lemma_pred,
    }
    pk = {
        "translation_lookup": ["book_id", "line_number", "segment_id"],
        "milestone_line_ranges": ["work_id", "milestone"],
    }
    # Columns whose value is allowed to differ between main and ext.
    ignore = {"authors": {"has_translations"}}
    errors = []
    print("  verifying full == extended restricted to the full scope...")
    for t in _table_names():
        cols = _table_columns(conn, "main", t)
        keys = pk.get(t, ["id"])
        cmp_cols = [c for c in cols if c not in keys and c not in ignore.get(t, set())]
        join = " AND ".join(f"e.{k} = m.{k}" for k in keys)
        same = " AND ".join(f"m.{c} IS e.{c}" for c in cmp_cols) or "1"
        extra = ""
        if t == "dictionary_entries":
            extra = " AND m.language <> 'system'"  # build_time text differs by design
        t0 = time.time()
        n_main = counts[t]
        n_same = conn.execute(
            f"SELECT COUNT(*) FROM main.{t} m JOIN ext.{t} e ON {join} "
            f"WHERE {same}{extra}"
        ).fetchone()[0]
        n_scope = conn.execute(
            f"SELECT COUNT(*) FROM ext.{t} WHERE {scope[t]}"
        ).fetchone()[0]
        n_expect_same = n_main
        if t == "dictionary_entries":
            n_expect_same = n_main - conn.execute(
                "SELECT COUNT(*) FROM main.dictionary_entries WHERE language = 'system'"
            ).fetchone()[0]
        ok = (n_same == n_expect_same) and (n_scope == n_main)
        print(f"    {t}: main {n_main:,}, identical-in-ext {n_same:,}, "
              f"ext-in-scope {n_scope:,} ({time.time() - t0:.0f}s) {'OK' if ok else 'MISMATCH'}")
        if not ok:
            errors.append(t)
    if errors:
        raise RuntimeError(f"filtered full DB differs from extended in: {errors}")
    print("✓ Full DB is exactly the extended DB restricted to the full scope, ids included")


def _write_full_sidecar(db_path: Path, ts: str, counts: dict) -> None:
    """full.manifest.json beside the full pack zip: lets the app read the
    release identity without extracting 5 GB (proposal section 5)."""
    zip_path = SCRIPT_DIR.parent / "full_database_pack" / "src" / "main" / "assets" / "perseus_texts_full.db.zip"
    if not zip_path.exists():
        raise FileNotFoundError(f"expected the full pack zip at {zip_path}")
    h = hashlib.sha256()
    with open(zip_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    manifest = {
        "manifest_version": 1,
        "pack_id": "full_database_pack",
        "build_time": ts,
        "db_bytes": db_path.stat().st_size,
        "zip_bytes": zip_path.stat().st_size,
        "zip_sha256": h.hexdigest(),
        "rows": counts,
    }
    out = zip_path.with_name("full.manifest.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    print(f"✓ Sidecar written: {out}")


# ---------------------------------------------------------------------------
# Extended delta cutter (full mode, after the filter). Proposal sections
# 4, 5 and 9. Cuts everything in the extended DB that is not in the full DB
# into on-demand asset packs ("parts"), each a canonical-schema SQLite file
# with the extended DB's ids, sized under PART_SIZE_TARGET_BYTES, and proves
# on the desktop that full + parts == extended with the same SQL the app runs.
# ---------------------------------------------------------------------------

_PARTS_DIR = SCRIPT_DIR / "delta_parts"            # build output, never staged
_MERGE_SQL_PATH = REPO_ROOT / "shared" / "delta_merge.sql"
_PART_MODULE_FMT = "db_extended_part{n}_pack"


def _load_merge_statements() -> list:
    """The shared merge SQL, checked against the canonical schema.

    Every INSERT's column list must equal the table's columns in order, so a
    schema change that is not mirrored in the .sql fails the build here
    rather than misaligning columns on a phone."""
    import re
    text = _MERGE_SQL_PATH.read_text(encoding="utf-8")
    text = re.sub(r"--[^\n]*", "", text)
    stmts = [x.strip() for x in text.split(";") if x.strip()]
    conn = sqlite3.connect(":memory:")
    create_schema(conn)
    seen = []
    for st in stmts:
        m = re.match(
            r"INSERT(?: OR REPLACE)? INTO main\.(\w+) \(([^)]*)\)\s+SELECT (.+?) FROM part\.\1",
            st, re.S,
        )
        if not m:
            raise RuntimeError(f"delta_merge.sql: unparseable statement: {st[:80]!r}")
        t = m.group(1)
        cols = [c.strip() for c in m.group(2).split(",")]
        sel = [c.strip() for c in m.group(3).split(",")]
        schema = [r[1] for r in conn.execute(f"PRAGMA table_info({t})")]
        if not (cols == sel == schema):
            raise RuntimeError(
                f"delta_merge.sql: {t} columns {cols} do not match the canonical "
                f"schema {schema}; fix shared/delta_merge.sql"
            )
        seen.append(t)
    from shared.database_schema import _table_names
    if seen != _table_names():
        raise RuntimeError(
            f"delta_merge.sql: tables {seen} are not the canonical FK-safe order "
            f"{_table_names()}"
        )
    conn.close()
    return stmts


def _delta_units(ext: sqlite3.Connection, ranges: list) -> list:
    """The indivisible pieces of the delta, each a dict:
    name, corpora, languages, lexicon_languages, work_ids."""
    langs_in_db = {
        pack_layout.normalize_language(r[0])
        for r in ext.execute("SELECT DISTINCT language FROM authors")
    }
    unknown = langs_in_db - pack_layout.EXTENDED_LANGUAGES
    if unknown:
        raise RuntimeError(
            f"languages in the extended DB not registered in shared/pack_layout.py: "
            f"{sorted(unknown)}"
        )
    where_full = pack_layout.full_works_where_sql("w", "a")
    units = []
    for suffix, name in (("_OGL", "greek_first1k"), ("_PTA", "greek_pta")):
        ids = [r[0] for r in ext.execute(
            "SELECT w.id FROM works w JOIN authors a ON a.id = w.author_id "
            "WHERE a.language = 'greek' AND w.id LIKE ? ESCAPE '\\' ORDER BY w.id",
            (f"%\\{suffix}",),
        )]
        units.append({"name": name, "corpora": [name.split("_")[1]],
                      "languages": ["greek"], "lexicon_languages": [], "work_ids": ids})
    for lang in sorted(langs_in_db - pack_layout.FULL_TEXT_LANGUAGES - {"greek"}):
        ids = [r[0] for r in ext.execute(
            "SELECT w.id FROM works w JOIN authors a ON a.id = w.author_id "
            "WHERE LOWER(a.language) = ? ORDER BY w.id", (lang,),
        )]
        lex = [] if lang in pack_layout.FULL_LEXICON_LANGUAGES else [lang]
        units.append({"name": lang, "corpora": [lang], "languages": [lang],
                      "lexicon_languages": lex, "work_ids": ids})
    # Every work of the extended DB is in the full set or in exactly one unit.
    all_ext = {r[0] for r in ext.execute("SELECT id FROM works")}
    full = {r[0] for r in ext.execute(
        f"SELECT w.id FROM works w JOIN authors a ON a.id = w.author_id WHERE {where_full}")}
    covered = set(full)
    for u in units:
        dup = covered & set(u["work_ids"])
        if dup:
            raise RuntimeError(f"work ids in two places: {sorted(dup)[:5]} (unit {u['name']})")
        covered |= set(u["work_ids"])
    if covered != all_ext:
        raise RuntimeError(
            f"{len(all_ext - covered)} works in neither full nor any unit: "
            f"{sorted(all_ext - covered)[:5]}"
        )
    # Lexicon languages present in the DB but in no unit and not full's.
    lex_langs_db = {pack_layout.normalize_language(r[0]) for r in ext.execute(
        "SELECT DISTINCT language FROM dictionary_entries WHERE language <> 'system'")}
    lex_langs_db |= {r["language"] for r in ranges}
    uncovered = lex_langs_db - pack_layout.FULL_LEXICON_LANGUAGES - {
        l for u in units for l in u["lexicon_languages"]}
    if uncovered:
        raise RuntimeError(f"lexicon languages in no part and not full's: {sorted(uncovered)}")
    return [u for u in units if u["work_ids"] or u["lexicon_languages"]]


def _cut_slice(ext_path: Path, out_path: Path, work_ids: list, lexicon_languages: list,
               ranges: list, with_indexes: bool = True, vacuum: bool = True) -> dict:
    """Write a canonical-schema DB holding exactly the given works (with
    their authors, books, text tables, milestones and orphan segments) and
    the given lexicon languages, ids as in the extended DB. Returns row
    counts per table."""
    if out_path.exists():
        out_path.unlink()
    conn = sqlite3.connect(out_path)
    conn.execute("PRAGMA journal_mode = OFF")
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("PRAGMA cache_size = -512000")
    conn.execute("PRAGMA temp_store = MEMORY")
    for ddl in TABLE_DDL:
        conn.execute(ddl)
    conn.execute("ATTACH DATABASE ? AS ext", (str(ext_path),))
    conn.execute("CREATE TEMP TABLE sel_works (id TEXT PRIMARY KEY)")
    conn.executemany("INSERT INTO sel_works (id) VALUES (?)", [(w,) for w in work_ids])
    conn.execute("CREATE TEMP TABLE sel_books AS SELECT id FROM ext.books "
                 "WHERE work_id IN (SELECT id FROM sel_works)")
    conn.execute("CREATE INDEX temp.ix_sel_books ON sel_books(id)")
    langs = ", ".join(f"'{l}'" for l in sorted(lexicon_languages)) or "''"
    lemma_pred = _between_sql(_ranges_for(ranges, "lemma_map", set(lexicon_languages)))
    seg_pred = (
        "(book_id IN (SELECT id FROM sel_books) OR "
        "(book_id NOT IN (SELECT id FROM ext.books) AND EXISTS ("
        "SELECT 1 FROM sel_works sw WHERE substr(book_id, 1, length(sw.id) + 1) = sw.id || '.')))"
    )
    predicates = {
        "authors": "id IN (SELECT DISTINCT author_id FROM ext.works WHERE id IN (SELECT id FROM sel_works))",
        "works": "id IN (SELECT id FROM sel_works)",
        "books": "work_id IN (SELECT id FROM sel_works)",
        "text_lines": "book_id IN (SELECT id FROM sel_books)",
        "translation_segments": seg_pred,
        "words": "book_id IN (SELECT id FROM sel_books)",
        "translation_lookup": "book_id IN (SELECT id FROM sel_books)",
        "milestone_line_ranges": "work_id IN (SELECT id FROM sel_works)",
        "dictionary_entries": f"(LOWER(language) IN ({langs}) OR language = 'system')",
        "normalization_patterns": f"LOWER(language) IN ({langs})",
        "prefix_assimilation_rules": f"LOWER(language) IN ({langs})",
        "lemma_map": lemma_pred,
    }
    from shared.database_schema import _table_names
    counts = {}
    for t in _table_names():
        cols = _table_columns(conn, "ext", t)
        col_sql = ", ".join(cols)
        conn.execute(f"INSERT INTO main.{t} ({col_sql}) SELECT {col_sql} FROM ext.{t} WHERE {predicates[t]}")
        counts[t] = conn.execute(f"SELECT COUNT(*) FROM main.{t}").fetchone()[0]
    counts["orphan_segments"] = conn.execute(
        "SELECT COUNT(*) FROM main.translation_segments "
        "WHERE book_id NOT IN (SELECT id FROM main.books)"
    ).fetchone()[0]
    conn.execute("DELETE FROM main.sqlite_sequence")
    conn.execute("INSERT INTO main.sqlite_sequence (name, seq) SELECT name, seq FROM ext.sqlite_sequence")
    conn.commit()
    if with_indexes:
        for ddl in INDEX_DDL:
            conn.execute(ddl)
        conn.commit()
    conn.execute("DETACH DATABASE ext")
    conn.execute("PRAGMA journal_mode = DELETE")
    if vacuum:
        conn.execute("VACUUM")
    conn.close()
    return counts


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _zip_slice(db_path: Path, zip_path: Path, entry_name: str, manifest: dict = None,
               level: int = 9) -> int:
    import zipfile
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=level,
                         allowZip64=True) as zf:
        zf.write(db_path, entry_name)
        if manifest is not None:
            zf.writestr("manifest.json", json.dumps(manifest, indent=1))
    return zip_path.stat().st_size


def _author_text_bytes(ext: sqlite3.Connection, work_ids: list) -> dict:
    """Rough uncompressed text bytes per author over the given works, for
    splitting a unit that is over the size target."""
    ext.execute("CREATE TEMP TABLE IF NOT EXISTS split_works (id TEXT PRIMARY KEY)")
    ext.execute("DELETE FROM split_works")
    ext.executemany("INSERT INTO split_works (id) VALUES (?)", [(w,) for w in work_ids])
    rows = ext.execute(
        "SELECT w.author_id, "
        " (SELECT COALESCE(SUM(LENGTH(t.line_text) + COALESCE(LENGTH(t.line_xml), 0)), 0) "
        "  FROM text_lines t JOIN books b ON b.id = t.book_id WHERE b.work_id = w.id) + "
        " (SELECT COALESCE(SUM(LENGTH(s.translation_text)), 0) "
        "  FROM translation_segments s JOIN books b ON b.id = s.book_id WHERE b.work_id = w.id) "
        "FROM works w WHERE w.id IN (SELECT id FROM split_works)"
    ).fetchall()
    out = {}
    for author, nbytes in rows:
        out[author] = out.get(author, 0) + (nbytes or 0)
    return out


def _pack_first_fit(items: list, capacity: int) -> list:
    """items: list of (name, size); returns list of lists of names, first-fit
    decreasing."""
    bins = []
    for name, size in sorted(items, key=lambda x: -x[1]):
        for b in bins:
            if b["size"] + size <= capacity:
                b["names"].append(name)
                b["size"] += size
                break
        else:
            bins.append({"names": [name], "size": size})
    return [b["names"] for b in bins]


def emit_extended_delta(full_db_path: Path, ext_path: Path, ranges: list, ts: str) -> None:
    """Cut, size, verify and place the extended delta parts."""
    print(f"\n{'=' * 60}")
    print("CUTTING THE EXTENDED DELTA")
    print(f"{'=' * 60}")
    merge_stmts = _load_merge_statements()
    units_dir = _PARTS_DIR / "units"
    units_dir.mkdir(parents=True, exist_ok=True)
    for stale in list(_PARTS_DIR.glob("*.db*")) + list(_PARTS_DIR.glob("*.manifest.json")):
        stale.unlink()
    for stale in units_dir.glob("*"):
        stale.unlink()

    ext = sqlite3.connect(ext_path)
    units = _delta_units(ext, ranges)
    print(f"  {len(units)} units: " + ", ".join(
        f"{u['name']}({len(u['work_ids'])} works{', lexicon' if u['lexicon_languages'] else ''})"
        for u in units))

    # 1. Measure each unit: cut it WITH its indexes (index pages are a large
    #    share of the compressed size and compress worse than text; measured
    #    2026-09-27, a part packed on index-less unit sizes came out 33
    #    percent over its estimate), zip it at a fast level. Level 9 (the
    #    shipped level) is smaller, so packing on these figures is conservative.
    target = pack_layout.PART_SIZE_TARGET_BYTES
    measured = []  # (unit dict, zip_bytes)
    for u in units:
        t0 = time.time()
        db = units_dir / f"{u['name']}.db"
        _cut_slice(ext_path, db, u["work_ids"], u["lexicon_languages"], ranges,
                   with_indexes=True, vacuum=False)
        z = _zip_slice(db, units_dir / f"{u['name']}.zip", f"{u['name']}.db", level=6)
        db.unlink()
        print(f"  unit {u['name']:14s} {z / 1e9:5.2f} GB compressed ({time.time() - t0:.0f}s)")
        measured.append((u, z))

    # 2. A unit over the target is split by author, largest authors first,
    #    on each author's share of the unit's text bytes.
    pieces = []  # (piece dict, est_zip_bytes)
    for u, z in measured:
        if z <= target:
            pieces.append((u, z))
            continue
        by_author = _author_text_bytes(ext, u["work_ids"])
        total = sum(by_author.values()) or 1
        est = [(a, int(z * b / total)) for a, b in by_author.items()]
        groups = _pack_first_fit(est, int(target * 0.9))
        author_works = {}
        for w in u["work_ids"]:
            a = ext.execute("SELECT author_id FROM works WHERE id = ?", (w,)).fetchone()[0]
            author_works.setdefault(a, []).append(w)
        for i, g in enumerate(groups, 1):
            piece = dict(u, name=f"{u['name']}_{i}",
                         work_ids=[w for a in g for w in author_works[a]])
            size = sum(s for a, s in est if a in g)
            pieces.append((piece, size))
        print(f"  unit {u['name']} ({z / 1e9:.2f} GB) split into {len(groups)} pieces by author")

    # 3. Pack pieces into parts.
    bins = _pack_first_fit([(p["name"], s) for p, s in pieces], target)
    by_name = {p["name"]: p for p, _ in pieces}
    parts = []
    for i, names in enumerate(bins, 1):
        ps = [by_name[n] for n in names]
        parts.append({
            "n": i,
            "pack_id": _PART_MODULE_FMT.format(n=i),
            "pieces": names,
            "corpora": sorted({c for p in ps for c in p["corpora"]}),
            "languages": sorted({l for p in ps for l in p["languages"]}),
            "lexicon_languages": sorted({l for p in ps for l in p["lexicon_languages"]}),
            "work_ids": [w for p in ps for w in p["work_ids"]],
        })
    ext.close()

    # 4. Cut, zip and manifest each part.
    print(f"\n  cutting {len(parts)} parts")
    for part in parts:
        t0 = time.time()
        db = _PARTS_DIR / f"{part['pack_id']}.db"
        counts = _cut_slice(ext_path, db, part["work_ids"], part["lexicon_languages"], ranges)
        manifest = {
            "manifest_version": 1,
            "pack_id": part["pack_id"],
            "part": part["n"],
            "parts": len(parts),
            "build_time": ts,
            "schema_sha256": _schema_sha256(),
            "corpora": part["corpora"],
            "languages": part["languages"],
            "lexicon_languages": part["lexicon_languages"],
            "lexicon_id_ranges": {
                t: [[r["lo"], r["hi"]] for r in _ranges_for(ranges, t, set(part["lexicon_languages"]))]
                for t in pack_layout.LEXICON_TABLES
            },
            "db_bytes": db.stat().st_size,
            "orphan_segments": counts.pop("orphan_segments"),
            "rows": counts,
        }
        zip_path = _PARTS_DIR / f"{part['pack_id']}.db.zip"
        zb = _zip_slice(db, zip_path, f"{part['pack_id']}.db", manifest)
        manifest["zip_bytes"] = zb
        manifest["zip_sha256"] = _sha256(zip_path)
        part.update(db=db, zip=zip_path, manifest=manifest)
        with open(_PARTS_DIR / f"{part['pack_id']}.manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=1)
        flag = ""
        if zb > pack_layout.PLAY_PER_PACK_CAP_BYTES:
            flag = "  OVER THE 1.5 GB CAP"
        elif zb > target:
            flag = "  over the target"
        print(f"  part {part['n']}: {', '.join(part['pieces'])}: "
              f"{db.stat().st_size / 1e9:.2f} GB db, {zb / 1e9:.2f} GB zip "
              f"({time.time() - t0:.0f}s){flag}")
    over = [p for p in parts if p["manifest"]["zip_bytes"] > pack_layout.PLAY_PER_PACK_CAP_BYTES]
    if over:
        raise RuntimeError(f"parts over the per-pack cap: {[p['pack_id'] for p in over]}")

    # 5. Partition and round trip.
    _verify_delta_partition(full_db_path, ext_path, parts, merge_stmts)

    # 6. Budget table.
    _check_on_demand_budget(parts)

    # 7. Gradle modules and copies.
    _place_parts(parts)

    # 8. Build output that has served its purpose: the inflated part DBs and
    #    the unit measurement zips (about 11 GB). The part zips and manifests
    #    stay in delta_parts/ for --copy-parts.
    for part in parts:
        if part["db"].exists():
            part["db"].unlink()
    for f in units_dir.glob("*"):
        f.unlink()


def _schema_sha256() -> str:
    from shared.database_schema import expected_sqlite_master
    ddl = "\n".join(f"{k}\n{v}" for k, v in sorted(expected_sqlite_master().items()))
    return hashlib.sha256(ddl.encode("utf-8")).hexdigest()


def _verify_delta_partition(full_db_path: Path, ext_path: Path, parts: list, merge_stmts: list) -> None:
    """Merge every part into a copy of the full DB with the shared SQL, then
    require the result to equal the extended DB row for row, ids included."""
    import shutil
    from shared.database_schema import _table_names
    print("\n  round trip: merging every part into a copy of the full DB...")
    rt = _PARTS_DIR / "roundtrip.db"
    if rt.exists():
        rt.unlink()
    shutil.copyfile(full_db_path, rt)
    conn = sqlite3.connect(rt)
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("PRAGMA journal_mode = OFF")
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("PRAGMA cache_size = -512000")
    for part in parts:
        t0 = time.time()
        conn.execute("ATTACH DATABASE ? AS part", (str(part["db"]),))
        for st in merge_stmts:
            conn.execute(st)
        conn.commit()
        conn.execute("DETACH DATABASE part")
        print(f"    merged {part['pack_id']} ({time.time() - t0:.0f}s)")
    conn.execute("ATTACH DATABASE ? AS ext", (str(ext_path),))
    pk = {"translation_lookup": ["book_id", "line_number", "segment_id"],
          "milestone_line_ranges": ["work_id", "milestone"]}
    errors = []
    for t in _table_names():
        cols = _table_columns(conn, "main", t)
        keys = pk.get(t, ["id"])
        join = " AND ".join(f"e.{k} = m.{k}" for k in keys)
        cmp_cols = [c for c in cols if c not in keys]
        same = " AND ".join(f"m.{c} IS e.{c}" for c in cmp_cols) or "1"
        extra = " AND m.language <> 'system'" if t == "dictionary_entries" else ""
        n_main = conn.execute(f"SELECT COUNT(*) FROM main.{t} m WHERE 1{extra}").fetchone()[0]
        n_ext = conn.execute(f"SELECT COUNT(*) FROM ext.{t} m WHERE 1{extra}").fetchone()[0]
        n_same = conn.execute(
            f"SELECT COUNT(*) FROM main.{t} m JOIN ext.{t} e ON {join} WHERE {same}{extra}"
        ).fetchone()[0]
        ok = n_main == n_ext == n_same
        print(f"    {t}: merged {n_main:,}, extended {n_ext:,}, identical {n_same:,} {'OK' if ok else 'MISMATCH'}")
        if not ok:
            errors.append(t)
    # Foreign keys: the extended DB itself carries translation segments whose
    # book_id has no books row (2,762 on 2026-09-27; see the filter's
    # _SEGMENT_SCOPE_SQL). The merged result must have exactly the extended
    # DB's violations and no others, table by table.
    def fk_by_table(schema):
        out = {}
        for row in conn.execute(f"PRAGMA {schema}.foreign_key_check"):
            out[row[0]] = out.get(row[0], 0) + 1
        return out
    fk_main, fk_ext = fk_by_table("main"), fk_by_table("ext")
    if fk_main != fk_ext:
        errors.append(f"foreign_key_check differs: merged {fk_main}, extended {fk_ext}")
    else:
        print(f"    foreign_key_check: {fk_main or 'clean'} (same as extended) OK")
    conn.close()
    rt.unlink()
    if errors:
        raise RuntimeError(f"round trip of full + parts does not equal extended: {errors}")
    print("✓ full + every part == extended, row for row, ids included, with the shared merge SQL")


def _check_on_demand_budget(parts: list) -> None:
    packs = {
        "full_database_pack": REPO_ROOT / "full_database_pack/src/main/assets/perseus_texts_full.db.zip",
        "audio_pack": REPO_ROOT / "audio_pack/src/main/assets/homer_iliad_chamberlain_audio.zip",
    }
    sizes = {}
    for name, p in packs.items():
        if not p.exists():
            raise FileNotFoundError(f"on-demand pack asset missing: {p}")
        sizes[name] = p.stat().st_size
    for name in ("topical_pack", "references_pack"):
        d = REPO_ROOT / name / "src/main/assets"
        sizes[name] = sum(f.stat().st_size for f in d.iterdir() if f.is_file())
    for part in parts:
        sizes[part["pack_id"]] = part["manifest"]["zip_bytes"]
    total = sum(sizes.values())
    print("\n  On-demand budget (compressed bytes in the bundle):")
    for name, b in sizes.items():
        print(f"    {name:26s} {b / 1e9:6.2f} GB")
    print(f"    {'total':26s} {total / 1e9:6.2f} GB of {pack_layout.PLAY_ON_DEMAND_BUDGET_BYTES / 1e9:.0f} GB")
    if total > pack_layout.PLAY_ON_DEMAND_BUDGET_BYTES:
        raise RuntimeError("on-demand packs exceed PLAY_ON_DEMAND_BUDGET_BYTES")


def _place_parts(parts: list) -> None:
    """Every part needs a Gradle asset-pack module, and no module may be
    left without a part. Missing or extra modules are a hard failure that
    names what to add or remove; the zips stay in delta_parts/ and can be
    placed with --copy-parts once the modules exist."""
    import shutil
    settings = (REPO_ROOT / "settings.gradle").read_text()
    app_gradle = (REPO_ROOT / "app" / "build.gradle").read_text()
    problems = []
    for part in parts:
        mod = part["pack_id"]
        if not (REPO_ROOT / mod / "build.gradle").exists():
            problems.append(f"add module {mod}/build.gradle (copy references_pack/build.gradle, packName = \"{mod}\")")
        if f"include ':{mod}'" not in settings:
            problems.append(f"add include ':{mod}' to settings.gradle")
        if f'":{mod}"' not in app_gradle:
            problems.append(f'add ":{mod}" to android.assetPacks in app/build.gradle')
    n = len(parts) + 1
    while (REPO_ROOT / _PART_MODULE_FMT.format(n=n)).exists():
        problems.append(f"remove module {_PART_MODULE_FMT.format(n=n)} (no part fills it)")
        n += 1
    if problems:
        print("\n❌ Part modules do not match the parts cut:")
        for p in problems:
            print(f"  {p}")
        print(f"  The part zips and manifests are in {_PARTS_DIR}; after fixing the modules run\n"
              f"  `assemble_database.py full --copy-parts` to place them without rebuilding.")
        raise RuntimeError("Gradle part modules do not match the parts")
    for part in parts:
        dest = REPO_ROOT / part["pack_id"] / "src" / "main" / "assets"
        dest.mkdir(parents=True, exist_ok=True)
        for old in dest.iterdir():
            old.unlink()
        shutil.copy(part["zip"], dest / part["zip"].name)
        shutil.copy(_PARTS_DIR / f"{part['pack_id']}.manifest.json", dest / f"{part['pack_id']}.manifest.json")
        print(f"  placed {part['pack_id']}: {part['zip'].name} + manifest")
    print("✓ Every part placed in its module")


def copy_parts_only() -> None:
    """--copy-parts: place already-cut parts from delta_parts/ into their modules."""
    manifests = sorted(_PARTS_DIR.glob("db_extended_part*.manifest.json"))
    if not manifests:
        raise FileNotFoundError(f"no cut parts in {_PARTS_DIR}; run `assemble_database.py full` first")
    parts = []
    for mp in manifests:
        m = json.loads(mp.read_text())
        z = _PARTS_DIR / f"{m['pack_id']}.db.zip"
        if not z.exists() or z.stat().st_size != m["zip_bytes"]:
            raise RuntimeError(f"{z} missing or does not match its manifest; re-run the full build")
        parts.append({"n": m["part"], "pack_id": m["pack_id"], "zip": z, "manifest": m})
    parts.sort(key=lambda p: p["n"])
    _check_on_demand_budget(parts)
    _place_parts(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=list(MODE_TO_DB_NAME.keys()))
    ap.add_argument(
        "--skip-oga",
        action="store_true",
        help="Skip OGA lemma enrichment (sample mode's OGA pass takes ~5 min).",
    )
    ap.add_argument(
        "--copy-parts",
        action="store_true",
        help="full mode only: place the delta parts already cut in data-prep/delta_parts/ "
             "into their Gradle modules without rebuilding (after adding missing modules).",
    )
    args = ap.parse_args()
    if args.copy_parts:
        if args.mode != "full":
            ap.error("--copy-parts applies to full mode only")
        os.chdir(SCRIPT_DIR)
        copy_parts_only()
        return

    # Writer side of the readers-writers build mutex. Assembly reads
    # every module DB, so it blocks until every module build finishes
    # (and blocks any new module build from starting).
    if not acquire_assembly_lock():
        print("Could not acquire assembly lock; a module build is still "
              "running. See above for holder PID. Aborting.", file=sys.stderr)
        sys.exit(1)
    try:
        assemble(args.mode, skip_oga=args.skip_oga)
    finally:
        release_locks()


if __name__ == "__main__":
    main()
