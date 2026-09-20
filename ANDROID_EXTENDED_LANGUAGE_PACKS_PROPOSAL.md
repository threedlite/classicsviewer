# Proposal: ship the extended database on Android as supplement asset packs

Status: proposal, not started. Written 2026-09-20 against 0.8.138.

## 1. Summary

Ship the extended corpus on Android as two on-demand Play Asset Delivery
supplement packs beside the existing full pack, and merge the supplements
the user chooses into the single on-device `perseus_texts.db` at runtime.
The Greek supplement holds First1KGreek and PTA; the languages supplement
holds Sanskrit and the eight other languages the full DB lacks. Each is the
exact complement of the full DB, so a merge only adds rows. This gives
Android the same extended coverage iOS gets from the `database_extended`
on-demand resource, without exceeding Google's per-pack limit and without a
15 GB whole-file swap. A per-language layout was considered and is kept as
an alternative in section 4.

The design has four parts:

1. **Play limits, verified today, planned conservatively.** 1.5 GB per
   asset pack and 100 packs per bundle apply to everyone. The cumulative
   on-demand limit is printed as 30 GB but was 4 GB for ordinary developers
   as recently as October 2025, and Google has not said the higher figure
   now applies to everyone. This proposal **plans against 4 GB** and treats
   anything above it as unconfirmed until an internal-track upload shows it
   (section 2). A single 3.1 GB extended pack is not allowed either way.
   Two supplements are, but under 4 GB only the Greek one fits beside the
   full, audio, references and topical packs. **No content is dropped.**
   The languages supplement is then distributed through the existing
   external download and imported through the external-DB import path,
   which merges it with the same installer the Play packs use (sections 4,
   7 and 8).
2. **Packs are canonical-schema SQLite slices.** Each pack holds a zipped
   SQLite file with the exact 12-table schema the app already validates, plus
   a small manifest. No new Room entities, no schema version bump (section 5).
3. **Integer ids live in fixed bands.** Every AUTOINCREMENT id in a pack is
   offset into a band reserved for that pack, and lexicon rows are offset
   into a band reserved for their language. This is what makes the client
   merge a plain `INSERT ... SELECT`, makes removal a range delete, and makes
   a crashed merge recoverable (section 6).
4. **The client merge is `ATTACH` plus `INSERT ... SELECT`.** Rows for any
   work the pack carries are deleted first, so a re-install or a pack from
   a different build always replaces, never duplicates. With complement
   packs that step deletes nothing in normal use. Replacement is by work,
   not by author, because 27 Greek authors have works in both Perseus and
   First1KGreek. The runtime DB is rebuilt from base plus installed packs
   whenever the app version changes (sections 7 and 8).

Everything is produced by `assemble_database.py extended` in one run. There
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
and the packs on the external channel in section 4 move to the `play`
channel. Nothing else in the design changes.

**Earlier published figures.** Older documentation and most
third-party write-ups quote 512 MB per on-demand or fast-follow pack, 1 GB
for install-time, and 2 GB for all packs combined. Those figures are gone
from the live page. Documents in this repo that should be corrected when
this proposal is adopted:

- `ASSET_PACK.md` uses a 4 GB on-demand pool, which matches this
  proposal's planning figure, but its pack list predates `references_pack`
  and `topical_pack`, so its "remaining" number is wrong.
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

Lexicon rows: `lemma_map` has 12.8 M rows and **no language column**. By
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
Greek supplement. Sanskrit's text tables match the extended DB row for
row.

Two facts that shape the design:

- The **Greek lexicon is identical in sample, full, and extended** (same
  sources, same counts: LSJ 30,639, Wiktionary 22,774, Cunliffe 9,396; the
  same lemma_map sources and counts). The Greek supplement therefore
  carries text tables only.
- The **sample DB has no Latin lexicon at all.** Its `dictionary_entries`
  are greek plus the system row, and its `lemma_map` has no Whitaker or
  Lewis & Short rows. `latin/latin_texts_sample.db` has an empty
  `dictionary_entries`. The full DB has the Latin lexicon (182 K entries).
  Neither supplement carries it, so a user on the sample base has no Latin
  lexicon with or without supplements, exactly as today.

## 4. Pack layout

### Recommended: the existing full pack plus two supplement packs

Three database packs. The full pack is unchanged and keeps its whole-file
replacement behaviour. The two supplements are cut as the **exact
complement of the full DB**: every work and every lexicon language in the
extended DB that is not in the full DB goes into exactly one supplement.
No work appears in two packs, so in normal use a supplement only adds
rows. Estimated sizes use each slice's share of the `dbstat` table bytes
in section 3 and the measured 0.209 zip ratio; the build measures the real
sizes and fails if any pack exceeds the cap (section 9).

| Pack (Gradle module) | Content | Rows (text_lines / segments / words) | Uncompressed | Zip |
|---|---|---|---|---|
| `full_database_pack` (existing) | Perseus Greek (91 authors, 772 works), all Latin, Sumerian, Akkadian, Italian, Old English, with the Greek and Latin lexicons | 1.01 M / 1.25 M / 14.7 M | 4.97 GB (measured) | 1.09 GB (measured) |
| `db_supplement_greek_pack` | First1KGreek (1,091 works) and PTA (193 works); text tables only, since the Greek lexicon is already in the base | 1.68 M / 1.69 M / 24.9 M | ~5.7 GB (est.) | ~1.2 GB (est.) |
| `db_supplement_languages_pack` | Sanskrit, Pali, Coptic, Hebrew, Syriac, Norse, Chinese, Persian, Arabic, each with its lexicon | 479 K / 379 K / 9.5 M | ~2.85 GB | ~0.6 GB |

