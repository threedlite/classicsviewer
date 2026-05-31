#!/usr/bin/env python3
"""
Perseus Latin Dependency Treebank (LDT) v2.1 loader.

Walks data-sources/treebank_data/v2.1/Latin/texts/*.xml and builds an
in-memory index from (book_id, line_number) -> LdtSentence -> [LdtWord].
The Latin interlinear generator queries this index per text_lines row;
tokens that match (by NFC surface form, case-insensitive) get LDT-derived
POS / lemma / morph / deprel / head. Tokens that don't match fall through
to Stanza (latin_stanza_nlp.py).

The LDT subdoc carries the canonical citation. Format varies per work
(BOOK.LINE for verse, single int for single-book prose, SECT.SUBSECT for
oratorical chapters, …). A per-work resolver maps (work_id, subdoc) to
(book_suffix, line_number).

The loader supports SENTENCE-RANGE SPANNING: each LDT sentence's words
are attached to every text_line from its start line through the next
sentence's start line - 1 in the same book. This is necessary because
LDT annotates only sentence-start references; the words inside that
sentence belong to every line the sentence runs through.

LDT coverage in v2.1 is small (~12 partial works, ~3000 sentences).
What isn't covered is fallback territory for Stanza.

NOT a standalone script — imported by generate_latin_interlinear.py.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import xml.etree.ElementTree as ET


# --------------------------------------------------------------------------- #
# Perseus 9-character postag → Universal Dependencies POS
# --------------------------------------------------------------------------- #
#
# Position 0 = POS major:
#   n=noun, v=verb, t=participle, a=adjective, d=adverb, c=conjunction,
#   r=preposition, p=pronoun, m=numeral, i=interjection, e=exclamation,
#   u=punctuation, x=irregular
#
# For nouns, position 7 = type:  c=common, p=proper
#   so "n-s---fap-" with pos7='p' → PROPN, pos7='c' → NOUN
#
# Reference: data-sources/treebank_data/v2.1/Latin/Harrington-tagset.pdf
_POS_MAP = {
    "v": "VERB",
    "t": "VERB",       # participles roll up to VERB in UD
    "a": "ADJ",
    "d": "ADV",
    "c": "CCONJ",      # coarse roll-up of conjunctions
    "r": "ADP",
    "p": "PRON",
    "m": "NUM",
    "i": "INTJ",
    "e": "INTJ",
    "u": "PUNCT",
    "x": "X",
}


def perseus_postag_to_upos(postag: str) -> Optional[str]:
    """Map a Perseus 9-character postag to a Universal Dependencies POS.
    Returns None for empty / malformed tags."""
    if not postag or postag == "---------":
        return None
    p0 = postag[0]
    if p0 == "n":
        if len(postag) > 7 and postag[7] == "p":
            return "PROPN"
        return "NOUN"
    return _POS_MAP.get(p0)


# --------------------------------------------------------------------------- #
# subdoc resolvers
# --------------------------------------------------------------------------- #
#
# Each resolver takes a `subdoc` string and returns (book_suffix, line_number)
# or None if the subdoc cannot be aligned. book_suffix is the trailing portion
# of the book_id after the work_id, including the leading dot (e.g. ".006" for
# Aeneid book 6, ".001" for single-book works).


def _book_dot_line(subdoc: str) -> Optional[tuple[str, int]]:
    """BOOK.LINE — Vergil, Caesar, Ovid (taking range start), Tibullus."""
    if not subdoc:
        return None
    head = subdoc.split("-", 1)[0]   # range like "1.163-1.167" → "1.163"
    m = re.match(r"^(\d+)\.(\d+)$", head)
    if not m:
        return None
    return (f".{int(m.group(1)):03d}", int(m.group(2)))


def _single_integer(subdoc: str) -> Optional[tuple[str, int]]:
    """Single integer — Sallust, Vulgate, Phaedrus. Single book (.001), the
    int is the section/verse/fable number."""
    if not subdoc:
        return None
    head = subdoc.split("-", 1)[0]
    m = re.match(r"^(\d+)$", head)
    if not m:
        return None
    return (".001", int(head))


def _book_colon_line(subdoc: str) -> Optional[tuple[str, int]]:
    """BOOK:LINE — Petronius uses colon separator instead of dot."""
    if not subdoc:
        return None
    head = subdoc.split("-", 1)[0]
    m = re.match(r"^(\d+):(\d+)$", head)
    if not m:
        return None
    return (f".{int(m.group(1)):03d}", int(m.group(2)))


def _unalignable(subdoc: str) -> Optional[tuple[str, int]]:
    """For works whose subdoc cannot be deterministically aligned in v1.
    Sentence is dropped — Stanza will provide POS at generation time."""
    return None


# Per-work subdoc resolver, keyed by the file's CTS work id.
#
# v1 alignment scope: ONLY the works whose subdoc → text_lines.line_number
# mapping is mechanical and verified by direct spot-check against the
# extended DB. The rest are intentionally unalignable in v1 — Stanza covers
# them with broad-Latin POS so we don't lose POS coverage, only the
# gold-tag accuracy bump.
#
# Verified-aligning works (smoke test against extended DB confirmed):
#   - phi0448.phi001 (Caesar BG)        BOOK.LINE → matches text_lines exactly
#   - phi0631.phi001 (Sallust Catiline) single int = section → ✓
#   - phi0690.phi003 (Vergil Aeneid)    BOOK.LINE = book.verse → ✓
#   - phi0959.phi006 (Ovid Metamorphoses) BOOK.LINE same shape → ✓
#
# Unalignable in v1 (reasons):
#   - phi0474.phi013 (Cicero):      SECT.SUBSECT doesn't map to line_number
#   - phi0620.phi001 (Tibullus):    BOOK.LINE but Tibullus has 1 book; need
#                                   to confirm line_number matches verse
#   - phi0972.phi001 (Petronius):   subdoc is chapter number (26+) but
#                                   text_lines breaks Satyricon into
#                                   sub-chapter lines; numbering mismatch
#   - phi0975.phi001 (Phaedrus):    BOOK:LINE with colon; book scheme in
#                                   text_lines unverified
#   - phi1221.phi007 (Propertius):  EMPTY subdocs
#   - phi1348.abo012 (Augustine):   single all-range subdoc, no per-sentence
#   - phi1351.phi005 (Tacitus):     EMPTY subdocs
#   - tlg0031.tlg027 (Vulgate):     single int = verse, but text_lines may
#                                   use chapter+verse merged; unverified
#
# Promoting any unalignable work to a real resolver in v2 requires
# spot-verification that subdoc N's first token text equals text_lines
# line_number=N's first token text in the extended DB.
SUBDOC_RESOLVERS: dict[str, "callable"] = {
    # ----- v1 verified aligning works -----
    # Only verse works where text_lines.line_number = canonical verse number.
    # For these the mapping is mechanical: subdoc "BOOK.LINE" maps to
    # book_id `<work_id>.<BOOK 3-digit>` and text_lines.line_number = LINE.
    "phi0690.phi003": _book_dot_line,        # Vergil Aeneid (book 6 covered)
    "phi0959.phi006": _book_dot_line,        # Ovid Metamorphoses (book 1 covered)

    # ----- v1 unalignable: prose, empty subdocs, non-mechanical -----
    # text_lines.line_number for prose is a paragraph counter within the
    # book, NOT the canonical section number. Aligning these requires
    # parsing the inline [N.M] markers embedded in text_lines.line_text
    # and building a canonical-ref → line_number index. v2 work.
    #
    # Caesar BG, Sallust Cat, Cicero, Tibullus, Phaedrus, Petronius, Vulgate
    # all fall here despite having mechanical-looking subdocs — verified by
    # spot-checking that subdoc N's first word does NOT match line N's
    # first word in extended DB.
    #
    # Propertius, Augustine, Tacitus have format-broken subdocs (empty or
    # whole-range).
    "phi0448.phi001": _unalignable,          # Caesar BG     — v2
    "phi0474.phi013": _unalignable,          # Cicero        — v2
    "phi0620.phi001": _unalignable,          # Tibullus      — v2
    "phi0631.phi001": _unalignable,          # Sallust Cat   — v2
    "phi0972.phi001": _unalignable,          # Petronius     — v2
    "phi0975.phi001": _unalignable,          # Phaedrus      — v2
    "phi1221.phi007": _unalignable,          # Propertius    — format-broken
    "phi1348.abo012": _unalignable,          # Augustine     — format-broken
    "phi1351.phi005": _unalignable,          # Tacitus       — empty subdocs
    "tlg0031.tlg027": _unalignable,          # Vulgate       — v2
}


# --------------------------------------------------------------------------- #
# Data shape
# --------------------------------------------------------------------------- #

@dataclass(slots=True)
class LdtWord:
    """One LDT word with everything the interlinear generator needs."""
    sentence_id: int            # within-file sentence number
    word_id: int                # within-sentence word number
    form: str                   # surface form
    form_normalized: str        # NFC, lowercase, punctuation-stripped
    lemma: str                  # LDT-provided lemma (trailing digit stripped)
    postag: str                 # raw Perseus 9-char tag
    upos: Optional[str]         # mapped UD POS, may be None
    deprel: str                 # raw Perseus relation
    head: int                   # within-sentence head id; 0 = root
    work_id: str                # e.g. phi0690.phi003
    book_id: str                # extended-DB book_id, e.g. phi0690.phi003.006
    start_line: int             # subdoc's start line for the parent sentence


@dataclass(slots=True)
class LdtSentence:
    """A whole LDT sentence and its words. The line range it covers is
    [start_line, end_line]; end_line is filled in after all sentences for a
    book have been seen (it's the next sentence's start_line - 1, or the
    sentence's own start_line if it's the last)."""
    sentence_id: int
    work_id: str
    book_id: str
    start_line: int
    end_line: int = -1          # filled by _finalize_book_ranges
    words: list[LdtWord] = field(default_factory=list)


# Strip a trailing digit from LDT lemmas (LDT marks homographs as `for1`,
# `sic1`, etc; the dictionary lookup expects bare lemmas).
_LEMMA_DIGIT_RE = re.compile(r"\d+$")


def _strip_lemma(s: str) -> str:
    return _LEMMA_DIGIT_RE.sub("", s) if s else ""


def _normalize_form(s: str) -> str:
    """NFC, strip combining marks (macrons / diaereses / breves), lowercase,
    strip leading/trailing punctuation. Latin editors mark vowel length
    with macrons (`ā`) or diaeresis (`ï`); LDT itself uses bare ASCII, so
    we strip those marks before matching."""
    if not s:
        return ""
    # NFD decomposes "ï" → "i" + COMBINING DIAERESIS, then we drop the
    # combining marks (category "Mn") and recompose to NFC.
    decomposed = unicodedata.normalize("NFD", s)
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    s = unicodedata.normalize("NFC", stripped)
    s = s.strip(".,;:!?\"'()[]{}«»“”‘’")
    return s.lower()


# --------------------------------------------------------------------------- #
# Loader
# --------------------------------------------------------------------------- #

LDT_DIR_DEFAULT = (
    Path(__file__).resolve().parents[3]
    / "data-sources" / "treebank_data" / "v2.1" / "Latin" / "texts"
)


# URN regex like "urn:cts:latinLit:phi0690.phi003.perseus-lat1" — we want the
# "phi0690.phi003" middle.
_URN_WORK_RE = re.compile(r":(?:latinLit|greekLit):([^.]+\.[^.]+)\.")


def _extract_work_id(document_id: str) -> Optional[str]:
    m = _URN_WORK_RE.search(document_id or "")
    return m.group(1) if m else None


class LdtLoader:
    """Loads all LDT XML files under `ldt_dir` once; offers per-line lookup
    that handles sentence-range spanning."""

    def __init__(self, ldt_dir: Path = LDT_DIR_DEFAULT) -> None:
        self.ldt_dir = Path(ldt_dir)
        # book_id -> sorted list of LdtSentence by start_line
        self._book_sentences: dict[str, list[LdtSentence]] = {}
        # work_id -> stats
        self._stats: dict[str, dict[str, int]] = {}
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        if not self.ldt_dir.is_dir():
            raise FileNotFoundError(f"LDT directory missing: {self.ldt_dir}")
        for xml_path in sorted(self.ldt_dir.glob("*.xml")):
            self._load_file(xml_path)
        # After loading, sort each book's sentences by (start_line,
        # sentence_id) and fill end_line. The covered range for sentence S
        # extends from S.start_line through (start_line of the next sentence
        # whose start_line differs from S.start_line) - 1. Multiple LDT
        # sentences sharing a start_line all get the same end_line — they
        # all belong to the same canonical-line bucket from LDT's POV.
        for book_id, sents in self._book_sentences.items():
            sents.sort(key=lambda s: (s.start_line, s.sentence_id))
            # First pass: for each unique start_line, find the next-different
            # start_line. Easier to walk in reverse and remember "the next
            # different start_line we've seen so far".
            next_diff_start: dict[int, int] = {}
            # Iterate from the highest start_line downward
            seen_next = None
            for s in reversed(sents):
                if seen_next is None or seen_next == s.start_line:
                    # nothing yet, or we're inside a run of same start_line —
                    # we'll fill this on the next distinct-start sentence
                    pass
                next_diff_start.setdefault(s.start_line, seen_next)
                if seen_next is None or s.start_line < seen_next:
                    seen_next = s.start_line
            # next_diff_start[start_line] -> first start_line > start_line
            # (or None for the last bucket). Now compute end_line.
            # Build a sorted unique list of start_lines for lookup:
            unique_starts = sorted({s.start_line for s in sents})
            start_index = {ls: i for i, ls in enumerate(unique_starts)}
            for s in sents:
                idx = start_index[s.start_line]
                if idx + 1 < len(unique_starts):
                    nxt = unique_starts[idx + 1]
                    s.end_line = nxt - 1
                else:
                    s.end_line = s.start_line   # last bucket, conservative
        self._loaded = True

    def _load_file(self, xml_path: Path) -> None:
        try:
            tree = ET.parse(xml_path)
        except ET.ParseError as e:
            print(f"[ldt] WARN: ParseError in {xml_path.name}: {e}")
            return
        root = tree.getroot()
        for sentence in root.iter("sentence"):
            self._load_sentence(sentence)

    def _load_sentence(self, sentence_el) -> None:
        document_id = sentence_el.get("document_id", "")
        subdoc = sentence_el.get("subdoc", "")
        try:
            sent_id = int(sentence_el.get("id", "0"))
        except ValueError:
            sent_id = 0

        work_id = _extract_work_id(document_id)
        if not work_id:
            return

        stats = self._stats.setdefault(
            work_id, {"sentences": 0, "dropped": 0, "kept": 0}
        )
        stats["sentences"] += 1

        resolver = SUBDOC_RESOLVERS.get(work_id)
        if resolver is None:
            stats["dropped"] += 1
            return
        resolved = resolver(subdoc)
        if resolved is None:
            stats["dropped"] += 1
            return
        book_suffix, line_number = resolved
        book_id = f"{work_id}{book_suffix}"

        sent = LdtSentence(
            sentence_id=sent_id,
            work_id=work_id,
            book_id=book_id,
            start_line=line_number,
        )

        for w in sentence_el.iter("word"):
            form = w.get("form", "") or ""
            postag = w.get("postag", "") or ""
            try:
                wid = int(w.get("id", "0"))
            except ValueError:
                wid = 0
            try:
                head = int(w.get("head", "0"))
            except ValueError:
                head = 0
            sent.words.append(
                LdtWord(
                    sentence_id=sent_id,
                    word_id=wid,
                    form=form,
                    form_normalized=_normalize_form(form),
                    lemma=_strip_lemma(w.get("lemma", "") or ""),
                    postag=postag,
                    upos=perseus_postag_to_upos(postag),
                    deprel=w.get("relation", "") or "",
                    head=head,
                    work_id=work_id,
                    book_id=book_id,
                    start_line=line_number,
                )
            )

        if sent.words:
            self._book_sentences.setdefault(book_id, []).append(sent)
            stats["kept"] += 1
        else:
            stats["dropped"] += 1

    # ----- query API used by the generator -----

    def lookup_sentences(
        self, book_id: str, line_number: int
    ) -> list[LdtSentence]:
        """Return ALL LDT sentences whose covered line range contains
        `line_number`. Empty list if none. Multiple LDT sentences can share
        the same start_line (and hence same covered range), so this returns
        the full set rather than picking one arbitrarily."""
        sents = self._book_sentences.get(book_id)
        if not sents:
            return []
        # Linear scan within the sorted list: collect every sentence whose
        # [start_line, end_line] covers `line_number`. With per-book sentence
        # counts in the hundreds to low thousands this is fast enough and
        # keeps the "multiple sentences per line" semantics correct.
        out: list[LdtSentence] = []
        for s in sents:
            if s.start_line > line_number:
                break
            if s.end_line >= line_number:
                out.append(s)
        return out

    def lookup_token(
        self, book_id: str, line_number: int, surface: str
    ) -> Optional[LdtWord]:
        """Find an LDT word whose normalized form matches `surface` across
        ALL sentences covering this (book_id, line_number). Tries exact
        NFC-lowercase first, then enclitic-strip on the surface side
        (text_lines tends to glue enclitics; LDT splits them)."""
        sents = self.lookup_sentences(book_id, line_number)
        if not sents:
            return None
        target = _normalize_form(surface)
        if not target:
            return None
        for s in sents:
            for w in s.words:
                if w.form_normalized == target:
                    return w
        # Try stripping enclitics from the target.
        for enc in ("que", "ne", "ve"):
            if target.endswith(enc) and len(target) > len(enc):
                stripped = target[: -len(enc)]
                for s in sents:
                    for w in s.words:
                        if w.form_normalized == stripped:
                            return w
        return None

    # ----- diagnostics -----

    def coverage_stats(self) -> dict[str, dict[str, int]]:
        out: dict[str, dict] = {}
        for w, s in self._stats.items():
            out[w] = dict(s)
        for book_id, sents in self._book_sentences.items():
            work_id = ".".join(book_id.split(".")[:2])
            o = out.setdefault(work_id, {"sentences": 0, "dropped": 0, "kept": 0})
            o.setdefault("books", set())
            o["books"].add(book_id)
            o.setdefault("covered_lines", 0)
            for s in sents:
                o["covered_lines"] += (s.end_line - s.start_line + 1)
        for v in out.values():
            if "books" in v:
                v["books"] = len(v["books"])
        return out


if __name__ == "__main__":
    loader = LdtLoader()
    loader.load()
    stats = loader.coverage_stats()
    total_sents = sum(s["sentences"] for s in stats.values())
    total_kept = sum(s["kept"] for s in stats.values())
    total_dropped = sum(s["dropped"] for s in stats.values())
    print(f"Loaded {total_sents:,} sentences  kept={total_kept:,}  "
          f"dropped={total_dropped:,}")
    print(f"Total (book_id) → sentence-list buckets: "
          f"{len(loader._book_sentences):,}")
    for work_id, s in sorted(stats.items()):
        print(f"  {work_id}: {s}")
