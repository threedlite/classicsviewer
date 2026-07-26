# Privacy Policy for Classics Viewer

**Last updated: July 2026**

## Introduction

Classics Viewer ("we", "our", or "the app") is committed to protecting your privacy. This Privacy Policy explains our practices regarding the collection, use, and disclosure of information when you use our Android application.

## Information Collection and Use

**Classics Viewer does not collect, store, or transmit any personal information.**

### No Data Collection

The app itself:
- Does not collect any personal data
- Does not track user behavior or analytics
- Does not use cookies or similar tracking technologies
- Does not require user accounts or registration
- Does not operate any server, and sends no data to us
- Makes no network connections of its own — it holds no internet permission
- Works offline: once content is installed, the app can be used indefinitely with no connection,
  including in airplane mode

We receive nothing from your use of the app. We have no servers and no way to identify you.

### Local Storage Only

All app data is stored locally on your device:
- Classical texts are stored in a local database
- User preferences (selected language, font size, etc.) are saved locally
- Reading progress and bookmarks are stored on your device only
- All data remains under your control and is never transmitted to us

## Age Verification

Access to Classics Viewer is restricted to users 18 years of age and older.

To enforce this, the app uses the **Google Play Age Signals API**. When you open the app, it asks the Google Play Store whether your account's age range meets the minimum age.

What the app receives from Google Play:
- Whether age information is available for your account
- An age range (for example "18 and over"), not an exact age
- An indicator of how that age range was established

What the app does **not** receive: your date of birth, your name, your account identity, or any other account details.

How the age result is used:
- Solely to decide whether to allow access to the app
- It is never written to your device's storage, and no record that you passed the check is kept — the app asks Google Play again each time it starts
- It is discarded as soon as the allow/deny decision is made
- It is never transmitted anywhere; the app has no internet permission and no server
- It is never used for advertising, marketing, profiling, or analytics
- It is never shared with any third party

If Google Play does not confirm that you are 18 or over, the app denies access. This includes cases where age information is unavailable, has not been shared, or where verification has not been completed.

The age check is performed by the Google Play Store app on your device. Google's handling of your account information is governed by Google's own privacy policy, not this one.

## Network Access

**Classics Viewer does not request the Android internet permission and makes no network connections of its own.**

Two operations are performed on the app's behalf by the Google Play Store app installed on your device:

- **Age verification** at launch, as described above. This is a request to the Play Store app on your device; the Play Store may answer it from information it already holds locally.
- **Content downloads** — the text database and the optional audio, reference, and topical content packs are delivered through Google Play Asset Delivery. These are one-time downloads that you initiate.

Reading texts, searching, word analysis, and bookmarks never involve a connection. Once your content is installed, the app is designed to be used offline indefinitely.

## Permissions

The app's own manifest declares one permission:

- **Storage Access** (`READ_EXTERNAL_STORAGE`): to read the packaged database file containing classical texts, and for the import/export bookmarks to CSV function

The following additional permissions are contributed automatically by the bundled Google Play and AndroidX libraries and appear in the installed app:

- `ACCESS_NETWORK_STATE` — used by Play Asset Delivery to check connectivity
- `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_DATA_SYNC` — used by Play Asset Delivery for content downloads
- `WAKE_LOCK`, `RECEIVE_BOOT_COMPLETED` — used by the download and background-task libraries

The app does not request and does not use:
- The internet permission
- Camera, microphone, or location access
- Access to contacts, calendar, call logs, or SMS
- Device identifiers for tracking or advertising

## Children's Privacy

Classics Viewer is not intended for and is not available to anyone under 18 years of age. Access is blocked unless Google Play confirms that the user meets the minimum age, as described under **Age Verification** above.

We do not knowingly collect information from anyone, of any age.

## Third-Party Services

Classics Viewer uses no analytics tools, no advertising networks, and no crash-reporting services.

It does rely on the following Google Play services, which are part of the Android platform on devices that have the Play Store:

- **Google Play Age Signals API** — for the age check described above
- **Google Play Asset Delivery** — for delivering the text database and optional content packs

Use of these is governed by Google's Privacy Policy and Google Play Terms of Service.

## Data Security

We do not collect or receive any of your data, so there is no data held by us that could be compromised. All app content and settings remain locally on your device.

## Changes to This Privacy Policy

We may update our Privacy Policy from time to time. Any changes will be reflected in the updated Privacy Policy with a new "Last updated" date.

## Contact Us

If you have any questions about this Privacy Policy, please contact us at:
threedliteguy@gmail.com

## Open Source

Classics Viewer is an open-source project. You can review our source code at:
https://github.com/threedlite/classicsviewer
