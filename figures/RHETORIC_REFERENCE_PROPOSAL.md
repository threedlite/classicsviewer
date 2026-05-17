# Proposal: Incorporate the *Silva Rhetoricae* Rhetoric Reference into the App

Add the contents of the `figures/` mirror — Dr. Gideon Burton's **Silva Rhetoricae**
("The Forest of Rhetoric", `rhetoric.byu.edu`) — to Classics Viewer as a browsable,
fully offline **rhetoric reference** on both Android and iOS.

This is a *new feature surface*, not a change to the text-reading pipeline. It needs
some UI redesign (a reference/glossary mode the app does not currently have) but it
**does not touch** the existing `perseus_texts.db` schema or Room/DAO layer.

---

## 1. What the source content is

`figures/` holds a `wget` mirror of `rhetoric.byu.edu`, produced by `mirror.sh` and
then made self-contained by three helper scripts already in the folder:

- `relativize.py` — rewrites absolute same-site URLs to relative paths.
- `strip_external.py` — removes third-party links/scripts/images (keeps the CC notice).
- `purge_urls.py` — strips every remaining `http(s)://` reference, so the mirror loads
  with zero network access.

### Inventory (`figures/rhetoric.byu.edu/`)

| Section | Pages | Notes |
|---|---|---|
| `Figures/` | ~495 | The core: rhetorical figures A–Z (alliteration, chiasmus, …) |
| `Canons/` | ~31 | Invention, Arrangement, Style, Memory, Delivery |
| `Primary Texts/` | ~21 | Source-text excerpts |
| Branches of Oratory, Persuasive Appeals (ethos/pathos/logos), Four Changes, Encompassing Terms, Pedagogy, Sources, Recognition | ~70 | Supporting/structural pages |
| **Total HTML** | **615** | ~4.1 MB of markup |
| `Images/` | 287 raster | 12 navigation/award chrome (dropped); **276 `Images/Greek/` GIFs are content** — Greek-script figure names, transcribed to Unicode |
| **Mirror total** | — | 6.9 MB on disk |

### Anatomy of a figure page

Each figure page (e.g. `Figures/A/acoloutha.htm`) carries a consistent, structured
payload buried in legacy table/`<font>`/`<basefont>` markup:

- **Name** (the figure)
- **Etymology** — Greek/Latin root and gloss (`Gk. acolouthos, "following…"`)
- **Definition** — one or more paragraphs
- **Examples** — quoted illustrations (present on many but not all pages)
- **Related Figures** — cross-references with short descriptions
- **See Also** — links into Canons / Four Changes / Groupings
- A repeated **footer** with the CC license notice and site nav

The cross-reference graph (`Related Figures`, `See Also`, Latin/Greek synonym pages
like `~acoloutha.htm`) is the most valuable structural asset — it should survive
import as real links between entries, not as dead text.

---

## 2. Licensing — read this before shipping

**The mirror's `ATTRIBUTION.txt` and every page footer state the license as
Creative Commons Attribution 3.0 (CC BY 3.0)** — *not* CC BY-SA 3.0.

This matters and is good news:

- **CC BY 3.0** requires only **attribution**. There is **no ShareAlike obligation**,
  so incorporating it imposes **no license constraint on the rest of the app**.
- We must, per CC BY 3.0:
  1. Credit **Dr. Gideon O. Burton, Brigham Young University**.
  2. Name the work: **"Silva Rhetoricae" (rhetoric.byu.edu)**.
  3. Link/reference the license: `https://creativecommons.org/licenses/by/3.0/`.
  4. Indicate that the content was adapted (HTML → structured database).
- `figures/rhetoric.byu.edu/ATTRIBUTION.txt` must be preserved in-repo, and an
  **in-app attribution screen** must reproduce points 1–4.

The license is **confirmed CC BY 3.0** (per `figures/rhetoric.byu.edu/ATTRIBUTION.txt`
and the page footers). There is **no ShareAlike obligation**: shipping the feature
requires attribution only and places no licensing constraint on the app's code or
other databases.

---

## 3. Deployment size — the constraint, addressed

The app already ships large packaged databases (sample 163 MB, full 838 MB,
extended 2.7 GB compressed) via Play Asset Delivery / iOS resources. Against that,
this feature is **negligible**, *if* we import rather than bundle raw HTML.

| Option | Size shipped | Verdict |
|---|---|---|
| Ship the raw mirror (615 HTML + 287 images) | ~6.9 MB | ❌ wasteful: ~60% is legacy markup + chrome images |
| Ship only de-chromed HTML | ~1–1.5 MB | ❌ still drags a WebView + legacy-markup rendering |
| **Import to a small SQLite DB** (recommended) | **est. 300–700 KB compressed** | ✅ content only; native rendering |

