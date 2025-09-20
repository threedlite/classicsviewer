# iOS Classics Viewer

iOS version of the Classics Viewer app for reading classical Greek and Latin texts offline.

## Project Structure

```
ios/ClassicsViewer/
├── ClassicsViewerApp.swift      # Main app entry point
├── Models/                      # Data models
│   └── DatabaseModels.swift     # Core data structures
├── Views/                       # SwiftUI views
│   ├── ContentView.swift        # Root view
│   ├── LanguageSelectionView.swift
│   ├── AuthorListView.swift
│   ├── BookListView.swift
│   ├── ReaderView.swift
│   ├── SearchView.swift
│   ├── WordDetailView.swift
│   └── SettingsView.swift
├── ViewModels/                  # View models
│   ├── AuthorListViewModel.swift
│   └── ReaderViewModel.swift
├── Database/                    # Database layer
│   ├── DatabaseManager.swift
│   ├── AuthorDAO.swift
│   ├── BookDAO.swift
│   ├── LineDAO.swift
│   ├── TranslationDAO.swift
│   ├── WordDAO.swift
│   └── LemmaDAO.swift
└── Resources/                   # Assets and resources
```

## Setup Instructions

### Prerequisites
- **Xcode**: 16.4 or later (tested and working)
- **iOS Deployment Target**: 16.1+ (minimum supported)
- **macOS**: 15.6 or later
- **Dependencies**: Automatically managed via Swift Package Manager

### Quick Start
1. **Clone and Navigate**:
   ```bash
   cd /path/to/classicsviewer/ios
   ```

2. **Build and Deploy**:
   ```bash
   # One-command build and deploy
   ./build_ios.sh
   ```
   Or manually:
   ```bash
   # List available simulators
   xcrun simctl list devices iPhone
   
   # Build for specific simulator
   xcodebuild -scheme ClassicsViewer \
       -project ClassicsViewer.xcodeproj \
       -destination 'platform=iOS Simulator,name=iPhone 16' \
       build
   
   # Install and launch
   xcrun simctl install booted "/path/to/built/ClassicsViewer.app"
   xcrun simctl launch booted com.classicsviewer.app
   ```

3. **Database Setup**:
   - **Bundled Database**: Included in `ClassicsViewer/Resources/perseus_texts.db.zip`
   - **Size**: ~300MB compressed, extracts to ~1.4GB
   - **First Launch**: App automatically extracts database (~5-10 seconds)

### Dependencies (Automatic)
- **SQLite.swift** v0.15.4: Type-safe SQLite interface
- **swift-toolchain-sqlite** v1.0.4: SQLite toolchain support

## Audio Package Management

#### How to Import Audio Files in Simulator:

1. **Get the app's container path**:
   ```bash
   # Find the app container for the current simulator
   CONTAINER=$(xcrun simctl get_app_container booted com.classicsviewer.app data)
   echo "App container: $CONTAINER"
   ```

2. **Copy your file to the app's Documents folder**:
   ```bash
   # Copy audio ZIP file to app's Documents directory
   cp /path/to/your/audio.zip "$CONTAINER/Documents/"
   
   # Example with the Homer Iliad audio package:
   cp audio/homer_iliad_chamberlain_audio.zip "$CONTAINER/Documents/"
   ```

3. **Import in the app**:
   - Open ClassicsViewer app
   - Go to Settings → Audio Management
   - Tap the "+" button → "Import from Path"
   - The filename will be pre-populated (e.g., `homer_iliad_chamberlain_audio.zip`)
   - Tap "Import"

#### Important Notes:
- **App containers change**: Each time you reinstall the app, it gets a new container ID
- **Radio button behavior**: Only one audio package can be active at a time
- **Automatic activation**: Newly imported packages automatically become active

#### Alternative: Using specific simulator ID:
```bash
# If you know your simulator ID (e.g., 93B0574C-3ED9-47BA-9290-635452C29A19)
SIMULATOR_ID="93B0574C-3ED9-47BA-9290-635452C29A19"
CONTAINER=$(xcrun simctl get_app_container $SIMULATOR_ID com.classicsviewer.app data)
cp audio/homer_iliad_chamberlain_audio.zip "$CONTAINER/Documents/"
```

## Database Integration

The iOS app uses the same SQLite database as the Android version:
- No modifications to the database schema
- Direct SQLite access using SQLite.swift
- Same query patterns as Android DAOs

## TODO
-- Integrate with TestFlight for beta testing
-- Prepare App Store submission materials

## Testing & Deployment

### Simulator Testing (Recommended)
1. **Automated Build & Deploy**:
   ```bash
   cd /path/to/classicsviewer/ios
   ./build_ios.sh  # Complete build and deployment
   ```

2. **Manual Testing**:
   ```bash
   # Build
   xcodebuild -scheme ClassicsViewer -project ClassicsViewer.xcodeproj \
       -destination 'platform=iOS Simulator,name=iPhone 16' build
   
   # Deploy
   xcrun simctl boot "iPhone 16"
   xcrun simctl install booted "$(find ~/Library/Developer/Xcode/DerivedData -name "ClassicsViewer.app" -path "*/Debug-iphonesimulator/*" | head -1)"
   xcrun simctl launch booted com.classicsviewer.app
   ```

### Physical Device Testing
1. Connect iPhone/iPad via USB
2. Open `ClassicsViewer.xcodeproj` in Xcode
3. Select your device
4. Set development team in project settings
5. Build and run (Cmd+R)

### Verification
After deployment, verify the app works:
```bash
# Check installation
xcrun simctl listapps booted | grep classicsviewer

# Monitor logs
xcrun simctl spawn booted log stream --predicate 'processImagePath contains "ClassicsViewer"'

# Check database extraction
xcrun simctl get_app_container booted com.classicsviewer.app
```

### Performance Expectations
- **Build Time**: ~30-60 seconds (clean), ~10-30 seconds (incremental)
- **First Launch**: ~5-10 seconds (database extraction)
- **Subsequent Launches**: ~2-3 seconds
- **Database Size**: ~1.4GB extracted in app container

The app should maintain feature parity with the Android version while following iOS design patterns and leveraging SwiftUI capabilities. 
