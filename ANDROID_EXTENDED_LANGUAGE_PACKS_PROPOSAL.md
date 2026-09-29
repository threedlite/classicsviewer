# Proposal: ship the extended database on Android as a delta of the full database

Status: proposal, not started. Revised 2026-09-27 against 0.8.139. This
revision replaces the 2026-09-20 design, which cut two supplement packs
from separately assembled databases and relied on id bands. Sections 2
and 3 are unchanged from that version except for three lines in section 3
that named the old supplements, one corrected row count (`lemma_map`,
below), a stale note about `ASSET_PACK.md` in section 2, and the new
subsection at the end of section 3, which records the measurement that
motivates the revision.

## 1. Summary

Derive the full database from the extended database by filtering, instead
of assembling it from its own module builds. Ship the difference between
the two, the **extended delta**, as on-demand Play Asset Delivery packs
beside the existing full pack, and merge the delta into the on-device
`perseus_texts.db` at runtime. The sample database and the iOS curated
database are not touched: they keep their own assemblies, their own ids
and their own build markers.

Why this works: the full DB is already an exact content subset of the
extended DB, verified row for row on 2026-09-27 (section 3, last
subsection). Cutting it from the extended DB instead of rebuilding it
changes nothing a user can see, but it makes every id in the full DB the
same id the extended DB uses. The delta is then the rows of the extended
DB whose ids are absent from the full DB. Merging it is a plain insert:
nothing collides, nothing is remapped, and full plus delta equals extended
exactly. The id bands, the base stamping, the lexicon renumbering in the
sample and iOS builds, and the `Int` to `Long` entity change of the
previous design all disappear.

The design has five parts:

1. **Play limits decide whether this ships at all** (section 2,
   unchanged). 1.5 GB per pack applies to everyone. The delta is 1.78 GB
   compressed (measured 2026-09-27), so it ships as two physical packs,
   which the build cuts by size. The cumulative on-demand limit is printed as 30 GB
   but may be 4 GB for this account; with the delta the on-demand total is
   about 4.7 GB. An internal-track upload settles it before any app code
   is written (section 12, milestone 1). **If Play holds this account to
   4 GB, this proposal is cancelled**: no parts ship, the app is
   unchanged, and Android's extended route stays the whole extended zip
   on the external download, as today. There is no reduced variant that
   ships some of the delta on Play and the rest another way.
2. **Full is a filter of extended** (section 9). `assemble_database.py
   full` no longer merges `greek_texts_full.db` and `latin_texts_full.db`;
   it opens the assembled extended DB and copies the full set of works and
   lexicon languages into a new canonical-schema file, ids preserved, and
   cuts the delta parts in the same run. The full build therefore
   requires the extended build.
3. **Every database carries the build it came from** (section 6). The
   assembly already writes a `build_time` row into `dictionary_entries`.
   The filter copies that row unchanged, so the full DB, the delta parts
   and the extended DB of one data release all carry the same value. The
   installer merges a part only onto a base with the same `build_time`.
   That check replaces bands: it is the only thing that keeps ids
   consistent, and it is exact.
4. **The client merge is `ATTACH` plus `INSERT ... SELECT`** (section 7),
   one part at a time, in registry order, each exactly once per
   extraction of the full pack. Each part is
   deleted from the device as soon as it is merged (decided, section 13);
   the full pack is handled exactly as today. Before the first change
   the current database is copied aside; anything that goes wrong puts
   that copy back on its own, with no dialog, so the user keeps exactly
   what they had, sample or full. They can start Extended again from the
   menu when they choose.
5. **Every path a user can take is enumerated** (section 8). Extended is
   one tap from any base: if the base is the sample, or Play holds a
   newer full pack than the device, the same job downloads and extracts
   the full pack first, then merges the parts, and restarts once at the
   end.

**The external whole-database route is kept as it is.** Today an Android
user can download `perseus_texts_extended.db.zip` from the external
download and import it through "Select database", with no Play
involvement. That stays: the build keeps producing the whole extended zip
(it already does, for iOS), the external download keeps publishing it,
the import flow is unchanged, and an imported whole DB keeps opening in
preference to the bundled one exactly as today (section 8). The parts are
an addition for users who want a smaller download, not a replacement.

Everything is produced by the existing assembly in one run per mode. There
are no manual steps beyond the ones that exist today.

## 2. Google Play limits, verified 2026-09-20

Fetched directly from the Play Console help page "Optimize your app's size
and stay within Google Play app size limits"
(`support.google.com/googleplay/android-developer/answer/9859372`) on
2026-09-20:

| App component | Download size limit |
|---|---|
| Base module | 500 MB |
| Individual feature modules | 500 MB |
| Individual asset packs | 1.5 GB |
| Cumulative total for all modules and install-time asset packs | 4 GB |
| Cumulative total for asset packs delivered on-demand or fast-follow | 30 GB |
| Total compressed download for an app | 34 GB |
| Maximum asset packs in one bundle | 100 |

Other rules from the same page and from the Play Asset Delivery guides
(`developer.android.com/guide/playcore/asset-delivery`, updated 2025-09-18,
and `.../asset-delivery/integrate-java`, updated 2026-09-16):

- Limits are on **compressed download size**. Our pack zips are already
  deflated, so the zip size is the number that counts.
- A download over **200 MB on mobile data** does not start until the user
  consents through `showConfirmationDialog()`. The app already handles
  `REQUIRES_USER_CONFIRMATION` and `WAITING_FOR_WIFI` in
  `FullDatabaseDownloadManager.kt`.
- On-demand packs are delivered as archives and expanded into the app's
  internal storage. The app must treat those files as read-only and must not
  assume they persist. `removePack()` schedules deletion of a pack.
- On an app update, previously downloaded on-demand packs are invalidated and
  patched to the new version. The app can be opened before the patch lands.
- Apps over 200 MB show a non-blocking size dialog at install. Apps over 1 GB
  must target API 21 or higher. We are at minSdk 23.

### Which of these numbers apply to us

**Confident, applies to everyone:** 1.5 GB per pack, 500 MB base, 4 GB for
base plus install-time packs, 100 packs, the 200 MB consent dialog. The
table carries no eligibility clause in any of the five English locales
checked (en, en-GB, en-AU, en-IN, en-CA, raw HTML read on 2026-09-20). The
`full_database_pack` zip in the current tree is 1,085,755,158 bytes and has
been in the bundle since 0.8.78 (2025-12-15). If Play accepted that upload,
the per-pack ceiling is above the old 512 MB figure.

**Not confident: 30 GB cumulative for on-demand and fast-follow packs.**
The evidence conflicts:

- For: the live table lists 30 GB with no footnote, in every locale checked.
- Against: Google's Android Developers blog post of 2025-10-24, "5 things
  you need to know about publishing and distributing your app for Android
  XR", says Android XR apps are afforded 30 GB "instead of a cumulative
  total of 4 GB for asset packs delivered on demand or fast follow". A
  cached copy of this same help page, quoted by search engines, says 30 GB
  applies "instead of 4 GB for developers distributing Android XR titles and
  developers in the Google Play Partner Programme for Games". The Play Asset
  Delivery guide still says "Higher size limits are also possible for
  developers who are part of Google Play Partner Program for Games". The
  App Bundle FAQ, updated 2026-07-28, still says Play "checks that the
  maximum cumulative total compressed download size that any individual
  device receives is not over 4 GB".

Google removed the eligibility wording from the table sometime after
October 2025, but nothing says enforcement changed for a developer who is
neither in the Partner Program nor shipping Android XR. **This proposal
therefore plans against a 4 GB cumulative on-demand budget.** The only test
that settles the question is uploading a real bundle to an internal testing
track: Play Console computes the sizes at upload and rejects there, and no
user sees an internal-track bundle. That upload is milestone 1 (section 12).
If it is accepted above 4 GB, the budget constant in the build is raised
and the proposal proceeds. If it is rejected on the cumulative total, the
proposal is cancelled (section 4).

**Earlier published figures.** Older documentation and most
third-party write-ups quote 512 MB per on-demand or fast-follow pack, 1 GB
for install-time, and 2 GB for all packs combined. Those figures are gone
from the live page. Documents in this repo that should be corrected when
this proposal is adopted:

- `ASSET_PACK.md` (2026-09-20) uses a 4 GB on-demand pool and lists all
  four packs; its closing paragraph was updated with this revision.
- `docs/multipart-database-deployment.md` says 512 MB per pack and describes
  Kotlin and Python files that do not exist in the tree.
- `docs/database-expansion-analysis.md` lists the 512 MB and 1 GB figures.
- `EXTERNAL_CONTENT_DOWNLOAD_ANALYSIS.md` treats 4 GB as the total limit
  including the base; the base counts against the separate install-time
  row.
- `CLAUDE.md` says the database uses install-time delivery. All four packs
  in `app/build.gradle` are `on-demand`.

Play Core library: `com.google.android.play:asset-delivery` release is
2.3.0 (maven metadata last updated 2024-12-17). `app/build.gradle` already
uses 2.3.0.

## 3. What exists today

### Android

- One on-device file, `perseus_texts.db`. `PerseusDatabase.kt:135-143` opens
  it by name with a plain `Room.databaseBuilder`. There is no `createFromAsset`
  or `createFromFile`.
- The sample DB is extracted from the APK on first launch
  (`AssetPackDatabaseHelper.kt`). The only check is `File.exists()`
  (`MainActivity.kt:409-416`), so an app update that ships a newer sample zip
  does not re-extract.
- The full pack overwrites the same file (`FullDatabaseDownloadActivity.kt:187-250`):
  close Room, delete the DB and its `-wal`/`-shm`, extract the pack zip,
  set a preference, restart the process.
- There is no `ATTACH`, no cross-database `INSERT ... SELECT`, and no
  version or hash check on the main DB anywhere in the app.
- Room turns foreign keys on: `PerseusDatabase_Impl.java` (generated)
  executes `PRAGMA foreign_keys = ON`, and six entities declare
  `ON DELETE CASCADE` relationships.
- The language picker is driven by `SELECT DISTINCT language FROM authors`
  (`AuthorDao.kt:15`), and `MainActivity.kt:155-205` auto-registers any new
  language. Merged rows appear in the UI with no picker changes.
- All four asset packs are `on-demand`: `full_database_pack`, `audio_pack`,
  `references_pack`, `topical_pack`.

### iOS

- `ODRManager.swift` requests tags `database_full` and `database_extended`.
  The zips are extracted to `Documents/` as `perseus_texts_full.db` and
  `perseus_texts_extended.db`, kept side by side with the sample, and a
  preference plus restart selects which file `DatabaseManagerAsync.swift`
  opens. iOS uses raw sqlite3, so it can switch files freely.

Android cannot copy the iOS side-by-side model without a 15 GB whole-file
swap, and a single 3.1 GB pack is over the 1.5 GB limit. That is why packs
must be smaller than "extended" and why they must be merged.

### Build pipeline