**No image files ship.** The 287 raster files split into two kinds, and neither is
shipped:

- **12 navigation/award GIFs** (`Images/Navigation/`, `Images/Awards/`) — pure
  chrome (rules, green-diamond bullets, banners, old web-award badges). Dropped
  entirely; the native UI provides its own navigation and list styling.
- **276 `Images/Greek/` GIFs** — these are *content*: each is the Greek-script
  spelling of a figure's name, and the page text carries only the transliteration.
  They are **transcribed to Unicode polytonic Greek** at import time and stored as
  text in the `etymology_greek` field (see §4). The GIF itself is not shipped — the
  app renders the Greek natively, as it already does throughout.

The real payload is the text of ~600 entries plus the cross-reference graph: a few
hundred KB.

**Recommendation:** bundle the imported reference DB **directly inside the app
binary** — Android `app/src/main/assets/`, iOS app bundle resources — *not* as a Play
Asset Pack and *not* inside `perseus_texts.db`. At well under 1 MB it needs no asset
pack, no download step, and no first-launch extraction. It does not meaningfully
affect the Android base-APK/AAB limits or the iOS IPA/cellular-download limits.

---

## 4. Data-prep: HTML → `rhetoric.db`

Following the project rule that everything is scripted and repeatable (no manual
edits to generated files), add **one converter** under `figures/`:

```
figures/build_rhetoric_db.py        # parses the cleaned mirror -> rhetoric.db
```

Run order (each step already idempotent / re-runnable):

```
mirror.sh  ->  relativize.py  ->  strip_external.py  ->  purge_urls.py  ->  build_rhetoric_db.py
```

`build_rhetoric_db.py` responsibilities:

1. Walk `figures/rhetoric.byu.edu/`, classify each page by section (Figures, Canons, …).
2. Parse the consistent table structure to extract: name, etymology, definition
   paragraphs, examples, related figures, see-also.
3. **Normalize legacy encoding** — pages contain Windows-1252 bytes (e.g. curly
   quotes rendered as `�`); decode cp1252 → UTF-8 and clean `&nbsp;`/entity noise.
4. Resolve every internal `href` to a target entry **ID**, building a real
   cross-reference table. **Handle broken links gracefully** — see below.
5. **Resolve Greek-script terms** — where a page references an `Images/Greek/*.gif`,
   look up the Unicode polytonic Greek for that GIF in a checked-in mapping file
   (see below) and store it in `etymology_greek`. No image is read or shipped.
6. Strip all presentational markup; keep at most a minimal inline whitelist
   (`<i>`, `<b>`) so etymology emphasis survives.
7. Emit `figures/rhetoric.db` and a compressed `figures/rhetoric.db.zip`, plus a
   short quality report (entry counts, pages with/without examples, entries missing
   a Greek-term mapping, unresolved refs).
8. Copy the artifact into the app asset locations (mirroring how
   `create_perseus_database.py` populates `app/src/{debug,main}/assets/`).

### Broken links — graceful handling

The original site has genuine broken links — `href`s to pages that 404 on the live
site and are absent from the mirror (`relativize.py` already detects and lists these
"dangling" targets). The pipeline and the app must both **degrade gracefully**;
a broken source link is expected, not a build failure.

At **build time** (`build_rhetoric_db.py`):

- A cross-reference whose target resolves to no known entry ID is **dropped from
  `rhetoric_cross_refs`** — never written as a dangling row.
- If the dead `href` had visible anchor text, that text is **kept inline as plain
  text** (the reader still sees the term, just not as a tappable link) rather than
  discarded.
- Every dropped link is **counted and listed in the quality report** (source page →
  missing target), so coverage can be reviewed — but it **does not fail the build**.
- A page that fails to parse at all is logged, skipped, and counted; one malformed
  page never aborts the run.

At **runtime** (Android + iOS):

- Every cross-reference row already points at a valid entry ID (guaranteed by the
  build), so normal navigation cannot dead-end.
- As defense in depth, the detail screen still **guards every navigation**: tapping
  a cross-reference whose target is somehow missing is a no-op (optionally a brief
  "entry unavailable" message) — never a crash.

### Greek-term transcription (`figures/greek_terms.csv`)

The 276 `Images/Greek/*.gif` files are the only source for each figure's
Greek-script name. A **one-time transcription** produces a checked-in mapping file:

```
figures/greek_terms.csv      # columns: gif_name, greek_unicode
```

