#!/usr/bin/env python3
"""
Load Lewis & Short, *A Latin Dictionary* (Clarendon Press, 1879) into
`dictionary_entries`.

Source: latin/data-sources/lexica/CTS_XML_TEI/perseus/pdllex/lat/ls/
        lat.ls.perseus-eng2.xml   (CC BY-SA 4.0, PerseusDL/lexica)

See latin/LEWIS_SHORT_PLAN.md for the full design and the measurements behind
every constant here. The three decisions that shape this module:

  * ONE ROW PER <orth> SPELLING, not one per entry (§5.4). Entries carry up to
    20 non-alt <orth> elements; emitting only the first would drop 16,192
    spellings, including forms readers actually type ("Hispania" is the second
    orth of the entry keyed "Hispani").

    With ONE exception: an <orth> beginning with a hyphen is a CONTINUATION,
    the abbreviated tail of the variant ("Parnasus" then "-os"), not a word.
    917 such elements produce 366 headwords, 115 of which shadow real and very
    common entries -- "sum" resolved to the article for "retroversus". See
    _is_continuation_orth.

  * GRADUATED LENGTH CAP at 15,000 chars (§7.3 D2). The Android dictionary
    screen renders a TextView with an O(n^2) word-wrapping pass; the longest
    thing it handles today is a 13,583-char Greek entry. Articles over the cap
    lose their <cit> citations first, and only then get hard-truncated.

  * BRIDGE-A (§5.2.1). `lemma_map.lemma` holds Whitaker *stems* while L&S
    headwords are full dictionary forms, so inflected surface tokens cannot
    reach L&S on their own. An extra row under the Whitaker stem fixes that
    without touching `lemma_map`.

No word-specific logic anywhere, per CLAUDE.md. Every rule is a class rule.
"""

import collections
import html
import re
import sqlite3
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

try:
    from .latin_normalization import (
        normalize_latin_headword,
        assert_ascii_headwords,
    )
except ImportError:  # direct script / sys.path import
    from latin_normalization import (
        normalize_latin_headword,
        assert_ascii_headwords,
    )

SOURCE_NAME = "Lewis-Short"

# Default source path, relative to latin/ (this file lives in latin/build_modules/).
_DEFAULT_XML = (
    Path(__file__).resolve().parent.parent
    / "data-sources" / "lexica" / "CTS_XML_TEI" / "perseus" / "pdllex"
    / "lat" / "ls" / "lat.ls.perseus-eng2.xml"
)

# Measured invariants of the source file. The loader asserts these so a swapped
# or truncated source fails loudly instead of silently shipping less (CLAUDE.md:
# no silent failures). Note the sibling -eng1.xml in the same directory: taking
# an explicit path and checking the count is what stops it being picked up.
EXPECTED_ENTRIES = 51643
EXPECTED_SENSES = 101982

# §7.3 D2. Just above the 13,583-char Greek Cunliffe entry the app renders today.
ENTRY_CHAR_CAP = 15000
TRUNCATION_MARKER = " […truncated]"

_LOCAL = lambda tag: tag.split("}")[-1]  # noqa: E731  strip XML namespace

# L&S lists alternative spellings by CONTINUATION: an entry gives its head form
# in full, then abbreviates the variants to the differing tail, marked with a
# leading hyphen.
#
#     <orth>rē^trō-versus</orth> <orth>-sum</orth> <orth>-vorsus</orth>
#     <orth>Parnāsus</orth>      <orth>-os</orth>
#
# "-sum" is not a Latin word; it is the tail of "retroversum". Treating it as a
# standalone headword mints garbage keys AND collides with real, very common
# words: 1,819 such <orth> elements produce 366 headwords, of which 115 shadow
# genuine entries (sum, os, us, um, is, es, a, e, on, ius). The measured damage
# is not subtle -- "sum", the commonest verb in Latin, resolved to the article
# for "retroversus" and glossed as "turned back or backwards".
#
# We cannot splice the tail back on reliably: the hyphen marks where the variant
# diverges, but the number of head characters it replaces is not encoded, and
# guessing it would be invention. So these are skipped as HEADWORDS. Nothing is
# hidden from the reader -- the full spelling list, fragments included, is
# rendered verbatim in the entry's orthography line by _render_entry().
#
# This is a markup-convention rule keyed on a closed character class (the
# leading hyphen), not a vocabulary list. Per CLAUDE.md, no word-specific fixes.
_CONTINUATION_PREFIXES = (
    "-",       # HYPHEN-MINUS
    "\u2010",  # HYPHEN
    "\u2011",  # NON-BREAKING HYPHEN
    "\u2013",  # EN DASH
    "\u2014",  # EM DASH
    "\u00ad",  # SOFT HYPHEN
)


