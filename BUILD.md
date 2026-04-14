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

**Optional** - For extended database (778 authors, 14 languages):

**Note**: Clone these repos before starting the extended build.

```bash
cd data-sources

# First1KGreek corpus (300+ additional Greek authors, ~1.7GB) - REQUIRED for extended
git clone https://github.com/OpenGreekAndLatin/First1KGreek.git

# Patristic Text Archive (Greek church fathers, ~170MB) - REQUIRED for extended
git clone https://github.com/PatristicTextArchive/pta_data.git

cd ..
```

The following repos are cloned but not currently processed by the database build (future support):
```bash
cd data-sources
# Hebrew Bible and lexicon
git clone https://github.com/openscriptures/morphhb.git
git clone https://github.com/openscriptures/HebrewLexicon.git
# Arabic texts
git clone https://github.com/cltk/arabic_text_perseus.git
# Persian texts
git clone https://github.com/PerseusDL/canonical-farsiLit.git
# Sanskrit texts (~3GB)
git clone https://github.com/OliverHellwig/sanskrit.git
# Syriac texts (~1.2GB)
git clone https://github.com/srophe/syriaca-data.git
# Coptic texts (~1.2GB)
git clone https://github.com/CopticScriptorium/corpora.git
cd ..
```

**Optional** - For enhanced lemma coverage (OGA corpus, 8.6GB download):
```bash
cd data-sources

# Opera Graeca Adnotata corpus - provides additional lemma mappings
curl -L -O https://zenodo.org/records/14206061/files/opera_graeca_adnotata_v0.2.0.zip

# ⚠ ZIP64 format (7.8 GB) — standard `unzip` WILL FAIL. Use ditto (macOS) or 7z (Linux):
ditto -x -k opera_graeca_adnotata_v0.2.0.zip .
# Verify: ls opera_graeca_adnotata_v0.2.0/workspace/oga.zip

cd ..
```
If you skip this download, add `--skip-oga` to the database build command in Step 5.

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

⚠ **One venv for the whole project.** Scripts in `sanskrit/run_build.sh` and `data-prep/build_modules/generate_interlinear/run_interlinear_no_sleep.sh` reference `<project-root>/venv`. Do NOT use `source venv/bin/activate` for multiprocessing scripts — worker processes inherit the system Python, not the activated venv. Use `./venv/bin/python3` or the wrapper scripts instead.

## Step 5: Generate Interlinear Translations (Extended Mode Only)

⚠ **This is the most time-consuming step and the most commonly skipped — but without it, ~80% of translation data is missing.** The interlinear XMLs are NOT committed to git (too large). They must be regenerated on every fresh clone.

**Build order matters:** The interlinear generator reads dictionary data from the Perseus database to produce glosses. The correct sequence is:

1. Build a base extended DB first (Step 7, without interlinear — it will have ~500K translations)
2. Generate interlinear XMLs (this step — reads the base DB's dictionary)
3. Rebuild extended DB (Step 7 again — imports the XMLs, bringing translations to ~3.3M)

If the base DB doesn't exist yet, the interlinear generator will fail or produce empty glosses.

```bash
cd data-prep/build_modules/generate_interlinear

# Greek interlinear (~7 hours, 8 workers, ~2,049 works)
./run_interlinear_no_sleep.sh INTERLINEAR_ALL_GREEK_WITH_IDS.csv ../../perseus_texts_extended.db 8
# Monitor: tail -f generation.log
# Check:   grep -c "Work .* done" generation.log

# Latin interlinear (~17 seconds, 230 works)
./run_latin_interlinear_no_sleep.sh INTERLINEAR_ALL_LATIN_WITH_IDS.csv ../../perseus_texts_full.db 8

cd ../../..
```

Output: ~2,200 XML files in `data-sources/classicsviewer_interlinear/`. These are imported by the extended database build in Step 7.

⚠ **Gloss quality depends on dictionary quality.** The interlinear generator uses the Wiktionary definitions from `wiktionary_definitions_complete.json`, which is regenerated during each database build. If you update the Wiktionary extraction code, rebuild the databases first, then regenerate interlinear to pick up the improved definitions.

## Step 6: Build Language Databases (Extended Mode Only)

Skip this step if you only need the sample database. Each module produces a standalone `.db` that gets merged into the extended database. These can all run in parallel (they are independent).

```bash
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

Each script creates a `*_texts.db` file that will be automatically merged when you build the extended database. Missing databases are skipped with a warning — but the data will be absent.

## Step 7: Build the Perseus Databases

**NEVER run these in parallel** — they share output files and will corrupt each other.

```bash
cd data-prep

# Sample: 12 authors, ~8 min, 670 MB / 162 MB zip
python3 create_perseus_database.py sample

# Full: 135 authors (Greek + Latin), ~12 min, 4.2 GB / 929 MB zip
python3 create_perseus_database.py full

# Extended: 780 authors (all languages), ~70 min, 13 GB / 2.8 GB zip
# ⚠ Merges all language DBs from Step 6 + interlinear XMLs from Step 5
python3 create_perseus_database.py extended

cd ..
```

Add `--skip-oga` if you didn't download the OGA corpus in Step 2.

**Verification** (extended mode):
```bash
# Check sizes
ls -lh data-prep/perseus_texts_extended.db   # ~13 GB
unzip -t data-prep/perseus_texts_extended.db.zip  # no errors

# Spot-check row counts
sqlite3 data-prep/perseus_texts_extended.db "
SELECT 'authors', COUNT(*) FROM authors
UNION ALL SELECT 'works', COUNT(*) FROM works
UNION ALL SELECT 'text_lines', COUNT(*) FROM text_lines
UNION ALL SELECT 'translation_segments', COUNT(*) FROM translation_segments
UNION ALL SELECT 'dictionary_entries', COUNT(*) FROM dictionary_entries
UNION ALL SELECT 'lemma_map', COUNT(*) FROM lemma_map;"
# Expected (Apr 2026):
#   authors:              ~780
#   works:                ~2,728
#   text_lines:           ~3,158,000
#   translation_segments: ~3,300,000  (if <500K, interlinear XMLs are missing — see Step 5)
#   dictionary_entries:   ~625,000    (if coptic=0 or no BDB, check Step 2 + Step 6 notes)
#   lemma_map:            ~12,760,000
```

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

| Mode | Command | Authors | DB Size | ZIP Size | Build Time |
|------|---------|---------|---------|----------|------------|
| Sample | `python3 create_perseus_database.py sample --skip-oga` | 12 | 615MB | 143MB | ~2 min |
| Sample (with OGA) | `python3 create_perseus_database.py sample` | 12 | 671MB | 163MB | ~5 min |
| Full | `python3 create_perseus_database.py full --skip-oga` | 135 | 2.3GB | 558MB | ~4 min |
| Full (with OGA) | `python3 create_perseus_database.py full` | 135 | 3.7GB | 838MB | ~7 min |
| Extended | `python3 create_perseus_database.py extended --skip-oga` | 778 | 8.7GB | 2.0GB | ~22 min |
| Extended (with OGA) | `python3 create_perseus_database.py extended` | 778 | ~10GB | ~2.5GB | ~28 min |

**Note**: Only use the sample database for APK builds. Full and extended databases are too large for the Play Store.
The `--skip-oga` flag skips the 8.6GB OGA corpus download, resulting in slightly smaller database.

**Extended mode requirements**: Before building extended, first complete Step 5 to build all language databases. Then run extended mode which merges them automatically. Missing databases will be skipped.

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
| Latin interlinear (230 works) | ~17 seconds |
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
| Extended DB has <500K translation_segments | Interlinear XMLs missing (Step 5 skipped) | Run Greek + Latin interlinear generation, then rebuild extended |
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