The languages supplement figure is Sanskrit measured from its module
files (2.39 GB, 500 MB zip, single lexicon copy) plus the eight small
modules' files in the tree (about 0.45 GB, about 0.1 GB zipped). It
assumes the Sanskrit double import in section 3 is fixed before the
supplement is cut (section 9); cut from today's extended DB the pack
would carry the second copy and be larger, by an amount not measured.

The Greek supplement is the pack near the per-pack cap: about 80 percent
of 1.5 GB on the estimate, and First1KGreek grows. If its measured zip is
over the auto-split target (below), PTA moves to the languages supplement,
which takes it to about 0.7 GB. The build makes that choice from the
measured sizes, not from this table.

The base is either the sample DB from the APK or the full pack, exactly as
today. A supplement merges on top of either. A user on the sample base who
installs the Greek supplement gets First1K and PTA without Perseus Greek;
that is allowed, and the UI says so.

### The 4 GB on-demand budget

Everything delivered on-demand counts against one cumulative figure. Sizes
from the tree today:

| On-demand pack | Bytes in tree | GB |
|---|---|---|
| audio_pack (full Iliad recitation) | 1,022,816,561 | 1.02 |
| topical_pack (greek + latin) | 522,664,811 | 0.52 |
| references_pack (three PDFs + manifest) | 101,865,562 | 0.10 |
| full_database_pack | 1,085,755,158 | 1.09 |
| **Current total** | | **2.73** |

Adding both supplements (~1.8 GB) gives about 4.5 GB. That is fine under
30 GB and about 0.5 GB over a 4 GB cap. With the Greek supplement alone
the total is about 3.9 GB, which fits with roughly 0.1 GB of margin, inside
the estimate error.

**Every pack is built on every extended build. The budget only decides the
delivery channel.** `shared/pack_layout.py` holds
`PLAY_ON_DEMAND_BUDGET_BYTES` (initially 4,000,000,000) and a `channel`
field per pack, `play` or `external`. `assemble_database.py extended` sums
the real zip sizes of every Play-channel on-demand pack, database and
non-database alike, prints the table, and **fails if the Play set exceeds
the budget**. No pack is dropped automatically and no pack is left unbuilt.

Under 4 GB:

| Pack | Est. GB | Running total incl. 1.64 GB non-database | Channel |
|---|---|---|---|
| full_database_pack | 1.09 | 2.73 | play |
| db_supplement_greek | 1.2 | 3.93 | play |
| db_supplement_languages | ~0.6 | ~4.5 | external |

The languages supplement goes out on the external channel: the same zip
file, published on the external download the README already points to
for the extended DB, imported through the file picker and merged by the
same installer (sections 7 and 8). The whole extended DB zip stays on the
external download as well, for users who prefer one file. If the probe
upload (section 12, milestone 1) shows 30 GB applies, the languages
supplement's channel changes to `play` and nothing else changes. Under
either outcome every language is available on Android.

**Headroom rule.** The build must not assume the Greek supplement fits.
It computes the slice, and if its zip would exceed a configured target
(proposed: 1.2 GB, leaving 20 percent under the 1.5 GB cap), it first
moves PTA to the languages supplement, and if First1K alone is still over
the target it splits First1K by author into parts, largest authors first,
emitting `db_supplement_greek_1_pack`, `db_supplement_greek_2_pack`, and
so on. The manifest records the part. The UI groups parts under one row.
Gradle modules for parts must exist ahead of time; the build fails if a
slice needs a module that is not in `settings.gradle`, so adding a part is
a visible, reviewed change.

**Complement rule, enforced by the build.** For each of `works`,
`text_lines`, `translation_segments`, `words`, `translation_lookup`,
`milestone_line_ranges`, `dictionary_entries` and `lemma_map`, the row
count of the full DB plus the row counts of all supplements must equal the
row count of the extended DB, and no `works.id` may appear in more than
one pack. Either failing aborts the build. This is what lets the client
merge be additive in the normal case.

### Alternative considered: one pack per language

Seventeen packs, one per language with Greek split into Perseus, First1K
and PTA, about 3.0 GB compressed in total. Measured rows and estimated
sizes:

| Pack | Rows (text_lines / segments / words) | Est. zip |
|---|---|---|
| greek_first1k | 1.53 M / 1.54 M / 22.8 M | ~1.1 GB |
| greek_perseus | 632 K / 771 K / 9.8 M | ~0.5 GB |
| greek_pta | 146 K / 146 K / 2.1 M | ~0.1 GB |
| latin (with lexicon) | 360 K / 467 K / 4.8 M | ~0.45 GB |
| sanskrit (with lexicon) | 210 K / 221 K / 6.9 M | 0.5 GB (measured module zip) |
| twelve small languages, each with its lexicon | see section 3 | ~0.12 GB together |

