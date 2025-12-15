# Classics Viewer
Note: If you have trouble loading the app after an update, save bookmarks, uninstall and reinstall.  Only updating the app will not update the data.  
If you have trouble cloning this repo set GIT_LFS_SKIP_SMUDGE=1

An Android app for reading ancient Greek and Latin texts offline. Browse works from Homer, Plato, Virgil, Cicero and many other classical authors - all stored locally on your phone with no internet required.

NOTE - NEW: There is now a download option within the menu to optionally retrieve the large full db from Google Play Store. This has interlinear for all Greek and Latin plus a latin dictionary in addition to the Greek one. A few Akkadian and Sumerian texts are there as well. Another option exists to download the full Chamberlain Iliad audio.
Audio licensed as CC-BY, © 2016, 2017 by David Chamberlain. https://creativecommons.org/licenses/by/4.0/  Source: https://hypotactic.com/my-reading-of-homer-work-in-progress/ 



Patreon links below added for production hosting purposes. All db files are free and can be also be generated locally using create_perseus_database.py script after data-sources repo links are cloned.

Beta: Extended db support with First1k data (https://github.com/OpenGreekAndLatin/First1KGreek/tree/master). 300+ authors, 900+ works, some untranslated. 40G free on device needed. perseus_texts_extended.db.zip   https://www.patreon.com/posts/classics-viewer-141298606  (free)


  SAMPLE DATABASE:
  - Greek: 10 authors, 259 works
  - Latin: 2 authors, 6 works
  - Total: 12 authors, 265 works

  FULL DATABASE:
  - Akkadian: 1 author, 1 work
  - Greek: 91 authors, 772 works
  - Latin: 40 authors, 230 works
  - Sumerian: 1 author, 11 works
  - Total: 133 authors, 1,014 works

  EXTENDED DATABASE:
  - Akkadian: 1 author, 1 work
  - Arabic: 1 author, 1 work
  - Greek: 367 authors, 1,855 works
  - Hebrew: 39 authors, 39 works
  - Latin: 40 authors, 230 works
  - Persian: 1 author, 1 work
  - Sanskrit: 270 authors, 270 works
  - Sumerian: 1 author, 11 works
  - Total: 457 authors, 2,145 works


NEW: Suggested reading list bookmarks to import READING_LIST_GREEK.csv
 

## Features

- 📚 **100+ Greek and Latin authors** with complete works
- 🔍 **Tap any word** to see dictionary definitions and find other occurrences
- 🌐 **English translations** available for most texts
- 📱 **100% offline** - no internet connection needed
- 🎨 **Customizable display** - adjust text size, colors, and reading preferences

## Quick Start

### Prerequisites for building app
- Android Studio
- Android device or emulator (Android 5.0+)
- Python 3 (for building the database)
- ~2GB free disk space

### Building the App

1. **Clone the repository**
   ```bash
   git clone https://github.com/threedlite/classicsviewer.git
   cd classicsviewer
   ```

2. **Build the database** (required first time only)
   ```bash
   cd data-prep
   python3 create_perseus_database.py sample
   cd ..
   ```
   This creates a sample database with selected authors. Takes about 3-4 minutes.

3. **Deploy to your Android device**
   ```bash
   ./deploy_simple.sh
   ```
   The app will install and launch automatically.

### Alternative: Build in Android Studio

1. Open the project in Android Studio
2. Make sure the database exists: `app/src/debug/assets/perseus_texts.db.zip`
3. Click "Run" to build and deploy

## Using the App

1. **Select a language** - Choose Greek or Latin
2. **Browse authors** - Tap an author to see their works
3. **Select a work** - Choose from available books/sections
4. **Read and explore** - Tap any word for definitions, swipe for translations

## Troubleshooting

**App crashes on startup?**
- Clear app data: `adb shell pm clear com.classicsviewer.app.debug`
- Reinstall: `adb uninstall com.classicsviewer.app.debug` then redeploy

**Build fails?**
- Make sure you have Android SDK installed
- Check that `./gradlew` is executable: `chmod +x gradlew`

- *.md files are mostly genereated by Claude and may not be entirely up-to-date.

## Data Sources

Texts are from the Perseus Digital Library:
- Greek texts from canonical-greekLit
- Latin texts from canonical-latinLit
- Morphological data from Wiktionary

## License

This project uses texts from the Perseus Digital Library. See LicenseActivity.kt and individual text files for specific licensing information.

## Other unaffiliated projects
A more in-depth morphological system, which I have not incorporated but is likely to be more accurate, is here: https://bitbucket.org/ben-crowell/lemming/src/master/README.md

## A project based on similar source corpora with CC-BY-SA 4 license. There may be a possibility of incorporating their parsing and lemmatization strategies in the future.
https://github.com/OperaGraecaAdnotata/OGA


