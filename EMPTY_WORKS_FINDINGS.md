# Empty-Works Defect — Audit Findings (2026-05-17)

## Summary

The text-integrity audit (`data-prep/text_integrity/audit.py`) run against the
post-GLAUx extended DB on 2026-05-17 detected **65 Perseus works that import
as 0 books / 0 text_lines** despite having substantial content in their
source XML files. Total text lost: **~2.56 million letter characters**.

The build pipeline produces no error or warning for any of these — they
silently appear in the `works` table with the right title and author, but
their content is absent from `text_lines`. Only the integrity audit caught
the defect.

## Affected works

### Dominant: Aristides Aelius — 54 of his orations

All 54 missing works belong to author `tlg0284` (Aelius Aristides, 2nd c.
sophist). His orations (`tlg0284.tlg001` through `tlg0284.tlg054`) use
**`subtype="Jebb_page"`** — a custom subtype name referring to pages in
Jebb's 1899 critical edition. This subtype is not in the build's
`structural_subtypes` set, so `is_structural_div()` returns False for every
div in the file, no leaf div is ever found, and the work produces zero
books.

### Other affected works (11)

| Work | Author + Title | Subtypes used | refsDecl status | Root cause |
|---|---|---|---|---|
| `phi0631.phi003` | Sallust *Historiae* | `book` (n=Lep, Phil, Cott, Pomp, Macr) | active | Non-numeric `book` `n` values — Fix1+Fix2's literal-`n` scheme didn't extend to the `book` level |
| `phi1014.phi004` | Seneca the Elder *Fragmenta* | `book` + `fragment` | active | Both subtypes are in the SET; failure is in a different code path — needs investigation |
| `tlg0545.tlg003` | Aelian *Epistulae Rusticae* | `letter` (20) | **commented out** | `letter` is in the 1640-tuple but NOT the 904/1610 set |
| `tlg0555.tlg008` | Clement of Alexandria | `paragraph` (6) | active | `paragraph` is in the 904/1610 set but NOT the 1640-tuple |
| `tlg0557.tlg004` | Epictetus *Gnomology 1-2* | `sentence` (8) | active | `sentence` is in neither set/tuple |
| `tlg0557.tlg005` | Epictetus *Gnomology 3-4* | `sentence` (67) | active | Same as above |
| `tlg0627.tlg013` | Hippocrates *Jusjurandum* (Oath) | `oath` (1) | **commented out** | `oath` is in neither set/tuple |
| `tlg0638.tlg004` | Philostratus *Heroicus* | `page` (94) | **commented out** | Body uses `page` (we added that in Fix3), but the active CTS refsDecl is single-level and disagrees with body structure |
| `tlg2003.tlg013` | Julian *Epistolae* | `letter` + `paragraph` | active | Hits **both** the set/tuple mismatches above |
| `tlg2003.tlg017` | Julian *Contra Galilaeos* | `paragraph` (65) | **commented out** | `paragraph` in set, not tuple, + no active refsDecl |
| `tlg2040.tlg004` | Basil of Caesarea *Epistulae* | `letter` (368) | **commented out** | `letter` not in set |

## Root-cause analysis

### Bug class 1: `structural_subtypes` SET ≠ TUPLE

`greek/build_modules/monolith_fn.py` contains **two different definitions
of `structural_subtypes`**:

- **SET at lines 904 and 1610** (used by `is_structural_div` / `is_leaf_div`):
  `{section, chapter, episode, hypothesis, fragment, book, volume, part,
  haeresis, subsection, paragraph, entry, work, excerpt, fable, fabula,
  centuria, homilia, choral, lyric, strophe, antistrophe, ephymnion,
  anapests, epode, trochees, page}`

- **TUPLE at line 1640** (used by `get_parent_hierarchy` to build book IDs):
  `(volume, book, chapter, part, haeresis, commentary, letter, epistle,
  work, homily, homilia, fragment, excerpt, fable, fabula, centuria,
  choral, lyric, episode, section, subsection, page)`

Symmetric difference:

| In SET only | In TUPLE only |
|---|---|
| hypothesis, paragraph, entry, strophe, antistrophe, ephymnion, anapests, epode, trochees | commentary, letter, epistle, homily |

Works using `letter`/`epistle`/`commentary`/`homily` pass through
`is_structural_div`'s SET check as non-structural — leaf detection never
fires — zero books. Conversely, works using `paragraph`/`hypothesis`/etc.
pass `is_structural_div` but the parent-hierarchy walker doesn't include
them in book IDs, which can produce inconsistent state downstream.

### Bug class 2: Custom subtype names

`Jebb_page` (Aristides), `sentence` (Epictetus), `oath` (Hippocrates) —
names outside the structural_subtypes vocabulary entirely.

### Bug class 3: Commented-out `<refsDecl>`

Several files have their canonical `<refsDecl>` blocks commented out (XML
comments around the `<cRefPattern>` elements). When the active refsDecl
disagrees with the body structure, the build silently produces nothing.

