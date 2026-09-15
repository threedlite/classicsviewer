#!/usr/bin/env python3
"""
Compare Latin interlinear glosses between two states, weighted by how often
each word actually occurs in the corpus.

WHY FREQUENCY WEIGHTING
-----------------------
Sampling entries uniformly hides the failures that matter. Measured on
`lsgloss/ls_glosses.tsv`: its weakest source (`tr`, the dictionary's own <tr>
tag taken verbatim) is 14% of ENTRIES but lands on 44% of running-text TOKENS,
because common words have the longest articles and so the most ways to pick the
wrong part of one. A uniform sample would have reported 86% correct and shown
none of it.

USAGE
    gloss_eval.py capture  <label>            # snapshot current XML glosses
    gloss_eval.py compare  <before> <after>   # diff two snapshots
    gloss_eval.py flag     <label>            # suspicious glosses only

Snapshots are written to latin/tools/snapshots/<label>.json.
"""

import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
XML_DIR = ROOT / "latin" / "interlinear_output"
SNAP_DIR = Path(__file__).resolve().parent / "snapshots"
# Frequencies come from the Latin MODULE db, not the assembled one. The module
# db holds only Latin (43 authors, 4.8M words) so it needs no language join, and
# it is not being rewritten while an assembly runs.
MODULE_DB = ROOT / "latin" / "latin_texts_extended.db"
ASSEMBLED = ROOT / "data-prep" / "perseus_texts_extended.db"

# Each interlinear token is three cells spread over three physical lines:
#
#     | conj ~ SCONJ advmod 5 1 L1 |  | vos |     <- morph of prev token, then SURFACE
#     | **you (pl.), ye** |                        <- GLOSS
#     | tu acc p c pron|nom p c pron ~ PRON ... |  <- morph, then next surface
#
# So the surface is the LAST cell on the line before the gloss line. It cannot
# be found by splitting on "|": morph cells contain "|" internally as an
# alternation separator ("acc p c pron|nom p c pron"). Anchoring to end-of-line
# avoids that entirely.
GLOSS_LINE = re.compile(r"^\s*\|\s*\*\*(.*?)\*\*\s*\|\s*$")
LAST_CELL = re.compile(r"\|\s*([^|]+?)\s*\|\s*(?:</l>)?\s*$")


# --------------------------------------------------------------------------- #
# Suspicious-gloss detectors
#
# These FLAG for review. They do not reject.
#
# The first version of this tried to spot Latin by suffix (-us, -um, -is, -at,
# -are ...). It was useless: English shares every one of those endings, so
# "this", "that", "where", "war, warfare" and "by (agent)" were all reported as
# Latin. Measured on the current build it flagged 8.88% of tokens, and the top
# 50 by frequency were almost entirely correct glosses.
#
# The replacement asks a real question instead of a shape question: is this
# token a word that occurs in OUR Latin corpus and is NOT an English word? That
# needs both lists, so the detectors are built once against the corpus.
# --------------------------------------------------------------------------- #
ENGLISH_DICT = Path("/usr/share/dict/words")
LATIN_MIN_FREQ = 3          # ignore corpus hapaxes; they are often OCR noise
LATIN_SHARE = 0.5           # half the gloss reading as Latin is enough
MAX_SANE_LEN = 60

_ALLCAPS = re.compile(r"\b[A-Z]{3,}\b")
_SENSE_FRAG = re.compile(r"^\s*(\d+\s*\.|[IVXLC]+\s*\.)\s*$")
# L&S section rubrics. Bare "Of "/"With " are NOT here: they open many perfectly
# good glosses ("with respect to which" for quod, 29,888 tokens).
_RUBRIC = re.compile(
    r"^\s*(In gen\.|In partic\.|Absol\.|Transf\.|Trop\.|Lit\.|Meton\.|"
    r"Esp\.|Poet\.|Sc\.|Cf\.|Syn\.|Hence|Hence,)", re.I)
_FORM_TAG = re.compile(
    r"^\s*(gen|dat|acc|abl|voc|nom|perf|imperf|plup|fut|inf|sup|part|comp|superl)"
    r"\s*\.", re.I)
_WORDS = re.compile(r"[A-Za-z]{2,}")
# Latin cited inside brackets is normal and correct: "(alii ... alii)", "(PERS)",
# "(w/GEN)". Only the prose outside them is supposed to be English.
_PARENS = re.compile(r"\([^)]*\)|\[[^\]]*\]")


def _english_variants(w):
    """web2 lists only base forms - it has no "others", "carried", "running".
    Without this backoff every plural in every gloss reads as non-English."""
    yield w
    for suf, subs in (("s", ("",)), ("es", ("", "e")), ("ies", ("y",)),
                      ("ed", ("", "e")), ("ing", ("", "e")),
                      ("er", ("", "e")), ("est", ("", "e")),
                      ("ly", ("",)), ("ness", ("",)), ("men", ("man",))):
        if w.endswith(suf) and len(w) > len(suf) + 1:
            for sub in subs:
                yield w[: len(w) - len(suf)] + sub


