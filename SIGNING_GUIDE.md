# Play Store Signing Guide for Classics Viewer

## Overview
This guide explains how to create and manage signing keys for releasing the Classics Viewer app on Google Play Store.

## Prerequisites
- Java Development Kit (JDK) installed
- `keytool` command available (comes with JDK)

## Step 1: Generate the Release Keystore

Run the provided script to create your release keystore:

```bash
./create_release_keystore.sh
```

You will be prompted for:
1. **Keystore password** (minimum 6 characters) - This protects the keystore file
2. **Key password** (can be same as keystore password) - This protects the specific key
3. **Your details**:
   - First and Last Name
   - Organizational Unit
   - Organization
   - City/Locality
   - State/Province
   - Country Code (2 letters, e.g., US)

### Example Input:
```
Enter keystore password: [your-secure-password]
Re-enter new password: [your-secure-password]
Enter key password for <classics-viewer-key>: [your-key-password]
Re-enter new password: [your-key-password]
What is your first and last name? [Your Name]
What is the name of your organizational unit? [Development]
What is the name of your organization? [Your Company/Name]
What is the name of your City or Locality? [Your City]
What is the name of your State or Province? [Your State]
What is the two-letter country code for this unit? [US]
```

## Step 2: Create keystore.properties File

After successfully creating the keystore, create a file named `keystore.properties` in the project root:

```properties
storePassword=YOUR_KEYSTORE_PASSWORD
keyPassword=YOUR_KEY_PASSWORD
keyAlias=classics-viewer-key
storeFile=keystore/release-keystore.jks
```

Replace `YOUR_KEYSTORE_PASSWORD` and `YOUR_KEY_PASSWORD` with the actual passwords you used.

## Step 3: Build Signed Release AAB

To build a signed Android App Bundle (AAB) for Play Store:

```bash
./gradlew bundleRelease
```

The signed AAB will be created at:
`app/build/outputs/bundle/release/app-release.aab`

## Step 4: Build Signed Release APK (Optional)

If you need a signed APK for testing:

```bash
./gradlew assembleRelease
```

The signed APK will be created at:
`app/build/outputs/apk/release/app-release.apk`

## Security Best Practices

### 1. **NEVER Commit Sensitive Files**
The following files are already in `.gitignore` and should NEVER be committed:
- `keystore.properties` (contains passwords)
- `*.jks` (keystore files)
- `*.keystore` (keystore files)

### 2. **Backup Your Keystore**
- **CRITICAL**: Back up your keystore file and passwords in multiple secure locations
- **You cannot update your app on Play Store without the original keystore**
- Suggested backup locations:
  - Encrypted cloud storage (e.g., password manager)
  - Secure USB drive in a safe location
  - Company/team secure storage system

### 3. **Password Security**
- Use strong, unique passwords
- Store passwords in a password manager
- Never share passwords via email or chat
- Consider using different passwords for keystore and key

### 4. **Team Development**
If working in a team:
- Store keystore in secure shared location (not Git)
- Use secure password sharing tools
- Document who has access
- Consider using Play App Signing (see below)

## Google Play App Signing (Recommended)

Google offers Play App Signing which provides additional security:

1. You upload your app signing key to Google Play Console once
2. Google manages and protects your app signing key
3. You use an upload key for subsequent updates
4. If you lose your upload key, Google can reset it

To enable Play App Signing:
1. Go to Google Play Console
2. Select your app
3. Go to Setup → App integrity
4. Follow the Play App Signing enrollment process

## Verify Your Signed APK/AAB

To verify your APK/AAB is properly signed:

```bash
# For APK
jarsigner -verify -verbose -certs app/build/outputs/apk/release/app-release.apk

# For AAB
jarsigner -verify -verbose -certs app/build/outputs/bundle/release/app-release.aab
```

You should see "jar verified" if successful.

## Troubleshooting

### "Keystore file not found"
- Ensure you've run `./create_release_keystore.sh`
- Check that `app/keystore/release-keystore.jks` exists
- Verify the path in `keystore.properties` is correct

### "Cannot recover key"
- You're using the wrong key password
- Check your `keystore.properties` file

### "Keystore was tampered with, or password was incorrect"
- You're using the wrong keystore password
- Check your `keystore.properties` file

## Summary Checklist

- [ ] Run `./create_release_keystore.sh` to create keystore
- [ ] Create `keystore.properties` with your passwords
- [ ] Verify `keystore.properties` is in `.gitignore`
- [ ] Back up keystore file and passwords securely
- [ ] Build signed release with `./gradlew bundleRelease`
- [ ] Upload AAB to Google Play Console
- [ ] Consider enabling Play App Signing for added security

## Important Reminders

⚠️ **NEVER LOSE YOUR KEYSTORE**: You cannot update your app without it!

⚠️ **NEVER COMMIT PASSWORDS**: Double-check before every commit!

⚠️ **ALWAYS BACKUP**: Keep multiple secure backups of your keystore and passwords!