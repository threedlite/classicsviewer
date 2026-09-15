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
import sqlite3
import unicodedata
from collections import Counter, defaultdict
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
# Actually enabled below (see SUBDOC_RESOLVERS) — TWO works, not four:
#   - phi0690.phi003 (Vergil Aeneid)      BOOK.LINE = book.verse
#   - phi0959.phi006 (Ovid Metamorphoses) BOOK.LINE same shape
#
# Caesar BG and Sallust Catiline were listed here as "verified-aligning" while
# the resolver table below mapped them to _unalignable, and the note under that
# table says they were verified NOT to align. The two claims contradicted each
# other; the code has always followed the second. Corrected rather than
# resolved in favour of either, because see the warning below.
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
# ⚠ THE SPOT-CHECK DESCRIBED ABOVE DOES NOT WORK. Do not promote a work on
# the strength of it.
#
# "subdoc N's first token equals line N's first token" fails on works that
# demonstrably DO align: measured over the first 40 subdocs of each file, the
# Aeneid scores 8% and Ovid 68%, yet both are enabled and between them supply
# every gold tag the build has. The reason is in the SENTENCE-RANGE SPANNING
# note at the top of this file — LDT records the line a sentence STARTS on, and
# in verse a sentence usually starts mid-line, so its first word is not the
# line's first word. A low score means "sentences start mid-line", not
# "misaligned".
#
# A valid promotion test has to compare the whole token multiset of the
# sentence against the span of lines it covers, not first-token against
# first-token. Until someone writes that, the resolver table stays as it is:
# a wrong resolver silently attaches gold POS and lemmas to the wrong words,
# which is worse than falling back to Stanza.
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


class LdtLexicon:
    """Surface form -> lemma, learned from every LDT file at once.

    The per-line LdtLoader below can only apply treebank data to lines it can
    align to a (book_id, line_number). That reaches 0.14% of Latin corpus
    tokens, because `text_lines.line_number` is a paragraph counter for most
    works while LDT's `subdoc` is a canonical citation.

    But a surface-form -> lemma mapping is not location-dependent. "oris ->
    ora", annotated by hand in Aeneid 6, is just as true in Aeneid 1. Reading
    all 12 files as one lexicon gives 67,108 tokens over 18,897 distinct forms,
    83% of which have exactly one lemma.

    Corpus coverage by agreement threshold (measured over 4,813,689 tokens):

        100% (unambiguous)   14.8%
         90%                 19.7%
         80%                 27.9%     <- default
         75%                 36.6%
         50% (plain majority) 60.7%

    The default of 0.8 includes `oris` (ora1 4x vs os1 1x = 80%) and excludes
    `ora` itself (os1 12x vs ora1 3x = 75%), where the majority reading is
    wrong in some contexts. Raising coverage past this trades accuracy for
    reach; it is a threshold, not a word list.

    This does NOT override in-context treebank data - LdtLoader still wins
    where it covers a line. It only replaces Stanza's guess elsewhere.
    """

    def __init__(self, ldt_dir: Path = LDT_DIR_DEFAULT,
                 min_agreement: float = 0.8) -> None:
        self.ldt_dir = Path(ldt_dir)
        self.min_agreement = min_agreement
        self._lemma: dict[str, str] = {}
        # surface -> [(lemma, upos, share)] sorted by share desc, for the
        # dual-gloss path: a form like `ora` is annotated `os` (mouth) 81% and
        # `ora` (shore) 19%, and showing both is more use to a reader than
        # silently picking the majority.
        self._readings: dict[str, list[tuple[str, str, float]]] = {}
        self._loaded = False
        self.stats: dict[str, int] = {}

    def load(self) -> None:
        if self._loaded:
            return
        if not self.ldt_dir.is_dir():
            raise FileNotFoundError(f"LDT directory missing: {self.ldt_dir}")
        counts: dict[str, Counter] = defaultdict(Counter)
        pos_counts: dict[str, Counter] = defaultdict(Counter)
        tokens = 0
        for xml_path in sorted(self.ldt_dir.glob("*.xml")):
            try:
                root = ET.parse(str(xml_path)).getroot()
            except ET.ParseError as exc:
                raise ValueError(f"LDT file unparseable: {xml_path}: {exc}")
            for w in root.iter("word"):
                form = _normalize_form(w.get("form") or "")
                lemma = _strip_lemma((w.get("lemma") or "").strip())
                postag = w.get("postag") or ""
                if not form or not lemma or postag[:1] == "u":
                    continue
                counts[form][lemma] += 1
                upos = perseus_postag_to_upos(postag)
                if upos:
                    pos_counts[form][(lemma, upos)] += 1
                tokens += 1
        kept = 0
        for form, c in counts.items():
            top, n = c.most_common(1)[0]
            if n / sum(c.values()) >= self.min_agreement:
                self._lemma[form] = top
                kept += 1
        for form, c in pos_counts.items():
            total = sum(c.values())
            self._readings[form] = [
                (lem, up, n / total) for (lem, up), n in c.most_common(3)
            ]
        self.stats = {
            "tokens": tokens,
            "forms": len(counts),
            "kept": kept,
            "min_agreement_pct": int(self.min_agreement * 100),
        }
        self._loaded = True

    def readings_for(self, surface: str) -> list[tuple[str, str, float]]:
        """Every attested (lemma, POS, share) for this form, most common first.

        Used to show both readings of a genuinely ambiguous form. Empty list if
        LDT has not seen it.
        """
        if not self._loaded:
            self.load()
        return self._readings.get(_normalize_form(surface), [])

    def lemma_for(self, surface: str) -> Optional[str]:
        """Hand-annotated lemma for this surface form, or None if LDT has not
        seen it or its annotators disagree beyond the threshold."""
        if not self._loaded:
            self.load()
        return self._lemma.get(_normalize_form(surface))