Under 4 GB this layout puts the same content on Play (everything except
Sanskrit) with the same 0.1 GB margin. It gives users a per-language
choice and smaller downloads, and it retires the whole-file full pack. It
costs seventeen Gradle modules, a language-list UI, and a replacement-by-
work step in every merge, because 27 Greek authors have works in both
Perseus and First1K and a pack of Perseus works and a pack of First1K
works both carry those authors. Not chosen for the first release because
of that surface area. The pack format, manifest, id bands and installer
are the same, so moving to it later is a change of the registry and the
Gradle modules, not of the app's merge code.

## 5. Pack contents

A pack is one zip file, the same file on both channels:

```
<pack>.db.zip
    <pack>.db          a canonical-schema SQLite file
    manifest.json      the pack manifest (below)
```

The manifest lives inside the zip so an externally downloaded pack is a
single file the user picks in the system file picker. A Play-channel pack's
`src/main/assets/` also holds a sidecar copy, `<pack>.manifest.json`, so the
UI can show size and contents before the pack is downloaded. The client
trusts only the copy inside the zip.

`<pack>.db` is created with `shared/database_schema.py`'s `create_schema()`
and passes `diff_against_canonical()`. It has all 12 tables and 21 indexes.
Tables the pack does not use are empty. The file is `VACUUM`ed before
zipping. The Greek supplement contains rows in `authors`, `works`, `books`,
`text_lines`, `words`, `translation_segments`, `translation_lookup`,
`milestone_line_ranges`. A pack with a lexicon also has `dictionary_entries`,
`lemma_map`, and that language's `normalization_patterns` and
`prefix_assimilation_rules`.

The manifest:

```json
{
  "layout_version": 1,
  "pack_id": "db_supplement_greek",
  "pack_band": 1,
  "languages": ["greek"],
  "lexicon_languages": [],
  "corpora": ["first1k", "pta"],
  "part": 1,
  "parts": 1,
  "schema_sha256": "<sha256 of canonical sqlite_master DDL>",
  "build_time": "<the assembly build_time stamp>",
  "db_bytes": 5700000000,
  "zip_bytes": 1200000000,
  "zip_sha256": "<sha256 of <pack>.db.zip>",
  "rows": {"authors": 328, "works": 1284, "books": 166127, "text_lines": 1679527,
           "words": 24938667, "translation_segments": 1689195,
           "translation_lookup": 1721297, "milestone_line_ranges": "<count>",
           "dictionary_entries": 0, "lemma_map": 0,
           "normalization_patterns": 0, "prefix_assimilation_rules": 0}
}
```

The row figures shown are the measured First1K plus PTA totals from
section 3; the build writes the real values. `rows.authors` counts the
author rows the pack carries, including the 27 authors it shares with the
full DB; `authors` is merged with `INSERT OR REPLACE` and the row content is
identical wherever it appears, since every pack and the full DB are cut
from the same assembly.

The client checks `layout_version` and `schema_sha256` against constants
compiled into the app before merging. A mismatch is a hard error with a
"update the app" message, never a partial merge. `rows` is used to verify
the merge (section 7) and to show sizes before download.

## 6. Id bands

Seven tables use `INTEGER PRIMARY KEY AUTOINCREMENT`: `text_lines`,
`translation_segments`, `words`, `dictionary_entries`, `lemma_map`,
`normalization_patterns`, `prefix_assimilation_rules`. The base (sample or full) and
every pack are separate assemblies, each numbering from 1. Merged naively
their ids collide, and `lemma_map` rows cannot be attributed to a language
after the fact because the table has no language column and the schema is
frozen (CLAUDE.md: never change tracked table schemas).

Bands solve both problems with arithmetic only:

```
BAND_WIDTH        = 1_000_000_000            (1e9; max id in extended is 49 M)
band 0            = the base DB, sample or full (ids untouched; full max is 14.7 M)
pack band p ≥ 1   = text-table ids of pack p, offset p * BAND_WIDTH
language band L   = lexicon-table ids of language L, offset (100 + L) * BAND_WIDTH
```

Rules:

- **Text tables** (`text_lines`, `translation_segments`, `words`): a pack's
  rows are written as `id + pack_band * BAND_WIDTH` when the slice is cut.
  `translation_lookup.segment_id` is shifted by the same amount, so no
  mapping table is needed.
- **Lexicon tables** (`dictionary_entries`, `lemma_map`,
  `normalization_patterns`, `prefix_assimilation_rules`): rows are placed in
  the language band of the language they belong to, in **every** assembly
  mode, including the sample DB in the APK. The assembly knows the language
  of every lexicon row at the moment it inserts it (module merge order, OGA
  pass, lexicon import), so it assigns ids in the band directly instead of
  letting AUTOINCREMENT pick. `merge_database.py` and `monolith_fn.py`'s OGA
  and lexicon import paths are the three places that insert lexicon rows.
- A registry in `shared/pack_layout.py` fixes the language numbers and the
  pack band numbers. Numbers are never reused. The same file holds
  `LAYOUT_VERSION`.
- The assembly asserts, after every mode, that `max(id) < BAND_WIDTH` for
  the base text tables and that every lexicon row sits inside its language
  band. Both are hard failures. Measured maximum ids in the current extended
  DB: words 49,207,601; lemma_map 15,194,760; translation_segments
  3,324,121; text_lines 3,169,237; dictionary_entries 768,625.
