# Build Guide for Classics Viewer

Step-by-step instructions to build and run Classics Viewer from a fresh clone.

## Prerequisites

Before starting, ensure you have:

- **Git** - for cloning repositories
- **Python 3.13+** - for database creation (cltk 2.x requires 3.13+)
- **Java 17+** - required for Gradle/Android builds (JDK, not just JRE)
  - macOS: `brew install openjdk@17` or install from [Adoptium](https://adoptium.net/)
  - Verify with: `java -version`
- **Android SDK** - Install via one of these methods:
  - **Android Studio** (recommended): Download from [developer.android.com](https://developer.android.com/studio)
  - **Command-line tools only**: Download from [Android SDK](https://developer.android.com/studio#command-tools)
  - After installation, set `ANDROID_HOME` environment variable or create `local.properties`:
    ```bash
    # Option 1: Set environment variable (add to ~/.zshrc or ~/.bashrc)
    export ANDROID_HOME=$HOME/Library/Android/sdk  # macOS default
    export PATH=$PATH:$ANDROID_HOME/platform-tools

    # Option 2: Create local.properties in project root
    echo "sdk.dir=$HOME/Library/Android/sdk" > local.properties
    ```
- **Android device or emulator** - Android 5.0+ (API 21+)
- **~15GB free disk space** - for data sources, build artifacts, and optional OGA corpus

## Step 1: Clone the Repository

```bash
git clone https://github.com/threedlite/classicsviewer.git
cd classicsviewer
```

## Step 2: Clone Data Sources

⚠ **IMPORTANT: ALL data sources in this step must be cloned, downloaded, and extracted BEFORE starting any builds in Steps 5-7.** Module builds will fail or produce incomplete/empty databases if their required data sources are missing. Complete this entire step first.

The app requires several upstream repositories containing classical texts and dictionaries.

```bash
cd data-sources

# Required for sample/full database (Greek and Latin texts)
git clone https://github.com/PerseusDL/canonical-greekLit.git
git clone https://github.com/PerseusDL/canonical-latinLit.git
git clone https://github.com/PerseusDL/canonical-pdlrefwk.git
git clone https://github.com/PerseusDL/perseus_catalog.git

# Required for Latin dictionary
git clone https://github.com/mk270/whitakers-words.git

# Required for lemma mappings
git clone https://github.com/PerseusDL/treebank_data.git

cd ..
```

**Extract included dictionaries:**
```bash
cd data-sources

# Extract Cunliffe Homeric dictionary (included as reference file)
unzip -o cunliffe.zip.reference

cd ..
```

**Required for extended database** (778 authors, 14 languages):

```bash
cd data-sources

# First1KGreek corpus (300+ additional Greek authors, ~1.7GB) - REQUIRED for extended
git clone https://github.com/OpenGreekAndLatin/First1KGreek.git

# Patristic Text Archive (Greek church fathers, ~170MB) - REQUIRED for extended
git clone https://github.com/PatristicTextArchive/pta_data.git

cd ..
```

**Required for language module builds** (extended mode):
```bash
cd data-sources
# Hebrew Bible and lexicon - REQUIRED for Hebrew module
git clone https://github.com/openscriptures/morphhb.git
git clone https://github.com/openscriptures/HebrewLexicon.git
# Coptic texts (~1.2GB) - REQUIRED for Coptic module
git clone https://github.com/CopticScriptorium/corpora.git
# Sanskrit DCS corpus (~3GB) - REQUIRED for Sanskrit module (treebank + dictionary + CoNLL-U)
git clone https://github.com/OliverHellwig/sanskrit.git
# Persian texts - REQUIRED for Persian module (Hafez Divan)
git clone https://github.com/PerseusDL/canonical-farsiLit.git
cd ..
```

The following repo is cloned but not currently processed by the database build (future support):
```bash
cd data-sources
# Arabic texts (Arabic module uses bundled data in arabic/data-sources/ instead)
git clone https://github.com/cltk/arabic_text_perseus.git
cd ..
```

**Required** - OGA corpus for Greek lemma coverage (8.6GB download):

⚠ **The OGA corpus must be downloaded and extracted before building the Greek module (Step 6).** The Greek module build depends on OGA lemma data; it cannot start without it.

```bash
cd data-sources

# Opera Graeca Adnotata corpus - provides 268K Greek lemma mappings
curl -L -O https://zenodo.org/records/14206061/files/opera_graeca_adnotata_v0.2.0.zip

# ⚠ ZIP64 format (7.8 GB) — standard `unzip` WILL FAIL. Use ditto (macOS) or 7z (Linux):
ditto -x -k opera_graeca_adnotata_v0.2.0.zip .
# Verify: ls opera_graeca_adnotata_v0.2.0/workspace/oga.zip

cd ..
```
If you skip this download, add `--skip-oga` to the database assembly command in Step 7 — but the resulting DB will be missing essential Greek dictionary data and must not be shipped.

**Required for Coptic dictionary** (11,284 entries — build succeeds without it but produces 0 dictionary entries):
```bash
mkdir -p coptic/data-sources
curl -L -o coptic/data-sources/Comprehensive_Coptic_Lexicon-v1.2-2020.xml \
  "https://raw.githubusercontent.com/KELLIA/dictionary/master/xml/Comprehensive_Coptic_Lexicon-v1.2-2020.xml"
```

**Sanskrit Bhagavad Gita** (download + parse, needed before Sanskrit build):
```bash
cd sanskrit/data-sources
bash download_bhagavad_gita_sanskrit.sh   # 18 chapters from Sanskrit Wikisource
bash download_bhagavad_gita_english.sh    # Arnold translation
bash download_bhagavad_gita_besant.sh     # Besant translation
python3 parse_bhagavad_gita_sanskrit.py
python3 parse_bhagavad_gita_english.py
python3 parse_bhagavad_gita_besant.py
cd ../..
```
⚠ Without this, the Sanskrit build silently skips Bhagavad Gita (700 verses, 2 translations).

## Step 3: Download Wiktionary Dumps

The morphological analysis uses a cached extraction from Wiktionary. Use the bundled script to download the dump and rebuild the cache:

```bash
cd data-prep/wiktionary-processing
./build_greek_pages_cache.sh --el    # Downloads en+el dumps (~1.8 GB total), extracts Greek pages cache (~5 min)
cd ../..
```

The script is idempotent — if the dump is already downloaded, it skips to extraction. If the cache already exists, it regenerates it from the dump (useful after a Wiktionary update).

**Note**: The repository may include a pre-existing `all_greek_wiktionary_pages.json` cache, but it can be stale. Re-running the script ensures you get the latest Wiktionary data (~137k Greek pages as of Apr 2026).

## Step 4: Set Up Python Environment

```bash
# Create virtual environment (Python 3.13+ required)
python3 -m venv venv

# Install dependencies
venv/bin/pip install -r data-prep/requirements.txt
```

⚠ **One venv for the whole project.** Scripts in `sanskrit/run_build.sh` and `greek/build_modules/generate_interlinear/run_interlinear_no_sleep.sh` reference `<project-root>/venv`. Do NOT use `source venv/bin/activate` for multiprocessing scripts — worker processes inherit the system Python, not the activated venv. Use `./venv/bin/python3` or the wrapper scripts instead.

## CRITICAL: Build Order — Do Not Skip Ahead

⚠ **Steps 2, 3, and 4 are prerequisites. ALL of them must be fully complete before starting ANY build in Steps 5, 6, or 7.**

Specifically:
- **Every** repo in Step 2 must be cloned (not just started — finished)
- **Every** download in Step 2 must be downloaded AND extracted (OGA, Coptic lexicon, Sanskrit BG)
- **All** Wiktionary dumps in Step 3 must be downloaded, verified, and cached
- The Python venv in Step 4 must be set up with all dependencies installed

**Why this matters**: Module builds that run without their data sources will silently produce empty or incomplete databases. These bad databases then propagate downstream — interlinear generation reads dictionary data from them and produces bad glosses, assembly merges them into the final DB, and the shipped app has missing content. There is no shortcut. If a prerequisite is still downloading, wait for it.

### Extended mode end-to-end build sequence

The extended build has a strict four-phase pipeline. Each phase depends on the previous one being fully complete:

1. **Prerequisites** (Steps 2-4) — clone all repos, download and extract OGA, download Wiktionary dumps, set up venv
2. **Module builds** (Step 6) — build all language module DBs (Greek, Latin, Sanskrit, etc.). OGA must be installed first.
3. **First assembly** (Step 7) — `assemble_database.py extended` merges all module DBs, inserts OGA lemmas, builds the base extended DB (~500K translations)
4. **Interlinear generation** (Step 5) — generates interlinear XMLs for both Greek (~7 hours, 2,048 works) and Latin (~17 seconds, 231 works). Both read dictionary and OGA lemma data from the assembled DB to produce glosses. Without OGA in the DB, glosses will be incomplete.
5. **Greek and Latin rebuild** (Step 6 again) — rebuild Greek and Latin module DBs importing their new interlinear XMLs
6. **Second assembly** (Step 7 again) — re-assembles with interlinear, bringing translations to ~3.3M

**Do NOT start a later phase before the previous one is fully complete.**

## Step 5: Generate Interlinear Translations (Extended Mode Only)

⚠ **This is the most time-consuming step and the most commonly skipped — but without it, ~80% of translation data is missing.** The interlinear XMLs are NOT committed to git (too large). They must be regenerated on every fresh clone.

⚠ **Do NOT start interlinear generation until the first assembly pass (Step 7) is complete, with OGA lemmas included.** The interlinear generator reads dictionary and lemma data from the assembled database to produce glosses. If OGA was not installed before the build, the glosses will be incomplete.

```bash
cd greek/build_modules/generate_interlinear

# Greek interlinear (~7 hours, 8 workers, ~2,049 works)
# DB path: ../../../greek/greek_texts.db  (relative from the generator dir)
./run_interlinear_no_sleep.sh INTERLINEAR_ALL_GREEK_WITH_IDS.csv ../../greek_texts.db 8
# Monitor: tail -f generation.log
# Check:   grep -c "Work .* done" generation.log

cd ../../..
```

Output: ~2,000 XML files in `greek/interlinear_output/` (mirroring `latin/interlinear_output/` — Greek is self-contained). These are imported by the extended database build in Step 7.

**Latin interlinear is no longer generated here** — it is produced automatically by the Latin module (Step 6) and lives under `latin/interlinear_output/`.

### Rebuilding after a Perseus / First1K / PTA update

When the upstream Greek corpora change, run `greek/rebuild_after_update.sh` (wraps the 3-pass rhythm described below). It:
1. Builds `greek/greek_texts.db` with whatever XMLs exist now (Pass 1).
2. Regenerates `INTERLINEAR_ALL_GREEK_WITH_IDS.csv` from the fresh DB (new works picked up, removed works dropped).
3. Regenerates every Greek interlinear XML (Pass 2 — ~5-7 hours, atomic writes, kill-safe).
4. Rebuilds `greek/greek_texts.db` importing the fresh XMLs (Pass 3).

The Latin module and the assembly step are independent — run them after this script finishes:

```bash
cd greek && ./rebuild_after_update.sh && cd ..
cd latin && ./run_build.sh extended && cd ..
cd data-prep && python3 assemble_database.py extended && cd ..
```

⚠ **Gloss quality depends on dictionary quality.** The interlinear generator uses the Wiktionary definitions from `wiktionary_definitions_complete.json`, which is regenerated during each database build. If you update the Wiktionary extraction code, rebuild the databases first, then regenerate interlinear to pick up the improved definitions.

## Step 6: Build Language Databases

## Release targets

There are **three distinct release builds** — each with its own assembly mode, compression output, and target deployment directory. They differ in corpus breadth and which platform receives the shipped ZIP:

| Mode | Corpus | Destination(s) | Purpose |
|---|---|---|---|
| **sample** | 12 authors (Greek + Latin curated) | `app/src/{debug,main}/assets/perseus_texts.db.zip` + `perseus_database/src/main/assets/perseus_texts.db.zip` | Small-footprint Android APK (install-time) |
| **full** | ~138 authors (all Perseus Greek + Latin) | `full_database_pack/src/main/assets/perseus_texts_full.db.zip` + `ios/ClassicsViewer/Resources/OnDemand/perseus_texts_full.db.zip` | Android Play Asset Delivery "full" pack + iOS on-demand |
| **extended** | ~786 authors (Perseus + First1K + PTA + Sanskrit + Pali + Hebrew + Arabic + ...) | `ios/ClassicsViewer/Resources/OnDemand/perseus_texts_extended.db.zip` | iOS on-demand only (too large for Android) |

An additional `ios` variant builds the curated iOS base-app DB (`ios/ClassicsViewer/Resources/perseus_texts.db.zip`) — see the iOS section below. It is a sample-size DB driven by `IOS_SAMPLE_AUTHORS.csv`, not a separate corpus scale.

### Per-module prerequisites by release target

**Latin** is required for every release. **Other language modules** (Sanskrit, Chinese, Hebrew, Persian, Pali, Norse, Coptic, Syriac, Dante/Italian, Old English, Cuneiform) are required only for `full` and `extended`. Each module produces a standalone `.db` that is merged into the Perseus database in Step 7. Module builds are independent and can run in parallel.

```bash
# Latin — MODE MUST MATCH your release target:
cd latin && ./run_build.sh sample   && cd ..   # for sample release
cd latin && ./run_build.sh full     && cd ..   # for full release
cd latin && ./run_build.sh extended && cd ..   # for extended release
# For iOS curated, see the "iOS curated-sample build" section below — uses a custom CSV.

# Sanskrit (~10 hours full mode, 270 works, uses Stanza NLP)
# ⚠ Ensure BG data exists first (see Step 2 — "Sanskrit Bhagavad Gita")
cd sanskrit && ./run_build.sh full && cd ..

# Chinese (~75 seconds, downloads from Wikisource)
cd chinese && python3 create_chinese_database.py && cd ..

# Hebrew — ⚠ TWO scripts needed:
cd hebrewOT
python3 process_hebrew_complete.py     # builds hebrew_texts.db (text + Strong's)
python3 create_hebrew_lexicon.py       # builds hebrew_lexicon.zip (Strong's + BDB)
cd ..
# ⚠ MUST run BOTH scripts. process_hebrew_complete.py alone produces a lexicon
#    with only Strong's entries (8,674). create_hebrew_lexicon.py adds Brown-Driver-
#    Briggs (11,845 entries). The extended merge imports hebrew_lexicon.zip.

# Coptic (~30 seconds, requires data-sources/corpora + Coptic lexicon XML)
# ⚠ Without the lexicon XML, build succeeds but produces 0 dictionary entries.
cd coptic && python3 create_coptic_database.py && cd ..

# Syriac (~10 seconds, requires data-sources/pta_data)
cd syriac && python3 create_syriac_database.py && cd ..

# Pali (~2 minutes, auto-clones bilara-data from SuttaCentral)
cd pali && python3 create_pali_database.py && cd ..

# These are all fast (stdlib only, seconds each):
cd norse       && python3 create_norse_database.py && cd ..
cd old_english && python3 create_old_english_database.py && cd ..
cd dante       && python3 create_dante_database.py && cd ..
cd arabic      && python3 create_arabic_texts.py && cd ..
cd persian     && python3 create_persian_database.py && cd ..
cd cuneiform   && python3 process_sumerian_complete.py && python3 process_akkadian_complete.py && cd ..
```

Each script creates a `*_texts.db` file that is merged into the Perseus database by `assemble_database.py`. Every module listed in the mode's merge rules is **required** — assembly hard-fails if any expected module DB is missing (no silent skips, no partial ships).

### Greek module (required for every release)

Greek has its own module (`greek/run_build.sh`, mirroring `latin/run_build.sh`). It produces `greek/greek_texts.db` (or `greek/greek_texts_ios.db` for iOS) with canonical schema. **Mode must match your release target.**

```bash
cd greek && ./run_build.sh sample   && cd ..   # for sample release (~5 min)
cd greek && ./run_build.sh full     && cd ..   # for full release (~8 min, Perseus Greek only)
cd greek && ./run_build.sh extended && cd ..   # for extended release (~30-40 min: Wiktionary + First1K + PTA + Greek interlinear import)
cd greek && ./run_build.sh ios      && cd ..   # for iOS curated build (uses IOS_SAMPLE_AUTHORS.csv)
```

Greek is fully self-contained under `greek/`: processing code lives at `greek/build_modules/monolith_fn.py`, dictionary/lemma pipeline at `greek/build_modules/*.py`, Wiktionary extraction at `greek/wiktionary-processing/`, author CSVs at `greek/data/`. No dependency on `data-prep/` apart from the shared canonical schema (`shared/database_schema.py`) and the top-level `merge_database.py` tool.

## Step 7: Assemble the Perseus Database

`data-prep/assemble_database.py` is the single build entry point. It merges the per-language module DBs from Step 6, runs the OGA lemma pass, lexicon imports, a schema-drift check, translation_lookup rebuild, quality report, compression, and deployment copy to platform-specific destinations. The mode you pass here **must** match the mode you used for each module's build.

**NEVER run builds in parallel** — they share intermediate files and will corrupt each other. The build lock enforces this; attempting a second build while one is running aborts immediately.

### Sample release (small APK)

```bash
cd latin && ./run_build.sh sample && cd ..
cd greek && ./run_build.sh sample && cd ..
cd data-prep && python3 assemble_database.py sample && cd ..
```
Deploys `perseus_texts_sample.db.zip` to:
- `app/src/debug/assets/perseus_texts.db.zip`
- `app/src/main/assets/perseus_texts.db.zip`
- `perseus_database/src/main/assets/perseus_texts.db.zip`

Expected: 12 authors, 265 works, 667 books, ~154 MB zip, ~8 min total (including OGA).

### Full release (Android Play Asset Delivery full pack + iOS on-demand)

Requires Step 6 Latin in full mode. Does NOT require other non-Greek/Latin language modules (those are extended-only).

```bash
cd latin && ./run_build.sh full && cd ..
cd greek && ./run_build.sh full && cd ..
cd data-prep && python3 assemble_database.py full && cd ..
```
Deploys:
- `full_database_pack/src/main/assets/perseus_texts_full.db.zip` (Android Play Asset Delivery)
- `ios/ClassicsViewer/Resources/OnDemand/perseus_texts_full.db.zip` (iOS on-demand)

Expected: ~138 authors (Greek + Latin, no other languages), ~1,021 works, ~1M text_lines, ~930 MB zip, ~15 min total.

### Extended release (iOS on-demand only — too large for Android)

Requires all of Step 6 — every non-Greek/Latin language module must be pre-built (Sanskrit, Chinese, Hebrew, Persian, Arabic, Pali, Norse, Coptic, Syriac, Dante/Italian, Old English, Cuneiform Sumerian+Akkadian).

```bash
cd latin && ./run_build.sh extended && cd ..
cd greek && ./run_build.sh extended && cd ..
cd data-prep && python3 assemble_database.py extended && cd ..
```
Deploys:
- `ios/ClassicsViewer/Resources/OnDemand/perseus_texts_extended.db.zip` (iOS only)

Expected: ~786 authors, ~2,734 works, ~3.16M text_lines, ~2.8 GB zip, ~45-55 min including Greek extended build.

### iOS curated base app (separate from extended)

Builds the curated base-app DB (`IOS_SAMPLE_AUTHORS.csv`) that ships with the iOS App Store binary. Does NOT affect the Android APK or the iOS on-demand full/extended packs.

```bash
cd greek && ./run_build.sh ios && cd ..
cd latin && ../venv/bin/python3 create_latin_database.py sample \
    --csv ../greek/data/IOS_SAMPLE_AUTHORS.csv \
    --output latin_texts_ios.db && cd ..
cd data-prep && python3 assemble_database.py ios && cd ..
```
Deploys:
- `ios/ClassicsViewer/Resources/perseus_texts.db.zip`

Expected: 11 authors, 41 works, 358 books, ~84 MB zip, ~8 min total.

### Build all four releases (driver)

Run this when you need to produce all release artifacts at once. Assembly
exceeds the 2-minute foreground timeout many agents impose, so each stage
runs via `nohup`. The readers-writers build lock (see "Concurrent-build
mutex" below) lets independent module builds run in parallel but keeps
assembly from starting until they all finish. Within a single module,
different modes (sample/full/extended/ios) must still run sequentially
because they share intermediate state inside that module's directory.

```bash
# Assumes Step 2-6 prerequisites are met (module DBs for sample/full/extended
# already exist, OGA extracted, venv set up, Greek interlinear XMLs present).

# --- sample (~5-8 min) ---
cd data-prep && nohup ../venv/bin/python3 assemble_database.py sample > /tmp/build_sample.log 2>&1 &
wait; grep -E "ASSEMBLY COMPLETE|❌|Traceback|CRITICAL" /tmp/build_sample.log; cd ..

# --- full (~6-15 min) ---
cd data-prep && nohup ../venv/bin/python3 assemble_database.py full > /tmp/build_full.log 2>&1 &
wait; grep -E "ASSEMBLY COMPLETE|❌|Traceback|CRITICAL" /tmp/build_full.log; cd ..

# --- extended (~20-40 min; iOS-only deploy) ---
cd data-prep && nohup ../venv/bin/python3 assemble_database.py extended > /tmp/build_extended.log 2>&1 &
wait; grep -E "ASSEMBLY COMPLETE|❌|Traceback|CRITICAL" /tmp/build_extended.log; cd ..

# --- ios curated (~10-15 min; needs greek+latin ios module DBs first) ---
cd greek && nohup ./run_build.sh ios > /tmp/build_greek_ios.log 2>&1 & wait; cd ..
cd latin && nohup ../venv/bin/python3 create_latin_database.py sample \
    --csv ../greek/data/IOS_SAMPLE_AUTHORS.csv \
    --output latin_texts_ios.db > /tmp/build_latin_ios.log 2>&1 & wait; cd ..
cd data-prep && nohup ../venv/bin/python3 assemble_database.py ios > /tmp/build_ios.log 2>&1 &
wait; grep -E "ASSEMBLY COMPLETE|❌|Traceback|CRITICAL" /tmp/build_ios.log; cd ..
```

Each log ends with `ASSEMBLY COMPLETE (<mode> mode, X.X min)` on success
or one of the `❌` / `Traceback` / `CRITICAL` markers on failure. If a
build fails, do **not** continue to the next mode — fix the root cause
per `BUILD.md` Step 6 troubleshooting and re-run just that stage.

### `--skip-oga` (dev only)

Add `--skip-oga` to `assemble_database.py` to skip the 5-min OGA lemma pass (~268K Greek lemmas). **Do not ship a DB built with `--skip-oga`** — it is missing essential Greek dictionary data. The flag exists only so devs without the 8.6 GB OGA corpus can still get a usable test DB.

### Schema drift check

The assembly script refuses to compress a DB that drifts from `shared/database_schema.py` (canonical DDL extracted from the shipped `perseus_texts-2.db`). Any drift = immediate abort before deployment copies are touched.

### Concurrent-build mutex

The build mutex is a readers-writers scheme implemented in `shared/build_lock.py` (owned by neither the Greek nor the Latin module, so both stay self-contained). The lock files themselves are runtime state and live in the system temp directory, keyed on the absolute repo root so different clones on the same machine have independent locks.

- **Per-module exclusive lock** (`classicsviewer_<repo>_module_<name>.lock`). Each module build (Greek, Latin, and any other language module) takes an exclusive lock on its own file. A second build of the same module in a different mode aborts with the holding PID printed — sample, full, extended, and ios Greek builds all contend on the same `module_greek.lock` file because they share intermediate state inside `greek/`.
- **Assembly readers-writers lock** (`classicsviewer_<repo>_assembly.lock`). Module builds take a shared reader lock on this file (any number of modules can hold it in parallel — Greek + Latin + Sanskrit can all run simultaneously). `data-prep/assemble_database.py` takes an exclusive writer lock on the same file, which blocks until every module releases its reader lock, and blocks any new module from starting while assembly runs.

Call sites: `greek/create_greek_database.py` and `latin/create_latin_database.py` call `acquire_module_lock("<name>")`; `data-prep/assemble_database.py` calls `acquire_assembly_lock()`. All three release via `release_locks()` which is also wired to `atexit`, so the lock is freed even on uncaught exceptions.

### Legacy: `create_perseus_database.py` is retired

The monolithic `create_perseus_database.py` has been fully retired. Its code now lives at `greek/build_modules/monolith_fn.py` — it is the Greek module's build engine, imported by both `greek/create_greek_database.py` and `data-prep/assemble_database.py` (for the post-merge helpers: OGA lemma insertion, lexicon imports, translation_lookup rebuild, quality report, compression, APK copy).

Other Greek-owned state moved alongside:
- `data-prep/build_modules/` → `greek/build_modules/`
- `data-prep/wiktionary-processing/` → `greek/wiktionary-processing/`
- `data-prep/SAMPLE_AUTHORS.csv`, `EXTENDED_AUTHORS.csv`, `IOS_SAMPLE_AUTHORS.csv` → `greek/data/`

`data-prep/` now holds only cross-language assets: `assemble_database.py`, `verify_module_output.py`, and per-mode quality reports.

### Verification (all modes)

Run after each assembly (or after the "Build all four releases" driver).
Mismatches mean the build is bad — do not ship.

```bash
# 1. ZIP integrity — must print "No errors detected"
for m in sample full extended ios; do
  echo "=== $m ==="
  unzip -t "data-prep/perseus_texts_${m}.db.zip" | tail -1
done

# 2. Row counts
for m in sample full extended ios; do
  db="data-prep/perseus_texts_${m}.db"
  [ -f "$db" ] || { echo "SKIP $m (no db)"; continue; }
  echo "=== $m ==="
  sqlite3 "$db" "
    SELECT 'authors',              COUNT(*) FROM authors
    UNION ALL SELECT 'works',              COUNT(*) FROM works
    UNION ALL SELECT 'books',              COUNT(*) FROM books
    UNION ALL SELECT 'text_lines',         COUNT(*) FROM text_lines
    UNION ALL SELECT 'translation_segments', COUNT(*) FROM translation_segments
    UNION ALL SELECT 'dictionary_entries', COUNT(*) FROM dictionary_entries
    UNION ALL SELECT 'lemma_map',          COUNT(*) FROM lemma_map;"
done

# 3. Deployment destinations — sizes must match the source zip
ls -la app/src/debug/assets/perseus_texts.db.zip \
       app/src/main/assets/perseus_texts.db.zip \
       perseus_database/src/main/assets/perseus_texts.db.zip \
       full_database_pack/src/main/assets/perseus_texts_full.db.zip \
       ios/ClassicsViewer/Resources/OnDemand/perseus_texts_full.db.zip \
       ios/ClassicsViewer/Resources/OnDemand/perseus_texts_extended.db.zip \
       ios/ClassicsViewer/Resources/perseus_texts.db.zip
```

Expected values (measured Apr 2026). If a row is off by more than ~5%,
something is wrong — most often an unbuilt module, missing interlinear
XMLs, or a stale module DB from a different mode. Note that
`dictionary_entries` and `lemma_map` are driven by the merged dictionary
corpora (not filtered by author CSV), so `sample` and `ios` land on the
same base Greek+Latin totals; `full` adds Latin-full + a few other
modules; `extended` adds all language lexicons.

| Mode     | authors | works | books  | text_lines | translation_segments | translation_lookup | dict_entries | lemma_map | DB size  | ZIP size |
|----------|---------|-------|--------|------------|----------------------|--------------------|--------------|-----------|----------|----------|
| sample   | 12      | 265   | 667    | ~223K      | ~126K                | ~377K              | ~96K         | ~853K     | ~641 MB  | ~158 MB  |
| full     | 138     | 1,021 | 3,407  | ~1.01M     | ~1.26M               | ~1.73M             | ~233K        | ~3.14M    | ~4.00 GB | ~907 MB  |
| extended | 786     | 2,734 | 172,795| ~3.17M     | ~3.32M               | ~3.91M             | ~660K        | ~12.81M   | ~13.3 GB | ~2.80 GB |
| ios      | 11      | 41    | 358    | ~60K       | ~89K                 | ~113K              | ~96K         | ~853K     | ~371 MB  | ~87 MB   |

Red flags:
- `translation_segments < 500K` on extended — Greek interlinear XMLs missing (see Step 5)
- `dictionary_entries < 500K` on extended — Coptic lexicon or Hebrew BDB missing (Step 2 + Step 6)
- `lemma_map < 10M` on extended — OGA lemma pass skipped or OGA corpus missing (do NOT ship)
- `dictionary_entries` differs between sample and ios — one used a stale Greek/Latin module DB from a different mode
- Deployed ZIP size/mtime doesn't match `data-prep/perseus_texts_*.db.zip` — the copy step was skipped or the destination is stale

## Step 8: Build the APK

### Option A: Command Line

```bash
# Make gradlew executable (first time only)
chmod +x gradlew

# Build debug APK (~2-3 minutes)
./gradlew clean assembleDebug

# Verify APK was created
ls -lh app/build/outputs/apk/debug/app-debug.apk
# Should show ~155MB (with --skip-oga) or ~165MB (with OGA)
```

### Option B: Android Studio

1. Open the project in Android Studio
2. Wait for Gradle sync to complete
3. Select **Build > Build Bundle(s) / APK(s) > Build APK(s)**
4. APK will be at `app/build/outputs/apk/debug/app-debug.apk`

## Step 9: Deploy to Device

Connect your Android device via USB with USB debugging enabled.

```bash
# Uninstall any existing version (important for clean install)
adb uninstall com.classicsviewer.app.debug

# Install the new APK
adb install app/build/outputs/apk/debug/app-debug.apk
```

Or use the convenience script:
```bash
./deploy_simple.sh
```

## Step 10: Verify Installation

1. Launch the app on your device
2. Wait for database extraction (~6-7 seconds on first launch)
3. Select Greek or Latin
4. You should see a list of authors (10 Greek + 2 Latin for sample database)
5. Tap an author and work to view text

## Build Modes Reference

| Mode | Release? | Corpus scale | DB Size | ZIP Size | Build Time (incl. OGA) | Deploys to |
|------|----------|--------------|---------|----------|------------------------|------------|
| **sample** | ✅ | 12 authors | ~670 MB | ~154 MB | ~8 min | `app/src/{debug,main}/assets/`, `perseus_database/src/main/assets/` |
| **full** | ✅ | ~138 authors (Greek+Latin only) | ~4.3 GB | ~930 MB | ~15 min | `full_database_pack/src/main/assets/`, `ios/ClassicsViewer/Resources/OnDemand/` |
| **extended** | ✅ | ~786 authors (all langs) | ~13 GB | ~2.8 GB | ~45-55 min | `ios/ClassicsViewer/Resources/OnDemand/` (iOS only — too large for Android) |
| ios (curated) | ✅ | 11 authors (IOS_SAMPLE_AUTHORS.csv) | ~370 MB | ~84 MB | ~8 min | `ios/ClassicsViewer/Resources/` (iOS base app) |

All four are real release builds with distinct deployment destinations. `full` ships as Android's Play Asset Delivery "full pack" + iOS on-demand pack; `extended` ships only to iOS on-demand (too large for the Android Play Store).

**`--skip-oga` is dev-only.** All release builds MUST include OGA (268,065 Greek lemma mappings). The flag exists so developers without the 8.6 GB OGA corpus can still get a usable test DB; it must not be passed for release builds.

**Build prerequisites by release target**:
- **sample**: OGA corpus (Step 2) + `latin/run_build.sh sample` + `greek/run_build.sh sample`
- **full**: OGA corpus (Step 2) + `latin/run_build.sh full` + `greek/run_build.sh full` (NO other language modules)
- **extended**: OGA corpus (Step 2) + every Step 6 language module built in its extended/full mode, plus `latin/run_build.sh extended` + `greek/run_build.sh extended`, plus Greek interlinear XMLs from Step 5
- **ios (curated)**: OGA corpus (Step 2) + `greek/run_build.sh ios` + latin with iOS CSV (see Step 7 iOS section)

## Troubleshooting

### "Database not found" error on app launch
- Verify ZIP exists: `ls -la app/src/debug/assets/perseus_texts.db.zip`
- Verify ZIP integrity: `unzip -t app/src/debug/assets/perseus_texts.db.zip`
- If corrupted, rebuild the database

### App crashes on startup
```bash
# Clear app data and reinstall
adb shell pm clear com.classicsviewer.app.debug
adb uninstall com.classicsviewer.app.debug
adb install app/build/outputs/apk/debug/app-debug.apk
```

### Build fails with "./gradlew: Permission denied"
```bash
chmod +x gradlew
```

### Build fails with "SDK location not found"
Create `local.properties` in project root:
```bash
echo "sdk.dir=$HOME/Library/Android/sdk" > local.properties  # macOS
# Or on Linux: echo "sdk.dir=$HOME/Android/Sdk" > local.properties
```
Or set the `ANDROID_HOME` environment variable.

### Python errors during database build
- Ensure virtual environment is activated: `source venv/bin/activate`
- Ensure all data sources are cloned (Step 2)
- Ensure Wiktionary dumps are downloaded (Step 3)

### "Pre-packaged database has an invalid schema"
This means the database schema doesn't match the app's expectations.
```bash
# Always uninstall before reinstalling after database changes
adb uninstall com.classicsviewer.app.debug
adb install app/build/outputs/apk/debug/app-debug.apk
```

## Quick Reference Commands

```bash
# Activate Python environment
source venv/bin/activate

# Build sample database
cd data-prep && python3 create_perseus_database.py sample && cd ..

# Build APK
./gradlew clean assembleDebug

# Deploy to device
adb uninstall com.classicsviewer.app.debug && adb install app/build/outputs/apk/debug/app-debug.apk

# View app logs
adb logcat | grep -E "classicsviewer|Perseus"
```

## Build Times (Apple Silicon, Apr 2026)

| Step | Time |
|------|------|
| Wiktionary cache (download + extract) | ~12 min |
| Greek interlinear (2,049 works, 8 workers) | ~7 hours |
| Latin module full (`latin/run_build.sh full`, 230 works, includes interlinear) | ~2 min |
| Sanskrit full (270 works, 8 workers) | ~10 hours |
| Chinese (downloads from Wikisource) | ~75 seconds |
| All other language modules combined | ~2 minutes |
| Sample DB | ~8 min |
| Full DB | ~12 min |
| Extended DB | ~70 min |
| **Total (worst case, sequential)** | **~19 hours** |

Greek interlinear and Sanskrit can run in parallel if you have CPU/RAM headroom (each uses 8 workers). All other language modules can run in parallel with everything.

## Common Pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| `assemble_database.py` fails with `CRITICAL: required module database missing: <name>_texts.db` | The listed module wasn't built (Step 6) for the mode you're assembling | Build the named module in the matching mode, then re-run assembly |
| `import_interlinear_translations` aborts with `CRITICAL: interlinear XML import failed` | One or more XMLs in `greek/interlinear_output/` are truncated/corrupt (usually from an interrupted generation) | Re-run the **full** Greek interlinear generation (Step 5); no targeted fixes allowed |
| Coptic has 0 dictionary_entries | `Comprehensive_Coptic_Lexicon-v1.2-2020.xml` missing | Download from KELLIA repo (see Step 2) |
| Hebrew lexicon missing BDB entries (only ~8,674 instead of ~20,500) | Only ran `process_hebrew_complete.py` | Also run `create_hebrew_lexicon.py` (see Step 6) |
| Sanskrit missing Bhagavad Gita (700 verses) | `bhagavad_gita_sanskrit.json` not generated | Run download + parse scripts (see Step 2) |
| OGA extraction fails with "End-of-central-directory signature not found" | ZIP64 file, standard `unzip` can't handle it | Use `ditto -x -k` (macOS) or `7z x` (Linux) |
| Syriac Philippians has 10 chapters of 1 line each | PTA work code collision (pta0001/pta073 vs pta9999/pta073) | Verify syriac build checks author-level code is pta9999 for NT books |
| Interlinear glosses show "epi ...", leading commas, or "adjective" | Stale `wiktionary_definitions_complete.json` | Rebuild databases (Step 7) to regenerate the definitions file, then regenerate interlinear (Step 5) |

## Next Steps

- See `CLAUDE.md` for detailed development guidelines
- See `data-prep/README.md` for database creation details
- See `data-prep/wiktionary-processing/WIKTIONARY_EXTRACTION_GUIDE.md` for morphology pipeline details
- See `BUILD_ISSUES.md` for historical build issue log from Apr 2026
