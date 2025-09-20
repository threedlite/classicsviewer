# iOS Classics Viewer

## Status: ✅ FULLY FUNCTIONAL & TESTED

The iOS app is complete and ready for use. All build and deployment processes have been tested and documented.

## Quick Start

### Automated Build & Deploy (Recommended)
```bash
cd /path/to/classicsviewer/ios
./build_ios.sh
```

This single command will:
- Build the app for iOS Simulator
- Boot and open the simulator
- Install and launch the app
- Show verification commands

### Manual Build & Deploy
```bash
# 1. List available simulators
xcrun simctl list devices iPhone

# 2. Build for specific simulator
xcodebuild -scheme ClassicsViewer \
    -project ClassicsViewer.xcodeproj \
    -destination 'platform=iOS Simulator,name=iPhone 16' \
    build

# 3. Install and launch
xcrun simctl boot "iPhone 16"
open -a Simulator
xcrun simctl install booted "$(find ~/Library/Developer/Xcode/DerivedData -name "ClassicsViewer.app" -path "*/Debug-iphonesimulator/*" | head -1)"
xcrun simctl launch booted com.classicsviewer.app
```

### Using Xcode IDE
```bash
# Open project in Xcode
./open_in_xcode.sh
# OR
open ClassicsViewer.xcodeproj

# Then build and run with Cmd+R
```

## Documentation

- **[BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md)** - Complete build and deployment guide
- **[iOS_README.md](iOS_README.md)** - Detailed project overview and architecture
- **[iOS_Project_Plan.md](iOS_Project_Plan.md)** - Original development plan

## Requirements

- **Xcode**: 16.4+ (tested and working)
- **iOS**: 16.1+ deployment target
- **macOS**: 15.6+
- **Dependencies**: Auto-resolved via Swift Package Manager

## Project Status

✅ **All Android features implemented**:
- Offline Perseus Digital Library texts (100+ authors)
- Full-text search with normalization
- Word lookup with lemmatization
- Translation viewing and alignment
- Bookmarks and settings
- Database import/export
- SwiftUI native interface

✅ **Build system tested and documented**:
- Command line build process
- Automated deployment script
- Simulator testing
- Physical device deployment

## Performance

- **Build Time**: 30-60 seconds (clean)
- **App Launch**: 5-10 seconds (first launch), 2-3 seconds (subsequent)
- **Database**: 1.4GB Perseus texts, auto-extracted on first launch

The iOS app maintains complete feature parity with the Android version while following iOS design patterns and utilizing SwiftUI capabilities.

