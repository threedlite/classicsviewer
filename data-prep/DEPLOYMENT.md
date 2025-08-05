# Deploying Perseus Database to Android

## Quick Start

The simplest way to deploy the database:

```bash
# Connect your Android device with USB debugging enabled
adb push perseus_texts.db /storage/emulated/0/Download/
```

Then in your Android app, copy the database from Downloads to your app's database directory.

## Deployment Scripts

We provide two deployment scripts:

### 1. Simple Deployment (`deploy_simple.sh`)

```bash
./deploy_simple.sh
```

This pushes the database to your device's Download folder. You'll need to move it to the correct location manually or update your app to read from Downloads.

### 2. OBB Deployment (`deploy_to_android.sh`)

```bash
# Edit the script first to set your app's package name
nano deploy_to_android.sh
# Change PACKAGE="com.example.classicsviewer" to your actual package name

./deploy_to_android.sh
```

This creates an OBB (Opaque Binary Blob) file structure that Android apps can access without special permissions.

## Manual Deployment Options

### Option 1: Direct Push to App Directory (Requires Root or Debuggable App)

```bash
# Replace com.example.classicsviewer with your package name
adb push perseus_texts.db /data/data/com.example.classicsviewer/databases/
```

### Option 2: Use Android Studio

1. Place `perseus_texts.db` in your app's `assets` folder
2. On first run, copy from assets to the app's database directory

### Option 3: Download from URL

Host the database file and have your app download it on first run.

## Database Info

- **File**: perseus_texts.db
- **Size**: ~67 MB
- **Format**: SQLite database compatible with Android Room
- **Content**: 
  - 16 authors
  - 271 works  
  - 431 books
  - 310,718 text lines
  - 81,648 translation segments
  - 94.1% of works have English translations

## Troubleshooting

If the database doesn't load:

1. **Clear app data**: Settings → Apps → Your App → Clear Data
2. **Check permissions**: Ensure your app has storage permissions if reading from external storage
3. **Check file location**: Verify the database is in the expected location
4. **Check Room schema**: Ensure your Room entities match the database schema
5. **Enable logging**: Add logging to see where your app is looking for the database

## Room Entity Classes

Make sure your Android app has matching Room entities:

```kotlin
@Entity(tableName = "authors")
data class Author(
    @PrimaryKey val id: String,
    val name: String,
    val name_alt: String?,
    val language: String
)

@Entity(tableName = "works")
data class Work(
    @PrimaryKey val id: String,
    val author_id: String,
    val title: String,
    val title_alt: String?,
    val title_english: String?,
    val type: String?,
    val urn: String?,
    val description: String?
)

@Entity(tableName = "books")
data class Book(
    @PrimaryKey val id: String,
    val work_id: String,
    val book_number: Int,
    val label: String?,
    val start_line: Int?,
    val end_line: Int?,
    val line_count: Int?
)

@Entity(tableName = "text_lines")
data class TextLine(
    @PrimaryKey val id: Long,
    val book_id: String,
    val line_number: Int,
    val line_text: String,
    val line_xml: String?,
    val speaker: String?
)

@Entity(tableName = "translation_segments")
data class TranslationSegment(
    @PrimaryKey val id: Long,
    val book_id: String,
    val start_line: Int,
    val end_line: Int,
    val translation_text: String,
    val translator: String?
)
```