- **Three Kotlin entity fields must change from `Int` to `Long` first.**
  `LemmaMapEntity.id`, `DictionaryEntity.id` and
  `TranslationLookupEntity.segment_id` are declared `Int`;
  `TextLineEntity`, `WordEntity` and `TranslationSegmentEntity` ids are
  already `Long`. Banded ids exceed 2^31, so the three `Int` fields would
  be truncated on read. Room maps both `Int` and `Long` to SQLite
  `INTEGER`, so the column affinity, and with it Room's schema identity
  hash, should not change. That must be confirmed, not assumed: the hash is
  the string literal in the generated `PerseusDatabase_Impl.java`
  (`app/build/generated/ksp/release/.../PerseusDatabase_Impl.java:330`),
  and it must be byte-identical before and after the type change, or the
  change is not allowed under CLAUDE.md's no-schema-change rule. No
  non-entity class in `app/src/main/java` declares an `Int` id for these
  tables, so the change does not spread.

What bands buy at runtime:

- Insert is `INSERT INTO main.t SELECT * FROM pack.t`, no remapping.
- Removing a pack is `DELETE FROM t WHERE id BETWEEN lo AND hi` per text
  table, plus the pack's works and books by text key, plus any author left
  with no works.
- Replacing a language's lexicon is a range delete on each lexicon table.
- A merge that dies half way is recoverable: delete the pack's band and try
  again. Nothing outside the band was touched.

Cost on the build side: lexicon rows are inserted with explicit ids, which
is the same insert cost as today. Nothing in the app inserts into these
tables, so `sqlite_sequence` being at a high value is harmless. The text
tables in the assembled extended DB are not renumbered; the offset is
applied when a slice is written. The iOS whole-file zips are unaffected
except that their lexicon ids move into bands, which no query depends on.

This changes ids in the sample DB that ships in the APK. Room does not care
about id values. `DatabaseValidator.kt` compares schema, not ids. Before this
refactor lands, run `data-prep/text_integrity/audit.py` on the current
extended DB as a baseline, per CLAUDE.md, and diff after.

## 7. Client merge

A new `LanguagePackInstaller` (raw `android.database.sqlite`, not Room) runs
in a foreground service with a progress notification, one pack at a time.
Steps for pack P:

The installer takes a pack source, which is one of two things:

- a Play pack: `AssetPackManager.getPackLocation(pack).assetsPath()` plus the
  zip name;
- an external pack: a content URI from the system file picker (the same
  Storage Access Framework picker the whole-DB external import uses today).
  The installer first copies the zip into `filesDir/packs/<pack>.db.zip` so
  a later rebuild (section 8) does not depend on the user's Downloads
  folder still holding the file.

From step 3 on, the two sources are handled by the same code.

1. Preconditions: for a Play pack, state `COMPLETED` from `AssetPackManager`;
   for an external pack, the zip opens and contains `manifest.json` and one
   `.db` entry. Manifest `layout_version` and `schema_sha256` match the app.
   Free space at least `db_bytes` plus 10 percent of the current runtime DB
   size plus 500 MB, plus `zip_bytes` for an external pack's retained copy
   (`StatFs` on `filesDir`, the idiom every download screen already uses).
2. `PerseusDatabase.destroyInstance()`. No Room connection may be open.
3. Inflate `<pack>.db` from the zip into `cacheDir/packs/<pack>.db`. Verify
   `zip_sha256` while streaming.
4. Open `perseus_texts.db` with `SQLiteDatabase.openDatabase(..., OPEN_READWRITE)`,
   then:

```sql
PRAGMA foreign_keys = OFF;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
ATTACH DATABASE '<cacheDir>/packs/<pack>.db' AS pack;
BEGIN IMMEDIATE;
INSERT OR REPLACE INTO pack_state
    (pack_id, state, band, channel, layout_version, app_version_code,
     zip_sha256, build_time, started_at)
    VALUES (:pack, 'merging', :band, :channel, :layout, :app_version,
            :sha, :build_time, :now);
COMMIT;
```

5. Remove anything this pack supersedes, in one transaction. With
   complement packs this finds nothing on a first install; it matters for a
   re-install, for recovery after a crash, and for a pack built later than
   the base. Replacement is **by work**, never by author: 27 Greek authors
   have works in both the full DB and the Greek supplement, and deleting by
   author would remove the full DB's Perseus works when the supplement
   installs.

```sql
BEGIN IMMEDIATE;
-- (a) rows of any work the pack carries, wherever they came from
DELETE FROM translation_lookup WHERE book_id IN
   (SELECT id FROM books WHERE work_id IN (SELECT id FROM pack.works));
DELETE FROM translation_segments  WHERE book_id IN (...same subquery...);
DELETE FROM words                 WHERE book_id IN (...);
DELETE FROM text_lines            WHERE book_id IN (...);
DELETE FROM milestone_line_ranges WHERE work_id IN (SELECT id FROM pack.works);
DELETE FROM books   WHERE work_id IN (SELECT id FROM pack.works);
DELETE FROM works   WHERE id IN (SELECT id FROM pack.works);
-- authors are not deleted here; they are upserted in step 6
-- (b) leftovers from an earlier or interrupted install of this pack
DELETE FROM text_lines           WHERE id BETWEEN :lo AND :hi;
DELETE FROM translation_segments WHERE id BETWEEN :lo AND :hi;
DELETE FROM words                WHERE id BETWEEN :lo AND :hi;
DELETE FROM translation_lookup   WHERE segment_id BETWEEN :lo AND :hi;
-- (c) lexicon of each language in manifest.lexicon_languages
DELETE FROM dictionary_entries        WHERE id BETWEEN :llo AND :lhi;
DELETE FROM lemma_map                 WHERE id BETWEEN :llo AND :lhi;
DELETE FROM normalization_patterns    WHERE id BETWEEN :llo AND :lhi;
DELETE FROM prefix_assimilation_rules WHERE id BETWEEN :llo AND :lhi;
COMMIT;
```

   Step (a) is what makes a second install of the same pack idempotent,
   and what lets a future build move a work between packs without
   duplicates.

