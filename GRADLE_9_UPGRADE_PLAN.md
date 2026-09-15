# Gradle 8.6 → 9.x — completion record

**Status (2026-09-12): the work is done and verified. The wrapper is still on
8.6 by choice.** Moving it is one line, proven below; it has not been applied
because that is a release decision, not a build fix.

This file replaces the plan written 2026-08-27. The plan's analysis was
useful; two of its central assumptions turned out to be wrong when measured,
and those are recorded here so they are not re-derived.

---

## 1. What was verified, by building

Every row below is a real build on this tree, not `./gradlew help`. AGP 8.3.0,
Kotlin 1.9.22 and Room 2.6.1 are unchanged throughout.

| Gradle | `clean assembleDebug` | `clean bundleRelease` | notes |
|---|---|---|---|
| 8.6 (current) | ✓ | ✓ | baseline, with the two changes in §2 applied |
| 8.14 (newest 8.x) | ✓ 49 s | ✓ 1 m 42 s | before the §2 changes — works even with kapt |
| 9.7.1 (newest 9.x) | ✓ 39 s | ✓ 1 m 41 s | **requires both §2 changes** |

For every successful build: `checkDatabaseExists`, `checkNoConcurrentDataBuild`
and `checkAabSize` ran; `copyFontToAssets`, `copyAudioToAssets` and
`copyReferencesToAssets` ran; the references manifest's mtime advanced (so
the exec really executed — see §5e of `AGP_9_MIGRATION_PLAN.md` for why that
matters); the AAB carried all four asset packs, a 3.71 MB release DEX, version
0.8.136, and the release keystore's signature.

The 9.7.1 debug APK was not installed; the 8.6 build of the same source was:
`adb uninstall` → `pm clear` → install → launch. Extracted DB byte-identical to
the sample build (663,887,872), Room opened both `perseus_texts.db` and
`user_data.db` (`-wal`/`-shm` present), no `Pre-packaged database`,
`EOFException` or `FATAL` in logcat.

---

## 2. What was changed

Two changes, both backward-compatible with Gradle 8.6 (verified — §1 row 1).

### 2.1 kapt → KSP, on the existing Kotlin

kapt processed exactly one thing, Room's annotation processor. KSP has a
release pinned to our Kotlin, so no Kotlin change was needed.

```
build.gradle          + id 'com.google.devtools.ksp' version '1.9.22-1.0.18' apply false
app/build.gradle:4    - id 'kotlin-kapt'            + id 'com.google.devtools.ksp'
app/build.gradle:106  - kapt 'androidx.room:...'    + ksp  'androidx.room:room-compiler:2.6.1'
```

No `kapt { }` block, no schema-export arguments, no other processors, and no
app code referencing generated `*_Impl` classes — so nothing else moved.

### 2.2 `exec { }` → injected `ExecOperations`

`Project.exec` is removed in Gradle 9. `copyReferencesToAssets` used it to run
`build_manifest.py`. Replaced with the injected service, declared at script
level with fully-qualified names so no `import` precedes `plugins {}`:

```groovy
interface ExecOps { @javax.inject.Inject org.gradle.process.ExecOperations getExecOperations() }
def execOps = objects.newInstance(ExecOps).execOperations
// in doLast:
execOps.exec { spec -> spec.workingDir = rootDir
                       spec.commandLine python, "$rootDir/references_pack/build_manifest.py" }
```

The task still throws if the manifest is not produced.

---

## 3. What the plan got wrong

Recorded because each one cost time and would again.

1. **AGP 8.3.0 was not the gate.** The plan's §1 made "does AGP 8.3.0 run on
   Gradle 9?" the question that decided everything. It runs. What failed on
   9.7.1 was **kapt in Kotlin 1.9.22**:
   `Could not create task ':app:kaptDebugKotlin' …
   Configuration.fileCollection(Spec)` — a Gradle API removed in 9.
2. **kapt → KSP does not require Kotlin 2.** Both plans coupled them. KSP
   `1.9.22-1.0.18` exists. Doing the swap alone, first, is what made Gradle 9
   reachable without K2 and without the golden-output harness.
3. **`buildDir` is deprecated in 9, not removed.** `delete rootProject.buildDir`
   (`build.gradle:9`) and `$buildDir` in `checkAabSize` (`app/build.gradle`)
   both ran on 9.7.1. The plan's §2.1 replacement is still good practice; it
   was not required.
