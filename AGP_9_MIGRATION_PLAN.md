# AGP 8.3.0 → 9.x migration plan

**Gradle is no longer a prerequisite.** `GRADLE_9_UPGRADE_PLAN.md` is now a
completion record: Gradle 9.7.1 builds this project (debug and release,
verified 2026-09-12) with AGP 8.3.0 and Kotlin 1.9.22 unchanged, after two
changes — kapt → KSP on the existing Kotlin, and `exec {}` → `ExecOperations`.
Both are in the tree. The wrapper itself is still 8.6 by choice.

Written 2026-08-27; corrected 2026-09-12 where measurement contradicted it.
Current state:

| | now | target |
|---|---|---|
| Gradle | 8.6 (8.14 and 9.7.1 both verified) | ≥ 9.6.0 for AGP 9.4 |
| AGP | 8.3.0 | 9.4.0 (newest, checked 2026-09-12; requires Gradle ≥ 9.6.0) |
| Kotlin | 1.9.22 | 2.4.10 (newest stable, checked 2026-08-27 — re-check at the time) |
| Annotation processing | **KSP 1.9.22-1.0.18 — done** | KSP pinned to whatever Kotlin 2.x lands |
| JDK | Temurin 17.0.18 | **17** — AGP 9.4.0 release notes list JDK 17 minimum and default; no move needed |
| Room | 2.6.1 | **unchanged** — see §6 |
| Codebase | 132 Kotlin files, 24,640 lines, 0 Java, no Compose | |

**The lower-risk alternative, recorded here because it now exists:** the
newest AGP 8.x (8.13.0) requires Gradle ≥ 8.13 and JDK 17, supports API 36.1,
and needs no Kotlin change. It would clear the "AGP 8.3.0 tested up to
compileSdk 34" warning without any of the K2 risk in §1. Not yet attempted.

---

## 1. The actual risk is behavioural, not syntactic

This is the part that matters and it should be read before anything else.

Kotlin 2.x replaces the compiler frontend (K1 → K2). Most write-ups frame this
as a compile-error exercise: build, fix what the compiler rejects, done. **That
framing is wrong for this project**, because K2 also changes decisions the
compiler makes silently:

- **Overload resolution.** Where two overloads were both applicable, K2 may pick
  a different one. Compiles clean, calls different code.
- **SAM conversion.** Changed in 2.0; affects which functional-interface
  implementation is produced.
- **Generic type inference.** Inferring a different type parameter can change
  which extension function applies.
- **Platform types from Java interop.** Every Android framework call returns a
  platform type (`String!`, `View!`). K2 propagates nullability through these
  differently in some positions. This codebase is 132 Kotlin files calling
  Android APIs constantly — it is entirely platform-type interop.

None of these produce an error. They produce working code that behaves
differently.

### 1.1 There are no tests

```
app/src/test        0 files
app/src/androidTest 0 files
```

`junit`, `androidx.test.ext:junit` and `espresso-core` are declared in
`app/build.gradle:134-136` and unused. So there is **no automated safety net at
all**, and the compiler — the one check that does exist — is blind to exactly
the class of change described above.

This single fact should drive the shape of the migration.

### 1.2 Honest statement of the risk

I cannot tell you the probability that K2 changes behaviour in this codebase.
The mechanisms in §1 are real and documented, but whether any of them fire here
depends on specifics no amount of reading the source will settle — you find out
by compiling with K2 and comparing.

An earlier draft of this section argued that the comparators below were likely
to break, on the grounds that they are complex. That was reasoning backwards
from the scariest-looking code. `compareBy(vararg selectors: (T) ->
Comparable<*>?)` has one applicable overload and the selector lambdas return
`Int`, `Double` and `String` — all unambiguously `Comparable`. There is no
obvious ambiguity for K2 to resolve differently.

The case for verification does not rest on that. It rests on:

- behaviour changes here produce a **green build**, so the compiler cannot tell
  you whether they happened;
- there are **no tests** (§1.1), so nothing else can either;
- the affected output is **which definition a reader sees**, which is the
  product, not an implementation detail.

