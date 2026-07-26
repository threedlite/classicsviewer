# Google Play Age Signals API - Android Implementation Guide

This document describes how age verification is implemented in ClassicsViewer using Google's Play
Age Signals API.

Reference implementation: `app/src/main/java/com/classicsviewer/app/AgeVerificationActivity.kt`.
That file is the source of truth; this document describes it.

## Overview

The Play Age Signals API lets an app ask the Google Play Store for the age range associated with
the user's Play account. The app never sees a date of birth or account identity — only a range
such as "18 and over", plus an indicator of how that range was established.

**The gate is fail-closed.** Access is granted only when Play affirmatively reports an age range
whose lower bound is at least the minimum age. Every other outcome — signals not shared,
verification required, no range returned, or any API error — denies access. The app cannot
establish an age that Play does not report, so "unknown" is treated as "not eligible".

## 1. Dependency

`app/build.gradle`:

```gradle
dependencies {
    implementation 'com.google.android.play:age-signals:0.0.4'
}

android {
    defaultConfig {
        minSdk 23   // required floor: the age-signals AAR declares minSdkVersion 23
    }
}
```

The artifact is `com.google.android.play:age-signals` — note there is no `play-` prefix.

## 2. API surface in 0.0.4

Verified against `age-signals-0.0.4.aar`. **`AgeSignalsResult.userStatus()` does not exist in
0.0.4** — it was present in 0.0.3 and was removed. Code written against 0.0.3 will not compile.

```
AgeSignalsManager
  Task<AgeSignalsAccessResult> requestAgeSignalsAccess(AgeSignalsAccessRequest)
  Task<AgeSignalsResult>       checkAgeSignals(AgeSignalsRequest)

AgeSignalsAccessResult
  Integer ageSignalsStatus()

AgeSignalsResult
  Integer ageLower()  Integer ageUpper()  Integer ageRangeSource()
  String  installId()
  Integer significantChangeStatus()   Date significantChangeApprovalDate()

model.AgeSignalsStatus   UNSPECIFIED=0  SHARED=1  NOT_SHARED=2  VERIFICATION_REQUIRED=3
model.AgeRangeSource     UNSPECIFIED=0  TIER_A=1  TIER_B=2  TIER_C=3  TIER_D=4
model.SignificantChangeStatus  UNSPECIFIED=0  APPROVED=1  PENDING=2  DECLINED=3

model.AgeSignalsErrorCode
   NO_ERROR=0                      API_NOT_AVAILABLE=-1
   PLAY_STORE_NOT_FOUND=-2         NETWORK_ERROR=-3
   PLAY_SERVICES_NOT_FOUND=-4      CANNOT_BIND_TO_SERVICE=-5
   PLAY_STORE_VERSION_OUTDATED=-6  PLAY_SERVICES_VERSION_OUTDATED=-7
   CLIENT_TRANSIENT_ERROR=-8       APP_NOT_OWNED=-9
   SDK_VERSION_OUTDATED=-10        INTERNAL_ERROR=-100
```

The AAR also contributes a transparent `AgeSharingConsentWrapperActivity` to the merged manifest.
It is the UI Play uses for the in-app age-sharing prompt; the app does not declare or launch it
directly.

## 3. Two-step flow

0.0.4 replaced the single `checkAgeSignals()` call with a two-step flow.

**Step 1 — `requestAgeSignalsAccess(AgeSignalsAccessRequest)`.** Takes an `Activity`, because it
may surface Play's in-app age-sharing prompt. Returns an `ageSignalsStatus`:

| Status | Handling in this app |
|---|---|
| `SHARED` | proceed to step 2 |
| `NOT_SHARED` | deny; tell the user age sharing can be changed in Play Store settings |
| `VERIFICATION_REQUIRED` | deny; tell the user to complete verification in the Play Store |
| `UNSPECIFIED` or an unrecognised value | deny |

**Step 2 — `checkAgeSignals(AgeSignalsRequest)`.** Only called when status is `SHARED`. Returns
the age range.

Retrying is scoped to the step that failed, so a failure in step 2 does not re-trigger Play's
consent prompt. Repeated prompting is undesirable.

## 4. Eligibility decision

The single grant condition:

```kotlin
if (ageLower != null && ageLower >= MINIMUM_AGE) { proceedToApp() }
```

