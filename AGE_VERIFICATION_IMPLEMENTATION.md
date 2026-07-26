# Google Play Age Signals API - Android Implementation Guide

This document describes how age verification is implemented in ClassicsViewer using Google's Play
Age Signals API.

Reference implementation: `app/src/main/java/com/classicsviewer/app/AgeVerificationActivity.kt`.
That file is the source of truth; this document describes it.

## Overview

The Play Age Signals API lets an app ask the Google Play Store for the age range associated with
the user's Play account. The app never sees a date of birth or account identity — only a range
such as "18 and over", plus an indicator of how that range was established.

**The objective is to restrict users under the minimum age.** That is deliberately not the same
as denying every user Play cannot describe, and the implementation distinguishes the two.

Play's answer is authoritative wherever Play gives one. A reported range below the minimum age is
a hard denial with no fallback and no override. `VERIFICATION_REQUIRED` is likewise a denial,
because that status means Play has identified the user as being in a jurisdiction where
verification is mandatory — self-declaration must not become an escape hatch in exactly the place
the law applies.

Where Play gives *no* answer — `NOT_SHARED`, no age range, an unrecognised status, or an
unrecoverable error — the app falls back to asking the user to declare a date of birth. Play's
silence is an absence of information, not evidence that a user is under age.

**This distinction is load-bearing, not an edge case.** Play returns age signals only in a short
and slowly growing list of jurisdictions — Brazil and a handful of US states (see §9). Treating
silence as denial locks out every account everywhere else while identifying no additional minor,
which is what versions 0.8.131–0.8.133 did.

A store-level control, **Restrict Minor Access**, covers the same objective worldwide and is
independent of both this code and the app's content rating. See §10.

Ordering preserves the guarantee: Play is always asked first, so a declaration can only fill a
gap Play left, never contradict an answer Play gave.

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
| `NOT_SHARED` | **age declaration fallback** (§4a) |
| `VERIFICATION_REQUIRED` | deny, with an **Open Google Play** button (§3a) |
| `UNSPECIFIED` or an unrecognised value | **age declaration fallback** (§4a) |

`NOT_SHARED` is ambiguous by construction. Google documents it as covering "user didn't share age
range, parent rejected the request, **or not eligible**" — and "not eligible" is every account
outside the two rollout regions. The API exposes no way to tell a refusal from an ineligibility,
so the status carries no evidence about age and cannot support a denial on its own.

### 3a. VERIFICATION_REQUIRED is a denial the user can clear

This status is not a permanent lockout, and an adult in a covered state does have a way through —
but it runs through the Play Store, not through this app:

1. Play returns `VERIFICATION_REQUIRED`, because the user is in a jurisdiction where verification
   is mandatory and they have not completed it.
2. The user verifies **in the Play Store** — by ID, payment card, selfie, or a third-party
   service, depending on region.
3. They return and tap **Retry**. `requestAgeSignalsAccess` now returns `SHARED`, step 2 runs, and
   an adult is admitted normally.

Step 2 is the weak link: Google publishes **no deep link** to the verification flow, and users do
not find the setting on their own. `openPlayStore()` therefore opens this app's store listing —
where Play surfaces the age check for an age-restricted title — and falls back to the Play Store's
launcher entry, then to an explanatory message if Play is absent entirely. Without that button the
screen only instructs the user to go and verify "in the Google Play Store", which in practice is
not discoverable.

The declaration fallback is deliberately **not** offered here. This is the one status where Play
has positively told us the user is somewhere verification is legally required, so a self-declared
date of birth must not substitute for it.

**Step 2 — `checkAgeSignals(AgeSignalsRequest)`.** Only called when status is `SHARED`. Returns
the age range.

Retrying is scoped to the step that failed, so a failure in step 2 does not re-trigger Play's
consent prompt. Repeated prompting is undesirable.

## 4. Eligibility decision

The single grant condition:

```kotlin
if (ageLower != null && ageLower >= MINIMUM_AGE) { proceedToApp() }
```

`ageLower == null` carries no age information, so it routes to the declaration fallback rather
than to a denial. An open-ended range is expressed as `ageLower = 18, ageUpper = null`.