def _is_continuation_orth(raw: str) -> bool:
    """True if this <orth> is an abbreviated variant tail, not a headword."""
    return raw.lstrip().startswith(_CONTINUATION_PREFIXES)



# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #

class LsEntry:
    """One <entryFree>: its spellings and its rendered article."""

    __slots__ = ("key", "spellings", "html", "plain", "dropped_citations",
                 "truncated")

    def __init__(self, key, spellings, html_, plain, dropped_citations, truncated):
        self.key = key
        self.spellings = spellings          # [(normalised, raw, is_alt)]
        self.html = html_
        self.plain = plain
        self.dropped_citations = dropped_citations
        self.truncated = truncated


def _text_of(el) -> str:
    """Flattened text of an element, whitespace-collapsed."""
    return " ".join("".join(el.itertext()).split())


def _render_entry(entry_el, drop_citations: bool) -> Tuple[str, str]:
    """Render one <entryFree> to (html, plain).

    The Android and iOS dictionary views BOTH strip every tag except <br> and
    </p> (DictionaryTextFormatter.kt:119-134, ImprovedWordDetailView.swift:778).
    So sense hierarchy has to survive as *literal text* — explicit numerals and
    leading spaces — not as markup. Nested <ol>/<li> would render as one
    unbroken paragraph on both platforms.
    """
    parts_html: List[str] = []
    parts_plain: List[str] = []

    # Leading orthography line, in its typographic form (macrons intact) —
    # this is the only place the reader sees vowel quantities, since `headword`
    # is normalised to ASCII for joining.
    orths = [_text_of(o) for o in entry_el.iter()
             if _LOCAL(o.tag) == "orth" and _text_of(o)]
    if orths:
        head = ", ".join(dict.fromkeys(orths))  # dedupe, preserve order
        parts_html.append(f"<b>{html.escape(head)}</b>")
        parts_plain.append(head)

    senses = [s for s in entry_el.iter() if _LOCAL(s.tag) == "sense"]

    if not senses:
        # 6,657 entries (12.9%) carry no <sense> at all — the definition sits
        # directly in <entryFree>. Without this branch they would render empty.
        body = _entry_body_text(entry_el, drop_citations)
        if body:
            parts_html.append(f"<br>{html.escape(body)}")
            parts_plain.append(body)
        return "".join(parts_html), "\n".join(parts_plain)

    for sense in senses:
        level = sense.get("level") or "1"
        n = (sense.get("n") or "").strip()
        try:
            depth = max(1, min(5, int(level)))
        except ValueError:
            depth = 1
        indent = "  " * (depth - 1)
        label = f"{n}. " if n else ""
        body = _sense_body_text(sense, drop_citations)
        if not body and not label:
            continue
        line_plain = f"{indent}{label}{body}".rstrip()
        parts_plain.append(line_plain)
        parts_html.append(
            "<br>" + "&nbsp;" * (2 * (depth - 1))
            + (f"<b>{html.escape(label)}</b>" if label else "")
            + html.escape(body)
        )

    return "".join(parts_html), "\n".join(parts_plain)


def _collect_text(el, drop_citations: bool, skip_nested_senses: bool) -> str:
    out: List[str] = []
    if el.text:
        out.append(el.text)
    for child in el:
        tag = _LOCAL(child.tag)
        if skip_nested_senses and tag == "sense":
            pass  # rendered as its own line
        elif tag == "orth" and not out:
            pass  # already emitted as the headword line
        elif drop_citations and tag == "cit":
            pass  # §7.3 D2 step 2
        else:
            out.append(_collect_text(child, drop_citations, skip_nested_senses))
        if child.tail:
            out.append(child.tail)
    return " ".join(" ".join(out).split())


def _sense_body_text(sense_el, drop_citations: bool) -> str:
    return _collect_text(sense_el, drop_citations, skip_nested_senses=True)


def _entry_body_text(entry_el, drop_citations: bool) -> str:
    return _collect_text(entry_el, drop_citations, skip_nested_senses=True)


