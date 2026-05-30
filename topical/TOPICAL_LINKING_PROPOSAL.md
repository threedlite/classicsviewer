# Topical Linking — design & implementation

## Summary

A **Topical Links** button (icon: two overlapping circles) on the edit-bookmark
screen opens a standalone list of *other passages in the corpus that are
semantically related* to the bookmarked line. The screen does not share code
with the dictionary-occurrences screen. Each result row (a **target** passage)
shows a human-readable **English** author / work / book reference, a *limited*
original Greek/Latin snippet, and the target's *aligned English translation*
snippet — read from the existing translation-alignment system without modifying
it.

Relatedness is computed **language-internally**: per passage, a TF-IDF vector
over its content lemmata (nouns / verbs / adjectives / proper nouns) sourced
from the interlinear in `translation_segments`. Top-K cosine-similar passages
are precomputed offline. Nothing in the similarity pipeline depends on English,
on translations, or on any external model.

The topical-link data ships as the on-demand asset pack **`topical_pack`** —
one DB file per supported language inside the one pack — mirroring
`references_pack`. The pipeline is **language-pluggable**: a single registry
maps each language to its `authors.language` value, its interlinear translator,
its lemma parser, and its db filename, so adding a language is a registry entry
plus a per-language parser if the interlinear format differs.

The pack contains two DBs:

- `topical_greek.db`
- `topical_latin.db`

Each DB contains two tables:

1. `bookmark_positions` — one row per addressable text position, tagged with the
   passage it belongs to.
2. `topical_links` — for each passage, its top-K most semantically similar
   passages, with a cosine-similarity score.

