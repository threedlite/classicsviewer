#!/usr/bin/env python3
"""
check_dict_lemma_health.py — class-level dictionary/lemma_map sanity check.

Purpose
-------
The recent change in greek/wiktionary-processing/extract_all_ancient_greek_words_with_diacritics.py
("aligned translations override perseus, fix latin aligned-dir path" series)
deliberately stops emitting a dictionary_entries row for any Wiktionary page
whose definition lines consist solely of `{{inflection of}}` references — those
are inflected word forms, not lemmas, and emitting them was corrupting
lemma_map by creating confidence-1.0 form==lemma self-mappings that outranked
real form→lemma rows.

The promise of that change is: dropped inflected forms remain fully resolvable
*through* lemma_map. This script audits that promise at the class level:

  1. Per-source row counts for dictionary_entries and lemma_map (by language),
     to catch any source disappearing entirely or shrinking massively.
  2. Reachability: a deterministic random sample of word_forms drawn from
     the `words` table must resolve to a real dictionary headword either
     directly or via lemma_map → dictionary_entries.

Run after assembly:
    python3 data-prep/check_dict_lemma_health.py data-prep/perseus_texts_sample.db
Exit code is 0 on pass, 1 on any failure.

The script is parameter-light by design: it asks the DB what languages exist,
samples uniformly, and reports actuals. No word-specific probes, no per-lemma
allow-lists — class-level only.
"""

import argparse
import random
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

# Reuse the runtime app's full normalization + lookup chain rather than
# reimplement a shadow lookup here. check_dictionary_coverage.py mirrors the
# Android/iOS app behavior (NFC, apostrophe normalization, ultra-normalized
# diacritic-stripped lookup, prefix search, compound decomposition).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_dictionary_coverage import DictionaryCoverageChecker  # noqa: E402

# Minimum reachability for each language we evaluate. Tuned against
# 0.8.125-era DBs across modes:
#   sample  greek=77.6%
#   ios     greek=87.6%
#   full    greek=65.7%, latin=59.0%
# Reachability varies by corpus breadth (full has more rare/proper-noun
# forms than the curated sample/ios sets) so a single tight per-language
# floor would either be too lax for sample or too strict for full. These
# defaults are intentionally conservative — they exist to catch a
# catastrophic regression (a whole dictionary source failing to merge,
# the wiktionary inflected-form filter mis-firing and dropping lemmas),
# not to grade overall coverage. Tighten via --floor for stricter checks.
DEFAULT_REACHABILITY_FLOOR = {
    "greek": 0.50,
    "latin": 0.40,
}

# Sample size per language. 2000 is enough to make a single dropped lemma
# table visible (one lost source = ~10-30 pp loss in reachability) while
# keeping the script under a few seconds on the extended DB.
DEFAULT_SAMPLE_SIZE = 2000

# Deterministic seed: same DB → same probe set → same result, run to run.
SAMPLE_SEED = 0xC1A551C5  # "ClassicS" in hex-leet


def per_source_counts(conn, table, lang_col="language"):
    """Return {(language, source): count} for the given table."""
    rows = conn.execute(
        f"SELECT {lang_col} AS lang, source, COUNT(*) "
        f"FROM {table} "
        f"GROUP BY {lang_col}, source"
    ).fetchall() if lang_col else conn.execute(
        f"SELECT NULL AS lang, source, COUNT(*) FROM {table} GROUP BY source"
    ).fetchall()
    out = defaultdict(int)
    for lang, source, n in rows:
        out[(lang, source or "(null)")] = n
    return dict(out)


def lemma_map_per_source(conn):
    """lemma_map has no language column; bucket by source only."""
    rows = conn.execute(
        "SELECT source, COUNT(*) FROM lemma_map GROUP BY source"
    ).fetchall()
    return {src or "(null)": n for src, n in rows}


def languages_in_words(conn):
    """Return languages present in `words` (joined through books → works → authors)."""
    rows = conn.execute(
        "SELECT DISTINCT a.language "
        "FROM words w "
        "JOIN books b ON b.id = w.book_id "
        "JOIN works wk ON wk.id = b.work_id "
        "JOIN authors a ON a.id = wk.author_id "
        "WHERE a.language IS NOT NULL"
    ).fetchall()
    return sorted(r[0] for r in rows)


def sample_word_forms(conn, language, n, rng):
    """Pull a deterministic random sample of word_forms in `language`.

    Uses `words` (the per-token table) so the sample reflects the actual
    text distribution rather than the bias of the headword vocabulary.
    Restricted to alphabetic forms to skip obvious noise (digits, marks).
    """
    rows = conn.execute(
        "SELECT DISTINCT w.word "
        "FROM words w "
        "JOIN books b ON b.id = w.book_id "
        "JOIN works wk ON wk.id = b.work_id "
        "JOIN authors a ON a.id = wk.author_id "
        "WHERE a.language = ?",
        (language,),
    ).fetchall()
    candidates = [r[0] for r in rows if r[0] and any(ch.isalpha() for ch in r[0])]
    if not candidates:
        return []
    if len(candidates) <= n:
        return sorted(candidates)
    rng.shuffle(candidates)
    return candidates[:n]


