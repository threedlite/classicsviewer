# Debug Setup for Classics Viewer

## Problem
The data-sources folder contains large text datasets that would be inefficient to copy to the device repeatedly during development.

## Solution Strategy

### 1. Mock Data for UI Development
Create a mock data provider that returns sample data for testing UI and navigation:

```kotlin
// In app/src/debug/java/com/perseus/viewer/data/MockDataProvider.kt
object MockDataProvider {
    fun getMockAuthors(language: String): List<Author> {
        return when(language) {
            "tlg" -> listOf(
                Author("tlg0012", "Homer", "tlg"),
                Author("tlg0003", "Aeschylus", "tlg"),
                Author("tlg0011", "Sophocles", "tlg")
            )
            "phi" -> listOf(
                Author("phi0448", "Caesar", "phi"),
                Author("phi0690", "Virgil", "phi"),
                Author("phi0474", "Cicero", "phi")
            )
            else -> emptyList()
        }
    }
    
    fun getMockWorks(authorId: String): List<Work> {
        return when(authorId) {
            "tlg0012" -> listOf(
                Work("tlg001", "Iliad", "tlg0012", "tlg"),
                Work("tlg002", "Odyssey", "tlg0012", "tlg")
            )
            "phi0690" -> listOf(
                Work("phi001", "Aeneid", "phi0690", "phi"),
                Work("phi002", "Georgics", "phi0690", "phi")
            )
            else -> emptyList()
        }
    }
    
    fun getMockTextLines(startLine: Int, endLine: Int): List<TextLine> {
        return (startLine..endLine).map { lineNum ->
            TextLine(
                lineNumber = lineNum,
                text = "μῆνιν ἄειδε θεὰ Πηληϊάδεω Ἀχιλῆος line $lineNum",
                words = emptyList()
            )
        }
    }
}
```

### 2. Build Variants
Set up debug and release build variants:

```gradle
// In app/build.gradle
android {
    buildTypes {
        debug {
            buildConfigField "boolean", "USE_MOCK_DATA", "true"
            applicationIdSuffix ".debug"
        }
        release {
            buildConfigField "boolean", "USE_MOCK_DATA", "false"
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
}
```

### 3. Minimal Test Dataset
Create a minimal subset of texts for debugging:

```
app/src/debug/assets/
├── test-data/
│   ├── greek/
│   │   ├── homer_iliad_book1_lines1-100.xml
│   │   └── metadata.json
│   └── latin/
│       ├── virgil_aeneid_book1_lines1-100.xml
│       └── metadata.json
```

### 4. Data Access Abstraction
Create an interface to switch between real and mock data:

```kotlin
// DataRepository.kt
interface DataRepository {
    suspend fun getAuthors(language: String): List<Author>
    suspend fun getWorks(authorId: String): List<Work>
    suspend fun getTextLines(workId: String, bookId: String, startLine: Int, endLine: Int): List<TextLine>
}

// MockDataRepository.kt (debug)
class MockDataRepository : DataRepository {
    override suspend fun getAuthors(language: String) = MockDataProvider.getMockAuthors(language)
    // ... other methods
}

// RealDataRepository.kt (release)
class RealDataRepository(private val parser: PerseusXmlParser) : DataRepository {
    // Real implementation
}
```

### 5. Gradle Task for One-Time Copy
Create a gradle task to copy data only when needed:

```gradle
task copyPerseusData(type: Copy) {
    from '../data-sources'
    into 'src/main/assets/data-sources'
    include '**/__cts__.xml'  // Only copy metadata files for development
}

task copyFullPerseusData(type: Copy) {
    from '../data-sources'
    into 'src/main/assets/data-sources'
    // Copies everything for release builds
}
```

### 6. Remote Loading Option (Advanced)
For development, load data from your development machine:

```kotlin
// DebugDataLoader.kt
class DebugDataLoader {
    private val baseUrl = "http://192.168.4.xxx:8080" // Your dev machine
    
    suspend fun loadText(path: String): String {
        // Load from local server during debug
    }
}
```

## Recommended Approach

1. **For UI Development**: Use mock data (Option 1)
2. **For Integration Testing**: Use minimal test dataset (Option 3)
3. **For Final Testing**: Use gradle task to copy full data once (Option 5)

## Implementation Steps

1. Create debug source set: `app/src/debug/java/`
2. Add MockDataProvider
3. Update activities to use DataRepository interface
4. Add BuildConfig check to switch implementations
5. Create minimal test files for real data testing

## Debug Configuration

```kotlin
// In your activities
class AuthorListActivity : AppCompatActivity() {
    private lateinit var repository: DataRepository
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        repository = if (BuildConfig.USE_MOCK_DATA) {
            MockDataRepository()
        } else {
            RealDataRepository(PerseusXmlParser(this))
        }
        
        loadAuthors()
    }
}
```

This approach allows rapid iteration without copying large datasets while maintaining the ability to test with real data when needed.