**Both DBs are always generated from the EXTENDED database** (the superset),
regardless of which main DB tier (sample / full / extended) the user has
installed. Because a related passage may point at a position that is not present
in the loaded `perseus_texts.db` (e.g. the user only has the sample DB), the app
**filters out any related passage whose position does not exist in the loaded
database** before showing the list (see "Filtering against the loaded
database"). The `(book_id, line_number, sequence_number)` natural key is stable
across all three tiers, so it bridges the topical pack to whichever main DB is
loaded.

The topical DBs are accessed via a **raw-SQLite helper, not Room** (exactly like
`RhetoricDbHelper`), so there is no Room schema change and no version bump (per
the backwards-compatibility rules in `CLAUDE.md`). **`perseus_texts.db` is never
modified — no table is added and nothing about it changes; it is only read.**

---

## Motivation

The app already lets a reader jump between every occurrence of a *word/lemma*
(dictionary occurrences). There is no way to ask "what *else* in the corpus is
*about the same thing* as this passage?" Topical linking fills that gap: from
any bookmark a reader can discover thematically/semantically adjacent passages
across authors and works, even when they share no vocabulary.

Topical similarity is computed **language-internally**, with no external model
and nothing in English. Each passage is represented by a TF-IDF vector over its
content lemmata, sourced from the interlinear translation stored in
`translation_segments` for that language; cosine similarity over those vectors
gives the topic signal. Lemma + part-of-speech are read directly from the
interlinear, so the build needs no model weights, no GPU, and no internet.

The extended corpus contains 13 other languages (Sanskrit, Hebrew, Coptic,
Syriac, Arabic, …); each becomes eligible for a topical pack as soon as it has
an interlinear translator in `translation_segments` whose pipe format a parser
can decode (Greek and Latin both do; their parsers differ because their formats
differ).
### Representative output (full Greek build, source passage = Plato *Phaedo* 108a–d, the myth of the afterlife)

```
1   0.189  Plato, Meno
2   0.188  Plato, Theaetetus
3   0.166  Acts of John
4   0.160  Genesis
5   0.159  Simplicius, on Aristotle De Caelo
6   0.158  Philoponus, on Aristotle De Gen.
7   0.156  Aristotle, Physica
8   0.152  Eusebius, Demonstratio Evangelica
9   0.147  Ammonius, on De Interpretatione
10  0.146  Plato, Republic (Book 6)
11  0.145  Didache
12  0.145  Sextus Empiricus, Adversus Math.
```

Top neighbours are Plato dialogues, Aristotelian metaphysics + commentators,
and patristic / biblical eschatology — recognisably topical.

---

## User-facing behavior

### 1. New button on the edit-bookmark screen

- **Screen:** `BookmarkEditorActivity`
  (`app/src/main/java/com/classicsviewer/app/ui/BookmarkEditorActivity.kt`,
  layout `app/src/main/res/layout/activity_bookmark_editor.xml`).
- Add a `MaterialButton` labeled **"Topical Links"** (or "Related Passages")
  alongside the existing `copyButton` / `saveButton` / `cancelButton`.
- **Icon:** two overlapping circles (a Venn-style mark) to suggest topical
  overlap / shared subject matter. Use it as the button's leading icon (and as
  the action's icon anywhere the feature is surfaced).
- The button is shown only when **all** of the following hold:
  1. The topical pack is installed and contains a DB for the bookmark's
     language. The language is derived from its author/work (as the app already
     does), then looked up in the language registry; languages with no DB in the
     pack (today, everything except Greek and Latin) simply never show the
     button.
  2. The bookmarked position resolves to a row in the pack's
     `bookmark_positions` with at least one entry in `topical_links`.
  3. After filtering against the loaded `perseus_texts.db`, at least one related
     passage remains (see "Filtering against the loaded database").
  Otherwise the button is hidden (or disabled with a "No related passages"
  affordance).

### 2. New "Topical Links" list screen

A **standalone** screen with its **own** Activity, adapter, and row layout. Use
the dictionary-occurrences screen (`LemmaOccurrencesActivity` /
`OccurrenceAdapter` / `item_occurrence.xml`) **only as a visual reference** —
**do not reuse, subclass, or share its code.** It is a heavily-used screen that
may change for unrelated reasons; topical links must not break when it does, and
this feature is non-essential so it should never destabilize the occurrences
flow either. Duplicating the bit of layout/styling we want is the right call
here. The row is a richer, three-part layout and has **no word highlighting**
(relatedness is semantic, not a literal match).

Each result row represents a **target** (related) passage and shows three
things, all looked up **read-only** from the loaded `perseus_texts.db`:

- **Reference (human-readable English):** author + work + book + line — e.g.
  *"Homer, Iliad, Book 1.15"* — from `authors.name` (already Latinized English),
  `works.title_english`, and `books.label`, resolved via the target's `book_id`.
- **Limited original snippet:** a short, *truncated* Greek/Latin excerpt of the
  target passage (from `text_lines`), rendered plain (no highlighting).
- **Aligned English translation snippet:** a short, *truncated* excerpt of the
  translation aligned to **the target passage**, fetched for the target's
  position via the existing
  `PerseusRepository.getTranslationSegments(bookId, startLine, endLine)`
  (`translation_segments` / `translation_lookup`). The target is what carries the
  aligned translation. This **reuses and does not modify the translation
  alignment system** — read-only, no re-alignment, no new tables.

Notes:
- **"Limited"** = truncated to keep rows compact (e.g. the first line / first
  ~N characters of each snippet), not the full passage.
- Use a dedicated row layout `item_topical.xml` and a dedicated adapter —
  **not** `item_occurrence.xml` or `OccurrenceAdapter`. Highlighting isn't
  implemented at all (nothing to disable).
- Optionally show the similarity score (faint, right-aligned).
- Tapping a row opens the target passage in the reader at its
  `(book_id, line_number, sequence_number)`, using the app's existing
  open-passage-in-reader navigation (a stable entry point, not occurrences code).
- Results are ordered by descending similarity and capped (e.g. top 25) **after**
  the loaded-DB filter.

---

## Position identity

The canonical unique key for an addressable position is:

```
(book_id, line_number, sequence_number)
```

`line_number` restarts within each book, so `book_id` is required for
uniqueness. This matches the existing bookmark uniqueness index in
`BookmarkEntity` (`@Index(value = ["book_id","line_number","sequence_number"], unique = true)`)
and the `text_lines` schema in `shared/database_schema.py`.

`bookmark_positions` therefore keys on `(book_id, line_number, sequence_number)`
with a stable integer surrogate `position_id` for compact joins *within the
topical DB*, and carries `author_id` / `work_id` as denormalized columns for
grouping, display, and author/work-level filtering.

**Portability across DBs is the reason the natural key matters.** The topical
pack is generated from the extended DB and carries its own `position_id` values;
those surrogates are meaningless in the loaded `perseus_texts.db`. Only the
natural key `(book_id, line_number, sequence_number)` is stable across the
sample/full/extended tiers, so it is the join used to (a) resolve a bookmark to
its passage in the topical pack and (b) check whether a related passage exists
in the loaded main DB.

---

## Schema (tables in each topical DB)

These tables live in the standalone `topical_greek.db` / `topical_latin.db`
files (both bundled in the single `topical_pack`), **not** in `perseus_texts.db`.
They are built from the extended DB by a dedicated build script (see "Build
pipeline") and accessed at runtime via a raw-SQLite helper — never Room. The
schema below is identical for every language DB.

### `bookmark_positions`

One row per addressable position (effectively per `text_lines` row that is a
valid bookmark target). Each row is tagged with the `passage_id` of the
multi-line block it belongs to; embeddings and links are computed at the
passage level (see "Granularity" below).

```sql
CREATE TABLE bookmark_positions (
    position_id      INTEGER PRIMARY KEY NOT NULL,  -- stable surrogate id
    book_id          TEXT    NOT NULL,
    line_number      INTEGER NOT NULL,
    sequence_number  INTEGER NOT NULL,
    author_id        TEXT    NOT NULL,              -- denormalized for display/filtering
    work_id          TEXT    NOT NULL,              -- denormalized for display/filtering
    passage_id       INTEGER NOT NULL,              -- the passage this position belongs to
    UNIQUE (book_id, line_number, sequence_number)
);
CREATE INDEX idx_bookmark_positions_lookup
    ON bookmark_positions (book_id, line_number, sequence_number);
CREATE INDEX idx_bookmark_positions_passage
    ON bookmark_positions (passage_id);
CREATE INDEX idx_bookmark_positions_work
    ON bookmark_positions (work_id);
```

`position_id` is a compact integer key; `passage_id` groups the positions that
make up one embedding unit. A passage has no separate table — it is just the set
of positions sharing a `passage_id`. The passage's **anchor** (used for the
display reference and for navigation) is its first position, i.e.
`MIN(line_number, sequence_number)` within the `passage_id`.

### `topical_links` (mapping table)

For each source passage, its top-K most similar target passages.

```sql
CREATE TABLE topical_links (
    source_passage_id  INTEGER NOT NULL,
    target_passage_id  INTEGER NOT NULL,
    rank               INTEGER NOT NULL,   -- 1 = most similar
    similarity         REAL    NOT NULL,   -- cosine similarity, 0..1
    PRIMARY KEY (source_passage_id, target_passage_id)
);
CREATE INDEX idx_topical_links_source
    ON topical_links (source_passage_id, rank);
```

Keying the mapping at passage level (rather than position level) avoids storing
identical link rows for every line inside the same passage, shrinking the table
by roughly the passage size.

**Store more than you display.** Because the pack is built from extended but may
be queried against the smaller sample/full DB, the cross-DB filter (below) drops
targets that aren't in the loaded DB. To ensure enough survive, store a
generous K in the table (e.g. **K = 50**) and let the app display a smaller
number (e.g. 25) *after* filtering.

### App query (raw SQL via the topical helper)

From a bookmarked line, find its passage, then its related passages' anchor
positions:

```sql
-- 1) passage_id for the bookmarked line (in the topical pack)
SELECT passage_id FROM bookmark_positions
WHERE book_id = ? AND line_number = ? AND sequence_number = ?;

-- 2) related passages, resolved to each target passage's anchor position
SELECT anchor.book_id, anchor.line_number, anchor.sequence_number,
       anchor.author_id, anchor.work_id, tl.similarity
FROM topical_links tl
JOIN bookmark_positions anchor
  ON anchor.position_id = (
       SELECT position_id FROM bookmark_positions bp
       WHERE bp.passage_id = tl.target_passage_id
       ORDER BY bp.line_number, bp.sequence_number
       LIMIT 1
     )
WHERE tl.source_passage_id = ?
ORDER BY tl.rank;   -- no LIMIT here; the app filters then caps
```

(If the correlated-subquery anchor lookup is a concern, precompute an
`anchor_position_id` per passage during the build and store it once — e.g. as an
extra column on the anchor's `bookmark_positions` row — to make this a plain
join. Decide during the spike.)

The candidate target keys returned from the topical pack are then filtered and
hydrated against the **loaded** `perseus_texts.db` (see next section): only keys
that exist there are kept, and their author/work/book labels and line text come
from the loaded DB's `authors` / `works` / `books` / `text_lines` tables via this
feature's **own** read-only queries (the same standard tables other screens read,
but not shared code).