6. Copy, one table per transaction, in FK-safe order (`authors`, `works`,
   `books`, `text_lines`, `translation_segments`, `milestone_line_ranges`,
   `words`, `dictionary_entries`, `lemma_map`, `normalization_patterns`,
   `prefix_assimilation_rules`, `translation_lookup`). `authors` uses
   `INSERT OR REPLACE`, since an author shared between the base and a pack
   (Plato, in the full DB and the Greek supplement) is carried by both with
   identical content; every other table uses plain `INSERT`, because step 5
   has already cleared what the pack replaces:

```sql
INSERT OR REPLACE INTO main.authors (id, name, name_alt, language, has_translations)
    SELECT id, name, name_alt, language, has_translations FROM pack.authors;
INSERT INTO main.words (id, word, book_id, line_number, sequence_number, word_position)
    SELECT id, word, book_id, line_number, sequence_number, word_position FROM pack.words;
```

   Columns are listed explicitly from the canonical schema so a column
   order difference can never silently misalign. For the three big tables
   the installer drops that table's secondary indexes before the insert and
   recreates them from the canonical DDL afterwards. Index names and
   definitions must match `shared/database_schema.py` exactly because Room
   validates them on the next open. `sqlite_autoindex_*` primary key indexes
   cannot be dropped and are not.

7. Verify before declaring success:
   - `SELECT count(*)` per table over the pack's band equals `manifest.rows`.
   - `PRAGMA foreign_key_check` returns no rows.
   - `PRAGMA quick_check` returns `ok`.
   - Then `PRAGMA foreign_keys = ON`, `PRAGMA wal_checkpoint(TRUNCATE)`,
     `DETACH pack`, `UPDATE pack_state SET state='installed', finished_at=:now`.
8. Delete `cacheDir/packs/<pack>.db`. Reopen Room; its schema validation is
   the last gate. A validation failure routes to `DatabaseErrorActivity` as
   today.

Crash recovery: on launch, any `pack_state` row in `merging` is repaired by
running step 5(b) and 5(c) for that pack and marking it `absent`. The user
is told the download can be resumed. Because every row the merge wrote is in
the pack's band, this is exact.

Removal of a pack: step 5(a) for the pack's works (the retained pack copy
supplies the work list), plus 5(b) and 5(c), then
`DELETE FROM authors WHERE id NOT IN (SELECT DISTINCT author_id FROM works)`,
then `removePack()` or deletion of the retained external copy, then mark
`absent`. Removing a supplement removes only what it added, because the
base and the supplements do not share works.

Merge duration is not known and must be measured on a mid-range device
before any UI copy quotes a time. The Greek supplement writes about 5.7 GB
and rebuilds indexes over 24.9 M word rows. Expect minutes to tens of
minutes. Only the measured number goes in the UI.

## 8. Runtime DB lifecycle

State lives in a `pack_state` table inside `perseus_texts.db`, created with
raw SQL from `RoomDatabase.Callback.onOpen()` exactly as `normalization_patterns`
is in `UserDatabase`. It is not a Room entity, so the entity list and
version do not change. `DatabaseValidator.kt:153` must exclude it the same
way it excludes `room_master_table`.

```sql
CREATE TABLE IF NOT EXISTS pack_state (
    pack_id      TEXT PRIMARY KEY NOT NULL,
    state        TEXT NOT NULL,            -- absent | merging | installed
    band         INTEGER NOT NULL,
    channel      TEXT NOT NULL,            -- play | external
    layout_version INTEGER NOT NULL,
    app_version_code INTEGER NOT NULL,
    zip_sha256   TEXT,
    build_time   TEXT,                     -- from the pack manifest
    started_at   INTEGER,
    finished_at  INTEGER
);
CREATE TABLE IF NOT EXISTS base_state (
    k TEXT PRIMARY KEY NOT NULL, v TEXT
);   -- rows: base (sample | full | external), app_version_code, layout_version, extracted_at
```

The base is the sample zip from the APK or the full pack, whichever the
user has chosen, exactly as today. Installing the full pack keeps its
current whole-file flow (close Room, delete, extract, restart) with one
addition: it is treated as a base change, so the installed supplements are
re-merged onto the new base afterwards, through the same rebuild below.

Policy:

- **The runtime DB is a function of (base, installed packs).** Whenever
  `base_state.app_version_code` differs from `BuildConfig.VERSION_CODE`, or
  the user changes base, the app rebuilds: read `pack_state` into memory
  first, since re-extracting the base deletes the file that holds it, then
  re-extract the chosen base (sample zip or full pack zip), recreate
  `pack_state` from the saved list with every row set to `absent`, then
  re-merge each pack. Play-channel packs come from
  `AssetPackManager.getPackLocation()`, which Play has already patched to
  the new version. External packs come from the retained copy in
  `filesDir/packs/`. If a retained copy is missing, that pack is marked
  `absent` and the pack row shows "Import again". This also closes
  today's gap where an app update never re-extracts a newer sample zip.
  Users with no packs see the ~7 second extraction they saw on first
  install.
- Packs stay on the device after merging, on both channels. Play keeps its
  packs patched, so a rebuild after an app update needs no re-download; the
  retained external copies serve the same purpose. The steady-state cost is
  the runtime DB (~15 GB with everything) plus the pack copies (~3 GB). A
  "free space after install" option that calls `removePack()` per Play pack
  and deletes the retained external copies is possible, but then an app
  update means a re-download or a re-import. Default: keep.
- `PreferencesManager.useFullDatabase` stays and becomes the value of
  `base_state.base`.
- **The external import handles two kinds of file.** The existing "Select
  database" flow opens a zip through the file picker. If the zip contains
  `manifest.json` and a `.db` entry, it is a supplement pack and goes to the
  installer (section 7). Otherwise it is a whole database, and the existing
  behaviour applies: it is copied to `external_perseus_texts.db`, a
  separate file that `PerseusDatabase.kt:57-82` opens in preference to
  `perseus_texts.db` while the external preference is set. The two kinds
  are distinguished by content, not by file name.
- **A whole external DB is a third base**, `base_state.base = external`,
  and while it is active supplements merge into `external_perseus_texts.db`.
  It can take packs only if the assembly stamped it with the lexicon bands
  (section 6) and a layout-version marker: the assembly writes a second
  system row in `dictionary_entries`, `headword='layout_version'`, in every
  mode, and the installer refuses to merge a pack onto any base, bundled or
  external, whose layout version does not match the pack's. A whole DB
  built before this proposal has no such row and cannot take packs; the UI
  says so. On an app update with an external base, the base file is not
  re-extracted, because the app did not ship it; the rebuild re-merges each
  pack onto it, which is safe because a merge first deletes the pack's
  band.

## 9. Build pipeline changes

All in `data-prep/assemble_database.py`, extended mode, after the schema
drift check and before compression, as one new stage `emit_language_packs()`.
No new standalone scripts. No manual steps.

Prerequisite, before the first supplement is cut: resolve the Sanskrit
double import (section 3) in the assembly, so that each lexicon exists
once in the extended DB. Otherwise the languages supplement inherits the
second copy, the complement rule below still passes (full plus supplements
still equals extended), and the desktop round trip cannot see it, because
it compares against the same extended DB. Where to resolve it, the module
build or `LEXICON_PATHS`, is a pipeline decision outside this proposal.
The Arabic lexicon zip is a separate matter: it is not imported today
because of its member names, and fixing that adds about 7 MB compressed to
the languages supplement.

1. Read the pack registry from `shared/pack_layout.py`: language numbers,
   pack ids, bands, channels, the size target, and the definition of each
   supplement as a complement of the full DB (Greek supplement: Greek works
   not in the full DB; languages supplement: every language not in the
   full DB, with its lexicon).
2. Compute the complement against `data-prep/perseus_texts_full.db`, which
   the extended build therefore requires to exist from the same data
   release; abort if it is missing or older than the module DBs.
3. For each pack: create `<pack>.db` with `create_schema()`, `ATTACH` the
   assembled extended DB, `INSERT ... SELECT` the pack's rows with the band
   offset applied, create indexes, `VACUUM`, run `diff_against_canonical()`,
   zip with the entry named `<pack>.db`, write the manifest.
4. Auto-split: if the Greek supplement's zip is over the target, move PTA
   to the languages supplement and recompute; if still over, split First1K
   by author into parts and redo step 3 for each part.
5. Hard failures: any Play-channel zip over 1.5 GB (the Play cap, separate
   from the target); the sum of all Play-channel on-demand packs, database
   and non-database, over `PLAY_ON_DEMAND_BUDGET_BYTES` (section 4); a
   Play-channel pack whose `<pack>_pack/build.gradle` is missing, or an
   external-channel pack whose module is still listed in `settings.gradle`
   (an asset-pack module with an empty `assets/` fails `bundleRelease`);
   the complement rule of section 4 (full plus supplements equals extended
   per table, no work id in two packs); any lexicon row outside its band;
   `max(id)` in the base text tables at or above `BAND_WIDTH`. The budget
   table is printed on every run, pass or fail, so the measured sizes are
   always in the build log.
6. Self-check by round trip: merge both supplements into a copy of the full
   DB, and separately into a copy of the sample DB, on the build machine
   using the same SQL the client runs (kept in one shared `.sql` resource
   the Python and the Kotlin both read). The full-based result must match
   the extended DB per table and per language and pass
   `data-prep/text_integrity/audit.py` against it with zero regressions.
   This proves on the desktop what the phone will do, every build.
7. Copy each Play-channel zip and its sidecar manifest to
   `<pack>_pack/src/main/assets/`. Copy each external-channel zip to
   `data-prep/external_packs/` (build output, gitignored, never staged),
   together with a generated `external_packs_index.json` listing pack id,
   languages, zip size, sha256 and build time, which is the text to post
   with the download links. Uploading those files to the external download
   is a manual step, like pushing a zip to a device. The full pack's copy
   and the iOS extended copy are unchanged.

