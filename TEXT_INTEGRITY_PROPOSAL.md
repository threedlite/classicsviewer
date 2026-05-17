# Proposal: Hash-Based Text-Integrity Verification

Borrow the integrity-verification pattern from the sibling **diodorus** project and adapt it to Classics Viewer's data-prep pipeline. Goal: prove, per work, that every byte of intended source text and English translation that enters the pipeline also reaches the DB — no drops, no dups, no reordering.

This is **not** an alignment or quality check. It's a strict completeness/order/dedup check, independent of how text is later mapped to lines or aligned across languages.

---

## What diodorus does

Diodorus's `scripts/verify_alignment_integrity.py` runs six checks per work:

1. **Section-ref completeness** — every source CTS ref in the input JSON appears in the output alignment JSON, and same for English.
2. **No duplicate CTS refs** in source data.
3. **SHA-256 of all source texts** — verifies none were corrupted.
4. **English coverage hash** — checks that refined pieces account for the source text.
5. **Order preservation** — Greek and English sections appear in source order (per book, per work for multi-work configs).
6. **TEI XML output hash** — reconstructs text from the produced TEI `<p>` elements and hashes it; must match the source-English hash exactly. This is described in their code as "the ironclad check."

The signal architecture:
- Each pipeline step produces a JSON dump (`greek_sections.json`, `english_sections.json`) of sections with `cts_ref` and `text`.
- Hashes are computed on the section-text content (whitespace-normalized).
- The verification step compares input-derived hashes against output-derived hashes.
- Each work has a `config.json` with options (e.g. `xml_div_per_source_section`) that controls which checks apply — accommodates work-specific edge cases without losing the generic backbone.

Key principle: the hash is computed on **normalized, post-extraction content**, not raw XML. The extraction step itself is what defines "the text" — anything excluded (footnotes, editorial markup, etc.) is excluded *consistently* on both sides of the hash comparison.

---

## Adapting to Classics Viewer

### Goal

For every work in `data-sources/canonical-greekLit`, `canonical-latinLit`, `First1KGreek`, `pta_data`, and the other language corpora:

- Compute a **canonical source-text hash** directly from the XML at the start of the build.
- After the build, **reconstruct the same canonical text from the DB** (joining `text_lines` for the work) and hash it.
- Compare. Any mismatch = the build dropped, duplicated, or reordered source text for that work.

Same for English translations.

### Where it lives — self-contained folder, standalone on-demand diagnostic

This is **an independent audit tool**, run on-demand against an existing built DB. It does **not** sit inside the build pipeline (initially) and does not block builds. Everything for the tool lives in its own self-contained folder so it can be developed, used, and (eventually) versioned independently from the rest of `data-prep/`.

**Proposed folder layout** — `data-prep/text_integrity/`:

```
data-prep/text_integrity/
├── README.md                  ← usage, policy reference, examples
├── audit.py                   ← main CLI entry point
├── extract.py                 ← XML → canonical (section_ref, text) pairs
├── reconstruct.py             ← DB → (section_ref, text) pairs
├── verify.py                  ← diff + classify + WorkReport
├── normalize.py               ← whitespace + Unicode normalization
├── report.py                  ← Markdown / HTML rendering
├── policy/
│   ├── __init__.py            ← generic exclusion list + policy resolver
│   ├── perseus_standard.py    ← Priority 1 sub-policies
│   ├── bekker_milestoned.py
│   ├── stephanus_milestoned.py
│   ├── drama.py
│   ├── first1k_standard.py    ← Priority 2
│   ├── pta_commentary.py
│   ├── sanskrit.py            ← Priority 3
│   ├── coptic.py
│   └── work_overrides.py      ← per-author/per-work mapping registry
├── reports/                   ← default output directory for generated reports
│   └── .gitkeep
└── tests/                     ← unit tests for extractor + normalizer
    ├── fixtures/              ← small XML samples
    └── test_extract.py
```

**Invocation** (from repo root):

```bash
python3 -m data-prep.text_integrity.audit extended                    # audit Perseus works in extended DB
python3 -m data-prep.text_integrity.audit extended --works tlg0007.tlg083
python3 -m data-prep.text_integrity.audit extended --corpus perseus   # explicit scope
python3 -m data-prep.text_integrity.audit extended --corpus all       # after Phase 4+
python3 -m data-prep.text_integrity.audit extended --report-out custom_report.html
```

Default behavior: writes the Markdown + HTML reports to `data-prep/text_integrity/reports/<timestamp>_<mode>_<corpus>.md` (and `.html`), plus a JSON sidecar for trend tracking.

**Strictly read-only**: the tool reads `data-sources/` (XML) and `data-prep/perseus_texts_*.db` (built DBs). It writes **nothing** to either. Reports go only to its own `reports/` directory (or the user-specified `--report-out` path). No mutations to data-sources, no DB schema changes, no DB row writes, no migrations, no temporary tables in the production DB. SQLite connections are opened with `mode=ro` URI flags as a hard safety constraint.

Why standalone first, and in its own folder:

- **Fast iteration**: the policy-gap iteration loop (Phase 1) needs "run, look, classify, fix policy, re-run" cycles measured in seconds. Build-gating would gate that on minutes of rebuild time.
- **Independence (read-only)**: the tool only reads the DB and the XML. It cannot mutate data-sources (those are sacrosanct per CLAUDE.md), cannot mutate the production DB, cannot break the build. It can be developed and modified without coordinating with build code changes.
- **Versioning**: as the policy evolves, the folder accumulates its own changelog. The `WorkReport` JSON sidecars let us track integrity scores over time.
- **Future portability**: a self-contained folder makes it trivial to extract this tool to its own repo later if useful (e.g. for other TEI projects).
- **Reproducibility**: anyone can run the audit on a built DB without understanding the assembly pipeline. The tool documents what "correct text extraction" means in a way the build code never quite did.

### Components

The folder modules map to the conceptual pieces of the tool:

1. **`extract.py`** — `extract_canonical_text(xml_path, policy) → list[(section_ref, normalized_text)]`. Deterministic, exclusion-aware XML reader. Returns ordered (ref, text) pairs after applying the policy.
2. **`reconstruct.py`** — `reconstruct_from_db(db_path, work_id) → list[(section_ref, normalized_text)]`. Pulls back the same content from `text_lines` (and later `translation_segments`) in document order via `(book_number, line_number, sequence_number)`.
3. **`verify.py`** — `verify(work_id, policy) → WorkReport`. Diffs the two sequences, hashes, descends to per-section diff on mismatch, classifies the failure (A/B/C/D/?), returns a `WorkReport` dataclass.
4. **`normalize.py`** — whitespace collapse, Unicode normalization (NFC), policy-driven token treatment. Same function called on both sides of the comparison so the hashes are format-tolerant but order-strict.
5. **`policy/`** — the generic exclusion list and per-corpus sub-policies. Each sub-policy is a small Python module exposing `INCLUDE`, `EXCLUDE`, `STRIP_KEEP_TEXT`, and any work-specific tweaks.
6. **`report.py`** — `render_report(reports, format='md'|'html') → str`. Generates the readable artifact.
7. **`audit.py`** — the CLI entry point. Orchestrates: select works → run verify per work → collect reports → render → save.

### Report format

The report should be **scannable** at the top and **drilled-down** below:

```
============================================================
TEXT INTEGRITY AUDIT — extended build
============================================================
DB:           data-prep/perseus_texts_extended.db
Run time:     2026-05-14 19:15:32
Policy ver:   v0.1 (52 elements excluded, 11 strip-keep-text)
Override reg: 8 sub-policies, 47 work-specific entries

────────────────────────────────────────────────────────────
SUMMARY
────────────────────────────────────────────────────────────
Works audited:        2,734
Passing:              2,128  (78%)  ████████░░
Failing:                606  (22%)  ██▒░░░░░░░

Breakdown of failures:
  A. parse bug              12  ───  real defects to fix
  B. policy gap            354  ───  exclusion list needs update
  C. work-specific          89  ───  needs sub-policy override
  D. normalization          43  ───  whitespace/unicode issue
  ?. unclassified          108  ───  needs manual triage

────────────────────────────────────────────────────────────
BY AUTHOR (top failing)
────────────────────────────────────────────────────────────
tlg0007 Plutarch              4 works     all class C (PTA-like commentary structure)
tlg9010 Suda                  1 work      class A — see drilldown
tlg2018 Eusebius              5 works     mixed B+C
…

────────────────────────────────────────────────────────────
PASS LIST (collapsed; click to expand in HTML version)
────────────────────────────────────────────────────────────
tlg0012.tlg001 Iliad                hash=4d2639… (24 books, 15,693 lines)
tlg0012.tlg002 Odyssey              hash=a98aed… (24 books, 12,109 lines)
…

────────────────────────────────────────────────────────────
FAILURE DRILLDOWN
────────────────────────────────────────────────────────────

▼ tlg0007.tlg083 Plutarch, Virtues of Women   [FAIL, class C suspected]
    hash_canonical:  5c5dbf14b1c4ca12…
    hash_db:         e934b7f44f6e4eed…
    Section count:   canonical=29, db=29 (match)
    First divergent section: cts_ref="0" (intro)
        canonical: "Concerning the virtues of women, O Clea, I am not of…"
        db:        "(no row found for this section)"
    Working hypothesis: section n="0" in source; canonical extraction
      includes it; DB lookup expects start_line>=1. Likely needs the
      pta_commentary or intro-handling sub-policy.

▼ tlg9010.tlg001 Suda                          [FAIL, class A confirmed]
    hash_canonical:  abc123…
    hash_db:         def456…
    Section count:   canonical=24,159, db=24,148 (DB short by 11)
    Missing refs:    book4.sec591.entry_3077, book4.sec591.entry_3078, …
    Classification:  parse bug — entries 3077-3087 not inserted
    Suggested fix:   investigate process_first1k_work loop around line ___;
                      these entries have <div n="alphabetic_letter_α"> nesting

▼ tlg2018.tlg001 Eusebius, Praeparatio Evangelica   [FAIL, class B]
    hash_canonical:  …
    hash_db:         …
    First divergent character at offset 14,832 of section "1.2.3"
    Canonical contains: " (Mras 12.4)"   ← from <ref>
    DB contains:       ""
    Working hypothesis: <ref> tag not in exclusion list. Policy gap.

… (one entry per failing work, sorted by class then by author)

────────────────────────────────────────────────────────────
RECOMMENDED ACTIONS
────────────────────────────────────────────────────────────
1. Add <ref>, <listBibl>, <fw> to generic exclusion list  (closes ~80 class-B failures)
2. Define pta_commentary sub-policy   (closes ~40 class-C failures)
3. Normalize U+00A0, U+2009 to space in normalizer  (closes ~25 class-D failures)
4. File parse bugs for 12 class-A works (see drilldown section)
```

The report is saved as Markdown by default; an HTML version with collapsible sections (`<details>`) is rendered for browser viewing. The tool also emits a small machine-readable JSON sidecar (`text_integrity_audit.json`) so trends can be tracked across runs.

---

## The hard part — what counts as "source text"

The pipeline already filters out editorial markup, but the rules aren't centralized. To compute a meaningful hash, we have to formally define the inclusion/exclusion policy.

### Tentative generic exclusion list

Editorial / non-source elements that should NOT be in the canonical text:

```
<teiHeader>            metadata
<note>                 editorial footnotes
<bibl> <biblScope>     citations
<ref> <ptr>            cross-references
<gloss>                editorial glosses
<editorialDecl>
<rdg> <witDetail>      apparatus criticus (variant readings)
<app type="apparatus"> apparatus container; we keep <lem> but drop the apparatus
<witness>
<respStmt>
<change>
```

Elements with their text kept but the wrapper element stripped:

```
<lem>                  the lemma reading of an <app> — keep text
<hi>                   typographic highlighting — keep text, drop tag
<emph>                 emphasis — keep text
<seg>                  generic segment marker — keep text
<choice><orig>X</orig><reg>Y</reg></choice>
                       use one of them (work-specific or policy choice)
<supplied>             editor-supplied text — keep, possibly mark
<add> <corr> <sic>     corrections — policy choice
<gap reason="lost"/>   record as a token, do not silently drop
```

Tail text handling: every kept element's `.tail` is concatenated in document order (this is exactly the bug we hunted earlier — getting tail-text inclusion right is half the work).

Whitespace normalization: collapse runs of whitespace to single spaces, preserve hard newlines or not (per the canonical policy). Same on both sides of the comparison so the hash is order-stable but format-tolerant.

### Generic vs work-specific logic

Like diodorus, we'd need both:

- **Generic policy** — covers Perseus standard TEI works (Iliad, Plato dialogues, etc.). Drop the editorial set, keep everything else.
- **Work-specific overrides** — for edge cases where the generic policy is wrong:
  - PTA texts: `<quote type="lemma">` contains a biblical lemma the commentary refers to; whether to count it as "source text" is a policy question.
  - Aristotle Bekker / Plato Stephanus: `<milestone>` markers carry pagination metadata that's neither dropped nor part of the running text.
  - Drama with `<sp>`, `<speaker>`, `<stage>`: do speaker labels count as source text?
  - Sanskrit / Coptic / non-TEI corpora: different element vocabularies entirely.

The user identified this correctly as the central design challenge. Diodorus handles ~7 works with `config.json` per work; we have ~2,700+ works in extended mode. We can't write per-work configs for everything.

**Two-tier strategy:**

1. **Tier 1 (Generic policy)** covers the vast majority. The policy is one shared Python module that lists included/excluded elements and how to handle ambiguous ones (`choice`, `supplied`, etc.).

2. **Tier 2 (Work-specific overrides)** is a registry of `(work_id_pattern → overrides)`. Most works inherit the generic. Specific ones (PTA, drama, Bekker-numbered, etc.) declare exceptions.

Likely sub-policies needed (priority ordered — **Perseus first**):

**Priority 1 — Perseus (highest priority)**
- `perseus_standard` — most Perseus Greek/Latin works (Homer, Plato, Aristophanes, Demosthenes, Cicero, Caesar, etc.). The core scholarly corpus, what users read most. Get this right first.
- `bekker_milestoned` — Aristotle (page/column references). Perseus Aristotle works.
- `stephanus_milestoned` — Plato. Perseus Plato dialogues.
- `drama` — Aeschylus, Sophocles, Euripides, Aristophanes, Plautus, Terence (speakers, stage directions). All Perseus.

**Priority 2 — First1KGreek and PTA**
- `first1k_standard` — most First1KGreek works (the OGL `_OGL` corpus)
- `pta_commentary` — Hesychius, Severian, Theodoret, etc. (lemma + commentary structure). PTA `_PTA` works.

**Priority 3 — Other languages**
- `sanskrit` — Devanagari, IAST conversion considerations
- `coptic` — special character handling
- (any other language corpora that appear in `extended` mode)

Each Greek/Latin author maps to one of the four Priority-1 sub-policies via a small lookup table. The phased rollout (below) builds Priority 1 first; subsequent priorities are additive.

---

## Code outline

Skeletons for the modules in `data-prep/text_integrity/`. Each shows the public interface, key data types, and the main logic shape. Designed so Phase 0 can drop these in and start running against Perseus immediately.

### `audit.py` — CLI entry point

```python
"""text_integrity.audit — on-demand text-integrity audit of a built DB.

Read-only: reads data-sources/ XML and the named DB; writes reports to
data-prep/text_integrity/reports/ only.
"""
from __future__ import annotations
import argparse, json, sqlite3, time
from pathlib import Path
from . import extract, reconstruct, verify, report
from .policy import resolve_policy_for_work

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_SOURCES = REPO_ROOT / "data-sources"
REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("mode", choices=["sample", "full", "extended", "ios"])
    p.add_argument("--corpus", default="perseus",
                   choices=["perseus", "first1k", "pta", "all"],
                   help="Which corpus to audit (Phase 1 = perseus only)")
    p.add_argument("--works", nargs="*",
                   help="Specific work_ids; default = all in scope")
    p.add_argument("--report-out", type=Path, default=None)
    p.add_argument("--format", default="both", choices=["md", "html", "both"])
    args = p.parse_args()

    db_path = REPO_ROOT / "data-prep" / f"perseus_texts_{args.mode}.db"
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    # READ-ONLY DB connection (mode=ro URI flag is the hard safety constraint)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    works = _select_works(conn, args.corpus, args.works)
    print(f"[text_integrity] auditing {len(works)} works from {args.corpus}")

    reports = []
    for work_id in works:
        xml_path = _find_source_xml(work_id)
        if xml_path is None:
            reports.append(verify.WorkReport.unfindable(work_id))
            continue
        policy = resolve_policy_for_work(work_id)
        report_obj = verify.verify_work(conn, xml_path, work_id, policy)
        reports.append(report_obj)

    conn.close()

    # Render + save
    out_base = args.report_out or REPORTS_DIR / f"{_timestamp()}_{args.mode}_{args.corpus}"
    REPORTS_DIR.mkdir(exist_ok=True)
    if args.format in ("md", "both"):
        (out_base.with_suffix(".md")).write_text(report.render(reports, fmt="md"))
    if args.format in ("html", "both"):
        (out_base.with_suffix(".html")).write_text(report.render(reports, fmt="html"))
    (out_base.with_suffix(".json")).write_text(report.render(reports, fmt="json"))
    print(f"[text_integrity] reports written to {out_base.parent}")


def _select_works(conn, corpus, explicit):
    """Return ordered list of work_ids to audit, filtered by corpus."""
    if explicit:
        return list(explicit)
    sql = "SELECT id FROM works"
    if corpus == "perseus":
        sql += " WHERE id NOT LIKE '%\\_OGL' ESCAPE '\\' AND id NOT LIKE '%\\_PTA' ESCAPE '\\'"
    elif corpus == "first1k":
        sql += " WHERE id LIKE '%\\_OGL' ESCAPE '\\'"
    elif corpus == "pta":
        sql += " WHERE id LIKE '%\\_PTA' ESCAPE '\\'"
    return [row[0] for row in conn.execute(sql + " ORDER BY id")]


def _find_source_xml(work_id) -> Path | None:
    """Locate the source XML file for a work_id under data-sources/."""
    base = work_id.replace("_OGL", "").replace("_PTA", "")
    if "." not in base:
        return None
    author, num = base.split(".", 1)
    candidates = [
        DATA_SOURCES / "canonical-greekLit/data" / author / num,
        DATA_SOURCES / "canonical-latinLit/data" / author / num,
        DATA_SOURCES / "First1KGreek/data" / author / num,
        DATA_SOURCES / "pta_data/data" / author / num,
    ]
    for d in candidates:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.xml")):
            if f.name.startswith("__") or "eng" in f.name:
                continue
            if "grc" in f.name or "lat" in f.name or "pta-" in f.name:
                return f
    return None


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


if __name__ == "__main__":
    main()
```

### `extract.py` — XML → canonical text sequence

