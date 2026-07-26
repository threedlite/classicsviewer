# Play Policy Audit — 2026-07-26

Record of running Google's `play-policy-insights` auditor against this repo, what it
found, what was fixed as a result, and what remains open.

**Scope note:** this tool is an automated advisory scanner. Its own disclaimer states it
does not constitute legal advice or a guarantee of Play Store approval, and that the
Google Play review team has final authority. Everything below is informational.

## The tool

| | |
|---|---|
| Source | `https://github.com/android/skills` → `play/play-policy-insights` |
| Author | Google LLC |
| Skill last-updated | 2026-07-13 |
| Domains audited | Permissions & APIs hygiene · User account & identity · Data safety & privacy |
| Protocol | Two phases: `orchestrator.py init` → per-goal workers → `aggregate` → critic → `generate_report.py` |

## How it was run

- **`app_dir` = `app/`, not the repo root.** The scanner's ignore list (`.git`, `build`,
  `.gradle`, `test`, `node_modules`, `ios`, …) does *not* exclude `data-sources/`,
  `data-prep/`, or `venv/`. Pointing it at the repo root would walk tens of thousands of
  Perseus XML files and contaminate findings with non-app code. Nothing policy-relevant
  lives in the root `gradle.properties` (only `useAndroidX`, `enableJetifier`, jvmargs,
  code style, `nonTransitiveRClass`).
- **Run from a scratch directory, not the repo.** `orchestrator.py` sets
  `workspace_root = os.getcwd()` and creates `.scratch/play_policy_insights_<uuid>/`
  there. Running it from inside the repo would litter the working tree.
- **Mode A (parallel delegation)**, subagents batched 3 at a time per the skill's
  concurrency limit.
- Python invoked via the repo `venv`.

## Known bug in the skill — Play Store validation silently skips

`orchestrator.py:460` extracts the package name from the manifest:

```python
details["package_name"] = root.get("package")
```

The `package` attribute was **removed from AndroidManifest.xml by AGP 7.0+** — it now
lives as `namespace` in `build.gradle`. This project correctly has no `package=`
attribute, so extraction yields `null` (as does `target_sdk`, which is also gradle-side).

Downstream in `generate_report.py`:

```python
680:  package_name = manifest_details.get("package_name")     # → None
688:  if not play_store_info and package_name:                # → guard fails
689:    play_store_info = run_scraper(package_name, temp_dir)  # never runs
```

The scraper is never invoked. There is no error and no warning — the report simply
declares *"App is not yet published. No declarations found for comparison"* and titles
itself `unknown`. **The tool's headline feature, comparing code behaviour against live
Play Store declarations, silently does not run.**

This is not specific to this project; it will mis-fire on any AGP 7+ app. Ironically
`orchestrator.py:37-46` already contains regexes that extract both `applicationId` and
`namespace` from gradle, and line 391 computes a `primary_id` from them — the value is
available, just not plumbed into `generate_report.py`.

**Workaround used:** after `init`, patch the generated
`<temp_dir>/manifest_details.json` with the real values read from `app/build.gradle`
(`package_name: "com.classicsviewer.app"`, `target_sdk: 36`), then run the report. The
scraper then executes natively. This is a manual patch of a generated scratch artifact
and must be repeated on every run until the skill is fixed upstream.

Once given a package name the scraper works correctly, returning:

```
is_published:    true          title:     Classics Viewer
developer:       threedliteguy category:  EDUCATION
content_rating:  Teen
data_safety:     data_collected: []   data_shared: []
privacy_policy:  github.com/threedlite/classicsviewer/blob/main/PRIVACY_POLICY.md
```

## Run 1 — against code as of commit `80be0ad`

7 goals activated. Status: 🟢 Compliant. Two findings, both Suggestion after critic review.

### 1. `READ_EXTERNAL_STORAGE` was dead state

Declared at `AndroidManifest.xml:6` with no `maxSdkVersion`, never requested at runtime
anywhere in `app/src`, and not grantable at all on API 33+. Because it is a dangerous
permission and `minSdk` is 23, it was never granted on *any* supported device. Its only
effect was adding a broad storage declaration to the Play listing.

The critic **downgraded this from Important to Suggestion**, correctly noting that the
Files and Docs declaration form is gated on `MANAGE_EXTERNAL_STORAGE` (absent here), so
this was manifest hygiene rather than an enforceable blocker.

### 2. `ObbDatabaseHelper` prefers legacy paths

`ObbDatabaseHelper.kt:32` and `:34` probe `Environment.getExternalStorageDirectory()` and
a hardcoded `/sdcard/Android/obb/...` before the scoped `context.obbDir` at `:36`.
`getObbDirectoryPath()` at `:175` also returns a literal `/sdcard` string for display.
Read-only, confined to the app's own OBB directory, so not a shared-storage violation —
but deprecated and unreliable under scoped storage, and wrong on multi-user and
non-emulated-storage devices.

