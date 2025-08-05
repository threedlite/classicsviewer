# Google Play Store Deployment Checklist

## Prerequisites

- [x] Google Play Developer account ($25 one-time fee)
- [ ] Release keystore created (`./create_release_keystore.sh`)
- [ ] keystore.properties file created with credentials

## App Assets

### Required Graphics
- [x] App Icon (512x512) - Already in app resources
- [x] Feature Graphic (1024x500) - `play-store-assets/feature_graphic.png`
- [x] Phone Screenshots (2-8) - `screenshots/` directory
- [ ] Optional: 7" tablet screenshots
- [ ] Optional: 10" tablet screenshots

### Store Listing
- [x] App name: Classics Viewer
- [x] Short description (80 chars)
- [x] Full description (4000 chars) - See `store_listing.txt`
- [ ] App category: Education
- [ ] Content rating: Everyone
- [ ] Contact email
- [ ] Privacy policy URL (required)

## Build Files

### AAB (Android App Bundle)
To create:
```bash
./build_release_aab.sh
```
Output: `classics-viewer-release-v1.0.aab`

### OBB Expansion File
- [x] Debug OBB: `data-prep/output/main.1.com.classicsviewer.app.debug.obb` (173MB)
- [x] Release OBB: `data-prep/output/main.1.com.classicsviewer.app.obb` (173MB)

## Deployment Steps

1. **Create Release Keystore** (if not done)
   ```bash
   ./create_release_keystore.sh
   ```

2. **Create keystore.properties**
   ```
   storePassword=YOUR_KEYSTORE_PASSWORD
   keyPassword=YOUR_KEY_PASSWORD
   keyAlias=classics-viewer-key
   storeFile=keystore/release-keystore.jks
   ```

3. **Build Release AAB**
   ```bash
   ./build_release_aab.sh
   ```

4. **Upload to Play Console**
   - Go to https://play.google.com/console
   - Create new app
   - Fill in store listing details
   - Upload AAB in Production release
   - Upload OBB as expansion file
   - Set up pricing (free)
   - Complete content rating questionnaire
   - Review and publish

## Important Notes

- **Keystore Security**: Never lose your keystore or passwords! Back them up securely.
- **Version Code**: Increment `versionCode` in `app/build.gradle` for each update
- **OBB Naming**: Must follow pattern `main.{versionCode}.{packageName}.obb`
- **Privacy Policy**: Required for apps that access device storage
- **Testing**: Test the release build thoroughly before publishing

## Post-Launch

- [ ] Monitor crash reports in Play Console
- [ ] Respond to user reviews
- [ ] Plan regular updates
- [ ] Consider implementing in-app feedback