```python
"""Deterministic canonical-text extraction from a source XML file.

Applies the per-work policy to decide which elements are kept, stripped,
or excluded. Returns an ordered list of (section_ref, normalized_text).
"""
from __future__ import annotations
from dataclasses import dataclass
import xml.etree.ElementTree as ET
from pathlib import Path
from .normalize import normalize_text
from .policy import Policy

TEI_NS = "{http://www.tei-c.org/ns/1.0}"


@dataclass(frozen=True)
class Section:
    ref: str           # CTS-style reference (e.g. "1.2.3" or "Ps_91")
    text: str          # normalized canonical text


def extract_canonical_text(xml_path: Path, policy: Policy) -> list[Section]:
    """Walk the XML and produce ordered (ref, text) pairs per the policy.

    Order: document order. Refs come from the structural div / line / section
    addressing scheme appropriate to the work (per the policy).
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    # Strip namespaces for simpler traversal
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]

    body = root.find(".//body") or root.find(".//text")
    if body is None:
        return []

    sections: list[Section] = []
    for sec_elem, ref in _iter_section_leaves(body, policy):
        text = _gather_text(sec_elem, policy)
        text = normalize_text(text, policy.normalization)
        if text:
            sections.append(Section(ref=ref, text=text))
    return sections


def _iter_section_leaves(elem, policy: Policy):
    """Yield (leaf_section_element, ref_string) pairs in document order.

    "Section" here is whatever the policy declares as the addressable unit
    (typically a div[type=textpart] leaf, but works with line-level addressing
    like Homer use <l> instead). The ref string is composed from ancestor
    structural divs' n attributes per the policy's addressing scheme.
    """
    # Implementation walks the tree, tracking ancestor refs, yields leaves.
    ...


def _gather_text(elem, policy: Policy) -> str:
    """Concatenate text content of an element subtree per the policy.

    Rules:
    - If elem.tag in policy.EXCLUDE: return "" (drop entirely, do not recurse)
    - If elem.tag in policy.STRIP_KEEP_TEXT: recurse into children but don't
      emit any tag markers
    - Else: recurse normally, including tail text after each child
    - <choice><orig/><reg/></choice>: handle per policy.choice_handling
    - <gap reason="lost"/>: emit policy.gap_marker (default "[…]") to preserve
      structural position without inventing content
    - <supplied>: include the supplied text per policy.supplied_handling
    """
    if elem.tag in policy.exclude:
        return ""
    parts = []
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        if child.tag in policy.exclude:
            # Skip entirely but include the tail text that follows it
            if child.tail:
                parts.append(child.tail)
            continue
        if child.tag == "choice":
            parts.append(_resolve_choice(child, policy))
            if child.tail:
                parts.append(child.tail)
            continue
        if child.tag == "gap":
            parts.append(policy.gap_marker)
            if child.tail:
                parts.append(child.tail)
            continue
        # Normal: recurse (strip-keep-text falls through here too)
        parts.append(_gather_text(child, policy))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _resolve_choice(choice_elem, policy):
    """Resolve <choice><orig>X</orig><reg>Y</reg></choice> per policy."""
    ...
```

### `reconstruct.py` — DB → text sequence

```python
"""Reconstruct a work's canonical text sequence from the built DB.

Joins text_lines in (book_number, line_number, sequence_number) order, then
normalizes the same way extract.py does so the hashes are comparable.
"""
from __future__ import annotations
from sqlite3 import Connection
from .extract import Section
from .normalize import normalize_text
from .policy import Policy


def reconstruct_from_db(conn: Connection, work_id: str, policy: Policy) -> list[Section]:
    """Read all rows from text_lines for this work, return as Section list.

    The per-book grouping in `books.id` becomes part of the section ref.
    For most Perseus works, ref = f"{book_number}.{line_number}".
    For nested works (Bekker, hierarchical), ref includes additional levels
    derived from book_id structure.
    """
    rows = conn.execute(
        """
        SELECT
            b.id AS book_id, b.book_number, b.label,
            t.line_number, t.sequence_number, t.line_text
        FROM books b
        JOIN text_lines t ON t.book_id = b.id
        WHERE b.work_id = ?
        ORDER BY b.book_number, t.line_number, t.sequence_number
        """,
        (work_id,),
    ).fetchall()

    sections: list[Section] = []
    for row in rows:
        ref = policy.ref_from_db(row)  # build the canonical ref string
        text = normalize_text(row["line_text"], policy.normalization)
        if text:
            sections.append(Section(ref=ref, text=text))
    return sections
```

### `verify.py` — diff + classify