`ageLower == null` carries no age information and is **not** eligible. An open-ended range is
expressed as `ageLower = 18, ageUpper = null`.

`ageRangeSource` is currently logged but not enforced. If a stronger standard of proof is wanted,
the tier can be added to the condition — but note that requiring a high tier will also exclude
adults who have never completed a strong verification with Play.

## 5. Error handling

No error path grants access in a release build.

| Code | Handling |
|---|---|
| `APP_NOT_OWNED` (-9) | deny, no retry — app was not installed by Play |
| `SDK_VERSION_OUTDATED` (-10) | deny, no retry — prompt to update the app |
| `NETWORK_ERROR` (-3) | deny; bounded auto-retry, then a Retry button |
| `PLAY_STORE_NOT_FOUND` (-2), `PLAY_SERVICES_NOT_FOUND` (-4) | deny; prompt to install or enable |
| `API_NOT_AVAILABLE` (-1), `PLAY_STORE_VERSION_OUTDATED` (-6) | deny; prompt to update the Play Store |
| `PLAY_SERVICES_VERSION_OUTDATED` (-7) | deny; prompt to update Play services |
| `CANNOT_BIND_TO_SERVICE` (-5), `CLIENT_TRANSIENT_ERROR` (-8), `INTERNAL_ERROR` (-100) | deny; bounded auto-retry, then a Retry button |
| unknown code, or a non-`AgeSignalsException` | deny; bounded auto-retry, then a Retry button |
| manager construction throws | deny, Retry offered |

`API_NOT_AVAILABLE` means the Play Store on the device is too old. It does **not** indicate an
unsupported region.

### Debug bypass

```kotlin
if (BuildConfig.DEBUG &&
    (errorCode == AgeSignalsErrorCode.APP_NOT_OWNED ||
     errorCode == AgeSignalsErrorCode.CANNOT_BIND_TO_SERVICE)) {
    proceedToApp()
    return
}
```

Sideloaded debug builds are not owned by Play and can never obtain signals, so the gate is
untestable locally without this. `BuildConfig.DEBUG` is a compile-time `false` in release, and
with `minifyEnabled true` R8 removes the branch entirely. **The fail-closed behaviour is therefore
only observable in a release build installed through Play** (for example via an internal testing
track). A debug build will always open.

## 6. Manifest

`AgeVerificationActivity` is the launcher activity, so the gate runs before anything else:

```xml
<activity android:name=".AgeVerificationActivity" android:exported="true">
    <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
    </intent-filter>
</activity>

<activity android:name=".MainActivity" android:exported="false" />
```

`MainActivity` and every other activity are non-exported, so no other app can start them directly.

## 7. Testing

`FakeAgeSignalsManager` (`com.google.android.play.agesignals.testing`) implements
`AgeSignalsManager` and can be driven with either a result or an exception for each of the two
calls:

```
setNextAgeSignalsAccessResult(AgeSignalsAccessResult)
setNextRequestAgeSignalsAccessException(AgeSignalsException)
setNextAgeSignalsResult(AgeSignalsResult)
setNextAgeSignalsException(AgeSignalsException)
```

`AgeSignalsResult.builder()` and `AgeSignalsAccessResult.builder()` are public, so arbitrary
inputs can be constructed.

Note: `AgeVerificationActivity` currently calls `AgeSignalsManagerFactory.create()` directly, so
there is no seam to inject the fake. Exhaustive branch testing would require introducing one.

## 8. Notes and limitations

- **No permissions required.** The API works over an IPC binding to the Play Store; the app
  declares no internet permission. The Play Store performs the network work.
- **Play installs only.** Sideloaded builds return `APP_NOT_OWNED` and are denied in release.
- **Repackaging defeats the gate.** Anyone who rebuilds the APK can remove the check. Play
  Integrity is the countermeasure and is not currently integrated.
- **`TIER_A` age ranges are self-declared** on the Google account, so the gate does not stop a
  minor who entered a false birthday. Enforcing a higher tier is possible but excludes many adults.
- **`significantChangeStatus()` / `significantChangeApprovalDate()` are not handled.** They relate
  to parent-approved changes for supervised accounts.
- **Regional and jurisdictional behaviour has not been verified by this project.** The statements
  in this document about the API surface and about this app's own logic were checked against the
  AAR and the source. Claims about what Play returns in a given country, and about what any law
  or Play policy requires, should be checked against Google's primary documentation.