Under those three conditions, "probably fine" is not something that can be
established by inspection. It has to be measured.

### 1.3 The most consequential site

`PerseusRepository.kt:963` and `:1138` — multi-selector comparators:

```kotlin
val sortedEntries = deduplicatedEntries.sortedWith(compareBy(
    { entry -> if (entry.hasNonTreebankPath) 0 else 1000 },
    { entry -> /* Int penalty derived from regex over a nullable String */ },
    { entry -> /* source rank */ },
    { entry -> -(entry.confidence ?: 0.0) },   // Double
    { entry -> entry.lemma.length },            // Int
    { entry -> entry.lemma }                    // String
))
```

Six selector lambdas returning `Int`, `Double` and `String`, over a `compareBy`
overload set, with nullable handling inside. This is precisely the shape where
inference and overload resolution differ between K1 and K2 — and its output
decides **which definition a user sees for a word**. A silent reordering here
would not crash, would not warn, and would not be noticed without looking.

11 sort sites in total; these two are the consequential ones.

---

## 2. Verification strategy — golden output

Because §1.1 leaves nothing to rely on, the migration must carry its own
verification. The property that makes this cheap: **dictionary lookup is
deterministic for a fixed database.** Same word, same DB, same result — so a
recording made today is a valid reference for any future build.

This is the same technique that has repeatedly proved decisive in this project's
data work: the Greek interlinear XMLs were backed up before regeneration and
diffed afterwards, showing 4 changed files out of 1,993; the Latin XMLs were
diffed to prove a set of loader fixes were behaviour-neutral; the released
database was extracted and compared to establish what had actually changed. In
every case the conclusion came from a recorded baseline, not from reading the
code.

The harness is worth building on its own merits. This project has 24,640 lines
of Kotlin and zero tests; a golden comparison over dictionary lookup would be
the first thing standing between a code change and a reader seeing the wrong
definition. AGP is the occasion, not the justification.

**Before touching anything**, capture golden output:

1. Pick the word list by corpus frequency, straight from the database:

   ```sql
   SELECT wd.word, a.language, COUNT(*) n FROM words wd
     JOIN books bk ON wd.book_id=bk.id
     JOIN works wk ON bk.work_id=wk.id
     JOIN authors a ON wk.author_id=a.id
   GROUP BY wd.word, a.language ORDER BY n DESC LIMIT 2000;
   ```

   Take the top 2,000 per language, then add these specifically, because each
   has a known-awkward resolution path found during the Latin gloss work:

   `est esse sunt sit erat fuit iam tibi vos se sibi me multum multa vi ora
    res rem an causa qui quae quid` (Latin)
   `ἄν ἐν ποιῶν ἰών εἰμί ἐπαΐοντος` (Greek — the ultra-normalisation
   collisions)
2. Run each through `PerseusRepository.getAllDictionaryEntries` and record the
   **full ordered result**: lemma, source, definition prefix, for every entry —
   not just the first. Ordering is the thing at risk.
3. Store as a file.

Repeat after migration and diff. Any difference is a behaviour change to be
explained before proceeding — not assumed benign.

The harness is an instrumented test (`androidTest`), because it needs a real
database on a device. It is also, not incidentally, the first test this project
would have.

**A second, cheaper cross-check exists.** The interlinear generator's Python
lookup (`greek/build_modules/generate_interlinear/ui_dictionary_lookup.py`,
`latin/build_modules/interlinear/latin_dictionary_lookup.py`) mirrors the Kotlin
ranking. Divergence between the Kotlin golden output and the Python ordering is
a signal, though the two are not line-for-line equivalent.

---

## 3. Order of work

Four separable steps. Each ends verifiable; do not batch.

1. **JDK — no move needed.** AGP 9.4.0's release notes list JDK 17 as both
   minimum and default (verified 2026-09-12); Temurin 17.0.18 is installed.
   Re-read the notes for whichever AGP 9.x is chosen at the time, since a
   later release could raise it.
