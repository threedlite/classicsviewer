# Topical Linking — current architecture

Single source of truth for the topical-links feature as it currently ships.
This document supersedes the earlier `TOPICAL_LINKING_PROPOSAL.md`,
`TOPICAL_REDESIGN.md`, `TOPICAL_FRAGILITY_ANALYSIS.md`, and the part-by-part
combined `TOPICAL.md` that preceded this one.

Two evaluation artifacts remain as separate files because they are data, not
spec:

- `SPOTCHECK_11.md` — qualitative spot-check of LDA neighbours at the
  opening passage of ~15 representative Greek works (Homer, Hesiod, Plato,
  Aristotle, Thucydides, Herodotus, the tragedians, Plutarch, NT, …).
- `TOPICAL_EVAL_SAMPLE.md` — quantitative same-author-bias evaluation across
  ~45 stratified Greek sources. Cited where it informs decisions below.

A third local-only artifact `SPOTCHECK_LATIN.md` (untracked) recorded the
entity-kind post-ship spot-check on 4 Greek + 4 Latin opening passages;
the relevant findings are inlined in §10.3.

## 0. What ships today

The Topical Links feature gives a reader, from any passage in the loaded
Perseus DB, a list of cross-author thematic and lexical neighbours. It runs
entirely on-device, against a binary pack distributed via Play Asset
Delivery (Android) and bundled resources (iOS). One pack per language
(`greek`, `latin`).

| Aspect | Current state |
|---|---|
| Pack format | **No SQLite.** Raw mmap'd binary files + a small `manifest.json` |
| Files in pack | `positions.bin`, `rowmeta.bin`, `T.f16`, `ivf.centroids`, `ivf.lists`, `bags.bin`, `invidx.bin`, `vocab.bin`, `entity_bags.bin`, `entity_invidx.bin`, `entity_vocab.bin`, `manifest.json` |
| Signal kinds available | `lda` (Topical) — default; `tfidf` (Lexical); `entity` (Names) |
| K_topics | **1000** (single seed, pinned) |
| IVF | `nlist = round(sqrt(P))`, `nprobe = 24` at runtime |
| LDA library | **tomotopy** (C++ Gibbs LDA, ~10 min for 200 iter on Greek) |
| K-means for IVF | sklearn `MiniBatchKMeans`, `random_state` pinned |
| UI affordance | **Top-bar action item** on the bookmark editor (two-overlapping-circles icon) |
| Kind selection | **Dropdown** in the topical-links screen header; per-language sticky |
| Empty result | Screen shows "No entries found"; dropdown stays interactive |
| Cross-tier filter | App reads only `text_lines` + `authors`/`works`/`books` + `translation_segments` from whichever main DB tier is loaded; passes that are not in the loaded tier are silently filtered out at hydrate time |

Greek pack: ~452 MB compressed. Latin pack: ~71 MB.

## 1. Design principles

These are load-bearing. The rest of the doc follows from them.

### P1. Ship the input, not the cache

What carries the signal is the **lemma vocabulary, the IDF weights, the LDA
topic vectors, the per-source bag, and the position index**. These compress
to ~430 MB for Greek. The earlier architecture materialised every passage's
top-K neighbours into a relational table, which blew that up by ~3× and
landed us in the Samsung-wipe regime (see §11 history). We refuse to ship
the cache.

### P2. Inputs are read-only, immutable, content-addressed

Every shipped file has a `sha256` recorded in `manifest.json`. The runtime
helper never trusts a file on disk without verifying its sha against the
manifest. On any mismatch the helper wipes and re-extracts. Files are never
mutated at runtime; the only writes are the one-time extract.

### P3. No SQLite for the bulk data

