# Classics Viewer Android App - Detailed Setup Notes

## Current Project State

### Project Structure Created
```
/home/user/classics-viewer/
├── app/
│   ├── build.gradle                     # App-level Gradle config
│   ├── src/main/
│   │   ├── AndroidManifest.xml         # No internet permissions
│   │   ├── java/com/perseus/viewer/
│   │   │   ├── MainActivity.kt         # Entry point - language selection
│   │   │   ├── AuthorListActivity.kt   # Shows authors for selected language
│   │   │   ├── WorkListActivity.kt     # TODO: Implement
│   │   │   ├── BookListActivity.kt     # TODO: Implement
│   │   │   ├── TextViewerActivity.kt   # Shows text with clickable words
│   │   │   ├── DictionaryActivity.kt   # TODO: Implement
│   │   │   ├── LemmaOccurrencesActivity.kt # TODO: Implement
│   │   │   ├── LanguageAdapter.kt      # RecyclerView adapter
│   │   │   ├── AuthorAdapter.kt        # RecyclerView adapter
│   │   │   ├── TextLineAdapter.kt      # RecyclerView adapter with clickable words
│   │   │   ├── models/
│   │   │   │   ├── Author.kt           # data class Author(id, name, language)
│   │   │   │   ├── Work.kt             # data class Work(id, title, authorId, language)
│   │   │   │   ├── Book.kt             # data class Book(id, number, workId, lineCount)
│   │   │   │   └── TextLine.kt         # data class TextLine(lineNumber, text, words)
│   │   │   └── data/
│   │   │       └── PerseusXmlParser.kt # XML parsing for Perseus CTS format
│   │   └── res/
│   │       ├── layout/
│   │       │   ├── activity_main.xml           # Language selection screen
│   │       │   ├── activity_list.xml           # Generic list screen
│   │       │   ├── activity_text_viewer.xml    # Text display with navigation
│   │       │   ├── item_language.xml           # Language card item
│   │       │   ├── item_text.xml               # Generic text list item
│   │       │   └── item_text_line.xml          # Text line with line number
│   │       ├── values/
│   │       │   ├── strings.xml                 # App strings
│   │       │   ├── colors.xml                  # Color definitions
│   │       │   └── themes.xml                  # Material theme
│   │       ├── xml/
│   │       │   ├── backup_rules.xml            # Backup config
│   │       │   └── data_extraction_rules.xml   # Data extraction config
│   │       ├── drawable/
│   │       │   └── ic_launcher_background.xml  # Placeholder icon
│   │       └── mipmap-*/                       # Icon directories (empty)
├── build.gradle                         # Project-level Gradle config
├── settings.gradle                      # Gradle settings
├── gradle.properties                    # Gradle properties
├── gradle/wrapper/
│   └── gradle-wrapper.properties       # Gradle 8.2
├── CLAUDE.md                           # Project instructions
├── REQS.txt                           # Requirements document
├── README.md                          # Project documentation
└── data-sources/                      # Perseus data (DO NOT MODIFY)
    ├── canonical-greekLit/            # Greek texts
    ├── canonical-latinLit/            # Latin texts
    ├── canonical-pdlrefwk/            # Reference works
    └── perseus_catalog/               # Catalog data
```

## Implementation Details

### 1. Navigation Flow
```
MainActivity (Language Selection)
    ↓
AuthorListActivity (Author List)
    ↓
WorkListActivity (Work List) - TODO
    ↓
BookListActivity (Book/Chapter List) - TODO
    ↓
Line Range Selection - TODO
    ↓
TextViewerActivity (Text Display)
    ↓ (on word click)
DictionaryActivity (Word Definition) - TODO
    ↓ (optional)
LemmaOccurrencesActivity (All Occurrences) - TODO
```

### 2. Data Model Structure

#### Author
- id: String (e.g., "tlg0012" for Homer)
- name: String (e.g., "Homer")
- language: String ("tlg" for Greek, "phi" for Latin)

#### Work
- id: String (e.g., "tlg001" for Iliad)
- title: String (e.g., "Iliad")
- authorId: String (reference to Author)
- language: String

