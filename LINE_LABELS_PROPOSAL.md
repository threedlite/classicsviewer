# Proposal: Non-numeric line numbers ("line labels")

Status: **rejected for now** (owner decision, 2026-09-27). Kept as a record
of the measurements and the code survey. Written 2026-09-26; nothing
implemented. Every figure below was
measured on that date against the TEI sources in `data-sources/` and the
shipped `perseus_texts_{sample,full,extended,ios}.db` (all built
2026-09-14); the file:line references were read from the current tree.
Reviewed 2026-09-27: every DB figure re-measured, every file:line reference
re-read; corrections are in place and marked where the earlier text was
wrong.

## 1. Summary

Perseus TEI numbers some verse lines with labels that are not integers:
`929a`–`929t` in Hesiod's Theogony, `169a`–`169d` in Works and Days, `325b`
in Terence, `41_43` in Theocritus. The pipeline stores the integer part only
(`text_lines.line_number INTEGER NOT NULL`), so Theogony 929 and 929a–t are
twenty-one rows all labelled 929, distinguishable only by `sequence_number`.
The label survives nowhere the app reads. Nothing can address such a line by
its printed number: not the reader's line column, not bookmarks' "Line N",
not an audio file named `line_929a.mp4`.

The sibling project `~/git/hesiod` already ships per-line audio for every
hexameter poet in Perseus and has `_lettered` package variants whose file
names keep the suffix. Its own report (`~/git/hesiod/reports/phase7_hesiod.md:31-38`)
names the two blockers on the Android side: `AudioImportWorker` parses the
text after `line_` as an integer, and `audio_mappings.line_number` is
INTEGER. iOS has the same two in its own form: `DefaultAudioExtractor.swift:121`
does `Int(lineStr)`, and the iOS audio store is `audio_files.line_start` /
`line_end`, both INTEGER (§3).

Proposed: keep `text_lines` exactly as it is and add a **sparse label table**
to the shipped Perseus DB, `line_labels (book_id, sequence_number) → label`,
holding a row only where the TEI label differs from the integer. It is not a
Room entity, so no entity list or version changes. The app overlays the label
on each line it already loads and shows it, where it refines the stored
number (929 → 929a), in place of the number. No stored or displayed number
changes (§5a). The audio
database, which is plain SQLite owned by the app, gets a real version-2 table
keyed by label. That is the "version 2 table with string line numbers, in
addition to the int" the request describes, applied where each fits.

## 2. What the data contains

### 2a. TEI sources (`<l n="…">` elements, Greek and Latin canonical repos)

| Form | Count | Where |
|---|---|---|
| integer | (the rest) | |
| digits + one letter (`929a`, `325b`) | 22,524 | mostly Terence (phi0134) and Plautus (phi0119), Greek and English files alike |
| letters only (`cast`, `argument`, `tr`) | 11,836 | almost all in the English translations of Lucan and Terence; structural labels, not lines |
| range (`179_180`, `41_43`) | 293 | Theocritus, Aratus, Apollonius, Quintus, Nonnus |
| range + letter (`624_625b`) | 113 | |
| digits + letters (`101aa`, `3ff`) | 80 | |
| other (`subject_1`, `602 608`, `366O`) | 362 | |

Files with at least one non-integer `n`: 101 Greek, 83 Latin.

Classification used in this table and in §2b: "lettered" is digits followed
by one or more **lowercase** letters; an uppercase suffix (`366O`, the
Juvenal `O` fragment lines) is counted under "other"; "range" includes the
range-plus-letter forms. Re-counted 2026-09-27 with the same rule: same
totals.

### 2b. Shipped databases (`text_lines` rows whose stored `<l n>` differs from `line_number`)

The label is the `n` of the **outer `<l>` element** that the pipeline made
the line from. A first pass that also accepted a nested `<lb n>` inside prose
sections over-counted by 466 rows (all Euclid, tlg1799); those are excluded
here and must be excluded by the pipeline rule in §5.

