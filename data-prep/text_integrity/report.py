"""Render WorkReport collections to Markdown / JSON.

The Markdown report mirrors the mock-up in TEXT_INTEGRITY_PROPOSAL.md:
summary block → by-author roll-up → pass list (collapsed) → failure
drilldown → recommended actions. The JSON sidecar is for trend tracking.
"""
from __future__ import annotations
import json
import time
from collections import Counter, defaultdict
from .verify import WorkReport, FailureClass


def render(reports: list[WorkReport], fmt: str = "md", **meta) -> str:
    if fmt == "md":
        return _render_md(reports, **meta)
    if fmt == "json":
        return _render_json(reports, **meta)
    raise ValueError(f"unknown format: {fmt}")


# --- Markdown -----------------------------------------------------------

def _render_md(reports: list[WorkReport], **meta) -> str:
    lines: list[str] = []
    lines.append(_header_md(reports, **meta))
    lines.append(_summary_md(reports))
    lines.append(_by_author_md(reports))
    lines.append(_pass_list_md(reports))
    lines.append(_drilldown_md(reports))
    lines.append(_recommendations_md(reports))
    return "\n".join(lines)


def _header_md(reports, **meta) -> str:
    db_path = meta.get("db_path", "?")
    mode = meta.get("mode", "?")
    corpus = meta.get("corpus", "?")
    policy_ver = meta.get("policy_version", "v0")
    return "\n".join([
        "=" * 60,
        f"# TEXT INTEGRITY AUDIT — {mode} build, {corpus} corpus",
        "=" * 60,
        "",
        f"- **DB**: `{db_path}`",
        f"- **Run time**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Policy version**: {policy_ver}",
        "",
        "## How the check works",
        "",
        "For each work, we concatenate every section's text in document order",
        "from two sources and SHA-256 the result:",
        "",
        "  1. **Canonical**: extracted from the source XML in `data-sources/`,",
        "     filtered by the policy (drops `<note>`, `<bibl>`, apparatus, etc.).",
        "  2. **DB**: reconstructed from `text_lines` rows for the work, joined",
        "     in `(book_number, line_number, sequence_number)` order.",
        "",
        "**Both streams pass through the same normalizer (Unicode NFC, whitespace",
        "collapsed) before hashing.** A work *PASSES* iff `SHA-256(canonical) ==",
        "SHA-256(db)` — any byte difference (drop, dup, swap, reorder, format)",
        "produces different hashes and the work fails. Character counts and",
        "missing-ref lists are used only to *classify* what kind of failure",
        "occurred, never to decide pass/fail.",
        "",
    ])


def _summary_md(reports) -> str:
    total = len(reports)
    passing = sum(1 for r in reports if r.passed)
    failing = total - passing
    if total == 0:
        return "\n## Summary\n\nNo works to audit.\n"

    bar_pass = _bar(passing, total, width=20)
    bar_fail = _bar(failing, total, width=20)

    class_counts = Counter(
        r.classification.value if r.classification else "?"
        for r in reports if not r.passed
    )

    out = [
        "## Summary",
        "",
        f"- Works audited:                **{total}**",
        f"- Passing (SHA-256 match):      **{passing}** ({passing/total*100:.0f}%)  {bar_pass}",
        f"- Failing (SHA-256 differs):    **{failing}** ({failing/total*100:.0f}%)  {bar_fail}",
        "",
        "### Failure classes",
        "",
        "Pass/fail is hash-based. The classes below tell you *what kind of*",
        "difference the hash detected, so you know how to address it:",
        "",
        "  - **A. parse bug** — real text drop/dup/reorder in the build",
        "  - **B. policy gap** — verifier's element-handling rules are wrong",
        "  - **C. work-specific** — needs a per-author/per-work sub-policy",
        "  - **D. normalization** — whitespace / Unicode-form difference only",
        "  - **?. unclassified** — heuristics couldn't auto-decide; needs review",
        "",
        "### Counts",
        "",
    ]
    if failing == 0:
        out.append("None.")
    else:
        labels = {
            "A": "parse bug",
            "B": "policy gap",
            "C": "work-specific",
            "D": "normalization",
            "?": "unclassified",
        }
        for cls in ("A", "B", "C", "D", "?"):
            c = class_counts.get(cls, 0)
            if c == 0:
                continue
            note = " ← real defects" if cls == "A" else ""
            out.append(f"  - **{cls}.** {labels[cls]:<14} {c}{note}")
    out.append("")
    return "\n".join(out)