class Detectors:
    """Holds the English and Latin vocabularies the flags are tested against."""

    def __init__(self, latin_freq):
        self.english = set()
        if ENGLISH_DICT.exists():
            self.english = {w.strip().lower()
                            for w in ENGLISH_DICT.read_text(errors="ignore").splitlines()
                            if w.strip()}
        else:
            print(f"  ! {ENGLISH_DICT} missing; 'reads-as-latin' disabled",
                  file=sys.stderr)
        self.latin = {w.lower() for w, n in latin_freq.items()
                      if n >= LATIN_MIN_FREQ and len(w) > 1}

    def is_english(self, w):
        return any(v in self.english for v in _english_variants(w))

    def reads_as_latin(self, gloss):
        """True when most of the non-bracketed gloss is corpus Latin, not English.

        Only LOWERCASE tokens can count as Latin. Capitalised ones are almost
        always proper nouns, and a proper noun is a correct gloss for itself:
        "Cicero", "Scipio", "Africa (North)", "Publius (Roman praenomen)" were
        all reported as Latin text before this rule, because web2 has no
        gazetteer. Real Latin leakage is running text and stays lowercase.
        """
        if not self.english:
            return False
        toks = _WORDS.findall(_PARENS.sub(" ", gloss))
        if not toks:
            return False
        lat = [t for t in toks
               if t[0].islower() and t.lower() in self.latin
               and not self.is_english(t.lower())]
        return len(lat) / len(toks) >= LATIN_SHARE

    def flags_for(self, surface, gloss):
        """Reasons this gloss looks wrong. Empty means clean."""
        out = []
        if not gloss or gloss == "???":
            return ["blank"]
        if self.reads_as_latin(gloss):
            out.append("reads-as-latin")
        if _SENSE_FRAG.match(gloss):
            out.append("sense-number-fragment")
        if _RUBRIC.match(gloss):
            out.append("rubric-not-definition")
        if _FORM_TAG.match(gloss):
            out.append("cited-form-not-definition")
        if len(gloss) > MAX_SANE_LEN:
            out.append("too-long")
        if gloss.count("[") != gloss.count("]") or gloss.count("(") != gloss.count(")"):
            out.append("truncated-bracket")
        return out

    def notes_for(self, surface, gloss):
        """Not errors, reported separately so they do not bury real problems.

        Whitaker writes grammatical tags in caps by convention
        ("he/she/it/they (by GENDER/NUMBER)"). And a gloss may legitimately
        repeat its own headword when Latin and English coincide: "six, sex",
        "speaker, orator", "Cicero". An earlier "cites-own-headword" flag fired
        on 244 surfaces, nearly all of them of that kind.
        """
        n = []
        if _ALLCAPS.search(gloss or ""):
            n.append("whitaker-caps-tag")
        if gloss and gloss.strip().lower() == (surface or "").lower():
            n.append("gloss-equals-headword")
        return n


def corpus_frequency():
    """word -> occurrences in the Latin corpus. Empty dict if unavailable."""
    if MODULE_DB.exists():
        con = sqlite3.connect(f"file:{MODULE_DB}?mode=ro", uri=True)
        rows = con.execute(
            "SELECT word, COUNT(*) FROM words GROUP BY word").fetchall()
        con.close()
        return dict(rows)
    if ASSEMBLED.exists():
        con = sqlite3.connect(f"file:{ASSEMBLED}?mode=ro", uri=True)
        rows = con.execute("""
            SELECT wd.word, COUNT(*) FROM words wd
              JOIN books bk ON wd.book_id = bk.id
              JOIN works wk ON bk.work_id = wk.id
              JOIN authors a ON wk.author_id = a.id
            WHERE a.language = 'latin' GROUP BY wd.word""").fetchall()
        con.close()
        return dict(rows)
    print("  ! no Latin db found; frequencies unavailable", file=sys.stderr)
    return {}


def read_xml_glosses():
    """surface -> most common gloss, plus how many tokens carry it."""
    per_surface = {}
    counts = Counter()
    orphans = 0
    files = sorted(XML_DIR.glob("*.perseus-eng99.xml"))
    if not files:
        sys.exit(f"ERROR: no interlinear XMLs in {XML_DIR}")
    for path in files:
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            m = GLOSS_LINE.match(line)
            if not m:
                continue
            gloss = m.group(1).strip()
            prev = lines[i - 1] if i else ""
            sm = LAST_CELL.search(prev)
            if not sm:
                orphans += 1
                continue
            surface = sm.group(1).strip()
            counts[surface] += 1
            per_surface.setdefault(surface, Counter())[gloss] += 1
    if orphans:
        print(f"  ! {orphans:,} glosses had no recoverable surface", file=sys.stderr)
    return {s: c.most_common(1)[0][0] for s, c in per_surface.items()}, counts


