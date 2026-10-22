# Classics Viewer
Note: If you have trouble loading the app after an update, save bookmarks, uninstall and reinstall.  Only updating the app will not update the data.  

An Android and iOS app for reading ancient Greek and Latin texts offline. Browse works from Homer, Plato, Virgil, Cicero and many other classical authors - all stored locally on your phone with no internet required. Using the app requires no internet connection and it can be used indefinitely in airplane mode.

The app is restricted to users 18 and older. On Apple and Android, age is confirmed through your account. App contains some AI-derived data, mistakes may be present.

There is a download option within the menu to optionally retrieve the large full db from Google Play Store and Apple App Store. This has interlinear for all Greek and Latin plus a latin dictionary in addition to the Greek one. A few Akkadian and Sumerian texts are there as well. Another option exists to download the full Chamberlain Iliad audio.
Audio licensed as CC-BY, © 2016, 2017 by David Chamberlain. https://creativecommons.org/licenses/by/4.0/  Source: https://hypotactic.com/my-reading-of-homer-work-in-progress/ 
 
Extended db support with First1k data (https://github.com/OpenGreekAndLatin/First1KGreek/tree/master). 300+ authors, 900+ works, some untranslated. 40G free on device needed. Download extended db module from within app on both app stores.

The GitHub release https://github.com/threedlite/classicsviewer/releases/tag/data-2026-10-17 (see fetch_release.sh) is not a runnable program and not an app download. It holds only intermediate build components (the assembled database zips, asset packs, module databases, generated interlinear XML and caches) so that someone building the app from this repo can skip some lengthy steps. The built app itself is obtainable on Google or Apple App Stores. 


  SAMPLE DATABASE (632MB, 143MB compressed):
  - Greek: 10 authors, 259 works
  - Latin: 2 authors, 6 works
  - Total: 12 authors, 265 works, 223K lines, 2.8M words

  FULL DATABASE (4.8GB, 968MB compressed):
  - Akkadian: 1 author, 1 work
  - Greek: 91 authors, 772 works
  - Italian: 1 author, 3 works
  - Latin: 43 authors, 233 works
  - Old English: 1 author, 1 work
  - Sumerian: 1 author, 11 works
  - Total: 138 authors, 1,021 works, 1.0M lines, 14.7M words

  EXTENDED DATABASE (14.4GB, 2.74GB compressed):
  - Akkadian: 1 author, 1 work
  - Arabic: 1 author, 1 work
  - Chinese: 2 authors, 2 works
  - Coptic: 29 authors, 51 works
  - Greek: 392 authors, 2,056 works
  - Hebrew: 40 authors, 40 works
  - Italian: 1 author, 3 works
  - Latin: 43 authors, 233 works
  - Norse: 1 author, 25 works
  - Old English: 1 author, 1 work
  - Pali: 1 author, 5 works
  - Persian: 1 author, 1 work
  - Sanskrit: 272 authors, 272 works
  - Sumerian: 1 author, 11 works
  - Syriac: 5 authors, 41 works
  - Total: 791 authors, 2,743 works, 3.45M lines, 48.2M words


 
## Features

- 📚 **100+ Greek and Latin authors** with complete works
- 🔍 **Tap any word** to see dictionary definitions and find other occurrences
- 🌐 **English translations** available for most texts
- 📱 **100% offline** - no internet connection needed
- 🎨 **Customizable display** - adjust text size, colors, and reading preferences

## To build locally, point your AI at BUILD.md

### Prerequisites for building app
- Android Studio
- Android device or emulator (Android 7.0+, minSdk 24)
- Python 3 (for building the database)
- ~50GB free disk space

### iOS

#### Prerequisites
- Xcode 16.4 or later
- macOS 15.6 or later
- iOS 16.1+ deployment target


3. **Database**: A sample database is bundled in `ClassicsViewer/Resources/perseus_texts.db.zip`. The app extracts it automatically on first launch.

- Repo *.md files are mostly genereated by Claude and may not be entirely up-to-date.

## License

The Classics Viewer code is dual-licensed under the MIT License or the Apache License, Version 2.0, at your option (`LICENSE.txt`, `LICENSE-MIT`, `LICENSE-APACHE`; SPDX `MIT OR Apache-2.0`).

The texts, translations, dictionaries and other data the app displays are third-party works under their own licences (Perseus CC BY-SA, public domain, Project Gutenberg License and others). The full notice is in `THIRD_PARTY_LICENSES.txt` and on the licence screen of each app (`LicenseActivity.kt`).

## Other unaffiliated projects
A more in-depth morphological system, which I have not incorporated but is likely to be more accurate, is here: https://bitbucket.org/ben-crowell/lemming/src/master/README.md

## A project based on similar source corpora with CC-BY-SA 4 license. There may be a possibility of incorporating their parsing and lemmatization strategies in the future.
https://github.com/OperaGraecaAdnotata/OGA


