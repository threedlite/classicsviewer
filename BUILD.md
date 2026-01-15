# Build Guide for Classics Viewer

Step-by-step instructions to build and run Classics Viewer from a fresh clone.

## Prerequisites

Before starting, ensure you have:

- **Git** - for cloning repositories
- **Python 3.8+** - for database creation
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
unzip opera_graeca_adnotata_v0.2.0.zip

cd ..
```
If you skip this download, add `--skip-oga` to the database build command in Step 5.

**Generate missing interlinear file** (if needed):

The sample build requires interlinear translations for Iliad, Odyssey, and Aeneid.
If the Aeneid file is missing, generate it:
```bash
cd data-prep/build_modules/generate_interlinear
source ../../../venv/bin/activate
python3 generate_latin_interlinear.py ../../perseus_texts_sample.db \
    /path/to/classicsviewer/data-sources/classicsviewer_interlinear phi0690.phi003
cd ../../..
```
Note: This requires running the database build first (it will fail at interlinear import),
then generating the file, then re-running the database build.

## Step 3: Download Wiktionary Dumps (Optional)

The morphological analysis uses pre-extracted Wiktionary data included in the repository.
However, if you need to regenerate this data from scratch, download these dumps:

```bash
cd data-sources

# English Wiktionary (~1.4GB compressed)
curl -L -O https://dumps.wikimedia.org/enwiktionary/latest/enwiktionary-latest-pages-articles.xml.bz2

# Greek Wiktionary (~98MB compressed)
curl -L -O https://dumps.wikimedia.org/elwiktionary/latest/elwiktionary-latest-pages-articles.xml.bz2

cd ..
```

**Note**: The repository includes `data-prep/wiktionary-processing/all_greek_wiktionary_pages.json`
which is the pre-extracted cache. You can skip this step for a basic build.

## Step 4: Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# Or on Windows: venv\Scripts\activate

# Install dependencies
pip install -r data-prep/requirements.txt
```

## Step 5: Build Language Databases (Extended Mode Only)

Skip this step if you only need the sample database. For extended mode with 778+ authors across multiple languages, build these databases first:

```bash
source venv/bin/activate

# Sanskrit (~15-20 minutes, includes interlinear generation)
cd sanskrit && python3 create_sanskrit_database_interlinear.py full && cd ..

# Hebrew (~1 minute)
cd hebrewOT && python3 process_hebrew_complete.py && cd ..

# Coptic (~1 minute, requires data-sources/corpora)
cd coptic && python3 create_coptic_database.py && cd ..

# Syriac (~30 seconds, requires data-sources/pta_data)
cd syriac && python3 create_syriac_database.py && cd ..

# Pali (~2 minutes, auto-clones bilara-data from SuttaCentral)
cd pali && python3 create_pali_database.py && cd ..

# Norse (~1 minute, auto-clones CLTK Old Norse texts)
cd norse && python3 create_norse_database.py && cd ..

# Old English (~30 seconds, auto-downloads from Project Gutenberg)
cd old_english && python3 create_old_english_database.py && cd ..

# Dante (~30 seconds, auto-downloads from Project Gutenberg)
cd dante && python3 create_dante_database.py && cd ..

# Arabic (~10 seconds)
cd arabic && python3 create_arabic_texts.py && cd ..

# Persian (~30 seconds, requires data-sources/canonical-farsiLit)
cd persian && python3 create_persian_database.py && cd ..

# Sumerian and Akkadian (~30 seconds each)
cd cuneiform && python3 process_sumerian_complete.py && python3 process_akkadian_complete.py && cd ..
```

Each script creates a `*_texts.db` file that will be automatically merged when you build the extended database.

## Step 6: Build the Sample Database

The sample database includes 12 authors (Homer, Plato, Sophocles, etc.) and is suitable for the Play Store release.

```bash
cd data-prep

# Activate virtual environment first
source ../venv/bin/activate

# Build takes ~5 minutes
# Add --skip-oga if you didn't download the OGA corpus in Step 2
python3 create_perseus_database.py sample

# Or with --skip-oga:
# python3 create_perseus_database.py sample --skip-oga

cd ..
```

**Expected output**:
- `data-prep/perseus_texts_sample.db` (~671MB)
- `app/src/debug/assets/perseus_texts.db.zip` (~163MB)
- `app/src/main/assets/perseus_texts.db.zip` (~163MB)

**Verification**:
```bash
# Check database was created
ls -lh data-prep/perseus_texts_sample.db
# Should show ~671MB

# Check ZIP was created and is valid
ls -lh app/src/debug/assets/perseus_texts.db.zip
# Should show ~163MB

unzip -t app/src/debug/assets/perseus_texts.db.zip
# Should show "No errors detected"
```

## Step 7: Build the APK

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

## Step 8: Deploy to Device

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

## Step 9: Verify Installation

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

## Next Steps

- See `CLAUDE.md` for detailed development guidelines
- See `data-prep/README.md` for database creation details
- See `data-prep/BUILD_INSTRUCTIONS.md` for morphology extraction details