Gradle: one `com.android.asset-pack` module per Play-channel supplement
(each a two-line `build.gradle` identical to `references_pack/build.gradle`
with its own `packName`), listed in `settings.gradle` and in
`android.assetPacks`; initially just `db_supplement_greek_pack`.
`full_database_pack` stays. `checkDatabaseExists` gains a check that every
declared pack module has its zip and manifest, or the release build fails.
Moving a pack between channels is a registry change plus adding or
removing its module, and the build checks the two agree.

Sample and iOS builds change only in that lexicon ids move into language
bands (section 6). `greek/run_build.sh` and `latin/run_build.sh` are
untouched. BUILD.md gains the new stage in Step 7, the pack table in
"Release targets", and replaces every "too large for Android" note.

Debug builds cannot read asset packs. `LanguagePackInstaller` gets the same
fallback `TopicalPackManager` has: if `getPackLocation()` is null in a debug
build, look for `<pack>.db.zip` and its manifest under
`getExternalFilesDir("packs")`. That directory needs no permission and is
reachable with `adb push`, which is the one manual step CLAUDE.md allows.
`deploy_with_bundletool.sh --local-testing` remains the way to exercise the
real on-demand path.

## 10. UI

One "Database downloads" screen with three rows: Full database (the
existing flow), Greek supplement (First1K and PTA), Languages supplement
(Sanskrit and eight others), each listing what it contains. Each row has a
status and an action: Download, Downloading (percent), Installing
(percent), Installed, Remove. A supplement on the external channel shows
"Import" instead of "Download"; it opens the file picker and shows where
the file is published. An installed row shows which channel it came from
and the pack's build time. The Greek supplement row on a sample base says
that Perseus Greek is in the full database. The overflow item "Download
Full Database" becomes "Database downloads" and opens that screen. "Select
database" keeps its name and now accepts either a whole database or a
supplement pack (section 8). Before a download, show the
compressed size from the manifest, the space the merge needs, and the
measured install time. Route
`REQUIRES_USER_CONFIRMATION` and `WAITING_FOR_WIFI` through
`showConfirmationDialog()` as `FullDatabaseDownloadActivity` does. A pack
that Play reports present but `pack_state` says absent shows "Install"
rather than "Download".

The merge runs in a foreground service so the user can leave the screen.
The reader is unavailable while a merge runs, because Room must be closed;
the main screen shows the same "database is being prepared" state
`DatabaseExtractionActivity` shows today.

## 11. Migration

- Existing full-pack users: unchanged experience. The first launch after
  this ships sees a version change and rebuilds from the full pack, which
  Play has already patched, with no supplements to merge. The only visible
  difference is that the full DB is re-extracted on app updates from now
  on, which it was not before.
- Whole external DB users: the import flow is unchanged for a whole DB. A
  whole DB built before this proposal keeps working on its own but cannot
  take packs (section 8). The next data release published on the external
  download carries the layout version row, and packs can then be merged on
  top of it.
- iOS: unchanged in this proposal. The lexicon band change is invisible to
  it. Apple has deprecated On-Demand Resources as of iOS 27; the separate
  `IOS_BACKGROUND_ASSETS_MIGRATION_PLAN.md` covers that move.
- README: the external download entry for extended gains the languages
  supplement zip alongside the whole extended DB zip, with the build time
  of each.

## 12. Verification plan

Milestone 1, before any Kotlin is written: **the size-limit probe.** Build
the packs (section 9), assemble a release bundle with both supplements on
the `play` channel (the languages supplement's Gradle module exists for
this probe even if it later moves to the external channel), and upload it
to the internal testing track. Play Console
computes the compressed download sizes at upload and rejects a bundle that
breaks a limit, with the limit named. Nobody outside the internal testers
list sees it, and it can be discarded. Outcomes:

- Accepted with the on-demand total above 4 GB: the 30 GB figure applies
  to this account. Raise `PLAY_ON_DEMAND_BUDGET_BYTES` and move every pack
  to the `play` channel.
- Rejected on the cumulative total: 4 GB is the real limit. Keep the budget
  at 4 GB and set channels from the measured table (section 4). The packs
  on the external channel still reach Android users through the external
  download.
- Rejected on a per-pack size: the 1.5 GB figure does not hold either;
  lower the auto-split target and rebuild.

Everything after this milestone is the same under both outcomes.

1. Build-side round trip (section 9, step 6) on every extended build.
2. `bundletool build-apks --local-testing` install on a device; download
   and merge each pack; confirm `pack_state`, row counts, `foreign_key_check`,
   `quick_check`, and that Room opens.
2a. Room identity hash: record the hash literal in the generated
   `PerseusDatabase_Impl.java` before the `Int` to `Long` change (section
   6), rebuild, and confirm it is unchanged. Then install the new build
   over an existing install without clearing data and confirm Room opens.
2b. Shared authors: install the full pack, then the Greek supplement, then
   remove the supplement. After each step confirm Plato (tlg0059) still has
   every Perseus work, and after the removal that Plato's First1K works are
   gone and the author row remains. Repeat on the sample base with an
   author present in both the sample and the supplement: the sample's works
   survive and the author row is not duplicated.