def parse_lewis_short(xml_path: Path, stats: Dict[str, int]) -> Iterable[LsEntry]:
    """Stream <entryFree> elements, rendering each with the graduated cap."""
    for _event, el in ET.iterparse(str(xml_path), events=("end",)):
        if _LOCAL(el.tag) != "entryFree":
            continue

        stats["entries"] += 1
        stats["senses"] += sum(1 for s in el.iter() if _LOCAL(s.tag) == "sense")

        spellings: List[Tuple[str, str, bool]] = []
        for o in el.iter():
            if _LOCAL(o.tag) != "orth":
                continue
            raw = _text_of(o)
            if not raw:
                continue
            # Abbreviated variant tail ("-sum"), not a headword. See
            # _is_continuation_orth. Still rendered in the orthography line.
            if _is_continuation_orth(raw):
                stats["spellings_continuation_skipped"] += 1
                continue
            norm = normalize_latin_headword(raw)
            if not norm:
                stats["spellings_empty_after_norm"] += 1
                continue
            spellings.append((norm, raw, o.get("type") == "alt"))

        if not spellings:
            stats["entries_without_usable_orth"] += 1
            el.clear()
            continue

        # Graduated cap (§7.3 D2).
        html_, plain = _render_entry(el, drop_citations=False)
        dropped = truncated = False
        if len(plain) > ENTRY_CHAR_CAP:
            html_, plain = _render_entry(el, drop_citations=True)
            dropped = True
            stats["capped_citations_dropped"] += 1
            if len(plain) > ENTRY_CHAR_CAP:
                plain = plain[:ENTRY_CHAR_CAP] + TRUNCATION_MARKER
                html_ = html_[:ENTRY_CHAR_CAP] + html.escape(TRUNCATION_MARKER)
                truncated = True
                stats["capped_hard_truncated"] += 1

        yield LsEntry(el.get("key"), spellings, html_, plain, dropped, truncated)
        el.clear()


# --------------------------------------------------------------------------- #
# Bridge-A
# --------------------------------------------------------------------------- #

