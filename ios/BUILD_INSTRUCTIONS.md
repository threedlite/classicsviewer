# iOS Build Instructions

## Prerequisites
- Xcode 16.4 or later (tested with 16.4-16F6)
- iOS 16.1+ deployment target (minimum supported)
- macOS 15.6 or later
- iPhone/iPad simulator or physical device

## Project Structure

The iOS app uses a standard Xcode project with Swift Package Manager for dependencies:

```
ios/
├── ClassicsViewer.xcodeproj/        # Main Xcode project
├── ClassicsViewer/                  # Source code
│   ├── ClassicsViewerApp.swift      # App entry point
│   ├── Database/                    # Database management
│   │   ├── DatabaseManager.swift    # Core database connection
│   │   ├── DatabaseExtractor.swift  # ZIP extraction
│   │   ├── DatabaseValidator.swift  # Schema validation
│   │   └── ...DAOs                 # Data access objects
│   ├── Models/                      # Data models matching Android schema
│   ├── ViewModels/                  # MVVM view models
│   ├── Views/                       # SwiftUI views
│   ├── Utilities/                   # Helper classes
│   └── Resources/                   # App bundle resources
├── build.log                        # Build output log
├── open_in_xcode.sh                # Quick open script
└── BUILD_INSTRUCTIONS.md            # This file
```

## Building the App

### Method 1: Command Line Build (Recommended)

#### Step 1: Navigate to iOS Directory
```bash
cd /path/to/classicsviewer/ios
```

#### Step 2: List Available Simulators
```bash
xcrun simctl list devices iPhone
```
This will show available simulators like:
- iPhone 16 Pro
- iPhone 16 Plus
- iPhone 16
- etc.

#### Step 3: Clean Build (if needed)
```bash
xcodebuild -scheme ClassicsViewer \
    -project ClassicsViewer.xcodeproj \
    -destination 'platform=iOS Simulator,name=iPhone 16' \
    clean
```

#### Step 4: Build the App
For quick builds:
```bash
xcodebuild -scheme ClassicsViewer \
    -project ClassicsViewer.xcodeproj \
    -destination 'platform=iOS Simulator,name=iPhone 16' \
    build
```

For background builds (recommended for CI/automation):
```bash
nohup xcodebuild -scheme ClassicsViewer \
    -project ClassicsViewer.xcodeproj \
    -destination 'platform=iOS Simulator,name=iPhone 16' \
    clean build > build.log 2>&1 &
```

Monitor build progress:
```bash
tail -f build.log
```

### Method 2: Using Xcode IDE

1. **Open Project**:
   ```bash
   ./open_in_xcode.sh
   ```
   Or manually:
   ```bash
   open ClassicsViewer.xcodeproj
   ```

2. **Configure Build Settings**:
   - Select ClassicsViewer scheme
   - Choose target simulator or device
   - Ensure deployment target is iOS 16.1+

3. **Build and Run**:
   - Press Cmd+R to build and run
   - Or Cmd+B to build only

## Deploying to Simulator

### Step 1: Boot Simulator
```bash
# List available simulators
xcrun simctl list devices iPhone

# Boot specific simulator (replace with available device)
xcrun simctl boot "iPhone 16"

# Open Simulator app
open -a Simulator
```

### Step 2: Install App on Simulator
```bash
# Install the built app
xcrun simctl install booted "/Users/$USER/Library/Developer/Xcode/DerivedData/ClassicsViewer-*/Build/Products/Debug-iphonesimulator/ClassicsViewer.app"
```

**Note**: The actual DerivedData path will vary. You can find it in the build output or use:
```bash
# Find the exact path
find ~/Library/Developer/Xcode/DerivedData -name "ClassicsViewer.app" -path "*/Debug-iphonesimulator/*" | head -1
```

### Step 3: Launch App
```bash
# Launch the app on simulator
xcrun simctl launch booted com.classicsviewer.app
```

The app should now be running on the simulator with process output showing the assigned PID.

## Complete Build and Deploy Script

Here's the complete process as a single script:

```bash
#!/bin/bash
set -e

# Configuration
SCHEME="ClassicsViewer"
PROJECT="ClassicsViewer.xcodeproj"
SIMULATOR="iPhone 16"
BUNDLE_ID="com.classicsviewer.app"

echo "🏗️  Building iOS Classics Viewer..."

# Navigate to iOS directory
cd "$(dirname "$0")"

# Check if simulator exists
if ! xcrun simctl list devices | grep -q "$SIMULATOR"; then
    echo "❌ Simulator '$SIMULATOR' not found. Available simulators:"
    xcrun simctl list devices iPhone
    exit 1
fi

# Boot simulator
echo "🚀 Booting simulator: $SIMULATOR"
xcrun simctl boot "$SIMULATOR" 2>/dev/null || echo "Simulator already running"

# Open Simulator app
open -a Simulator

# Build the app
echo "🔨 Building app..."
xcodebuild -scheme "$SCHEME" \
    -project "$PROJECT" \
    -destination "platform=iOS Simulator,name=$SIMULATOR" \
    clean build

# Find the built app
APP_PATH=$(find ~/Library/Developer/Xcode/DerivedData -name "ClassicsViewer.app" -path "*/Debug-iphonesimulator/*" | head -1)

if [ -z "$APP_PATH" ]; then
    echo "❌ Could not find built app"
    exit 1
fi

echo "📱 Installing app: $APP_PATH"

# Install the app
xcrun simctl install booted "$APP_PATH"

# Launch the app
echo "🎯 Launching app..."
PID=$(xcrun simctl launch booted "$BUNDLE_ID")

echo "✅ App launched successfully: $PID"
echo "📱 App is now running on $SIMULATOR simulator"
```