### Critic caught a worker overclaim

The worker asserted all file access was already SAF-scoped. The critic rejected that and
identified two remaining direct-`File` paths: the bookmarks CSV export at
`PerseusDatabase.kt:223` and the OBB probing above. Neither was enabled by the declared
permission, so removing it did not regress them.

### Incidental discovery — a functional bug

`PerseusDatabase.tryExportBookmarks()` wrote the rescue CSV straight to public Downloads
via `Environment.getExternalStoragePublicDirectory()`. That needs `WRITE_EXTERNAL_STORAGE`
below API 29 and is blocked by scoped storage from 29 on, and the app requests no storage
permission at runtime — so **it could never succeed on any supported device**. The
exception was swallowed by a `catch`, returning `null` silently.

This ran on the database-failure path, immediately before `DatabaseErrorActivity` tells
the user to uninstall and reinstall — which destroys `user_data.db` where bookmarks live.
Auto Backup does not rescue them either: `backup_rules.xml` and `data_extraction_rules.xml`
both `<exclude domain="database" path="."/>`.

Users were not falsely reassured — with `backupPath` null the message collapses to the
plain "Please uninstall and reinstall the app." branch — but no backup was ever produced.

## Changes made between runs

| Change | File |
|---|---|
| Removed `READ_EXTERNAL_STORAGE`; app now declares **zero** permissions | `AndroidManifest.xml` |
| Removed the bookmarks rescue export entirely (`tryExportBookmarks`, its private `escapeCSV`, the call site, the `backup_path` extra) | `PerseusDatabase.kt` |
| Removed the `backup_path` branch from the error message | `DatabaseErrorActivity.kt` |
| Permissions section rewritten to match | `PRIVACY_POLICY.md` |

The rescue was removed by product decision rather than repaired. `BookmarksActivity`'s
user-facing SAF export/import (`CreateDocument` / `OpenDocument`) is a separate
implementation and was untouched.

## Run 2 — after those changes

Only **6 goals activated** — `permissions_and_apis` no longer triggers, as there are no
app-declared permissions left to audit. `aggregate` returned `critic_chunks: 0`.

Status: 🟢 Compliant. **No policy risks identified.**

### Data Safety comparison (ran properly this time)

| Data Type | Code Detection | Play Declaration | Status |
|---|---|---|---|
| Files and docs | Detected | Not declared | Exempt: Obvious core functionality |

This run's evidence names the exemption case explicitly, which Run 1 did not:

> *"a user-selected app via a chooser is a Third Party and this is on-device transfer, but
> it fires only when the user taps 'Open' on the Snackbar, so user_initiated is true
> **(Case 4)**."*

Case 4 in the skill's matrix is *"Manual Sharing: Policy Exempt. User triggers transfer to
3P; no disclosure or declaration needed."* So the `Files and docs` entry the report
suggests is **advisory, not required**, and the currently-empty Data Safety label is
consistent with the code.

This matters because the report's `"Exempt: Obvious core functionality"` label is
generated whenever `prominent_disclosure_status` contains "Exempt"
(`generate_report.py:522-534`), flattening three different cases — one of which (Case 3)
*does* still require a form declaration. The label alone does not tell you which.

### Verified clean

Forward-tracing confirmed no `INTERNET` permission in any manifest, no HTTP client, no
analytics / ads / crash-reporting SDK, and no egress path for bookmark notes, audio, or
filenames. A long list of pattern false positives was cleared: "gender" (grammatical, in
license text), "race" (`printStackTrace`), "uid" (`Guideline` widgets), "position"
(ExoPlayer playback offset), "record" (`recordCount` in a binary parser).


## Reproducing

```bash
# from a scratch directory, NOT the repo
git clone --depth 1 https://github.com/android/skills.git
PPI=skills/play/play-policy-insights

python3 $PPI/scripts/orchestrator.py init /path/to/classicsviewer/app
# → prints temp_dir and activated_goals

# REQUIRED WORKAROUND: orchestrator leaves these null on AGP 7+
#   patch <temp_dir>/manifest_details.json with
#   package_name = com.classicsviewer.app, target_sdk = 36

# for each goal: run prompt_worker_<goal>.md, write worker_<goal>.json
python3 $PPI/scripts/orchestrator.py aggregate <temp_dir>
# for each critic chunk: run prompt_critic_<i>.md, write critic_output_<i>.json
python3 $PPI/scripts/generate_report.py <temp_dir>
# → <temp_dir>/compliance_report.md
```