- This is **source data, not a generated artifact** — analogous to `SAMPLE_AUTHORS.csv`.
  It is checked in and consumed by every build, so the build stays fully repeatable;
  it is *not* a manual patch of generated output.
- `build_rhetoric_db.py` fails the build (or reports loudly) if a page references a
  Greek GIF with no row in `greek_terms.csv`, so coverage gaps cannot pass silently.

#### OCR pipeline (one-time, scripted, then human-reviewed)

The first pass is produced by a one-time helper script (e.g.
`figures/ocr_greek_terms.py`) and then **human-reviewed** before check-in. The GIFs
are small, low-resolution, indexed-palette images, so running OCR on the originals
is unreliable for polytonic Greek — the script must preprocess each GIF before
recognition.

**Engine:** Tesseract using the **`tessdata_best`** Ancient Greek model (`grc`) —
the high-accuracy LSTM training data, *not* the default or `tessdata_fast` models.
The lighter models routinely drop or mangle polytonic diacritics (breathings,
accents, iota subscript), which are exactly what must be captured here.

**Page-segmentation mode: `--psm 13` (raw line).** This matters. The obvious choice,
`--psm 7` ("single text line"), applies line-layout heuristics that *systematically*
misread a word-initial epsilon as omicron — e.g. `ekphrasis` came back with a
leading omicron instead of epsilon across dozens of entries. `--psm 13` bypasses
those heuristics, reads the leading letter correctly, and still handles the
multi-word terms (`hysteron proteron`, `kata enallagen`, …) as well as `--psm 7`.

**Per-GIF preprocessing with Pillow, in this order:**

1. **Grayscale** — `Image.open(path).convert("L")`, collapsing the indexed GIF
   palette to a plain 8-bit grayscale image.
2. **Upscale 4–6×** with `Image.LANCZOS` resampling — gives Tesseract enough pixels
   per glyph to resolve accents and breathings on these small source images.
3. **Binarize** to pure black/white — a fixed threshold, or **Otsu's method** to
   choose the cutoff automatically per image.
4. **Pad a 20 px white border** around the image — Tesseract's layout analysis
   needs quiet margin around the text or it clips edge glyphs.

**Review aid — side-by-side HTML table.** When the OCR pass finishes, the script
also emits a **review HTML page** (e.g. `figures/greek_terms_review.html`) — a
single table with one row per GIF:

| Column | Content |
|---|---|
| GIF filename | e.g. `acoloutha.gif` — identifies the source |
| Image | the original `Images/Greek/*.gif`, shown inline (`<img>`) so the reviewer sees exactly what was read |
| OCR text | the recognized Unicode polytonic Greek, rendered large in a Greek-capable font |

Placing the image and the recognized text **next to each other** lets a reviewer
scan the whole set quickly and spot diacritic errors (wrong breathing, missing
accent, dropped iota subscript) at a glance, instead of opening 276 GIFs
individually. The HTML page is a **local review artifact only** — not shipped, not
consumed by the build, and may be regenerated any time.

#### Two-stage post-OCR cleanup (repeatable)

The OCR script regenerates `greek_terms.csv` on every run, so corrections cannot be
hand-edited into that file — they would be overwritten, and editing a generated
file violates the project's repeatability rule. Two stages instead, both of which
a rerun reproduces exactly:

1. **Edge trim** — `trim_edges()` strips leading/trailing characters that are not
   letters (stray breathing marks, apostrophes, commas, periods Tesseract appends).
   This is a general algorithmic fix; it never touches the interior of a term or
   the internal spaces of multi-word terms.
2. **Corrections file** — `figures/greek_terms_corrections.csv` (`gif_name,
   corrected_greek`) holds human-reviewed fixes for genuine *in-word* misreads that
   no algorithm can repair (e.g. a misrecognized accent or an inserted glyph). Each
   row overrides that GIF's OCR result. This is **source data, checked in** — the
   captured output of human review — analogous to `greek_terms.csv` itself; the
   script fails if it references a GIF that does not exist.

**Verification:** every OCR result is **human-reviewed** for polytonic accuracy
(breathings, accents, iota subscript) via the review table above; the review HTML
flags rows fixed by the corrections file as `(corrected)`. The OCR script remains a
convenience for the first pass — run once, reviewed once, then maintained only
through `greek_terms_corrections.csv` — and is **not** part of the repeatable
`build_rhetoric_db.py` pipeline.

### Proposed schema (`rhetoric.db`)

Kept in its **own database file** so it never participates in Room schema
validation against `perseus_texts.db`.

