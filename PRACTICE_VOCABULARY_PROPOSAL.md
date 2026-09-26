# Proposal: "Practice Vocabulary" (Greek, DCC Core List)

Status: Android implemented 2026-09-24, Latin added 2026-09-26, iOS written 2026-09-26 (this document updated to match); iOS unbuilt
Author: Claude (with danmeany@gmail.com)
Date: 2026-09-24
Current app version: 0.8.138
Target release: TBD

## 1. Summary

Add a **Practice Vocabulary** option directly below **Practice Alphabets** on both
platforms. Version 1 covers Greek only. The word set is the Dickinson College
Commentaries (DCC) Greek Core Vocabulary, ordered by its frequency rank, so the
learner works through the most common words first.

The feature follows the two existing precedents:

- **Practice Alphabets** (`alphabet/AlphabetGameActivity.kt`,
  `ios/.../PracticeAlphabetsView.swift`) for the game mechanic and screen layout.
- **Rhetoric reference** (`figures/build_rhetoric_db.py`, `rhetoric/RhetoricDbHelper.kt`)
  for shipping a small third-party dataset under a Creative Commons licence with
  a one-script, repeatable build.

It does not touch `perseus_texts.db`, any Room entity, or `data-sources/`.

## 2. Source data (verified 2026-09-24)

Source: https://dcc.dickinson.edu/greek-core-list
Machine-readable exports on the same site: `/greek-core-list.csv` and `/greek-core-list.xml`.

What the CSV contains, measured from a download today:

| Item | Value |
|---|---|
| Rows | 524 (header + 524 entries) |
| Columns | `Headword`, `DEFINITION`, `Part of Speech`, `SEMANTIC GROUP`, `FREQUENCY RANK` |
| Distinct part-of-speech labels | 29 (e.g. `noun: 2nd declension`, `verb: contracted`, `adverb`) |
| Distinct semantic groups | 28 (e.g. `War and Peace`, `Time`, `Body Parts`) |
| Definition length | average 29 characters, longest 151 |
| Headwords containing principal parts or genitive + article | 415 of 524 contain a space, 290 contain a comma |

Quirks the build script must handle (all present in the current download):

- Rank 384 is assigned to two entries (θνῄσκω and λύω) and rank 385 is unused.
  Ranks are otherwise 1–524 with no gaps.
- One headword (ζῷον) is not in Unicode NFC form. Every field must be NFC-normalised.
- Four headwords are correlative pairs written with an ellipsis (`μέν...δέ`,
  `οὔτε...οὔτε`, `μήτε...μήτε`, `εἴτε…εἴτε`), using both three periods and U+2026.
- One headword carries an optional ending in parentheses: `εἴκοσι(ν)`.
- Verb headwords list principal parts, sometimes with English glosses embedded
  (e.g. ἵστημι). Noun headwords give nominative, genitive and article.

Provenance, from https://dcc.dickinson.edu/vocab/core-vocabulary: the list was
compiled in 2012–13 under Christopher Francese from TLG frequency data (texts to
AD 200, about 20 million words, supplied by Maria Pantelia) and Perseus frequency
data (about 5 million words, supplied by Helma Dik). DCC states the roughly 500
words cover about 65% of word forms in a typical Greek text.

Licence: **Creative Commons Attribution-ShareAlike 3.0 Unported (CC BY-SA 3.0)**.
See §10.

## 3. Placement in the app

**Android** — `app/src/main/res/menu/main_menu.xml`: add
`action_practice_vocabulary`, title "Practice Vocabulary", immediately after
`action_practice_alphabets`. `MainActivity.onOptionsItemSelected` starts
`VocabularyGameActivity`, mirroring the existing alphabet case.

**iOS** — `SettingsView.swift`, "Learning" section: add a `NavigationLink` to
`PracticeVocabularyView()` immediately after the "Practice Alphabets" link.

The option is always visible. The language picker inside the screen offers only
"Greek" in v1, which leaves room for other languages later without moving the
menu item.

## 4. Data pipeline

New directory `vocabulary/` at the repo root, following `figures/`:

```
vocabulary/
  README.md                          source URL, download date, licence
  sources/
    dcc_greek_core_list.csv          the DCC export, committed as downloaded
  build_vocabulary.py                the ONE build script
  greek_core_vocabulary.json         generated output (committed, like figures/rhetoric.db.zip)
  vocabulary_quality_report.txt      generated
```

The source CSV is committed rather than fetched at build time, for the same
reason the rhetoric mirror is committed: the build must be repeatable and must
not depend on a live website. Refreshing the list is a deliberate step:
re-download, replace the file, rerun the script, review the diff.

`build_vocabulary.py`:

1. Reads `sources/dcc_greek_core_list.csv`. Fails if the header is not exactly
   the five columns above, if there are fewer than 500 data rows, or if any
   field is empty.
2. NFC-normalises every field.
3. Derives `lemma` from `Headword` with one general rule (§5). Fails if any
   lemma is empty or contains a character outside the Greek blocks.
4. Parses `FREQUENCY RANK` as an integer. Fails on non-numeric. Duplicate ranks
   are kept and reported, ordering ties by source row order.
5. Optional coverage check: if `data-prep/perseus_texts_sample.db` is present,
   looks each lemma up in `dictionary_entries` (`headword = ?`, `language = 'greek'`)
   and fails if coverage drops below 95%. Today's measured coverage is 517/524
   (§5), so the floor catches a regression in the lemma rule without failing on
   the known non-resolving entries.
6. Writes `greek_core_vocabulary.json`: an array of objects
   `{rank, headword, lemma, definition, pos, group}` plus a top-level
   `{source, url, license, retrieved}` block. Also writes the quality report.
7. Copies the JSON to:
   - `app/src/main/assets/vocabulary/greek_core_vocabulary.json`
   - `app/src/debug/assets/vocabulary/greek_core_vocabulary.json`
   - `ios/ClassicsViewer/Resources/greek_core_vocabulary.json`

JSON rather than CSV at runtime so neither platform needs a CSV parser that
copes with quoted commas. The file is about 70 KB; no compression needed.

No network access, no manual edits to the generated file, no intermediate steps.

## 5. Lemma derivation and dictionary linking

The game displays the lemma on the word tile and uses it to open the app's own
dictionary. The rule is general and applies to every row identically:

1. NFC-normalise.
2. If the headword contains `...` or `…`, split there and keep the first part
   (the display keeps the full correlative headword).
3. Remove any parenthesised segment, e.g. `(ν)`.
4. Take the first token, splitting on commas and whitespace.
5. Strip leading and trailing hyphens and en dashes.

Measured by the build script against `data-prep/perseus_texts_sample.db`,
**522 of 524** lemmas match a `dictionary_entries.headword` exactly. The two
that do not (πλέον, a comparative form, and δέδοικα, a perfect used as a
present) still get the "Open in dictionary" button; `DictionaryActivity`
already handles a Greek headword with no entry. No word-specific handling.

Linking uses the existing `DictionaryActivity` intent contract, which was
verified from the source: extras `word`, `lemma`, `language`. On iOS the
equivalent is the existing word-detail view.

## 6. Game design

Same mechanic as Practice Alphabets so the two screens feel like one feature:

- Greek word chips above, shuffled definition tiles below (layout in §6a).
  Definitions show the DCC text **verbatim**, wrapped, never truncated, so no
  gloss is ever altered.
- Tap a word, then tap its definition. Correct pairs turn green; a wrong tap
  shows "Try again!" and marks the round as imperfect.
- Round scoring, the 3-second pause, the perfect-round glow and the points
  header are reused unchanged.

Controls in the header, replacing the alphabet screen's "combined forms" checkbox:

| Control | Values | Default |
|---|---|---|
| Language | Greek | Greek |
| Words per round | 2–7 | 3 |
| Set | Ranks 1–25, 26–50, … 501–524, and All | 1–25 |

"Set" is what "by top frequency" means in practice: the learner starts with the
25 most frequent words and moves down the list. Rounds draw only from the
chosen set. A word counts as mastered once it has been matched in a perfect
round, and that record persists (§7). Mastery of a set (gold stars) is awarded
when every word in it is mastered. The alphabet game's session-long perfect
streak requirement is not carried over: with progress persisting across
sessions, a single mistake permanently blocking the stars would make no sense.
Rounds draw unmastered words first, then mastered ones, so a set is worked
through rather than sampled at random.

