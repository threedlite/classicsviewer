# References Asset Pack — Design Doc

Status: Draft
Author: Claude (with danmeany@gmail.com)
Date: 2026-05-21
Target release: TBD (post 0.8.125)

## 1. Goal

Ship a new on-demand Play Asset Delivery pack named **`references_pack`** containing the reference PDFs in `references/` (Smyth's *Greek Grammar for Colleges* and Allen & Greenough's *New Latin Grammar*). When the pack is installed, the main menu gains a **References** item that opens a list of installed reference works; tapping one opens a built-in PDF viewer that supports pinch-to-zoom, jump-to-page, and per-document last-read-page resume.

Out of scope:
- Bundling the PDFs in the base APK (they total ~75 MB — too large for the install-time path that already carries the sample DB + audio).
- Annotations, highlights, search-inside-PDF. (Future work.)
- Modifying or generating the PDFs from source. They are checked-in binaries sourced from archive.org per `references/README.txt`.

iOS parity is **in scope** — see §10. Both platforms must ship the feature in the same release.

## 2. Constraints (from `CLAUDE.md` and project conventions)

- 100% local operation. No internet permission, no runtime download from anywhere except the Play Asset Delivery API already in use.
- Schema-stable: **no** Room version bumps and **no** entity changes (see `CLAUDE.md` → "Backwards Compatibility"). Per-PDF last-read state goes in `SharedPreferences`, not the Room database.
- Asset pack discipline mirrors `audio_pack` / `full_database_pack`: each is a separate Gradle module with `com.android.asset-pack` plugin and `dynamicDelivery { deliveryType = "on-demand" }`.
- Menu item must be **conditionally visible** — only shown when `assetPackManager.getPackLocation("references_pack")` is non-null. This matches the pattern where "Download Full Database" stays in the menu but the post-download UX swaps in.

## 3. Asset pack layout

New Gradle module at the repo root:

```
references_pack/
  build.gradle
  src/main/assets/
    allengreenoughsn00alleiala.pdf
    greekgrammarforc0000herb.pdf
    references_manifest.json          ← see §5
```

`references_pack/build.gradle`:

```gradle
plugins {
    id 'com.android.asset-pack'
}

assetPack {
    packName = "references_pack"
    dynamicDelivery {
        deliveryType = "on-demand"
    }
}
```

`settings.gradle` adds:

```gradle
include ':references_pack'
```

`app/build.gradle` adds the pack to `assetPacks`:

```gradle
assetPacks = [":full_database_pack", ":audio_pack", ":references_pack"]
```

Per BUILD.md §"Audio packaging", asset-pack assets are an AAB-only feature — they ship via `bundleRelease`, not `assembleDebug`. For debug builds we'll fall back to reading the PDFs from `app/src/debug/assets/references/` so devs can exercise the UI without a Play install (mirrors how the debug DB is bundled directly in APK assets while production uses the pack).

## 4. Populating the pack

A new step in `BUILD.md` between the audio step and the AAB build:

```bash
# Copy reference PDFs into the on-demand pack before bundling.
mkdir -p references_pack/src/main/assets
cp references/*.pdf references_pack/src/main/assets/
# Also generate the manifest (see §5):
./venv/bin/python3 references_pack/build_manifest.py
```

`references_pack/build_manifest.py` is a ~30-line stdlib-only script that:
1. Lists every `*.pdf` in `references/`.
2. For each, opens with `pypdf` to read `/Title`, `/Author`, and page count. Falls back to filename-derived title if metadata is empty.
3. Writes `references_pack/src/main/assets/references_manifest.json`.

Constraints from `CLAUDE.md`:
- Script lives in the pack's own directory (self-contained, like the language modules under `greek/`, `latin/`, etc.).
- No "manual fixes" — the build script regenerates the manifest from the PDFs every release.
- If a future PDF has no title metadata, the script must fail loudly (not silently emit "Untitled") so the build catches missing data.

## 5. The manifest (`references_manifest.json`)