A reported `ageLower` *below* the minimum is a terminal denial: `allowRetry = false`,
`exitApp = true`, and no declaration is offered. This is the one place the app has positive
evidence about age, and nothing the user can enter overrides it.

## 4a. Age declaration fallback

Reached only when Play produced no usable answer. Implemented by `requireAgeDeclaration()`.

The user is shown a `DatePicker` and enters a date of birth. `completedYearsSince()` converts it
to an age; the age is compared against `MINIMUM_AGE`; the date is then discarded. Design points:

- **The picker defaults to today's date**, not to a plausible adult birth date. Nothing is
  pre-filled toward passing, so a user who taps Continue without changing anything computes to
  age 0 and is denied. `maxDate` is set to now, so future dates cannot be entered.
- **A neutral date entry is used rather than an "I am 18 or older" button**, which would state the
  answer that passes.
- **Only the boolean outcome is persisted**, as `age_declaration_confirmed` in
  `PreferencesManager`. The date of birth is never written to preferences, never logged, and never
  leaves the method.
- **The stored flag is read only on the fallback path.** Play is still queried fresh on every
  launch, and its answer is evaluated first. A stored `true` therefore cannot admit a user Play
  has since reported as under age.

The flag is **not** a cache of a Play age signal and must not be allowed to become one. The
prohibition in `CLAUDE.md` on persisting age signals is intact: no age range, no age value, and no
"Play said yes" flag is stored.

### Offline behaviour

This also resolves the open question in `CLAUDE.md` about airplane mode. A device with no network
produces `NETWORK_ERROR`, which retries a bounded number of times and then falls back to the
declaration path — so a release build no longer denies access offline, and the app's offline
design goal holds without weakening the gate. Play is still asked first on every launch, and still
wins whenever it can answer.

`ageRangeSource` is currently logged but not enforced. If a stronger standard of proof is wanted,
the tier can be added to the condition — but note that requiring a high tier will also exclude
adults who have never completed a strong verification with Play.

## 5. Error handling

No error path grants access directly. Two are terminal denials; the rest are transient conditions
that say nothing about the user's age, so after bounded retries they route to the declaration
fallback rather than locking the user out.

| Code | Handling |
|---|---|
| `APP_NOT_OWNED` (-9) | **deny, terminal, no fallback** — app was not installed by Play |
| `SDK_VERSION_OUTDATED` (-10) | **deny, terminal, no fallback** — prompt to update the app |
| `NETWORK_ERROR` (-3) | bounded auto-retry → declaration fallback |
| `PLAY_STORE_NOT_FOUND` (-2), `PLAY_SERVICES_NOT_FOUND` (-4) | bounded auto-retry → declaration fallback |
| `API_NOT_AVAILABLE` (-1), `PLAY_STORE_VERSION_OUTDATED` (-6) | bounded auto-retry → declaration fallback |
| `PLAY_SERVICES_VERSION_OUTDATED` (-7) | bounded auto-retry → declaration fallback |
| `CANNOT_BIND_TO_SERVICE` (-5), `CLIENT_TRANSIENT_ERROR` (-8), `INTERNAL_ERROR` (-100) | bounded auto-retry → declaration fallback |
| unknown code, or a non-`AgeSignalsException` | bounded auto-retry → declaration fallback |
| manager construction throws | declaration fallback |

`APP_NOT_OWNED` stays terminal on purpose: it is the check that stops a sideloaded release build
from reaching the declaration path, so the fallback cannot be used to bypass Play distribution.
The retry messages still name the remediation (update Play Store, enable Play services) before the
fallback appears, so a user who can fix the underlying problem is told how.

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
- **The declaration fallback is self-attested and can be lied about.** This is inherent to any age
  gate operating without a verified signal, and is the same weakness `TIER_A` already carries on
  the Play path. It is a floor, not a ceiling: it restricts minors who answer honestly, and it
  never weakens the verified path, since Play is asked first and overrides it.
- **`significantChangeStatus()` / `significantChangeApprovalDate()` are not handled.** They relate
  to parent-approved changes for supervised accounts.
