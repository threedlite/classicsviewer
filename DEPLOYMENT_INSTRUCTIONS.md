# Deployment Instructions - Expanded Database

## APK Ready for Installation

The debug APK with the expanded database (100 Greek authors) has been built successfully.

**APK Location**: `app/build/outputs/apk/debug/app-debug.apk`
**APK Size**: 342MB (includes compressed database)

## Installation Steps

### Option 1: Using ADB (when device is connected)
```bash
# 1. Connect your Android device via USB
# 2. Enable USB debugging on your device
# 3. Run these commands:

adb install app/build/outputs/apk/debug/app-debug.apk
adb shell pm clear com.classicsviewer.app.debug
```

### Option 2: Manual Installation
1. Transfer the APK to your phone:
   - Email it to yourself
   - Use Google Drive/Dropbox
   - Use Android File Transfer
   
2. On your phone:
   - Open the APK file
   - Allow installation from unknown sources if prompted
   - Install the app

3. **IMPORTANT**: Clear app data after installation:
   - Go to Settings → Apps → Classics Viewer
   - Tap "Storage & cache"
   - Tap "Clear storage" or "Clear data"

## What's New in This Build

### Database Contents:
- **103 authors** (100 Greek + 3 Latin)
- **845 works**
- **914,504 lines of text**
- **175,610 translation segments**
- **28,647 dictionary entries**

### Major Greek Authors Included:
- Homer (Iliad, Odyssey)
- Plato (all dialogues)
- Aristotle (major works)
- Plutarch (Lives and Moralia)
- Xenophon (complete works)
- All Greek dramatists (Aeschylus, Sophocles, Euripides, Aristophanes)
- Historians (Herodotus, Thucydides, Polybius)
- And 80+ more!

### Database Size:
- Compressed in APK: 340MB
- Extracted on device: 1.5GB
- First launch will take ~6-7 seconds to extract

## Testing the Expanded Database

1. Launch the app
2. Wait for database extraction (progress bar will show)
3. Select Greek language
4. Browse the author list - you should see 100 authors
5. Test various authors and works
6. Verify translations are properly aligned

## Troubleshooting

If you encounter issues:

1. **App crashes on startup**: Clear app data
   ```bash
   adb shell pm clear com.classicsviewer.app.debug
   ```

2. **Authors not showing**: Force stop and restart
   ```bash
   adb shell am force-stop com.classicsviewer.app.debug
   ```

3. **Check logs**:
   ```bash
   adb logcat | grep -E "AssetPackDatabaseHelper|MainActivity"
   ```

## Performance Notes

With the expanded database:
- Initial author list load may take 1-2 seconds
- Search operations will be slightly slower
- Dictionary lookups remain fast (indexed)
- Overall app remains responsive

The app is now ready with the complete Perseus Digital Library Greek collection!