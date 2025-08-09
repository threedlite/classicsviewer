# Classics Viewer - Android App Skeleton

This is an Android application skeleton for viewing classical texts (using data from the Perseus Digital Library).

## Project Structure

```
app/
├── src/main/
│   ├── java/com/perseus/viewer/
│   │   ├── MainActivity.kt              - Language selection
│   │   ├── AuthorListActivity.kt        - Author listing
│   │   ├── WorkListActivity.kt          - Work listing (to be implemented)
│   │   ├── BookListActivity.kt          - Book listing (to be implemented)
│   │   ├── TextViewerActivity.kt        - Text display with clickable words
│   │   ├── DictionaryActivity.kt        - Dictionary lookup (to be implemented)
│   │   ├── LemmaOccurrencesActivity.kt  - Lemma search (to be implemented)
│   │   ├── models/                      - Data models
│   │   │   ├── Author.kt
│   │   │   ├── Work.kt
│   │   │   ├── Book.kt
│   │   │   └── TextLine.kt
│   │   ├── data/                        - Data access
│   │   │   └── PerseusXmlParser.kt     - XML parsing utilities
│   │   └── adapters/                    - RecyclerView adapters
│   └── res/                             - Resources (layouts, values, etc.)
└── build.gradle                         - App-level build configuration
```

## Features Implemented in Skeleton

1. **Basic Navigation Structure**:
   - Language selection (Greek/Latin)
   - Author listing
   - Placeholder for work/book/line navigation

2. **Data Models**:
   - Author, Work, Book, TextLine models
   - XML parser for Perseus CTS format

3. **Text Viewer**:
   - Basic text display with line numbers
   - Clickable word implementation
   - Navigation buttons

## Next Steps to Complete Implementation

1. **Complete Navigation Activities**:
   - Implement WorkListActivity
   - Implement BookListActivity
   - Add line range selection

2. **Data Access**:
   - Set up Room database for efficient data access
   - Pre-process and import Perseus XML data
   - Implement dictionary data structure

3. **Dictionary Features**:
   - Implement LSJ dictionary parsing
   - Create DictionaryActivity
   - Add lemma search functionality

4. **UI Enhancements**:
   - Add proper theming
   - Implement text size preferences
   - Add search functionality

## Building the App

1. Ensure you have Android Studio installed
2. Open the project in Android Studio
3. Sync project with Gradle files
4. Build and run on an emulator or device

## Data Sources

The app uses data from:
- `data-sources/canonical-greekLit/` - Greek texts
- `data-sources/canonical-latinLit/` - Latin texts
- Dictionary data needs to be added for word lookups

## Requirements Met

✓ 100% local operation (no internet permissions in manifest)
✓ Navigation hierarchy structure
✓ Basic text viewer with clickable words
✓ Foundation for dictionary and lemma search

# Wiktionary data from:
https://dumps.wikimedia.org/enwiktionary/latest/enwiktionary-latest-pages-articles.xml.bz2

## Local web app
- There is also a simple web viewer in /web-app that runs locally in Docker.