def reachability(checker, language, sample):
    """Fraction of sampled word_forms that resolve to a real dict headword
    OR a morphological entry, via the app's full lookup chain.

    A "miss" here means: the runtime app finds nothing for this word —
    not even a morphology hint. That is the regression the recent change
    must not introduce (dropped inflected-form dict entries are supposed
    to remain reachable via lemma_map).
    """
    if not sample:
        return 1.0, 0, 0
    hit = 0
    for form in sample:
        status, _sources = checker.check_word_in_dictionary(form, language)
        if status != "no_entry":
            hit += 1
    return hit / len(sample), hit, len(sample)


def fmt_pct(x):
    return f"{x*100:.2f}%"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("db", help="Path to an assembled perseus_texts_*.db")
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE,
                        help=f"Word-sample size per language (default {DEFAULT_SAMPLE_SIZE})")
    parser.add_argument("--floor", action="append", default=[],
                        metavar="LANG=FRACTION",
                        help="Override reachability floor for a language "
                             "(e.g. greek=0.97). Repeatable.")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress per-source breakdown; print summary only.")
    args = parser.parse_args(argv)

    floors = dict(DEFAULT_REACHABILITY_FLOOR)
    for spec in args.floor:
        if "=" not in spec:
            parser.error(f"--floor expects LANG=FRACTION, got {spec!r}")
        lang, frac = spec.split("=", 1)
        floors[lang.strip()] = float(frac)

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: db not found: {db_path}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = 1;")
    # Reachability probe uses the runtime app's normalization chain.
    checker = DictionaryCoverageChecker(str(db_path))

    print(f"=== dict/lemma health check: {db_path.name} ===")

    # 1. Per-source breakdown.
    dict_counts = per_source_counts(conn, "dictionary_entries")
    lemma_counts = lemma_map_per_source(conn)

    if not args.quiet:
        print("\n-- dictionary_entries by (language, source) --")
        for (lang, src), n in sorted(dict_counts.items(),
                                     key=lambda kv: (kv[0][0] or "", -kv[1])):
            print(f"  {lang or '(null)':>10}  {src:<32}  {n:>10,}")
        print("\n-- lemma_map by source --")
        for src, n in sorted(lemma_counts.items(), key=lambda kv: -kv[1]):
            print(f"  {src:<32}  {n:>10,}")

    # 2. Reachability per language present in words.
    rng = random.Random(SAMPLE_SEED)
    failures = []
    # Languages that have dictionary_entries in this DB. Sample mode legitimately
    # has no Latin dict (Whitaker is full/extended only), so we can't fail it.
    dict_languages = {lang for (lang, _src), n in dict_counts.items()
                      if n > 0 and lang and lang != "system"}
    print("\n-- reachability (sample_size={}) --".format(args.sample_size))
    for lang in languages_in_words(conn):
        if lang not in dict_languages:
            print(f"  {lang:<10}        n/a  (no dictionary_entries for this language in this DB)")
            continue
        if lang not in floors:
            # No floor configured → report but don't fail. Keeps the script
            # useful for languages that aren't part of the recent change
            # without forcing us to pick floors blindly.
            sample = sample_word_forms(conn, lang, args.sample_size, rng)
            frac, hit, total = reachability(checker, lang, sample)
            print(f"  {lang:<10}  {fmt_pct(frac):>8}  ({hit:>5}/{total:<5})  [no floor configured — informational]")
            continue
        sample = sample_word_forms(conn, lang, args.sample_size, rng)
        frac, hit, total = reachability(checker, lang, sample)
        status = "PASS" if frac >= floors[lang] else "FAIL"
        print(f"  {lang:<10}  {fmt_pct(frac):>8}  ({hit:>5}/{total:<5})  floor={fmt_pct(floors[lang])}  {status}")
        if frac < floors[lang]:
            failures.append((lang, frac, floors[lang]))

    if failures:
        print("\n❌ reachability regression:")
        for lang, frac, floor in failures:
            print(f"   {lang}: {fmt_pct(frac)} < floor {fmt_pct(floor)}")
        print("\nLikely causes: a lemma_map source (oga / wiktionary / "
              "perseus_treebank / inflection_of / Enhanced Wiktionary) failed "
              "to import, OR dictionary_entries lost a major source. Compare "
              "the per-source breakdown above against the previous-release "
              "database_quality_report_*.txt.")
        return 1

    print("\n✅ dict/lemma health OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