- **Regional and jurisdictional behaviour has not been verified by this project.** The statements
  in this document about the API surface and about this app's own logic were checked against the
  AAR and the source. Claims about what Play returns in a given country, and about what any law
  or Play policy requires, should be checked against Google's primary documentation.

## 9. Regional availability — why the fallback exists

Checked on 2026-07-26. **Treat this table as indicative, not authoritative** — coverage is
expanding as US state laws take effect, and Google's own availability page lags the rollout.

| Region | Law | Status |
|---|---|---|
| Brazil | Digital ECA | signals returned since 2026-03-17 |
| Texas, USA | SB2420 | signals returned for accounts **created after 2026-05-28** |
| Utah, USA | App Store Accountability Act | in effect since 2026-05-07 |
| Louisiana, USA | HB570 | in effect since 2026-07-01 |
| Alabama, California, USA | — | scheduled January 2027 |
| Everywhere else | — | no signals — `requestAgeSignalsAccess` returns `NOT_SHARED` |

Caveats on the rows above, because the sources disagree:

- Google's own availability page (last updated 2026-07-21) still names **only Brazil and Texas**,
  and says "ongoing updates will be provided in advance of age verification bills in other US
  states." It does not list Utah or Louisiana.
- The Utah and Louisiana **statutory** dates are not in dispute; whether Play returns signals in
  those states is what Google's page has not confirmed.
- Texas SB2420 survived its court challenge and **is enforceable**. A preliminary injunction was
  granted 2025-12-23 in *CCIA v. Paxton*, stayed by the Fifth Circuit on 2026-06-01; the Act took
  effect 2026-06-04, and the Supreme Court declined to block it on 2026-07-07. Anything citing the
  December injunction as current is out of date.

**None of this affects the code.** `AgeVerificationActivity` hardcodes no region list and never
asks where the user is — it reacts only to the status Play returns. A user in a newly covered
state simply starts getting `SHARED` or `VERIFICATION_REQUIRED` instead of `NOT_SHARED`, and is
routed correctly with no code change. This table exists to explain *why* the fallback is needed,
not to drive any behaviour, and it does not need to be kept current for the app to stay correct.

The load-bearing fact is only this: the overwhelming majority of the world is not covered by any
of these laws, gets `NOT_SHARED`, and was locked out by versions 0.8.131–0.8.133.

Google states plainly that **use of the API is not mandatory**: *"Google Play doesn't mandate the
use of these features."* Its sanctioned purpose is narrow: *"You may only use information from the
Play Age Signals API to provide age-appropriate content and experiences in compliance with laws."*
Nothing in Google's policy requires denying access to users who return `NOT_SHARED`, and outside
the covered regions there is no signal to act on in the first place.