def cmd_capture(label):
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    glosses, counts = read_xml_glosses()
    freq = corpus_frequency()
    snap = {
        "label": label,
        "xml_count": len(list(XML_DIR.glob("*.perseus-eng99.xml"))),
        "tokens": sum(counts.values()),
        "glosses": glosses,
        "token_counts": dict(counts),
        "corpus_freq": {w: freq.get(w, freq.get(w.lower(), 0)) for w in glosses},
    }
    out = SNAP_DIR / f"{label}.json"
    out.write_text(json.dumps(snap), encoding="utf-8")
    blank = sum(counts[s] for s, g in glosses.items() if g == "???")
    print(f"  captured '{label}': {len(glosses):,} distinct surfaces, "
          f"{snap['tokens']:,} tokens")
    print(f"  blank (???): {blank:,} ({100*blank/snap['tokens']:.2f}%)")
    print(f"  -> {out}")


def _load(label):
    p = SNAP_DIR / f"{label}.json"
    if not p.exists():
        sys.exit(f"ERROR: no snapshot '{label}' at {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def cmd_compare(before_label, after_label, top=40):
    a, b = _load(before_label), _load(after_label)
    det = Detectors(corpus_frequency())
    ag, bg = a["glosses"], b["glosses"]
    weight = b.get("token_counts", {})

    gained = lost = changed = same = 0
    rows = []
    for s in set(ag) | set(bg):
        w = weight.get(s, a.get("token_counts", {}).get(s, 0))
        old, new = ag.get(s), bg.get(s)
        old_blank = (old is None or old == "???")
        new_blank = (new is None or new == "???")
        if old == new:
            same += w
        elif old_blank and not new_blank:
            gained += w
            rows.append((w, s, old, new, "GAINED"))
        elif new_blank and not old_blank:
            lost += w
            rows.append((w, s, old, new, "LOST"))
        else:
            changed += w
            rows.append((w, s, old, new, "CHANGED"))

    tot = same + gained + lost + changed
    print(f"  {before_label} -> {after_label}, weighted by corpus tokens")
    print(f"    unchanged {same:>10,}")
    print(f"    gained    {gained:>10,}   (??? -> gloss)")
    print(f"    changed   {changed:>10,}")
    print(f"    LOST      {lost:>10,}   <- regressions, must be 0 or explained")
    print(f"    total     {tot:>10,}")

    # newly-flagged glosses are the "obvious wrong entry" signal
    newly = []
    for w, s, old, new, kind in rows:
        if new and new != "???":
            fa = set(det.flags_for(s, old) if old else [])
            fb = set(det.flags_for(s, new))
            if fb - fa - {"blank"}:
                newly.append((w, s, old, new, sorted(fb - fa)))
    newly.sort(key=lambda r: -r[0])
    nw = sum(r[0] for r in newly)
    print(f"\n  newly flagged as suspicious: {len(newly):,} surfaces, "
          f"{nw:,} tokens ({100*nw/max(tot,1):.2f}%)")
    for w, s, old, new, f in newly[:top]:
        print(f"    {w:>7} {s:14s} {str(old)[:26]!r} -> {str(new)[:30]!r}  {','.join(f)}")

    if lost:
        print(f"\n  LOST a gloss (largest first):")
        for w, s, old, new, kind in sorted([r for r in rows if r[4] == "LOST"],
                                           key=lambda r: -r[0])[:top]:
            print(f"    {w:>7} {s:14s} was {str(old)[:44]!r}")

    print(f"\n  biggest changes:")
    for w, s, old, new, kind in sorted([r for r in rows if r[4] == "CHANGED"],
                                       key=lambda r: -r[0])[:top]:
        print(f"    {w:>7} {s:14s} {str(old)[:26]!r} -> {str(new)[:32]!r}")


def cmd_flag(label, top=60):
    snap = _load(label)
    det = Detectors(corpus_frequency())
    weight = snap.get("token_counts", {})
    hits, notes = [], Counter()
    for surface, g in snap["glosses"].items():
        w = weight.get(surface, 0)
        f = [x for x in det.flags_for(surface, g) if x != "blank"]
        if f:
            hits.append((w, surface, g, f))
        for n in det.notes_for(surface, g):
            notes[n] += w
    hits.sort(key=lambda r: -r[0])
    tw = sum(h[0] for h in hits)
    tot = snap["tokens"]
    print(f"  '{label}': {len(hits):,} suspicious surfaces, {tw:,} tokens "
          f"({100*tw/max(tot,1):.2f}% of corpus)")
    by = Counter()
    for w, _, _, fl in hits:
        for f in fl:
            by[f] += w
    for k, n in by.most_common():
        print(f"    {k:26s} {n:,} tokens")
    print("  informational (not errors):")
    for k, n in notes.most_common():
        print(f"    {k:26s} {n:,} tokens")
    print()
    for w, surface, g, f in hits[:top]:
        print(f"    {w:>7} {surface:14s} {g[:46]!r}  {','.join(f)}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "capture":
        cmd_capture(sys.argv[2])
    elif cmd == "compare":
        if len(sys.argv) < 4:
            sys.exit("usage: gloss_eval.py compare <before> <after>")
        cmd_compare(sys.argv[2], sys.argv[3])
    elif cmd == "flag":
        cmd_flag(sys.argv[2])
    else:
        sys.exit(__doc__)
