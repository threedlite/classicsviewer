# Classics Viewer Audio System Documentation

## Overview
The Classics Viewer app supports line-by-line audio playback for Greek and Latin texts, enabling users to hear the proper pronunciation while reading. The audio system includes import functionality, playback controls, and continuous playback mode.

## Audio Package Structure

### Package Format
Audio packages are ZIP files containing:
- MP4 audio files (AAC codec)
- Organized in directory structure: `Author/Work/book_N/line_X.mp4`
- Example: `Homer/Iliad/book_1/line_1.mp4`

### Supported Formats
- **MP4** (preferred): AAC audio codec, widely supported
- **MIDI** files are converted to MP4 before packaging (see conversion guide)

## Database Schema

### Audio Tables
```sql
-- Audio packages table
CREATE TABLE audio_packages (
    id INTEGER PRIMARY KEY,
    package_name TEXT NOT NULL,
    zip_filename TEXT NOT NULL,
    total_files INTEGER NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    is_active INTEGER DEFAULT 0,
    import_date INTEGER NOT NULL
);

-- Audio mappings table
CREATE TABLE audio_mappings (
    id INTEGER PRIMARY KEY,
    package_id INTEGER NOT NULL,
    author_name TEXT NOT NULL,
    work_title TEXT NOT NULL,
    book_number INTEGER NOT NULL,
    line_number INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    file_format TEXT NOT NULL,
    duration_ms INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (package_id) REFERENCES audio_packages(id)
);
```

## App Components

### 1. Audio Management Activity
- **Location**: `app/src/main/java/com/classicsviewer/app/audio/AudioManagementActivity.kt`
- **Purpose**: Lists imported audio packages, allows activation/deletion
- **Features**:
  - Import progress UI with percentage display
  - Package activation (only one active at a time)
  - Package deletion with storage cleanup

### 2. Audio Import Service
- **Location**: `app/src/main/java/com/classicsviewer/app/audio/AudioImportService.kt`
- **Purpose**: Background service for importing large audio packages
- **Features**:
  - Foreground service with notification
  - Progress broadcasts to update UI
  - Handles 15,000+ files efficiently
  - Error recovery for corrupted files
  - Book-by-book progress reporting

### 3. Audio Playback Service
- **Location**: `app/src/main/java/com/classicsviewer/app/audio/AudioPlaybackService.kt`
- **Purpose**: Handles actual audio playback using ExoPlayer
- **Features**:
  - Play/pause/stop controls
  - Playback completion callbacks
  - Error handling with automatic skip
  - Continuous playback support

### 4. Text Viewer Integration
- **Location**: `app/src/main/java/com/classicsviewer/app/TextViewerPagerActivity.kt`
- **Features**:
  - Play buttons on individual lines (when audio available)
  - Continuous playback mode toggle in menu
  - Auto-advance to next line with audio
  - Preference persistence

## Import Process

### Package Import Flow
1. User selects ZIP file from file picker
2. AudioImportService starts as foreground service
3. Service extracts ZIP to app's internal storage
4. Each file is parsed to extract metadata (author, work, book, line)
5. Metadata is inserted into database
6. Progress is broadcast to UI (showing book X of 24, % complete)
7. Package list refreshes when complete

### File Path Parsing
Files are parsed to extract:
- Author name
- Work title  
- Book number (from `book_N`)
- Line number (from `line_X.mp4`)

Example: `Homer/Iliad/book_1/line_100.mp4`
- Author: Homer
- Work: Iliad
- Book: 1
- Line: 100

## Continuous Playback Mode

### How It Works
1. User enables "Continuous Audio" from overflow menu
2. When a line finishes playing, system automatically:
   - Finds next line with available audio
   - Skips lines without audio
   - Plays next available audio file