class LdtLoader:
    """Loads all LDT XML files under `ldt_dir` once; offers per-line lookup
    that handles sentence-range spanning."""

    # Content alignment. A sentence is located by finding its own words in the
    # work's text, not by trusting the subdoc citation.
    #
    # The subdoc route reaches 2 works of 12. Measured 2026-09-03 with a test
    # that scores the two known-good works correctly (Aeneid 0.99, Ovid 0.90 --
    # the test the file used to prescribe scored the Aeneid at 0.08): Tibullus,
    # Sallust, Petronius and Phaedrus sit at chance level, so their subdocs
    # genuinely do not map to line_number. Their TEXT does. Matching on content
    # instead reaches 38,011 gold words against 5,143, with zero ambiguous
    # matches across the corpus.
    _NGRAM = 5              # candidate key length
    _MIN_COVER = 0.90       # fraction of the sentence that must be recovered
    _MAX_GAP = 6            # tokens skipped while matching (editions differ)
    _RIVAL_DIST = 10        # a second match this far away makes it ambiguous

    def __init__(self, ldt_dir: Path = LDT_DIR_DEFAULT,
                 db_path: Optional[str] = None) -> None:
        self.ldt_dir = Path(ldt_dir)
        self.db_path = db_path
        # book_id -> sorted list of LdtSentence by start_line
        self._book_sentences: dict[str, list[LdtSentence]] = {}
        # work_id -> stats
        self._stats: dict[str, dict[str, int]] = {}
        # work_id -> (tokens, positions, ngram index); built on first use
        self._work_index: dict[str, Optional[tuple]] = {}
        self._loaded = False

    # ----- content alignment -----

    def _index_work(self, work_id: str):
        """(tokens, positions, ngram_index) for a work, or None if unavailable.

        `positions[i]` is the (book_id, line_number) the i-th token came from,
        so a matched span yields an exact line range instead of the
        next-sentence-start guess the subdoc route has to make.
        """
        if work_id in self._work_index:
            return self._work_index[work_id]
        if not self.db_path:
            self._work_index[work_id] = None
            return None
        try:
            con = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        except sqlite3.Error:
            self._work_index[work_id] = None
            return None
        toks: list[str] = []
        pos: list[tuple[str, int]] = []
        try:
            rows = con.execute(
                "SELECT tl.book_id, tl.line_number, tl.line_text "
                "FROM text_lines tl JOIN books b ON tl.book_id = b.id "
                "WHERE b.work_id = ? ORDER BY tl.book_id, tl.line_number",
                (work_id,)).fetchall()
        except sqlite3.Error:
            rows = []
        finally:
            con.close()
        for book_id, line_number, line_text in rows:
            # Caesar carries a canonical "[1.1]" prefix on most lines; it is
            # citation apparatus, not text, and would pollute the match.
            body = re.sub(r"^\[[^\]]*\]\s*", "", line_text or "")
            for w in re.findall(r"[A-Za-z\u00C0-\u024F]+", body):
                n = _normalize_form(w)
                if n:
                    toks.append(n)
                    pos.append((book_id, line_number))
        if len(toks) < self._NGRAM:
            self._work_index[work_id] = None
            return None
        ix: dict[tuple, list[int]] = {}
        k = self._NGRAM
        for i in range(len(toks) - k + 1):
            ix.setdefault(tuple(toks[i:i + k]), []).append(i)
        self._work_index[work_id] = (toks, pos, ix)
        return self._work_index[work_id]

    @staticmethod
    def _rejoin_enclitics(forms: list[str]) -> list[str]:
        """LDT splits `classique` into `classi` + `-que`; the text has one word."""
        out: list[str] = []
        for f in forms:
            if f.startswith("-") and out:
                out[-1] = out[-1] + f[1:]
            else:
                out.append(f)
        return [_normalize_form(x) for x in out if _normalize_form(x)]

    def _cover(self, sent_toks, toks, start) -> int:
        """Tokens of the sentence recovered in order from `start`."""
        i = start
        hit = 0
        for t in sent_toks:
            j = i
            while j < min(i + self._MAX_GAP, len(toks)):
                if toks[j] == t:
                    hit += 1
                    i = j + 1
                    break
                j += 1
        return hit

    def _locate(self, work_id: str, sent_toks: list[str]):
        """(book_id, first_line, last_line) for this sentence, or None.

        Requires the whole sentence, not a keyword hit: >= _MIN_COVER of its
        tokens recovered in order, and no rival position _RIVAL_DIST or more
        tokens away scoring as well (so a repeated formula cannot land on the
        wrong passage).
        """
        idx = self._index_work(work_id)
        if not idx or len(sent_toks) < self._NGRAM + 2:
            return None
        toks, pos, ix = idx
        k = self._NGRAM
        cands: set[int] = set()
        for i in range(0, min(len(sent_toks) - k, 12)):
            for p in ix.get(tuple(sent_toks[i:i + k]), []):
                cands.add(max(0, p - i))
        if not cands:
            return None
        scored = sorted(((c, self._cover(sent_toks, toks, c)) for c in cands),
                        key=lambda kv: -kv[1])
        best, hit = scored[0]
        if hit / len(sent_toks) < self._MIN_COVER:
            return None
        for c, h in scored[1:]:
            if (h / len(sent_toks) >= self._MIN_COVER
                    and abs(c - best) >= self._RIVAL_DIST):
                return None                      # ambiguous, refuse
        end = min(best + int(len(sent_toks) * 1.5), len(toks) - 1)
        book_id, first_line = pos[best]
        last_line = first_line
        for j in range(best, end + 1):
            if pos[j][0] != book_id:
                break
            last_line = pos[j][1]
        return (book_id, first_line, last_line)

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
                if s.end_line >= 0:
                    continue        # exact range from the content match
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

        # Content alignment first. The subdoc resolvers stay as a fallback so
        # that nothing which aligns today can be lost: the Aeneid and Ovid
        # resolve mechanically, and short sentences (< _NGRAM + 2 tokens) are
        # below the content matcher's evidence threshold.
        forms = [w.get("form", "") or "" for w in sentence_el.iter("word")]
        located = self._locate(work_id, self._rejoin_enclitics(forms))
        end_line = -1
        if located is not None:
            book_id, line_number, end_line = located
            stats["by_content"] = stats.get("by_content", 0) + 1
        else:
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
            stats["by_subdoc"] = stats.get("by_subdoc", 0) + 1

        sent = LdtSentence(
            sentence_id=sent_id,
            work_id=work_id,
            book_id=book_id,
            start_line=line_number,
            end_line=end_line,
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
