# Quick Start Guide for Debugging

## Setup Complete! 

The app is now configured to use mock data for debugging, avoiding the need to copy large text files to your phone.

## To Debug on Your Phone (192.168.4.209:45739):

1. **First Time Setup:**
   ```bash
   # Connect to your phone
   adb connect 192.168.4.209:45739
   
   # Build and install the debug version
   ./debug-install.sh
   ```

2. **Subsequent Updates:**
   ```bash
   # Just run the install script - it will rebuild and install
   ./debug-install.sh
   ```

3. **Launch the App:**
   ```bash
   adb -s 192.168.4.209:45739 shell am start -n com.perseus.viewer.debug/com.perseus.viewer.MainActivity
   ```

## What You'll See:

The debug version includes:
- Mock Greek authors: Homer, Aeschylus, Sophocles, Euripides, etc.
- Mock Latin authors: Caesar, Virgil, Cicero, Ovid, etc.
- Sample works for each author
- Sample text lines with clickable words
- Simulated loading delays for realistic testing

## Debug vs Release:

- **Debug APK**: Uses mock data, has `.debug` suffix
- **Release APK**: Will use real Perseus data (when implemented)

## Viewing Logs:

```bash
# View app logs
adb -s 192.168.4.209:45739 logcat -s ClassicsViewer

# Clear old logs
adb -s 192.168.4.209:45739 logcat -c
```

## Benefits of This Approach:

1. ✅ No large data transfers during development
2. ✅ Fast iteration - changes deploy quickly
3. ✅ Consistent test data
4. ✅ Can test all UI flows immediately
5. ✅ Easy to add new mock data as needed

## Next Steps:

The mock data system is in place. You can now:
1. Test the navigation flow
2. Implement missing activities (Work, Book, Dictionary)
3. Polish the UI
4. Add real data handling later