Round assembly avoids two words with identical definition text in one round
(519 distinct definitions across 524 rows, so a few pairs collide), mirroring
how the alphabet game avoids duplicate phonetics.

Long-press (Android) or a small info button (both) on a word tile opens a sheet
with the full DCC headword (principal parts or genitive and article), part of
speech, semantic group, rank, and an "Open in dictionary" button when the lemma
resolves.

Not in v1: reverse direction (English to Greek), typing answers, semantic-group
filtering, spaced repetition. These are listed in §12.

### 6a. Layout

The alphabet screen cannot be reused as is. It places two equal-width columns
side by side, every tile is a fixed 57dp tall with 37sp text, nothing scrolls,
and a round can have seven rows. On a phone each column is about 150dp wide,
so a 60-character definition would wrap to four or five lines and seven rows
would overflow the screen.

Measured from the DCC CSV (lemma derived by the rule in §5):

| Item | Value |
|---|---|
| Longest lemma | 11 characters |
| Definitions of 30 characters or fewer | 317 of 524 |
| 31 to 60 characters | 152 |
| 61 to 100 characters | 44 |
| Over 100 characters (longest 151) | 11 |

Proposed: a stacked layout.

- **Word chips on top.** Lemmas go in a wrapping flow row (`FlexboxLayout` on
  Android, `LazyVGrid` with adaptive columns on iOS). At about 24sp three or
  four chips fit per row, so a round of seven takes two rows. Chips keep the
  alphabet tile styling and colours: white, yellow when selected, green when
  matched.
- **Definition tiles below, full width.** One per row, height wraps the text,
  16sp, minimum height 48dp. Full width gives roughly 45 characters per line,
  so 317 definitions fit on one line, 152 on two, and 55 need three or four.
- **Only the game area scrolls.** Controls, points line and message text stay
  fixed; the chips and definitions sit in a `ScrollView`. Rounds of two to
  five fit without scrolling on a typical phone; a round of seven with several
  long definitions may need a short scroll.
- **Selection survives scrolling.** The selected chip stays highlighted while
  the learner scrolls to the definitions, so tap-word-then-tap-definition still
  works.
- **Principal parts stay off the chip.** The chip shows the lemma only. The full
  DCC headword, part of speech, group and rank are in the info sheet.

Rejected alternative: keep two columns with a 35/65 width split and wrapping
tiles. Rows of different heights no longer line up, the word column wastes most
of its space, and definition tiles still get only about 200dp.

`com.google.android.flexbox:flexbox:3.0.0` is already a dependency in
`app/build.gradle`, so no new library is needed. The
`item_vocabulary_word.xml` and `item_vocabulary_definition.xml` layouts in §8
use `wrap_content` height rather than the alphabet tiles' fixed 57dp.

## 7. Progress persistence

The alphabet game keeps nothing between launches, which is fine for 24 letters
but not for 524 words. V1 stores one thing: the set of mastered ranks per
language, as a JSON array in `SharedPreferences` (Android, via
`PreferencesManager`, which already stores JSON arrays for custom languages) and
`UserDefaults` (iOS). A "Reset progress" action clears it.

This deliberately avoids `UserDatabase`. If richer per-word statistics are
wanted later, they go in a new table created in `RoomDatabase.Callback.onOpen`
and accessed by a helper class, per the approved pattern in `CLAUDE.md`. No Room
entity or version changes under any variant.

## 8. Android implementation

New package `com.classicsviewer.app.vocabulary`:

| File | Purpose |
|---|---|
| `VocabularyData.kt` | `VocabularyEntry` and `VocabularySet` data classes; loads and caches `assets/vocabulary/greek_core_vocabulary.json`; exposes `availableLanguages`, `entries(language)`, `sets(language)` |
| `VocabularyGameActivity.kt` | the game, adapted from `AlphabetGameActivity` |
| `VocabularyProgress.kt` | mastered-rank persistence (§7) |

