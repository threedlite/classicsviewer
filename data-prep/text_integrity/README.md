# text_integrity — Classics Viewer text-integrity audit tool

On-demand diagnostic that verifies every byte of intended source text and
English translation that enters the build pipeline also reaches the DB, with
no drops, duplications, or reordering.

**Strictly read-only.** Reads `data-sources/` XML and `data-prep/perseus_texts_*.db`.
Writes only its own report files under `reports/`. Never mutates the build DB,
the source XML, or anything else.

This tool exists to convert "unknown unknowns" (silent parsing defects) into a
deterministic per-work pass/fail signal. Run it on any built DB to get a fresh
report. The first runs surface mostly **policy gaps** (verifier-side
adjustments); over time the residue narrows to real defects.

## Status

**Phase 0** — initial harness. Perseus-first.

Currently implemented:
- CLI entry (`audit.py`)
- XML canonical extraction (`extract.py`)
- DB reconstruction (`reconstruct.py`)
- Verify + classify (`verify.py`)
- Normalization (`normalize.py`)
- Report rendering (`report.py`, Markdown)
- Policy framework (`policy/`)
- Sub-policies: `perseus_standard.py`

To be added in subsequent phases:
- More sub-policies (drama, bekker_milestoned, stephanus_milestoned, pta_commentary, etc.)
- Translation-side audit (translation_segments vs `*-eng*.xml`)
- HTML report rendering
- Tests

See `TEXT_INTEGRITY_PROPOSAL.md` (repo root) for the full design rationale.

## Usage

```bash
# Default: audit Perseus works in the named build, write reports to ./reports/
python3 data-prep/text_integrity/audit.py extended

# Just one work
python3 data-prep/text_integrity/audit.py extended --works tlg0012.tlg001

# Scope by corpus (perseus | first1k | pta | all). Default: perseus.
python3 data-prep/text_integrity/audit.py extended --corpus all

# Custom report path
python3 data-prep/text_integrity/audit.py extended --report-out /tmp/myreport.md
```

The mode (`sample` / `full` / `extended` / `ios`) selects which built DB to
audit at `data-prep/perseus_texts_<mode>.db`.

## Output

Default: `reports/<timestamp>_<mode>_<corpus>.md` (+ a `.json` sidecar for
trend tracking).

Each report contains:
- Summary block (total works, pass/fail, classification breakdown)
- By-author roll-up
- Per-work pass list (collapsed)
- Failure drilldown (hashes, diverging sections, hypothesis)
- Recommended actions

## Policy

The verifier reproduces what the build pipeline *should* extract from each XML.
Editorial elements (`<note>`, `<bibl>`, apparatus criticus, etc.) are stripped
on both sides of the hash comparison.

**Policy gaps** — when the verifier's exclusion list is wrong, hashes mismatch
even though the build is correct. The triage rule:

- If the build's behavior matches scholarly-editor expectations (notes
  stripped, apparatus stripped, etc.) → it's a **policy gap**, update the
  exclusion list.
- If the build's behavior loses/duplicates/scrambles content that should be
  in the canonical text → it's a **parse bug**, file it.

See `policy/` for the generic exclusion list and per-corpus sub-policies.

## Read-only safety

- SQLite connections are opened with `mode=ro` URI flags.
- The tool does not import the build modules; it reads the DB and XML as data.
- The `reports/` directory is the only filesystem location written to.
- No `data-sources/` access beyond `read()`.
