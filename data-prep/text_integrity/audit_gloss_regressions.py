#!/usr/bin/env python3
"""Audit interlinear gloss changes — release gate for regressions.

Consumes a merkle diff file (produced by `merkle_snapshot.py diff`) to find
which rows changed, then looks up the actual translation_text content from
both DBs to classify each change:

  IMPROVED      ??? → real definition
  REGRESSED     real definition → ???    ← gate fails on this
  CHANGED       real → real (different text; needs manual judgment)
  UNCHANGED     bytes identical (shouldn't happen if merkle said it changed)
  STRUCTURAL    line count differs (multi-line interlinear restructured)

Exit codes:
  0 — regressions ≤ --max-regressions
  1 — regressions exceed threshold (gate failure)
  2 — usage / DB error

Usage:
  python3 audit_gloss_regressions.py \\
      --diff       diff_xxx_vs_release.txt \\
      --before-db  perseus_texts_extended.db.preFix \\
      --after-db   perseus_texts_extended.db \\
      [--max-regressions N]        (default: 0)
      [--samples-per-class K]      (default: 20)
      [--report-out PATH]

This codifies the audit that caught the 998 Bug-A regressions during the
May 16 A+B episode. Wire it into the build verification step after every
interlinear regen + re-assemble cycle.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from shared.venv_check import assert_libs  # noqa: E402
assert_libs("audit")
import argparse
import re
import sqlite3
from collections import Counter


GLOSS_RE = re.compile(r'^\|\s+\*\*(.+?)\*\*\s+\|\s*$')
ROW_KEY_RE = re.compile(r'^\s+~\s+row\s+key=\["([^"]+)",\s*"[^"]+",\s*(\d+)\]')


def parse_changed_translation_rows(diff_path: Path):
    """Yield (book_id, seq) tuples for rows in the translation_segments
    section of a merkle diff file."""
    in_translation = False
    seen = set()
    with open(diff_path) as f:
        for line in f:
            if line.startswith("~ TABLE translation_segments:"):
                in_translation = True
                continue
            if (line.startswith("~ TABLE ") or line.startswith("+ TABLE ")
                    or line.startswith("- TABLE ")):
                # Any other TABLE header ends the translation_segments section
                if not line.startswith("~ TABLE translation_segments"):
                    in_translation = False
            if not in_translation:
                continue
            m = ROW_KEY_RE.match(line)
            if m:
                key = (m.group(1), int(m.group(2)))
                if key not in seen:
                    seen.add(key)
                    yield key


def get_text(conn: sqlite3.Connection, book_id: str, seq: int) -> str | None:
    """Fetch the Interlinear translation_text for a single row."""
    r = conn.execute(
        "SELECT translation_text FROM translation_segments "
        "WHERE book_id=? AND sequence_number=? AND translator LIKE 'Interlinear%'",
        (book_id, seq),
    ).fetchone()
    return r[0] if r else None


def find_word_for_gloss(lines: list[str], gloss_idx: int) -> str | None:
    """Look backward from a gloss line to find the Greek word being glossed.

    Interlinear layout puts the gloss `| **gloss** |` on the line AFTER the
    word's lemma/morph line `| ... |  | next_word |`. We split the preceding
    line by `|`, take the rightmost token that looks like a bare Greek word.
    """
    if gloss_idx == 0:
        return None
    prev = lines[gloss_idx - 1]
    tokens = [t.strip() for t in prev.split("|") if t.strip()]
    for tok in reversed(tokens):
        if "~" in tok or tok.startswith("**") or "=" in tok:
            continue
        if any('Ͱ' <= ch <= 'Ͽ' or 'ἀ' <= ch <= '῿' for ch in tok):
            return tok
    return None


def corpus_of(work_id: str) -> str:
    if "_OGL" in work_id:
        return "First1KGreek"
    if "_PTA" in work_id:
        return "PTA"
    if work_id.startswith("tlg"):
        return "Perseus_Greek"
    if work_id.startswith("phi"):
        return "Perseus_Latin"
    if work_id.startswith("stoa"):
        return "Stoa"
    return f"Other({work_id.split('.')[0]})"


def classify_row(before: str, after: str):
    """Compare two translation_text strings line-by-line. Return
    a per-class Counter and a list of per-line diff records (for samples)."""
    counts = Counter()
    diffs = []
    if before == after:
        return counts, diffs
    p_lines = before.split("\n")
    c_lines = after.split("\n")
    if len(p_lines) != len(c_lines):
        counts["STRUCTURAL"] += 1
        diffs.append({"type": "STRUCTURAL", "before_lines": len(p_lines),
                      "after_lines": len(c_lines)})
        return counts, diffs
    for i, (pl, cl) in enumerate(zip(p_lines, c_lines)):
        if pl == cl:
            continue
        pg = GLOSS_RE.match(pl)
        cg = GLOSS_RE.match(cl)
        if not pg or not cg:
            counts["NON_GLOSS_LINE"] += 1
            continue
        before_gloss = pg.group(1)
        after_gloss = cg.group(1)
        word = find_word_for_gloss(p_lines, i)
        if before_gloss == after_gloss:
            counts["UNCHANGED_GLOSS"] += 1
            continue
        if before_gloss == "???" and after_gloss != "???":
            cls = "IMPROVED"
        elif before_gloss != "???" and after_gloss == "???":
            cls = "REGRESSED"
        else:
            cls = "CHANGED"
        counts[cls] += 1
        diffs.append({"type": cls, "word": word,
                      "before": before_gloss, "after": after_gloss})
    return counts, diffs


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Audit interlinear gloss regressions using an existing "
                    "merkle diff to identify which rows to inspect.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--diff", required=True, type=Path,
                   help="Merkle diff file (output of `merkle_snapshot.py diff`)")
    p.add_argument("--before-db", required=True, type=Path,
                   help="Baseline DB referenced by the diff's 'before' snapshot")
    p.add_argument("--after-db", required=True, type=Path,
                   help="Candidate DB referenced by the diff's 'after' snapshot")
    p.add_argument("--max-regressions", type=int, default=0,
                   help="Exit 1 if regressions exceed this count (default: 0)")
    p.add_argument("--samples-per-class", type=int, default=20)
    p.add_argument("--report-out", type=Path, default=None,
                   help="Write report to this file (default: stdout)")
    args = p.parse_args(argv)

    for path in (args.diff, args.before_db, args.after_db):
        if not path.exists():
            print(f"ERROR: not found: {path}", file=sys.stderr)
            return 2

    print(f"Parsing changed rows from {args.diff}...", file=sys.stderr)
    changed = list(parse_changed_translation_rows(args.diff))
    print(f"  {len(changed)} translation_segments rows changed (from diff)",
          file=sys.stderr)

    bcon = sqlite3.connect(f"file:{args.before_db}?mode=ro", uri=True)
    acon = sqlite3.connect(f"file:{args.after_db}?mode=ro", uri=True)

    totals = Counter()
    samples = {"IMPROVED": [], "REGRESSED": [], "CHANGED": [], "STRUCTURAL": []}
    per_corpus_reg = Counter()
    per_work_reg = Counter()
    rows_audited = 0

    for book_id, seq in changed:
        b_text = get_text(bcon, book_id, seq)
        a_text = get_text(acon, book_id, seq)
        if b_text is None or a_text is None:
            # Row exists in only one DB — structural diff, skip
            continue
        rows_audited += 1
        counts, diffs = classify_row(b_text, a_text)
        for cls, n in counts.items():
            totals[cls] += n
        for d in diffs:
            cls = d["type"]
            if cls == "REGRESSED":
                corp = corpus_of(book_id)
                per_corpus_reg[corp] += 1
                work = book_id.rsplit(".", 1)[0]
                per_work_reg[work] += 1
            if cls in samples and len(samples[cls]) < args.samples_per_class:
                samples[cls].append({"book_id": book_id, "seq": seq, **d})

    out = []
    def w(s=""):
        out.append(s)

    w("=" * 78)
    w("INTERLINEAR GLOSS-REGRESSION AUDIT")
    w("=" * 78)
    w(f"  diff:     {args.diff}")
    w(f"  before:   {args.before_db}")
    w(f"  after:    {args.after_db}")
    w(f"  rows changed (per diff):  {len(changed)}")
    w(f"  rows audited (in both DBs): {rows_audited}")
    w("")
    w("Per-class line counts:")
    for cls in ("IMPROVED", "REGRESSED", "CHANGED", "UNCHANGED_GLOSS",
                "STRUCTURAL", "NON_GLOSS_LINE"):
        w(f"  {cls:<22} {totals.get(cls, 0):>8}")
    w("")

    regs = totals.get("REGRESSED", 0)
    impr = totals.get("IMPROVED", 0)
    w(f"  NET (improvements - regressions) = {impr - regs:+d}")
    w("")

    if per_corpus_reg:
        w("Regressions by corpus:")
        for corp, n in per_corpus_reg.most_common():
            w(f"  {corp:<18} {n:>6}")
        w("")
    if per_work_reg:
        w("Top 10 works by regressed rows:")
        for work, n in per_work_reg.most_common(10):
            w(f"  {work:<28} {n:>6}  ({corpus_of(work)})")
        w("")

    if samples["REGRESSED"]:
        w("=" * 78)
        w(f"REGRESSED samples (first {len(samples['REGRESSED'])}):")
        w("=" * 78)
        for s in samples["REGRESSED"]:
            w(f"  word={s.get('word')!r:<24}  {s['book_id']} seq={s['seq']}")
            w(f"    BEFORE: {s['before']!r}")
            w(f"    AFTER:  {s['after']!r}")

    if samples["IMPROVED"]:
        w("")
        w("=" * 78)
        w(f"IMPROVED samples (first {len(samples['IMPROVED'])}):")
        w("=" * 78)
        for s in samples["IMPROVED"]:
            w(f"  word={s.get('word')!r:<24}  {s['book_id']} seq={s['seq']}")
            w(f"    BEFORE: {s['before']!r}")
            w(f"    AFTER:  {s['after']!r}")

    text = "\n".join(out) + "\n"
    if args.report_out:
        args.report_out.write_text(text)
        print(f"Report written to {args.report_out}", file=sys.stderr)
    else:
        sys.stdout.write(text)

    print(file=sys.stderr)
    print(f"REGRESSIONS: {regs}   IMPROVEMENTS: {impr}   MAX: {args.max_regressions}",
          file=sys.stderr)
    if regs > args.max_regressions:
        print(f"FAIL: {regs} regressions > threshold {args.max_regressions}",
              file=sys.stderr)
        return 1
    print(f"PASS: {regs} regressions ≤ threshold {args.max_regressions}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