Resources: `activity_vocabulary_game.xml` (§6a layout), `item_vocabulary_word.xml`,
`item_vocabulary_definition.xml`, `menu/vocabulary_menu.xml` (Reset progress,
About), the `vocabulary_*` strings (§10), and the main menu item (§3).

Theme handling copies `applyTheme()` so inverted mode matches the rest of the app.

## 9. iOS implementation

Status: written 2026-09-26, not built (see §14).

| File | Purpose |
|---|---|
| `Views/PracticeVocabularyView.swift` | SwiftUI game, adapted from `PracticeAlphabetsView` |
| `Views/VocabularyData.swift` | loads the bundled JSON with `Codable` |
| `SettingsView.swift` | the new `NavigationLink` (§3) |

`ios/ClassicsViewer.xcodeproj/project.pbxproj` lists bundled resources
individually (`rhetoric.db.zip` has its own `PBXFileReference`), so the new JSON
needs a matching entry. Per project rules Claude edits Swift only and does not
regenerate or build the Xcode project; adding the resource reference is a
hand-off step for the user.

## 10. Licence and attribution

CC BY-SA 3.0 requires attribution and requires that adaptations of the list be
shared under the same licence. Proposed handling:

- An About entry on the game screen (Android overflow item, iOS toolbar button)
  with text modelled on `rhetoric_about_text`: source title, URL, the DCC
  editors, "Licensed under CC BY-SA 3.0", and the licence URL.
- The generated JSON carries the same notice in its header block, and
  `vocabulary/README.md` records the download date.
- The definitions are shipped verbatim. The only derived field is `lemma`,
  which is a substring of the headword.

The rhetoric precedent was CC BY 3.0 without ShareAlike. Whether bundling a
ShareAlike dataset inside this app is a "collection" (the app keeps its own
licence) or an "adaptation" (the derived JSON must itself be CC BY-SA, which
the header block satisfies) is a licensing judgement for the project owner, not
something this proposal settles.

## 11. Constraints honoured

- 100% offline: the JSON ships in the APK / app bundle. No download, no
  permission changes.
- No change to `perseus_texts.db`, Room entities, DAOs or database versions.
- No change to `data-sources/`.
- One repeatable build script, fails loudly on bad input, no manual edits to
  generated files. The only manual steps are committing the refreshed source CSV
  and the iOS project reference.
- Feature-scoped: the alphabet game is not modified.

## 12. Out of scope, possible later

- ~~Latin~~: added 2026-09-26, see §14.
- Filtering by semantic group or part of speech (both fields are already in the JSON).
- English-to-Greek direction, typed answers, audio.
- Spaced-repetition scheduling with per-word statistics (would use the
  `onOpen` dynamic-table pattern).
- A link from the reader: "this word is #37 in the core list".

## 13. Open questions for review

1. Set size of 25 (21 sets) versus 50 (11 sets). 25 keeps mastery reachable in
   one sitting; 50 means fewer steps through the list.
2. Should the word tile show only the lemma, or the lemma plus article for
   nouns (e.g. "λόγος, ὁ")? The article is in the DCC headword; extracting it
   is a second general rule.
3. Should the definition tile show the whole DCC definition, including embedded
   Greek examples such as "καί...καί both...and"? Verbatim is safest for
   accuracy; some tiles will be tall.
4. Whether to refresh the source CSV on a schedule or only on demand.
5. Licence question in §10.

## 14. Implementation record

### Done on Android (2026-09-24)

Data pipeline, all new, under `vocabulary/`:

| File | Status |
|---|---|
| `README.md` | source URL, retrieval date, licence, editors, refresh procedure |
| `sources/dcc_greek_core_list.csv` | the DCC export, committed unchanged |
| `build_vocabulary.py` | the one build script; run with `./venv/bin/python3 vocabulary/build_vocabulary.py` |
| `greek_core_vocabulary.json` | generated, committed (the tracked copy; see below) |
| `vocabulary_quality_report.txt` | generated |

Build script results on the committed source: 524 entries, rank 384 duplicated
and 385 unused, one headword normalised to NFC, 29 parts of speech, 28 groups,
5 definitions shared by two entries each. Dictionary coverage against
`perseus_texts_sample.db` is 522/524 with the coverage floor set at 95%.