3. On error, skips to next line (won't get stuck)
4. Stops at end of current page (user must navigate)

### Error Handling
- Missing files: Skip to next
- Corrupted files: Skip to next
- Network issues: N/A (all files are local)
- Shows user-friendly error messages

## Audio File Conversion

### MIDI to MP4 Conversion
For Lyresong MIDI files, conversion process:

1. **Install tools**:
```bash
brew install timidity ffmpeg
```

2. **Convert MIDI to WAV**:
```bash
timidity input.mid -Ow -o output.wav
```

3. **Convert WAV to MP4 with volume boost**:
```bash
ffmpeg -i output.wav -filter:a "volume=1.5" -c:a aac -b:a 128k output.mp4
```

### Batch Conversion Script
See `/audio/MIDI_CONVERSION_GUIDE.md` for complete batch processing script.

## Homer's Iliad Audio Package

### Package Details
- **Name**: `homer_iliad_complete.zip`
- **Size**: ~975MB compressed
- **Contents**: All 24 books, 15,693 audio files
- **Source**: https://hypotactic.com/homer/audio/

### Book Line Counts
```
Book 1: 611    Book 9: 713     Book 17: 761
Book 2: 877    Book 10: 579    Book 18: 617
Book 3: 461    Book 11: 848    Book 19: 424
Book 4: 544    Book 12: 471    Book 20: 503
Book 5: 909    Book 13: 837    Book 21: 611
Book 6: 529    Book 14: 522    Book 22: 515
Book 7: 482    Book 15: 746    Book 23: 897
Book 8: 565    Book 16: 867    Book 24: 804
```

### Download Scripts
- **Controlled download**: `/audio/download_iliad_controlled.sh`
  - Sequential downloads with rate limiting
  - Verification of file sizes
  - Progress logging

## Storage Management

### File Storage Locations
- **Audio files**: `/data/data/com.classicsviewer.app/files/audio/[package_id]_[package_name]/`
- **Database**: `/data/data/com.classicsviewer.app/databases/audio_data.db`

### Storage Cleanup
When deleting a package:
1. Remove database entries
2. Delete package directory recursively
3. Update UI to reflect removal

## Performance Considerations

### Large Package Import
- Uses foreground service to prevent Android from killing the process
- Shows progress notification with percentage
- Updates every 10 files to avoid notification spam
- Batch database inserts in transaction

### Memory Management
- Files extracted one at a time (not loading entire ZIP)
- Audio files played directly from storage
- No caching of audio data in memory

## Testing

### Test Packages
1. **Lyresong** (small): ~200 files for testing
2. **Homer Book 7** (medium): 482 files
3. **Full Iliad** (large): 15,693 files

### Test Scenarios
- Import during low battery
- Import with storage nearly full
- Playback with missing files
- Continuous playback across pages
- App backgrounding during import
- Device rotation during playback

## Troubleshooting

### Common Issues

**Import hangs or shows no progress**
- Check logcat for errors
- Verify ZIP file integrity: `unzip -t package.zip`
- Ensure sufficient storage space

**Audio doesn't play**
- Verify package is activated (only one can be active)
- Check file exists in storage
- Verify audio format is MP4/AAC

**"Package already exists" error**
- Delete existing package first
- Or rename ZIP file before import

**Continuous playback stops unexpectedly**
- Check if reached end of page
- Look for error messages in snackbar
- Verify next lines have audio available

## Future Enhancements

### Potential Improvements
1. Cross-page continuous playback
2. Playback speed control
3. Audio download from server
4. Waveform visualization
5. Bookmarking with audio position
6. Export/share audio clips
7. Multiple active packages
8. Audio-text synchronization highlighting

## API Reference

### AudioRepository Methods
```kotlin
suspend fun getAudioForLineRange(
    authorName: String,
    workTitle: String,
    bookNumber: Int,
    startLine: Int,
    endLine: Int
): List<AudioMapping>

suspend fun getAllPackages(): List<AudioPackage>
suspend fun setActivePackage(packageId: Long): Boolean
suspend fun deletePackage(packageId: Long): Boolean
```

### AudioPlaybackService Methods
```kotlin
fun playAudio(file: File)
fun stopPlayback()
fun pausePlayback()
fun resumePlayback()
fun isPlaying(): Boolean
fun setPlaybackListener(listener: PlaybackListener)
```

## Build Requirements

### Android Manifest Permissions
```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />
```

### Dependencies
- ExoPlayer for audio playback
- Coroutines for async operations
- Room database for audio metadata

## Version History

### v1.0 - Initial Audio Support
- Basic audio playback for individual lines
- Audio package import
- Single package activation

### v1.1 - Continuous Playback
- Added continuous playback mode
- Improved import progress UI
- Better error handling
- Support for 15,000+ file packages

---

*Last Updated: August 2025*
*Author: Claude with user collaboration*