## Database Setup

The app requires the Perseus database file. Current database file:
- **Location**: `ClassicsViewer/Resources/perseus_texts.db.zip`
- **Size**: ~300MB compressed, ~1.4GB uncompressed
- **Format**: ZIP-compressed SQLite database

### Database Management Options:

1. **Use Bundled Database**: The app includes a sample database in Resources/
2. **Import External Database**: Use Settings → Database Management to import .db or .zip files
3. **Revert to Original**: Use "Revert to Bundled Database" in settings

## Dependencies

The app uses Swift Package Manager with these dependencies:

### SQLite.swift
- **Repository**: https://github.com/stephencelis/SQLite.swift
- **Version**: 0.15.4
- **Purpose**: Type-safe SQLite interface for Swift

### swift-toolchain-sqlite
- **Repository**: https://github.com/swiftlang/swift-toolchain-sqlite
- **Version**: 1.0.4
- **Purpose**: SQLite toolchain support

Dependencies are automatically resolved during build.

## Build Configuration

### Xcode Project Settings:
- **Bundle Identifier**: com.classicsviewer.app
- **Development Team**: FAKETEAMID (simulator only)
- **Deployment Target**: iOS 16.1
- **Swift Version**: 5.9+
- **Build Configuration**: Debug (for simulator)

### Build Script Phases:
1. **Check Database**: Validates database file exists in Resources
2. **SwiftUI Preview Support**: Enables Xcode previews
3. **Package Dependencies**: Resolves Swift packages

## Testing on Physical Device

### Prerequisites:
1. **Apple Developer Account** (free or paid)
2. **Development Certificate** installed in Xcode
3. **Device registered** for development

### Steps:
1. Connect device via USB
2. Trust computer on device
3. Select device in Xcode
4. Set valid development team in project settings
5. Build and run (Cmd+R)

## Troubleshooting

### Build Errors

**"Unknown build action 'run'"**:
- Use `build` action, then install manually with `simctl`
- Command line xcodebuild doesn't support `run` action

**"Invalid device: iPhone 15"**:
- Check available simulators: `xcrun simctl list devices iPhone`
- Use exact simulator name from the list

**Package resolution fails**:
- Reset package caches in Xcode: File → Packages → Reset Package Caches
- Or command line: `xcodebuild -resolvePackageDependencies`

**Build takes too long**:
- Use background build: `nohup xcodebuild ... > build.log 2>&1 &`
- Monitor with: `tail -f build.log`

### Database Issues

**App crashes on launch**:
- Check database file exists in Resources/
- Verify ZIP integrity: `unzip -t ClassicsViewer/Resources/perseus_texts.db.zip`
- Check console logs for database errors

**Database extraction fails**:
- Ensure sufficient storage space (1.4GB+ free)
- Check file permissions
- Use Database Management screen for detailed error info

### Simulator Issues

**Simulator won't boot**:
- Reset simulator: `xcrun simctl erase "iPhone 16"`
- Restart Simulator app
- Check macOS storage space

**App won't install**:
- Clean build folder: `xcodebuild -scheme ClassicsViewer clean`
- Reset simulator: `xcrun simctl erase "iPhone 16"`
- Rebuild and try again

## Performance Notes

### Build Times:
- **Clean build**: ~30-60 seconds
- **Incremental build**: ~10-30 seconds
- **Package resolution**: ~10-20 seconds (first time)

### App Launch:
- **First launch**: ~5-10 seconds (database extraction)
- **Subsequent launches**: ~2-3 seconds
- **Database size**: 1.4GB uncompressed in app container

## Verification Commands

After successful deployment, verify the app is working:

```bash
# Check if app is installed
xcrun simctl listapps booted | grep classicsviewer

# Check app logs
xcrun simctl spawn booted log stream --predicate 'processImagePath contains "ClassicsViewer"'

# Get app container path
xcrun simctl get_app_container booted com.classicsviewer.app

# Check database extraction
ls -la "$(xcrun simctl get_app_container booted com.classicsviewer.app data)/Documents/"
```

## Automation Scripts

All build and deployment steps have been tested and can be automated. See the complete script example above or use the individual commands for CI/CD integration.

The process is reliable and repeatable across different macOS systems with Xcode installed.