def _by_author_md(reports) -> str:
    fail_by_author = defaultdict(list)
    for r in reports:
        if r.passed:
            continue
        # Extract author prefix from work_id (e.g. tlg0007 from tlg0007.tlg083)
        author = r.work_id.split(".")[0] if "." in r.work_id else r.work_id
        fail_by_author[author].append(r)

    if not fail_by_author:
        return ""

    out = ["## By author (failing only)", ""]
    rows = sorted(fail_by_author.items(), key=lambda kv: -len(kv[1]))
    for author, rs in rows[:25]:
        classes = Counter(r.classification.value if r.classification else "?" for r in rs)
        cls_str = " ".join(f"{v}{k}" for k, v in classes.most_common())
        out.append(f"- `{author}` — {len(rs)} works failing  ({cls_str})")
    if len(rows) > 25:
        out.append(f"- … +{len(rows) - 25} more")
    out.append("")
    return "\n".join(out)


def _pass_list_md(reports) -> str:
    passing = [r for r in reports if r.passed]
    if not passing:
        return ""
    out = [
        "## Pass list",
        "",
        f"<details><summary>{len(passing)} passing works (click to expand)</summary>",
        "",
        "```",
    ]
    for r in passing:
        out.append(f"  {r.work_id:<30} hash={r.canonical_hash[:12]}... ({r.canonical_count} sections)")
    out.extend(["```", "", "</details>", ""])
    return "\n".join(out)


def _drilldown_md(reports) -> str:
    failing = [r for r in reports if not r.passed]
    if not failing:
        return ""

    # Sort by class then by work_id, so similar issues cluster
    def sort_key(r):
        cls = r.classification.value if r.classification else "z"
        return (cls, r.work_id)
    failing.sort(key=sort_key)

    out = ["## Failure drilldown", ""]
    for r in failing:
        out.append(_drilldown_one_md(r))
    return "\n".join(out)


def _drilldown_one_md(r: WorkReport) -> str:
    cls = r.classification.value if r.classification else "?"
    cls_name = r.classification.name if r.classification else "UNCLASSIFIED"
    lines = [
        f"### ▼ `{r.work_id}` — class {cls} ({cls_name})",
        "",
    ]
    if r.error:
        lines.append(f"- **Error**: {r.error}")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"- Policy:                  `{r.policy_name}`")
    lines.append(f"- Canonical SHA-256:       `{r.canonical_hash[:16]}...`  ({getattr(r, 'canonical_total_chars', 0):,} chars, {r.canonical_count} sections)")
    lines.append(f"- DB SHA-256:              `{r.db_hash[:16]}...`  ({getattr(r, 'db_total_chars', 0):,} chars, {r.db_count} sections)")
    # Derived sub-hash signals
    ws_match = getattr(r, 'whitespace_stripped_match', None)
    letters_match = getattr(r, 'letters_only_match', None)
    if ws_match is not None or letters_match is not None:
        ws_label = "✓ match" if ws_match else "✗ differs"
        letters_label = "✓ match" if letters_match else "✗ differs"
        lines.append(f"- After stripping whitespace:  {ws_label}")
        lines.append(f"- Letters & digits only:       {letters_label}  "
                     f"({getattr(r, 'canonical_letters_chars', 0):,} vs "
                     f"{getattr(r, 'db_letters_chars', 0):,} chars)")
    if hasattr(r, 'first_divergence_offset') and r.first_divergence_offset is not None:
        lines.append(f"- First divergent byte:    offset {r.first_divergence_offset:,}")
        # Show the surrounding context if we captured it. Helps a reader see
        # at a glance whether the failure is a missing period, a lost word,
        # a paragraph that didn't get split, etc.
        snip_c = getattr(r, 'divergence_canonical_snippet', None)
        snip_d = getattr(r, 'divergence_db_snippet', None)
        if snip_c is not None or snip_d is not None:
            lines.append("  Context at divergence (30 chars before, 60 after):")
            lines.append(f"    canonical: `{(snip_c or '')!r}`")
            lines.append(f"    db:        `{(snip_d or '')!r}`")
    if hasattr(r, 'addressing_matches') and not r.addressing_matches:
        lines.append(f"- Addressing schemes:      differ (canonical vs DB ref styles don't match — diagnostic only, not a failure cause)")
    if r.hypothesis:
        lines.append(f"- Hypothesis:              {r.hypothesis}")

    if r.missing_in_db:
        lines.append("")
        lines.append(f"- Missing in DB ({len(r.missing_in_db)}):")
        for ref in r.missing_in_db[:5]:
            lines.append(f"    - `{ref}`")
        if len(r.missing_in_db) > 5:
            lines.append(f"    - … +{len(r.missing_in_db) - 5} more")

    if r.missing_in_canonical:
        lines.append("")
        lines.append(f"- Missing in canonical ({len(r.missing_in_canonical)}):")
        for ref in r.missing_in_canonical[:5]:
            lines.append(f"    - `{ref}`")
        if len(r.missing_in_canonical) > 5:
            lines.append(f"    - … +{len(r.missing_in_canonical) - 5} more")

    if r.section_diffs:
        lines.append("")
        lines.append(f"- Differing sections ({len(r.section_diffs)}):")
        for d in r.section_diffs[:3]:
            lines.append(f"    - `{d.ref}` — first diverges at offset {d.first_divergent_offset}")
            if d.canonical and d.db:
                snip_c = d.canonical[max(0, d.first_divergent_offset-20):d.first_divergent_offset+40]
                snip_d = d.db[max(0, d.first_divergent_offset-20):d.first_divergent_offset+40]
                lines.append(f"        canonical: `{snip_c!r}`")
                lines.append(f"        db:        `{snip_d!r}`")
        if len(r.section_diffs) > 3:
            lines.append(f"    - … +{len(r.section_diffs) - 3} more")
    lines.append("")
    return "\n".join(lines)