```python
"""Compare canonical-extracted vs DB-reconstructed text. Classify mismatches."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from sqlite3 import Connection
from .extract import Section, extract_canonical_text
from .reconstruct import reconstruct_from_db
from .policy import Policy


class FailureClass(Enum):
    PARSE_BUG = "A"            # build dropped/dup'd/reordered text
    POLICY_GAP = "B"           # verifier policy missed an editorial element
    WORK_SPECIFIC = "C"        # needs a sub-policy override
    NORMALIZATION = "D"        # whitespace/unicode quirk
    UNCLASSIFIED = "?"         # needs manual triage


@dataclass
class SectionDiff:
    ref: str
    canonical: str | None      # None if missing on canonical side
    db: str | None             # None if missing on DB side
    first_divergent_offset: int | None = None


@dataclass
class WorkReport:
    work_id: str
    passed: bool
    canonical_hash: str
    db_hash: str
    canonical_count: int
    db_count: int
    missing_in_db: list[str] = field(default_factory=list)
    missing_in_canonical: list[str] = field(default_factory=list)
    section_diffs: list[SectionDiff] = field(default_factory=list)
    classification: FailureClass | None = None
    hypothesis: str | None = None    # human-readable hypothesis when classifiable
    error: str | None = None         # set on extraction error

    @classmethod
    def unfindable(cls, work_id):
        return cls(work_id=work_id, passed=False,
                   canonical_hash="", db_hash="",
                   canonical_count=0, db_count=0,
                   error="source XML not found")


def verify_work(conn: Connection, xml_path, work_id: str, policy: Policy) -> WorkReport:
    """Run the integrity check for one work."""
    try:
        canonical = extract_canonical_text(xml_path, policy)
    except Exception as e:
        return WorkReport(work_id=work_id, passed=False,
                          canonical_hash="", db_hash="",
                          canonical_count=0, db_count=0,
                          error=f"extraction error: {e}")

    db_sections = reconstruct_from_db(conn, work_id, policy)
    c_hash = _hash_sections(canonical)
    d_hash = _hash_sections(db_sections)

    report = WorkReport(
        work_id=work_id,
        passed=(c_hash == d_hash),
        canonical_hash=c_hash,
        db_hash=d_hash,
        canonical_count=len(canonical),
        db_count=len(db_sections),
    )

    if not report.passed:
        _populate_diffs(report, canonical, db_sections)
        _classify(report, policy)

    return report


def _hash_sections(sections: list[Section]) -> str:
    """SHA-256 of section hashes joined by newline. Mirrors diodorus."""
    return hashlib.sha256(
        "\n".join(hashlib.sha256(s.text.encode("utf-8")).hexdigest()
                  for s in sections).encode("utf-8")
    ).hexdigest()


def _populate_diffs(report, canonical, db_sections):
    """Compute missing refs and per-section diffs for the failure drilldown."""
    c_by_ref = {s.ref: s.text for s in canonical}
    d_by_ref = {s.ref: s.text for s in db_sections}
    report.missing_in_db = sorted(set(c_by_ref) - set(d_by_ref))
    report.missing_in_canonical = sorted(set(d_by_ref) - set(c_by_ref))
    for ref in sorted(set(c_by_ref) & set(d_by_ref)):
        c, d = c_by_ref[ref], d_by_ref[ref]
        if c != d:
            offset = next((i for i, (a, b) in enumerate(zip(c, d)) if a != b), min(len(c), len(d)))
            report.section_diffs.append(SectionDiff(ref=ref, canonical=c, db=d,
                                                     first_divergent_offset=offset))


def _classify(report, policy):
    """Apply heuristics to classify the failure as A/B/C/D/?.

    These heuristics are intentionally conservative — they only auto-classify
    when confident. Uncertain cases stay as UNCLASSIFIED and surface in the
    report's drilldown for manual triage. As Phase 1 progresses and patterns
    emerge, heuristics gain more cases.
    """
    if report.missing_in_db and not report.missing_in_canonical:
        # Canonical has refs that DB doesn't — most likely parse bug
        # (text dropped during build) OR policy gap (verifier including
        # editorial sections the build correctly excludes).
        # Heuristic: if missing refs include any element from policy.
        # suspected_excluded_in_build, lean class B; else class A.
        if any(_looks_editorial(r, policy) for r in report.missing_in_db):
            report.classification = FailureClass.POLICY_GAP
            report.hypothesis = ("canonical includes refs that look editorial; "
                                  "build correctly excluded them — extend policy.exclude")
            return
        report.classification = FailureClass.PARSE_BUG
        return

    if report.missing_in_canonical and not report.missing_in_db:
        # DB has refs canonical doesn't — likely policy gap (verifier missing
        # some section type) or build duplication.
        report.classification = FailureClass.POLICY_GAP
        return

    if not report.missing_in_db and not report.missing_in_canonical:
        # Same refs on both sides, but text differs. Either policy gap
        # (different content per ref because of element handling) or
        # normalization. Sample the first diff to guess.
        if report.section_diffs:
            d = report.section_diffs[0]
            if _looks_normalization(d.canonical, d.db):
                report.classification = FailureClass.NORMALIZATION
                return
        report.classification = FailureClass.POLICY_GAP
        return

    report.classification = FailureClass.UNCLASSIFIED


def _looks_editorial(ref: str, policy: Policy) -> bool:
    """Heuristic: ref string looks like an editorial division
    (e.g. 'intro', 'preface', 'app.crit', 'bibl.X')."""
    ...


def _looks_normalization(canonical: str, db: str) -> bool:
    """Heuristic: only whitespace or Unicode-form differences."""
    ...
```

### `normalize.py` — whitespace + Unicode

```python
"""Text normalization applied identically on canonical and DB sides."""
from __future__ import annotations
import re, unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizationPolicy:
    unicode_form: str = "NFC"            # NFC | NFD | NFKC | NFKD | "none"
    collapse_whitespace: bool = True     # runs of WS → single space
    strip_outer: bool = True             # strip leading/trailing WS
    treat_nbsp_as_space: bool = True     # U+00A0 → U+0020
    strip_zero_width: bool = True        # U+200B-U+200F, U+FEFF
    case_fold: bool = False              # usually False — case is content


def normalize_text(text: str, pol: NormalizationPolicy) -> str:
    if pol.unicode_form != "none":
        text = unicodedata.normalize(pol.unicode_form, text)
    if pol.treat_nbsp_as_space:
        text = text.replace(" ", " ")
    if pol.strip_zero_width:
        text = re.sub(r"[​-‏﻿]", "", text)
    if pol.collapse_whitespace:
        text = re.sub(r"\s+", " ", text)
    if pol.strip_outer:
        text = text.strip()
    if pol.case_fold:
        text = text.casefold()
    return text
```

### `policy/__init__.py` — generic policy + resolver