```sql
CREATE TABLE rhetoric_sections (
    id          TEXT PRIMARY KEY NOT NULL,   -- 'figures','canons',...
    title       TEXT NOT NULL,
    sort_order  INTEGER NOT NULL
);

CREATE TABLE rhetoric_entries (
    id              TEXT PRIMARY KEY NOT NULL, -- slug, e.g. 'alliteration'
    section_id      TEXT NOT NULL,
    name            TEXT NOT NULL,
    etymology_greek TEXT,                      -- Unicode polytonic, nullable
    etymology       TEXT,                      -- transliteration + gloss, nullable
    definition      TEXT NOT NULL,
    examples        TEXT,                      -- nullable
    source_path     TEXT NOT NULL              -- original .htm, for traceability
);

CREATE TABLE rhetoric_cross_refs (
    from_id     TEXT NOT NULL,
    to_id       TEXT NOT NULL,
    kind        TEXT NOT NULL,               -- 'related' | 'see_also' | 'synonym'
    note        TEXT,
    PRIMARY KEY (from_id, to_id, kind)
);

CREATE INDEX idx_entries_section ON rhetoric_entries(section_id);
CREATE INDEX idx_entries_name    ON rhetoric_entries(name);
CREATE INDEX idx_xref_from       ON rhetoric_cross_refs(from_id);
```

A FTS table over `name`/`etymology`/`definition` can be added later for fast search.

---

## 5. App integration & redesign

The app today is built around a single navigation spine (Language → Author → Work →
Book → Lines). A reference work has no author/work hierarchy, so it needs its **own
entry surface**. Three integration points:

### 5.0 Isolation from the existing text display (hard requirement)

**The rhetoric feature does not touch, reuse, or modify any of the existing
language text-display code.** That code path — the Lines/Book reading view,
interlinear word-by-word morphology, translation-swipe alignment, word-tap
highlighting — is built for *classical text indexed by line number*. A rhetoric
entry has none of that structure: it is encyclopedia prose. Routing it through the
reading view would force invasive, regression-prone changes to shared code.

Instead, rhetoric ships as **entirely new, self-contained screens**:

- New activities/fragments (Android) and new view controllers / SwiftUI views (iOS)
  that import **nothing** from the line-reading code.
- Its own data layer (`RhetoricDbHelper` / `RhetoricDAO`) against its own
  `rhetoric.db` — no Room entities, no DAO changes, no shared queries.
- The only thing it shares is global app *theme/preferences* (font size, color
  inversion), read the same way other screens read them — no edits to those.

Net effect: the language reading code is untouched. The rhetoric display is much
simpler than the reading view, so this is the *less* code, not more.

### 5.1 A new top-level "Rhetoric" reference section

Rhetoric is a **separate top-level menu option**, sitting beside — not inside — the
language list, because it is structurally unlike a language corpus (no
Author/Work/Book hierarchy).

- **Android:** a new `RhetoricActivity` / fragment set under
  `app/src/main/java/com/classicsviewer/app/` — a section list → entry list (A–Z,
  with letter index) → entry detail. Data access via a small raw-SQL helper class
  (`RhetoricDbHelper`) that opens the bundled `rhetoric.db` read-only. **No Room
  entities, no DAO additions, no Room version bump** — this respects the hard rule
  in `CLAUDE.md` against changing tracked schemas.
- **iOS:** mirror the existing DAO pattern with a new `RhetoricDAO.swift` under
  `ios/ClassicsViewer/Database/` plus SwiftUI/UIKit screens consistent with the
  current navigation.

### 5.2 How an entry displays

An entry detail screen is a **single vertically scrolling document** — no lines, no
columns, no swipe panes. It is rendered natively (no WebView) as a list of typed
rows, so cross-references stay tappable and the app theme applies:

| Row type | Content | Style |
|---|---|---|
| Title | figure/term name | large heading |
| Etymology | Greek-script term (Unicode) + transliteration + gloss | smaller, italic, optional |
| Definition | one or more prose paragraphs | body text |
| Examples | quoted illustrations | indented / set off as block quotes, optional |
| Related Figures | each: name + short note | **tappable** → navigates to that entry |
| See Also | cross-section links (Canons, Four Changes…) | **tappable** → navigates |

Concretely:

- **Android:** a `RecyclerView` with the row types above (or a `ScrollView` +
  `LinearLayout`). Cross-reference rows carry the target entry ID and on tap push a
  new `RhetoricEntryActivity`/fragment. Inline emphasis (`<i>`/`<b>` kept by the
  importer) is applied with simple spans.
- **iOS:** a `UITableView` (sectioned) or SwiftUI `ScrollView`/`List` with the same
  row types; cross-reference rows navigate via the standard navigation stack.