2. **Capture golden output** (§2) while still on Kotlin 1.9.22. This is the
   baseline and cannot be recreated afterwards.
3. **Kotlin 1.9.22 → 2.x.** kapt → KSP is already done on 1.9.22 (KSP
   `1.9.22-1.0.18`), so this step is Kotlin plus the KSP version pin
   (`2.x.y-…` form) and nothing about kapt. Coroutines 1.7.3, Lifecycle 2.7.0
   and core-ktx 1.12.0 are 1.9-era and realistically move too.
   Concrete targets to resolve at the time (all are 1.9-era today):

   | | now | note |
   |---|---|---|
   | Kotlin | 1.9.22 | → 2.4.10 |
   | KSP | 1.9.22-1.0.18 (done) | must match Kotlin exactly, `2.4.10-x.y.z` form |
   | coroutines-android | 1.7.3 | compiled against a Kotlin version; mismatches give unhelpful metadata errors |
   | lifecycle-runtime-ktx | 2.7.0 | |
   | core-ktx | 1.12.0 | |
   | appcompat | 1.6.1 | |
   | room | 2.6.1 | **stays** — §6 |

   **Then re-run the golden comparison.**
4. **AGP 8.3.0 → 9.3.2.** Build-system only by this point. Re-run the golden
   comparison again; it should be untouched, and any diff here is a surprise
   worth stopping for.

Going to the newest 9.x rather than 9.0.0: many stable 9.x releases exist, and
landing on the minimum means doing this again shortly. Whichever is chosen,
check its minimum Gradle (9.4.0 wants ≥ 9.6.0) against the wrapper.

---

## 4. kapt → KSP — done (2026-09-12)

Done on Kotlin 1.9.22 with KSP `1.9.22-1.0.18`, independently of this
migration; see `GRADLE_9_UPGRADE_PLAN.md` §2.1. Verified by clean debug and
release builds and a device install: Room opened both pre-packaged and user
databases with no schema-validation crash.

What remains for this plan is only the version pin: when Kotlin moves, the KSP
plugin version must move to the matching `2.x.y-…` release.

---

## 4a. AGP DSL changes present in this build

Scanned across `app/build.gradle` and the four asset-pack modules. Two blocks
were renamed in AGP 8.0, deprecated since, and are removed in 9.

### `aaptOptions` → `androidResources` — **functional, not cosmetic**

```groovy
// app/build.gradle:84
aaptOptions {
    noCompress 'db', 'zip'
}
```

This is what stops the packager compressing `perseus_texts.db.zip` a second
time. Renamed form:

```groovy
androidResources {
    noCompress += ['db', 'zip']
}
```

**If this silently stops applying, the failure is not a build error.** The APK
still builds; the database asset gets re-compressed; extraction behaviour and
APK size both change. Verify after migrating by comparing the packaged asset's
stored size against the source zip — equal means uncompressed, smaller means the
setting was lost.

### `packagingOptions` → `packaging` — empty, delete it

```groovy
// app/build.gradle:79
packagingOptions {
    // Database files are now included directly
}
```

Contains only a comment. Delete rather than rename.

### Already satisfied

- `namespace 'com.classicsviewer.app'` is set (`:8`) — required since AGP 8
- `buildFeatures { buildConfig true }` is set (`:75`) — required since AGP 8 for
  the three `buildConfigField` calls
- `viewBinding true` — unaffected
- No `dexOptions`, `lintOptions`, `adbOptions`, `renderscript`, `splits`, or
  Transform API usage
- `compileSdk 36` / `targetSdk 36` — no bump needed
- The four asset-pack modules are four lines each; nothing to change

### Noted, not scheduled

```groovy
// app/build.gradle:45
buildConfigField "String", "BUILD_TIME", "\"${new Date().format(...)}\""
```

Evaluates `new Date()` at configuration time, so every build differs and the
result is not reproducible. It also blocks the Gradle configuration cache. Not
an AGP 9 blocker; worth removing whenever build reproducibility matters.

---

## 5. What must not break