```python
"""Policy module: defines what counts as canonical source text.

Each sub-policy (perseus_standard, drama, etc.) is a Python module with:
  EXCLUDE: set of TEI tags to drop entirely (do not recurse, drop content)
  STRIP_KEEP_TEXT: set of tags to remove from the structure but keep text
  CHOICE_HANDLING: 'orig' | 'reg' | 'both'
  SUPPLIED_HANDLING: 'include' | 'mark' | 'exclude'
  GAP_MARKER: string emitted for <gap reason="lost"/>
  ADDRESSING: how to build section refs (line-level, section-level, hierarchical)
  WORK_OVERRIDES: optional dict of {work_id_pattern: {<field>: <override>}}

The resolver picks the right sub-policy based on work_id, falling back to
perseus_standard for any Perseus work that doesn't match a more specific rule.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import importlib
from .work_overrides import RESOLVER_TABLE
from ..normalize import NormalizationPolicy


@dataclass
class Policy:
    name: str
    exclude: set[str]
    strip_keep_text: set[str]
    choice_handling: str
    supplied_handling: str
    gap_marker: str
    addressing: str           # 'line' | 'section' | 'hierarchical'
    normalization: NormalizationPolicy
    _module: Any              # the sub-policy module (for hooks like ref_from_db)

    def ref_from_db(self, db_row) -> str:
        return self._module.ref_from_db(db_row)


# The generic exclusion list. Sub-policies start from this and add/remove.
GENERIC_EXCLUDE = {
    "teiHeader", "note", "bibl", "biblScope", "ref", "ptr", "gloss",
    "editorialDecl", "rdg", "witDetail", "witness", "respStmt", "change",
    "listBibl", "fw", "milestone",  # milestones handled separately
    # ... extend as policy iteration finds more
}

GENERIC_STRIP_KEEP_TEXT = {
    "lem", "hi", "emph", "seg", "supplied", "corr",
    "foreign", "label", "rs",
    # ... extend as needed
}


def resolve_policy_for_work(work_id: str) -> Policy:
    """Look up the right sub-policy for this work_id."""
    sub_policy_name = RESOLVER_TABLE.get(work_id)  # exact match first
    if sub_policy_name is None:
        sub_policy_name = _pattern_match(work_id)  # author-level pattern
    if sub_policy_name is None:
        sub_policy_name = "perseus_standard"       # generic default

    module = importlib.import_module(f".{sub_policy_name}", package=__name__)
    return Policy(
        name=sub_policy_name,
        exclude=GENERIC_EXCLUDE | getattr(module, "ADD_EXCLUDE", set())
                - getattr(module, "UNEXCLUDE", set()),
        strip_keep_text=GENERIC_STRIP_KEEP_TEXT | getattr(module, "ADD_STRIP_KEEP_TEXT", set()),
        choice_handling=getattr(module, "CHOICE_HANDLING", "reg"),
        supplied_handling=getattr(module, "SUPPLIED_HANDLING", "include"),
        gap_marker=getattr(module, "GAP_MARKER", "[…]"),
        addressing=getattr(module, "ADDRESSING", "line"),
        normalization=getattr(module, "NORMALIZATION", NormalizationPolicy()),
        _module=module,
    )


def _pattern_match(work_id):
    """Match work_id by author prefix or suffix conventions.
    e.g. 'tlg0086.*' → 'bekker_milestoned' (Aristotle)
         '*_PTA'      → 'pta_commentary'
    """
    ...
```

### `policy/perseus_standard.py` — example sub-policy

```python
"""Generic Perseus Greek/Latin policy. Default fallback for Perseus works.

Most Perseus TEI documents follow consistent conventions; this module captures
those. Specific authors with idiosyncrasies (Aristotle, Plato, drama) override
in their own sub-policy modules.
"""
from __future__ import annotations

# Generic policy already excludes the standard editorial set. Perseus-specific
# additions go here.
ADD_EXCLUDE = {
    "app",          # apparatus criticus container — we drop entirely
    "del",          # editor deletions
}

ADD_STRIP_KEEP_TEXT = {
    "q", "quote", "cit",   # quotations: keep the text
    "title",                # work titles cited in running text
}

CHOICE_HANDLING = "reg"       # use regularized form by default
SUPPLIED_HANDLING = "include" # include editor-supplied text without marking
GAP_MARKER = "[…]"
ADDRESSING = "line"           # most Perseus works are line-addressed


def ref_from_db(row) -> str:
    """Build canonical ref from a books+text_lines join row."""
    # Default: "<book_number>.<line_number>"
    return f"{row['book_number']}.{row['line_number']}"
```

### `policy/work_overrides.py` — registry

```python
"""Work-specific and author-specific policy resolution registry.

When the generic perseus_standard policy is wrong for a work or author,
add an entry here. Examples:
  - Plato → stephanus_milestoned (Stephanus page numbering)
  - Aristotle → bekker_milestoned (Bekker page/column)
  - Aeschylus, Sophocles, etc. → drama (speaker, stage handling)
"""

# Exact work-id → sub-policy module name
RESOLVER_TABLE: dict[str, str] = {
    # tlg0007.tlg083: "pta_lemma_handling",  # example
}

# Author prefix → sub-policy. First match wins.
AUTHOR_PATTERNS: list[tuple[str, str]] = [
    ("tlg0086.", "bekker_milestoned"),    # Aristotle
    ("tlg0059.", "stephanus_milestoned"), # Plato
    ("tlg0085.", "drama"),                # Aeschylus
    ("tlg0006.", "drama"),                # Euripides
    ("tlg0011.", "drama"),                # Sophocles
    ("tlg0019.", "drama"),                # Aristophanes
    ("phi0119.", "drama"),                # Plautus
    # extend as needed during Phase 1 iteration
]

# Corpus-suffix patterns
CORPUS_SUFFIX_PATTERNS: list[tuple[str, str]] = [
    ("_OGL", "first1k_standard"),
    ("_PTA", "pta_commentary"),
]
```

### `report.py` — rendering

```python
"""Render WorkReport collections to Markdown, HTML, or JSON.

Markdown is the primary format (matches the report mock-up in the proposal).
HTML adds <details> collapsible sections for the pass-list. JSON is for trend
tracking across runs.
"""
from __future__ import annotations
import json
from collections import Counter
from .verify import WorkReport, FailureClass


def render(reports: list[WorkReport], fmt: str = "md") -> str:
    if fmt == "md":
        return _render_md(reports)
    if fmt == "html":
        return _render_html(reports)
    if fmt == "json":
        return _render_json(reports)
    raise ValueError(fmt)


def _render_md(reports):
    lines = []
    lines.append(_header())
    lines.append(_summary_section(reports))
    lines.append(_by_author_section(reports))
    lines.append(_pass_list(reports, collapsed=True))
    lines.append(_failure_drilldown(reports))
    lines.append(_recommended_actions(reports))
    return "\n".join(lines)


def _summary_section(reports):
    """Renders the SUMMARY block from the mock-up — total works, pass/fail,
    class breakdown with the unicode bar visualisations."""
    ...


def _failure_drilldown(reports):
    """One ▼ block per failing work, with hashes, first divergent section,
    and hypothesis. Sorted by class then by work_id."""
    ...


def _recommended_actions(reports):
    """Aggregate class-B and class-C suggestions into actionable bullets:
    'Add <ref>, <listBibl>, <fw> to generic exclusion list (closes ~80 class-B failures)'.
    """
    class_counts = Counter(r.classification for r in reports if not r.passed)
    ...
```

### Tests scaffold

```python
# data-prep/text_integrity/tests/test_extract.py
"""Unit tests for the XML extractor.

Each test feeds a minimal XML fixture through extract_canonical_text and
checks the output. Fixtures live in fixtures/*.xml. Naming convention:
  fixtures/<scenario>.xml + fixtures/<scenario>.expected.txt
"""
import pytest
from pathlib import Path
from data_prep.text_integrity.extract import extract_canonical_text
from data_prep.text_integrity.policy.perseus_standard import ...

FIXTURES = Path(__file__).parent / "fixtures"


def test_strips_note():
    """Sanity: <note> content does not appear in extracted text."""
    ...


def test_keeps_lem_drops_apparatus():
    """The <lem> child of <app> is kept; the <app> container is dropped."""
    ...


def test_choice_uses_reg_by_default():
    ...


def test_gap_emits_marker():
    ...


def test_tail_text_preserved():
    """Element's .tail text follows the previous sibling correctly."""
    ...


def test_nested_structural_divs_addressed_correctly():
    ...
```

