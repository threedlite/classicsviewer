# Classics Viewer
Note: If you have trouble loading the app after an update, uninstall and reinstall.
If you have trouble cloning this repo set GIT_LFS_SKIP_SMUDGE=1

An Android app for reading ancient Greek and Latin texts offline. Browse works from Homer, Plato, Virgil, Cicero and many other classical authors - all stored locally on your phone with no internet required.

NOTE: If you just want all the Perseus authors (90+), copy data-prep/perseus_texts_full.db.zip (700MB+) to phone, e.g. in Downloads folder, then in the app select "Select external database" and select that file.
If git-lfs is not working, file (for version 0.8.19+) is also available at:  https://drive.google.com/file/d/1pDvFgMshF56LRU9UAfc1fIdYSaaS5c-A/view?usp=sharing


NEW: Audio file for entire Iliad prosody-aware line by line (menu option manage audio), project audio folder or: https://drive.google.com/file/d/1fOOfQeMP53Kz3dvnu-5X9Qd76VSmzjBm/view?usp=sharing 
Audio licensed as CC-BY, © 2016, 2017 by David Chamberlain. https://creativecommons.org/licenses/by/4.0/  Source: https://hypotactic.com/my-reading-of-homer-work-in-progress/ 


NEW (beta): Extended db support with First1k data (https://github.com/OpenGreekAndLatin/First1KGreek/tree/master). 300+ authors, 900+ works, some untranslated. 10G+ uncompressed.
perseus_texts_extended.db.zip  via Github LFS or Google Drive link:  https://drive.google.com/file/d/1EhxEsUYAm2TrkPuhrQEuEYLXdjz0tmYv/view?usp=sharing


NEW: Akkadian and Sumerian added to full db. Extended db has in addition some Sanskrit, Persian, Arabic, Hebrew.  Some dictionary support mainly for Sanskrit.  An Arabic classical treebank licensed CC-BY-SA without NC would have allowed more.




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

This project uses texts from the Perseus Digital Library. See individual text files for specific licensing information.

## Other unaffiliated projects
A more in-depth morphological system, which I have not incorporated but is likely to be more accurate, is here: https://bitbucket.org/ben-crowell/lemming/src/master/README.md