---

## Filtering against the loaded database

The topical DBs are built from the **extended** corpus, but a user may have
only the **sample** or **full** main DB installed. A related passage returned
from the pack can therefore point at a position that does not exist in the
loaded `perseus_texts.db`. **Such rows must not be shown.**

Rule: for each candidate target `(book_id, line_number, sequence_number)`
returned by the topical helper, confirm the position exists in the loaded
`perseus_texts.db` before displaying it. Drop any that don't, then cap the list
at the display limit. Concretely:

1. The topical helper returns the ranked candidate keys (no limit).
2. For those candidates, run this feature's **own** read-only query once
   (`SELECT ... FROM text_lines WHERE (book_id, line_number, sequence_number) IN (...)`)
   to both **test existence** and **fetch the original snippet**. (Its own query
   — don't depend on the occurrences/reader lookup code.)
3. Keep candidates that exist, preserving similarity rank, and stop at the
   display cap (e.g. 25).

This is also why the table stores an over-provisioned K (e.g. 50): on the sample
DB a large fraction of extended-corpus targets won't be present, so the extra
candidates keep the list usefully full. The same rule means the **button
visibility** check must run this filter — if nothing survives, hide the button.

Note: the *source* bookmark always resolves, since extended is a superset of
sample/full, so a loaded position is guaranteed to exist in the pack.

---

## Build pipeline

The build is one self-contained script — `topical/build_topical_links.py
<language>` — driven by the language registry; no per-language branching.
Defaults: `N=10` (passage window), `K=50` (links per source), `min_bag=8` (drop
passages with fewer content lemmata), `--exclude-scope work` (same-work
neighbours never link). `--max-books` exists for dev slices.

`topical/` is the home: it's a post-assembly, cross-language artifact, so it
sits outside the per-language modules (like `figures/build_rhetoric_db.py`).
It needs only the project `./venv` with scikit-learn (which pulls scipy +
numpy). No GPU, no torch, no `sentence-transformers`, no internet, no external
models.

Steps:

1. **Look up the language** in the registry → `authors.language` value, db
   filename, interlinear translator string, lemma parser. Hard-fail on unknown
   language.
2. **Read the extended DB** (`data-prep/perseus_texts_extended.db`), iterating
   the language's books in order.
3. **Enumerate positions.** Populate `bookmark_positions` from `text_lines`
   (every `(book_id, line_number, sequence_number)`), collapsing duplicate
   triples and denormalising `author_id` / `work_id`.
4. **Form passages.** Group each book's positions into fixed, non-overlapping
   N-position windows.
5. **Build content-lemma bags.** For each book, read its interlinear segments
   from `translation_segments` (one query per book) and run the language's
   parser to extract per-token (lemma, POS); keep content POS, NFC-normalise
   the lemma, drop a small NFC-normalised light-verb / function-word stoplist.
   Distribute lemmata to each passage by its line range.
6. **Vectorise.** TF-IDF over the content-lemma bags
   (`sublinear_tf=True`, `max_df=0.30`, `min_df=3`), L2-normalised. Passages
   whose bag is smaller than `min_bag` get a zero row — they neither source
   nor target links (this drops the tiny scholia / lexicon fragments whose
   rare-lemma matches would otherwise dominate the top).
7. **Nearest neighbours.** Chunked sparse cosine `Q @ X.T`; for each source,
   mask out same-work targets and self, take top-K (cosine > 0). Write to
   `topical_links` with rank + similarity.
8. **Compress and place** the DB as `topical_<language>.db.zip` in the three
   locations the apps read from: `topical_pack/src/main/assets/` (release AAB
   source of truth), `app/src/debug/assets/topical/` (debug APK fallback), and
   `ios/ClassicsViewer/Resources/` (iOS bundle). The script `mkdir -p`'s them
   for fresh clones.

The interlinear format differs by language, so each registry entry names its
parser:
- **Greek** — treebank interlinear (translator
  `Interlinear (Beta, generated from app dictionary and treebank)`) with
  explicit `~ POS` markers; parser keeps NOUN / PROPN / VERB / ADJ.
- **Latin** — AI-generated interlinear (translator
  `Interlinear (Beta, AI-generated from app dictionary)`) without POS markers;
  parser takes the lemma from the field immediately after each `**gloss**`
  field and relies on the (larger) Latin function-word stoplist instead of POS.

Must hard-fail if the source DB is missing or if a passage of any size produces
zero non-empty bags (means the interlinear lookup is broken).

### Build time

- **Greek: 14.6 min** — 331,767 passages, vocab ≈ 58k after `max_df` / `min_df`,
  `min_bag=8` drops ≈ 99k tiny passages.
- **Latin: 1.0 min** — 36,639 passages.
- **Combined ≈ 16 minutes**, CPU only.

### Regeneration dependency (keep topical DBs in sync with text parsing)

⚠️ The topical DBs are tightly coupled to the **exact text segmentation** of
the extended build that produced them. They are bound to `perseus_texts.db` only
through the natural key `(book_id, line_number, sequence_number)` — they store no
copy of the text itself. So if a future change to the text-build pipeline (the
per-language module builds or `data-prep/assemble_database.py`) alters **how
text/XML is split into lines, how line numbers or `sequence_number`s are
assigned, or sentence/segment boundaries**, then the same key will point at
*different* text than it did when the embeddings were computed. The precomputed
passages and links would silently become wrong, and a user's existing bookmark
would resolve to a shifted passage.

**Therefore: any change that affects line/sequence numbering or segmentation
requires rebuilding all topical DBs from the updated extended DB.** Treat them
as a derived artifact of the text build, not an independent dataset. The same
caveat applies to user bookmarks generally (they already key on the same
triple), but topical links amplify it because every link's *target* is also
keyed this way.

#### Sync model: release-based (no runtime comparison, no extra main-DB reads)

Sync is handled **at the release level**, not by comparing values at runtime:

- The topical pack is a **derived artifact of the text build** and ships in the
  **same app release** as the `perseus_texts.db` it was built against. Both are
  versioned by the app's `versionCode`.
- Reuse the existing **re-extract-on-version-code-change** mechanism that
  `RhetoricDbHelper` already implements: when the version code changes the helper
  re-extracts its bundled DB. The main DB extraction is also version-keyed, so on
  every app update the pack and the main DB are replaced **together**. A device
  can never end up pairing a release-N pack with a release-M main DB.
- **Because of this the app does no runtime staleness check and reads nothing
  extra from `perseus_texts.db`.** We deliberately do *not* read the `build_time`
  row — that sidesteps the per-mode-timestamp problem entirely and keeps the main
  DB strictly untouched.
- Optional, build-time only: stamp a build id into a `meta` table **inside the
  topical DB itself** purely for diagnostics/logs. It is never used for runtime
  gating.

The release discipline is the contract, so it **must be documented in
`BUILD.md`** (next).

#### BUILD.md documentation (required deliverable)

Add a "Topical Links" section to `BUILD.md` stating clearly:

1. **When to rebuild:** any change to the text pipeline that affects how text/XML
   is split into lines or how `line_number` / `sequence_number` are assigned
   (i.e. anything in `assemble_database.py` or the per-language module builds that
   moves the `(book_id, line_number, sequence_number)` → text mapping) **requires
   rebuilding all topical DBs from the updated extended DB before release.**
2. **How to rebuild:** the exact command(s)
   (`build_topical_links.py <language>` for each registered language), which venv
   to use (one with `torch` + `sentence-transformers`), expected runtime
   (~2–2.5 h, embedding-bound), and where the output zips must land (the
   `topical_pack` module + debug/main assets + iOS `Resources/`).
3. **Release rule:** the topical DBs and the main DB must be built from the
   **same text build** and shipped in the **same release** (same `versionCode`).
   Never ship a topical pack built against a different text build than the main
   DB in that release.
4. **Ordering:** the topical DBs are built **after** the extended DB is complete
   (they read it), and slot into the existing build order in `BUILD.md`.

This is a non-optional part of the feature: shipping a pack out of step with the
text build is the one way to make links point at the wrong passage.

### Granularity: fixed multi-line passages

Embeddings are computed over **passages**, defined as fixed, non-overlapping
windows of **N consecutive lines within a book** (default **N = 10**, tunable).
This is deliberately larger than a sentence and is the most general rule that
works uniformly across the whole corpus:

- It is meaningful: ~10 lines is paragraph-sized, enough context for the model
  to capture topic — a single verse line is too short and too noisy.
- It is uniform: every passage is comparable in size, unlike the text's native
  section/milestone units (Bekker, Stephanus, chapter), which range from a
  couple of lines to dozens and would produce uneven embeddings. (Native units
  remain a possible future refinement, but fixed windows are the general
  default — consistent with the project's "most general solution" rule.)
- It applies identically to verse and prose, since both are stored as
  `text_lines` rows.

Every bookmark position still exists in `bookmark_positions`; it simply inherits
the `passage_id` of the window it falls in, and the related-passages list
navigates to each related passage's anchor line.

**Scale (per language DB, built from extended, N = 10).** Each DB covers only its
own language's positions, so the two DBs split the corpus rather than duplicating
it. Figures below are the **actual built totals** (positions = `text_lines` rows
for that language after collapsing duplicate triples; passages = sum over books
of `ceil(rows / 10)`; links = stored after same-work exclusion + 0.3 cosine
floor, capped at K = 50 per passage):

| Pack            | source        | positions  | passages | links      | zip    |
|-----------------|---------------|------------|----------|------------|--------|
| `topical_greek` | extended (greek) | 2,311,171 | 331,767  | 11,640,550 | 355 MB |
| `topical_latin` | extended (latin) | 360,007   | 36,639   |    ~1.4 M  |  55 MB |

(Counts are from the **TF-IDF rebuild**: K=50 capped, no similarity floor;
~99k tiny Greek passages dropped by `min_bag=8` so they neither source nor
target links. Links are fewer than the K×passages cap because many sources
have no further valid targets above zero cosine after same-work exclusion.)

(The 0.3 floor + work-scope exclusion barely reduced links — 16,588,350 vs the
16,588,700 cap — i.e. almost every passage has ≥50 cross-work neighbors above
0.3 cosine.)

Across 167,962 Greek books and 1,390 Latin books. Note Greek passages (~332K)
run ~1.4× higher than a naive lines ÷ 10 (~231K): extended splits First1KGreek
works into many small books (avg ~13.8 lines/book), so per-book windowing
produces many partial windows. Because those small books are sections of larger
works, neighbor exclusion is done at the **work** level (not book), so a passage
doesn't merely link to adjacent sections of its own work.

These are the only sizes that ship — there is no per-main-tier variant. The
sample/full/extended distinction only affects how many rows survive the loaded-
DB filter at display time, not the pack contents.

Rollout: build and validate the **Greek** DB first against a small slice (a
few works) to confirm link quality and the filter behavior, then build the full
Greek and Latin DBs.

---

## Android integration

### Packaging (asset-pack module, mirrors `references_pack`)

- **Delivery: on-demand asset pack**, mirroring `references_pack`.
  Single module `topical_pack/` with `build.gradle`:
  ```
  plugins { id 'com.android.asset-pack' }
  assetPack { packName = "topical_pack"
              dynamicDelivery { deliveryType = "on-demand" } }
  ```
  Declared in `settings.gradle` and `app/build.gradle`'s `assetPacks` list. The
  pack bundles every per-language zip (`topical_greek.db.zip`,
  `topical_latin.db.zip`, …). All-or-nothing — every language's DB downloads
  together (the user doesn't pay for the pack until they tap the menu entry).
- **Three asset locations** (the build script copies to all three):
  - `topical_pack/src/main/assets/topical_<lang>.db.zip` — source of truth for
    release AAB / Play Asset Delivery.
  - `app/src/debug/assets/topical/topical_<lang>.db.zip` — debug-build fallback
    (asset packs are AAB-only, so debug APKs need their own copy under a `topical/`
    subdir, exactly like references uses `assets/references/`).
  - `ios/ClassicsViewer/Resources/topical_<lang>.db.zip` — iOS bundle.
  All three are gitignored. `app/src/main/assets/` no longer holds them.
- **Runtime access — `TopicalPackManager`** (mirrors `ReferencesPackManager`):
  Play Core `AssetPackManager` facade with the same API surface
  (`isInstalled` / `getAssetsPath` / `startDownload` / `cancelDownload` /
  `removeAssetPack` / `showConfirmationDialog`). In release it returns
  `AssetPackManager.getPackLocation(packName).assetsPath()`; in debug it copies
  `assets/topical/*` into `cacheDir/topical_pack_cache/` on first use and returns
  that path. `TopicalDbHelper` calls `TopicalPackManager.getAssetsPath()` to find
  the zip and unzip it to the databases dir (still raw `SQLiteDatabase`, no Room).
  The helper is parameterised by language so more languages = more DB files in
  one pack, no new helper class or module.
- **User-facing install entry — `TopicalDownloadActivity`** (mirrors
  `ReferencesDownloadActivity`): a download screen with progress / cancel /
  "already installed" states. Reached from the main menu via a permanently
  visible **"Download Topical Links"** item (mirrors `R.id.action_download_references`).
  When installed, the bookmark editor's Topical-Links button lights up as before;
  when not, it stays hidden and the user can install from the menu.
- **Build-side check — `checkTopicalAssets`** (warn, not fail): looks for both
  per-language zips in `topical_pack/src/main/assets/` *and*
  `app/src/debug/assets/topical/` and prints a clear instruction
  (`python3 topical/build_topical_links.py greek`) if any are missing. Wired to
  `preBuild`.
- **No Room involvement at all.** Because the data is in standalone DBs opened
  outside Room, there is no `@Database` change, no entity, and no version bump —
  the strongest form of the `CLAUDE.md` backwards-compatibility guarantee.

### No changes to the main database

`perseus_texts.db` is **not modified in any way** by this feature: no table is
added to it, no schema change, no version bump. All topical data lives in the
separate `topical_*.db` files. The main DB is only ever **read**:
- the cross-DB filter does read-only `SELECT`s on `text_lines` to test position
  existence and fetch the original snippet;
- result rows read `authors` / `works` / `books` for the English reference;
- result rows read the **existing translation alignment system**
  (`translation_segments` / `translation_lookup`, via `getTranslationSegments`)
  for the aligned English snippet — **read-only; the translation alignment system
  is not modified** (no re-alignment, no schema change, no new tables);
- sync is release-based, so there is no `build_time`/staleness read.

(User bookmarks remain in `UserDatabase` as today; that is also unchanged.)

### Wiring

- `BookmarkEditorActivity`: add the button. On entry, determine the bookmark's
  language, check the pack is available and contains that language's DB, resolve
  the bookmark's
  `(book_id, line_number, sequence_number)` to a `passage_id`, fetch candidate
  related passages, filter them against the loaded `perseus_texts.db`, and only
  then show the button (with the surviving results passed/recomputed for the
  list screen).
- New, **self-contained** `TopicalLinksActivity` — its own code, **not** a
  subclass of or dependent on `LemmaOccurrencesActivity`. It gets candidate
  targets from `TopicalDbHelper`, then filters + hydrates each against the loaded
  main DB into the three-part row — English reference (`authors`/`works`/`books`),
  limited original snippet (`text_lines`), and the target's aligned translation
  snippet (read-only via `getTranslationSegments`). Navigate on tap.
- Use a dedicated `RelatedPassageAdapter` + `item_topical.xml`. **Do not reuse
  `OccurrenceAdapter`.** It's a few extra files, but it keeps topical links
  insulated from changes to the occurrences screen (and vice-versa).
- **iOS** mirrors the access pattern: a raw-SQLite helper over the same
  `topical_*.db.zip`. ⚠️ Delivery differs from `rhetoric.db.zip`: rhetoric is
  tiny and can sit in `Resources/`, but the topical DBs are large, so bundling
  them in `Resources/` would bloat the app and likely requires On-Demand
  Resources (which this project has had trouble with). Treat iOS delivery sizing
  as an open item. (Per project rules I will not build iOS — Swift changes are
  handed off.)

### Failure handling — the UI must never crash

Topical links are a **non-essential enhancement**: anything that goes wrong must
degrade to "no button / no results", never a crash, and must never affect the
rest of the bookmark editor or the app. This mirrors the existing defensive
posture (e.g. `RhetoricDbHelper` and the tree-view cycle guards already swallow
bad data rather than crash).

Every failure mode degrades gracefully:

| Situation | Behavior |
|-----------|----------|
| Topical pack not installed / not yet downloaded (on-demand) | Hide the button. No error shown. |
| Pack zip missing, corrupt, or fails to unzip | Catch, log, hide the button. The editor opens normally. |
| Topical DB fails to open / unexpected schema / SQLite error | Catch, log, treat language as unsupported → hide the button. |
| No `bookmark_positions` row for the bookmark's key | Hide the button (nothing to link from). |
| Query throws mid-lookup | Catch, return empty → hide the button. |
| All candidates filtered out (none in loaded main DB) | Hide the button (or show an empty-state message), no crash. |
| A target row can't be opened on tap (e.g. since-removed) | No-op / brief toast; stay on the list. |
| Target has no aligned translation (`getTranslationSegments` empty) | Render the row without the translation line; never crash. |
| English title/label lookup misses for a target | Fall back to the stored/id label; the row still renders. |
| Pack accidentally out of step with the main DB | Release discipline prevents this; if a stale key still misses on the filter, it is simply dropped — no crash, at worst a missing/odd row. |

Implementation notes:
- Do all topical work (extraction, open, queries, filtering) **off the main
  thread**; failures resolve to an empty result the UI treats as "hide".
- Wrap helper open/query in try/catch; **never** let a `topical_*` failure
  propagate into `BookmarkEditorActivity`'s normal save/cancel/edit flow.
- Treat "feature unavailable" and "no results" identically from the user's
  point of view: the button simply isn't there.

---

## Bookmark CSV export — human-readable English columns

Separate from topical links, but sharing the same English-description lookup:
make the exported bookmark CSV human-readable by adding the **English
author / work / book descriptions**.

- **Where:** `BookmarksActivity.exportBookmarksToCSV()`
  (`app/src/main/java/com/classicsviewer/app/ui/BookmarksActivity.kt`), which
  today writes stored `BookmarkEntity` fields directly with header:
  `work_id, book_id, line_number, sequence_number, author_name, work_title,
  book_label, line_text, note, created_at, last_accessed`.
- **Add** human-readable English columns by looking them up **read-only** from
  the loaded `perseus_texts.db` by `work_id` / `book_id` at export time:
  add `work_title_english` (`works.title_english`); `author_name` is already
  Latinized English and `book_label` is already present, so the real gap is the
  English work title (the stored `work_title` may be in the original script).
- **Do NOT change `BookmarkEntity` / `UserDatabase`** — no new stored column, no
  Room version bump. English values are fetched at export time, not stored.
- **Fallback:** if a bookmark's `work_id` isn't in the loaded DB (e.g. a tier
  switch), fall back to the stored snapshot fields so export never fails.
- **Data caveat:** `works.title_english` is 100% populated, but a minority of
  works fall back to a non-readable id (e.g. `tlg001`) — a pre-existing
  data-quality issue, out of scope here. Prefer `title_english`, optionally
  falling back to `title` when `title_english` looks like a bare id.

This is the **same** English author/work/book lookup the topical results row
uses, so both should share one helper.

---

## Extensibility: adding a language

A single registry is the source of truth; nothing else hardcodes the language
set. Each entry maps a language to:

| Field          | Example (Greek)                                                            |
|----------------|----------------------------------------------------------------------------|
| `language`     | `greek` (matches `authors.language`)                                       |
| `db_file`      | `topical_greek.db` (rides in the one `topical_pack`)                       |
| `translator`   | `Interlinear (Beta, generated from app dictionary and treebank)`           |
| `parser`       | `greek` (selects the parser that understands that interlinear's format)    |

Two copies of this registry stay in sync: a build-side one (Python in
`build_topical_links.py`) and a small client-side one (Kotlin in
`TopicalRegistry`).

**To add a language (e.g. Sanskrit):**

1. Confirm the language has interlinear coverage in
   `translation_segments` under some translator string.
2. If its pipe format differs from Greek and Latin, add a parser function
   (`parse_interlinear_<lang>`) that extracts `(lemma, content?)` per token, and
   register it in the build script's `PARSERS` map.
3. Add a registry entry — `language`, `db_file`, `translator`, `parser`.
4. Run `build_topical_links.py <lang>` against the extended DB. The pack already
   ships all language DBs; the new file rides along with it (no new gradle
   module).

**What does NOT change:** the table schema, the build script structure, the
`TopicalDbHelper` class, the asset-pack module, the list screen, and the
cross-DB filtering rule are all language-agnostic. A language with no DB in the
pack simply never shows the button.

---

## Configuration

- **Build parameters:** `N=10` (passage window), `K=50` (stored links per
  source), `min_bag=8` (passages with fewer content lemmata are excluded from
  both source and target), `--exclude-scope work` (same-work neighbours never
  link), no cosine floor.
- **Display cap:** the UI shows up to 25 results per source after the cross-DB
  filter.
- **Cross-language links:** out of scope. Greek↔Greek and Latin↔Latin only.

---

## Risks / notes

- **Pack size:** `topical_pack` bundles all languages, total **~410 MB
  compressed** (Greek 355 MB + Latin 55 MB). Greek dominates. The pack ships
  on-demand via Play Asset Delivery, so it does not bloat the base APK/IPA.
- **Sparse results on the sample DB:** filtering extended-built links against a
  small loaded DB can thin the list out. K=50 mitigates it, but some bookmarks
  legitimately show few or zero related passages on the sample tier — hence the
  "hide button if empty" rule.
- **Interlinear coverage:** the build depends on per-language interlinear
  segments in `translation_segments`. Hard-fails if a language has no parsable
  interlinear (no silent skip).
- **Window boundaries:** fixed N-position windows can split a coherent passage
  across two windows; N=10 keeps this minor and is the price of uniform passage
  sizes. Native section units (Bekker / Stephanus / chapter) are a possible
  future refinement.
- **No word-specific or one-off fixes:** relatedness is fully script-driven on
  the original-language text, consistent with the project's "most general
  solution" rule.