**Room schema validation.** The pre-packaged database is validated against
entity definitions at open time; a mismatch is an immediate crash on launch
("Pre-packaged database has an invalid schema"). Nothing in this plan changes
entities or the Room version — if that crash appears, something was changed that
should not have been. Test with `adb uninstall` + `pm clear` + install, never an
in-place upgrade, which can mask it.

**Dictionary entry ordering.** §1.2. Golden comparison is the check.

**Age verification.** Release-only and Play-dependent, so it cannot be exercised
in a debug build at all. AGP and Kotlin changes touch the code path around it.
Per CLAUDE.md this outranks everything including offline operation, so it needs a
real release build installed through Play before shipping.

**Asset packs.** Four on-demand packs. `bundleRelease` must still produce all
four — verify the AAB contents, not merely that it builds.

**The build guards.** `checkDatabaseExists` and `checkNoConcurrentDataBuild`
must still fail the build; test by breaking them deliberately.

---

## 5a. The release artifact is the AAB, and it is the untested one

**The APK is a local testing convenience. What ships is the AAB.** That
distinction drives this whole section, because the two differ in ways that
matter:

| | debug APK | release AAB |
|---|---|---|
| minification | off | **`minifyEnabled true`, `shrinkResources true`** |
| R8 | not run | **run** |
| asset packs | bundled into assets | **four Play Asset Delivery packs** |
| age verification | bypassed entirely | **active** |
| signing | debug key | release keystore |

Everything in §3 verifies with `assembleDebug`, which exercises none of the
right-hand column.

### R8 — measured 2026-09-12

The release AAB built with R8 on (`minifyEnabled true`, `shrinkResources true`,
`proguard-android-optimize.txt`, full mode by default) carries a **3.71 MB**
release DEX in one file, down from 23.65 MB unminified, with a 328,855-line
mapping file. Play's February 2027 DEX-optimization requirement applies only
above 10 MB of DEX, so it does not apply here — see
`support.google.com/googleplay/android-developer/answer/17492799`.

AGP 9 ships a newer R8. When R8 strips something still needed, the symptom is a
`ClassNotFoundException`, a missing method, or a silently-null field — at
runtime, in the release artifact only. Exposure here is concrete: 58 lines of
`proguard-rules.pro`, and 51 reflection / `::class.java` sites in the Kotlin.
The existing `-keep class com.classicsviewer.app.models.**` rule indicates this
has bitten before.

### Asset packs cannot be tested from an APK at all

The four `com.android.asset-pack` modules — `full_database_pack`, `audio_pack`,
`references_pack`, `topical_pack` — exist only in a bundle. An APK build cannot
carry Play Asset Delivery packs, so "the debug build works" says nothing about
whether delivery still functions.

### How to actually test it

The repo already has the path; use it rather than inventing one:

```bash
./build_release_aab.sh          # -> app/build/outputs/bundle/release/app-release.aab
./deploy_with_bundletool.sh     # bundletool build-apks + install-apks
```

`deploy_with_bundletool.sh` runs `bundletool build-apks` and `install-apks`,
which is the closest local simulation of what Play does — it splits the bundle
and installs the result, exercising the asset packs.

**Age verification still cannot be fully tested this way.** Per CLAUDE.md it
depends on the Play Age Signals API and only behaves correctly for a build
installed *through Play*. A bundletool install is not that. It outranks
everything including offline operation, so a Play internal-track release is the
only real test.

### Consequence for the golden comparison

Run it against the **bundletool-installed release build**, not only the debug
build. If debug and release disagree, R8 is the difference, and that is a
finding rather than noise.

## 5b. There is no CI

No `.github/workflows`, no pipeline. Every check in this plan is manual and
nothing enforces that any of them ran. This is not an argument for adding CI
during a migration — it is a warning that "the plan says to verify X" and "X was
verified" are separate facts here, and only the second one matters.

Keep a written record of which checks were actually run.

## 5c. Signing