4. **Eager `task foo { }` declarations produced no deprecation warning** from
   our files on 9.7.1 (`--warning-mode all`). The plan's §2.2 expected them to
   "warn loudly". Converting to `tasks.register` remains optional.
5. **The Groovy `List.execute()`** in `checkNoConcurrentDataBuild` (§2.4) works
   unchanged on 9.7.1.

---

## 4. What remains

- **The wrapper line**, if and when the upgrade is wanted:
  `gradle/wrapper/gradle-wrapper.properties` →
  `distributionUrl=https\://services.gradle.org/distributions/gradle-9.7.1-bin.zip`.
  Do not use `./gradlew wrapper` (it rewrites four files including a jar).
- **Eight Gradle-10 deprecations** in our files, all one kind — Groovy space
  assignment, which Gradle 10 will require as `=`. Mechanical:

  ```
  app/build.gradle:8   namespace 'com.classicsviewer.app'   → namespace = '…'
  app/build.gradle:9   compileSdk 36                         → compileSdk = 36
  app/build.gradle:37  minSdk 23                             → minSdk = 23
  app/build.gradle:38  targetSdk 36                          → targetSdk = 36
  app/build.gradle:59  shrinkResources true                  → shrinkResources = true
  app/build.gradle:62  signingConfig signingConfigs.release  → signingConfig = …
  app/build.gradle:74  viewBinding true                      → viewBinding = true
  app/build.gradle:75  buildConfig true                      → buildConfig = true
  ```

  Everything else `--warning-mode all` reports on 9.7.1 is inside AGP 8.3.0
  itself (`isCrunchPngs`, `isUseProguard`, multi-string dependency notation)
  and is not ours to fix.
- **Not done, deliberately:** the two guard tests the plan's §4 prescribes —
  rename the DB zip and confirm `checkDatabaseExists` fails; start a data
  build and confirm `checkNoConcurrentDataBuild` refuses. Both guards ran on
  every build above, but "ran" is not "still fails when it should". Do these
  before shipping a build from Gradle 9.

---

## 5. Sequencing, rollback

Never run Gradle while a database or interlinear build is in progress —
`ps aux | grep -E "python|interlinear|create_|assemble"` first. The Gradle
guard's pattern (`assemble_database\.py|run_build\.sh|create_.*_database\.py`)
does not match unrelated Python such as the lsgloss `package.py`; that is
correct, not a gap.

Rollback of the wrapper is the same one line back to `gradle-8.6-bin.zip`.
The §2 changes need no rollback: they build on 8.6.

---

## 6. Related work this unblocks — see `AGP_9_MIGRATION_PLAN.md`

- **Newest AGP 8.x (8.13.0)** requires Gradle ≥ 8.13 and JDK 17, supports
  API 36.1, and needs no Kotlin change. With Gradle 8.14 or 9.7.1 verified,
  this is the low-risk way to clear the "AGP 8.3.0 tested up to compileSdk 34"
  warning. Not yet attempted.
- **AGP 9.x** requires Gradle ≥ 9.6.0 (9.4.0 release notes) and JDK 17 — not
  21 as feared — but does require Kotlin 2 and therefore the golden-output
  harness. Unchanged in scope; no longer blocked on Gradle.

---

## 7. Decisions recorded

### 7.1 Keep Room; kapt → KSP only (decided 2026-08-27, executed 2026-09-12)

Room stays as it is, in both databases. The only change is replacing kapt
with KSP, now done (§2.1). Recorded so the reasoning does not have to be
rediscovered, and so the alternatives are on record as considered and
declined.

**What this deliberately does NOT solve.** The `PerseusDatabase` schema stays
frozen. Every rule in CLAUDE.md — never bump the version, never change
entities, add new tables only via raw SQL in `onOpen()` — remains in force,
because Room still validates the pre-packaged database against the entity
definitions. The "Pre-packaged database has an invalid schema" crash remains
possible.

**Alternatives considered and declined:**

| | why not |
|---|---|
| Remove Room from `PerseusDatabase` (9 read-only DAOs), keep it for user data | Would unfreeze the shipped schema, but costs ~90 queries rewritten as raw SQL with manual cursor mapping |
| Remove Room entirely | Hand-written migrations for bookmarks and imported dictionaries — real data-loss risk |
| SQLDelight | Trades one code-generating framework for another |

If the frozen-schema constraint later becomes the binding problem, the first
row is the one to revisit — iOS already reads this database with raw
`sqlite3_*` (`ios/ClassicsViewer/Database/DictionaryDAO.swift`), so the
access patterns are proven without Room.
