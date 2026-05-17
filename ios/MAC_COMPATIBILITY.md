# Running Classics Viewer on Apple Silicon Mac

## Current status

Classics Viewer is an iOS-only build. It will NOT install on an Apple
Silicon Mac as a "Designed for iPad" app. This document records why, and
what's needed to change that.

## Remaining blockers

### 1. `LSRequiresIPhoneOS = true` (Info.plist)

This key tells the system "iPhone OS only — not iPadOS, not macOS." When
true, Apple Silicon Macs refuse to install the app. Apple's App Store
also uses this flag to decide whether to list the app under the
iPhone/iPad tab on the Mac App Store.

**Change to enable Mac:** set the value to `false`, or remove the key
entirely. Apps that omit `LSRequiresIPhoneOS` default to running on
iPhone, iPad, AND Apple Silicon Mac.

### 2. Mac destination not opted into the build

The Xcode target (in `project.yml`) declares:

```
platform: iOS
deploymentTarget: { iOS: 18.0 }
TARGETED_DEVICE_FAMILY: 1,2     # iPhone + iPad only — no Mac
```

There is no `SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD` setting and no Mac
Catalyst setting. The resulting `.ipa` simply does not contain a Mac
slice, so even if `LSRequiresIPhoneOS` were false, no installable build
exists for the Mac runtime.

**Two ways forward, pick one:**

  - **Designed for iPad on Mac** (cheap, iPad UI in a Mac window):
    Add to `project.yml` under `targets.ClassicsViewer.settings.base`:
    ```
    SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD: YES
    ```
    Then `./generate_xcodeproj.sh` to regenerate the .xcodeproj.

  - **Mac Catalyst** (more work, native-feeling Mac app):
    Add `SUPPORTS_MACCATALYST: YES` instead. You may also need to add a
    Catalyst-specific build configuration and audit Swift code for
    iOS-only APIs that have no Catalyst equivalent (e.g. certain UIKit
    appearance proxies, some scene-delegate paths, audio session
    behaviors). This is a deeper refactor.

The two are not exclusive — you can ship both — but they are different
runtimes and each requires its own QA pass.

## Decision points (review before flipping the switches above)

### Deployment target — iOS 18 implies macOS 15+ on the Mac side

`deploymentTarget: iOS: 18.0` means the Apple Silicon Mac running the
app must be on macOS 15 (Sequoia) or newer. Older Apple Silicon Macs
running macOS 14 or earlier will never see the app as compatible. If
you want wider Mac reach, lower the iOS deployment target alongside
the Mac-enablement edits.

### On-Demand Resources still work — but check the install flow

The `audio_full`, `database_full`, and `database_extended` ODR tags
declared in `project.yml` work on Mac the same way they do on iOS: the
initial install is small, and tagged resources download on first use.
This is fine in principle, but the user-facing "Audio Download" /
"Extended database" affordances are designed for iPhone/iPad form
factors. If you ship to Mac, walk through the download flow on Mac to
make sure the UI is sensible at desktop window sizes.

### File Sharing / Documents

Info.plist sets `UIFileSharingEnabled = true` and
`LSSupportsOpeningDocumentsInPlace = true`. These expose the app's
Documents folder in the Files app on iOS. On Mac, the equivalent is the
`~/Library/Containers/<bundle-id>/Data/Documents/` path, accessible via
the Finder's "Go to Folder" menu (or by enabling sidebar in Finder for
the app). Worth a manual test that file imports/exports work — the
Catalyst pickers behave differently from iOS in some edge cases.

### Custom UTI declaration

The Info.plist declares a custom UTI for `.db` files
(`com.classicsviewer.database` conforming to `public.database`). This
should carry over to Mac without changes, but if you enable
"Designed for iPad on Mac" you'll want to confirm that
double-clicking a `.db` file in Finder routes to Classics Viewer
correctly (it should, but Apple Silicon Mac UTI registration is
sometimes flaky on first install).

### Distribution channel

On Apple Silicon Macs, iOS apps install **only via the Mac App Store**.
Sideloading an `.ipa` directly is not supported. For development /
TestFlight on Mac you'll need to upload a build to App Store Connect
and TestFlight, then install via the Mac TestFlight app. Internal Ad
Hoc / Enterprise distribution does NOT work for the Mac-as-iOS
runtime.

This also means the App Store Connect "Pricing and Availability →
Make this app available on Apple Silicon Macs" checkbox must be ON
when you submit the build. The checkbox defaults to ON for new apps,
but if it was ever turned OFF on a prior submission, it stays OFF
until you flip it back.

### Intel Macs are out regardless

iOS apps cannot run on Intel Macs at all — there is no x86 iOS slice
and the iOS-on-macOS runtime is arm64-only. Any documentation /
marketing about Mac support should explicitly say "Apple Silicon Mac."

## Minimum edits to actually enable Mac (if you decide to)

1. `ios/ClassicsViewer/Info.plist` — change `<true/>` to `<false/>` for
   `LSRequiresIPhoneOS`, OR delete the key + value entirely.
2. `ios/project.yml` — under
   `targets.ClassicsViewer.settings.base`, add:
   ```
   SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD: YES
   ```
3. `ios/generate_xcodeproj.sh` — re-run to regenerate the `.xcodeproj`
   from the updated yaml.
4. Build, archive, upload to TestFlight, install on a macOS-15+ Apple
   Silicon Mac via the Mac TestFlight app, and verify the app launches
   and the database extracts.

Until these three edits are made, the iOS app will continue to install
only on iPhone/iPad.