2c. Base change: with both supplements merged onto the sample base, install
   the full pack; confirm the rebuild re-merges both supplements and the
   result matches the full-based desktop round trip per table.
3. Measure merge time and peak disk use per pack on a mid-range phone and a
   flagship. Record in BUILD.md.
4. Kill the app during a Greek supplement merge; relaunch; confirm recovery
   leaves the DB identical to before the merge (row counts per band).
5. Install the full pack and both supplements, then `adb pull` the runtime
   DB and run `text_integrity/audit.py --corpus all` against the extended
   DB. Zero per-work regressions.
6. Uninstall/reinstall, app update with packs installed, remove a pack.
7. External pack import: pick the languages supplement zip through the file picker,
   confirm the same `pack_state`, row-count, `foreign_key_check` and
   `quick_check` results as a Play pack, and confirm the retained copy in
   `filesDir/packs/`. Then an app update with the external pack installed
   (rebuild uses the retained copy), and the same with the retained copy
   deleted first (row marked absent, "Import again" shown, no crash).
8. Whole-DB import: a whole external DB with the layout version row takes
   packs; one without it is refused with the message, and still opens on
   its own as today.
9. Internal-track upload to Play Console. This is the only real test of the
   size limits and of Play's confirmation dialog for the 1.2 GB pack.

## 13. Open decisions

1. Ship the external pack import (section 8) in the first release
   (recommended, so the languages supplement is a 0.6 GB import instead of
   the 3.1 GB whole extended DB), or leave the whole extended DB as the
   only external route at first.
2. Keep packs on device after merging (recommended) or offer "free space",
   which costs a re-download on every app update.
3. Rebuild the runtime DB on every app version change for all users
   (recommended, fixes the stale-sample gap) or only for pack users.
4. The recommended two-supplement layout, or the per-language alternative
   in section 4.
5. Size target for auto-split: 1.2 GB (recommended) or something else.
6. Run the text-integrity baseline before the lexicon band change lands.
7. Do the internal-track probe upload first (recommended). It needs one
   extended build and one upload.
8. Retain a copy of each imported external pack in app storage
   (recommended, so a rebuild after an app update needs no re-import) or
   not (saves the pack's zip size on device, costs a re-import).
9. Where the external packs are published: the existing Patreon post, or
   somewhere else. The build produces the files and an index either way.
10. Where to resolve the Sanskrit double import (section 3): stop the
    module build importing the lexicon zip, or remove Sanskrit from
    `LEXICON_PATHS`. Either gives one copy; the choice decides whether the
    module DB stays self-contained like Greek and Latin. Separately,
    whether to fix the Arabic lexicon zip member names so it imports.

## 14. Risks

- **Merge time on low-end phones.** Unknown until measured. Mitigation: the
  foreground service, per-table transactions, index drop/recreate. The
  Greek supplement writes about 5.7 GB and rebuilds indexes over 24.9 M
  word rows, and a base change re-merges everything.
- **The supplements depend on the full DB.** They are defined as its
  complement, so the extended build now requires a full DB from the same
  data release and aborts without it. The build order in BUILD.md must say
  so.
- **Disk pressure.** Everything installed is ~18 GB. The space check runs
  before each download and each merge, and the UI states the total.
- **A Play upload rejected on size.** The two hard failures in the build
  (1.5 GB per pack, 4 GB cumulative on-demand) match the most conservative
  reading of Google's published figures. A rejection after that would mean
  Google lowered a limit or the account is being held to something not
  published. The auto-split target and the channel settings are the knobs.
- **External packs and version skew.** A user can download an external
  pack months after the app build on the device, or the other way round.
  The schema hash and layout version checks stop an incompatible pair from
  merging. A compatible but older pack merges fine, because replacement is
  by work and by band, and the row shows the pack's build time so the
  skew is visible. The external download page must state the build time
  of each file.
- **Two channels to keep in step.** The registry, `settings.gradle` and the
  external download must agree on which packs are where. The build checks
  the first two against each other; the third is a manual upload and the
  generated index is what makes it checkable.
- **The size estimates are ±20 percent.** The initial Play set in
  section 4 has about 0.07 GB of estimated margin. The measured table from the
  first build fixes the set. Sanskrit is the one measured figure; the
  Greek supplement is still an estimate.
- **Duplicated rows inflate packs invisibly.** The Sanskrit double import
  was found only by comparing the module DB with the extended DB. The
  complement rule and the round trip both compare against the extended DB
  and would not catch a duplicate that is already in it. A per-language
  comparison of module DB row counts against the extended DB, for every
  language with a separate lexicon zip, belongs in the build's checks.
- **Schema drift between base and packs.** Impossible by construction:
  both come from `shared/database_schema.py`, both are drift-checked, and
  the client compares the schema hash before merging.
- **Room index validation after drop/recreate.** Mitigated by generating
  the recreate statements from the same canonical DDL the drift check uses,
  and by the desktop round trip.
- **The `Int` to `Long` entity change.** If the Room identity hash does
  change, the band layout must instead be redesigned to keep every id under
  2^31, which means narrower bands and dense renumbering of ids at slice
  time. That is possible but it is a different section 6. The hash check
  in section 12 settles it before any other work starts.

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
