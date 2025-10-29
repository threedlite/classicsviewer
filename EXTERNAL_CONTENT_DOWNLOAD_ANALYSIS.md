# External Content Download Analysis
Due to 4GB Play Store total cumulative size limit, files have to be hosted externally.
https://developer.android.com/guide/app-bundle/faq#what_are_google_play_app_size_limits_when_using_aabs

## Proposed Feature

Add internal config file with external download links (example):
- `extended_db_link`: https://www.patreon.com/file?h=141298606&m=555498325
- `chamberlain_iliad_audio_link`: https://www.patreon.com/file?h=141299909&m=548857457

Add "Manage Expansion Data" option under "Manage Languages" in UI to download these files to the Downloads folder.

## Technical Assessment

### What Works
✅ Config file with download links - straightforward implementation
✅ UI option under settings - easy to add
✅ Patreon file hosting - works for direct downloads
✅ Download large files to device - Android supports this

### Critical Considerations

#### 1. Android Permissions (Breaking Change)
**Current State**: App requires NO permissions (stated in CLAUDE.md: "100% local operation on phone; no internet access or other android permissions are required")

**New Requirement**:
```xml
<uses-permission android:name="android.permission.INTERNET" />
```

**Impact**: This changes the app's privacy/security model - needs to be communicated to users

#### Downloads Folder Access
- Android 10+ (API 29+): Use MediaStore or app-specific directory without additional permission
- Downloads folder is accessible for writing
- **Post-download processing needed**:
  - Must move/extract from Downloads to app's database directory (`/data/data/com.classicsviewer.app/databases/`)

#### File Sizes and User Warnings
- **Extended DB compressed**: 2.3GB download
- **Extended DB uncompressed**: 10GB
- **Audio files**: Varies
- **Required**: WiFi/data usage warnings
- **Required**: Download progress indication

#### Post-Download Processing Requirements

**Extended Database:**
1. Download 2.3GB ZIP to Downloads folder
2. Extract ZIP → 10GB uncompressed database
3. Requires **12.3GB+ temporary disk space** (both ZIP and extracted DB simultaneously)
4. Copy/move extracted DB to `/data/data/.../databases/perseus_texts_extended.db`
5. Delete temporary files (ZIP + extraction folder)
6. **Total time estimate**: Several minutes on typical device


#### Disk Space Requirements

**Pre-download checks needed**:
- Extended DB: Minimum 15GB free space recommended
  - 2.3GB download
  - 10GB extracted
  - 2-3GB safety buffer
- Should warn/block download if insufficient space

**Implementation needs**:
- Use `DownloadManager` API or modern WorkManager approach
- Handle download failures (network interruption, etc.)
- Retry logic
- Background download support
- Notification while downloading
- Handle app closure during download

#### Database Integrity Verification

**After download**:
- Verify ZIP integrity (corrupted downloads)
- Verify extracted database is valid SQLite
- Verify schema matches app expectations
- Fallback to previous database if verification fails


### Disk Space Policy
- Should app check for 15GB+ free space before allowing download?
- Should it provide detailed space requirements in UI?
- Block or warn users with insufficient space?

### Error Handling
What happens if:
- Download fails partway?
- Extraction fails (corrupt ZIP)?
- Not enough space during extraction?
- Database doesn't match expected schema?

## Hosting Platform Analysis: Zenodo vs Patreon

### Zenodo (Recommended)

**Perfect for This Use Case**:
- **Academic/Research Focus**: CERN-backed repository designed for scholarly data (classical texts fit perfectly)
- **Free Hosting**: No cost for academic/educational content
- **Large File Support**: Up to 50GB per dataset (2.3GB extended DB is no problem)
- **No Account Required**: Users can download without signing up
- **Stable Direct Links**: Permanent URLs that won't break
- **Unlimited Bandwidth**: No download restrictions or throttling

**Technical Benefits**:
- **DOI Assignment**: Citeable, permanent identifier for database versions
- **Versioning Built-in**: Can update database and maintain version history
- **API Access**: Could potentially integrate programmatic downloads
- **Long-term Preservation**: Designed for 20+ year data availability
- **Metadata Support**: Can document database contents, versions, etc.

**Practical Benefits**:
- **Professional**: Looks more legitimate than Patreon for educational resources
- **No Monetization Confusion**: Zenodo is clearly for open data, not paid content
- **Better Reliability**: Designed for large scientific data, not creator support
- **Community Norms**: Zenodo is standard for open educational/research datasets

### Patreon (Not Recommended)

**Disadvantages**:
- **Not Designed for File Hosting**: It's a creator support platform
- **May Require Account**: Depending on settings, users might need to sign up
- **Link Stability**: Links can change, may be tied to post/membership status
- **Wrong Context**: Suggests monetization rather than open educational resource
- **Less Professional**: For an academic classical texts app

### Recommendation
**Use Zenodo** for:
- Extended database (2.3GB compressed)
- Audio files (Homer readings, etc.)
- Future content expansions

This aligns better with the app's educational mission and the open-source nature of Perseus/First1K texts.
