#!/usr/bin/env python3
"""Build the vocabulary practice data files from the committed source lists.

Sources (all CC BY-SA, see README.md), one CSV per language under sources/:
    dcc_greek_core_list.csv     DCC Greek Core Vocabulary
    dcc_latin_core_list.csv     DCC Latin Core Vocabulary

Outputs (under vocabulary/):
    <language>_core_vocabulary.json     the app data files
    vocabulary_quality_report.txt       counts, coverage, and source quirks

The JSON files are copied into the Android asset dirs and the iOS Resources
dir that exist, mirroring figures/build_rhetoric_db.py.

Every check here is fatal unless stated in the report. The script never
rewrites source data.
"""
import csv
import json
import re
import sqlite3
import sys
import unicodedata
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPORT_OUT = HERE / "vocabulary_quality_report.txt"

# Dictionary coverage is measured against the first of these that holds
# dictionary entries for the language. The sample DB has no Latin dictionary.
DICTIONARY_DBS = [
    ROOT / "data-prep" / "perseus_texts_sample.db",
    ROOT / "data-prep" / "perseus_texts_full.db",
]

ASSET_DIRS = [
    ROOT / "app" / "src" / "main" / "assets" / "vocabulary",
    ROOT / "app" / "src" / "debug" / "assets" / "vocabulary",
    ROOT / "ios" / "ClassicsViewer" / "Resources",
]

# Header comparison is case-insensitive: the Greek export capitalises these
# differently from the Latin one.
EXPECTED_HEADER = ["headword", "definition", "part of speech", "semantic group", "frequency rank"]
MIN_DICTIONARY_COVERAGE = 0.95
# Rows with an empty definition cannot be played and are excluded; more than
# this fraction of them means the export is broken rather than quirky.
MAX_SKIPPED_FRACTION = 0.01

SOURCES = [
    {
        "language": "greek",
        "csv": HERE / "sources" / "dcc_greek_core_list.csv",
        "json": HERE / "greek_core_vocabulary.json",
        "min_rows": 500,
        "lemma_re": re.compile(r"^[Ͱ-Ͽἀ-῿’᾽᾿῾]+$"),
        "info": {
            "language": "greek",
            "source": "Dickinson College Commentaries, Greek Core Vocabulary",
            "url": "https://dcc.dickinson.edu/greek-core-list",
            "license": "CC BY-SA 3.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/3.0/",
            "retrieved": "2026-09-24",
        },
    },
    {
        "language": "latin",
        "csv": HERE / "sources" / "dcc_latin_core_list.csv",
        "json": HERE / "latin_core_vocabulary.json",
        "min_rows": 900,
        "lemma_re": re.compile(r"^[A-Za-zāēīōūȳĀĒĪŌŪȲ]+$"),
        "info": {
            "language": "latin",
            "source": "Dickinson College Commentaries, Latin Core Vocabulary",
            "url": "https://dcc.dickinson.edu/latin-vocabulary-list",
            "license": "CC BY-SA 3.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/3.0/",
            "retrieved": "2026-09-26",
        },
    },
]


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def nfc(s):
    return unicodedata.normalize("NFC", s).strip()


def derive_lemma(headword):
    """One general rule for every row; see PRACTICE_VOCABULARY_PROPOSAL.md sec. 5.

    1. NFC-normalise.
    2. Correlative pairs (a...b / a…b): keep the first member.
    3. Drop parenthesised optional segments, e.g. (ν), (-um).
    4. First token, splitting on commas, slashes and whitespace.
    5. Strip leading/trailing hyphens, en dashes and punctuation.
    """
    h = nfc(headword)
    h = re.split(r"\.\.\.|…", h)[0]
    h = re.sub(r"\([^)]*\)", "", h)
    first = re.split(r"[,/\s]+", h.strip())[0]
    return first.strip("-–:;.")


def strip_macrons(s):
    """Dictionary headwords carry no macrons; the DCC Latin list does."""
    decomposed = unicodedata.normalize("NFD", s)
    return unicodedata.normalize("NFC", decomposed.replace("̄", ""))


def read_source(src):
    path = src["csv"]
    if not path.exists():
        fail(f"missing source file {path}")
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        fail(f"{path.name} is empty")
    header = [h.strip().lower() for h in rows[0]]
    if header != EXPECTED_HEADER:
        fail(f"{path.name}: unexpected header {rows[0]!r}; expected {EXPECTED_HEADER!r}")
    data = rows[1:]
    if len(data) < src["min_rows"]:
        fail(f"{path.name}: only {len(data)} rows; expected at least {src['min_rows']}")
    return data


def build_entries(src, data):
    entries = []
    non_nfc = []
    skipped = []
    for i, row in enumerate(data, start=2):
        if len(row) != 5:
            fail(f"{src['csv'].name} line {i}: expected 5 fields, got {len(row)}: {row!r}")
        headword, definition, pos, group, rank_s = row
        if not definition.strip():
            skipped.append((i, headword))
            continue
        if any(not f.strip() for f in row):
            fail(f"{src['csv'].name} line {i}: empty field in {row!r}")
        if any(unicodedata.normalize("NFC", f) != f for f in row):
            non_nfc.append(headword)
        try:
            rank = int(rank_s.strip())
        except ValueError:
            fail(f"{src['csv'].name} line {i}: non-numeric rank {rank_s!r}")
        lemma = derive_lemma(headword)
        if not lemma:
            fail(f"{src['csv'].name} line {i}: empty lemma from headword {headword!r}")
        if not src["lemma_re"].match(lemma):
            fail(f"{src['csv'].name} line {i}: lemma {lemma!r} has characters outside "
                 f"the {src['language']} alphabet (headword {headword!r})")
        entries.append({
            "rank": rank,
            "headword": nfc(headword),
            "lemma": lemma,
            "definition": nfc(definition),
            "pos": nfc(pos),
            "group": nfc(group),
        })
    if len(skipped) > MAX_SKIPPED_FRACTION * len(data):
        fail(f"{src['csv'].name}: {len(skipped)} rows have an empty definition; "
             f"more than {MAX_SKIPPED_FRACTION:.0%} of the export")
    # The app keys progress and on-screen tiles by headword.
    headwords = [e["headword"] for e in entries]
    dup_headwords = sorted({h for h in headwords if headwords.count(h) > 1})
    if dup_headwords:
        fail(f"{src['csv'].name}: duplicate headwords {dup_headwords}")
    # Stable order: rank, then source order for ties.
    entries.sort(key=lambda e: e["rank"])
    return entries, non_nfc, skipped


