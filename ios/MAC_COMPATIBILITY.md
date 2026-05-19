# Running Classics Viewer on Apple Silicon Mac

## Current status

Classics Viewer is an iOS-only app. iOS apps install and launch on
Apple Silicon Macs by default, so the app *can* be installed on a Mac
(e.g. via TestFlight or the Mac App Store). However, the app's own
code blocks it on Mac at the age verification screen — see below — so
it cannot actually be used there. **Mac is not a supported platform.**

## Age verification — the actual blocker

`ClassicsViewer/Views/AgeVerificationView.swift` gates **all** access
behind age verification. At launch it checks
`ProcessInfo.processInfo.isiOSAppOnMac`; when `true` (the app is
running on an Apple Silicon Mac) it shows `AgeVerificationBlockedView`
with the message "This app is not available on Mac" and the user
cannot proceed. On iOS/iPadOS it instead runs `AgeVerificationView_iOS`,
which uses the iOS 26 `DeclaredAgeRange` API (`requestAgeRange`).

This block is deliberate and technically justified — the
`DeclaredAgeRange` age check does not function on Mac:

- Apple states the `DeclaredAgeRange` **API is available** on iOS,
  iPadOS, and macOS 26+. It is callable; it does not crash.
- But Apple also states: "In macOS, `isEligibleForAgeFeatures` returns
  false because the system doesn't require Age Assurance for the
  person or device. However, you can still call `requestAgeRange` in
  macOS to get the declared age range."
- In practice developers report `requestAgeRange` on macOS throws
  `AgeRangeService.Error.notAvailable`. A "Designed for iPad" app on
  an Apple Silicon Mac runs on the macOS system and inherits this
  behavior — there is no configuration or entitlement that makes the
  API return a verified age on Mac.
- Apple's mandatory 18+ age-assurance enforcement applies to the
  iOS/iPadOS App Store only. There is no Apple age-verification
  requirement for the Mac App Store, and Apple has published no
  roadmap to add one.

## What this means — no action required

The app is legally required to verify users' age, and the
`DeclaredAgeRange` API cannot do so on Mac. The `isiOSAppOnMac` block
keeps the app compliant by preventing it from running on Mac at all.

- The `isiOSAppOnMac` block in `AgeVerificationView.swift` must stay.
  It must **not** be removed, weakened, or replaced with a
  self-declared or manual age confirmation — none of those satisfy the
  legal requirement.
- **No App Store Connect change is required.** The block makes the app
  compliant regardless of whether it is distributed to Macs.
  Optionally, you can opt the app out of Apple Silicon Mac
  distribution (App Store Connect → Pricing and Availability →
  "Apple Silicon Mac Availability" → deselect "Make this app
  available") so Mac users cannot install a non-functional app. That
  is a UX choice, not a compliance requirement.

If Apple ever brings a working age-assurance mechanism to the Mac
runtime, this can be revisited — until then, the app is iPhone/iPad
only.

## Sources

- Age requirements for apps distributed in Brazil, Australia,
  Singapore, Utah, and Louisiana — Apple Developer News:
  https://developer.apple.com/news/?id=f5zj08ey
- Age assurance developer Q&A — Apple Developer:
  https://developer.apple.com/support/age-assurance/
- isEligibleForAgeFeatures / requestAgeRange on macOS — Apple
  Developer Forums (thread 810857):
  https://developer.apple.com/forums/thread/810857