These outlines are sized so Phase 0 implementation is a focused weekend's work: ~600 lines of code, mostly straightforward XML walking and SQL queries. The policy module is where the real iteration happens during Phase 1.

---

## Phased rollout — Perseus first, expanding outward

All corpora will eventually be covered, but the priority order matters because (a) Perseus is the most-read content, (b) Perseus TEI is the cleanest and best-documented, making the generic policy easier to nail down first, and (c) early wins on Perseus de-risk the approach before tackling messier corpora (PTA, scholia, non-Greek/Latin).

### Phase 0 — Build the harness

Write `data-prep/text_integrity_audit.py` with:
- The generic Perseus-oriented exclusion policy (one definitive list, tuned for Perseus TEI conventions)
- `extract_canonical_text()` — XML walker that applies the policy
- `reconstruct_from_db()` — joins `text_lines` for a work in `(book_number, line_number, sequence_number)` order
- `verify(work_id)` — hash + drill-down diff
- A `WorkReport` dataclass (hash, section count, missing refs, etc.) and `render_report()`

Run against the current extended DB filtered to **Perseus works only** (`tlg*` and `phi*` without `_OGL`/`_PTA` suffix). Expect many mismatches initially — those are findings, not failures.

### Phase 1 — Classify the mismatches (this is the bulk of the work)

When the verifier finds `hash_canonical ≠ hash_db` for a work, *something* differs — but the fault isn't necessarily in the build pipeline. The verifier computes two hashes:

```
hash_canonical = SHA-256( apply_exclusion_policy(work.xml) )
hash_db        = SHA-256( join text_lines for work )
```

Any mismatch is one of four root causes, and most of the effort in adopting this approach goes into separating them. **This is the central work** — get the policy right, and what remains is real defect surface.

#### The four root causes

| Class | Where the fault is | Resolution | Example |
|---|---|---|---|
| **A. Parse bug** | The build pipeline | Fix `monolith_fn.py` or related code | XML has 1000 chars, only 800 ended up in `text_lines` — text dropped or shuffled |
| **B. Policy gap** | The verifier's generic exclusion list | Update the exclusion list, re-verify, no code change | XML has `<bibl>` citations; build correctly strips them; policy forgot `<bibl>` so the verifier *includes* them in `hash_canonical` → mismatch even though the build is correct |
| **C. Work-specific edge case** | The verifier's per-author/per-pattern override registry | Add an override entry, re-verify, no code change | PTA commentary works treat `<quote type="lemma">` as canonical source text; generic policy doesn't know that; the override declares this for the `pta_commentary` sub-policy |
| **D. Normalization quirk** | The verifier's whitespace/Unicode handling | Tighten normalization, re-verify | XML has a non-breaking space `U+00A0`; DB has a regular space; both are "correct" but hash differs because we didn't normalize them to the same character |

#### Worked example — class B vs class A

Suppose the generic exclusion list has `<note>` and `<bibl>` but forgot `<witDetail>` (apparatus criticus witness details).

Source XML:
```xml
<l>Μῆνιν ἄειδε θεὰ <witDetail>codd. omit</witDetail> Πηληϊάδεω</l>
```

- **Build pipeline**: existing code correctly strips `<witDetail>` → DB stores `"Μῆνιν ἄειδε θεὰ Πηληϊάδεω"`
- **Verifier (with the gap)**: doesn't strip `<witDetail>` → `hash_canonical` is computed over `"Μῆνιν ἄειδε θεὰ codd. omit Πηληϊάδεω"`
- Hashes differ — **but the build is fine**. The fix is update the policy. One line in the exclusion list. No code change.

By contrast, a real parse bug looks like this:

Source XML:
```xml
<l n="62">Αἰτναίων εἴσω σκοπέλων;</l>
<l n="62a">—νύττ' οὐ τᾷδ' οὔ;</l>
```

- **Verifier**: extracts both lines, `hash_canonical` covers `"Αἰτναίων εἴσω σκοπέλων; —νύττ' οὐ τᾷδ' οὔ;"`
- **Build pipeline**: collapses `n="62a"` into line_number=62, so both lines end up under the same key — content technically present but the order/reconstruction depends on `sequence_number` resolution
- Reconstruction from DB joins in `(book_number, line_number, sequence_number)` order — if the seq numbers got the right document order, hashes match; if they didn't, hashes differ
- A hash mismatch here is a **real parse bug** (the existing `parse_line_number` letter-suffix collapse we identified earlier)

The triage rule:

> If the build's behavior matches what a scholarly editor would expect (notes stripped, apparatus criticus stripped, page references stripped, etc.) → **policy gap**, update the verifier.
> If the build's behavior loses, duplicates, or scrambles content that *should* be in the canonical text → **parse bug**, fix the code.

#### Why policy gaps dominate the first run

On day one, the generic exclusion list is a best guess. The Perseus TEI guidelines define ~80 distinct editorial elements; we'll get a subset wrong. Hundreds of mismatches will fire — most of them policy gaps, not parse bugs.

The iteration loop:

1. Run verify on a representative slice (say 50 works of mixed shape).
2. For each mismatch, look at the first divergent character in `hash_canonical` vs `hash_db`. Manually classify: was that content stripped on purpose (B) or accidentally lost (A)?
3. If B: add the element to the exclusion list. Re-run. Recheck.
4. If C: the same element should be included in some works but not others. Add to the work-specific registry under the relevant sub-policy. Re-run.
5. If D: tighten the normalizer (Unicode NFC, whitespace collapse, etc.). Re-run.
6. If A: file it as a parse defect, leave the build temporarily failing this work, move on.

The policy stabilizes when steps B/C/D stop generating new entries. At that point every remaining mismatch is class A — real bugs to fix in `monolith_fn.py` (or, more likely, the language-specific build modules).

#### Tracking progress

A small status board per build:

```
text_integrity report — extended build
─────────────────────────────────────────
Works processed:        2,734
Passing:                2,128  (78%)
Failing:                  606  (22%)
  └─ A. parse bug:        12  (real defects)
  └─ B. policy gap:       —   (none after run 7)
  └─ C. work-specific:    —   (none after run 7)
  └─ D. normalization:    —   (none after run 7)
  └─ unclassified:       594  (need triage)
```

Each iteration of the policy should drive B/C/D down. Once they're zero, the residue is real defect surface — the same defect surface we've been hunting case-by-case throughout this conversation, but now enumerated and persistent across builds.

#### The cost is up-front; the benefit compounds

Closing policy gaps is tedious. The first 50 mismatches will surface most editorial elements that need exclusion. The next 200 will surface most work-specific patterns. After that, new mismatches become rare and almost all are real bugs.

After Phase 1 is done, every future build automatically catches:
- Any new work that has a structural quirk we hadn't seen
- Any regression that drops/duplicates/reorders text
- Any change to the build code that subtly affects extraction

Without this work, those bugs would continue to land silently until a user notices missing or garbled text — which is how we found most defects in this conversation. Phase 1 inverts that: bugs are detected at build time, before users see them.

### Phase 2 (deferred) — Optional build-gate integration

Once Phase 1 settles and the report is reliably showing few/no class-B/C/D failures, **then** we can consider integrating into the build:

- As a post-build check (warn but don't fail): run after assembly; if regressions appear, log them.
- As a strict gate (fail the build): only after the existing class-A failures are fixed, so the gate doesn't immediately get bypassed.

Both are one-line additions to the assembly script (`subprocess.run(['python3', 'data-prep/text_integrity_audit.py', mode])`). Defer this decision until Phase 1 has demonstrated value.

In the meantime, the audit tool is run on-demand:
- Before declaring a build "good"
- When investigating user-reported text issues
- When verifying a fix didn't regress other works
- Periodically during development

### Phase 3 — Extend to translations (Perseus first)

Apply the same approach to English translations, **still scoped to Perseus**:
- Extract canonical English text per section from the `*-eng*.xml` files (Perseus + aligned overrides)
- Reconstruct from `translation_segments` rows
- Hash and compare

This catches the same defect classes for the English side — the same hash-collision, structural-collapse, and section-numbering issues we hunted earlier. Perseus translations are the priority because they're the ones users read in the app today.

### Phase 4 — Expand to First1KGreek + PTA

Once Phase 1–3 are stable on Perseus, expand coverage:
- Enable the `first1k_standard` sub-policy and re-run on `*_OGL` works
- Enable `pta_commentary` and re-run on `*_PTA` works
- Each expansion will surface a new wave of policy gaps (class B) and work-specific edge cases (class C). Iterate the same Phase 1 loop until they close.

### Phase 5 — Other language corpora

Sanskrit, Coptic, Arabic, Hebrew, Persian, Pali, Norse, Chinese, Old English, Dante, Syriac, Cuneiform. Each gets its own sub-policy module. Less urgent because:
- These corpora are smaller and less-read than Perseus
- Their build pipelines are simpler (no apparatus criticus, fewer editorial conventions)
- Existing defects are less likely to be subtle hash-mismatch issues

Order within Phase 5 should follow user-read volume, not corpus size.

---

## Side effects (probably good)

The user noted: *"in doing this we may uncover more existing parse issues in our code."* That's a feature.

Expected discoveries on first run:

- **The 6,586 PTA triple-duplicates** we already identified (will fail integrity check until fixed)
- **The Pliny `<hi rend="bold">` leakage** in Latin
- **The 5–6 catastrophic long-line collapses** (one Greek work has a 599-KB single line)
- **The 170 inverted translation ranges** in Longinus *On the Sublime* and Coptic Shenoute
- Unknown issues in works we haven't yet inspected (likely many, especially in scholia, catenae, and patristic corpora)

The integrity check converts these from "unknown unknowns" to a measurable count of failing works. Each gets a ticket; the count goes down over time.

---

## Effort estimate

- **Phase 0** (harness): 1–2 days for the extractor + reconstructor + report. The hard part is the generic XML walker — it has to handle tails correctly, `<choice>` properly, and skip the exclusion set without breaking text continuity.
- **Phase 1** (classify): 3–5 days of iterating. The unknown is how many work-specific overrides we'll end up needing. If 8 sub-policies cover everything, this is fast. If we end up needing per-author configs for 100+ authors, it's slower.
- **Phase 2** (build gate): half a day once Phase 1 has stabilized.
- **Phase 3** (translations): 1–2 days. Reuses the same harness.
- **Real defect fixes uncovered**: open-ended. The integrity check tells us what's broken; fixing each defect is its own task.

Total proposal effort to get a working, useful gate: about **two weeks of focused work**, with the value delivered incrementally (Phase 0 alone tells us a lot).

---

## Why this is worth doing

Today our regression detection is:
- The Merkle-tree snapshot diff (`data-prep/merkle_snapshot.py`) — detects whether the build *changed*, but not whether the change is a defect.
- Manual spot-checks against XML — catches single-instance bugs but doesn't scale.
- The defect catalogs we've built (`XML_PARSING_DEFECTS_VERIFIED.md`, etc.) — historical, not enforced.

The hash integrity check is the missing link: it gives us a single, deterministic "is the source text fully preserved?" answer per work, per build. Combined with the Merkle snapshot:

- **Merkle**: did anything change between builds? (regression detection)
- **Integrity**: does the current build faithfully represent the source XML? (correctness)

Together they catch both new bugs (Merkle shows a change you didn't intend) and old ones (Integrity shows a divergence that's been there all along).

---

## Open questions for you to confirm before Phase 0

1. **Policy on `<choice><orig>X</orig><reg>Y</reg></choice>`** — keep `orig` (medieval spelling), `reg` (regularized), or both?
2. **Apparatus `<app>`** — keep `<lem>` only (current behavior) or also include selected `<rdg>` readings?
3. **Speaker labels in drama** — count as source text or not? Current pipeline includes them in `text_lines.speaker`, not in `line_text`. Either policy is fine but the verifier needs to know which.
4. **Editorial supplements `<supplied>`, `<corr>`, `<add>`** — include the supplied text? Mark it? Drop it?
5. **Sanskrit & Coptic** — start with Greek + Latin only, add others later? Their TEI vocabularies differ enough that a separate policy module makes sense.
6. **Run on which build mode first** — sample (fast feedback, ~12 authors), full, or extended (most coverage but slowest)?

Each of these is a one-line policy decision but locks the hash baseline, so worth getting right before Phase 0.