### Bug class 4: Non-numeric `n` at `subtype="book"` level

Sallust *Historiae* uses `<div type="textpart" subtype="book" n="Lep">`
where the `n` value is a Latin abbreviation (Lep = Lepidus, etc.). Fix1+Fix2
addressed non-numeric `n` values for the OGA/PTA hash-collision case but
didn't extend to the top-level `book` subtype.

## Why a quick fix is unsafe

The natural reflex is "just add the missing subtype names to both
definitions." This is **unsafe** because of how the structural_subtypes
list works:

- A subtype in the set is treated as **structural everywhere** — used to
  identify leaf divs and assemble book IDs.
- Adding `letter` would make every `<div subtype="letter">` a structural
  div. Currently many works (Plato *Letters*, Demosthenes *Epistulae*,
  Cicero's letters, Pliny's letters, etc.) produce **one book containing
  multiple letter divs as content**. After the change, those works would
  fragment into **one book per letter** — shattering their structure and
  invalidating all downstream interlinear data.

Measured blast radius of naive subtype additions (from the audit run):

| Subtype | Files currently using it | Currently working | Would shatter on naive add |
|---|---|---|---|
| `letter` | 18 | 13 (Cicero, Pliny, Plato, Demosthenes, ...) | 13 |
| `paragraph` | 69 | 65 (mostly First1KGreek fragmentary works) | 65 |
| `sentence` | 10 distinct files | 7 small First1KGreek works (18–1716 lines) | 7 |

This is the same blast-radius trap that bit us when we considered adding
`line` to `structural_subtypes` during Fix3 — single addition recovers a
few works but shatters dozens of currently-working ones.

## Fix candidates — ranked by safety

| # | Fix | Recovers | Blast radius | Recommendation |
|---|---|---|---|---|
| **C** | **Loudness gate** — abort build if any author-CSV-listed work produces 0 books/0 text_lines | All 65 (turns silent failure into loud) + future regressions | **None** — only adds error checking | **Do first.** Tiny code change. Forces investigation rather than blanket subtype additions. |
| D | Handle non-numeric `n` at `book` level (extend Fix1+Fix2 scope) | Sallust *Historiae* | Low — affects only `book` divs with alphanumeric `n` | Reasonable follow-up |
| E | Detect structural subtypes from `<body>` when active `<refsDecl>` is missing or single-level but body is deeper | Heroicus, Hippocrates *Oath*, Aelian *Epistulae*, ... | Medium — would change behavior for any work with commented-out CTS | Needs careful design |
| F | **refsDecl-driven structural detection** — when a file declares its own `<cRefPattern>`, use those subtype names for *that file only*, not the global structural_subtypes set | Most of the 11 misc cases | Medium — but per-file scoping limits collateral damage | Best long-term architecture |
| G | Per-work overrides — small manifest like `data/structural_overrides.csv` mapping work_id → custom-structural-subtypes | All 65 with manual curation | Zero (per-work explicit) | Violates "no work-specific fixes" rule unless framed as data, not code |
| **A** | Align SET ↔ TUPLE by union | 5 of the 11 misc works | **High** — would shatter 13 letter-works + 65 paragraph-works + a few others | **Do not do** without per-work scoping |
| **B** | Add `sentence`/`oath`/`Jebb_page`/etc. to structural_subtypes | 57 (54 Aristides + 2 Epictetus + Hippocrates) | **High** — would shatter 7 sentence-works and any future works using these subtypes | **Do not do** without per-work scoping |

## State of the audit tool

This defect was found by `data-prep/text_integrity/audit.py extended
--corpus perseus`. Run on demand:

```bash
./venv/bin/python3 -m data-prep.text_integrity.audit extended --corpus perseus
```

Run time: ~18 seconds for 1458 Perseus works. Output: Markdown + JSON
reports in `data-prep/text_integrity/reports/` (gitignored).

The audit reports class-A failures (real text drop/dup/reorder). The 65
zero-content works are the most actionable subset — they have `db_chars=0`
and `canonical_chars > 0` with 100% letter delta.

## Action items (not yet executed; this document is informational only)

- [ ] **Fix C: Loudness gate** — error in `create_greek_database.py` /
      `create_latin_database.py` when an author-CSV-listed work produces
      0 books or 0 text_lines after processing
- [ ] Investigate non-numeric `n` handling at `subtype="book"` level
      (Sallust *Historiae*)
- [ ] Design and prototype `refsDecl`-driven structural detection
      (Fix F) — most general long-term fix
- [ ] Consider per-work-overrides manifest (Fix G) for the 65 cases that
      can't be solved without explicit per-work hints

## Decision context

Date: 2026-05-17. The user explicitly chose to document these findings
rather than apply any fix immediately, to avoid the blast-radius traps
identified above. The current release-ready extended DB (post-GLAUx,
post-Bug-B, audit gate passed) ships with these 65 works missing —
documented as a known issue.