def _build_bridge(cursor, normalised_headwords: Iterable[str]) -> Dict[str, set]:
    """Map Whitaker stem -> {L&S normalised headword} via `lemma_map.word_form`.

    Whitaker's inflection engine emits the dictionary form among the word_forms
    it generates, so an L&S headword is usually sitting in `word_form` already;
    joining through it yields the stem the app will actually look up. Derived
    entirely from data already in the DB — no rules, no lists.
    """
    wanted = set(normalised_headwords)
    stem_to_headwords: Dict[str, set] = collections.defaultdict(set)
    cursor.execute("SELECT word_form, lemma FROM lemma_map")
    for word_form, lemma in cursor:
        if word_form in wanted and lemma != word_form:
            stem_to_headwords[lemma].add(word_form)
    return stem_to_headwords


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def load_lewis_short(cursor, ls_xml_path: Optional[Path] = None) -> Dict[str, int]:
    """Insert L&S into `dictionary_entries`. Returns a stats dict.

    Fails the build loudly on a missing/unparseable source, an unexpected entry
    count, non-ASCII residue, or bridge coverage below threshold.
    """
    xml_path = Path(ls_xml_path) if ls_xml_path else _DEFAULT_XML
    if not xml_path.exists():
        raise FileNotFoundError(
            f"Lewis & Short source not found: {xml_path}\n"
            "Clone it first (BUILD.md Step 2):\n"
            "  cd latin/data-sources && "
            "git clone --depth 1 https://github.com/PerseusDL/lexica.git"
        )

    print(f"  Source: {xml_path}")
    stats: Dict[str, int] = collections.Counter()

    rows: List[Tuple[str, str, str, str, str, str]] = []
    all_norm: List[str] = []
    headword_to_rowidx: Dict[str, List[int]] = collections.defaultdict(list)

    for entry in parse_lewis_short(xml_path, stats):
        for norm, _raw, is_alt in entry.spellings:
            all_norm.append(norm)
            headword_to_rowidx[norm].append(len(rows))
            rows.append((norm, norm, "latin", "", entry.html, entry.plain))
            stats["rows_alt" if is_alt else "rows_primary"] += 1

    # --- assertions on the source ------------------------------------------
    if stats["entries"] != EXPECTED_ENTRIES:
        raise ValueError(
            f"Lewis & Short: expected {EXPECTED_ENTRIES} <entryFree> entries, "
            f"found {stats['entries']}. Wrong source file (note the sibling "
            f"lat.ls.perseus-eng1.xml) or a truncated download."
        )
    if stats["senses"] != EXPECTED_SENSES:
        raise ValueError(
            f"Lewis & Short: expected {EXPECTED_SENSES} <sense> elements, "
            f"found {stats['senses']}."
        )
    assert_ascii_headwords(all_norm, "Lewis & Short headwords")

    print(f"  Parsed {stats['entries']:,} entries / {stats['senses']:,} senses")
    print(f"  Spellings: {stats['rows_primary']:,} primary + "
          f"{stats['rows_alt']:,} alt = {len(rows):,} rows")
    print(f"  Length cap ({ENTRY_CHAR_CAP:,} chars): "
          f"{stats['capped_citations_dropped']} entries lost citations, "
          f"{stats['capped_hard_truncated']} hard-truncated")
    if stats["spellings_continuation_skipped"]:
        print(f"  Skipped {stats['spellings_continuation_skipped']:,} continuation "
              f"<orth> fragments (\"-sum\", \"-os\"): abbreviated variant tails, "
              f"not headwords")
    if stats["spellings_empty_after_norm"]:
        print(f"  Skipped {stats['spellings_empty_after_norm']} spellings that "
              f"normalise to empty (editorial marks only)")
    if stats["entries_without_usable_orth"]:
        print(f"  Skipped {stats['entries_without_usable_orth']} entries with "
              f"no usable <orth>")

    # --- Bridge-A -----------------------------------------------------------
    print("  Building stem bridge (Bridge-A)...")
    stem_to_headwords = _build_bridge(cursor, headword_to_rowidx.keys())

    bridge_rows: List[Tuple[str, str, str, str, str, str]] = []
    for stem, headwords in stem_to_headwords.items():
        for hw in headwords:
            for idx in headword_to_rowidx[hw]:
                _, _, lang, xml_col, html_col, plain_col = rows[idx]
                bridge_rows.append((stem, stem, lang, xml_col, html_col, plain_col))

    cursor.execute("SELECT COUNT(DISTINCT lemma) FROM lemma_map")
    total_lemmas = cursor.fetchone()[0] or 0
    direct = set(headword_to_rowidx) & {
        r[0] for r in cursor.execute("SELECT DISTINCT lemma FROM lemma_map")
    }
    reachable = set(stem_to_headwords) | direct
    coverage = 100.0 * len(reachable) / total_lemmas if total_lemmas else 0.0

    print(f"  Bridge: {len(stem_to_headwords):,} stems bridged, "
          f"{len(bridge_rows):,} alias rows")
    print(f"  Lemma-path coverage: {len(reachable):,}/{total_lemmas:,} "
          f"= {coverage:.1f}%")
    if coverage < 65.0:
        raise ValueError(
            f"Lewis & Short bridge coverage {coverage:.1f}% is below the 65% "
            f"floor (measured baseline 73.3%). The normaliser has probably "
            f"regressed — check latin_normalization.py before proceeding."
        )

    # --- insert -------------------------------------------------------------
    all_rows = rows + bridge_rows
    cursor.executemany(
        "INSERT INTO dictionary_entries "
        "(headword, headword_normalized_ultra, language, entry_xml, "
        " entry_html, entry_plain, source) VALUES (?, ?, ?, ?, ?, ?, "
        f"'{SOURCE_NAME}')",
        all_rows,
    )
    print(f"  Inserted {len(all_rows):,} Lewis & Short rows "
          f"({len(rows):,} entry + {len(bridge_rows):,} bridge)")

    stats["rows_bridge"] = len(bridge_rows)
    stats["rows_total"] = len(all_rows)
    stats["bridge_coverage_pct"] = round(coverage, 1)
    return dict(stats)


def backfill_whitaker_ultra(cursor) -> int:
    """Populate `headword_normalized_ultra` for existing Latin Whitaker rows.

    Nothing reads it for Latin today (the ultra fallback in PerseusRepository is
    Greek-gated), but it is the correct value and costs nothing. Scoped to
    language='latin' — an unscoped UPDATE would rewrite Greek's 62,809
    populated values.
    """
    cursor.execute(
        "SELECT id, headword FROM dictionary_entries "
        "WHERE language = 'latin' AND source LIKE 'Whitaker%'"
    )
    updates = [
        (normalize_latin_headword(hw), rowid)
        for rowid, hw in cursor.fetchall()
    ]
    cursor.executemany(
        "UPDATE dictionary_entries SET headword_normalized_ultra = ? WHERE id = ?",
        updates,
    )
    return len(updates)