| | sample | full | extended | iOS |
|---|---|---|---|---|
| rows in `text_lines` | 222,709 | 1,010,513 | 3,169,237 | 59,607 |
| rows with no outer `<l n>` in `line_xml` (prose etc.; label = number) | 129,018 | 665,010 | 2,823,734 | 20,097 |
| **rows whose label ≠ `line_number`** | **5,758** | **71,783** | **71,783** | **25** |
| of which lettered (`929a`, `680ab`) | 983 | 12,212 | 12,212 | 25 |
| of which ranges (`41_43`, `624_625b`) | 0 | 218 | 218 | 0 |
| of which other (`602 608`, `366O`) | 0 | 79 | 79 | 0 |
| of which **plain integers that differ** (see below) | 4,775 | 59,274 | 59,274 | 0 |
| books affected | 43 | 194 | 194 | 3 |
| bytes of label text (size of a sparse table's payload) | 13 KB | 140 KB | 140 KB | 99 B |

Every `<l>` element that the pipeline made a line from carries an `n`
(0 rows with an outer `<l>` and no `n`, all four DBs).

Extended equals full: the 17,726 non-Perseus books contribute no row, verified
by building the table from the extended DB itself.

The "plain integers that differ" population was not in the request but falls
out of the same measurement. In the poem/epigram-collection path
(`greek/build_modules/monolith_fn.py:7480-7563`: `poem_divs` at 7480,
`sequential_line_num = 1` once per book at 7491, `'number':
sequential_line_num` at 7557) `line_number` is a running counter over the
whole book and the TEI `n`, which restarts at 1 for each poem, is read only
as a gate (`parse_line_number` at 7538 decides whether the line counts) and
then discarded. In this path `line_number == sequence_number` for every row.
The reader therefore shows Catullus-style collections with
book-wide numbers that match no printed edition. A label table records the
printed number with the same rule, since the label is simply the TEI `n`.
It is **not displayed** for these lines: showing it would change the number
users see and have bookmarked (§5a).

**Uniqueness, measured on the full DB (re-measured 2026-09-27):** lettered,
range and other labels never repeat within a book (0 duplicate `(book_id,
label)` pairs). Collection labels do repeat, by construction: inside the
label table 4,779 `(book_id, label)` pairs occur more than once, across 72
books; counting every `<l n>` row, including the unstored lines whose label
equals their number, 5,410 pairs across 74 books (Martial book 2 has 94 rows
labelled "1", one per epigram). (The earlier text said 4,795 pairs in 85
books; that count could not be reproduced by either definition.) So a
label identifies a line only where it carries a suffix or range; for
collections it is stored but not shown (§5a), and anything that must address
a line keeps using `(line_number, sequence_number)`. §5, §8 and §11 are written to that.

Per-work breakdown: §2d.

### 2c. Ordering

`TextLineDao.getByBook` and `getByBookAndRange` order by
`line_number, sequence_number`. Where the TEI prints lines out of numeric
order this puts them back in numeric order, against the editor. Works and
Days stores seq 168→168, 169→**170**, 170→171, 171→172, 172→173, 173→**169**,
174–177→169a–d. The reader shows 169, 169a–d after 173.

| | sample | full |
|---|---|---|
| books with at least one adjacent pair out of numeric order | 6 | 69 |
| such pairs | 10 | 173 |

Greek drama is not among them: the drama path sorts lines by integer at
build time (`monolith_fn.py:7389-7449`, `lines.sort(key=lambda x:
x['number'])` at 7423, a stable sort, so rows sharing an integer keep
document order) before assigning `sequence_number`, so for those plays
document order was already lost and sequence order equals numeric order.
That path is taken only for `author_id in ['tlg0085', 'tlg0011', 'tlg0006',
'tlg0019']` (Aeschylus, Sophocles, Euripides, Aristophanes; `:7349`). The
Latin monolith has the identical block (`latin/build_modules/monolith_fn.py:4614,
4655-4715`) with the same four Greek ids, so no Latin author ever takes it:
Plautus, Terence and Seneca go through the standard `<l n>` path and keep
document order, which is why Seneca's tragedies head the out-of-order list
in §2d. The ordering decision in §11 therefore changes nothing for the four
Greek dramatists and applies to every other path.

### 2d. Per-work breakdown

Sample DB, the one bundled in the APK:

| Kind | Rows | Books | Largest works |
|---|---|---|---|
| lettered | 983 | 37 | Sophocles Oedipus at Colonus 92, Euripides Orestes 91, Ion 79, Iphigenia Aulidensis 57, Phoenissae 56, Hercules 47, Sophocles Philoctetes 46, Euripides Troades 45 |
| renumbered (poem collections) | 4,775 | 6 | Horace Carmina 2,870, Sermones 1,905 |
| range / other | 0 | 0 | |
| out-of-order pairs | 10 | 6 | Theogony 3, Works and Days 3, Aeneid book 10, Ars Poetica, Odyssey books 3 and 14, one each |

Theogony, checked row by row on 2026-09-26 and again on 2026-09-27: 1,042
rows, highest number 1,022, `books.line_count` 1,042. Exactly 20 rows carry
a label that differs (929a–929t), each unique in the book. The three
transpositions are seq 213/214 (lines 214, 213), seq 426/427 (427, 426) and
seq 430/431 (434, 430), all editorial and all present in the TEI. The Hesiod
`_lettered` package's 1,042 Theogony file names equal the DB's 1,042 labels
exactly, both ways.

iOS DB (`IOS_SAMPLE_AUTHORS.csv`): 25 lettered rows in 3 books, 9
out-of-order adjacent pairs in 5 books, no collections.

In the drama books the letters mark split lines shared between speakers,
which the edition prints as, for example, 325a and 325b. Today those rows show
325 twice. The label restores the edition's text; it does not "fix" the
duplicate, which is legitimate.

Full DB:

| Kind | Rows | Books | Largest works |
|---|---|---|---|
| lettered (one or more letters) | 12,212 | 123 | Plautus Miles Gloriosus 502, Terence Phormio 490, Eunuchus 478, Andria 469, Heautontimorumenos 463, Plautus Rudens 438, Pseudolus 431, Poenulus 422 |
| renumbered (poem collections) | 59,274 | 74 | Greek Anthology 20,526, Martial 9,288, Propertius 3,793, Statius Silvae 3,324, Juvenal 2,973, Horace Carmina 2,870, Ovid Ex Ponto 2,842, Tristia 2,556 |
| range (`41_43`) | 218 | 22 | Plautus Casina 42, Mostellaria 27, Menaechmi 23, Pseudolus 21, Stichus 14 |
| other (`602 608`, `366O`) | 79 | 7 | Juvenal 34, Plautus Amphitruo 22, Cistellaria 13, Aulularia 5, Seneca Troades 2, Medea 2 |
| out-of-order pairs | 173 | 69 | Seneca Troades 12, Hercules Oetaeus 11, Medea 8, Persius 6, Seneca Phaedra 6, Oedipus 6, Nonnus Dionysiaca books 42 and 40, 6 and 5 |

The Greek Anthology figure means every one of its 20,526 lines currently
shows a book-wide running number instead of the epigram-relative number the
TEI carries, and under §5a it keeps doing so; the label only records the
printed number.

### 2e. Size impact per database (measured 2026-09-26)

Method: the proposed table (§5), with both secondary indexes, was built from
each database's real rows into a standalone SQLite file with the same 4 KB
page size, vacuumed, and zipped with `zip -9`. The standalone zip is the
proxy for the compressed delta.

| DB | Rows | Table only | With indexes | Zipped | Current DB | Current zip | Delta, uncompressed | Delta, compressed |
|---|---|---|---|---|---|---|---|---|
| sample | 5,758 | 381 KB | 729 KB | 141 KB | 664.0 MB | 163.3 MB | +0.11 % | +0.09 % |
| iOS | 25 | 12 KB | 20 KB | 1.3 KB | 376.3 MB | 88.0 MB | +0.01 % | +0.00 % |
| full | 71,783 | 4.65 MB | 8.9 MB | 1.67 MB | 4.97 GB | 1.086 GB | +0.18 % | +0.15 % |
| extended | 71,783 | 4.65 MB | 8.9 MB | 1.67 MB | 14.99 GB | 3.135 GB | +0.06 % | +0.05 % |

Extended equals full because the non-Perseus texts (17,726 books, 59,842
rows with `line_xml`) yield no row whose label differs from its number;
verified by building the table from the extended DB itself.

Against the delivery limits documented in `ASSET_PACK.md` (Play limits and
current pack sizes), `ANDROID_EXTENDED_LANGUAGE_PACKS_PROPOSAL.md` §2 and,
for iOS, `IOS_BACKGROUND_ASSETS_MIGRATION_PLAN.md:83,156`:

| Delivery | Limit | Today | After |
|---|---|---|---|
| Android base module (sample zip, install-time) | 500 MB Play; 200 MB self-check in `app/build.gradle:404-405` (`checkAabSize`, measured on the built AAB) | 163.3 MB (`app/src/main/assets/perseus_texts.db.zip`, 163,297,763 B) | 163.4 MB |
| Android `full_database_pack` (on-demand) | 1.5 GB per pack | 1.086 GB | 1.088 GB |
| Android AAB cumulative on-demand | 4 GB (treated as the limit; 30 GB as printed) | 2.73 GB (2,733,102,092 B, `ASSET_PACK.md`) | 2.74 GB |
| Android extended (external host, not Play) | none from Play | 3.135 GB | 3.137 GB |
| iOS bundled sample zip | app bundle, no separate limit | 88.0 MB | 88.0 MB |
| iOS full / extended ODR packs | 8 GB per pack (iOS 18+) | 1.086 / 3.135 GB | +1.7 MB each |

(Corrected 2026-09-27: the earlier table gave 157.7 MB for the base module
and 2.68 GB for the on-demand total; neither matched the files in the tree
or `ASSET_PACK.md`. The AAB self-check itself was not run.)

No limit moves. The largest delta is 1.7 MB compressed on a 1.09 GB pack.
The two secondary indexes account for half the uncompressed size. Leaving
`idx_line_labels_book_line` out would save about 2 MB in the full DB at the
cost of a scan when listing labels by integer range. That choice has to be
made before the first build that ships the table: once an index has shipped
it stays (§5b).

## 3. How the system treats line numbers today (verified)

Pipeline (`greek/build_modules/monolith_fn.py`, Latin copy at
`latin/build_modules/monolith_fn.py:792`):

```python
# monolith_fn.py:2956-2973  parse_line_number
if line_n.isdigit(): return int(line_n)
match = re.match(r'^(\d+)', line_n)
if match: return int(match.group(1))
return None            # callers skip the line
```

- `929a` → 929. The label is kept only as the serialised element in
  `text_lines.line_xml` (`<ns0:l … n="929a">`). `'original_line_n'` exists in
  the parse dict "for debugging" (`monolith_fn.py:7561`, Latin `:4826`) and
  is never read or written; the `text_lines` INSERT (`:7614-7618`) takes
  `line['number']`, `line['text']`, `line['xml']`, `line.get('speaker')`.
- A label with no leading digits (`τ`, `cast`) returns `None` and the line is
  skipped. This proposal does not change that; §10.
- `words` rows copy the same integer and `sequence_number`.
- Translations: a lettered `n` in an English file yields one segment with
  `start_line = end_line = 929`; `translation_lookup` maps line 929 to all of
  them. Theogony has 5 Evelyn-White segments at 929, one per English TEI
  label (`tlg0020.tlg001.perseus-eng2.xml` has `<l n="929a">`, `929e`,
  `929j`, `929o`, `929t` and no plain 929). The reader shows them as one
  group. Unchanged by this proposal; §10. (Corrected: the earlier text said 6.)
- **Interlinear is ambiguous for every duplicated integer.** The generator
  reads `SELECT line_number, line_text … ORDER BY line_number`
  (`generate_interlinear.py:553-558`; `sequence_number` appears nowhere in
  that file) and writes `<l n="{line_num}">` (`:1878`); the import
  (`monolith_fn.py:5706`, INSERT at `:5844-5847`; Latin `:3369`, `:3507-3510`)
  stores `start_line = end_line = sequence_number = int(n)`. Theogony
  therefore has 21 interlinear segments all stored as (929, seq 929), one per
  Greek row, with nothing to say which belongs to 929c. Full DB: 22,594
  interlinear rows in 9,870 such groups across 120 books; `text_lines` itself
  has 9,875 duplicate `(book_id, line_number)` groups (22,605 rows, 121
  books), so all but five groups carry interlinear (drama split lines
  included). Pre-existing; the label table does not fix it and this proposal
  does not touch the interlinear pipeline. Follow-up in §10.

Schema (`shared/database_schema.py:60-69`): `text_lines(id INTEGER PRIMARY
KEY AUTOINCREMENT NOT NULL, book_id, line_number INTEGER NOT NULL,
sequence_number INTEGER NOT NULL, line_text, line_xml, speaker, FOREIGN KEY
(book_id))`, indexes `idx_text_lines_book(book_id)` and
`idx_text_lines_sequence(book_id, sequence_number)` (`:157-160`), **no
unique key on `(book_id, line_number)`** and none on `(book_id,
sequence_number)` either. `sequence_number` is the 1-based document position
and the only unique line key in practice. Bookmarks already key on it
(`BookmarkEntity.kt:11`: unique `(book_id, line_number, sequence_number)`).
`data-prep/schema.sql:35` is a second copy of the DDL that nothing in the
pipeline reads; the module builds, `latin/create_latin_database.py:83,199`
and `data-prep/assemble_database.py:41` all use `shared/database_schema.py`.

Android consumers of `lineNumber`, by role:

| Role | Where |
|---|---|
| Display label | `TextLineAdapter.kt:67`, `TextLineWithSpeakerAdapter.kt:80`, `OccurrenceAdapter.kt:71`, `ui/BookmarksAdapter.kt:43`, `ui/BookmarkEditorActivity.kt:141`, `export/TextExporter.kt:58, 94, 227` (`:87` is the CSV header). `TranslationAdapter.kt:166-170` shows `segment.startLine`/`endLine`, a translation-segment number, not a text line |
| Range / paging ordinal | `TextLineDao.getByBookAndRange` (`TextLineDao.kt:12-13`), `data/PerseusRepository.kt:297-315` (`getTextLines`, DAO call at `:303`), `TextViewerPagerActivity.kt:196-209, 500-580, 1292, 1355` (also `:309`, `:1155`), `LemmaOccurrencesActivity.kt:113-115`, `ui/BookmarksActivity.kt:167`, `topical/TopicalLinksActivity.kt:340`, `LineRangeDialogFragment.kt:16, 53` |
| Exact key (with sequence) | `TextLineDao.getByBookLineAndSequence` (`:15-16`), `BookmarkDao`, `fragments/TextPageFragment.kt:325-327`, topical packs (`topical/TopicalReader.kt:304, 324-325`: `anchorLine` and `anchorSeq` read as int32 from `rowmeta.bin`; consumed in `TopicalLinksActivity.kt:282-314`) |
| Audio key | `TextLineWithSpeakerAdapter.kt:112` `audioMappings[line.lineNumber]`; map declared `Map<Int, AudioMapping>` at `TextViewerPagerActivity.kt:61`, built at `:312-320` and `:640-647` |

Audio is a separate plain-SQLite database, `audio_data.db`, opened with
`SQLiteDatabase.openOrCreateDatabase` (`AudioDatabaseHelper.kt:248`). It is
not Room and not a `SQLiteOpenHelper` either: `DATABASE_VERSION = 1` is
declared (`:12`) and never used, so there is no `onUpgrade` hook and nothing
sets a stored schema version (`PRAGMA user_version` is never written). `ensureTablesExist()`
(`:62-73`) runs `CREATE TABLE IF NOT EXISTS`:

```sql
audio_mappings(... book_number INTEGER NOT NULL, line_number INTEGER NOT NULL,
  file_path TEXT NOT NULL, ..., UNIQUE(package_id, author_name, work_title, book_number, line_number))
```

Package layout `Author/Work/book_N/line_X.{mp4|mid}`, with or without a
leading package folder (`AudioImportWorker.kt:284-285`).
`AudioImportWorker.kt:308-310` parses `X` with
`substringAfter("line_").substringBefore(".").toIntOrNull() ?: return null`,
so `line_929a.mp4` is dropped; `DefaultAudioExtractor.kt:117-137` and its
duplicate at `:269-290` do the same for the bundled Iliad with `toInt()`
inside `try/catch (NumberFormatException)` and a `Log.w`. Lookup is
`getAudioForLineRange(authorName, workTitle, bookNumber, startLine, endLine)`
(`:164`, `line_number BETWEEN ? AND ?` at `:175`), results keyed
`associateBy { it.lineNumber }` into `Map<Int, AudioMapping>`, so every row
sharing an integer would play the same file. `AudioMapping`
(`AudioDatabaseHelper.kt:337-347`) has `lineNumber: Int` and no label field.

iOS mirrors all of this, with a different audio store:
`Models/DatabaseModels.swift:37-41` (`lineNumber: Int`, `sequenceNumber:
Int`), `Database/LineDAO.swift:13-17` (same ORDER BY),
`Database/DefaultAudioExtractor.swift:117-122` (`Int(lineStr)`; a
non-integer name falls through silently; the extractor is hard-coded to
`Homer/Iliad/book_1`). The reader prints the number at
`Views/ReaderView.swift:884` (also `:1457`, `:1718`). Audio mappings live in
`user_data.db` (`UserDatabaseManagerAsync.swift:8`), tables `audio_packages`
and `audio_files(id, package_id, work_id TEXT, book_id TEXT, line_start
INTEGER NOT NULL, line_end INTEGER NOT NULL, file_path, duration_ms,
file_size, mime_type)` (`:185-213`); lookup is `AudioPackageDAO.swift:188-190`
(`line_start <= ? AND line_end >= ?`), called from `AudioPlayer.swift:30-40`
(`playAudioForLine(... lineNumber: Int)`). There is no `audio_mappings`
table on iOS; the integer pair `line_start`/`line_end` is its counterpart.

Precedents this proposal follows:

- Shipped tables that are not Room entities and are read with raw SQL:
  `prefix_assimilation_rules` and `normalization_patterns`, both present in
  the shipped Perseus DB (populated by `monolith_fn.py:10017`), read at
  `data/PerseusRepository.kt:74-75` and `:113-114` via
  `database.openHelper.readableDatabase.query(...)`, each with a "table not
  available (older database)" fallback (`:102`, `:136`). Neither is in the
  `PerseusDatabase` entity list (`PerseusDatabase.kt:16-25`, nine entities).
  `milestone_line_ranges` (`database_schema.py:81-87`, composite primary key,
  no AUTOINCREMENT) is shipped and never read by either app (no match in
  `app/src` or `ios/`). Room validates only the tables in its entity list;
  these extra tables open without error today. iOS reads
  `prefix_assimilation_rules` with raw SQL too
  (`Database/PrefixAssimilationRuleDAO.swift:50, 129, 148`).
- (Not followed.) `ios/…/BookmarkDAO.swift:34` once altered an existing
  table (`ALTER TABLE bookmarks ADD COLUMN sequence_number INTEGER NOT NULL
  DEFAULT 0`). Under the rule in §5b this proposal adds no column to any
  existing table on either platform; it is listed only so nobody cites it as
  the pattern.
- Dynamic table in a Room DB via `onOpen`: `UserDatabase.kt:82-88, 99-140`,
  `NormalizationPatternHelper`. Note this is a *second* table named
  `normalization_patterns`, in `user_data.db`, with a different schema
  (`package_id`, `created_at`) from the shipped one. Not needed here (the
  table ships in the DB), but it is the pattern if an app-side table were
  ever wanted.

## 4. Options considered

**A. `text_lines_v2`, a full copy with `line_number TEXT`.** Rejected. It
duplicates the largest table (3.1M rows with text in the extended DB), gives
two sources of truth, and every DAO and page-arithmetic site would need a
parallel path. The integer is still needed as the paging ordinal.

**B. Sparse `line_labels` table in the shipped DB. Recommended.** One row per
line whose label differs from its integer: 5,758 rows in the sample DB,
71,783 in the full. Everything else keeps working untouched; consumers that
want the label overlay it.

**C. Derive the label at runtime from `line_xml`.** No pipeline or DB change,
works on already-downloaded databases. Rejected as the primary mechanism:
`line_xml` is absent for 58–66 % of rows, the app would parse XML in every
display path on both platforms, and nothing could query by label where a label is unique (audio join,
"go to 929a"). Kept as a documented fallback for a debug build only.

**D. Change `text_lines.line_number` to TEXT.** Impossible under the Room
rule: the column is in a registered entity; any type change crashes every
existing install.

## 5. Data model (option B)

Added to `shared/database_schema.py`, so all four DBs (sample, full,
extended, iOS) get it:

```sql
CREATE TABLE line_labels (
    book_id         TEXT    NOT NULL,
    sequence_number INTEGER NOT NULL,   -- joins text_lines(book_id, sequence_number)
    line_number     INTEGER NOT NULL,   -- integer part, equal to text_lines.line_number
    label           TEXT    NOT NULL,   -- TEI n verbatim, NFC, trimmed
    PRIMARY KEY (book_id, sequence_number)
);
CREATE INDEX idx_line_labels_book_label ON line_labels(book_id, label);
CREATE INDEX idx_line_labels_book_line  ON line_labels(book_id, line_number);
```

Rules:

- A row exists **only** when `label != CAST(line_number AS TEXT)`. Absence
  means "the label is the number". This keeps the table at 140 KB of text in
  the full DB and makes the overlay a no-op for prose.
- `label` is the `n` of the element the pipeline made the line from (the
  `<l>`), exactly (after NFC and trim), including ranges (`41_43`) and the
  odd forms (`602 608`, `366O`). Never a nested `<lb>` or milestone `n`
  (§2b). No parsing, no normalisation of suffix style. The app never
  interprets it beyond the §5a display test; it shows it only where it
  refines the stored number, and uses it as a key only together with
  `line_number` (§8), because collection labels repeat within a book.
- The table has no AUTOINCREMENT `id` and does not reference `text_lines.id`.
  `merge_database.py` (repo root) drops and regenerates `id` for every table
  whose DDL says AUTOINCREMENT (`:101-146`) and remaps ids only for
  `translation_segments` (`:117`), carrying the mapping into
  `translation_lookup.segment_id` (`:164-187`); `line_labels` takes the plain
  branch instead (`:148-162`: common columns copied with `INSERT OR IGNORE`),
  the same branch `milestone_line_ranges` already uses. Rows cannot collide
  across module DBs because `book_id` carries the work namespace.
  (Corrected: the earlier text described `:108-134` as a general
  `text_lines.id` remapping; there is none.)
- `line_number` is repeated so the audio range query and any "which labels
  fall in page 901–1000" query need no join.
- Not registered in `PerseusDatabase`. Read through a small helper over
  `openHelper.readableDatabase`, exactly like `prefix_assimilation_rules`.
- Name: `line_labels`, not `text_lines_v2`, because it does not replace
  `text_lines` and is not a second version of it.

Poem collections (the 59,274 "renumbered" rows): the rule above stores the
TEI `n` for them too, since it differs from the running counter. It needs no
special case, and the §5a display test keeps it off the screen. Decision
recorded in §11 in case the owner wants that path excluded from storage as
well.

## 5a. Invariant: stored line numbers never change

Bookmarks are the reason. On both platforms a bookmark is identified by
`(book_id, line_number, sequence_number)`: Android `BookmarkEntity` with its
unique index, iOS `BookmarkDAO.swift:51-64`. The CSV export carries exactly
those columns and the import re-inserts them verbatim, with no matching
against the text:

```
work_id,book_id,line_number,sequence_number,author_name,work_title,book_label,line_text,note,created_at,last_accessed,work_title_english
```
(`ui/BookmarksActivity.kt` `performExport`/`performImport`;
`ios/…/Utilities/BookmarkCSVHandler.swift:10`, which also reads old exports
without `sequence_number` by defaulting it to 0.) Topical links build their
reference from the integer (`BookmarkEditorActivity.kt:302`). Users also
have these numbers in their own notes.

So the rule for this proposal, and for the rebuild that ships it:

1. **`text_lines.line_number` and `sequence_number` are byte-identical for
   every existing row before and after.** The proposal writes nothing to
   `text_lines` or `words`; `line_labels` is additive; the ordering decision
   (§11.1) changes display order only, never a stored value. Any bookmark,
   exported CSV or topical reference made before resolves to the same Greek
   line after.
2. **No displayed number changes either.** A label is shown only when it
   *begins with* the stored integer: `929a`, `41_43`, `680ab`. A line whose
   label does not start with its number, which is the whole poem-collection
   population (Martial stores 57, label "1"), keeps showing 57. Lettered
   lines gain a suffix; nothing loses or changes the number a user has
   written down or bookmarked. The test is one general rule: the label's
   leading run of digits equals the stored integer (`^(\d+)` of the label
   == `line_number`). That is exactly the relation the pipeline's
   `parse_line_number` guarantees wherever the integer came from the TEI
   `n`. A plain `startsWith` would be wrong for a label "10" on line 1, so
   it is not used. Measured on the label tables: the test shows 983 labels
   in the sample DB and 12,464 in the full DB, and never fires for a
   digit-only collection label (0 cases in either DB). Two collection
   facts are recorded so nobody relies on the opposite: 815 collection
   labels are numerically larger than their counter (Juvenal books 2, 3 and
   5, Catullus book 2 and Propertius book 4 supply most of them), so no
   ordering assumption is made; and 45 suffixed labels sit inside collection
   books (Juvenal book 2 has 37, among them the uppercase `O` fragment
   lines; Tibullus `14a`–`14c`; Catullus `23b` at counter 411) and fail the
   test, so those lines keep showing the counter, which is today's number.
   The rule is applied in the reader, the text export and iOS alike.
3. The bookmark list keeps saying "Line 929"; the reader shows 929a; the
   bookmark's stored `line_text` identifies the exact line, as it does today.
   Showing the suffix in the list is decision 3.
4. Verification is a direct diff, not an inference: dump
   `book_id, sequence_number, line_number, line_text` from the old and new DB
   with `sqlite3` and `diff`; it must be empty. The text-integrity audit
   hashes reconstructed text in `(book_number, line_number, sequence_number)`
   order, which catches reordering but not a renumbering that keeps order, so
   the key diff is the check that protects bookmarks. A previously exported
   bookmark CSV is re-imported on the new build and every entry opens on the
   same line.

Collection labels are still stored (§5); they cost 4 MB in the full DB and
are the only record of the printed number. Whether to show them somewhere,
for example as a secondary "poem line" in the detail view, is a later
decision that does not touch this invariant.

## 5b. Invariant: existing tables and indexes never change

Owner's rule, recorded 2026-09-27: **in every database the app touches, the
schema of an existing table or index cannot change; only new tables and new
indexes may be added.** This covers the shipped Perseus DB, Android
`audio_data.db`, Android `user_data.db` and the iOS `user_data.db`. No
`ALTER TABLE`, no `DROP TABLE`, no `DROP INDEX`, no rebuilt index, on
anything that exists today.

How each part of this proposal complies:

| Database | Existing objects | This proposal |
|---|---|---|
| Perseus DB (all four builds) | `text_lines`, `words`, `translation_*`, their indexes | untouched; adds `line_labels` and its two indexes (§5) |
| Android `audio_data.db` | `audio_packages`, `audio_mappings`, its indexes | untouched and never dropped; adds `audio_mappings_v2` (§8) |
| iOS `user_data.db` | `audio_packages`, `audio_files`, `bookmarks`, … | untouched; adds `audio_file_labels` (§9) |
| Android `user_data.db` (Room) | bookmarks and dictionary tables | untouched |

`ORDER BY` changes in queries (§11.1) are not schema changes. Verification
is §12 step 12.

## 6. Pipeline changes

All in the existing monolith build modules; no new scripts (project rule).

1. `shared/database_schema.py`: the DDL above.
2. `greek/build_modules/monolith_fn.py` and `latin/build_modules/monolith_fn.py`:
   every path that reads a TEI `n` and calls `parse_line_number` also keeps
   the raw `n` (`line_label = nfc(line_n.strip())`) in the line dict. Paths
   that assign a running counter (poem collections, prose, First1K) set
   `line_label` to the TEI `n` when there is one, else to the counter as
   text. At insert time, one general statement:
   `if line_label != str(line_number): INSERT INTO line_labels …`.
   The `text_lines`-writing sites, so none is missed:
   - Greek `process_text_file` (`:7324`): drama `:7403`/INSERT `:7436-7440`,
     poem collection `:7538`/`:7614-7618`, standard `<l n>` per book div
     `:7585`, second poem-div path `:7666`, single-book fallback `:7730`.
   - Greek counter paths: `process_first1k_work` `:2733, 2762`;
     `process_prose_with_books` `:6246, 6314`; `process_prose_text` `:6782`;
     `process_pta_bible_text` `:6940, 7019`; `process_new_testament_text`
     `:7100`; `handle_tei_format` `:7245`; `handle_tei_format_first1k`
     `:7303`; `process_euclid_elements` `:7875`.
   - Latin `process_text_file` (`:4589`): `:4668, 4803, 4850, 4931, 4995`,
     INSERTs `:4701, 4879, 4966, 5021`; prose `:3891, 3959, 4428`.
   - `extract_translation_segments` also calls `parse_line_number` (Greek
     `:3550, 3600, 4319`; Latin `:1093, 1148, 1867`) but writes
     `translation_segments`, out of scope (§10).
3. `assemble_database.py` / `merge_database.py`: nothing to change, for a
   different reason than first written. The merge reads the source table
   list from `sqlite_master` (`merge_database.py:67`) but **skips** any table
   missing in the target with a warning (`:82-85`); it does not create
   tables. `line_labels` travels because step 1 puts it in `TABLE_DDL`, which
   every module build and the assembled target use (`create_schema`,
   `assemble_database.py:220`), and `diff_against_canonical`
   (`assemble_database.py:270-278`, `database_schema.py:265-292`) raises on
   any extra or missing table, so forgetting step 1 fails the build rather
   than dropping the table silently. Non-Greek/Latin module DBs (Dante,
   Sanskrit, …) define their own schemas and simply lack the table in their
   `sqlite_master`, which the merge tolerates. The `_stamp_build_time` step
   (`assemble_database.py:313-345`) is unaffected. Two table lists outside
   the pipeline may be updated for completeness but are not run by it:
   `data-prep/verify_module_output.py` (~`:174`) and
   `data-prep/merkle_snapshot.py:87`.
4. Quality report: `generate_quality_report` (`monolith_fn.py:8625`, totals
   at `:8649-8664`, called from `assemble_database.py:296-299`) gets a
   per-DB line `line_labels rows: N (lettered A, range B, renumbered C,
   other D), books E`, checked against the §2b figures for the first build;
   the Latin module summary (`latin/create_latin_database.py:416-428`, which
   already counts `milestone_ranges`) gets the module-level count. A count of
   zero for a DB that had labels before is a build failure, not a warning
   (project rule).
5. Lines whose `n` has no leading digit stay skipped, as today (§10).

Text-integrity: this touches the build pipeline for every DB, so per
`CLAUDE.md` a `data-prep/text_integrity/audit.py --corpus all` snapshot is
taken before the change and diffed after. The audit reads `works`
(`audit.py:140-150`) and `books JOIN text_lines` (`reconstruct.py:24-39`),
read-only; it does not read `translation_segments` (that is the separate
`audit_gloss_regressions.py`) and does not list tables, so a new table
cannot disturb it. It hashes (SHA-256, `verify.py:205`) the reconstructed
text in `(book_number, line_number, sequence_number)` order
(`reconstruct.py:37`). Expected diff: none; the change is purely additive.
Any non-empty diff blocks the rebuild.

## 7. Android changes

| File | Change |
|---|---|
| `database/helpers/LineLabelHelper.kt` (new) | `labels(bookId, seqFrom, seqTo): Map<Int, String>` and `labelsForLines(bookId, lineFrom, lineTo)` via raw SQL on `openHelper.readableDatabase`; returns empty if the table is absent (older downloaded DB) |
| `models/TextLine.kt` | add `label: String` (constructor default `lineNumber.toString()`) and `displayLabel` per §5a rule 2 |
| `data/PerseusRepository.kt:297` `getTextLines` | after `getByBookAndRange`, overlay labels by `sequenceNumber` |
| `TextLineAdapter.kt:67`, `TextLineWithSpeakerAdapter.kt:80` | show `line.displayLabel`: the label when it begins with the integer, else the integer (§5a rule 2) |
| `TextLineWithSpeakerAdapter.kt:112` | `audioMappings[line.lineNumber to line.label] ?: audioMappings[line.lineNumber to line.lineNumber.toString()]` (§8) |
| `TextViewerPagerActivity.kt:61, 312-320, 640-647` | declare and build `Map<Pair<Int, String>, AudioMapping>` keyed by (integer, label); `AudioMapping` (`AudioDatabaseHelper.kt:337-347`) gains `lineLabel: String` |
| `TextLineDao.kt:9-13` `getByBook`, `getByBookAndRange` | `ORDER BY sequence_number` (decision, §11) |
| `export/TextExporter.kt:58, 94, 227` | write `displayLabel` (`:87` is the CSV header `line_number,text`, unchanged). Only change: an exported lettered line reads `929a` where it read `929`; every other line exports the same number as today |
| `ui/BookmarksAdapter.kt:43`, `OccurrenceAdapter.kt:71` | optional: look up the label by `(bookId, sequenceNumber)`; both already have the sequence. Default in v1: unchanged |

Untouched: `PerseusDatabase` entity list and version, every DAO signature,
paging arithmetic (pages stay integer ranges; a range that contains 929
returns all 21 rows, as it does today), bookmarks (keyed by sequence),
topical packs, translation queries, search.

**Existing installs do not pick the table up on upgrade.** The app extracts
the bundled sample DB only when `perseus_texts.db` is absent
(`MainActivity.kt:412-421` `needsDatabaseExtraction()`, `return
!dbFile.exists()` at `:420`), and iOS skips extraction when the existing
file validates (`Database/DatabaseExtractor.swift:46-57`, "Existing database
is valid, skipping extraction"). Neither platform reads the DB's build stamp
(the only version checks are for the rhetoric DB, `RhetoricDbHelper.kt:34`,
and topical packs, `TopicalReader.kt:49`; iOS `DatabaseValidator.swift:343-351`
reads `PRAGMA user_version` and only logs it). So after the app update an
upgrader keeps the old DB and sees numbers only, until Reset to Bundled
Database (`MainActivity.kt:359-361` menu, `:749` dialog, `:768` deletes the
DB and `-wal/-shm/-journal` and re-copies), Settings "Refresh Database"
(`SettingsActivity.kt:216`, deletes the file so the exists-check fires), a
full-DB re-download, or a fresh install. The helper therefore checks
`sqlite_master` once and returns empty maps when the table is absent; that
path is the normal one for upgraders, not an edge case, and nothing may
crash or log noisily on it. Whether to prompt upgraders to reset is decision
5 in §11.

## 8. Audio changes (Android `audio_data.db`, plain SQLite)

This database is created and owned by the app, so it can carry a real
version-2 table:

```sql
CREATE TABLE IF NOT EXISTS audio_mappings_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_id INTEGER NOT NULL, author_name TEXT NOT NULL, work_title TEXT NOT NULL,
    book_number INTEGER NOT NULL,
    line_number INTEGER NOT NULL,   -- integer part, for range queries
    line_label  TEXT    NOT NULL,   -- text after "line_" in the file name, verbatim
    file_path TEXT NOT NULL, ...,
    UNIQUE(package_id, author_name, work_title, book_number, line_number, line_label)
);
```

**Key rule.** A text line is matched to audio by the pair
`(line_number, label)`, falling back to `(line_number, str(line_number))`.
Why a pair and not the label alone: collection labels repeat within a book
(§2b), and a package named by the running counter (`line_57.mp4` for the
line the DB stores as 57 / "1") must keep working as it does today. Under
the rule: `line_929a.mp4` → (929, "929a") matches Theogony 929a and nothing
else; `line_929.mp4` → (929, "929") matches only the plain 929;
`line_57.mp4` → (57, "57") matches the collection line via the fallback,
exactly today's behaviour; a package that names collection files by the
printed number (`line_1.mp4` for epigram 2 line 1) does not match, exactly
as it does not today. Nothing that works now stops working.

- `ensureTablesExist()` creates it and, once, copies every `audio_mappings`
  row with `line_label = CAST(line_number AS TEXT)`. "Once" needs a marker,
  because this database has no schema version today (§3: `DATABASE_VERSION`
  unused, no `onUpgrade`). The marker is the table itself: in one
  transaction, if `audio_mappings_v2` is absent in `sqlite_master`, create it
  and run the copy; if present, do nothing. No `PRAGMA user_version` write
  and no other change to the file's existing contents. **`audio_mappings` is
  left exactly as it is, indexes included, and is never dropped (§5b).**
  New code reads and writes only `audio_mappings_v2`; the old table becomes
  inert. (Corrected: the earlier text dropped it after one release.)
- `AudioImportWorker.kt:308-310`, `DefaultAudioExtractor.kt:117-137` **and**
  its duplicate at `:269-290`: `label = substringAfter("line_").substringBefore(".")`;
  `line_number = leading digits of label` (same rule as the pipeline); a name
  with no leading digit is skipped and logged, as now.
  `AudioImportWorker.AudioMappingEntry` (`:391`) gains the label.
- `getAudioForLineRange` (`AudioDatabaseHelper.kt:164-175`) selects from v2
  by `line_number BETWEEN`, returns `lineLabel`; callers build the
  `(line_number, label)` map.
- The bundled Iliad package has integer names only, so its rows are
  unchanged: `line_label` equals the number.
- Hesiod `_lettered` packages then import completely: 2,352 files for
  Hesiod (24 lettered: Theogony 929a–t, Works and Days 169a–d), 16 lettered
  lines in the Homeric Hymns package (2,342 files), and the four Nonnus
  range names (`line_74_75.mp4`, `line_75_74.mp4` in Dionysiaca 21;
  `line_95_97.mp4`, `line_97_95.mp4` in 37), which the DB stores verbatim as
  `74_75`, `75_74`, `95_97`, `97_95` and which therefore match under the
  pair rule. No other corpus package (Apollonius, Aratus, Theocritus,
  Quintus) has a range-named file. (Corrected: the earlier text said
  "`41_43`-style names in the later corpora".) The package folder names
  match the DB strings: `Hesiod/Theogony`, `Hesiod/Works and Days`,
  `Hesiod/Shield of Heracles` equal `authors.name` and `works.title`; the
  Hymns package uses `Homeric Hymns/Hymn N to <deity>`, which equals the
  33 `works.title` values including `Hymn 17 To the Dioscuri`.

## 9. iOS changes

| File | Change |
|---|---|
| `Models/DatabaseModels.swift:37-45` | `TextLine.label: String` |
| `Database/LineDAO.swift:13-18` | second query on `line_labels` for the loaded sequence range, overlay; `ORDER BY sequence_number` (§11); tolerate a missing table |
| `Views/ReaderView.swift:884` (line column; also `:1457`, `:1718`) | show `displayLabel` (§5a rule 2) |
| `Database/DefaultAudioExtractor.swift:117-122`, and `AudioPackageDAO.swift:75` (the `INSERT INTO audio_files`) | keep the text after `line_` as the label; leading digits as the integer |
| `UserDatabaseManagerAsync.swift:185-213` (`audio_files`), `AudioPackageDAO.swift:75, 188-190`, `AudioPlayer.swift:30-40` | the iOS store is `audio_files(line_start, line_end)` in `user_data.db`, not an `audio_mappings` table (§3), so "the same `_v2` table" does not apply literally. `audio_files` is not altered (§5b). Add a new sidecar table, created next to the others in `UserDatabaseManagerAsync.swift`: `audio_file_labels(file_id INTEGER PRIMARY KEY REFERENCES audio_files(id) ON DELETE CASCADE, line_label TEXT NOT NULL)`, one row per imported file whose label differs from `CAST(line_start AS TEXT)`, written by the same code that does the `INSERT INTO audio_files` (`:75`). Lookup becomes `audio_files LEFT JOIN audio_file_labels` on the existing `line_start <= ? AND line_end >= ?`, label defaulting to the integer, and the caller applies the §8 pair rule with the same fallback. Existing rows need no migration: absence of a sidecar row already means "label equals the number" |
| `BookmarkDAO.swift` | unchanged (keyed by `sequence_number`) |

(Corrected 2026-09-27: the earlier table assumed an iOS `audio_mappings`
table; the model, DAO and reader line references were also off by a few
lines.)

Per project rule the iOS project is not built or regenerated here; Swift is
edited and handed off. No new resource files, so no pbxproj change.

## 10. Out of scope, stated so they are not mistaken for oversights

- **Lines whose `n` has no leading digit** (`τ`, `cast`, 11,836 mostly
  structural labels in English files) stay skipped. Making them lines is a
  separate question about what they are.
- **Translation alignment by label.** English 929a–t segments still attach to
  the 929 group. A `segment_labels` table could pair them later using the
  same rule; it needs its own measurement of how English files label lines.
- **`words` and search.** Occurrence results show `book.929`; they carry the
  sequence number and can be given the label in a follow-up.
- **Interlinear per line.** Making interlinear rows line-exact means the
  generator selecting `sequence_number` alongside `line_number` and the
  import writing it into `translation_segments.sequence_number`, then a
  full interlinear regeneration (about 5 hours Greek, 51 minutes Latin) and
  the pass-2 module rebuilds. It is the only way a lettered or split line
  gets its own interlinear block. Separate proposal; it needs its own
  text-integrity baseline because it regenerates `translation_segments`.
- **Paging by document position** instead of integer ranges. Correct in
  principle, but it touches every page-arithmetic site and the topical pack
  format; not needed for labels.
- **The `has_alphanumeric` translation path and `INSERT OR IGNORE`
  semantics** are left as they are.

## 11. Decisions for the owner

1. **Order lines by `sequence_number` in the reader?** Recommended yes. It
   restores the editor's order in the 69 full-DB books that have transposed
   lines and makes a visibly out-of-order label (169 after 173) honest rather
   than silently re-sorted. Pages remain integer ranges and no stored value
   changes (§5a). If no, the label overlay still works and only §7/§9 ORDER
   BY lines are dropped.
2. **Store labels for poem collections** (the 59,274 renumbered rows)?
   Recommended yes, store but do not display (§5a rule 2): storing is the
   same pipeline rule with no special case and keeps the printed number on
   record; displaying it would change the number users see and have
   bookmarked, which §5a forbids. If no, the collection path sets
   `line_label = str(counter)` and writes nothing, saving 4 MB.
3. **Bookmark and occurrence display** with labels in v1 or later. Proposed
   later.
4. **Take the text-integrity baseline now** (`audit.py --corpus all` on the
   current extended DB) or reuse an existing report? Facts: the
   `baseline_extended_all.*` symlinks point at
   `20260904_treebank_content_extended_all.*` (2026-09-04); the shipped DBs
   were built 2026-09-14, after pipeline commits on 2026-09-14 (`2a5c02a`,
   Latin gloss and interlinear modules, `assemble_database.py`,
   `latin/build_modules/monolith_fn.py`); the newest audit of that build is
   `20260914_post_ijfix_extended_all.*` (2026-09-14 18:26, after the
   extended DB's 18:01 write). So the symlinked baseline is ten days older
   than the DB it would be compared with. Proposed: diff
   `20260914_post_ijfix_extended_all` against the symlinked baseline first;
   if clean, repoint the symlink to it and use it as the pre-change
   baseline; if not, take a fresh snapshot of the current extended DB before
   any pipeline edit. (Corrected: the earlier text called the existing
   baseline valid without checking its date.)
5. **Upgraders.** Existing installs keep their old DB (§7). Options: leave it
   (labels appear after the next reset or re-download), or show a one-time
   notice pointing at Reset to Bundled Database. Proposed: leave it in v1;
   the reader is correct either way, only the label column differs.

## 12. Verification plan

Pipeline, on a sample build first (5 min), then full:

1. `line_labels` row count and breakdown equal §2b for that DB; every row
   joins to exactly one `text_lines` row; no row has `label ==
   CAST(line_number AS TEXT)`.
2. Text-integrity diff against the baseline is empty.
2a. Bookmark-identity diff (§5a rule 4): `sqlite3 old.db "SELECT book_id,
    sequence_number, line_number, line_text FROM text_lines ORDER BY 1,2"`
    and the same on the new DB, `diff`ed, is empty for sample, full and
    extended.
3. `sqlite3 … "SELECT label FROM line_labels WHERE book_id='tlg0020.tlg001.001'
   ORDER BY sequence_number"` lists `929a … 929t`.

Android, debug build with the new sample DB, after uninstall and `pm clear`:

4. App opens; no "Pre-packaged database has an invalid schema" (the table is
   unlisted, so Room ignores it).
5. Theogony page 901–1000 shows 929, 929a … 929t in the line column; Works
   and Days shows 168, 170, 171, 172, 173, 169, 169a–d in that order if
   decision 1 is yes.
6. A bookmark on 929c survives restart and reopens on 929c. A bookmark CSV
   exported from the previous build imports on the new build and every entry
   opens on the same line, including one in a poem collection (Martial) and
   one on a drama split line.
7. Import `hesiod_chamberlain_tts_female_lettered.zip`; 929a plays its own
   file; the Iliad bundled audio still plays line 1.
8. A full DB downloaded before the change shows numbers only and no crash
   (helper returns empty).
9. Upgrade path: install the previous build, open a text, then install the
   new build over it without uninstalling. The old sample DB stays; the
   reader works and shows numbers only; Reset to Bundled Database then
   shows labels.
10. Audio fallback: the Iliad bundled package still plays every line
    (integer names, fallback key); a collection book with a counter-named
    test package still plays. Import the Nonnus `_lettered` package: Dionysiaca
    21 line `74_75` plays `line_74_75.mp4` and `75_74` plays `line_75_74.mp4`.
10a. Audio migration marker: open an `audio_data.db` written by the previous
    build (integer-only `audio_mappings`), start the new build once, confirm
    `audio_mappings_v2` holds one row per old row with `line_label =
    CAST(line_number AS TEXT)`, then restart and confirm the copy did not run
    again (row count unchanged). `audio_mappings` and its indexes are still
    present with their original `sql` in `sqlite_master`.
12. Schema invariant (§5b): for each database, dump `SELECT type, name, sql
    FROM sqlite_master ORDER BY 1, 2` before and after and `diff`. The only
    lines allowed to differ are additions: Perseus DB `line_labels` and its
    two indexes; `audio_data.db` `audio_mappings_v2` and its indexes; iOS
    `user_data.db` `audio_file_labels`. Any changed or removed line fails
    the check. Run it on the sample, full and extended Perseus DBs and on an
    `audio_data.db` / `user_data.db` carried over from the previous build.
11. Pipeline guard: a unit check in the build that no `line_labels` row came
    from a nested `<lb>`: every stored label must equal the `n` of the
    namespace-prefixed `<l>` element that `line_xml` begins with.

iOS: the user builds; checks 5–7 on device.