- `assemble_database.py <mode>` merges module DBs via `merge_database.py`,
  runs the OGA lemma pass, lexicon imports, `translation_lookup` rebuild,
  schema drift check, compression, and copies. The extended zip goes to iOS
  only (`monolith_fn.py:10588-10595`, comment: "too large for Android asset
  pack").
- `merge_database.py` drops AUTOINCREMENT ids and lets SQLite reassign them.
  Only `translation_segments` gets an old-to-new map, for
  `translation_lookup.segment_id`. Text keys (`authors.id`, `works.id`,
  `books.id`) are carried through unchanged and are unique across languages
  by convention.
- The assembled DB carries one build marker: a `dictionary_entries` row with
  `language='system'`, `headword='build_time'`. Nothing on Android reads it.

### Measured content of the current extended DB (built 2026-09-14)

File: 14,989,332,480 bytes; zip: 3,134,906,462 bytes (ratio 0.209).

Per-table size from `dbstat`, MB:

| Object | MB |
|---|---|
| translation_segments | 4,562 |
| words + its two indexes | 5,423 |
| lemma_map + its three indexes | 2,070 |
| text_lines + its two indexes | 1,098 |
| translation_lookup + its indexes | 476 |
| dictionary_entries + its two indexes | 399 |
| books, works, authors, milestones, rules | 30 |

Rows by language (works, text lines, translation segments, word rows):

| Language | works | text_lines | translation_segments | words |
|---|---|---|---|---|
| greek | 2,056 | 2,311,248 | 2,460,585 | 34,731,476 |
| latin | 233 | 360,007 | 466,827 | 4,813,689 |
| sanskrit | 272 | 210,204 | 221,392 | 6,875,295 |
| pali | 5 | 151,933 | 132,752 | 1,064,019 |
| coptic | 51 | 59,477 | 13,613 | 476,460 |
| hebrew | 40 | 23,321 | 108 | 311,491 |
| syriac | 41 | 24,827 | 4,991 | 324,168 |
| norse | 25 | 3,857 | 1,236 | 349,883 |
| italian | 3 | 14,233 | 14,233 | 101,601 |
| chinese | 2 | 1,308 | 114 | 70,469 |
| persian | 1 | 4,192 | 4,179 | 64,324 |
| old_english | 1 | 3,239 | 39 | 19,355 |
| sumerian | 11 | 1,108 | 962 | 3,929 |
| akkadian | 1 | 205 | 202 | 672 |
| arabic | 1 | 78 | 126 | 770 |

Greek by corpus (a work is "perseus" if its id exists in the full DB,
"pta" if its id starts with `pta`, otherwise "first1k"). Authors per
corpus: perseus 91, first1k 307, pta 21, out of 392 Greek authors in total.
**27 authors have works in more than one corpus**, for example tlg0059
(Plato), tlg0006 (Euripides) and tlg0005 (Theocritus), each with works in
both Perseus and First1K. The corpus split is therefore by work, and so is
replacement at merge time (section 7).

| Corpus | works | books | text_lines | translation_segments | segment text bytes | words |
|---|---|---|---|---|---|---|
| first1k | 1,091 | 157,609 | 1,533,035 | 1,542,743 | 1,456,194,376 | 22,839,435 |
| perseus | 772 | 1,835 | 631,721 | 771,390 | 749,297,407 | 9,792,809 |
| pta | 193 | 8,518 | 146,492 | 146,452 | 144,701,083 | 2,099,232 |

Lexicon rows: `lemma_map` has 15.2 M rows (15,194,760, counted
2026-09-27; an earlier draft said 12.8 M) and **no language column**. By
source: DCS (Sanskrit) 9.39 M, Lewis & Short glosses 2.86 M, Whitaker
1.50 M, OGA 276 K, the Greek Wiktionary/LSJ/Cunliffe/treebank sources about
550 K together, then ePSD2 (Sumerian) 200 K, OSHB (Hebrew) 112 K,
Bosworth-Toller (Old English) 101 K, IcePaHC and Zoega (Norse) 96 K, RINAP
(Akkadian) 29 K, the two Coptic sources 44 K, and the Pali dictionary 11 K.
`dictionary_entries` has a language column: sanskrit 360 K,
latin 182 K, old_english 79 K, greek 63 K, norse 30 K, hebrew 21 K,
sumerian 15 K, coptic 11 K, pali 5.5 K, akkadian 3.7 K.

**The Sanskrit lexicon is in the extended DB twice.** The Sanskrit module
build imports `sanskrit/dcs_sanskrit_lexicon.zip` itself
(`create_sanskrit_database_interlinear.py:2060-2115`), and the assembly
imports the same zip again because Sanskrit is listed in `LEXICON_PATHS`
(`assemble_database.py:104`, importer at `monolith_fn.py:9912`). Both use
`INSERT OR IGNORE`, which ignores nothing since the only unique column is
the id. Measured: the module DB has 179,806 dictionary rows and 4,705,160
lemma rows; the extended DB has 359,612 and 9,410,320, with 179,765 and
421,542 distinct. Hebrew, Sumerian and Akkadian are imported once, because
their module DBs carry no lexicon table. The DCS morphology is also one
row per token by design (`extract_dcs_lexicon.py:353`, "duplicates allowed
for frequency tracking"): 4.7 M rows for 421,542 distinct. Whether any
query uses the repetition was not checked.

**Arabic has no lexicon in the extended DB.** `arabic/arabic_lexicon.zip`
holds 43,913 dictionary rows and a morphology CSV, but as
`arabic_dictionary.csv` and `arabic_morphology.csv`
(`create_arabic_lexicon.py:172-174`); the assembly importer reads only
`dictionary.csv` and `morphology.csv` and skips the zip without error.
The app's `DictionaryZipParser.kt:23-24` expects the same two names.

### Measured size of each language, from the module files

Uncompressed is the module SQLite file; compressed is its zip, measured
on 2026-09-20 (Greek was compressed with `zip -9` for this measurement, as
no zip of the extended Greek module exists in the tree). Each module holds
one copy of its lexicon where it has one. The separate lexicon zips the
assembly imports on top are listed in the last column.

| Language | Module file | Uncompressed | Compressed | Separate lexicon zip |
|---|---|---|---|---|
| Greek (extended) | `greek/greek_texts_extended.db` | 9.13 GB | 1.82 GB | none; lexicon inside |
| Sanskrit | `sanskrit/sanskrit_texts.db` | 2.39 GB | 500 MB | 37 MB, duplicate of what the module holds |
| Latin (extended) | `latin/latin_texts_extended.db` | 2.06 GB | 456 MB | none; lexicon inside |
| Pali | `pali/pali_texts.db` | 144 MB | 38 MB | none |
| Coptic | `coptic/coptic_texts.db` | 100 MB | 24 MB | none |
| Old English | `old_english/old_english_texts.db` | 49 MB | 17 MB | none |
| Hebrew | `hebrewOT/hebrew_texts.db` | 93 MB | 17 MB | 2.1 MB |
| Norse | `norse/norse_texts.db` | 64 MB | 16 MB | none |
| Syriac | `syriac/syriac_texts.db` | 20 MB | 4.4 MB | none |
| Italian (Dante) | `dante/dante_texts.db` | 16 MB | 3.7 MB | none |
| Persian | `persian/persian_texts.db` | 7.9 MB | 2.3 MB | none |
| Chinese | `chinese/chinese_texts.db` | 7.6 MB | 1.7 MB | none |
| Sumerian | `cuneiform/sumerian_texts.db` | 1.1 MB | 0.2 MB | 1.0 MB |
| Akkadian | `cuneiform/akkadian_texts.db` | 0.3 MB | 0.05 MB | 0.2 MB |
| Arabic | `arabic/arabic_texts.db` | 0.2 MB | 0.04 MB | 7 MB, not imported |

The modules total about 14.1 GB uncompressed and 2.9 GB compressed. The
extended DB is 15.0 GB and 3.13 GB, the difference being the rebuilt
lookup table, the OGA lemma pass and the duplicated Sanskrit lexicon.

The Greek figure is the whole module, including the Greek lexicon that
the sample and full DBs already carry. It is a check on the corpus split
in section 4 (Perseus text about 0.5 GB, First1K about 1.1 GB, PTA about
0.1 GB compressed, the rest lexicon and indexes), not the size of the
Greek parts of the delta. Sanskrit's text tables match the extended DB row for
row.

Two facts that shape the design:

- The **Greek lexicon is identical in sample, full, and extended** (same
  sources, same counts: LSJ 30,639, Wiktionary 22,774, Cunliffe 9,396; the
  same lemma_map sources and counts). The Greek parts of the delta therefore
  carry text tables only.
- The **sample DB has no Latin lexicon at all.** Its `dictionary_entries`
  are greek plus the system row, and its `lemma_map` has no Whitaker or
  Lewis & Short rows. `latin/latin_texts_sample.db` has an empty
  `dictionary_entries`. The full DB has the Latin lexicon (182 K entries).
  No part carries it, so a user on the sample base has no Latin
  lexicon with or without the delta, exactly as today.


### Verified 2026-09-27: the full DB is an exact content subset of the extended DB

Both files are from the same data release (`perseus_texts_full.db` and
`perseus_texts_extended.db`, built 2026-09-14). The full DB was attached
to the extended DB and every table was compared with `EXCEPT` on all
content columns, ids excluded. Result:

| Table | Rows in full but not in extended |
|---|---|
| `works`, `books` (all columns) | 0 |
| `text_lines` (book, line, sequence, text, xml, speaker) | 0 |
| `translation_segments` (book, lines, sequence, text, translator) | 0 |
| `words` (word, book, line, sequence, position) | 0 |
| `lemma_map` (form, lemma, source, morph, confidence) | 0 |
| `normalization_patterns`, `prefix_assimilation_rules` | 0 |
| `milestone_line_ranges` (work, milestone, lines) | 0 |
| `translation_lookup` (book, line, and the pointed-at segment's lines, translator and text) | 0; 1,729,102 rows in both |
| `dictionary_entries` | 1: the `language='system'`, `headword='build_time'` row, whose value is the build's own timestamp |
| `authors` | 2: `tlg0090` Agathemerus and `tlg2018` Eusebius have `has_translations=0` in full and `1` in extended, because their translated works are First1K works |

Every `works.id`, `books.id` and `authors.id` in full exists in extended.
The work sets are separated by a rule that already exists in the data:

| Language in extended | Works | Of which in full |
|---|---|---|
| Greek, id without suffix (Perseus) | 772 | 772 |
| Greek, id ending `_OGL` (First1K) | 1,091 | 0 |
| Greek, id ending `_PTA` (PTA) | 193 | 0 |
| Latin, Italian, Old English, Sumerian, Akkadian | 233, 3, 1, 11, 1 | all |
| Sanskrit, Pali, Coptic, Hebrew, Syriac, Norse, Chinese, Persian, Arabic | 272, 5, 51, 40, 41, 25, 2, 1, 1 | none |

The suffixes are assigned by the Greek module (`monolith_fn.py:8148-8153`).

The reverse direction holds too, which is what the filter needs: for the
books the full DB has, the extended DB has no `text_lines`,
`translation_segments` or `words` row that full lacks; for the five
lexicon languages the full DB has, no `dictionary_entries` row; and for
the sixteen `lemma_map` sources present in full, no `lemma_map` row;
and for full's works, no `milestone_line_ranges` row and no
`translation_lookup` row (compared by book, line and the text of the
segment each points at, since the segment ids differ until the filter
lands).
Every `lemma_map` source present only in extended belongs to an
extended-only language: DCS and DCS+Sandhi (Sanskrit), OSHB (Hebrew),
IcePaHC, Zoega and Thorpe Glossary (Norse), the two Coptic sources, and
Statistical Dictionary (Pali). So a filter of the extended DB by work set
and lexicon language reproduces today's full DB exactly, apart from the
`build_time` row and the two derived flags, provided translation
segments whose book id has no books row are scoped by work (section 9);
the content comparison above collapses those rows into the books they
name and so did not show them.

The largest ids in the extended DB are `words` 49,207,601, `lemma_map`
15,194,760, `translation_segments` 3,324,121, `text_lines` 3,169,237 and
`dictionary_entries` 768,625, all far below 2^31.

The forward comparison took 15 minutes on the desktop, almost all of it
the unrestricted `words` table; the reverse, restricted to full's books,
took under a minute. The commands are recorded in section 12, item 1, so the
build can repeat them.

## 4. Pack layout

### The delta, cut into parts by size

Two database sources on Play: the existing full pack, unchanged in
delivery and in the app's whole-file replacement flow, and the extended
delta, which is one logical unit cut into as many physical packs as the
1.5 GB per-pack cap requires.

| Pack (Gradle module) | Content | Uncompressed | Zip |
|---|---|---|---|
| `full_database_pack` (existing) | the filtered full DB: Perseus Greek, Latin, Sumerian, Akkadian, Italian, Old English, with the Greek and Latin lexicons | 4.97 GB (measured today; the filtered file will differ only by `VACUUM` layout) | 1.09 GB (measured today) |
| `db_extended_part1_pack` … `db_extended_partN_pack` | everything in extended that is not in full: First1K and PTA Greek text, and nine languages with their lexicons where one exists (Persian has none, Arabic's is not imported; section 3) | ~10 GB | ~2.0 GB total, estimated |

The delta estimate is the extended zip (3.13 GB) less the full zip
(1.09 GB), which assumes compression is additive; the 2026-09-20 slice
estimates (Greek supplement ~1.2 GB, languages ~0.6 GB) give about
1.8 GB, and that lower figure assumed a change to the Sanskrit lexicon
that this proposal does not make, so 2.0 GB is the better guide. **The
build measures the real sizes and the estimate decides nothing.** Either
figure is over 1.5 GB, so the delta is at least two packs.

The build cuts parts with these rules, in order:

1. A part holds whole works and whole lexicon languages. No work and no
   lexicon language is split across parts.
2. The first cut is by language and corpus: First1K Greek, PTA Greek, and
   each of the nine other languages are the units. Units are packed
   largest first into parts under the size target (1.2 GB, decided; 20
   percent under the cap).
3. If a single unit is over the target (First1K alone is estimated at
   1.1 GB and grows), it is split by author, largest authors first.
4. A Gradle module exists in `settings.gradle` for every part and for
   nothing else: an asset-pack module with an empty `assets/` fails
   `bundleRelease`. The build fails if the parts and the modules do not
   match one to one, so adding a part is a visible, reviewed change.
   Provision as many as the first measured cut produces.

Parts are an implementation detail of one user-facing choice, "Extended".
They are merged in registry order (any order would work, since parts
share nothing) and the UI groups them under one row (section 10). There is no per-part install or removal.

### The on-demand budget, and the go/no-go it implies

Every part is cut on every full build. `shared/pack_layout.py` holds
`PLAY_ON_DEMAND_BUDGET_BYTES`, and the build fails if the sum of every
on-demand pack in the bundle, database and non-database alike, exceeds
it. Sizes from the tree today:

| On-demand pack | GB |
|---|---|
| audio_pack | 1.02 |
| topical_pack | 0.52 |
| references_pack | 0.10 |
| full_database_pack | 0.97 (was 1.09 before the filter; the filtered file is written compact) |
| **Current total** | **2.61** |
| extended delta, all parts | ~1.8 (extended zip 2.75 GB less full zip 0.97 GB, after compaction) |
| **Total with the delta** | **~4.4** |

The total is over 4 GB by 0.5 to 0.7 GB, and every part is on Play or
the proposal does not ship. So the probe upload (section 12, milestone 1)
is a go/no-go gate, decided before any Kotlin is written:

- **Play accepts the 10 GB probe bundle:** the account is not held to
  4 GB. `PLAY_ON_DEMAND_BUDGET_BYTES` is set to 10,000,000,000, the
  figure actually proven, and the proposal proceeds with every part on
  Play and about 5 GB of headroom for the extended corpus to grow.
- **Play rejects it on the cumulative total:** 4 GB is the real limit and
  **the proposal is cancelled.** Nothing in the app changes. The whole
  extended zip on the external download remains Android's route to the
  extended corpus, as today. The build pipeline also stays as it is: the
  filter and the delta cutter are not adopted on their own (decided,
  section 13).

There is deliberately no third outcome in which part of the delta goes
through the external download and part through Play. The earlier draft
had one; it doubled the channels to keep in step, the version-skew cases
and the UI states, for a user population that already has the whole
extended zip. The whole extended zip stays on the external download under
both outcomes, for users who prefer one file, cannot use Play, or want
everything without a merge.

### Alternatives no longer considered

- **Two complement supplements with id bands** (the 2026-09-20 design).
  Superseded: the bands existed only because full and extended were
  numbered independently. They cost a renumbering of lexicon ids in every
  build including sample and iOS, a `layout_version` marker in every base,
  an `Int` to `Long` change in three Room entities, and a text-integrity
  re-baseline. None of that is needed once full is cut from extended.
- **One pack per language.** Still possible on top of this design, since
  the parts mechanism is the same, but not chosen: seventeen modules and a
  language-list UI for a benefit users have not asked for.
- **The whole extended DB as split packs, opened as a separate file.**
  Leaves the full pack untouched on the device, but costs 3.13 GB of
  on-demand budget instead of 2.0 GB, keeps two 5 GB and 15 GB databases
  on the phone for a user who has both, and only fits under the 30 GB
  reading. Kept as a fallback if the merge time measured in section 12
  turns out unacceptable.

## 5. Pack contents

A part is one zip file:

```
<part>.db.zip
    <part>.db          a canonical-schema SQLite file, ids as in extended
    manifest.json      the part manifest
```

The manifest lives inside the zip so the part is self-describing
wherever it is found, including the debug-build fallback of scenario 17.
The module's `src/main/assets/` also holds a sidecar copy,
`<part>.manifest.json`, so the UI can show size and contents before
download. The client takes everything from the copy inside the zip
except `zip_sha256`, which by construction can only be in the sidecar (a
file cannot contain its own hash); the two copies must agree on
`build_time`. Found on the device 2026-09-27: the first installer build
read the hash from the in-zip copy, where it is absent, and refused every
part; the refusal path then restored the sample exactly as designed.

`<part>.db` is created with `shared/database_schema.py`'s
`create_schema()`, passes `diff_against_canonical()`, has all 12 tables
and 21 indexes, is `VACUUM`ed, and carries the same `build_time` system
row as the extended DB it was cut from. Tables the part does not use are
empty. A Greek part has rows in `authors`, `works`, `books`, `text_lines`,
`words`, `translation_segments`, `translation_lookup` and
`milestone_line_ranges`. A part with a lexicon language also has
`dictionary_entries`, `lemma_map`, `normalization_patterns` and
`prefix_assimilation_rules` for that language.

The full pack gains a sidecar `full.manifest.json` in
`full_database_pack/src/main/assets/`, with the same fields, so the app can
read the full pack's `build_time` without extracting 5 GB (section 8).

The manifest:

```json
{
  "manifest_version": 1,
  "pack_id": "db_extended_part1",
  "part": 1,
  "parts": 3,
  "build_time": "2026-09-14T18:01:20.245519",
  "schema_sha256": "<sha256 of canonical sqlite_master DDL>",
  "corpora": ["first1k"],
  "languages": ["greek"],
  "lexicon_languages": [],
  "lexicon_id_ranges": {"lemma_map": [], "dictionary_entries": [],
                        "normalization_patterns": [], "prefix_assimilation_rules": []},
  "db_bytes": 0, "zip_bytes": 0, "zip_sha256": "<sha256 of <part>.db.zip>",
  "rows": {"authors": 0, "works": 0, "books": 0, "text_lines": 0, "words": 0,
           "translation_segments": 0, "translation_lookup": 0,
           "milestone_line_ranges": 0, "dictionary_entries": 0, "lemma_map": 0,
           "normalization_patterns": 0, "prefix_assimilation_rules": 0}
}
```

`build_time` is the release identity (section 6). `manifest_version` is
the format of this file and the installer's contract, bumped only when the
installer changes. `schema_sha256` is checked against the same hash
computed from the base database's `sqlite_master` on the device, which
Room has already validated against the app's entities, so no constant
has to be kept in step with the schema by hand. The device hash skips
`android_metadata` (which Android creates on the first read-write open)
and `room_master_table` (Room's); neither exists on the build machine.
Found on the device 2026-09-27: part 2 was refused because part 1's merge
had created `android_metadata` and changed the hash. `lexicon_id_ranges` lists `[lo, hi]` pairs per lexicon table
for the part's languages (section 6), used to count the merged lexicon
rows against `rows` when verifying the merge.

## 6. Ids and the release check

No bands. Every id in the full DB and in every part is the id the extended
DB assigned, and the three are cut from one file, so per table the id sets
of full and of all parts partition the id set of extended. The build
proves this on every run (section 9, check 5).

What has to hold, and how each is enforced:

- **Ids stay below 2^31.** The three Room entity fields declared `Int`
  (`LemmaMapEntity.id`, `DictionaryEntity.id`,
  `TranslationLookupEntity.segment_id`) stay `Int`. The assembly asserts
  after every extended build that `max(id) < 2^31` in all seven
  AUTOINCREMENT tables; today the largest is 49 M against a limit of
  2,147 M.
- **A base and a part must come from the same extended build.** Ids are
  consistent only within one assembly. The `build_time` row that the
  assembly already writes into `dictionary_entries` is the release
  identity: the filter copies it unchanged into the full DB, and the
  delta cutter copies it into every part. The row's `entry_plain` reads
  `Build Time: <timestamp>` on its first line and `Mode: <mode>` on the
  second; the timestamp is the identity, the mode differs by design (the
  filter rewrites the full DB's row to say `full`). The manifest's
  `build_time` is the bare timestamp, and the installer takes the text
  after `Build Time: ` on the first line of the base's row. The installer reads it from the base
  (`SELECT entry_plain FROM dictionary_entries WHERE language='system'
  AND headword='build_time'`) and from the part's manifest and refuses to
  merge unless they are equal. This is the one check that replaces bands,
  and unlike bands it also catches a part from a different release, which
  bands only tolerated.
- **The sample DB can never be a base for a part.** Its ids start at 1
  from its own assembly and its `build_time` is its own. The release check
  refuses it without any special case. The UI does not offer the delta on
  a sample base; it offers Extended, which installs the full pack first
  (section 8).
- **`lemma_map` has no language column.** The filter must know which of
  its rows are Greek and Latin, and a part's manifest must say which rows
  are its languages'. The assembly inserts lexicon rows at three places
  (the module merge in `merge_database.py` at the repo root, the OGA
  pass, and the lexicon import in `monolith_fn.py`), knows the language
  at each, and inserts each language's rows in blocks. It records
  `[language, table, lo, hi]` for every block, several per language where
  a language is inserted more than once, into a sidecar,
  `data-prep/perseus_texts_extended.lexicon_ranges.json`, written with the
  extended DB. The filter and the delta cutter consume it. The `source`
  column is a cross-check: the build asserts that every row inside a
  language's ranges has a `source` value registered to that language in
  `shared/pack_layout.py` (today Lewis & Short and Whitaker are Latin,
  OGA and the three Wiktionary sources are Greek, ePSD2 Sumerian,
  Bosworth-Toller Old English, and so on), and that no row outside the
  ranges has one of them. Tables with a `language` column
  (`dictionary_entries`, `normalization_patterns`,
  `prefix_assimilation_rules`) are filtered by that column and the ranges
  must agree with it.
- **`sqlite_sequence`** is copied as the extended values. Nothing on the
  device inserts into these tables, so its value is irrelevant, but making
  it identical keeps the filtered file a faithful subset.
- **`has_translations` on `authors`** is derived. The assembly never
  computes it; it rides in from the module DBs, where the Greek build
  (`monolith_fn.py:9430`) and the Latin build
  (`create_latin_database.py:380`) run the same SQL: an author has
  translations if any of its works has a segment longer than ten
  characters whose translator is not an interlinear. The filter recomputes
  it from the works it kept with that SQL, lifted into shared code so the
  filter and the modules cannot drift, so the full DB shows 0 for the two
  authors whose translated works are all in First1K, as it does today. A
  part carries the extended value for every author it touches, and the
  merge upserts it, so after the merge the flag is extended's. The
  measured effect today is those two rows.

## 7. Client merge

A new `ExtendedDeltaInstaller` (raw `android.database.sqlite`, not Room)
runs in a foreground service with a progress notification, one part at a
time. A part's source is the Play pack:
`AssetPackManager.getPackLocation(pack).assetsPath()` plus the zip name,
or the debug-build fallback directory of scenario 17.

1. Preconditions, all hard failures with a specific message:
   - the base is the full pack (`base_state.base = full`), not sample and
     not an external whole DB;
   - `AssetPackManager` reports `COMPLETED`, and the zip contains
     `manifest.json` and one `.db` entry;
   - `manifest_version` and `schema_sha256` match the app;
   - **the part's `build_time` equals the base's `build_time`** (section
     6). On mismatch the message names both and says that Google Play has
     not finished updating (scenario 9);
   - free space at least `db_bytes` plus 10 percent of the runtime DB plus
     500 MB.
2. `PerseusDatabase.destroyInstance()`. No Room connection may be open.
3. Inflate `<part>.db` from the zip into `filesDir/packs/tmp/<part>.db`,
   verifying `zip_sha256` while streaming. Not `cacheDir`: the system may
   delete cache files at any time, including under an attached database
   mid-merge.
4. Record the part as `merging` in `pack_state` (section 8), then open
   `perseus_texts.db` read-write:

```sql
PRAGMA foreign_keys = OFF;
PRAGMA journal_mode = OFF;
PRAGMA synchronous = OFF;
ATTACH DATABASE '<filesDir>/packs/tmp/<part>.db' AS part;
```

   No journal for the merge. A crash mid-way leaves the file unusable
   either way (decided: recovery is the rebuild, section 8), so a journal
   would only cost disk: in WAL mode the log grows to the size of the
   largest table being copied, several GB for a Greek part's `words`.

5. Copy, one table per transaction, in FK-safe order (`authors`, `works`,
   `books`, `text_lines`, `translation_segments`, `milestone_line_ranges`,
   `words`, `dictionary_entries`, `lemma_map`, `normalization_patterns`,
   `prefix_assimilation_rules`, `translation_lookup`). `authors` uses
   `INSERT OR REPLACE`; every other table plain `INSERT`, with ids:

```sql
INSERT OR REPLACE INTO main.authors (id, name, name_alt, language, has_translations)
    SELECT id, name, name_alt, language, has_translations FROM part.authors;
INSERT INTO main.words (id, word, book_id, line_number, sequence_number, word_position)
    SELECT id, word, book_id, line_number, sequence_number, word_position FROM part.words;
```

   `INSERT OR REPLACE` on `authors` is safe only because foreign keys are
   off for the merge (step 4): SQLite implements `REPLACE` as a delete
   plus an insert, and with `ON DELETE CASCADE` enforced it would delete
   the author's works and everything under them.
   Columns are listed explicitly from the canonical schema. The indexes
   stay in place and are maintained by the inserts. Dropping and
   recreating them, which the desktop does for speed, is not possible on
   Android: its SQLite is built with temporary storage forced into memory
   (`SQLITE_TEMP_STORE=3`), so `CREATE INDEX` over tens of millions of rows
   sorts in RAM; on a Pixel 6 (2026-09-27) it crashed the process in
   SQLite's allocator during the rebuild of part 1's indexes, at about
   9 GB of database. Incremental maintenance is slower but bounded, and it
   is what the build's round trip runs too. The merge connection also
   sets `PRAGMA hard_heap_limit` (384 MB): should any SQLite allocation
   ever grow past it, SQLite returns an out-of-memory error, a normal
   exception the installer turns into the restore of the previous
   database, instead of the process dying. The app must never crash;
   everything the installer does is streamed with bounded memory, and
   this is the backstop for what was not foreseen.
   A plain `INSERT` that hits a primary key conflict is a hard error, not
   an `OR IGNORE`: it means the release check was bypassed and the base is
   not what it claims to be. With the journal off (step 4) the statements
   run whole, one transaction each, and nothing has to be batched.
   (The idea of dropping the secondary indexes once and recreating them
   after the last part is withdrawn for the reason above.)

6. Verify before declaring success:
   - per table, the count of rows whose `book_id` belongs to the part's
     works (text tables) or whose id is in the part's ranges (lexicon
     tables) equals `manifest.rows`;
   - `PRAGMA foreign_key_check` reports nothing except rows of
     `translation_segments`, whose only violations are the orphan
     segments the extended DB itself carries (section 9); the count of
     those must equal `manifest.orphan_segments`;
   - `PRAGMA quick_check` returns `ok` (on a 15 GB file this alone takes
     minutes and is part of the time measured in section 12);
   - then `DETACH part`, `PRAGMA journal_mode = WAL` (how the shipped
     file has always been), `PRAGMA foreign_keys = ON`, and mark the part
     `installed` in `pack_state`.
7. Delete `filesDir/packs/tmp/<part>.db`. Reopen Room; its schema validation
   is the last gate. A validation failure is a failed step under the
   rebuild rules (section 8), not `DatabaseErrorActivity`: the launcher
   handles it like an interrupted merge.
8. `removePack(part)`. The part's zip is not kept (decided, section 13:
   the merged content is in the database and the zip is dead weight). The
   next part is downloaded only after this, so at most one part zip and
   one inflated part are on the device at a time. The full pack is not
   touched here; whatever the existing flow does with it after extraction
   stays as it is.

**Recovery goes back to the database the user had before the job
started, and nothing else** (decided 2026-09-27, section 13). Before the
first change, the installer copies the current `perseus_texts.db` aside
as `perseus_texts.db.pre_extended` and records the preferences that
describe it (full or sample, the target). On any failure, on the user
leaving the screen mid-job, and on the next launch after an interrupted
job (a job flag in preferences, or a `pack_state` record in `merging`,
checked **before** Room opens, because a half-merged file may be missing
indexes and Room would refuse it), the copy is moved back into place and
those preferences restored. That is exact for every case, including a
full base that Play has since updated to a newer release, and it needs
no download. If no copy exists, which can only mean nothing had been
changed yet, or the copy cannot be moved back, the fallback is the sample
from the APK, and the job is closed either way so a failed restore can
never repeat on every launch. On success the
copy is deleted. There is no in-place repair, no partial-delete logic,
no saved work list, and no state the app has to reason its way out of;
the user starts Extended again from the menu when they choose, and that
is the whole job again from the copy's state. The cost is the copy: up to
5 GB of disk during the job and about a minute to write it.

Because every merge is onto a base that has never seen that part, the
installer has no delete step: a part's rows are inserted exactly once per
extraction of the full pack. A primary key conflict during insert is
therefore a hard error that triggers the rebuild, never something to
skip past.

**Removal.** "Remove Extended" is the rebuild with no parts: re-extract
the full pack and set every part `absent`. Nothing is `removePack()`ed
because the parts were removed as they were merged. Per-work deletion is
not used for removal; re-extraction is simpler, exact, and its cost is the
same 5 GB extraction the full pack install already performs.

Merge duration is not known and must be measured on a mid-range device
before any UI copy quotes a time. A Greek part writes several GB and
rebuilds indexes over tens of millions of `words` rows. Expect minutes to
tens of minutes per part.

## 8. Runtime DB lifecycle and every scenario

State is a handful of values and lives in `PreferencesManager`, next to
`use_full_database`, `external_database_uri` and `full_audio_installed`,
which already record the same kind of thing. No database table, no Room
change, and nothing in `user_data.db`, which holds the user's bookmarks
and dictionaries and is not touched by this proposal. The state must not
live in `perseus_texts.db` because every rebuild in this design starts by
deleting that file. (The 2026-09-20 design put it there and had to copy it
to memory before each rebuild.)

```
base_state   base: sample | full | external      derived from the existing preferences
                                                 (use_full_database, external_database_uri)
             target: sample | full | extended    what the user chose (db_target)
             build_time                          NOT stored: read from the database's own
                                                 build_time row whenever it is needed
             rebuild_failures                    consecutive failures, keyed by the build_time
                                                 they happened under
             last_failure                        part and error text of the last one
pack_state   one JSON object, part id -> {state: absent | merging | installed,
                                          build_time, at}
```

`pack_state` is stored as one JSON string under a single key, read and
written only by the installer and the launcher, so a half-written record
cannot occur: the string is replaced whole. `base_state.target` records
what the user chose. `base` records what is on disk. The two differ while
an install is in progress and after a failure, and the launcher's job is
to make them equal.

**User data is unaffected.** Verified 2026-09-27 against the app and
the three databases:

- **What a bookmark stores.** `bookmarks` (`BookmarkEntity`) holds
  `work_id`, `book_id`, `line_number` and `sequence_number`, plus display
  strings (author, title, label, the line's text, a note). Its unique key
  is (`book_id`, `line_number`, `sequence_number`). No column is a
  database integer id.
- **How a bookmark is opened.** `BookmarksActivity.openBookmark` computes
  the 100-line page from `line_number`, asks the book's `line_count` by
  `book_id`, and starts the reader with `work_id`, `book_id`, the line
  range and `target_line`. The reader then queries `text_lines` by
  `book_id` and line range. Nothing on that path touches `text_lines.id`
  or any other integer id.
- **Those keys are identical across every database a user can be on.**
  `books` rows (including `line_count`) and `text_lines` rows (including
  `sequence_number`) of the sample DB all exist unchanged in the full DB
  (0 differing rows, measured 2026-09-27), and those of the full DB all
  exist unchanged in the extended DB (section 3). The filter and the
  merge copy those rows verbatim. So a bookmark made on the sample base
  resolves to the same line on full and on Extended, and one made on
  Extended still resolves after a return to full or to sample, as
  long as the work is present.
- **Other user state.** The user dictionary tables reference lemma and
  word-form strings. The saved reading position (`saveNavigationState`)
  stores the reader's intent extras as strings: work id, book id, line
  range, language. Audio mappings are keyed by author, title, book number
  and line number. The references-pack page state is keyed by a manifest
  entry id. No user table or preference stores a `text_lines`,
  `translation_segments`, `words`, `dictionary_entries` or `lemma_map`
  integer id.
- **`user_data.db` is never touched.** The full-pack install and the
  reset action delete only `perseus_texts.db`, its journal files and the
  external copy; neither this proposal nor the existing code deletes,
  migrates or rewrites `user_data.db`, and the rebuild and the fallbacks
  reuse those same two flows.
- **What stays as it is today.** A bookmark's line numbers come from the
  data release that was on the device when it was made. If a later data
  release renumbers a work's lines, the bookmark points at the new line
  with the old number, exactly as it does today across full-pack
  releases. This proposal neither causes nor fixes that.

**Policy: the runtime DB is a function of (target, the packs on the
device).** On every launch the app compares `base_state` with the packs
Play reports and with `BuildConfig.VERSION_CODE`, and runs whichever of
the following applies. Each step either completes or leaves a state
that the next launch recognises and resolves through the rebuild rules
below; nothing resumes mid-step.

| # | Start state | Event | What the app does |
|---|---|---|---|
| 1 | Fresh install | First launch | Extract the sample zip from the APK, as today. `base = sample`, `target = sample`. |
| 2 | Sample | User chooses Full | Existing whole-file flow, unchanged: download the full pack, close Room, delete the DB, extract, restart. `base = full`, `target = full`, `base_state.build_time` from the extracted DB. |
| 3 | Sample | User chooses Extended | One job, one tap. The current database is copied aside (section 7, recovery) and `target = extended`. Step A: the existing full download and whole-file extraction, run by the Extended screen itself, without the restart the Full screen performs. Step B: download every part, merge each (section 7). The screen shows both stages, the combined download size and the disk needed up front. The app restarts once, at the end. An interruption or failure anywhere is scenario 12: the copy goes back and the user has their sample again. |
| 4 | Full | User chooses Extended | Same job; step A is skipped unless Play holds a newer full pack than the device (scenario 8). |
| 5 | Extended | User chooses Full | Rebuild with no parts: re-extract the full pack, `target = full`. The parts are already gone. |
| 6 | Full or Extended | User chooses Sample | The existing reset action in `MainActivity` (`resetToBundledDatabase`) already does this for full and external bases: clear the preferences, close Room, delete the DB, re-extract the sample zip. It gains `target = sample`; the full pack is handled as it is today, and the parts are already gone. |
| 7 | Extended | App update, same data release | Play patches the full pack (the parts are no longer on the device). The app compares the full pack's sidecar `build_time` with `base_state.build_time`: equal, so nothing is rebuilt. Cost: none. |
| 8 | Extended | App update, new data release | The full pack's sidecar `build_time` differs from the database's own. The app changes nothing: the working database stays, and the Extended screen reads "Update available" with the cost. When the user taps it, the job of scenario 3 runs in full: copy aside, re-extract the full pack, download and merge every part again. The set of parts comes from the new build's registry and sidecars, not from `pack_state`, because a release may re-cut the delta into a different number of parts. Cost: the copy, the full extraction, about 1.8 GB of downloads and every merge, tens of minutes, routed through the Wi-Fi and consent handling. A failure puts the old extended database back. |
| 9 | Any | Play's packs are mid-update: the full pack and a part are from different releases | Google documents that the app can be opened before patched packs land. The release check catches it: the part's `build_time` differs from the base's. The installer refuses with a message naming both releases; nothing is changed, and the user tries again later. Since an Extended job always installs the full pack Play currently holds before merging parts, this can only happen while Play's own packs disagree with each other. No counter and no wait state. |
| 10 | Full | App update, new data release | Today the full DB is never re-extracted on update. With the sidecar the app detects the new release and marks the Full row "Update available"; the user taps it and the full pack is re-extracted, the same code path as 8 with no parts. Decided (section 13). |
| 11 | Sample | App update | As today. Not changed by this proposal. |
| 12 | Any | Job interrupted (crash, kill, reboot) or any step fails or the user leaves | The job flag, or a `pack_state` record in `merging`, is detected before Room is opened. The app does not ask anything: it moves the pre-job copy of the database back (section 7, recovery), restores the preferences that describe it, records the reason in `last_failure`, and opens the reader on what the user had before, sample or full. One notice says so and that Extended can be started again from the menu, where the screen shows the reason. Nothing is retried on its own. No in-place repair. |
| 12a | Any | Extended install fails a second time for the same release | Same as 12, and the Extended screen now also says the install has failed twice for this release with the recorded reason, and suggests checking free space or waiting for the next app update before trying again. The action stays available; every attempt is a tap by the user. |
| 13 | Any | Download interrupted | Play resumes on-demand downloads itself. |
| 14 | Any | Free space check fails | Refuse before download, or before merge, with the number needed. Never start a merge that might run out of disk half way. |
| 15 | Extended | User clears the app's storage | Everything is gone, including `pack_state` and `base_state`. Next launch is scenario 1. The parts were already removed after merging, so choosing Extended again downloads them afresh; whether Play keeps the full pack through a data clear is not verified and does not change the flow, which is scenario 1 then 3. |
| 16 | Any | Release build sideloaded, or Play packs unavailable | `getPackLocation()` is null. The Full and Extended rows show "Not available from this installation"; the external whole-DB import remains. |
| 17 | Debug build | Developer testing | Asset packs do not exist in an APK. The installer falls back to `getExternalFilesDir("packs")` for `<part>.db.zip` and its manifest, and for the full pack's zip, reachable with `adb push`, which is the one manual step CLAUDE.md allows. `deploy_with_bundletool.sh --local-testing` exercises the real path. |
| 18 | External whole DB as base (`base = external`) | Any | Unchanged from today: the whole external DB opens in preference to `perseus_texts.db`. Parts never merge onto it, even if its `build_time` matches, because the app did not ship it and cannot re-extract it for recovery. A user who wants everything in one external file uses the whole extended zip, as today. |
| 19 | Any | User chooses Extended while a merge or download is already running | One foreground job at a time; the button is disabled and the row shows the running stage. |
| 20 | Extended | User taps Remove on the Extended row | Scenario 5. Parts cannot be removed individually. |
| 21 | Any | Part downloaded but not merged (Play reports present, `pack_state` says absent) | The app was killed after the download completed and before the merge started. The database is intact, so the row shows "Install" and the merge simply continues; this is not scenario 12. |
| 22 | Any | User downgrades the app (sideload of an older APK over a Play install) | Room validation and the release check both still hold; if the older app's `schema_sha256` constant differs, parts are refused with "update the app". Not supported beyond not crashing. |

Parts do not stay on the device after merging (decided, section 13).
Steady-state cost with Extended installed is the runtime DB (~15 GB)
plus whatever the existing full-pack flow leaves behind today, which
this proposal does not change. The price is that every rebuild
(scenarios 8 and 12) re-downloads about 2 GB of parts.

**Rebuild rules, so a rebuild can never loop** (decided, section 13). A
rebuild is the one operation that deletes a working database, so it is
bounded in every direction:

- **A rebuild is only ever started by the user, from the Extended
  screen.** The launcher never starts one and never asks: when it finds
  an open job or a `merging` record it puts the pre-job copy back
  (scenario 12), and when it finds a new data release it leaves the
  working database alone and lets the Extended screen say "Update
  available" (scenario 8). Neither is a dialog. A launch therefore cannot
  trigger a rebuild that triggers a launch.
- **One attempt per step, no retry inside a rebuild.** A rebuild is a
  fixed sequence: fetch the full pack if Play does not hold it, extract
  it, then for each part in registry order download, inflate, merge,
  verify, remove. A step that fails ends
  the rebuild with the reason recorded in `base_state.last_failure`
  (step, part, error text, time). Nothing inside a rebuild retries
  anything; Play's own download resumption is the only retry, and it is
  Play's, not the app's.
- **Every failure ends on the database the user had before.** A failed
  step, an interrupted job, the user leaving the screen, or a Room
  validation failure after a merge all resolve the same way: the pre-job
  copy goes back (section 7, recovery), the reason is recorded in
  `last_failure` and counted in `rebuild_failures` for the current
  `build_time`. The sample from the APK is only the fallback when no copy
  exists. From there the user may choose Extended again from the menu,
  where the screen shows the recorded reason and, after the second
  failure for the same release, says so and suggests what to check. The
  counter changes only what the screen says, never what the app does on
  its own.
- **A part that fails verification fails the rebuild**, it is not
  skipped. A database with some parts is not a state the plan has; the
  user is either on full or on extended.
- **Scenario 9's refusal is not a rebuild.** A release mismatch between
  the full pack and a part is refused before anything is written; the
  message names both releases and the user tries again later. No
  counter, no wait state.
- **Disk is checked before every download and every merge**, not once at
  the start, so a rebuild that would run out of space stops before it
  writes rather than half way through.

`PreferencesManager.useFullDatabase` stays and becomes derived from
`base_state.target`.

**The external whole-database route is preserved.** "Select database"
keeps importing a whole `perseus_texts_*.db.zip` exactly as today: the
file is copied to `external_perseus_texts.db`, the preference is set, and
`PerseusDatabase` opens it in preference to `perseus_texts.db`
(`PerseusDatabase.kt:57-82`). The reset action returns to the bundled
sample. Neither the code path nor the published whole extended zip is
removed or changed by this proposal; a user who never touches Play, or
who is on a sideloaded build (scenario 16), has the same option they have
today, and it gives them everything the parts give a Play user. The whole
zips carry the same `build_time` row as every other artifact of their
release, so the app can show which release an imported file is from.

Parts are not importable through "Select database". A part is only
ever a Play pack (or its debug-build stand-in), so the import flow does
not need to recognise one, and a part zip picked there is refused with a
message rather than treated as a whole database.

## 9. Build pipeline changes

All in `data-prep/assemble_database.py`. No new standalone scripts. No
manual steps.

**Prerequisite, before any of this lands:** offer and, if accepted, run a
`data-prep/text_integrity/audit.py --corpus all` snapshot of the current
extended DB and of the current full DB, per CLAUDE.md. The full DB's
assembly path changes completely, so its audit must be re-run against the
filtered file and diffed against the baseline. The expected diff is zero
per work, because section 3 shows the content is already identical.

**The data is not changed.** The filter and the delta cutter only copy
rows out of the extended DB. No row is added, removed, deduplicated or
altered anywhere in this proposal; the extended DB, and therefore the full
DB and every part, carry exactly what the assembly produces today,
including the duplicated Sanskrit lexicon rows section 3 describes.

### `assemble_database.py extended` (unchanged, plus)

1. After the schema drift check, assert `max(id) < 2^31` in every
   AUTOINCREMENT table. Hard failure.
2. Write `perseus_texts_extended.lexicon_ranges.json` (section 6) from the
   ranges recorded at the three lexicon insertion points, and assert the
   `source` cross-check.
3. `VACUUM` before compression, in every mode (decided 2026-09-27, after
   the filtered full DB's zip came out 11 percent smaller for no other
   reason). Every assembly stage inserts into tables and indexes that
   already hold data, which leaves pages partly filled; VACUUM rewrites
   them packed. Rows and ids are untouched; the file is put back into
   WAL mode afterwards so its header is as it has always been.

The extended run does not cut the delta: the partition check needs the
filtered full DB, which is produced by the full run below.

### `assemble_database.py full` becomes a filter

`MERGE_RULES["full"]` is removed. `greek_texts_full.db` and
`latin_texts_full.db` are no longer inputs to anything; the Greek and
Latin module `full` modes are deleted (decided, section 13). The full
assembly:

1. Require `data-prep/perseus_texts_extended.db` and its
   `lexicon_ranges.json`, and abort if either is missing or older than any
   extended module DB.
2. Create `perseus_texts_full.db` with `create_schema()`, `ATTACH` the
   extended DB, and `INSERT ... SELECT` with explicit columns and ids:
   - `authors`, `works`, `books` and the five text tables for the full
     work set: Greek works whose id has neither the `_OGL` nor the `_PTA`
     suffix, plus every work of every language in
     `FULL_LANGUAGES = {latin, italian, old_english, sumerian, akkadian}`
     (section 3, verified rule). The rule lives in
     `shared/pack_layout.py` next to the language registry.
     `translation_segments` is scoped by book **and** by work for rows
     whose `book_id` has no `books` row: a translation split into parts
     the text does not have (the Verrines are one "Complete Text" book,
     translated as parts 002 to 005). The app cannot reach those rows,
     they have no text lines, words or lookup rows, but today's full DB
     carries the 934 of them that belong to its works, and the filter
     reproduces today's full DB exactly, so they are kept by the work
     their book id names. The extended DB has 2,762 such rows over 374
     book ids, every one naming an existing work, so the delta parts
     cover the rest the same way (found 2026-09-27 by the first filter
     build, which dropped them and so differed from the previous full DB
     by exactly those rows);
   - lexicon rows for `FULL_LEXICON_LANGUAGES = {greek, latin, sumerian,
     akkadian, old_english}` (section 3: the languages whose
     `dictionary_entries` the full DB has today), by `language` column
     where the table has one and by the recorded ranges otherwise;
   - the `system` rows of `dictionary_entries` unchanged, including
     `build_time`;
   - `sqlite_sequence` as in extended.
3. Recompute `authors.has_translations` from the kept works with the
   module builds' SQL (section 6).
4. Create indexes from the canonical DDL, `VACUUM`, run
   `diff_against_canonical()`, then the quality report, compression and
   the existing copies (`full_database_pack/src/main/assets/` and the iOS
   on-demand folder), plus the new `full.manifest.json` sidecar. The
   existing `_stamp_build_time()` step, which overwrites the inherited
   `build_time` row with the current run's time, must not run for the
   filtered DB: the row is the release identity and has to stay the
   extended value.
5. Cut the delta parts (below) from the same extended DB, in the same run.

### The delta cutter (full mode, after the filter; new stage `emit_extended_delta()`)

1. Read the part registry from `shared/pack_layout.py`: unit definitions
   (First1K, PTA, each language), size target, the list of
   part modules, and `PLAY_ON_DEMAND_BUDGET_BYTES`.
2. Compute the delta as the complement of the full rule of step 2 above,
   against the same extended DB: works not in the full set, lexicon
   languages not in `FULL_LEXICON_LANGUAGES`.
3. Measure each unit: cut it with its indexes and zip it at level 6
   (fast; level 9, the shipped level, is smaller, so packing on these
   figures is conservative). A unit over the target is split by author on
   each author's share of the unit's text bytes. Pack the pieces first-fit
   decreasing into parts under the target.
4. For each part: create `<part>.db` with `create_schema()`, `ATTACH` the
   extended DB, `INSERT ... SELECT` the part's rows with ids, copy the
   `system` rows, create indexes, `VACUUM`, run `diff_against_canonical()`,
   zip with the entry named `<part>.db`, write the manifest inside the zip
   and the sidecar.
5. Hard failures:
   - per table, the id set of full plus the id sets of all parts must
     equal the id set of extended, with no overlap (`EXCEPT` both ways,
     and a count check that the sum of the pieces equals the whole);
   - no `works.id` in two parts; no lexicon language in two parts;
   - `build_time` identical in extended, full and every part;
   - any part zip over 1.5 GB; the sum of all on-demand packs over the
     budget; a part whose module is missing from `settings.gradle`, or a
     listed part module with no part to fill it (an asset-pack module
     with an empty `assets/` fails `bundleRelease`).
   The budget table is printed on every run, pass or fail.
6. Round trip on the build machine: merge every part into a copy of the
   filtered full DB using the same SQL the client runs (one shared `.sql`
   resource the Python and the Kotlin both read), then compare with the
   extended DB table by table with the same `EXCEPT` queries as section 3.
   Zero differences, including ids. Then run `text_integrity/audit.py
   --corpus all` on the result against the extended baseline: zero per-work
   regressions.
7. Copy each part zip and sidecar to `<part>_pack/src/main/assets/`. The
   whole extended zip continues to be copied where it is today.

Gradle: one `com.android.asset-pack` module per part and no others (each
a two-line `build.gradle` identical to `references_pack/build.gradle`
with its own `packName`), listed in `settings.gradle` and
`android.assetPacks`. `full_database_pack` stays. `checkDatabaseExists`
gains a check that every part module has its zip and manifest, or the
release build fails. `checkAabSize` in `app/build.gradle`, which today
fails any bundle over 4 GB (the old published figure) and prints per-pack
sizes, is changed to read its limit from the same
`PLAY_ON_DEMAND_BUDGET_BYTES` the Python uses, so the two cannot
disagree; the probe bundle was built with `-x checkAabSize` for exactly
this reason.

### What this does to build order and time

- The full DB can no longer be built on its own. BUILD.md's "Full
  release" section becomes "requires the extended assembly of the same
  release", and its module builds (`greek/run_build.sh full`,
  `latin/run_build.sh full`) drop out. The three-pass rhythm for extended
  is unchanged.
- A developer who wants the full DB needs every extended prerequisite,
  including the non-Greek/Latin language modules (Sanskrit's is about
  3 hours). Today full needs only Greek and Latin in full mode plus the
  four small modules. This is decided (section 13): there is one way to
  build the full DB, and it starts with the extended build.
- The filter's own run time is not measured. It copies about 5 GB of rows
  out of a 15 GB file, builds indexes and vacuums; expect it to be
  comparable to today's full assembly. The 15-minute figure in section 3
  is for `EXCEPT` comparisons, not copying, and is an upper bound on the
  round-trip check per table pair.
- Sample and iOS curated builds are untouched: same modules, same
  assembly, same ids, same markers.
- The iOS on-demand full zip is the filtered full DB, because it is a copy
  of the same artifact. Its content differs from today's only in the
  `build_time` value, the two `has_translations` flags and the id values,
  none of which any iOS query depends on. Keeping a second, separately
  assembled full DB for iOS only would defeat the purpose; not proposed.

## 10. UI

One "Database downloads" screen with three rows: Sample (installed by
default), Full, Extended. Each shows what it contains, its download size,
the disk it needs, and the measured install time. Each has one action:
Download, Downloading (percent), Installing (stage and percent),
Installed, Update available (a new data release, scenarios 8 and 10),
Remove. A row whose last attempt failed or was interrupted shows the
recorded reason under its action, and after a second failure for the
same release a line suggesting what to check (scenario 12a). The
Extended row's size and time are the sum of the full pack and every part
when the base is sample, and of the parts alone when the base is full;
the row says which.

The overflow item "Download Full Database" becomes "Database downloads"
and opens that screen. "Select database" keeps its name and its
whole-database behaviour (section 8). Route `REQUIRES_USER_CONFIRMATION`
and `WAITING_FOR_WIFI` through `showConfirmationDialog()` as
`FullDatabaseDownloadActivity` does; the 200 MB mobile-data consent applies
to every pack separately. A part that Play reports present but
`pack_state` says absent shows "Install".

Tapping "Download and Install" first shows a confirmation that says the
job takes 30 minutes or more on a typical phone plus the downloads,
longer on older phones, that the app must stay open and the phone
plugged in, and that an interruption or failure puts back the database
the user has now (decided 2026-09-27). Measured on a Pixel 6 the same
day: full pack extraction under a minute, part 1 about 13 minutes
(7 merging, 6 verifying), part 2 about 8 minutes.

The merge runs in a foreground service so the user can leave the screen.
The reader is unavailable while a merge or a rebuild runs, because Room
must be closed; the main screen shows the same "database is being
prepared" state `DatabaseExtractionActivity` shows today. After an
interrupted merge (scenario 12) the same screen shows "restoring the
sample database" for the seconds the reset takes, then the reader opens
on the sample; the only trace is one notice and the reason on the
Extended row. No screen ever asks the user to choose a database in
order to get past it. Scenario 9's "waiting for Google Play" state is
also shown on the row, not as a blocker.

## 11. Migration

- Existing full-pack users: the first launch of a build that ships this
  reads the full pack's new sidecar. If its `build_time` differs from what
  is on disk, which it will because the filtered full DB is a new
  release, the Full row shows "Update available" (scenario 10). Their DB
  keeps working until they tap it.
- Existing sample users: nothing changes.
- Whole external DB users: unchanged. A whole external DB never takes
  parts (scenario 18).
- iOS: the curated base DB is untouched. The on-demand full zip is the
  filtered full DB (section 9). Apple has deprecated On-Demand Resources
  as of iOS 27; `IOS_BACKGROUND_ASSETS_MIGRATION_PLAN.md` covers that move
  and is unaffected by this proposal.
- README and BUILD.md: the external download entry for extended is
  unchanged; BUILD.md's release targets table,
  "Full release" section and Step 7 driver change as in section 9, and
  every "too large for Android" note is replaced.
- `ASSET_PACK.md`: the on-demand table gains the parts with measured
  sizes.

## 12. Verification plan

Milestone 1, before any code is written, Kotlin or Python: **the
size-limit probe.** Play checks only compressed sizes at upload, so the
probe does not need the real parts, and it probes the budget the app
should be able to grow into, not today's total: **10 GB of on-demand
packs** (decided, section 13). Six throwaway asset-pack modules,
`db_probe_part1_pack` to `db_probe_part6_pack`, each hold a 1.2 GB file
of random bytes (`head -c 1200m /dev/urandom`, incompressible, so Play
cannot shrink it), wired exactly like `references_pack` with `on-demand`
delivery, listed in `settings.gradle` and `android.assetPacks`, with a
`versionCode` above the current release. `bundleRelease` then carries
the four existing packs (2.73 GB) plus 7.2 GB of probe, about 9.9 GB
on-demand. Upload it to the internal testing track and promote it
nowhere. Play Console computes
compressed download sizes at upload and rejects a bundle that breaks a
limit, naming the limit. Nobody outside the internal testers list sees
it. Afterwards delete the two modules, their two Gradle entries and the
chunks, and discard the internal release; nothing from the probe ships.
Outcomes:

- Accepted at about 10 GB: the account is not held to 4 GB, and 10 GB
  is the proven figure. `PLAY_ON_DEMAND_BUDGET_BYTES` is set to
  10,000,000,000, the probed number, not the published 30 GB, so the
  build fails if the packs ever grow past what was tested. The proposal
  proceeds; everything below follows.
- Rejected on the cumulative total: 4 GB is the real limit. **The
  proposal is cancelled** (section 4). Nothing below is done.
- Rejected on a per-pack size: lower the size target, rebuild and upload
  again; this outcome says nothing about the cumulative limit.

The probe costs one release bundle build and one upload of about 10 GB,
and it is the first step because everything else depends on it. The
plan's build-pipeline work (section 9) starts only after it passes.

**Result so far (2026-09-27).** The probe bundle was built as described:
version code 140, signed, 10.43 GB, six probe packs of 1.26 GB
compressed each, on-demand total 10.26 GB including the four existing
packs, base module 0.17 GB. Two build-machine facts came out of it: the
signing step needs more than the project's 2 GB Gradle heap for a bundle
this size, so `gradle.properties` now sets `-Xmx16g` permanently; and
`checkAabSize` had to be skipped (`-x checkAabSize`) because it fails
anything over 4 GB, which section 9 now fixes by tying it to the budget
constant. **Play Console accepted the upload to the internal testing track; App
bundle explorer for version 140 lists all six probe packs as on-demand
asset packs beside the four existing ones; and a production release
created with the same bundle and taken to the review screen showed no
errors** (all 2026-09-27, release discarded, nothing sent for review).
**The probe is passed.** `PLAY_ON_DEMAND_BUDGET_BYTES` is
10,000,000,000. The probe modules, their Gradle entries and the version
bump were removed the same day; the 16 GB Gradle heap stays.

What the probe did not test: the final production review itself, which
runs when a real release is sent for review. Play's size checks run at
upload and on the review screen, and both passed, so a size rejection at
review is not expected, but section 15 is the backout if it happens.

1. **Subset proof on every release.** The `EXCEPT` comparison of section 3
   between the filtered full DB and the extended DB, on every table and
   including ids, is part of the build (section 9, check 5 and round trip
   6). The one-off form used on 2026-09-27, for reference:
   `ATTACH` the extended DB to the full DB and run, for each of the
   twelve tables,
   `SELECT COUNT(*) FROM (SELECT <content columns> FROM main.t EXCEPT SELECT <content columns> FROM ext.t)`,
   and the reverse with `ext.t` restricted to full's books, lexicon
   languages and `lemma_map` sources. `translation_lookup` is compared
   through a join to the segment it points at, because its `segment_id`
   is an integer id. Expected: 0 everywhere except the
   `build_time` row before the filter lands, and 0 everywhere after.
2. `bundletool build-apks --local-testing` install on a device; run
   scenarios 2, 3, 4, 5 and 20 of section 8 in that order; after each,
   confirm `pack_state`, per-table counts against `manifest.rows`,
   `foreign_key_check`, `quick_check`, and that Room opens.
3. Shared authors: after scenario 4 confirm Plato (tlg0059) has every
   Perseus work and every First1K work and one author row; after
   scenario 5 confirm the Perseus works remain and the First1K works are
   gone. Confirm Agathemerus and Eusebius show `has_translations=1` after
   the merge and `0` after removal.
4. Release check: build two releases; install the full pack of one and
   try a part of the other; confirm the refusal message and that the DB
   is untouched.
5. Scenario 9: with Extended installed, install the updated bundle's base
   APKs before its asset pack APKs; confirm the "waiting" state, no merge,
   no deletion, and that the merge proceeds once the parts arrive. If
   bundletool's local testing cannot separate the two installs, this
   scenario is tested on the internal track with the pack fetch observed
   in logcat.
6. Scenario 12, from both bases: on a sample base and again on a full
   base, kill the app during a Greek part merge; relaunch; confirm the
   app never opens Room on the damaged file, puts the pre-job copy back
   within seconds with no question asked, that the restored database is
   byte-identical to the copy taken (compare the file to a copy made by
   hand before the test), that the preferences say sample or full as
   before, that the one notice and the reason on the Extended screen
   appear, and that bookmarks are intact. Repeat with a kill during the
   full-pack extraction of step A, and with "Leave" from the screen.
   Then choose Extended again and confirm the result's per-table id sets
   equal the extended DB's with no partially merged rows. Then corrupt
   `pack_state` deliberately and confirm the same.
6a. Scenario 12a, the loop guard: make a part fail verification every
   time (a deliberately truncated part zip in the debug fallback
   directory). Choose Extended twice; confirm each failure ends on the
   database the user had before, that the screen's message changes after
   the second, and that across ten launches nothing starts without a
   tap.
7. Measure merge time and peak disk per part on a mid-range phone and a
   flagship, and the full rebuild time of scenario 8 including the part
   re-downloads. Record in BUILD.md and in the UI strings. After each part
   merges, confirm `AssetPackManager` no longer reports it present and
   the space it took is free.
8. Install Extended, `adb pull` the runtime DB, run
   `text_integrity/audit.py --corpus all` against the extended DB. Zero
   per-work regressions. Compare ids too: the pulled DB's id sets must
   equal the extended DB's per table.
8a. Bookmarks: create bookmarks on the sample base in a Perseus Greek work
   and a Latin work, then run scenarios 2, 4, 8, 5 and 6 in turn. After
   each, every bookmark opens to the same line with the same text, and
   `user_data.db` is byte-identical to before.
9. "Select database" with a part zip is refused with the message, and
   with a whole database behaves exactly as today.
10. Scenario 15 and 16: clear storage and reinstall; sideload the release
    APK; confirm the rows and no crash.
11. Internal-track upload to Play Console of the release candidate. The
    only real test of Play's confirmation dialog for a pack over 200 MB.

## 13. Decisions

### Decided 2026-09-27

- **A 4 GB on-demand budget cancels the proposal.** If the probe upload is
  rejected on the cumulative total, nothing ships and nothing in the app
  changes (section 4). There is no partial variant.
- **The probe upload comes first, at 10 GB.** A release bundle with six
  throwaway 1.2 GB placeholder packs, bringing the on-demand total to
  about 10 GB, and one internal-track upload, before any code is written
  for this proposal (section 12, milestone 1). The build's budget
  constant becomes the probed 10 GB, not the published 30 GB.
  **Passed 2026-09-27**: accepted on the internal track, ten on-demand
  packs in App bundle explorer, production review screen clean.
- **Implementation proceeds** (decided 2026-09-27), in the order of
  section 16, with the backout of section 15 held ready in case the
  final production review of the real release fails.
- **The Gradle heap stays at 16 GB** (`gradle.properties`,
  `-Xmx16g`), whatever the probe's outcome. Signing a multi-GB bundle
  needs it.
- **Part size target: 1.2 GB.**
- **Parts are deleted from the device as soon as they are merged**
  (section 7, step 8). The full pack is handled exactly as today; this
  decision is about the extended parts only. Every rebuild therefore
  re-downloads the parts.
- **Full-only users get the new data on a new release.** When the
  sidecar's `build_time` differs from the one on disk, the Full row shows
  "Update available" and the user starts the re-extraction (scenario 10).
  The app never starts it on its own.
- **No externally imported database ever takes parts.** Parts merge only
  onto the full pack the app extracted itself. An imported whole DB,
  full or extended, opens on its own exactly as today (scenario 18) and
  the installer refuses a part on it whatever its `build_time`.
- **The full DB build always requires the extended DB build first.**
  There is one way to make the full DB: the filter over the assembled
  extended DB of the same release (section 9). The separate full-mode
  assembly is retired.
- **The Greek and Latin module `full` modes are deleted** once the filter
  replaces them; nothing reads their output.
- **Recovery from an interrupted merge is the rebuild only.** No in-place
  repair, no partial-delete logic (section 7).
- **A rebuild cannot loop.** User-started only, from the Extended
  screen; one attempt per step; every failure or interruption puts the
  pre-job copy back on its own, with no dialog, and the screen shows the
  reason (section 8, rebuild rules).
- **The data is not changed** (section 9). The filter and the cutter copy
  rows; they never add, remove, deduplicate or alter one.

- **If the probe fails, the build pipeline stays exactly as it is.** The
  filter and the delta cutter are not kept for their own sake; the full
  DB keeps being assembled from its own Greek and Latin full-mode module
  builds, and BUILD.md is unchanged. Nothing from this proposal lands
  under cancellation.

- **An outdated full base is replaced, with no choice** (decided
  2026-09-27). If the full database on the device is an older release
  than the full pack on Play, choosing Extended downloads and installs the
  new full first, then the parts. The parts merge only onto a full of the
  same release, so there is nothing to choose; the confirmation says so.
- **Extended is one tap from any base** (decided 2026-09-27). If the
  base is the sample, or Play holds a newer full pack than the device,
  the Extended screen downloads and extracts the full pack itself, then
  the parts, and restarts once at the end. The user never has to run the
  Full download first.
- **Any failure goes back to the database the user had before the job**
  (decided 2026-09-27), sample or full, whatever release, by a copy
  taken before the first change (section 7, recovery). This replaces the
  earlier "sample is the floor" rule; the sample is now only the
  fallback when no copy exists. A download failure between parts is a
  failure like any other: the copy goes back.

### Open

None. Every decision is recorded above.

## 14. Risks and caveats

- **Ids are the contract.** The whole design rests on full and every part
  being cut from one extended file. The release check in the installer
  and the partition check in the build are the two guards; both must be
  hard failures, and the installer's plain `INSERT` must never be softened
  to `OR IGNORE`, or a bypassed check would silently drop rows.
- **A new data release means a full rebuild for Extended users.** Every
  release re-extracts 5 GB, re-downloads about 2 GB of parts and
  re-merges about 10 GB (scenario 8). The re-download is the price of not
  keeping parts on the device (decided); the rebuild itself is the price
  of ids without bands. Mitigation is only in the UI: say what it costs,
  let the user pick the time, and route the downloads through the Wi-Fi
  and consent handling.
- **Play's update window.** The app can run with a patched full pack and
  an unpatched part, or the reverse. The release check turns that into a
  wait, never into a merge; scenario 9 must be tested with bundletool, not
  assumed.
- **Merge time on low-end phones.** Unknown until measured. Mitigation:
  the foreground service, per-table transactions, index drop and
  recreate, and the whole-file fallback in section 4 if the number is
  unacceptable.
- **Disk pressure.** Sample to Extended in one go needs the full zip
  (1.0 GB), the extracted full DB (4.8 GB), then one part zip at a time
  (up to 1.2 GB), one inflated part at a time (up to ~6.3 GB), and the
  growth of the runtime DB to ~14 GB; with the journal off there is no
  WAL. Peak, during the last part's merge, is roughly 22 GB above the
  sample install, plus the pre-job copy of the current database, up to
  4.8 GB for a full base. The screen requires 25 GB plus the size of the
  current database before it starts, and the installer checks again
  before each merge.
- **An interrupted merge leaves an unusable database, by design.** With
  no in-place repair, the way out is the automatic return of the pre-job
  copy (scenario 12). The launcher must check the job flag and
  `pack_state` before Room opens, every launch, or the user sees a Room
  validation crash instead of the restore. The copy itself is the one
  thing that must not be lost: it is written before any download starts
  and deleted only after the job's final verification.
- **The full build depends on the extended build.** A change that breaks
  the extended assembly now blocks the full release too. The build order
  in BUILD.md must say so, and the filter must fail loudly if the extended
  DB is stale relative to the module DBs.
- **`lemma_map` attribution depends on contiguous inserts.** If any
  insertion point ever interleaves languages, the ranges are wrong and the
  `source` cross-check is what catches it. Both the range recording and
  the cross-check must be in the build before the first filter runs.
- **The probe may say no.** The on-demand total with the delta is about
  4.7 GB today against a limit that is either 4 GB or 30 GB for this
  account, and the proposal is cancelled outright under 4 GB (section 4).
  The probe tests 10 GB so that growth in the extended corpus has room;
  a rejection at 10 GB that names a figure above 4.7 GB is possible in
  principle and would be a third outcome, judged on the figure Play
  names. The probe is first for that reason; nothing else is built until
  it passes.
- **A Play upload rejected on size after the probe passed** means a
  limit changed, or a part grew past 1.5 GB. The size target is the knob.
- **The size estimates are rough.** The delta is estimated from zip
  arithmetic; the measured table from the first build fixes the parts.
- **The delta carries the extended DB as it is.** That includes the
  duplicated Sanskrit lexicon rows section 3 describes, which is part of
  why the 2.0 GB figure is the one to plan with. The proposal does not
  touch the data; it copies it.
- **Schema drift between base and parts.** Impossible by construction:
  all come from `shared/database_schema.py`, all are drift-checked, and
  the client compares the schema hash before merging.
- **Room index validation after drop and recreate.** Mitigated by
  generating the recreate statements from the canonical DDL and by the
  desktop round trip.
- **`has_translations` is the one derived column.** Its recomputation in
  the filter must use the assembly's rule, not a new one, or the full DB
  will differ from today's for reasons unrelated to this proposal. The
  measured effect is two rows; a difference elsewhere is a bug.
- **Play's behaviour after a data clear is unverified** (scenario 15).
  The design does not depend on it, but the UI copy for "download again"
  does.
- **Debug builds cannot exercise Play delivery.** Every scenario that
  involves `AssetPackManager` needs bundletool or an internal-track
  install; a passing debug run says nothing about them.

## 15. Backout plan

If the final production review of the first real release with parts
fails, on size or on anything else attributable to the parts, the
release is backed out to the shape the app has today without waiting on
a second review cycle:

1. **A build flag gates every part.** `app/build.gradle` gets
   `buildConfigField "boolean", "EXTENDED_PARTS_ENABLED"`, and the part
   modules are added to `android.assetPacks` only when it is true. The
   installer, the Extended row and the launcher's new-release marking
   are all behind `BuildConfig.EXTENDED_PARTS_ENABLED`. Backout is
   setting it false and rebuilding: the bundle then carries exactly the
   four packs it carries today, and the UI is today's UI. The Kotlin
   stays in the tree, unused, until the cause is understood.
2. **The full pack keeps working either way.** The filtered full DB is a
   whole-file pack with identical content to today's full DB (section 3),
   so the full flow, the whole external DB import and iOS are unaffected
   by the flag. Nothing about the filter has to be undone for the backout
   to be complete; whether to keep the filter after a backout is the same
   question as under cancellation, already decided: the pipeline goes
   back to today's full assembly, in a separate change, once the backout
   has shipped.
3. **Users who already merged parts** (internal or open testers) keep a
   valid database: the merged file is a normal `perseus_texts.db` with
   every index present. With the flag off the launcher never offers a
   rebuild, the Extended row reads "Not available in this version", and
   their data stays until they choose Full or Sample. No deletion is
   triggered by the backout.
4. **The budget constant and `checkAabSize`** stay tied together; a
   backout does not change them.
5. **What is not backed out:** the 16 GB Gradle heap, the `checkAabSize`
   change, and the plan itself.

## 16. Implementation sequence

Each stage ends in something verifiable on its own and is not started
until the previous one has passed its check. Long builds are run only on
an explicit go.

1. **Text-integrity snapshot** of the current extended and full DBs
   (`data-prep/text_integrity/audit.py --corpus all`), per section 9's
   prerequisite, if the 2026-09-14 reports are not to be used as the
   baseline.
2. **Registry and ranges.** `shared/pack_layout.py` (full language set,
   full lexicon language set, part units, size target, budget, source to
   language map); range recording at the three lexicon insertion points
   and the `source` cross-check; the `max(id) < 2^31` assertion. Check:
   an extended assembly writes `lexicon_ranges.json` and passes both
   assertions.
3. **The filter.** `assemble_database.py full` as section 9 describes,
   with `has_translations` recomputed by the shared SQL. Check: the
   section 3 `EXCEPT` comparison, both directions, all twelve tables,
   against the extended DB and against the current full DB, is zero
   everywhere except `build_time`; `diff_against_canonical()` passes;
   the text-integrity audit shows zero per-work regressions.
4. **The delta cutter** and its hard failures, the desktop round trip,
   the sidecar manifests, the copies into the part modules. Check: the
   partition check passes and the round-trip DB equals extended
   including ids.
5. **Gradle.** The part modules, `checkDatabaseExists`, `checkAabSize`
   tied to the budget, the `EXTENDED_PARTS_ENABLED` flag. Check:
   `bundleRelease` carries every part and the budget table matches the
   bundle.
6. **Kotlin.** `PreferencesManager` state, the installer, the launcher's
   `merging` check before Room opens and the automatic return to
   sample, the "Update available" marking, the downloads screen. Check:
   section 12 items 2 to 10 on a device through bundletool.
7. **BUILD.md, README, ASSET_PACK.md** as section 11 lists.
8. **Internal-track release** of the real bundle, then the production
   release sent for review, with section 15 ready.

### Progress

- **Stages 1 to 3 done 2026-09-27.** All four databases were backed up
  (byte-compared) to `data-prep/snapshots/pre_delta_20260927/` and fresh
  `--corpus all` audits taken of each. `shared/pack_layout.py` and the
  assembly changes landed. Results of the builds that followed, each
  against its backup:
  - extended (28.8 min): identical row for row **including ids** in all
    twelve tables; only the `build_time` stamp differs. 30 lexicon ranges
    recorded, the source registry agreed with every row, every max id
    unchanged (largest 49,207,601).
  - full by filter (4.9 min, against 15 min for the old module builds
    plus assembly): identical by content in all twelve tables, lookup
    compared through segment text; 138 authors, 1,021 works, 3,407
    books, 1,254,587 segments. The first run dropped the 934 orphan
    segments (section 9) and was rejected by the comparison; the second
    run, with the widened scope, matched. `PRAGMA integrity_check` ok.
    The file is 4.81 GB and its zip 0.97 GB, down from 4.97 and 1.09,
    because the filtered file is written compact.
  - sample (4.3 min) and iOS curated (2.6 min): identical row for row
    including ids; the sample and iOS zips came out the same size as the
    previous release's, to the byte.
  - Post-build text-integrity audits of all four: zero per-work change
    against the pre-build snapshot. The baseline symlinks now point at
    the post-build extended report.
  - Every shipped zip (`app/src/{main,debug}/assets`, the full pack, the
    three iOS copies) passed `unzip -t`.
- **Stage 4 done 2026-09-27.** The delta cutter is in
  `assemble_database.py full` after the filter, with `shared/delta_merge.sql`
  as the one copy of the merge statements (checked against the canonical
  schema on every build). Measured, from the compacted extended DB:

  | Unit | zip (level 6, with indexes) |
  |---|---|
  | First1K Greek (1,091 works) | 1.06 GB |
  | Sanskrit (272 works, lexicon) | 0.60 GB |
  | PTA Greek (193 works) | 0.10 GB |
  | Pali | 0.04 GB |
  | Coptic, Hebrew, Norse | 0.02 GB each |
  | Syriac, Chinese, Persian, Arabic | 0.01 GB or less each |

  Packed at the 1.2 GB target into **two parts**:
  `db_extended_part1_pack` (First1K, PTA, Hebrew, Syriac, Chinese, Arabic;
  6.31 GB db, **1.14 GB zip**) and `db_extended_part2_pack` (Sanskrit,
  Pali, Coptic, Norse, Persian; 3.29 GB db, **0.64 GB zip**). The delta is
  1.78 GB and the on-demand total 4.40 GB of the 10 GB budget. The
  desktop round trip, full plus both parts merged with the shared SQL,
  equals the extended DB row for row in all twelve tables, ids included,
  with the same foreign-key state (the 2,762 orphan segments). Two
  earlier attempts were rejected by the build's own checks: unit sizes
  measured without indexes under-estimated a part by a third (index
  pages compress worse than text; fixed by measuring with indexes), and
  the round trip demanded a clean `foreign_key_check` that the extended
  DB itself cannot pass (fixed by requiring the same violations as
  extended). Cutter time about 18 minutes on top of the filter.
- **Stage 5 done 2026-09-27.** Two asset-pack modules,
  `db_extended_part1_pack` and `db_extended_part2_pack`, gated with the
  full pack and the app code by one `extendedPartsEnabled` line in
  `app/build.gradle` (section 15). `checkDatabaseExists` requires every
  enabled part module to hold the zip and manifest the cutter wrote and
  the manifests to agree with the module count; `checkAabSize` reads the
  per-pack cap and the on-demand budget from `shared/pack_layout.py`.
  `bundleRelease` built a 4.42 GB bundle carrying all six packs, base
  module 134.7 MB, on-demand total 4.27 GB of 10 GB. A build-time copy of
  `shared/delta_merge.sql` into `app/src/main/assets/` gives the app the
  same merge statements the round trip ran.
- **Stage 6 code written 2026-09-27** (device testing, section 12, still
  to do; scenario 10's "Update available" on the Full screen for
  full-only users is not written yet): `ExtendedPartsManager` (Play facade, sidecars, state in
  `PreferencesManager`), `ExtendedDeltaInstaller` (section 7: release
  check on the base's own `build_time` row, schema hash computed the way
  the build computes it, zip checksum, inflate under `filesDir`, journal
  off for the merge, index drop and recreate from `sqlite_master`, the
  twelve shared statements, count and foreign-key and `quick_check`
  verification, then `removePack`), `ExtendedDatabaseDownloadActivity`
  (one job from any base: copy aside, full pack if needed, parts in
  order: download, merge, delete), the launcher's job and `merging` check
  before Room opens with the automatic restore of the copy, the "Update
  available" state from the full pack's sidecar, and the menu item. Two departures from the text above, both deliberate and both
  smaller than what they replace:
  - a separate "Download Extended Database" screen and menu item, the
    app's existing pattern for the full, audio, references and topical
    packs, instead of one "Database downloads" hub;
  - the merge runs in a process-level job (`ExtendedInstallJob`, a
    singleton coroutine) that the download screen attaches to, with the
    screen kept on while it shows, not yet in a foreground service; an
    interruption is safe by design (scenario 12) and the service is a
    follow-up. It was first written inside the screen's own lifecycle,
    and the device showed why that was wrong (2026-09-28): under
    predictive back the deprecated `onBackPressed` override is not
    called, so back closed the screen without the Leave dialog, the main
    screen opened over a database mid-merge, and the merge coroutine was
    cancelled with the screen. Now back goes through the dispatcher, the
    job survives the screen, and the main screen refuses to open the
    database while a job runs and sends the user back to the job's
    screen instead. The restore itself runs non-cancellable: on the
    first Leave test (2026-09-28) the job was already cancelled when it
    tried to restore, the dispatcher switch threw at once, and only the
    launch-time recovery after the restart put the sample back, which it
    did, identically, so the outcome was right for the wrong reason;
  - (withdrawn the same day: Extended is now one job from any base, and
    any failure restores the pre-job copy; see section 13.)
- **Device testing began 2026-09-27** on a Pixel 6 (Android 17, 60 GB
  free), debug build with the full pack and both parts pushed to the
  debug fallback directory. Results, in order:
  - Sample-base interruption (scenario 12): job started from the sample,
    app force-stopped while the full pack was being extracted over it;
    next launch restored the sample without asking. The restored file was
    pulled and compared to the shipped sample: identical in all twelve
    tables, ids included. (An earlier raw checksum differed only because
    the copy was taken after Room's WAL had been checkpointed into the
    file; the copy step now checkpoints first.)
  - Three defects found by the device and fixed the same day, each
    exercising the restore path correctly on failure: the installer read
    the zip hash from the in-zip manifest, where it cannot exist (now
    from the sidecar); the index drop-and-recreate crashed the process
    natively in SQLite's allocator, since Android's SQLite sorts in
    memory (indexes now stay in place; a hard heap limit added as a
    backstop); and the schema hash changed after the first read-write
    open because Android adds `android_metadata` (now excluded). Times
    measured: full pack extraction under a minute; part 1 about 7 min
    merging and 6 min verifying; part 2 about 8 min; whole job about
    28 min plus downloads.
  - The full job from the sample completed: both parts installed,
    target extended, backup deleted, restart clean, no schema error,
    languages list showing Sanskrit, Persian, Hebrew, Arabic, Coptic;
    Sanskrit and First1K Greek author lists read through Room. The
    merged file is 15.19 GB against the extended DB's 14.41 GB, the
    difference being index pages laid out by incremental inserts rather
    than compacted. The merged file was pulled and compared to the
    extended DB: **identical in all twelve tables, ids included**,
    49,207,601 word rows, `has_translations` and `build_time` equal.
    That is section 12, item 8.
  - Full-base interruption (scenario 12 from full, with the newest build
    including the confirmation, the sidecar hash, indexes in place and
    the heap limit): reset to sample, full pack installed through the
    Full screen (4,814,467,072 bytes), Extended started, confirmation
    accepted, app force-stopped at 6.6 GB during part 1's merge. Next
    launch restored the full database without asking, the app came back
    to the main screen, preferences returned to full with the failure
    recorded, and the restored file, pulled and compared to the shipped
    full DB, was identical in all twelve tables, ids included.
  - Retest of the final code, 2026-09-28: the whole job from the full
    base (23 min, merged database identical to the extended DB), then
    launch-time recovery from a deliberately abandoned job, then the
    whole job from the sample (23 min, identical again), then Leave
    pressed at 7.4 GB into part 1's merge: the stop dialog, the job's own
    restore of the sample (identical), the restart to the main screen.
    The Leave test found and fixed two defects on the way: back bypassing
    the deprecated override under predictive back, and the restore
    throwing inside an already-cancelled coroutine.
  - Not yet run on a device: item 8a (bookmarks across the flows), the
    second-failure hint, and scenario 15 (clear storage). Everything that
    touches the database has been, on the final code.
- **VACUUM added and all four rebuilt again the same day**, in one
  verified chain (each compared to the 2026-09-14 backup before the next
  build): all four identical again, audits unchanged per work. Zips
  after compaction: extended 2.75 GB (was 3.13), full 0.97 GB (was 1.09),
  sample 143 MB (was 163), iOS curated 79 MB (was 88). Whole-chain time
  57 minutes.

## Sources

- Play Console Help, "Optimize your app's size and stay within Google Play
  app size limits": https://support.google.com/googleplay/android-developer/answer/9859372
  (fetched 2026-09-20)
- Play Asset Delivery overview: https://developer.android.com/guide/playcore/asset-delivery
  (page dated 2025-09-18)
- Play Asset Delivery, Kotlin/Java integration: https://developer.android.com/guide/playcore/asset-delivery/integrate-java
  (page dated 2026-09-16)
- Play Asset Delivery guide: https://developer.android.com/guide/app-bundle/asset-delivery
- Android Developers Blog, 2025-10-24, "5 things you need to know about
  publishing and distributing your app for Android XR" (the "instead of a
  cumulative total of 4 GB" statement):
  https://android-developers.googleblog.com/2025/10/5-things-you-need-to-know-about.html
- Android App Bundle FAQ, size limits entry (page dated 2026-07-28):
  https://developer.android.com/guide/app-bundle/faq
- asset-delivery maven metadata: https://dl.google.com/dl/android/maven2/com/google/android/play/asset-delivery/maven-metadata.xml