`signingConfigs.release` reads a keystore path from `keystoreProperties`
(`app/build.gradle:24-29`), which comes from a properties file outside version
control. If that file is absent or the resolution changes, `bundleRelease` fails
in a way that resembles a migration fault and is not one. Confirm the release
build works **before** starting, so a later failure is attributable.

## 5d. What to do when the golden diff is not empty

A difference is not automatically a regression — several changes during the
Latin gloss work were improvements. The rule is:

1. Every differing entry gets a cause. Not a category, a cause: which change
   produced it and by what mechanism.
2. A difference with no explanation blocks the migration. "Looks fine" is not an
   explanation; it is the absence of one.
3. Only once every difference is explained is the result accepted — and the new
   output becomes the baseline for the next step.

An empty diff is the expected result. This migration is build tooling; it has no
business changing what a reader sees.

---

## 5e. Asset copies land in the SOURCE tree — stale files survive `clean`

Several Gradle tasks copy files **into `app/src/…/assets/`**, not into `build/`:

| task | copies into |
|---|---|
| `copyFontToAssets` | `src/debug/assets/fonts/`, `src/main/assets/fonts/` |
| `copyAudioToAssets` | `src/debug/assets/`, `src/main/assets/` |
| `copyReferencesToAssets` | `src/debug/assets/references/` |
| `checkTopicalAssets` | verifies `src/debug/assets/topical/` |

The data build also writes `perseus_texts.db.zip` into both asset directories,
and the assembly copies the extended zip into
`ios/ClassicsViewer/Resources/OnDemand/`.

**`./gradlew clean` deletes `build/` only. It does not touch `src/`.** So every
one of these files persists across a clean build. What is in the tree today:

```
app/src/main/assets/perseus_texts.db.zip          2026-05-30
app/src/main/assets/rhetoric.db.zip               2026-05-17
app/src/main/assets/homer_iliad_chamberlain_audio_7.zip  2026-07-26
app/src/debug/assets/references/*.pdf             2026-07-26
```

The database asset is three months old and matches the released build's date.

### Why this matters for the migration

If a path resolution changes (`buildDir` → `layout.buildDirectory` — optional, since `buildDir`
still works on Gradle 9.7.1; `GRADLE_9_UPGRADE_PLAN.md` §3) or a task stops firing after conversion to `tasks.register`, the
copy silently does not happen — **and the previous file is still sitting there**.
The build succeeds. The APK or AAB is assembled. It contains the old asset.

There is no error, no warning, and no missing-file failure, because the file is
not missing. It is merely wrong. This is the same failure shape as the silent
build defects found in the data pipeline: a green build carrying stale data.

### How to verify

Do not rely on the build passing. Before and after each migration step:

```bash
find app/src/debug/assets app/src/main/assets -type f \
     -exec stat -f '%Sm %N' -t '%Y-%m-%d %H:%M' {} \; | sort
find ios/ClassicsViewer/Resources -name "*.zip" \
     -exec stat -f '%Sm %N' -t '%Y-%m-%d %H:%M' {} \;
```

A file whose timestamp did **not** advance after a build that should have
rewritten it is the signal. Checking existence proves nothing.

**Stronger check for the destructive case:** delete the copied assets, build,
and confirm they are recreated. That distinguishes "the task ran" from "the file
happened to already be there". Do this deliberately rather than trusting it —
but note the database zips are large and are not regenerated by Gradle, so
delete only the files the Gradle tasks own (fonts, audio, references, topical).

---

## 5f. Dependency compatibility — nothing currently checks it

There is **no version catalog, no BOM, and no dependency locking**. All 21
dependencies are hand-pinned strings in `app/build.gradle`. Nothing verifies
they are mutually consistent; the only evidence that they are is that the
project builds today.

That is adequate while nothing moves. It stops being adequate the moment Kotlin
changes, because several of these are compiled *against* a Kotlin version.

### Hard constraints — these must move together