The script copies the JSON to `app/src/main/assets/vocabulary/`,
`app/src/debug/assets/vocabulary/` and `ios/ClassicsViewer/Resources/`. The
Android assets directory is gitignored (as it is for `rhetoric.db.zip`), so a
fresh clone must run the build script once before the APK contains the file.
There is no Gradle check for it; the app throws on first open of the screen if
the asset is missing.

Android app, new files:

| File | Purpose |
|---|---|
| `app/src/main/java/com/classicsviewer/app/vocabulary/VocabularyData.kt` | `VocabularyEntry`, `VocabularySet`, JSON loader with cache, set chunking (25 per set plus "All") |
| `.../vocabulary/VocabularyProgress.kt` | mastered lemmas per language as a JSON array in SharedPreferences file `vocabulary_progress` |
| `.../vocabulary/VocabularyGameActivity.kt` | the game |
| `app/src/main/res/layout/activity_vocabulary_game.xml` | stacked layout per §6a |
| `app/src/main/res/layout/item_vocabulary_word.xml` | lemma chip, 24sp, wrap height |
| `app/src/main/res/layout/item_vocabulary_definition.xml` | full-width definition tile, 16sp, wrap height |
| `app/src/main/res/menu/vocabulary_menu.xml` | Reset progress, About |

Android app, edited files:

| File | Change |
|---|---|
| `app/src/main/res/menu/main_menu.xml` | `action_practice_vocabulary` directly after `action_practice_alphabets` |
| `app/src/main/java/com/classicsviewer/app/MainActivity.kt` | starts `VocabularyGameActivity` |
| `app/src/main/AndroidManifest.xml` | activity registered |
| `app/src/main/res/values/strings.xml` | `vocabulary_title`, `vocabulary_about_title`, `vocabulary_about_text`, `vocabulary_reset_progress`, `vocabulary_reset_confirm`, `vocabulary_open_dictionary` |

Behaviour as built:

- Spinners: Language (Greek only), Words per round (2–7, default 3), Set
  (Words 1–25 … Words 501–524, All 524 words; default 1–25).
- A round draws unmastered words first, then mastered, never two entries with
  the same definition text.
- Tap word then definition; wrong tap marks the round imperfect. Perfect round
  gives 10 points, imperfect 1. Points are per session.
- Words matched in a perfect round are recorded as mastered and persist.
  Header shows "Mastered N of M in this set". When every word in the set is
  mastered the points line gets stars and a gold flash. Changing set or
  language clears the star state; reopening a fully mastered set shows the
  stars again without the flash.
- Long-press a chip: dialog with full DCC headword, definition, part of speech,
  group, rank, and "Open in dictionary", which starts `DictionaryActivity`
  with extras `word`, `lemma`, `language`.
- Overflow menu: Reset progress (confirmation, clears mastered list and session
  points) and About (attribution text and CC BY-SA 3.0 link).
- Inverted-colour theme handled the same way as the alphabet game.

Verified: `./gradlew clean assembleDebug` succeeds with no warnings from the
new code; the APK contains `assets/vocabulary/greek_core_vocabulary.json` and
the four new resource files. Alphabet game source untouched.

Not verified: anything at runtime. No device was attached and no emulator is
installed on the build machine. The on-device checks below are outstanding.

### Latin added on Android (2026-09-26)