The two list screens above it are equally plain: a **section list** (Figures,
Canons, …) and an **A–Z entry list** with a letter index. None of this needs the
reading view's machinery.

This is where the cross-reference graph pays off — Related / See-Also turn the
reference into a browsable web of entries rather than a flat glossary.

### 5.3 Cross-linking from the reading experience (optional, phase 2)

The dictionary/word-lookup UI could surface a "rhetoric" entry when a looked-up term
matches an entry name — turning the reference into something readers hit in context,
not just a standalone glossary. Defer until the standalone feature ships.

### 5.4 Attribution (required)

A dedicated **"About this reference"** screen reachable from the section, reproducing
the CC BY 3.0 credit (see §2).

In addition, the project's existing **license files must be updated** to include the
Silva Rhetoricae attribution — the credit must travel with the app, not live only on
the new screen:

- **`LICENSE.txt`** (repo root, the bundled licenses file — currently Perseus / LSJ /
  Scaife etc.): add a *Silva Rhetoricae* section — title, Dr. Gideon O. Burton
  (Brigham Young University), `rhetoric.byu.edu`, **CC BY 3.0**
  (`https://creativecommons.org/licenses/by/3.0/`), and a note that the content was
  adapted from HTML into a structured database.
- **In-app license screen** (`app/src/main/res/layout/activity_license.xml` /
  `LicenseActivity`, and the iOS equivalent): ensure the new entry is shown there.
- **`web-app/views/license.ejs`** — update too **if** the web app ships this content.
- `figures/rhetoric.byu.edu/ATTRIBUTION.txt` stays in-repo unchanged as the
  provenance record.

Note the license distinction: most existing entries in `LICENSE.txt` are CC BY-**SA**
3.0 (Perseus); Silva Rhetoricae is CC BY 3.0 (no ShareAlike) — keep that wording
accurate rather than copying a neighboring entry's license line.

### What "redesign" actually means here

- **Rhetoric is its own top-level menu option**, kept distinct from the language
  list — it is a reference work, not a language corpus, and mixing it into the
  language picker would misrepresent both. The main menu therefore gains a separate
  "Rhetoric" entry point (decided).
- Search currently scopes to texts; it may be worth letting it also return rhetoric
  entries (phase 2).
- Settings such as color inversion / font size should apply to the new screens for
  consistency.

---

## 6. Phased plan

| Phase | Scope |
|---|---|
| **1 — Data** | Transcribe the 276 Greek GIFs into `greek_terms.csv` (OCR + review); write `build_rhetoric_db.py`; produce `rhetoric.db` (+ zip) and quality report; verify encoding, Greek-term coverage, and graceful broken-link handling; update `LICENSE.txt` with the CC BY 3.0 attribution. |
| **2 — Android** | `RhetoricDbHelper` + section/list/detail screens (with cross-ref navigation guards); attribution screen + license-screen entry; bundle DB in `assets/`. |
| **3 — iOS** | `RhetoricDAO` + equivalent screens (with navigation guards); attribution + license-screen entry; bundle DB in app resources. |
| **4 — Polish** | Letter index, in-section search/FTS, optional cross-link from word lookup. |

---

## 7. Open questions

1. **Scope of import** — ship all sections, or Figures + Canons first and add
   Pedagogy / Primary Texts / Sources later?
2. **Examples fidelity** — examples mix prose, verse, and non-English snippets;
   confirm plain-text storage is acceptable vs. preserving light inline formatting.
3. **Bundle vs. asset pack** — proposal recommends in-binary bundling given the
   sub-1 MB size; confirm that is acceptable for both stores.

---

## Summary

- Source: ~600 content pages of *Silva Rhetoricae*, **CC BY 3.0** (attribution only —
  no constraint on the rest of the app).
- Convert HTML → a self-contained **`rhetoric.db`** (est. 300–700 KB compressed) via
  one repeatable `build_rhetoric_db.py` script. No images ship: 12 chrome GIFs are
  dropped; the 276 Greek-script GIFs are transcribed to Unicode polytonic Greek.
- Bundle that DB **in the app binary**, separate from `perseus_texts.db` — so it adds
  negligible deployment size and **cannot** trigger Room schema-validation crashes.
- Add a native "Rhetoric" reference section (section → entry list → detail with
  tappable cross-references) on Android and iOS. Broken source links degrade
  gracefully — dropped at build time, guarded at runtime, never a crash.
- Satisfy CC BY 3.0: an in-app attribution screen **and** an updated `LICENSE.txt` /
  in-app license screen carrying the Silva Rhetoricae credit.