SQLite is a great query engine and a terrible binary container for read-only
data shipped across the Android version boundary. Its default error handler
deletes files on transient errors; vendor forks (Samsung's) add aggressive
heuristics on top; and sqlite-version disagreement at the file format level
caused real corruption on real devices in our own deploys. The pack uses
**no SQLite for any of its data**. All lookups are over mmap'd binary files
or a tiny inverted index — formats whose failure modes are "EOF" or
"checksum mismatch", not "platform decided to wipe your data".

The runtime still uses the loaded main DB (`perseus_texts.db`) for the
cross-tier filter and English hydrate; that DB is a Room/SQLite DB managed
by the rest of the app. The pack itself has no SQLite.

### P4. Fail closed, never destructively

Every layer has one of two outcomes: it succeeds, or the feature is hidden.
There is no path that does damage:

- The helper never deletes data it didn't write itself.
- The build never overwrites old outputs until new outputs are fully
  verified (`dist/<lang>.tmp/` staging, atomic rename).
- A bad release can be rolled back by reverting one zip file.
- LDA without IVF is **not** a brute-force fallback — if `ivf.centroids` or
  `ivf.lists` go missing, `ldaKnn` returns empty. A future build error
  surfaces as "No entries found", not as a silent 3-second-per-click
  regression.

### P5. Runtime tunability over rebuild discipline

Anything we'd plausibly want to change without a code or text-pipeline
change is a runtime parameter: `min_sim` per kind, `K` per kind, `nprobe`,
the merge rule, whether to disable one kind entirely. The artifact ships the
*raw signal*; the cutoffs are policy applied on top. The current Android
runtime overrides the manifest's cutoffs because the manifest defaults
(0.50 LDA, 0.15 TF-IDF) were calibrated for K=200 and at K=1000 cosines
spread lower.

### P6. Deterministic builds via pinned seeds + pinned libraries

The build is byte-deterministic for fixed inputs:

- `lda_seed` is pinned in the manifest (default `0`).
- `kmeans_seed` is pinned (default `0`).
- `sklearn_version` and `tomotopy_version` are recorded in the manifest;
  changing either intentionally rotates `build_id` and forces on-device
  re-extract.
- The position table is sort-stable; the inverted index is sort-stable.

Two consecutive builds on the same machine with the same source DB produce
sha-identical files across the whole pack.

## 2. Artifact layout (byte-level)

Per language, the pack ships as a single zip `topical_<lang>.db.zip` (the
historical `.db.zip` suffix is preserved so existing
`TopicalPackManager` / debug-assets paths don't change). All multi-byte
integers are little-endian; floats are IEEE 754 (f16 = binary16, f32 =
binary32).

### 2.1 `manifest.json`

Small JSON file written last by the build. Its existence + valid sha
signals "complete". Schema (current values shown):

```json
{
  "schema_version": 1,
  "language": "greek",
  "build_id": "<hex sha256 of canonical-form inputs>",
  "text_build_time": "<from extended DB meta>",
  "topical_build_time": "<ISO8601 UTC>",
  "sklearn_version": "1.5.x",
  "tomotopy_version": "0.14.0",
  "vocab_size": 58426,
  "passage_count": 331767,
  "lda_topics": 1000,
  "lda_seeds": [0],
  "lda_iter": 200,
  "kmeans_seed": 0,
  "ivf_nlist": 576,
  "ivf_nprobe": 10,
  "min_bag": 8,
  "n": 10,
  "kinds_available": ["lda", "tfidf", "entity"],
  "kind_labels": {
    "lda":    {"ui": "Topical", "hint": "Shared latent topics — cross-author thematic neighbours"},
    "tfidf":  {"ui": "Lexical", "hint": "Shared content vocabulary — same case / treatise / lexicon references"},
    "entity": {"ui": "Names",   "hint": "Shared named entities — passages mentioning the same people or places"}
  },
  "default_kind": "lda",
  "lda_min_sim": 0.5,
  "tfidf_min_sim": 0.15,
  "entity_min_sim": 0.20,
  "entity_min_bag": 2,
  "entity_vocab_size": 7527,
  "exclude_scope": "work",
  "files": {
    "positions.bin":     {"bytes": …, "sha256": "…"},
    "rowmeta.bin":       {"bytes": …, "sha256": "…"},
    "T.f16":             {"bytes": …, "sha256": "…"},
    "ivf.centroids":     {"bytes": …, "sha256": "…"},
    "ivf.lists":         {"bytes": …, "sha256": "…"},
    "bags.bin":          {"bytes": …, "sha256": "…"},
    "invidx.bin":        {"bytes": …, "sha256": "…"},
    "vocab.bin":         {"bytes": …, "sha256": "…"},
    "entity_bags.bin":   {"bytes": …, "sha256": "…"},
    "entity_invidx.bin": {"bytes": …, "sha256": "…"},
    "entity_vocab.bin":  {"bytes": …, "sha256": "…"}
  }
}
```

`build_id` = sha256 of the canonicalised tuple
`(schema_version, language, lda_seeds, lda_topics, kmeans_seed, vocab_size,
min_bag, sklearn_version, tomotopy_version, text_build_time, source_code_sha)`.
The runtime compares this against its stored prefs key to decide
"is the on-device artifact this release's artifact".

`kinds_available` is the **public contract for the UI dropdown** (§6). The
runtime iterates this array to build the kind-selector. Adding a future
kind (`entity`, §12) is a build-side change only; no client code edit
required.

### 2.2 `positions.bin` — reverse position lookup

Sorted-array binary file enabling one O(log N) lookup per query:
`(book_id, line_number, sequence_number) → row_idx`. With a fallback that
matches `(book_id, line_number)` if the exact triple misses — different
sequence numbers within the same line belong to the same passage anyway,
so the fallback resolves callers whose seq-numbering disagrees with
`text_lines`. Required because the bookmark editor's seq value sometimes
disagrees with the build's view of `text_lines.sequence_number`.

Header (32 bytes), then 16-byte records sorted by
`(book_id_idx asc, line asc, seq asc)`, then a deduped book-id string pool.

### 2.3 `rowmeta.bin` — per-passage scalar metadata

One fixed-stride 20-byte record per passage, indexed by `row_idx`:
`(author_idx, work_idx, anchor_book_id_idx, anchor_line, anchor_seq)`.
Used for same-work exclusion in the hot KNN loop (one int compare per row,
no allocation) and for hydrating result rows without hitting SQLite.

A tail block carries the `author_id` and `work_id` string pools — runtime
uses those to look up English names in the loaded main DB.

### 2.4 `T.f16` — LDA topic vector matrix

The load-bearing semantic artifact. Single contiguous float16 matrix,
row-major, P × K_topics. No header (dimensions live in the manifest); a
plain `mmap` returns the matrix.

Greek: 331,767 × 1000 × 2 ≈ **663 MB**. Latin: 36,639 × 1000 × 2 ≈ **73 MB**.

Rows for tiny-bag passages (length below `min_bag`) are zeroed by the build
so they are inert at query time.

### 2.5 `ivf.centroids` — IVF-flat centroids

`nlist` centroids of dimension K_topics, float16, row-major, no header.
Greek: 576 × 1000 × 2 ≈ **1.1 MB**. Latin: 191 × 1000 × 2 ≈ **0.4 MB**.

Trained with `MiniBatchKMeans` on T, `random_state` pinned.

### 2.6 `ivf.lists` — IVF inverted lists

For each centroid, the (sorted ascending) list of `row_idx` assigned to it.
Header (16 bytes) + `nlist+1` u32 offsets (into the row-index array, not
bytes) + flat u32 row indices. ~1 MB Greek.

### 2.7 `bags.bin` — per-source query bag

Per-row sparse `(term_idx, tf)` lists, exactly the source row's nonzero
columns of the build's CountVectorizer output. Lets the runtime build a
TF-IDF query for the source passage **without re-parsing the loaded main
DB's interlinear**. The dependency on the loaded DB's interlinear coverage
was the bug that made Lexical return zero results on sample-tier installs
(sample DB has no interlinear translator at all).

Format: 16-byte header + `(P+1) × u32` row offsets (entry indices, not
bytes) + flat array of `(u32 term_idx, u16 tf)` 6-byte entries.

Greek: ~50 MB. Latin: ~5 MB.

### 2.8 `invidx.bin` — TF-IDF sparse inverted index

One postings list per vocabulary term. Each posting is `(u32 row_idx, f16
tfidf)`. Lists sorted by `row_idx` ascending for gallop-merge across terms
at query time.

Greek: ~44 MB. Latin: ~8 MB.

### 2.9 `vocab.bin` — term strings + IDF

Per term: byte-length, UTF-8 string, f16 IDF. Random access via a tail
offsets array. Used at query time to map source `term_idx` → IDF and back
where needed. ~5 MB Greek.

### 2.10 `entity_bags.bin` — per-source named-entity query bag

Same layout as `bags.bin` (§2.7) but vectorised over the entity vocabulary
instead of the content-lemma vocabulary. Per-row sparse `(term_idx, tf)`
list where `term_idx` indexes `entity_vocab.bin` and `tf` is the count of
that proper-noun lemma in the source row.

The entity vocabulary is built by a **separate parser** keyed on POS:
- Greek (`parse_entities_greek`): NOUN-tagged lemma whose surface form
  begins with an uppercase Greek letter. The Greek treebank (OGA/GLAUx)
  does not tag PROPN reliably, so we approximate with NOUN + uppercase.
- Latin (`parse_entities_latin`): strict `POS == "PROPN"` from Stanza,
  with a stoplist filter that drops case-marker abbreviations
  (`gen` / `nom` / `acc` / `dat` / `abl` / `voc` / `loc` and other
  morphology abbreviations) Stanza occasionally mis-tags as proper nouns.

Tiny-bag rows (`< entity_min_bag = 2`) are kept but produce empty entity
KNN — there is no point matching a single name. Vocabulary low-frequency
floor is `entity_min_df = 2`.

Greek: ~3.8 MB (~26k entity-bearing rows of 332k). Latin: ~0.7 MB (~26k
of 37k).

### 2.11 `entity_invidx.bin` — entity sparse inverted index

Same layout as `invidx.bin` (§2.8). One postings list per entity-vocab
term. Each posting is `(u32 row_idx, f16 tfidf)` where `tfidf` is
sublinear-tf scaled by the entity-vocab IDF.

Greek: ~2.6 MB. Latin: ~0.6 MB.

### 2.12 `entity_vocab.bin` — entity term strings + IDF

Same layout as `vocab.bin` (§2.9). Per term: byte-length, UTF-8 lemma
string, f16 IDF. The strings here are *lemmas* (e.g. `Ζεύς`, `pompeius`),
not surface tokens.

Greek: ~0.3 MB (~30k entity lemmas). Latin: ~0.1 MB (~7.5k entity lemmas).

### 2.13 What we do not ship

- ❌ Any precomputed `topical_links` neighbour table.
- ❌ Any SQLite file inside the pack.
- ❌ Any English / translation data (comes from the loaded main DB).
- ❌ A dense X_tfidf matrix (replaced by the inverted index + bags).

## 3. Build pipeline

The build is one script: `topical/build_topical_pack.py <language>`. It
writes to `topical/dist/<lang>/`, then atomically promotes and zips.

Stages:

1. **Enumerate positions** per book from the extended DB (per
   `CLAUDE.md`'s rule, **only the extended DB** is ever read for topical
   build). Form passages as fixed N=10-position windows. Carry along
   `(book_id, line, seq, author_id, work_id)` per position.
2. **Parse interlinear** per language's parser. Both languages now use
   POS-gated parsing: `parse_interlinear_greek` reads the OGA/GLAUx
   POS field; `parse_interlinear_latin` reads Stanza POS (from the
   Latin POS rebuild — see `latin/LATIN_POS_PLAN.md`). For each row,
   parallel entity parsers (`parse_entities_greek`,
   `parse_entities_latin`) produce a second per-row bag from PROPN
   lemmas (Latin) or NOUN-uppercase-Greek lemmas (Greek). See §2.10
   for entity-parser details.
3. **Vectorize** with `CountVectorizer(max_df=0.30, min_df=3)` →
   `X_counts`. `TfidfTransformer(sublinear_tf=True)` → L2-normalised
   `X_tfidf`. Drop tiny-bag rows (`min_bag=8`) by zeroing them so they
   are inert in both KNNs. In parallel, vectorize entity bags with
   `CountVectorizer(min_df=entity_min_df=2, max_df=1.0)` →
   `X_ent_counts`; transform → `X_ent_tfidf` (entity TF-IDF). Rows with
   fewer than `entity_min_bag=2` entity terms produce empty entity KNN
   at query time.
4. **Train LDA** with tomotopy: `LDAModel(k=K_topics, alpha=50/K, eta=0.01,
   seed=lda_seed)`, `train(iter=200, workers=0)`. Output: P × K float32
   topic matrix. Zero tiny-bag rows. L2-normalise rows.
5. **Train IVF**: `MiniBatchKMeans(n_clusters=round(sqrt(P)), random_state=
   kmeans_seed)` on the valid (non-zero) T rows. Build inverted lists.
6. **Write binary files**: `positions.bin`, `rowmeta.bin`, `T.f16`,
   `ivf.centroids`, `ivf.lists`, `bags.bin`, `invidx.bin`, `vocab.bin`,
   `entity_bags.bin`, `entity_invidx.bin`, `entity_vocab.bin`. Compute
   sha256 of each as written.
7. **Write `manifest.json`** with all shas and parameters.
8. **Atomic promote**: rename `dist/<lang>.tmp/` → `dist/<lang>/`. Zip to
   `dist/topical_<lang>.db.zip`. Verify zip integrity (`unzip -t`).
9. **Place** the zip in three asset locations:
   `topical_pack/src/main/assets/` (release AAB),
   `app/src/debug/assets/topical/` (debug APK fallback),
   `ios/ClassicsViewer/Resources/` (iOS bundle).

### 3.1 Build time

| Stage | Greek (K=1000) | Latin (K=1000) |
|---|---|---|
| Enumerate + parse | ~30 s | ~3 s |
| Vectorize | ~30 s | ~3 s |
| LDA train (tomotopy, 200 iter) | ~10 min | ~2 min |
| IVF k-means | ~15 s | ~5 s |
| Write binary files | ~30 s | ~10 s |
| Zip + place | ~3 min | ~10 s |
| **total** | **~14 min** | **~3 min** |

## 4. Runtime query path

The query path **branches on the user's selected kind** (§6). Only the
selected kind's KNN runs.

1. **Position lookup** in `positions.bin`: binary search by
   `(book_id, line, seq)`, then by `(book_id, line)` fallback. ~1 ms.
   Miss → empty.
2. **Row meta**: inline `work_idx` read from `rowmeta.bin[row_idx]` for
   same-work exclusion. ~0.1 ms.
3. **Read selected kind** from persisted preference (per-language sticky).
   Default `lda`.
4. **Run that kind's branch**:

   **4a. `lda` branch:**
   - Read q = `T.f16[row_idx]`. ~0.1 ms warm.
   - Score q against all `nlist` centroids. ~5 ms.
   - Pick top `nprobe = 24` centroids.
   - For each, walk its inverted list; for each row_idx, mask same-work,
     compute `sim = T[i] · q`, push to top-K heap above `min_sim`.
   - ~50 ms warm, ~200 ms cold (first-time page faults).
   - **No brute-force fallback.** Missing IVF → empty list.

   **4b. `tfidf` branch:**
   - Read pre-built source bag from `bags.bin[row_idx]`: a
     `(term_idx, tf)` map.
   - Apply `sublinear_tf` + IDF, L2-normalise the query vector.
   - For each query term, walk its `invidx.bin` postings; accumulate
     sims; filter by `min_sim` + same-work exclusion; top-K.
   - ~10 ms warm.

   **4c. `entity` branch:**
   - Read pre-built source entity bag from `entity_bags.bin[row_idx]`:
     a `(term_idx, tf)` map keyed on the entity vocabulary.
   - Empty bag → empty result (passage names no entities).
   - Apply `sublinear_tf` + entity-IDF, L2-normalise the query vector.
   - For each query term, walk its `entity_invidx.bin` postings;
     accumulate sims; filter by `entity_min_sim` (0.20) + same-work
     exclusion; top-K.
   - ~5 ms warm. Faster than tfidf because entity bags are smaller.

5. **Hydrate** the surviving candidates via the loaded main DB:
   `text_lines` lookup (existence + Greek/Latin snippet), `books` /
   `works` / `authors` for English reference, `translation_segments`
   filtered to drop the interlinear translator's rows (so the English
   slot never shows lemma+POS text). ~80–150 ms depending on tier.
6. **Render** the result list, capped at `DISPLAY_LIMIT = 50`.

### 4.1 Runtime parameter overrides

The Android client overrides three manifest defaults:

| Parameter | Manifest default | Runtime override | Why |
|---|---|---|---|
| `lda_min_sim` | 0.50 | **0.30** | K=1000 spreads cosines lower than K=200 the defaults were calibrated for |
| `tfidf_min_sim` | 0.15 | **0.12** | Same reasoning, smaller adjustment |
| `entity_min_sim` | 0.20 | **0.20** | No override — manifest default is the runtime value |
| `ivf_nprobe` | 10 | **24** | Better recall, ~2.4× cost on a fast loop |

These are per-app, not per-pack. The manifest values stay authoritative; the
client just chose to be more permissive than the build's conservative
default. Per P5 this is a runtime decision.

### 4.2 Display caps

| Cap | Value |
|---|---|
| `DISPLAY_LIMIT` (rows shown) | 50 |
| `CANDIDATE_LIMIT` (post-KNN, pre-hydrate) | 200 |
| Snippet length (original) | 160 chars |
| Snippet length (translation) | 220 chars |

## 5. Failure modes and recovery

There is **one runtime contract**: every reader method returns either valid
data or a defined "unavailable" sentinel. No exceptions cross the helper
boundary. The UI treats "unavailable" identically to "feature not installed"
— the icon is hidden, the menu still offers to install the pack.

There is **one build contract**: either the build promotes a verified new
`dist/<lang>/` and zip, or the old one is untouched. No half-built state
ships.

### 5.1 Failure matrix

| Failure | Where caught | Action | User-visible |
|---|---|---|---|
| Pack zip not in APK assets / not yet on-demand-downloaded | helper init | unavailable | Icon hidden; menu offers "Download Topical Links" |
| Pack zip present but extraction throws partway | extract step | wipe partial output dir, unavailable | Icon hidden; next launch retries |
| Extracted directory missing `manifest.json` | helper init | wipe, re-extract; still missing → unavailable | One-time delay on first detection |
| `manifest.json` malformed | helper init | wipe, re-extract; still bad → unavailable | One-time delay |
| sha256 mismatch on any file | helper init (sha verify post-extract) | wipe, re-extract once; still bad → unavailable | One-time delay |
| `manifest.build_id` ≠ prefs.build_id (release upgrade) | helper init | wipe old, extract new | One-time delay on release |
| mmap of `T.f16` throws (OOM, ENOENT) | T.f16 open | unavailable | Icon hidden |
| mmap of any other pack file throws | each open | unavailable | Icon hidden |
| Position lookup miss after fallback | step 1 | empty list | "No entries found"; dropdown stays interactive |
| Selected kind's KNN returns empty (cutoff + filter) | steps 4a/4b | empty list | "No entries found"; dropdown stays interactive |
| IVF files missing (theoretically, build bug) | step 4a | empty list (no brute-force) | "No entries found" |
| `bags.bin` row empty (tiny-bag passage at build time) | step 4b | empty list | "No entries found" for Lexical only |
| Translation snippet missing | step 5 | row rendered without translation | Row still shown |
| Selected kind no longer in `kinds_available` (release removed a kind) | helper init | silently fall back to `default_kind`, rewrite prefs | Transparent |
| Vendor wipe of any mmap file | next helper init | sha check fails → re-extract | One-time delay |
| Build script crashes mid-write | build promote step | tmp dir never promoted | No bad release; dev fixes & reruns |
| Build sha mismatch in CI determinism check | CI | red | Bad build never reaches user |

### 5.2 "Wipe and re-extract" protocol

Helper holds `cacheDir/topical_unpacked_topical_<lang>/`. On any mismatch:

1. Rename `<lang>/` → `<lang>.dead.<timestamp>/` (atomic on POSIX).
2. Extract into fresh `<lang>.tmp/`.
3. After extract + sha verify, atomic rename `<lang>.tmp/` → `<lang>/`.
4. Best-effort delete `<lang>.dead.*/`.

Two-phase rename means we never have a window where `<lang>/` is
half-written.

### 5.3 The Samsung `DefaultDatabaseErrorHandler` problem

We hit this in the SQLite-pack era. Samsung's fork of
`DefaultDatabaseErrorHandler.onCorruption` aggressively wipes files on any
`SQLITE_CORRUPT` signal. A 1.87 GB SQLite pack built on macOS sqlite 3.51
was reported corrupt at page 275666 by Android's bundled sqlite (the same
bytes, different verdict), and got wiped before our try/catch ran. The
redesign eliminated this class of failure structurally: with no SQLite in
the pack, the `DefaultDatabaseErrorHandler` code path is never on the
stack for our data.