- `vocabulary/sources/dcc_latin_core_list.csv`: the DCC export
  (https://dcc.dickinson.edu/latin-core-list.csv), committed unchanged.
- `build_vocabulary.py` now builds every language in its `SOURCES` table. Changes
  that were needed for the Latin export, all general: case-insensitive header
  check; rows with an empty definition are excluded and listed in the report,
  with the build failing if they exceed 1% of rows (Latin has one, `fore`);
  the lemma rule also splits on `/` and strips trailing punctuation (`diū:`,
  `deinde/dein`); dictionary coverage is measured against the first of the
  sample and full DBs that has entries for the language, with macrons stripped
  for the lookup; duplicate headwords fail the build.
- Result: 996 Latin entries, 995/996 resolve in the full DB's Latin dictionary
  (`coepī` does not). Five lemmas are homographs of two entries each (adeō,
  adversus, eō, licet, mundus). Greek output is byte-for-byte unchanged.
- App: progress and on-screen tiles are keyed by headword, not lemma, because
  lemmas are no longer unique. A round never contains two entries with the
  same lemma. "Open in dictionary" passes the lemma with macrons removed, since
  the app's Latin dictionary headwords carry none and the repository does not
  strip them. Language spinner lists Greek and Latin. About text covers both
  lists.
- Licence verified 2026-09-26: https://dcc.dickinson.edu/vocab/core-vocabulary
  states CC BY-SA 3.0 Unported for both lists. The sample DB has no Latin
  dictionary, so on a sample-DB install
  "Open in dictionary" for a Latin word shows the app's existing
  "latin dictionary not available" message.

### iOS written (2026-09-26)

- `ios/ClassicsViewer/Views/VocabularyData.swift`: `VocabularyEntry`,
  `VocabularyList`, `VocabularySet`, the `Codable` loader with cache and
  duplicate-headword check, set chunking, and `VocabularyProgress` (mastered
  headwords per language as a string array in `UserDefaults`, key
  `vocabulary_mastered_<language>`).
- `ios/ClassicsViewer/Views/PracticeVocabularyView.swift`: the game, plus
  `VocabularyWordChip`, `VocabularyDefinitionTile`, `VocabularyEntryDetailView`
  (long-press sheet) and `VocabularyAboutView`. Same behaviour as Android:
  Greek and Latin, 2–7 words, 25-word sets plus All, unmastered-first draw,
  no duplicate definition or lemma in a round, 10/1 points, mastery star and
  glow, red flash on a wrong tile, a round token that cancels the 3-second
  restart when set, count or language changes, Reset progress with
  confirmation, About sheet. Stacked layout per §6a: chips in an adaptive
  `LazyVGrid`, full-width definition tiles, only the game area scrolls.
- `SettingsView.swift`: "Practice Vocabulary" link directly after "Practice
  Alphabets" in the Learning section.
- `ClassicsViewer.xcodeproj/project.pbxproj`: file references, group entries
  and build-phase entries added by hand for the two Swift files and the two
  JSON resources, mirroring the existing `PracticeAlphabetsView.swift` and
  `rhetoric.db.zip` entries. The project was not regenerated. `plutil -lint`
  passes and the three Swift files pass `swiftc -parse`.
- Not in the iOS version: "Open in dictionary". `ImprovedWordDetailView`
  requires a `ReaderViewModel` built from a `Book` and `Author`, which a
  standalone game cannot supply. The detail sheet shows headword, definition,
  part of speech, group and rank only.
- Not done: building or running the iOS app. Per project rules the user
  builds iOS. First checks: the Learning section shows the link; the screen
  opens; Latin appears in the language picker; a perfect round awards 10
  points and the "Mastered" line increments.

### Not done

- On-device verification of the iOS build (above).
- Open questions in §13 remain open; the implementation took the defaults
  stated there (25-word sets, lemma only on the chip, verbatim definitions).

## 15. Verification plan

1. Done: `vocabulary/build_vocabulary.py` reports 524 entries and 522/524
   dictionary coverage.
2. Done: debug APK built with `clean`. Outstanding: uninstall, clear data,
   install on a device:
   ```bash
   adb uninstall com.classicsviewer.app.debug
   adb shell pm clear com.classicsviewer.app.debug
   adb install app/build/outputs/apk/debug/app-debug.apk
   ```
3. Outstanding, on device: menu shows "Practice Vocabulary" directly under "Practice
   Alphabets"; the screen opens offline in airplane mode; a round of 3 from set
   1–25 completes; a perfect round awards 10 points; mastering set 1–25 shows
   the stars; progress survives force-stop and relaunch; "Reset progress"
   clears it; "Open in dictionary" on λόγος shows LSJ, Cunliffe and Wiktionary
   entries; inverted colours render correctly.
4. Outstanding: Practice Alphabets still behaves as before (source untouched,
   but check once on device).
5. Outstanding: iOS implementation, pbxproj resource step, user builds and
   repeats step 3.
