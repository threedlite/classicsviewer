# Classics Viewer
Note: If you have trouble loading the app after an update, save bookmarks, uninstall and reinstall.  Only updating the app will not update the data.  

An Android and iOS app for reading ancient Greek and Latin texts offline. Browse works from Homer, Plato, Virgil, Cicero and many other classical authors - all stored locally on your phone with no internet required. The app holds no internet permission and can be used indefinitely in airplane mode.

The app is restricted to users 18 and older. On Android, age is confirmed through your Google Play account.

There is a download option within the menu to optionally retrieve the large full db from Google Play Store and Apple App Store. This has interlinear for all Greek and Latin plus a latin dictionary in addition to the Greek one. A few Akkadian and Sumerian texts are there as well. Another option exists to download the full Chamberlain Iliad audio.
Audio licensed as CC-BY, © 2016, 2017 by David Chamberlain. https://creativecommons.org/licenses/by/4.0/  Source: https://hypotactic.com/my-reading-of-homer-work-in-progress/ 
 
Patreon links below added for production hosting purposes. All db files are free and can be also be generated locally using create_perseus_database.py script after data-sources repo links are cloned.

Extended db support with First1k data (https://github.com/OpenGreekAndLatin/First1KGreek/tree/master). 300+ authors, 900+ works, some untranslated. 40G free on device needed. Download module from Apple store, or on Android, install external db perseus_texts_extended.db.zip from  https://www.patreon.com/posts/classics-viewer-141298606  (free) or build locally.


  SAMPLE DATABASE (673MB, 162MB compressed):
  - Greek: 10 authors, 259 works
  - Latin: 2 authors, 6 works
  - Total: 12 authors, 265 works, 238K lines, 3.2M words

  FULL DATABASE (4.2GB, 929MB compressed):
  - Akkadian: 1 author, 1 work
  - Greek: 91 authors, 772 works
  - Italian: 1 author, 3 works
  - Latin: 40 authors, 230 works
  - Old English: 1 author, 1 work
  - Sumerian: 1 author, 11 works
  - Total: 135 authors, 953 works, 1.0M lines, 15.4M words

  EXTENDED DATABASE (13GB, 2.8GB compressed):
  - Akkadian: 1 author, 1 work
  - Arabic: 1 author, 1 work
  - Chinese: 2 authors, 2 works
  - Coptic: 29 authors, 51 works
  - Greek: 388 authors, 2,049 works
  - Hebrew: 39 authors, 39 works
  - Italian: 1 author, 3 works
  - Latin: 40 authors, 230 works
  - Norse: 1 author, 25 works
  - Old English: 1 author, 1 work
  - Pali: 1 author, 5 works
  - Persian: 1 author, 1 work
  - Sanskrit: 270 authors, 270 works
  - Sumerian: 1 author, 11 works
  - Syriac: 4 authors, 39 works
  - Total: 780 authors, 2,663 works, 3.1M lines, 49.7M words


 
## Features

- 📚 **100+ Greek and Latin authors** with complete works
- 🔍 **Tap any word** to see dictionary definitions and find other occurrences
- 🌐 **English translations** available for most texts
- 📱 **100% offline** - no internet connection needed
- 🎨 **Customizable display** - adjust text size, colors, and reading preferences

## To build locally, point your AI at BUILD.md

### Prerequisites for building app
- Android Studio
- Android device or emulator (Android 6.0+, minSdk 23)
- Python 3 (for building the database)
- ~2GB free disk space

### iOS

#### Prerequisites
- Xcode 16.4 or later
- macOS 15.6 or later
- iOS 16.1+ deployment target


3. **Database**: A sample database is bundled in `ClassicsViewer/Resources/perseus_texts.db.zip`. The app extracts it automatically on first launch.

- Repo *.md files are mostly genereated by Claude and may not be entirely up-to-date.

## License

This project uses texts from the Perseus Digital Library. See LicenseActivity.kt and individual text files for specific licensing information.

## Other unaffiliated projects
A more in-depth morphological system, which I have not incorporated but is likely to be more accurate, is here: https://bitbucket.org/ben-crowell/lemming/src/master/README.md

## A project based on similar source corpora with CC-BY-SA 4 license. There may be a possibility of incorporating their parsing and lemmatization strategies in the future.
https://github.com/OperaGraecaAdnotata/OGA