#### Book
- id: String
- number: String (e.g., "1", "2", etc.)
- workId: String (reference to Work)
- lineCount: Int

#### TextLine
- lineNumber: Int
- text: String
- words: List<Word>

#### Word
- text: String (the actual word)
- lemma: String (dictionary form)
- startOffset: Int
- endOffset: Int

### 3. Key Classes Implementation Status

#### ✅ Completed:
- MainActivity: Shows Greek/Latin selection
- LanguageAdapter: Simple list adapter for languages
- AuthorListActivity: Loads and displays authors
- AuthorAdapter: List adapter for authors
- TextViewerActivity: Basic text display with pagination buttons
- TextLineAdapter: Makes each word clickable
- PerseusXmlParser: Parses CTS XML files for authors/works

#### ❌ TODO:
- WorkListActivity: List works for an author
- BookListActivity: List books/chapters for a work
- Line range selection UI
- DictionaryActivity: Show word definitions from LSJ
- LemmaOccurrencesActivity: Search all occurrences
- Database setup (Room)
- Dictionary data integration
- Actual Perseus data processing

### 4. XML Parser Details

The `PerseusXmlParser` class handles:
- Reading __cts__.xml files from assets
- Extracting author names (prefers English)
- Extracting work titles
- Parsing text content with line numbers

Expected file structure:
```
data-sources/
  canonical-greekLit/data/
    tlg0012/              # Author directory
      __cts__.xml         # Author metadata
      tlg001/             # Work directory
        __cts__.xml       # Work metadata
        *.xml             # Text files
```

### 5. Dependencies Added

In app/build.gradle:
- androidx.core:core-ktx:1.12.0
- androidx.appcompat:appcompat:1.6.1
- com.google.android.material:material:1.10.0
- androidx.constraintlayout:constraintlayout:2.1.4
- androidx.recyclerview:recyclerview:1.3.2
- androidx.room:room-runtime:2.6.0 (for future database)
- com.fasterxml.woodstox:woodstox-core:6.5.1 (XML parsing)
- org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3

### 6. Current Issues/Limitations

1. **Data Access**: The app expects Perseus data in assets folder, but currently reads from data-sources/
2. **No Dictionary Data**: LSJ dictionary data needs to be integrated
3. **No Database**: Currently parsing XML on-demand (inefficient)
4. **Incomplete Navigation**: Only Language → Author implemented
5. **Mock Data**: TextViewerActivity shows placeholder text

### 7. Next Implementation Steps

1. **Complete Navigation Chain**:
   - Implement WorkListActivity (copy pattern from AuthorListActivity)
   - Implement BookListActivity
   - Add line range selection dialog/activity

2. **Data Processing**:
   - Create scripts to process Perseus XML into efficient format
   - Set up Room database schema
   - Pre-populate database with processed data

3. **Dictionary Integration**:
   - Find/process LSJ dictionary data
   - Create dictionary database tables
   - Implement DictionaryActivity UI

4. **Text Display**:
   - Connect actual Perseus text data
   - Implement proper pagination
   - Add text formatting (preserve line breaks, etc.)

5. **Search Features**:
   - Implement lemma indexing
   - Create search UI
   - Add corpus-wide search functionality

### 8. File Patterns to Follow

When implementing new activities:
```kotlin
class NewActivity : AppCompatActivity() {
    private lateinit var binding: ActivityNewBinding
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityNewBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        // Get intent extras
        // Set up RecyclerView
        // Load data in coroutine
    }
}
```

### 9. Testing the Current State

To test what's implemented:
1. Build and run the app
2. Select a language (Greek or Latin)
3. View the author list (currently parsing from XML)
4. Click an author (will crash as WorkListActivity not implemented)

### 10. Important Constraints

- NO internet permissions (100% offline)
- Do NOT modify data-sources/ directory
- Must handle large text files efficiently
- Support both Greek (tlg) and Latin (phi) texts
- Clickable words for dictionary lookup
- Line-by-line text display with numbers