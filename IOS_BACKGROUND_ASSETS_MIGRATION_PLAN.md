# iOS: migrating from On-Demand Resources to Apple-Hosted Background Assets

Status: plan, not started. Written 2026-09-20 against the iOS project at
deployment target 26.0. Companion to
`ANDROID_EXTENDED_LANGUAGE_PACKS_PROPOSAL.md`, which leaves iOS unchanged.

## 1. Why

Apple has deprecated On-Demand Resources (ODR). From the WWDC26 App Store
guide and the App Store Connect help page "On-demand resources size
limits", both read 2026-09-20:

> On-Demand Resources are deprecated starting in iOS 27, iPadOS 27,
> tvOS 27, and visionOS 27. If your app or game uses On-Demand Resources,
> it will continue to function in the near term. However, to minimize
> future user disruption, we encourage you to plan your migration now.

The replacement is Managed Background Assets, and for App Store apps the
Apple-Hosted variant, in which Apple stores and serves the packs. It needs
iOS 26, which is already this app's deployment target, so every user can
receive the new packs from the first release that ships them.

The iOS app delivers three large files through ODR today, all requested by
`ODRManager.swift` with `NSBundleResourceRequest`:

| ODR tag | File | Bytes | Consumer |
|---|---|---|---|
| `database_full` | `perseus_texts_full.db.zip` | 1,085,755,158 | `DatabaseAssetDownloadManager.swift` |
| `database_extended` | `perseus_texts_extended.db.zip` | 3,134,906,462 | `ExtendedDatabaseDownloadManager.swift` |
| `audio_full` | `homer_iliad_chamberlain_audio.zip` | 1,022,816,561 | `AudioAssetDownloadManager.swift` |

Two more tags ship through the same mechanism: `references` (three grammar
PDFs, Smyth, Allen and Greenough, and Whitney, 101,864,744 bytes together,
plus `references_manifest.json`) used by
`ReferencesAssetDownloadManager.swift`, and `topical` (`topical_greek.db.zip`
451,735,465 bytes and `topical_latin.db.zip` 70,929,346 bytes) used by
`TopicalAssetDownloadManager.swift`. The generated
`ClassicsViewer.xcodeproj/project.pbxproj` lists all five tags under
`KnownAssetTags` and holds file references for the PDFs and topical zips.
`ios/project.yml`, however, lists only the three files in the rows above
and excludes `OnDemand/**` from the main resources, so a regeneration of
the project from `project.yml` would leave the PDFs and topical zips out
of the project entirely, and the `references` and `topical` downloads
would fail. The generated project and `project.yml` have drifted; the
migration removes the dependency on either.

Two things about the current setup are worth keeping in mind:

- ODR ties the packs to the Xcode project. Regenerating the project from
  `project.yml` has dropped the resource tags before, which put about 5 GB
  into the base bundle and produced ITMS-90558. Background Assets packs are
  uploaded separately and are not in the Xcode project at all, so that
  failure mode disappears.
- `AssetPackStatus.swift:15-62` still says the full DB is 1.3 GB compressed
  and 7 GB extracted, the extended DB 3.612 GB and 18.028 GB, and the
  references pack "two PDFs", 78 MB. The current files are 1.09 GB and
  4.97 GB, 3.13 GB and 15.0 GB, and three PDFs at 102 MB. Those constants
  should be corrected as part of this work, or better, replaced by
  `AssetPack.downloadSize` read from the manifest at runtime (section 3).

## 2. What Apple-Hosted Background Assets is

Verified on Apple's pages on 2026-09-20 (sources at the end).

- **Asset packs are built outside Xcode** with `xcrun ba-package` from a
  JSON manifest and the files. The output is an `.aar` archive.
- **Packs are uploaded to App Store Connect separately from the app**, by
  Transporter, iTMSTransporter, or the App Store Connect API. Each pack has
  its own version numbers. One version of each pack is live per context:
  internal TestFlight, external TestFlight, App Store.
- **Internal TestFlight uses the latest processed version automatically**,
  with no review. External TestFlight and the App Store require App Review
  of the pack version. Up to ten packs per submission, one version each.