We still added a no-op `DatabaseErrorHandler` to the now-removed
`TopicalDbHelper` during the transition. The lesson stands as a
project-wide rule: any read-only bundled SQLite DB elsewhere in this app
should be opened with a no-op error handler too.

## 6. Per-kind selection UI

### 6.1 Where the action lives

Bookmark editor → **action-bar icon at the top right** (two overlapping
circles drawable `ic_topical_links`). The icon is hidden until the
asynchronous gate confirms (a) the bookmark's language is in
`TopicalReader.isSupported`, (b) the pack zip exists in
`TopicalPackManager.getAssetsPath()`. Once both are true,
`invalidateOptionsMenu()` makes the icon visible. The actual position
lookup and KNN run on tap, not at gating time — that decoupling stops
slow first-launch extractions from blocking icon visibility.

### 6.2 The dropdown

The Topical Links screen has a sticky header with a `Spinner` (Android) /
SwiftUI `Picker` (iOS) populated from `manifest.kinds_available`. Selecting
an option re-runs the query path for that kind. Options are user-facing
labels from `manifest.kind_labels`; on-disk values (`"lda"`, `"tfidf"`)
are never shown.

| Kind id | UI label | What it actually is | When it shines |
|---|---|---|---|
| `lda` | **Topical** | Shared latent topics | Cross-author thematic neighbours (Phaedo → Plutarch's *Consolatio*; Iliad 1.1 → Iliadic scholia + Porphyrius; Hesiod *Works & Days* → Homeric Hymns cluster) |
| `tfidf` | **Lexical** | Shared content vocabulary | Within-author topical clusters and lexicon cross-refs (Demosthenes' *Onetor I* → *Onetor II* + Aphobus suits; Hippocrates *On Fractures* → other anatomical treatises) |
| `entity` | **Names** | Shared named entities (PROPN lemmas) | Genealogies, narrative histories, biographies, patristic genres: Herodotus 1.1 → Plutarch's *Of Herodotus's Malice*; Matthew 1.1 → other biblical genealogies; Caesar BG 1.1 → Livy + Cicero letters on Hispania |

### 6.3 Default and persistence

Default is `lda` (Topical) from `manifest.default_kind`. The user's
selection is sticky **per language**, persisted in
`SharedPreferences` / `UserDefaults` under key
`topical_selected_kind_<language>`. On launch, the helper validates the
persisted kind against `kinds_available`; missing → silently fall back to
default, rewrite prefs.

### 6.4 Empty result

If the selected kind produces zero survivors above its cutoff (or zero
after the cross-tier filter), the screen renders the dropdown, the
selected option, and an empty list area with **"No entries found."** The
user can switch kind from this state — the icon does not disappear once
the screen is open.

This deliberately departs from the icon-visibility rule (§6.1): once the
user has reached the screen, the affordance to switch kind must remain
accessible regardless of the current list's emptiness.

### 6.5 Extensibility contract

The entity kind (now shipping; see §12.1) is the worked example. Adding a
further kind follows the same pattern — a **build-side-only change**:

1. Build emits the kind's files (e.g. `<kind>_bags.bin`,
   `<kind>_invidx.bin`, `<kind>_vocab.bin`) and adds them to
   `manifest.files`.
2. Build appends the new id to `manifest.kinds_available` and adds a
   `kind_labels.<kind> = {ui: "…", hint: "…"}` entry.
3. Runtime gains a new `else if (kind == "<kind>")` branch in §4
   (and a parallel reader API on `TopicalReader` / `TopicalDatabase`).
4. **No UI code change.** The dropdown reads its options from the
   manifest; selector, persistence, and empty handling all work for the
   new kind automatically.

The entity rollout proved this pattern: the only Android/iOS UI delta
was the `case "entity":` branch in `TopicalLinksActivity.kt` /
`TopicalLinksView.swift`. The dropdown, persistence, and "No entries
found" rendering needed zero changes.

## 7. Storage and timing budgets

### 7.1 On-disk sizes (Greek / Latin)

| File | Greek MB | Latin MB |
|---|---|---|
| `manifest.json` | 0.003 | 0.003 |
| `positions.bin` | 42 | 7 |
| `rowmeta.bin` | 7 | 1 |
| `T.f16` (P × 1000 × 2) | 663 | 73 |
| `ivf.centroids` | 1.1 | 0.4 |
| `ivf.lists` | 1 | 0.2 |
| `bags.bin` | ~50 | ~5 |
| `invidx.bin` | 44 | 8 |
| `vocab.bin` | 5 | 2 |
| `entity_bags.bin` | 3.8 | 0.7 |
| `entity_invidx.bin` | 2.6 | 0.6 |
| `entity_vocab.bin` | 0.3 | 0.1 |
| **uncompressed** | **~820** | **~98** |
| **zip (DEFLATED-9)** | **~452** | **~71** |

### 7.2 Largest single file

Greek `T.f16` at 663 MB. Below the regime (~1 GB+) where OEM corruption
heuristics start tripping in our experience. The original failure was a
1.87 GB SQLite DB; this is a raw binary, structurally not subject to the
SQLite-specific wipe code path.

### 7.3 Cold-start cost

First time the user taps Topical Links after app launch:
- mmap is page-faulted on demand.
- One IVF query reads `nprobe × (P/nlist)` rows of T at ~1200 bytes each
  ≈ ~7 MB of T pages, plus the centroids file (~1 MB) and a portion of
  invidx (for TF-IDF queries).
- Cold I/O budget: ~100–300 ms.

Subsequent queries reuse cached pages and run in tens of ms.

### 7.4 RAM footprint at query time

- mmap'd files: paged on demand by the kernel; we never load whole files
  into the JVM heap.
- Allocated objects per query: scratch `FloatArray(K_topics)` for q
  (reused), small heap for top-K, a `HashMap<Int,Float>` for TF-IDF
  accumulation. Tens of KB.
- Heap impact: <5 MB. Fits any phone.

## 8. Cross-platform: Android + iOS

The artifact format is platform-agnostic by construction (raw
little-endian binary + JSON manifest). Both platforms get the same
`topical_<lang>.db.zip`.

### 8.1 Android

- Pack delivery: `topical_pack` asset-pack module (on-demand).
- Debug fallback: `app/src/debug/assets/topical/topical_<lang>.db.zip`,
  copied to cacheDir on first use.
- mmap: `FileChannel.map(MapMode.READ_ONLY, …)`. 2 GB per-region limit;
  our largest file is 663 MB.
- KNN math: plain Kotlin `FloatArray` operations + per-row inlined f16
  decode. If perf is ever insufficient on old devices, drop to NDK +
  NEON SIMD — a self-contained code change that doesn't affect the
  on-disk format.
- Reader: `app/src/main/java/com/classicsviewer/app/topical/TopicalReader.kt`.
- Activity: `TopicalLinksActivity.kt` with a `Spinner`-based dropdown.
- Action-bar wiring: `menu_bookmark_editor.xml` adds
  `action_topical_links`; `BookmarkEditorActivity.kt` toggles
  `MenuItem.isVisible` via `onPrepareOptionsMenu`.
- The icon: `app/src/main/res/drawable/ic_topical_links.xml`, white
  stroke for the dark action bar.

### 8.2 iOS

- Pack delivery: zip in `ClassicsViewer/Resources/topical_<lang>.db.zip`,
  extracted to `Application Support/topical_unpacked_<stem>/` on first
  use via `ZIPHandler.extractAll`.
- mmap: `Data(contentsOf: url, options: .alwaysMapped)`.
- KNN math: Swift with `Data.withUnsafeBytes`. Accelerate framework would
  be a follow-up speedup (`cblas_sgemv`); not in the current ship.
- Reader: `ios/ClassicsViewer/Database/TopicalDatabase.swift`
  (`TopicalReader` actor) — file kept this name so the existing Xcode
  project picks it up without regeneration.
- View: `ios/ClassicsViewer/Views/TopicalLinksView.swift` with a SwiftUI
  `Picker`.
- Per project rule, no Claude-driven xcodebuild. New Swift sources land
  in the source tree; the user regenerates the project as needed.

### 8.3 What stays in lockstep across platforms

- `manifest.schema_version` and file magic numbers gate format
  compatibility.
- The query algorithm (IVF nprobe, runtime cutoffs, merge rule) is
  defined here and implemented identically on both. If they diverge,
  results diverge.

## 9. Validation gates

Build must fail red if any of these miss; gates run inside
`build_topical_pack.py`:

### 9.1 Determinism

After steps 1–7 complete once, rerun steps 4–7 (the seeded parts) with
the same inputs. Outputs must be byte-identical (sha-equal). Mismatch =
red.

### 9.2 IVF recall

Sample 100 random source `row_idx`. For each, compute exact dense KNN
top-30 (brute force) and IVF KNN top-30 with the chosen `nprobe`. Compute
average recall@30. **Fail if < 0.95.**

If a build fails this gate, raise `ivf_nprobe` (or `nlist`), rebuild,
recheck. We do not ship low-recall IVF.

### 9.3 Statistical quality gates

Per `TOPICAL_EVAL_SAMPLE.md`'s rule against curated work-level
expectations, we use only corpus-wide statistics:

- **Topic coherence (NPMI)**: mean pairwise NPMI of each topic's top 10
  terms against a held-out co-occurrence count. Fail if mean NPMI < last
  green build's baseline_mean − 0.05.
- **Coverage histogram**: for a random sample of 10,000 sources, count
  surviving neighbours per kind. Fail if median source has fewer than 5
  surviving LDA neighbours, or if the 10th-percentile source has zero.

Both are class-level. A regression that breaks one specific work but
leaves the global distribution intact won't fail these gates — and we
accept that, because work-level regressions belong in user-facing
feedback loops, not in the build.

### 9.4 Pack size gate

After zip, assert `topical_<lang>.zip` ≤ size_threshold (currently 600 MB
Greek, 120 MB Latin). Catches accidental blowup (e.g. someone bumps
K_topics to 2000 without thinking).

### 9.5 Text-integrity baseline (project-wide rule)

This is the rule added to `CLAUDE.md` for any major refactor that
regenerates `translation_segments` or `text_lines` at scale. Before a
rebuild that touches the interlinear, take a baseline via
`data-prep/text_integrity/audit.py`. After the rebuild, rerun and diff.
Any non-Latin per-work regression, or any Latin regression on
source-text or English-translation integrity (only the interlinear
translator's segments are allowed to change), blocks release. See
`latin/LATIN_POS_PLAN.md` §0/§8 for the worked example.

## 10. Empirical evidence (summary)

Two separate evaluation artifacts live alongside this spec:

### 10.1 `SPOTCHECK_11.md` — qualitative LDA spot-check

Top-5 LDA neighbours for the opening passage of ~15 representative Greek
works. Key findings:

- **Strong topical hits**: Hesiod *Theogony / Works and Days* 1.1 →
  Homeric Hymns + Pindar + Bacchylides (Muse-invocation cluster, cosines
  0.91–0.93). Plato *Apology* 1.1 → Demosthenes / Hyperides / Dinarchus
  (forensic oratory — *Apology* IS a defence speech). Aeschylus
  *Agamemnon* → Euripides + Sophoclean scholia. NT Matthew 1.1 → 1
  Chronicles genealogy + Origen + Epiphanius (Matthew 1.1 opens with a
  genealogy).
- **Same-author clusters where appropriate**: Plato *Republic* 1.1 →
  Plato dialogues; Iliad 1.1 → Iliad scholia. Per `TOPICAL_EVAL_SAMPLE`'s
  earlier finding, same-author isn't noise when the author wrote
  repeatedly on the same theme.
- **Weakest in the spot-check**: Herodotus 1.1 (some scholia hits feel
  like noise) and Aristotle *Politics* 1.1 (cosines drop below 0.6 for
  several rows).

### 10.2 `TOPICAL_EVAL_SAMPLE.md` — same-author-bias study

Stratified ~45 distinct Greek passages across 10 genres. Reported lift
of same-author neighbours over chance. Key results:

- Mean lift at K=10: **TF-IDF ×53, LDA ×38**; median lift ×9 vs ×0
  respectively. The median tells the typical-case story: half of LDA
  queries return zero same-author neighbours; TF-IDF rarely does.
- Worst-case same-author rates concentrated in Oratory (Isocrates,
  Demosthenes), Medicine (Hippocrates, Galen), and parts of Patristic
  (NT).
- Reading the actual neighbour text revealed most of those "biased"
  results are correct (Demosthenes' *Onetor I* IS the same legal case as
  *Onetor II* and the Aphobus suits; Hippocrates wrote multiple
  treatises on bones). The high lift reflects real topical clustering
  in those oeuvres, not register-driven noise.

This is the empirical basis for the per-kind dropdown (§6). The three
kinds have qualitatively different result shapes; the user picks the
lens. We do not merge them into a single ranked list.

### 10.3 Entity kind — qualitative spot-check (post-ship)

After the entity kind shipped, a parallel spot-check at the opening
passage of 4 Greek + 4 Latin sources confirmed it surfaces results
LDA/TF-IDF cannot:

**Greek (strong):**
- Homer *Iliad* 1.1 (entities: Ζεύς, Ἀχιλλεύς, Λητώ, Ἀτρείδης,
  Πηληιάδης) → Euripides *Hecuba*, Sophocles *Philoctetes*, Maximus
  *Dialexeis*, Libanius *Epistulae* — all at cosine 0.62, all on the
  Zeus+Achilles axis.
- Herodotus *Histories* 1.1 → Plutarch *Of Herodotus's Malice* at 0.78
  (exactly on topic), plus Iliad scholia on Argos, Athenagoras, and
  Aristotle's *Mirabilium* on the Greek-Persian-Phoenician cluster.
- Plato *Republic* 1.1 → Plutarch on Polemarchus/Niceratus/Theramenes;
  Xenophon *Memorabilia* (Socrates+Glaucon); Lysias *Against
  Eratosthenes* (Polemarchus — the host of *Republic*).
- NT Matthew 1.1 → Vulgate Matthew 1.1 at 0.60; Epiphanius and Luke 3
  genealogies; LXX 2 Chronicles royal lists.

**Latin (strong after the case-marker stoplist landed):**
- Vergil *Aen.* 1.1 (entities: italia, iunonae, troias, musa,
  laviniaqus) → Quintilian *Institutio* 11.40; Horace *Ars Poetica* and
  *Odes* (musa/Iuppiter/troias); Propertius *Elegies* (Iunonae).
- Caesar *BG* 1.1 (entities: hispania, orgetorix) → Livy *History* 29
  and 43; three Cicero letters on Hispania + Brundisium.
- Tacitus *Annales* 1.1 → Cicero *Philippics* (roma, sulla, cinna);
  Seneca *De Clementia* (cinna+lucius+pompeius cluster); Martial
  *Epigrams*.
- Ovid *Metamorphoses* 1.1 → empty entity bag (correct: "In nova fert
  animus" mentions no proper nouns; the empty bag returns "No entries
  found" as designed in §6.4).

The Latin Stanza-PROPN tagger occasionally mis-tags editorial
abbreviations (`gen.`, `nom.`, `acc.`, `dat.`) as proper nouns; the
build script's `LATIN_ENTITY_STOPLIST` (§11) filters these out. See
also `SPOTCHECK_LATIN.md` (local, untracked).

## 11. What this design does *not* fix

Honesty section.

- **LDA topics drift when text or vocabulary changes.** Pinned seed +
  pinned `tomotopy_version` + pinned `sklearn_version` make the build
  byte-deterministic for fixed inputs, but re-fitting LDA on different
  counts produces different topics, and a given source's neighbours
  shift. Fundamental to any topic-model approach.
- **Quality calibration is empirical.** Neither `lda_min_sim` nor
  `tfidf_min_sim` is principled; they're eyeballed and runtime-tunable.
  A future evaluation-driven pass should set them properly against a
  held-out judged set.
- **Author bias in the model itself.** The dropdown lets the user route
  around author bias by switching kinds, but neither kind *eliminates*
  it. A future ranker could de-emphasise same-author overlap on the
  Topical branch — but that's runtime policy, not artifact format.
- **Latin entity tagger noise.** Stanza's PROPN tag occasionally fires
  on editorial abbreviations (`gen.`, `nom.`, `acc.`, `dat.`, `abl.`,
  …) in scholarly Latin. The build's `LATIN_ENTITY_STOPLIST` mitigates
  the worst cases (case markers, number/gender/mood abbreviations) but
  doesn't catch every false PROPN. Symptom: low-IDF tokens in some
  entity bags. Not a structural fix; would need a better tagger or a
  more conservative POS filter.
- **Greek entity tagger approximation.** OGA/GLAUx don't tag PROPN, so
  Greek entities are extracted as *NOUN with uppercase first character*
  — a heuristic that approximates PROPN with high but imperfect recall
  (e.g. titles like "βασιλεύς" can sneak in if capitalised). Acceptable
  in practice; the spot-check (§10.3) shows it surfaces the right
  people and places.

## 12. Open questions and planned kinds

### 12.1 The `entity` kind — shipped (Greek + Latin)

`kinds_available` ships `["lda", "tfidf", "entity"]`. Two passages are
topically related under the entity kind if they share named entities
(persons, places, deities). For history, geography, and patristic
genres this surfaces signal LDA/TF-IDF can't reliably produce —
`TOPICAL_EVAL_SAMPLE.md` showed History dropping to n=0 because all
three sampled historians had nearly all their passages in a single
work, and the cross-work baseline was zero under purely-lexical kinds.
The entity kind closes that gap: Herodotus passages on the
Persian Wars now surface Plutarch's *Of Herodotus's Malice* (cosine
0.78), and Caesar *BG* 1.1 surfaces Livy + Cicero letters on Hispania.

**Greek** uses a NOUN+uppercase-first-letter heuristic because OGA and
GLAUx don't tag PROPN reliably. See §11 for the limitation.

**Latin** uses Stanza's `POS == "PROPN"` after the Latin POS rebuild
(see `latin/LATIN_POS_PLAN.md` for that pipeline). A small
`LATIN_ENTITY_STOPLIST` in the build script drops editorial case-marker
abbreviations Stanza occasionally mis-tags as proper nouns.

**On-disk artefacts** (§§2.10–2.12): `entity_bags.bin`,
`entity_invidx.bin`, `entity_vocab.bin`. Runtime branch is §4c.
Spot-check evidence is §10.3.

### 12.2 Open questions and next kinds

Beyond the three shipping kinds, candidate signals worth evaluating:

- **Temporal / dating overlap.** Two passages referencing the same
  archon year or Olympiad would link tightly. Needs a date-mention
  extractor on top of NER; not in scope today.
- **Citation overlap.** Cross-references where work A cites a verse of
  work B. Patristic and scholiastic corpora are dense with these. The
  extraction is non-trivial (the citation format varies wildly across
  authors) but would surface different neighbours than entity or LDA.
- **Genre-conditioned kinds.** Per-passage genre tags would let a kind
  weight neighbours within or across genres. Genre tagging at the
  passage level is currently absent.

### 12.3 K_topics sweet spot

K=1000 is the current ship value (single seed, tomotopy). Sized for the
~331k Greek corpus's likely topic count (estimated 500–1500 from
domains × subtopics × heuristics). The spot-check (§10.1) shows strong
results at K=1000; we have not run an NPMI sweep across K=500/1000/2000.
If we ever do, the gate in §9.3 is the place to compare candidates.

### 12.4 IVF nprobe vs recall tradeoff

`ivf_nprobe = 24` (runtime override of manifest's `10`) was chosen by
hand to balance recall against the per-query cost. With nlist=576, each
extra nprobe step scores ~580 more rows. We have not measured exact
recall at the runtime nprobe (build-time gate uses nprobe=10). Worth a
follow-up once the post-Latin-POS rebuild ships.

### 12.5 iOS mmap of `T.f16` at 663 MB

Verified to work on test devices, but iOS imposes resource budgets that
older hardware may stumble on. If we ever see EOM crashes from the
`Data(contentsOf: …, options: .alwaysMapped)` call, the fallback is
chunked `FileHandle` reads — slower but bounded memory. Not implemented
today.

---

*End of spec.*