A static JSON that the app reads at runtime instead of scraping PDF metadata on-device (faster, no PDF library cost on the menu path). Schema:

```json
{
  "version": 1,
  "entries": [
    {
      "id": "smyth_greek_grammar",
      "filename": "greekgrammarforc0000herb.pdf",
      "title": "Greek Grammar for Colleges",
      "author": "Herbert Weir Smyth",
      "language": "greek",
      "pageCount": 838,
      "sizeBytes": 45706457
    },
    {
      "id": "allen_greenough_latin",
      "filename": "allengreenoughsn00alleiala.pdf",
      "title": "New Latin Grammar",
      "author": "Allen and Greenough",
      "language": "latin",
      "pageCount": 512,
      "sizeBytes": 32766486
    }
  ]
}
```

`id` is stable across releases — it keys the last-read-page SharedPreferences (§9). Choose IDs based on a slug of author + short title; never derive from filename (filenames may change if we replace sources).

## 6. PDF rendering — platform `PdfRenderer`

Use `android.graphics.pdf.PdfRenderer` (API 21+). No new dependencies, no JitPack/`FAIL_ON_PROJECT_REPOS` friction, no license footprint. Pinch-zoom and page jump are implemented by hand on top of it — outline below.

**Architecture:**

- `PdfViewerActivity` hosts a single `PdfPageView` (custom `View` subclass) plus a translucent footer with `currentPage / pageCount` and an overflow "Go to page" menu item.
- `PdfPageView` owns:
  - A `PdfRenderer` opened on a `ParcelFileDescriptor` for the PDF file (PdfRenderer requires a seekable FD — we copy the asset/pack file to `cacheDir` once per session if it's not already a regular File path).
  - The currently rendered page `Bitmap`, rendered **at 3× fit-width resolution in `Bitmap.Config.RGB_565`** (these PDFs are grayscale archive.org scans — RGB_565 looks identical to ARGB_8888 to the eye and halves memory).
  - A `Matrix` holding the current pan/zoom transform (the bitmap stays fixed; the matrix scales/translates it for display).
  - A `ScaleGestureDetector` for pinch-to-zoom, **clamped 1.0×–3.0×** (matches the rendered resolution exactly, so every zoom level is pixel-sharp with zero upscale — no re-render step needed).
  - A `GestureDetector` for double-tap-to-zoom (toggles between 1.0× and 2.5×) and for horizontal-fling page turns when zoom == 1.0× (when zoomed in, drag pans; when zoomed out, horizontal fling pages).
  - `onDraw` blits the bitmap through the current matrix.
- When the user crosses a page boundary, the view closes the previous `PdfRenderer.Page`, opens the next via `renderer.openPage(n)`, and renders into a fresh bitmap. The old bitmap is recycled before being reassigned to keep memory bounded — one decoded page on-screen at a time, no neighbour caching in v1.
- `onPause` persists state and closes the page and renderer; `onResume` reopens at the saved page/zoom/offset.

**Memory budget** (one page at a time, RGB_565, 3× fit-width):

| Device class | Content width | Bitmap |
|---|---|---|
| Phone portrait | ~1080 px | ~30 MB |
| 8" tablet portrait | ~1600 px | ~67 MB |
| 10" tablet landscape | ~2560 px | ~170 MB |

Android 8.0+ allocates bitmaps in native memory, not the Java heap, so these sizes do not push against `Runtime.maxMemory()`. The largest case (~170 MB on big tablets in landscape) is the only one to watch — if testing on a low-end tablet OOMs, the fallback is to drop to 2× render + cap zoom at 2.0×, with no other code changes.

Estimated cost: ~250 lines for `PdfPageView` + `PdfViewerActivity` (re-render machinery dropped). No new dependencies in `app/build.gradle`.

## 7. Menu wiring

`app/src/main/res/menu/main_menu.xml` — add two items after `action_rhetoric`:

```xml
<item
    android:id="@+id/action_references"
    android:title="@string/references_menu_title"
    app:showAsAction="never" />

<item
    android:id="@+id/action_download_references"
    android:title="@string/references_download_menu_title"
    app:showAsAction="never" />
```

`MainActivity.kt`:

- In `onCreateOptionsMenu`, inflate the menu, then ask `ReferencesPackManager(this).isInstalled()`:
  - Installed → show `action_references`, hide `action_download_references`.
  - Not installed → hide `action_references`, show `action_download_references` (title displays "Download References (~75 MB)").
- In `onOptionsItemSelected`:
  - `R.id.action_references → startActivity(Intent(this, ReferencesListActivity::class.java))`
  - `R.id.action_download_references → startActivity(Intent(this, ReferencesDownloadActivity::class.java))`

`ReferencesDownloadActivity` is a near-copy of `FullDatabaseDownloadActivity`/`AudioDownloadActivity`:

- Shows pack name, total size (~75 MB), and a "Download" button.
- Wires `AssetPackManager.fetch(listOf("references_pack"))` with the same listener pattern, progress UI, error mapping, and "Requires user confirmation" handling already implemented in `FullDatabaseDownloadManager`. The 75 MB pack is well under the 200 MB Play threshold that triggers user confirmation, so the confirmation path is unlikely to fire — but the code path stays for parity.
- On `COMPLETED`, finishes and pops back to `MainActivity`; `onResume` there re-checks `isInstalled()` and the menu reshuffles automatically.

`strings.xml`:

```xml
<string name="references_menu_title">References</string>
<string name="references_download_menu_title">Download References (~75 MB)</string>
```

## 8. New components

### `data/ReferencesPackManager.kt`

Facade over `AssetPackManager`, modeled on `FullDatabaseDownloadManager`. Responsibilities:

- `isInstalled(): Boolean` — `getPackLocation("references_pack") != null`. In debug builds, also returns true when `assets/references/` is populated (via `copyReferencesToDebugAssets`).
- `getAssetsPath(): String?` — absolute filesystem path to the directory holding PDFs + manifest. Returns the pack's `assetsPath()` in release, or a debug-only fallback under `cacheDir` (extracted from `assets/references/`) in debug.
- `loadManifest(): ReferencesManifest` — reads `references_manifest.json` from `<assetsPath>/references_manifest.json`. Cached in-process after first read.
- `startDownload(...)` / `cancelDownload()` / `removeAssetPack()` — same shape as `FullDatabaseDownloadManager`, delegated to `AssetPackManager`. Used by `ReferencesDownloadActivity`.
- `getPdfFile(entryId): File?` — convenience used by `PdfViewerActivity`. Must return a regular `File` (not an `AssetFileDescriptor`), because `PdfRenderer` needs a seekable `ParcelFileDescriptor` from a real file. Pack files are already on disk; in debug the helper copies `assets/references/<filename>.pdf` to `cacheDir/references/` once, then reuses it.

### `ReferencesListActivity.kt`

- Extends `BaseActivity` like the other lists.
- Layout: a `RecyclerView` of `ReferencesManifest.entries`, each row showing title, author, page count, and "last read page X of Y" if `PreferencesManager.getLastReadPage(id)` is set.
- Tapping a row launches `PdfViewerActivity` with extras `{ entryId, filename, title, pageCount }`.

### `PdfViewerActivity.kt` + `PdfPageView.kt`

- Layout: full-screen custom `PdfPageView` plus a translucent footer (`currentPage / pageCount`) and an action bar with a "Go to page" overflow item.
- `onCreate`:
  1. Resolve a `File` for the PDF via `ReferencesPackManager.getPdfFile(entryId)`.
  2. Open `ParcelFileDescriptor.open(file, MODE_READ_ONLY)` → `PdfRenderer(pfd)`.
  3. Restore `entryId`'s saved state from `PreferencesManager.getReferenceState(entryId)` (page, zoom, scrollX, scrollY — all optional; defaults: page 0, zoom 1.0, scroll 0/0).
  4. Render the initial page once at 3× fit-width into an `RGB_565` bitmap. Apply the restored matrix.
- Gestures (implemented in `PdfPageView`):
  - `ScaleGestureDetector` → pinch-to-zoom around the focal point, zoom clamped to **[1.0, 3.0]** (matches rendered resolution, so the bitmap never has to be re-rendered or upscaled).
  - `GestureDetector.onDoubleTap` → toggle zoom between 1.0× and 2.5× around the tap point.
  - `GestureDetector.onScroll` → when zoom > 1.0, pan the matrix (clamped so the page stays within view bounds, no overscroll). When zoom == 1.0, treat horizontal scrolls past a threshold as page turns.
  - `GestureDetector.onFling` → at zoom == 1.0, a horizontal fling switches page (with a short slide animation). At zoom > 1.0, falls through to standard fling within the page.
- Page changes: close current `PdfRenderer.Page`, open next, recycle and reallocate the bitmap at the same 3× fit-width size. One decoded page at a time.
- "Go to page" → `AlertDialog` with a numeric `EditText`. Validate `1 <= page <= pageCount` (otherwise show inline error and don't dismiss). Calls `goToPage(page - 1)` which animates the same way as a horizontal fling.
- `onPause`: persist `{ page, zoom, scrollX, scrollY }` via `PreferencesManager.setReferenceState(entryId, ...)`. Close the page and renderer in `onDestroy`.

Last-read state is **per `entryId`, not per filename**, so renaming source PDFs in the future doesn't lose user state.

### `ReferencesDownloadActivity.kt`

Mirrors `FullDatabaseDownloadActivity`:

- Single button + progress bar + status text. Same layout patterns and string conventions.
- Uses `ReferencesPackManager.startDownload` for fetch, listens for progress/completion/error, surfaces the `REQUIRES_USER_CONFIRMATION` confirmation dialog through an `ActivityResultLauncher<IntentSenderRequest>` (the 75 MB size is below Play's "large download" threshold so this path rarely fires).
- On completion, `finish()` — caller's `onResume` re-checks `isInstalled()` and reshuffles the menu.

## 9. Persistence — last-read page, zoom, and scroll offset

Per `CLAUDE.md`, do not add a Room entity. Use `SharedPreferences` — `utils/PreferencesManager.kt` already exposes a private `getPrefs(context)` and is the project's standard place for app-level preferences (font size, color inversion, full-database flag, etc.). We add new keys to the same prefs file; no new infrastructure.

We persist four scalars per `entryId`: page index, zoom factor, and the X/Y scroll offsets within the page (in **page coordinates** at zoom 1.0, not device pixels, so the values are stable across rotation and device changes).

New helpers in `utils/PreferencesManager.kt`:

```kotlin
private const val KEY_REF_PAGE    = "references.page."
private const val KEY_REF_ZOOM    = "references.zoom."
private const val KEY_REF_SCROLLX = "references.scrollX."
private const val KEY_REF_SCROLLY = "references.scrollY."

data class ReferenceState(val page: Int, val zoom: Float, val scrollX: Float, val scrollY: Float)

fun getReferenceState(context: Context, entryId: String): ReferenceState? {
    val prefs = getPrefs(context)
    if (!prefs.contains(KEY_REF_PAGE + entryId)) return null
    return ReferenceState(
        page    = prefs.getInt(KEY_REF_PAGE + entryId, 0),
        zoom    = prefs.getFloat(KEY_REF_ZOOM + entryId, 1.0f),
        scrollX = prefs.getFloat(KEY_REF_SCROLLX + entryId, 0f),
        scrollY = prefs.getFloat(KEY_REF_SCROLLY + entryId, 0f),
    )
}

fun setReferenceState(context: Context, entryId: String, s: ReferenceState) {
    getPrefs(context).edit()
        .putInt(KEY_REF_PAGE + entryId, s.page)
        .putFloat(KEY_REF_ZOOM + entryId, s.zoom)
        .putFloat(KEY_REF_SCROLLX + entryId, s.scrollX)
        .putFloat(KEY_REF_SCROLLY + entryId, s.scrollY)
        .apply()
}

fun getLastReadPage(context: Context, entryId: String): Int? =
    getReferenceState(context, entryId)?.page  // convenience for the list row
```

Convert between the matrix in `PdfPageView` and these stored coordinates by:
- Storing the matrix's net translation divided by the current zoom (so `scrollX/Y` is in page-space units).
- On restore, apply zoom first, then translate by `scrollX × zoom`, `scrollY × zoom`.

If the saved zoom × scroll combination would place the page off-screen on the current device (e.g. rotated, or a smaller screen), the view clamps back to valid bounds on first frame and re-persists. No special migration needed.

## 10. iOS parity

iOS must ship the References feature in the same release as Android. iOS already uses NSBundleResourceRequest On-Demand Resources (ODR) for the full audio and the full/extended databases (see `ios/ClassicsViewer/AssetPacks/ODRManager.swift`, `AudioAssetDownloadManager.swift`, `ExtendedDatabaseDownloadManager.swift`). References slots in as a fourth ODR pack with the same shape.

### iOS asset pack

- Add a new tag `references` to `ODRManager.AssetTag` (alongside `audioFull`, `databaseFull`, `databaseExtended`).
- Add a new `AssetPackInfo.references` constant with the expected ~75 MB compressed size.
- Ship the two PDFs + `references_manifest.json` under `ios/ClassicsViewer/Resources/OnDemand/References/`, each tagged `references` in the Xcode resource-tag configuration. **Critical:** per the `project_ios_odr_asset_tags` memory, ODR tags are easily dropped from `project.pbxproj` on regeneration, which bloats the app to 5 GB and triggers ITMS-90558. The Xcode project changes for this feature must be made by hand and not regenerated via xcodegen.

### iOS download manager

`ios/ClassicsViewer/AssetPacks/ReferencesAssetDownloadManager.swift`, structurally identical to `AudioAssetDownloadManager`:
- `@MainActor`, `ObservableObject`, `@Published` status + progress.
- Uses `ODRManager.shared.beginAccess(tag: .references)` / `endAccess`.
- Exposes `installedPDFs() -> [ReferenceEntry]` derived from the bundled manifest JSON.

### iOS UI

- `ios/ClassicsViewer/Views/ReferencesDownloadView.swift` — SwiftUI view modeled on `AudioDownloadView`. Shown when the pack is not yet downloaded.
- `ios/ClassicsViewer/Views/ReferencesListView.swift` — list of installed reference works (title, author, page count, last-read indicator). Tapping a row pushes the viewer.
- `ios/ClassicsViewer/Views/PDFReaderView.swift` — a thin SwiftUI wrapper around `UIViewRepresentable` of `PDFKit.PDFView`. PDFKit gives pinch-zoom and double-tap zoom for free, exposes `currentPage`, `go(to:)`, and `PDFView.scaleFactor` + `documentView.bounds.origin` for scroll-offset persistence. License-free, part of the standard SDK.
- The main app menu (in whatever the top-level navigation view is called) shows "References" when installed, "Download References (~75 MB)" otherwise. Mirror the conditional Android wiring.

### iOS persistence

Add UserDefaults helpers in `Utilities/UserDefaults+Extensions.swift` (the existing pattern used by `fullAudioInstalled`):

```swift
extension UserDefaults {
    func referenceState(entryId: String) -> (page: Int, zoom: CGFloat, scrollX: CGFloat, scrollY: CGFloat)? { ... }
    func setReferenceState(entryId: String, page: Int, zoom: CGFloat, scrollX: CGFloat, scrollY: CGFloat) { ... }
}
```

Same `entryId` slugs as Android (`smyth_greek_grammar`, `allen_greenough_latin`) — defined once in `references_manifest.json`, which iOS reads from the on-demand bundle the same way Android reads it from the asset pack. This keeps the two platforms behaviour-aligned (e.g. so analytics/debug logs across both surface the same identifiers).

### iOS Mac availability

Per memory `project_ios_mac_availability`, the iOS app distributes to Apple Silicon Macs but `AgeVerificationView.swift` hard-blocks Mac. References inherits whatever availability is already in place — no Mac-specific work required, and the References feature does not call any Mac-unavailable API.

### iOS build hand-off

Per memories `feedback_never_compile_ios` and `feedback_get_approval_project_config`:

- **I will not run `xcodebuild`, `xcodegen`, or regenerate the project.** The Swift source files are written; the user owns adding them to the Xcode target and configuring the new `references` resource tag.
- The Xcode steps to hand off:
  1. Add the four new Swift files to the `ClassicsViewer` target.
  2. Add `ios/ClassicsViewer/Resources/OnDemand/References/` and its contents to the project.
  3. In each PDF and the manifest's File Inspector, set "On Demand Resource Tags" to `references`.
  4. Verify in *Editor → Edit ODR Tags...* that the `references` tag exists and is set to "Initial Install Tags: off" (so it's a true on-demand pack).
- No entitlements or signing changes are needed; ODR is part of the default capability set.

## 11. Build/CI changes

`BUILD.md` additions, in three places:

1. **Step 6 / module builds** — add a sub-section "References pack" that runs `references_pack/build_manifest.py` and the `cp references/*.pdf references_pack/src/main/assets/` step. The full PDFs (~75 MB) stay in `references/` checked into git as they are now; the pack module's `assets/` directory is build output and should be `.gitignore`d.

2. **Step 8 / Audio packaging** — add a parallel "References packaging" subsection making the same install-time vs. asset-pack-only distinction. For debug builds, copy the PDFs into `app/src/debug/assets/references/` via a small Gradle task analogous to `copyAudioToAssets`. For release AAB, the `references_pack` module is the sole source.

3. **iOS section** — add a "References (iOS)" sub-section noting that `cp references/*.pdf ios/ClassicsViewer/Resources/OnDemand/References/` + `cp references_pack/src/main/assets/references_manifest.json ios/ClassicsViewer/Resources/OnDemand/References/` must run before the iOS archive build, and that the `references` ODR tag must be present in `project.pbxproj` (see §10 memory note).

4. **`bundleRelease` expected size** — update the expected ~2 GB total to include the additional ~75 MB references pack. On-demand packs do not count against the 200 MB base-AAB size limit.

CI: no new bot — the existing `bundleRelease` job will exercise the asset-pack manifest because Gradle will fail if `references_pack/src/main/assets/` is empty (same failure mode as `audio_pack`). iOS CI is hand-off-only per memory.

## 12. File-by-file change list

**Android — new:**
- `references_pack/build.gradle`
- `references_pack/build_manifest.py`
- `references_pack/.gitignore` (`src/main/assets/*.pdf`, `src/main/assets/references_manifest.json`)
- `app/src/main/java/com/classicsviewer/app/data/ReferencesPackManager.kt`
- `app/src/main/java/com/classicsviewer/app/data/ReferencesManifest.kt` (data class + JSON parser using `org.json.JSONObject` — no new dependency)
- `app/src/main/java/com/classicsviewer/app/references/ReferencesListActivity.kt`
- `app/src/main/java/com/classicsviewer/app/references/ReferenceListAdapter.kt`
- `app/src/main/java/com/classicsviewer/app/references/ReferencesDownloadActivity.kt`
- `app/src/main/java/com/classicsviewer/app/references/PdfViewerActivity.kt`
- `app/src/main/java/com/classicsviewer/app/references/PdfPageView.kt`
- `app/src/main/res/layout/activity_references_list.xml`
- `app/src/main/res/layout/item_reference.xml`
- `app/src/main/res/layout/activity_references_download.xml`
- `app/src/main/res/layout/activity_pdf_viewer.xml`
- `app/src/main/res/menu/pdf_viewer_menu.xml` (just "Go to page")

**Android — modified:**
- `settings.gradle` — add `:references_pack`
- `app/build.gradle` — add `:references_pack` to `assetPacks`, add `copyReferencesToDebugAssets` task
- `app/src/main/AndroidManifest.xml` — register `ReferencesListActivity`, `ReferencesDownloadActivity`, `PdfViewerActivity`
- `app/src/main/res/menu/main_menu.xml` — add `action_references` and `action_download_references` items
- `app/src/main/java/com/classicsviewer/app/MainActivity.kt` — show/hide the two menu items in `onCreateOptionsMenu`, route in `onOptionsItemSelected`
- `app/src/main/java/com/classicsviewer/app/utils/PreferencesManager.kt` — add `ReferenceState`, `getReferenceState`, `setReferenceState`, `getLastReadPage`
- `app/src/main/res/values/strings.xml` — add `references_menu_title`, `references_download_menu_title`, `references_goto_page_title`, `references_goto_page_hint`, `references_invalid_page`
- `BUILD.md` — Step 6 references-pack subsection, Step 8 references packaging subsection, iOS subsection, expected AAB size update

**iOS — new (hand-off to user for Xcode project integration):**
- `ios/ClassicsViewer/AssetPacks/ReferencesAssetDownloadManager.swift`
- `ios/ClassicsViewer/Views/ReferencesDownloadView.swift`
- `ios/ClassicsViewer/Views/ReferencesListView.swift`
- `ios/ClassicsViewer/Views/PDFReaderView.swift`
- `ios/ClassicsViewer/Resources/OnDemand/References/` (PDFs + manifest, populated by the same `cp` step as Android)

**iOS — modified:**
- `ios/ClassicsViewer/AssetPacks/ODRManager.swift` — add `.references` case to `AssetTag`
- `ios/ClassicsViewer/AssetPacks/AssetPackInfo` (or wherever sizes live) — add `references` entry
- `ios/ClassicsViewer/Utilities/UserDefaults+Extensions.swift` — add reference-state getters/setters
- Top-level menu/nav view — surface "References" / "Download References (~75 MB)" conditionally

**Unmodified (verified):** no Room entities/DAOs/schema files; no iOS entitlements or `project.yml` capability changes. Backwards-compat invariants in `CLAUDE.md` and memories `project_ios_odr_asset_tags`, `feedback_get_approval_project_config`, `feedback_never_compile_ios` all hold.

## 13. Testing checklist

**Android:**
- [ ] Debug APK: PDFs read from `app/src/debug/assets/references/`; "References" menu item visible.
- [ ] Release AAB built via `bundleRelease`, installed with `bundletool` *without* the pack: menu shows "Download References (~75 MB)", not "References".
- [ ] Same AAB after fetching the pack: menu shows "References" only.
- [ ] Open Smyth → swipe → pinch-zoom in → pan → close app → reopen Smyth → resumes on same page, same zoom, same pan offset.
- [ ] Open Allen & Greenough independently — its state is tracked separately from Smyth's.
- [ ] Pinch-zoom: zooms smoothly between 1.0× and 6.0×, clamped at the bounds.
- [ ] "Go to page" with valid page jumps; with out-of-range page shows inline error and does not move.
- [ ] Rotate device while reading: stays on the same page, scroll offset clamps to new bounds if needed, no crash.
- [ ] App upgrade from 0.8.125 → this build: existing perseus DB and user DB still open (schema validation passes, no Room version bump).
- [ ] `adb shell pm clear` then reinstall: app starts cleanly, "Download References" entry shown (pack not installed).

**iOS:**
- [ ] Fresh install: "Download References" entry visible; tap → ODR download succeeds; entry switches to "References".
- [ ] PDFKit viewer: pinch-zoom, double-tap zoom, "Go to page" all work.
- [ ] Per-PDF state (page + zoom + scroll offset) persists across app relaunches via UserDefaults.
- [ ] `entryId` values logged on iOS match those logged on Android for the same PDFs.
- [ ] AppStore archive size: base app does **not** include the PDFs (verify via `unzip -l` of the .ipa or Xcode "Show Build Folder"). If the PDFs end up in the base, the `references` ODR tag has dropped from `project.pbxproj` — see memory `project_ios_odr_asset_tags`.