def _recommendations_md(reports) -> str:
    """Aggregate B/C/D failures into actionable buckets."""
    failing = [r for r in reports if not r.passed and r.classification]
    if not failing:
        return ""

    by_class = defaultdict(list)
    for r in failing:
        by_class[r.classification.value].append(r)

    out = ["## Recommended actions", ""]
    if by_class.get("B"):
        out.append(f"1. **Policy gaps** ({len(by_class['B'])} works): review the first")
        out.append(f"   few failures' diff drilldowns; the editorial element(s) the")
        out.append(f"   verifier is missing usually show up at the first divergent")
        out.append(f"   offset. Add to `policy/__init__.py` GENERIC_EXCLUDE.")
    if by_class.get("C"):
        out.append(f"2. **Work-specific** ({len(by_class['C'])} works): these need")
        out.append(f"   sub-policy overrides. Add author/work entries to")
        out.append(f"   `policy/work_overrides.py`.")
    if by_class.get("D"):
        out.append(f"3. **Normalization** ({len(by_class['D'])} works): tighten the")
        out.append(f"   normalizer in `normalize.py` for the observed character class.")
    if by_class.get("A"):
        out.append(f"4. **Parse bugs** ({len(by_class['A'])} works): real defects in")
        out.append(f"   the build pipeline. File one issue per affected work.")
    if by_class.get("?"):
        out.append(f"5. **Unclassified** ({len(by_class['?'])} works): need manual")
        out.append(f"   triage. Read the drilldown and update verify._classify rules.")
    out.append("")
    return "\n".join(out)


def _bar(n, total, width=20):
    if total <= 0:
        return "[" + " " * width + "]"
    filled = round(n / total * width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


# --- JSON ---------------------------------------------------------------

def _render_json(reports: list[WorkReport], **meta) -> str:
    payload = {
        "meta": {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            **{k: str(v) for k, v in meta.items()},
        },
        "summary": {
            "total": len(reports),
            "passing": sum(1 for r in reports if r.passed),
            "failing": sum(1 for r in reports if not r.passed),
            "by_class": {
                cls.value: sum(1 for r in reports
                               if not r.passed and r.classification == cls)
                for cls in FailureClass
            },
        },
        "reports": [_report_to_dict(r) for r in reports],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _report_to_dict(r: WorkReport) -> dict:
    return {
        "work_id": r.work_id,
        "passed": r.passed,
        # Whole-text SHA-256 signals (primary check)
        "canonical_hash": r.canonical_hash,
        "db_hash": r.db_hash,
        "canonical_total_chars": getattr(r, "canonical_total_chars", 0),
        "db_total_chars": getattr(r, "db_total_chars", 0),
        "first_divergence_offset": getattr(r, "first_divergence_offset", None),
        "divergence_canonical_snippet": getattr(r, "divergence_canonical_snippet", None),
        "divergence_db_snippet": getattr(r, "divergence_db_snippet", None),
        # Derived sub-hash signals (used for classification)
        "whitespace_stripped_match": getattr(r, "whitespace_stripped_match", None),
        "letters_only_match": getattr(r, "letters_only_match", None),
        "canonical_letters_chars": getattr(r, "canonical_letters_chars", 0),
        "db_letters_chars": getattr(r, "db_letters_chars", 0),
        # Per-section diagnostic
        "canonical_count": r.canonical_count,
        "db_count": r.db_count,
        "policy_name": r.policy_name,
        "addressing_matches": getattr(r, "addressing_matches", True),
        "missing_in_db": r.missing_in_db,
        "missing_in_canonical": r.missing_in_canonical,
        "section_diff_count": len(r.section_diffs),
        "section_diffs_sample": [
            {
                "ref": d.ref,
                "first_divergent_offset": d.first_divergent_offset,
                "canonical": d.canonical[:200] if d.canonical else None,
                "db": d.db[:200] if d.db else None,
            }
            for d in r.section_diffs[:5]
        ],
        "classification": r.classification.value if r.classification else None,
        "hypothesis": r.hypothesis,
        "error": r.error,
    }
