# Forking and Rebranding Guide for Classics Viewer

This guide provides step-by-step instructions for creating an institution-specific or private labeled version of the Classics Viewer app.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Forking the Repository](#forking-the-repository)
3. [Renaming the Application](#renaming-the-application)
4. [Replacing App Icons](#replacing-app-icons)
5. [Customizing Branding](#customizing-branding)
6. [Customizing the Database](#customizing-the-database)
7. [Building and Testing](#building-and-testing)
8. [Publishing Your Version](#publishing-your-version)

## Prerequisites

Before starting, ensure you have:
- Android Studio installed (latest stable version)
- Git installed and configured
- Android SDK with API level 36 installed
- Python 3.x for database customization
- A Google Play Console account (if publishing to Play Store)

## Forking the Repository

### 1. Create Your Fork

```bash
# Clone the original repository
git clone https://github.com/[original-repo]/classicsviewer.git [your-institution-name]-classics
cd [your-institution-name]-classics

# Remove original remote
git remote remove origin

# Add your own repository as origin
git remote add origin https://github.com/[your-repo]/[your-institution-name]-classics.git

# Push to your repository
git push -u origin main
```

### 2. Create a Private Repository (Optional)

If you need a private version:
1. Create a new private repository on GitHub/GitLab
2. Follow the steps above but use your private repository URL

## Renaming the Application

### 1. Change the Application ID

The application ID must be unique on Google Play Store. Update it in multiple locations:

#### a. Update `app/build.gradle`:

```gradle
android {
    namespace 'edu.yourinstitution.classics'  // Change from com.classicsviewer.app
    
    defaultConfig {
        applicationId "edu.yourinstitution.classics"  // Change from com.classicsviewer.app
        // Keep the rest of the configuration
    }
}
```

#### b. Update Package Structure:

1. In Android Studio, right-click on `com.classicsviewer.app` package
2. Select "Refactor" → "Rename"
3. Change to your new package name (e.g., `edu.yourinstitution.classics`)
4. Select "Rename package" and "Search in comments and strings"
5. Click "Refactor"

#### c. Update Kotlin Files:

The refactoring should handle most files, but verify these key locations:
- All files in `app/src/main/java/`
- All test files in `app/src/test/` and `app/src/androidTest/`

### 2. Change the App Name

Edit `app/src/main/res/values/strings.xml`:

```xml
<resources>
    <string name="app_name">YourInstitution Classics</string>
    <!-- Keep other strings or customize as needed -->
</resources>
```

### 3. Update Version Information

In `app/build.gradle`, update version for your release:

```gradle
defaultConfig {
    versionCode 1  // Start from 1 for your fork
    versionName "1.0.0"  // Your version numbering
}
```

## Replacing App Icons

### 1. Prepare Your Icons

You'll need icon images in multiple resolutions. Use Android Studio's Asset Studio or prepare:
- Logo image (512x512 px) for adaptive icon foreground
- Background color or image for adaptive icon background

### 2. Generate Icons Using Android Studio

1. Right-click on `app/src/main/res` in Android Studio
2. Select "New" → "Image Asset"
3. Configure the icon:
   - **Icon Type**: Launcher Icons (Adaptive and Legacy)
   - **Name**: ic_launcher
   - **Foreground Layer**: Upload your logo/icon
   - **Background Layer**: Choose color or image
   - **Resize**: Adjust to fit properly
4. Click "Next" and "Finish"

### 3. Manual Icon Replacement

If replacing manually, update these files:

```
app/src/main/res/
├── drawable/
│   ├── ic_launcher_background.xml  # Background layer
│   └── ic_launcher_foreground.xml  # Foreground layer (your logo)
├── mipmap-anydpi-v26/
│   ├── ic_launcher.xml             # Adaptive icon configuration
│   └── ic_launcher_round.xml       # Round variant configuration
```

### 4. Replace Alpha Logo (Optional)

The app uses `ic_alpha_logo.xml` for the Greek letter alpha. To replace:

Edit `app/src/main/res/drawable/ic_alpha_logo.xml` or create a new vector drawable:

```xml
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <!-- Your institution's logo path data here -->
</vector>
```

## Customizing Branding

### 1. Update Colors

Edit `app/src/main/res/values/colors.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="primary">#YourPrimaryColor</color>
    <color name="primary_variant">#YourPrimaryVariant</color>
    <color name="secondary">#YourSecondaryColor</color>
    <!-- Add your institution's brand colors -->
</resources>
```

### 2. Update Themes

Modify `app/src/main/res/values/themes.xml` to use your colors:

```xml
<style name="Theme.ClassicsViewer" parent="Theme.MaterialComponents.DayNight.DarkActionBar">
    <!-- Customize your theme here -->
    <item name="colorPrimary">@color/primary</item>
    <item name="colorPrimaryVariant">@color/primary_variant</item>
    <item name="colorSecondary">@color/secondary</item>
</style>
```

### 3. Add Institution Branding

Consider adding:
- Institution logo in the main screen
- About page with institution information
- Custom splash screen with institution branding

## Customizing the Database

### 1. Creating a Custom Database

The app supports custom databases with specific authors or texts:

#### a. Create Custom Author List

Modify file `data-prep/SAMPLE_AUTHORS.csv` with your selected authors/works:

#### b. Build Your Database

```bash
cd data-prep
python3 create_perseus_database.py sample
```

### 2. Database Deployment

After creating your custom database:

```bash
# Copy to debug assets
cp data-prep/perseus_texts_custom.db app/src/debug/assets/perseus_texts.db

# Compress for deployment
cd app/src/debug/assets/
zip -9 perseus_texts.db.zip perseus_texts.db
```

## Building and Testing

### 1. Clean Build

```bash
# Clean previous builds
./gradlew clean

# Build debug version
./gradlew assembleDebug

# Install on connected device
./gradlew installDebug
```

### 2. Testing Checklist

- [ ] App launches with new name and icon
- [ ] Database loads correctly
- [ ] All texts display properly
- [ ] Navigation works as expected
- [ ] Settings reflect your customization

### 3. Create Release Build

#### a. Generate Signing Key

```bash
keytool -genkey -v -keystore your-institution-release-key.keystore \
    -alias your-institution-classics -keyalg RSA -keysize 2048 -validity 10000
```

#### b. Configure Signing

Create `keystore.properties` in project root:

```properties
storeFile=your-institution-release-key.keystore
storePassword=YourStorePassword
keyAlias=your-institution-classics
keyPassword=YourKeyPassword
```

#### c. Build Release APK

```bash
./gradlew assembleRelease
```

## Publishing Your Version

### 1. Google Play Store

If publishing publicly:

1. Create a Google Play Developer account
2. Create a new app with your application ID
3. Upload your APK/AAB:
   ```bash
   ./gradlew bundleRelease
   ```
4. Complete store listing with:
   - Institution-specific description
   - Screenshots with your branding
   - Privacy policy
   - Content rating

### 2. Private Distribution

For institutional use only:

#### a. Direct APK Distribution

1. Build signed APK
2. Host on institution's website
3. Provide installation instructions

#### b. Private App Store

Use Google Play's Private Apps for Work and Education:
1. Set up managed Google Play
2. Publish as private app
3. Distribute to institution's users only

#### c. Firebase App Distribution

1. Set up Firebase project
2. Configure App Distribution
3. Invite testers via email

### 3. Update Mechanism

Consider implementing:
- In-app update checks
- Version management
- Database update mechanism

## Important Considerations

### Legal and Attribution

1. **Maintain Attribution**: Keep references to original Perseus Digital Library
2. **License Compliance**: Ensure your fork complies with the original license
3. **Data Rights**: Verify rights to any custom texts added

### Technical Considerations

1. **Database Size**: The full database is ~1.4GB uncompressed
2. **Memory Usage**: Test on devices with limited RAM
3. **Update Strategy**: Plan for database and app updates

### Maintenance

1. **Upstream Changes**: Periodically check original repository for updates
2. **Security Updates**: Keep dependencies updated
3. **User Feedback**: Set up feedback mechanism for your institution

## Troubleshooting

### Common Issues

1. **Package name conflicts**: Ensure complete package rename
2. **Database not found**: Check ZIP file integrity with `unzip -t`
3. **Build failures**: Clean and rebuild project
4. **Icon not showing**: Clear app data and reinstall

### Getting Help

- Check original repository issues
- Android Studio documentation
- Stack Overflow for Android-specific issues

## Example Institution Configurations

### Example 1: University Classics Department

```
Package: edu.university.classics
App Name: University Classics Reader
Database: Custom selection of frequently taught texts
Icon: University seal as foreground, school colors as background