| | current | constraint |
|---|---|---|
| Kotlin | 1.9.22 | → 2.4.10 |
| KSP | 1.9.22-1.0.18 (done) | **exact pin** to Kotlin: `2.4.10-x.y.z`. Cannot be chosen independently |
| kotlinx-coroutines-android | 1.7.3 | 1.7.x is Kotlin-1.9 era. Compiled against Kotlin; a metadata mismatch is reported as an obscure error, not a clear one |
| Room | 2.6.1 | KSP support exists at 2.6.1, but Kotlin-2 support landed in later releases — **verify before assuming 2.6.1 is viable**, and note §6 says Room otherwise stays |

### Soft constraints — AndroidX, mixed vintages

```
core-ktx 1.12.0    appcompat 1.6.1    lifecycle-runtime-ktx 2.7.0
activity-ktx 1.8.0 recyclerview 1.3.2 constraintlayout 2.1.4
```

These are 2023-era and generally forward-compatible with a newer Kotlin.
Alongside them sit much newer artifacts — `material 1.12.0`,
`media3 1.9.0`, `asset-delivery 2.3.0` — so the set spans several years. Mixed
vintage is not itself a fault, but it means "it resolved" is doing more work
than usual.

### `age-signals` — must always be the newest published version

```groovy
implementation 'com.google.android.play:age-signals:0.0.4'   // app/build.gradle:132
```

**Standing rule: this dependency tracks latest, always.** It is the library
behind age verification, which CLAUDE.md places above every other concern
including offline operation. Google ships behaviour and signal changes through
it, so a stale version is the risk — an update is not.

This inverts the normal caution about pre-1.0 dependencies. The `0.0.x` version
number is not a reason to hold back here; it reflects where the library is in
its own lifecycle, not whether we should be on it.

**Check at the start of any build work, not only during a migration:**

```bash
curl -s https://dl.google.com/dl/android/maven2/com/google/android/play/age-signals/maven-metadata.xml \
  | grep -oE "<release>[^<]*</release>"
```

Checked 2026-08-27 and again 2026-09-12: `<release>` is **0.0.4**, which is
what we are on. No action needed today.

If it does move, the change cannot be verified in a debug build — age
verification is release-only and Play-dependent (§5a), so it needs a Play
internal-track release.

### What can actually be checked, and how

Static inspection cannot establish this; the Kotlin metadata version of a
published artifact is not readable without resolving it. The checks that do work:

```bash
./gradlew app:dependencies                 # full resolved graph, conflicts, forced versions
./gradlew app:dependencyInsight --dependency kotlin-stdlib
```

The second is the one that matters after a Kotlin bump: it shows which version
of `kotlin-stdlib` every dependency drags in, and whether anything is forcing an
older one.

**Recommendation, not scheduled here:** move the 21 strings into a version
catalog (`gradle/libs.versions.toml`). It does not validate compatibility, but it
puts every version in one file, which makes a coordinated bump reviewable
instead of a scatter of edits across a 400-line build file. Worth doing before
the migration rather than during it.

---

## 6. Room stays

Decision recorded in `GRADLE_9_UPGRADE_PLAN.md` §7.1: Room is kept in both
databases; the kapt → KSP part of that decision has been executed.

This deliberately leaves the `PerseusDatabase` schema frozen. Every CLAUDE.md
constraint — never bump the version, never change entities, add tables only via
raw SQL in `onOpen()` — remains in force.

---

## 7. Sequencing and rollback

**Never run Gradle while a database or interlinear build is in progress.** Check
first:

```bash
ps aux | grep -E "python|interlinear|create_|assemble" | grep -v grep
```

Rollback is per-step, which is why the steps are separated. Take a source
checkpoint before each. Reverting Kotlin means reverting the dependency block
too, not just the plugin version.

---

## 8. Effort

The syntax work is small — 132 files, no Java, no Compose, 25 `!!` and 14 casts
where K2 may object, all surfaced by the compiler.

**The verification work is the migration.** Building the golden-output harness
is most of the cost, and it is not optional: without it, a silent reordering in
`PerseusRepository` ships unnoticed and the first report is a user saying a word
shows the wrong definition.

Budget for the harness first, the migration second.