This matters for reading the git history. Commit `90dde68` ("add Googles new required api check
for Jan 1, 2026 eff date") introduced the gate on the understanding that the check was required of
all developers by that date. It is not. The 18+ restriction is a product decision; the API is a
tool for honouring it where Play can help — not a mandate, and not a mechanism that works
worldwide.

**Not an open item — do not re-raise.** The Play listing carries a `content_rating` of **Teen**
(see `PLAY_POLICY_AUDIT.md`) while `PLAY_STORE_LISTING.md` and this gate both assert an 18+
restriction. This cannot be changed in the Play Console and is settled: the discrepancy is known,
accepted, and not a defect to be fixed. It has no bearing on the gate's behaviour.

### SDK version

`0.0.4` is current. The docs path `/google/play/age-signals/v3/` is **not** a newer version — it
documents `0.0.3`, which Google marks as no longer supported. The Maven group index
(`dl.google.com/dl/android/maven2/com/google/android/play/group-index.xml`) lists
`0.0.1-beta01, 0.0.1-beta02, 0.0.1, 0.0.2, 0.0.3, 0.0.4`. No upgrade widens regional coverage.

## 10. Restrict Minor Access (Play Console, store-level)

**Status: ENABLED for this app since 2025-08-07.** Verified in the Play Console on 2026-07-26.
Target age group is "18 and over" (sole selection) with Restrict Minor Access checked. Nothing
needs doing here — this section is recorded so the app's real 18+ posture is not misread from the
Kotlin alone.

This is the app's **primary** 18+ control, and it predates the in-app gate by two months. It is a
second, independent lever outside the app, and it achieves the 18+ objective in a place the Age
Signals API cannot reach.

**Location.** "Target audience and content" is **not** a left-menu item — it is a section on the
**App content** page, with a Start/Manage button. That is the thing to look for.

Google's help article gives the path as:

> "Open Play Console and go to the **App content** page (**Policy** > **App content**)."
> "Under 'Target audience and content,' click **Start**."

Other sources describe the current left-hand nav as **Monitor and improve → Policy and programs →
App content**, so the top-level label appears to have been renamed without the article being
updated. The destination is the same **App content** page either way.

**The checkbox is conditionally rendered — this is why it looks absent.** It is not a control on
the App content page itself:

1. On **App content**, find the **Target audience and content** row → **Start** / **Manage**. This
   opens a multi-step questionnaire.
2. On the **Target age** step, tick **18 and over** and untick every other age group. It must be
   the only one selected.
3. The Restrict Minor Access checkbox appears **on that same screen** once, and only once, that is
   true. With any other age group still ticked it does not render.

Prerequisite: the article states the Target audience section is not reachable until the ads
declaration, app access instructions, and privacy policy are all complete.

> "To enable the Restrict Minor Access feature, select 18 and over as your app's only target age
> group. Then on the same screen, verify and check the box to restrict users that Google has
> determined to be minors from your app."

**It is independent of the IARC content rating.** The rating questionnaire and the target-audience
declaration are separate controls, so the Teen rating recorded in §9 does not prevent enabling it.

**Effect:** *"users determined to be under 18 will not be able to search for, download or purchase
the app."* Age is taken from *"the age provided in their Google Account or when our systems
indicate that a user may be under 18."*

**This is not tied to the Age Signals rollout.** It keys off Google Account age rather than the
per-jurisdiction signal programme, so unlike everything in §9 it applies worldwide.

### Limits

- **Not retroactive.** *"Users who have already installed the app will continue to be able to use
  it, but will not be able to renew existing subscriptions or make new purchases."*
- **Self-declared age.** Google Account age is user-entered on many accounts — the same class of
  assurance as `TIER_A`, not verified ID.
- **Narrows the audience declaration** to 18+ only, which affects discoverability.
- **Mandatory only for real-money gambling and dating/matchmaking apps** (Age-Restricted Content
  and Functionality policy). For everything else it is opt-in: *"If your app is only suitable or
  designed for an adult audience, you can enable the Restrict Minor Access feature."*
- One third-party source states Google reviews target-audience declarations for accuracy; the
  Console help page does not describe a review process. Unconfirmed.

### Relationship to the in-app gate

Different layers, no conflict:

| Layer | Mechanism | Covers |
|---|---|---|
| Acquisition | Restrict Minor Access | search, download, purchase — worldwide |
| Runtime | `AgeVerificationActivity` | existing installs, verified signals in covered jurisdictions |

Enabling the Console setting does not make the gate redundant (it is not retroactive, and it does
not run at launch), and the gate does not depend on the Console setting being enabled.

Because Restrict Minor Access has been active since 2025-08-07, the runtime gate is
**defence-in-depth, not the primary control**. Its residual job is the gap Google itself
acknowledges in the Console copy — *"Google Play may not be able to block all minor users who have
not declared themselves to be under the age of 18"* — plus installs predating the restriction, and
minors Play positively identifies in covered jurisdictions (where §4 hard-denies with no
fallback).

This is the strongest argument that the 0.8.131–0.8.133 behaviour was wrong on its own terms: the
store-level restriction was already blocking minors worldwide, so denying every `NOT_SHARED` user
at runtime added no protection and removed all legitimate access.

Sources: Play Console Help 9867159 (Manage target audience and app content settings) and 16302250
(Age-Restricted Content and Functionality). Checked 2026-07-26.
