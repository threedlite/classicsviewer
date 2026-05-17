"""Compare canonical-extracted vs DB-reconstructed text. Classify mismatches.

Two-level comparison:

1. **Whole-text hash** (the integrity check): concatenate every section's text
   in document order on each side, hash the result, compare. This catches
   drops/dups/reorders without depending on per-section addressing being
   identical on the two sides. This is the primary pass/fail signal.

2. **Per-section refs** (diagnostic): used for drilldown when the whole-text
   hash mismatches. Tells us *where* the divergence is.

Failure classes (used on whole-text mismatch):
  A. PARSE_BUG       — DB stream has less text than canonical (drops)
                        OR more text where it shouldn't (dups, reorder)
  B. POLICY_GAP      — addressing matches but content differs because the
                        verifier's policy includes/excludes the wrong elements
  C. WORK_SPECIFIC   — DB has structure canonical doesn't model
  D. NORMALIZATION   — whitespace/Unicode-only difference
  ?. UNCLASSIFIED    — needs manual triage

A subtle case is "addressing mismatch with text preserved": whole-text hashes
match but per-section refs don't. This is NOT a failure — text integrity is
fine. The report notes it informationally.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from sqlite3 import Connection

from .extract import Section, extract_canonical_text
from .reconstruct import reconstruct_from_db
from .policy import Policy


class FailureClass(Enum):
    PARSE_BUG = "A"
    POLICY_GAP = "B"
    WORK_SPECIFIC = "C"
    NORMALIZATION = "D"
    UNCLASSIFIED = "?"


# Marker used to join section texts into the whole-text stream. Choice of
# marker doesn't affect what's compared (same on both sides) but newline
# lets us locate the failing section index when streams differ.
SECTION_SEP = "\n"


@dataclass
class SectionDiff:
    """One section-level diff record (diagnostic only)."""
    ref: str
    canonical: str | None
    db: str | None
    first_divergent_offset: int | None = None


@dataclass
class WorkReport:
    """Verification result for one work.

    The primary pass/fail comes from `canonical_hash == db_hash` (whole-text
    SHA-256s, all chars included). Two derived signals help classify the
    failure:

      - whitespace_stripped_match: same content, only whitespace differs
                                   (separator-style differences from how
                                   text was chunked).
      - letters_only_match:        same letters+digits, only whitespace AND
                                   punctuation differ (likely lost terminal
                                   punctuation, common in line-split rebuilds).

    If `letters_only_match=False` even when `passed=False`, real text content
    was lost or duplicated — class A.
    """
    work_id: str
    passed: bool
    # Whole-text hashes (primary integrity check)
    canonical_hash: str
    db_hash: str
    canonical_total_chars: int = 0
    db_total_chars: int = 0
    first_divergence_offset: int | None = None    # in the joined stream
    # Two derived sub-hashes for classification:
    whitespace_stripped_match: bool = True        # same content modulo whitespace
    letters_only_match: bool = True               # same content modulo ws+punct
    canonical_letters_chars: int = 0
    db_letters_chars: int = 0
    # Short context snippets around the whole-stream divergence offset, so a
    # reader can see what each side actually has at the failure point without
    # opening the source XML or DB.
    divergence_canonical_snippet: str | None = None
    divergence_db_snippet: str | None = None
    # Per-section diagnostic
    canonical_count: int = 0
    db_count: int = 0
    policy_name: str = ""
    missing_in_db: list[str] = field(default_factory=list)
    missing_in_canonical: list[str] = field(default_factory=list)
    section_diffs: list[SectionDiff] = field(default_factory=list)
    addressing_matches: bool = True               # set False if section refs disagree
    classification: FailureClass | None = None
    hypothesis: str | None = None
    error: str | None = None

    @classmethod
    def unfindable(cls, work_id: str) -> "WorkReport":
        return cls(
            work_id=work_id, passed=False,
            canonical_hash="", db_hash="",
            error="source XML not found",
        )


def verify_work(
    conn: Connection,
    xml_path: Path,
    work_id: str,
    policy: Policy,
) -> WorkReport:
    """Run the integrity check for one work."""
    try:
        canonical = extract_canonical_text(xml_path, policy)
    except Exception as e:
        return WorkReport(
            work_id=work_id, passed=False,
            canonical_hash="", db_hash="",
            policy_name=policy.name,
            error=f"extraction error: {type(e).__name__}: {e}"[:200],
        )

    db_sections = reconstruct_from_db(conn, work_id, policy)

    canonical_whole = SECTION_SEP.join(s.text for s in canonical)
    db_whole = SECTION_SEP.join(s.text for s in db_sections)
    c_hash = _sha256(canonical_whole)
    d_hash = _sha256(db_whole)

    # Secondary: hash with ALL whitespace stripped. Decides whether the
    # difference is purely whitespace (NORMALIZATION class) vs real content.
    c_no_ws = _strip_ws(canonical_whole)
    d_no_ws = _strip_ws(db_whole)
    c_ws_hash = _sha256(c_no_ws)
    d_ws_hash = _sha256(d_no_ws)

    # Tertiary: hash with whitespace AND punctuation stripped. If THIS still
    # differs, then letters/numbers differ — definitely lost or duplicated
    # text characters, not just formatting.
    c_letters = _strip_ws_and_punct(canonical_whole)
    d_letters = _strip_ws_and_punct(db_whole)
    c_letters_hash = _sha256(c_letters)
    d_letters_hash = _sha256(d_letters)

    report = WorkReport(
        work_id=work_id,
        passed=(c_hash == d_hash),
        canonical_hash=c_hash,
        db_hash=d_hash,
        canonical_total_chars=len(canonical_whole),
        db_total_chars=len(db_whole),
        canonical_count=len(canonical),
        db_count=len(db_sections),
        policy_name=policy.name,
        whitespace_stripped_match=(c_ws_hash == d_ws_hash),
        letters_only_match=(c_letters_hash == d_letters_hash),
        canonical_letters_chars=len(c_letters),
        db_letters_chars=len(d_letters),
    )

    # Per-section ref comparison (diagnostic; doesn't affect pass/fail unless
    # whole-text also differs).
    c_refs = [s.ref for s in canonical]
    d_refs = [s.ref for s in db_sections]
    report.addressing_matches = (c_refs == d_refs)

    if not report.passed:
        _populate_diffs(report, canonical, db_sections, canonical_whole, db_whole)
        _classify(report, policy)

    return report


def _strip_ws(s: str) -> str:
    import re
    return re.sub(r"\s+", "", s)


def _strip_ws_and_punct(s: str) -> str:
    """Strip everything that's not a letter or digit (Unicode-aware).

    Used to detect whether a hash mismatch is purely formatting (whitespace
    and punctuation, e.g. a missing terminal period) vs actual lost letters.
    """
    import re
    # \W in Python 3 with default str pattern is Unicode-aware: matches
    # anything that's not [letter | digit | underscore]. Underscore being
    # included is harmless; it's not a meaningful textual character we'd
    # confuse with real content.
    return re.sub(r"\W+", "", s)


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _populate_diffs(report, canonical, db_sections, canonical_whole, db_whole):
    """Compute drilldown data for a failing report."""
    # First-divergence offset in the joined stream — points at the actual
    # character where the two streams diverge.
    offset = None
    for i, (a, b) in enumerate(zip(canonical_whole, db_whole)):
        if a != b:
            offset = i
            break
    if offset is None and len(canonical_whole) != len(db_whole):
        offset = min(len(canonical_whole), len(db_whole))
    report.first_divergence_offset = offset

    # Capture short context snippets around the divergence so the report can
    # show what each side actually contains at the failure point. 30 chars of
    # leading context + 60 chars after gives enough to recognize the content.
    if offset is not None:
        start = max(0, offset - 30)
        end_c = min(len(canonical_whole), offset + 60)
        end_d = min(len(db_whole), offset + 60)
        report.divergence_canonical_snippet = canonical_whole[start:end_c]
        report.divergence_db_snippet = db_whole[start:end_d]

    # Per-section diff
    c_by_ref = {s.ref: s.text for s in canonical}
    d_by_ref = {s.ref: s.text for s in db_sections}
    report.missing_in_db = sorted(set(c_by_ref) - set(d_by_ref))
    report.missing_in_canonical = sorted(set(d_by_ref) - set(c_by_ref))
    for ref in sorted(set(c_by_ref) & set(d_by_ref)):
        c, d = c_by_ref[ref], d_by_ref[ref]
        if c != d:
            sec_offset = next(
                (i for i, (a, b) in enumerate(zip(c, d)) if a != b),
                min(len(c), len(d)),
            )
            report.section_diffs.append(
                SectionDiff(ref=ref, canonical=c, db=d, first_divergent_offset=sec_offset)
            )


def _classify(report, policy):
    """Heuristic auto-classification based on the failure shape.

    New decision tree using the three-hash structure:

      Level 1 — letters+digits identical (letters_only_match=True)?
        ├─ whitespace also identical (whitespace_stripped_match=True)? →
        │     POLICY_GAP (addressing/separator differences only)
        └─ whitespace differs but letters same →
              NORMALIZATION (whitespace/punctuation distribution differs)

      Level 2 — letters differ (letters_only_match=False):
        Real text content differs. Use char-delta and section-level info to
        distinguish between:
          - PARSE_BUG (text dropped or duplicated, addressable to a section)
          - POLICY_GAP (verifier and build disagree on which content to include)
          - WORK_SPECIFIC (DB has extra structure canonical doesn't model)
    """
    c_chars = report.canonical_total_chars
    d_chars = report.db_total_chars
    delta = abs(c_chars - d_chars)
    letters_delta = abs(report.canonical_letters_chars - report.db_letters_chars)

    # ============================================================
    # Level 1 — letters+digits match. The hash differs only because of
    # whitespace/punctuation distribution.
    # ============================================================
    if report.letters_only_match:
        # All letters and digits are preserved. The only difference is
        # whitespace and/or punctuation.
        if report.whitespace_stripped_match:
            # Punctuation differs but whitespace doesn't.
            report.classification = FailureClass.POLICY_GAP
            report.hypothesis = (
                "all letters & digits match; only punctuation distribution "
                f"differs ({delta:,} char delta) — addressing or "
                f"punctuation handling differs between sides"
            )
            return
        # Whitespace differs. Punctuation may or may not also.
        # Common cause: DB's line-splitter drops sentence-final periods
        # while re-chunking paragraphs into lines.
        report.classification = FailureClass.NORMALIZATION
        report.hypothesis = (
            "all letters & digits preserved; whitespace and/or punctuation "
            f"distribution differs ({delta:,} char delta) — likely the "
            "build's line-splitter drops separator characters when "
            "re-chunking text"
        )
        return

    # ============================================================
    # Level 2 — letters differ. Real text content lost, gained, or substituted.
    # ============================================================

    # Letters-only match was False, so we have actual letter-level difference.
    bigger_letters = max(report.canonical_letters_chars, report.db_letters_chars, 1)
    letters_delta_pct = letters_delta / bigger_letters

    # Sub-case A: canonical has more letters → text lost from DB
    if report.canonical_letters_chars > report.db_letters_chars:
        if report.missing_in_db:
            report.classification = FailureClass.PARSE_BUG
            report.hypothesis = (
                f"DB stream missing {letters_delta:,} letter chars "
                f"({letters_delta_pct:.1%}); "
                f"{len(report.missing_in_db)} ref(s) missing in DB "
                f"(first: `{report.missing_in_db[0]}`) — text dropped during build"
            )
            return
        # No missing refs but letters lost — could be policy or parse.
        # Look at section diffs to guess.
        if report.section_diffs and _looks_editorial_diff(report.section_diffs):
            report.classification = FailureClass.POLICY_GAP
            report.hypothesis = (
                f"canonical has {letters_delta:,} more letter chars; "
                f"differences at section level look like editorial content "
                f"the build correctly strips — extend policy.exclude"
            )
            return
        report.classification = FailureClass.PARSE_BUG
        report.hypothesis = (
            f"DB stream missing {letters_delta:,} letter chars "
            f"({letters_delta_pct:.1%}) — content lost; "
            f"first byte diverges at offset {report.first_divergence_offset:,}"
        )
        return

    # Sub-case B: DB has more letters → DB has content canonical doesn't model,
    # or canonical's policy is too aggressive.
    if report.db_letters_chars > report.canonical_letters_chars:
        if report.missing_in_canonical:
            report.classification = FailureClass.WORK_SPECIFIC
            report.hypothesis = (
                f"DB has {letters_delta:,} more letter chars; "
                f"{len(report.missing_in_canonical)} DB sections not produced "
                f"by canonical extractor (first: "
                f"`{report.missing_in_canonical[0]}`) — needs sub-policy override"
            )
            return
        report.classification = FailureClass.POLICY_GAP
        report.hypothesis = (
            f"DB has {letters_delta:,} extra letter chars; canonical is too "
            "aggressive in stripping content — review policy.exclude"
        )
        return

    # Sub-case C: same number of letters but they don't match → letters
    # were substituted (e.g. wrong-line collapse, character corruption).
    report.classification = FailureClass.PARSE_BUG
    report.hypothesis = (
        f"same letter count ({report.canonical_letters_chars:,}) but "
        f"contents differ — letters substituted, not lost; first byte "
        f"diverges at offset {report.first_divergence_offset:,}"
    )


def _looks_editorial_diff(diffs: list[SectionDiff]) -> bool:
    """Heuristic: do the section diffs look like editorial markup leakage?

    Editorial markup tends to be short, low-letter-ratio strings (numbers,
    punctuation, brackets, codes). Real text differences tend to be longer
    Greek/Latin word sequences.
    """
    if not diffs:
        return False
    for d in diffs[:3]:
        if d.canonical is None or d.db is None:
            continue
        # Look at the chars right around the divergence point
        i = d.first_divergent_offset or 0
        snippet_c = d.canonical[i:i+40]
        snippet_d = d.db[i:i+40]
        # If canonical has chars like "[", "<", numbers, parens around the
        # divergence, classify as editorial-looking.
        if any(ch in snippet_c for ch in "[<>()") and not any(ch in snippet_d for ch in "[<>()"):
            return True
    return False