def dictionary_coverage(language, entries):
    """Fraction of lemmas that resolve to a dictionary_entries headword.

    Uses the first DB in DICTIONARY_DBS that has entries for the language.
    Returns (db path, hits, misses list) or None if no DB has any.
    """
    for db in DICTIONARY_DBS:
        if not db.exists():
            continue
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        total = con.execute(
            "SELECT COUNT(*) FROM dictionary_entries WHERE language = ?", (language,)
        ).fetchone()[0]
        if not total:
            con.close()
            continue
        misses = []
        hits = 0
        for e in entries:
            n = con.execute(
                "SELECT COUNT(*) FROM dictionary_entries WHERE headword = ? AND language = ?",
                (strip_macrons(e["lemma"]), language),
            ).fetchone()[0]
            if n:
                hits += 1
            else:
                misses.append(e)
        con.close()
        return db, hits, misses
    return None


def build_language(src, report):
    data = read_source(src)
    entries, non_nfc, skipped = build_entries(src, data)

    ranks = [e["rank"] for e in entries]
    dup_ranks = sorted({r for r in ranks if ranks.count(r) > 1})
    missing_ranks = sorted(set(range(1, max(ranks) + 1)) - set(ranks))
    definitions = [e["definition"] for e in entries]
    dup_defs = sorted({d for d in definitions if definitions.count(d) > 1})
    lemmas = [e["lemma"] for e in entries]
    dup_lemmas = sorted({l for l in lemmas if lemmas.count(l) > 1})

    coverage = dictionary_coverage(src["language"], entries)

    report.append(f"=== {src['language']} ===")
    report.append(f"Source: {src['csv'].relative_to(ROOT)}")
    report.append(f"Entries: {len(entries)}")
    report.append(f"Rows skipped for empty definition: "
                  + (", ".join(f"line {i} {h!r}" for i, h in skipped) if skipped else "none"))
    report.append(f"Rank range: {min(ranks)}-{max(ranks)}")
    report.append(f"Duplicate ranks: {dup_ranks or 'none'}")
    report.append(f"Unused ranks: {missing_ranks or 'none'}")
    report.append(f"Headwords not in NFC in source (normalised on output): {non_nfc or 'none'}")
    report.append(f"Distinct parts of speech: {len({e['pos'] for e in entries})}")
    report.append(f"Distinct semantic groups: {len({e['group'] for e in entries})}")
    report.append(f"Lemmas shared by more than one entry (homographs): {len(dup_lemmas)}")
    for l in dup_lemmas:
        report.append(f"  {l!r}: " + " | ".join(e["headword"] for e in entries if e["lemma"] == l))
    report.append(f"Definitions shared by more than one entry: {len(dup_defs)}")
    for d in dup_defs:
        report.append(f"  {d!r}: " + ", ".join(e["lemma"] for e in entries if e["definition"] == d))
    report.append("")
    if coverage is None:
        report.append(f"Dictionary coverage: skipped (no DB with {src['language']} entries)")
    else:
        db, hits, misses = coverage
        frac = hits / len(entries)
        report.append(f"Dictionary coverage against {db.name}: {hits}/{len(entries)} ({frac:.1%})")
        for e in misses:
            report.append(f"  unresolved: rank {e['rank']} lemma {e['lemma']!r} from headword {e['headword']!r}")
        if frac < MIN_DICTIONARY_COVERAGE:
            REPORT_OUT.write_text("\n".join(report) + "\n", encoding="utf-8")
            fail(f"{src['language']} dictionary coverage {frac:.1%} below floor "
                 f"{MIN_DICTIONARY_COVERAGE:.0%}; see {REPORT_OUT}")
    report.append("")

    payload = {**src["info"], "count": len(entries), "entries": entries}
    text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    src["json"].write_text(text, encoding="utf-8")
    return text


def main():
    report = ["Vocabulary build report", f"Built: {date.today().isoformat()}", ""]
    outputs = []
    for src in SOURCES:
        outputs.append((src["json"], build_language(src, report)))
    REPORT_OUT.write_text("\n".join(report) + "\n", encoding="utf-8")

    copied = []
    for d in ASSET_DIRS:
        if d.parent.exists():
            d.mkdir(parents=True, exist_ok=True)
            for path, text in outputs:
                (d / path.name).write_text(text, encoding="utf-8")
                copied.append(d / path.name)
    if not copied:
        fail("no asset directory exists; nothing copied")

    print("\n".join(report))
    for path, _ in outputs:
        print(f"Wrote {path} ({path.stat().st_size} bytes)")
    for c in copied:
        print(f"Copied to {c.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