- **When a new pack version is approved for the App Store, it replaces the
  previous version for every app version on every device.** There is no
  rollback and no pinning. A pack must therefore stay compatible with every
  app build still in use, or be submitted together with the app version
  that needs it.
- **Limits** (App Store Connect help, "Apple-hosted asset pack size
  limits"): 200 GB total across all packs and platforms per app, and an
  asset pack count limit the page gives as 200. A December 2025 developer
  forum thread quotes the enforced count as 100. No per-pack size limit is
  published. For comparison, ODR on iOS 18 and later allows 8 GB per pack
  and 70 GB hosted.
- **Download policies** are set in the manifest: `essential` (downloaded
  during install, app does not launch until done), `prefetch` (starts at
  install, continues in background), `onDemand` (only when the app asks).
  All of this app's packs are `onDemand`.
- **The system does not remove downloaded packs on its own** while the app
  is installed. The app calls `remove(assetPackWithID:)` to free space.
  This differs from ODR, which could purge on-demand content under storage
  pressure.
- **Runtime API** is `AssetPackManager` in the `BackgroundAssets`
  framework, an actor, iOS 26 and later:
  - `manifest` lists the packs available to download.
  - `assetPackIsAvailableLocally(withID:)` and `localStatus(ofAssetPackWithID:)`
    answer "is it on the device".
  - `ensureLocalAvailability(of:requireLatestVersion:)` downloads if
    needed and returns when the pack is local. The single-argument form and
    `assetPack(withID:)` are already marked deprecated; use `manifest`
    and the two-argument form.
  - `statusUpdates(forAssetPackWithID:)` is an async sequence of
    `began`, `paused`, `downloading(progress)`, `finished`, `failed`.
    Cancelling is `progress.cancel()` on the `downloading` case.
  - `url(for:)`, `descriptor(for:)` and `contents(at:)` give access to a
    file inside a pack by its relative path. `url(for:)` is what the
    existing zip extraction code needs.
  - `checkForUpdates()` refreshes pack information from the server and
    updates or removes packs as needed.
  - `remove(assetPackWithID:)` deletes the pack from the device.
- **Project requirements**: a downloader extension target (Xcode template
  "Background Download", type "Apple-Hosted, Managed") that adopts
  `StoreDownloaderExtension` from StoreKit, an App Groups capability
  shared by the app and the extension, and three Info.plist keys on the
  app: `BAAppGroupID`, `BAHasManagedAssetPacks` = YES,
  `BAUsesAppleHosting` = YES. Apple says to omit all other Background
  Assets keys when using Apple hosting. The default extension needs no
  custom code; `shouldDownload(_:)` is optional.
- **Local testing** uses `xcrun ba-serve` as a mock server. It requires
  HTTPS with a root certificate installed on the test device, and the
  device's Developer Settings pointed at the server through a URL override.
  Simulators failed with "The process lacks a team ID" until OS 26.5
  beta 1; testing on a device avoids that.
- **Coexistence with ODR** in one app during a transition is described as
  possible by third-party write-ups (Swift with Majid, February 2026; The
  Swift Dev, June 2026). I did not find an Apple statement either way.
  Section 6 does not rely on it.

Reading a file: the system merges all downloaded packs into one namespace,
so `url(for: "perseus_texts_extended.db.zip")` works without naming the
pack. `contents(at:)` and `descriptor(for:)` take a
`searchingInAssetPackWithID:` argument to narrow the search; `url(for:)`
takes only the path. Our packs carry distinct file names already, so the
merged namespace is enough.

## 3. Target design

### Packs

One pack per current ODR tag, same file inside, same file name:

| Asset pack ID | Contents | Policy |
|---|---|---|
| `database_full` | `perseus_texts_full.db.zip` | onDemand |
| `database_extended` | `perseus_texts_extended.db.zip` | onDemand |
| `audio_full` | `homer_iliad_chamberlain_audio.zip` | onDemand |
| `references` | the three grammar PDFs and `references_manifest.json` | onDemand |
| `topical` | `topical_greek.db.zip`, `topical_latin.db.zip` | onDemand |

Keeping the IDs equal to the ODR tag strings means `ODRManager.AssetTag`
keeps its raw values and the five download managers keep their call sites.
Five packs against a count limit of 100 or 200 is no constraint. Total
hosted size is about 5.9 GB against 200 GB.

The 3.13 GB extended pack is expected to be accepted as one pack. It
already ships through ODR at this size, within ODR's 8 GB per-pack limit
for iOS 18 and later, and the Apple-hosted limits page states only a
200 GB total and a pack count, with no per-pack maximum. The Android
proposal splits the extended DB for Google's 1.5 GB cap; nothing published
requires that on iOS. The pack is uploaded before device testing in any
case (section 7), so an unexpected refusal would surface at the first
upload.

### Manifest

One JSON manifest per pack, kept in the repo under `ios/AssetPacks/manifests/`
and produced by `xcrun ba-package template` once, then edited:

```json
{
  "assetPackID": "database_extended",
  "downloadPolicy": { "onDemand": {} },
  "fileSelectors": [
    { "file": "perseus_texts_extended.db.zip" }
  ],
  "platforms": ["iOS"]
}
```

`fileSelectors` paths are relative to the pack's source root, which is
`ios/ClassicsViewer/Resources/OnDemand/`, the directory the assembly
already fills. The `.aar` output goes to `ios/AssetPacks/packaged/`, which
is build output and is never staged.

### Runtime

`ODRManager` becomes a thin actor over `AssetPackManager` with the same
five entry points the download managers use today:

| Today (`ODRManager`) | After |
|---|---|
| `isDownloaded(tag:)` via `conditionallyBeginAccessingResources()` | `AssetPackManager.shared.assetPackIsAvailableLocally(withID: tag.rawValue)` |
| `download(tag:progressCallback:)` via `beginAccessingResources()` and KVO on `progress` | look the pack up in `manifest`, run `statusUpdates(forAssetPackWithID:)` on a task that forwards `downloading(_, progress)` to the callback, then `ensureLocalAvailability(of: pack, requireLatestVersion: true)` |
| `assetPath(tag:filename:)` via `request.bundle.url(forResource:)` | `AssetPackManager.shared.url(for: FilePath(filename))`; the file names are unique across packs |
| `cancelDownload(tag:)` via `request.progress.cancel()` | `progress.cancel()` on the last `downloading` update seen for that pack |
| `releaseResources(tag:)` via `endAccessingResources()` | no operation; see removal below |

The rest of each download manager, the zip extraction into `Documents/`
with the rename to `perseus_texts_full.db` or `perseus_texts_extended.db`,
the `UserDefaults` flags, `DatabaseManagerAsync.swift`'s file selection,
and the restart prompts, stay as they are. The
`NSBundleResourceRequestLowDiskSpaceNotification` observer in
`ODRManager.swift:182-207` has no Background Assets equivalent, because
the system does not purge these packs; it is removed along with the
`.odrResourcesMayBePurged` notification it posts.

### Removal and re-download

With ODR the zip could be purged by the system after extraction, and the
extracted DB in `Documents/` was the working copy. With Background Assets
the 3.13 GB zip would stay on the device beside the 15 GB extracted DB
unless the app removes it. The plan: after a successful extraction and
verification, call `remove(assetPackWithID:)`. If the user later deletes
the extracted DB through the existing "Delete" action and wants it back,
`ensureLocalAvailability` downloads the pack again. `removeFullDatabase()`
and its extended twin already call `releaseResources`; that call becomes
`remove(assetPackWithID:)`.

The compressed sizes shown before a download come from
`AssetPack.downloadSize` on the manifest entry, not from the constants in
`AssetPackStatus.swift`. The extracted sizes and free-space requirements
stay as constants, corrected to the current files.

### Pack versions and the extracted copy

An asset pack version can change under an installed app. The download
managers should record `AssetPack.version` in `UserDefaults` alongside the
existing "installed" flags when they extract, and show "Update available"
when `manifest` reports a higher version than the one extracted. Today
there is no such check with ODR either, so this is an improvement, not a
requirement for parity; it is listed as a decision in section 8.

Because a new pack version replaces the old one for every app build in
use, the data release inside a pack must keep working with older app
builds. The whole-file DBs already carry the canonical schema and the
app validates schema on open, so an incompatible DB fails visibly rather
than silently. A schema change on iOS therefore requires the pack and the
app version to be submitted together, which App Store Connect allows.

## 4. Project changes

These touch entitlements and `project.yml` capabilities and need explicit
approval before they are made, per the standing rule for this project.
None of them is made by this plan.

1. **App Groups capability** on the app target and the new extension
   target, one shared group, proposed `group.com.classicsviewer.app`. This
   is a new entitlement in `ClassicsViewer.entitlements`, which today holds
   only `com.apple.developer.declared-age-range`.
2. **Downloader extension target**, `ClassicsViewerAssetDownloader`, from
   the Xcode "Background Download" template, type "Apple-Hosted, Managed",
   adopting `StoreDownloaderExtension`. Expressed in `project.yml` as an
   `app-extension` target embedded in the app, with its own bundle ID under
   the app's, the same deployment target, and the App Groups entitlement.
3. **Info.plist keys** on the app: `BAAppGroupID` (the group above),
   `BAHasManagedAssetPacks` YES, `BAUsesAppleHosting` YES.
4. **Remove the ODR wiring** from `project.yml`: the three `resourceTags`
   entries, `OnDemandResourcesInitialInstallTags`,
   `OnDemandResourcesPrefetchOrder`, `ENABLE_ON_DEMAND_RESOURCES`,
   `EMBED_ASSET_PACKS_IN_PRODUCT_BUNDLE`. The `OnDemand/**` exclusion on
   the main resources path stays, so the large files are never copied into
   the bundle by accident. This is the step that ends the tags-dropped
   risk.
5. **Frameworks**: link `BackgroundAssets` in the app and the extension,
   `StoreKit` in the extension.
6. The `ODRManager` rewrite in section 3 and the two removed
   notification hooks. `ODRManager.swift` keeps its name and its
   `AssetTag` enum; a rename to `AssetPackStore` is cosmetic and can wait.

The age-verification code and its entitlement are not touched. The
extension downloads only what the app asks for and adds no network use of
the app's own; Apple's framework rule that Background Assets is used only
to fetch app assets is satisfied.

## 5. Build pipeline changes

The assembly already copies the iOS zips into
`ios/ClassicsViewer/Resources/OnDemand/`. Add one step after those copies,
in `monolith_fn.py`'s deployment code, that packages each pack:

```
xcrun ba-package ios/AssetPacks/manifests/<pack>.json \
    -o ios/AssetPacks/packaged/<pack>.aar
```

Rules for the step:

- It runs only when `xcrun` is available; the pipeline is macOS-only for
  iOS output already, and Apple also ships the packaging tool for Linux if
  that ever changes.
- A pack whose manifest lists a file that is missing fails the build.
- The step writes `ios/AssetPacks/packaged/index.json` with each pack's
  ID, source file, size, sha256 and the assembly's `build_time`, for the
  upload log.
- Uploading the `.aar` files to App Store Connect is a manual step, done
  with Transporter or the App Store Connect API, like every other upload
  in this project.

The audio, references and topical packs are not produced by the assembly;
their source files are static. The same packaging step covers them from
the same manifests directory, so one command produces all five.

`BUILD.md`'s iOS notes and `ios/BUILD_INSTRUCTIONS.md` gain the packaging
step and lose the ODR tag instructions.

## 6. Cutover

Because one pack version is live per context and a new version replaces
the old for all installed app builds, the order matters:

1. Land the project and code changes (section 4) in a build that contains
   no ODR tags. Upload the five `.aar` packs to App Store Connect. Internal
   TestFlight picks them up with no review.
2. Test on device (section 7).
3. Submit the app version and the five pack versions in one submission.
   Apple's rule: if a new app version requires a new asset pack to
   function, include the asset pack in the same submission.
4. After approval, users on the old ODR build keep working; ODR is
   deprecated, not disabled. Users who update get the new packs. Their
   previously extracted DBs in `Documents/` are untouched, so nobody
   re-downloads anything unless they choose to.

No gradual coexistence of ODR and Background Assets is planned, so the
unverified coexistence question does not arise.

## 7. Verification

1. **Upload the five packaged packs** to App Store Connect and confirm
   each processes. The 3.13 GB extended pack is expected to be accepted
   (section 3); this upload is the first step of testing, not a separate
   probe.
2. **Device test through internal TestFlight**, not the simulator and not
   `ba-serve`, unless the root-certificate setup for `ba-serve` is wanted
   for repeated local runs. For each of the five packs: download, progress
   updates, cancel mid-download, extraction, `remove`, re-download.
3. **Existing flows unchanged**: full DB activate and revert, extended DB
   activate and revert, delete, the "Restart Required" prompts, external
   DB import, references and topical open after download.
4. **App update over an ODR build**: install the current App Store build,
   download and extract the full DB, then install the new build over it.
   The extracted DB must still be selected and open. `useFullDatabase`
   must survive.
5. **Storage**: after extraction and `remove`, Settings > Storage shows
   the app without the pack; the extracted DB remains.
6. **Age verification** still runs at launch and is unaffected.

The iOS app is built and uploaded by the project owner; this plan produces
the Swift, manifest and build-step changes and stops there.

## 8. Decisions

1. Approve the App Groups entitlement, the extension target and the
   Info.plist keys (section 4). Nothing else can start before this.
2. Remove a pack from the device after extraction (recommended, saves the
   zip's size) or keep it.
3. Record the pack version at extraction and offer "Update available"
   (recommended), or keep today's behaviour of never re-offering.
4. Keep the extended DB as one 3.13 GB pack (recommended; expected to be
   accepted) or split it as the Android proposal does.
5. Whether to keep `ODRManager` as the type name.

## 9. Risks

- **Pack version replacement is global.** A pack uploaded for a new app
  version reaches old app versions the moment it is approved. Mitigation:
  submit packs with the app version that needs them, and keep the DB
  schema compatible across builds, which the canonical schema already
  enforces.
- **No per-pack size limit is published.** The 3.13 GB extended pack is
  expected to be accepted, since it ships through ODR today and the
  Apple-hosted limits page states no per-pack maximum. If the first upload
  refuses it, the fallback is splitting the zip into two packs and joining
  on device.
- **First-run tooling.** `ba-package`, `ba-serve`, the extension template
  and the simulator team-ID fix are all 26.x-era; expect small tooling
  differences between Xcode point releases.
- **Review turnaround.** External TestFlight and App Store both review
  packs. Internal TestFlight does not, which is where testing should
  happen.
- **Deprecation timing.** Apple says ODR "will continue to function in
  the near term" with no end date. The risk of waiting is an unannounced
  cutoff; the cost of moving is the work above.

## Sources

- WWDC26 App Store guide, deprecation statement and the 200 GB figure:
  https://developer.apple.com/wwdc26/guides/app-store/
- App Store Connect Help, "On-demand resources size limits" (deprecation
  notice and the iOS 18 ODR table):
  https://developer.apple.com/help/app-store-connect/reference/app-uploads/on-demand-resources-size-limits
- App Store Connect Help, "Apple-hosted asset pack size limits":
  https://developer.apple.com/help/app-store-connect/reference/app-uploads/apple-hosted-asset-pack-size-limits/
- App Store Connect Help, "Overview of Apple-hosted asset packs":
  https://developer.apple.com/help/app-store-connect/manage-asset-packs/overview-of-apple-hosted-asset-packs
- App Store Connect Help, "Test Apple-hosted asset packs":
  https://developer.apple.com/help/app-store-connect/test-a-beta-version/test-apple-hosted-asset-packs
- App Store Connect Help, "Submit Apple-hosted asset packs":
  https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/submit-apple-hosted-asset-packs
- Background Assets framework and articles "Downloading Apple-hosted
  asset packs", `AssetPackManager`, `AssetPack`:
  https://developer.apple.com/documentation/backgroundassets
- WWDC25 session 325, "Discover Apple-Hosted Background Assets":
  https://developer.apple.com/videos/play/wwdc2025/325/
- Apple Developer Forums thread 803976 (simulator team-ID error, fixed in
  OS 26.5 beta 1): https://developer.apple.com/forums/thread/803976
- Apple Developer Forums thread 810659 (100-pack count enforced, December
  2025): https://developer.apple.com/forums/thread/810659
