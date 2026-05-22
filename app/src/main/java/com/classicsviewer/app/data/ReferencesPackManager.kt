package com.classicsviewer.app.data

import android.content.Context
import android.util.Log
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.IntentSenderRequest
import com.classicsviewer.app.BuildConfig
import com.google.android.play.core.assetpacks.AssetPackManager
import com.google.android.play.core.assetpacks.AssetPackManagerFactory
import com.google.android.play.core.assetpacks.AssetPackState
import com.google.android.play.core.assetpacks.AssetPackStateUpdateListener
import com.google.android.play.core.assetpacks.model.AssetPackErrorCode
import com.google.android.play.core.assetpacks.model.AssetPackStatus
import java.io.File

/**
 * Facade over Play Asset Delivery for the on-demand "references_pack".
 * Mirrors FullDatabaseDownloadManager but for the ~75 MB References pack.
 *
 * In debug builds, if the pack is not installed but PDFs+manifest exist under
 * app/src/debug/assets/references/, they are copied to cacheDir on first
 * access so the in-app UI works without a Play Store install.
 */
class ReferencesPackManager(private val context: Context) {

    companion object {
        private const val TAG = "ReferencesPackManager"
        const val ASSET_PACK_NAME = "references_pack"
        const val MANIFEST_FILENAME = "references_manifest.json"
        const val DEBUG_ASSET_SUBDIR = "references"
        private const val CACHE_DIR_NAME = "references_pack_cache"
    }

    private val assetPackManager: AssetPackManager = AssetPackManagerFactory.getInstance(context)
    private var stateUpdateListener: AssetPackStateUpdateListener? = null
    private var cachedManifest: ReferencesManifest? = null

    /** True if the references pack is usable (downloaded via Play, or seeded in debug assets). */
    fun isInstalled(): Boolean {
        if (packAssetsPath() != null) return true
        return BuildConfig.DEBUG && hasDebugAssets()
    }

    /** Filesystem directory containing PDFs + manifest. Null if not installed. */
    fun getAssetsPath(): String? {
        packAssetsPath()?.let { return it }
        if (BuildConfig.DEBUG && hasDebugAssets()) {
            return ensureDebugCacheDir().absolutePath
        }
        return null
    }

    /**
     * Resolve a PDF entry to a regular File suitable for ParcelFileDescriptor.
     * Pack files are already on disk; debug builds copy from assets to cacheDir on first use.
     */
    fun getPdfFile(entry: ReferenceEntry): File? {
        val dir = getAssetsPath() ?: return null
        val file = File(dir, entry.filename)
        return if (file.exists()) file else null
    }

    /** Read references_manifest.json from the installed location. Cached in-process. */
    fun loadManifest(): ReferencesManifest? {
        cachedManifest?.let { return it }
        val dir = getAssetsPath() ?: return null
        val file = File(dir, MANIFEST_FILENAME)
        if (!file.exists()) return null
        return try {
            val parsed = ReferencesManifest.parse(file.readText(Charsets.UTF_8))
            cachedManifest = parsed
            parsed
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse manifest at ${file.absolutePath}", e)
            null
        }
    }

    fun startDownload(
        onProgress: (bytesDownloaded: Long, totalBytes: Long, percent: Int) -> Unit,
        onComplete: () -> Unit,
        onError: (errorCode: Int, message: String) -> Unit,
        onRequiresConfirmation: () -> Unit,
    ) {
        stateUpdateListener = AssetPackStateUpdateListener { state ->
            handleStateUpdate(state, onProgress, onComplete, onError, onRequiresConfirmation)
        }
        assetPackManager.registerListener(stateUpdateListener!!)

        assetPackManager.fetch(listOf(ASSET_PACK_NAME))
            .addOnSuccessListener { states ->
                val packState = states.packStates()[ASSET_PACK_NAME]
                if (packState != null) {
                    handleStateUpdate(packState, onProgress, onComplete, onError, onRequiresConfirmation)
                }
            }
            .addOnFailureListener { exception ->
                Log.e(TAG, "Fetch failed", exception)
                onError(-1, exception.message ?: "Download failed")
            }
    }

    fun cancelDownload() {
        assetPackManager.cancel(listOf(ASSET_PACK_NAME))
        unregisterListener()
    }

    fun removeAssetPack() {
        assetPackManager.removePack(ASSET_PACK_NAME)
        cachedManifest = null
    }

    fun showConfirmationDialog(launcher: ActivityResultLauncher<IntentSenderRequest>): Boolean {
        return assetPackManager.showConfirmationDialog(launcher)
    }

    private fun packAssetsPath(): String? {
        val location = assetPackManager.getPackLocation(ASSET_PACK_NAME) ?: return null
        return location.assetsPath()
    }

    private fun handleStateUpdate(
        state: AssetPackState,
        onProgress: (bytesDownloaded: Long, totalBytes: Long, percent: Int) -> Unit,
        onComplete: () -> Unit,
        onError: (errorCode: Int, message: String) -> Unit,
        onRequiresConfirmation: () -> Unit,
    ) {
        when (state.status()) {
            AssetPackStatus.PENDING -> {}
            AssetPackStatus.DOWNLOADING -> {
                val downloaded = state.bytesDownloaded()
                val total = state.totalBytesToDownload()
                val percent = if (total > 0) ((downloaded * 100) / total).toInt() else 0
                onProgress(downloaded, total, percent)
            }
            AssetPackStatus.TRANSFERRING -> {
                onProgress(state.bytesDownloaded(), state.totalBytesToDownload(), 99)
            }
            AssetPackStatus.COMPLETED -> {
                unregisterListener()
                onComplete()
            }
            AssetPackStatus.FAILED -> {
                unregisterListener()
                onError(state.errorCode(), getErrorMessage(state.errorCode()))
            }
            AssetPackStatus.CANCELED -> {
                unregisterListener()
                onError(AssetPackErrorCode.ACCESS_DENIED, "Download was canceled")
            }
            AssetPackStatus.WAITING_FOR_WIFI, AssetPackStatus.REQUIRES_USER_CONFIRMATION -> {
                onRequiresConfirmation()
            }
            AssetPackStatus.NOT_INSTALLED -> {}
            else -> {}
        }
    }

    private fun unregisterListener() {
        stateUpdateListener?.let {
            assetPackManager.unregisterListener(it)
            stateUpdateListener = null
        }
    }

    private fun hasDebugAssets(): Boolean {
        return try {
            context.assets.list(DEBUG_ASSET_SUBDIR)?.any { it == MANIFEST_FILENAME } == true
        } catch (e: Exception) {
            false
        }
    }

    private fun ensureDebugCacheDir(): File {
        val target = File(context.cacheDir, CACHE_DIR_NAME)
        if (!target.exists()) target.mkdirs()
        val names = context.assets.list(DEBUG_ASSET_SUBDIR) ?: emptyArray()
        for (name in names) {
            val outFile = File(target, name)
            if (outFile.exists() && outFile.length() > 0L) continue
            context.assets.open("$DEBUG_ASSET_SUBDIR/$name").use { input ->
                outFile.outputStream().use { output ->
                    input.copyTo(output)
                }
            }
        }
        return target
    }

    private fun getErrorMessage(errorCode: Int): String = when (errorCode) {
        AssetPackErrorCode.NO_ERROR -> "No error"
        AssetPackErrorCode.APP_UNAVAILABLE -> "App unavailable on Play Store"
        AssetPackErrorCode.PACK_UNAVAILABLE -> "Asset pack unavailable"
        AssetPackErrorCode.INVALID_REQUEST -> "Invalid request"
        AssetPackErrorCode.DOWNLOAD_NOT_FOUND -> "Download not found"
        AssetPackErrorCode.API_NOT_AVAILABLE -> "Play Core API not available"
        AssetPackErrorCode.NETWORK_ERROR -> "Network error"
        AssetPackErrorCode.ACCESS_DENIED -> "Access denied"
        AssetPackErrorCode.INSUFFICIENT_STORAGE -> "Insufficient storage"
        AssetPackErrorCode.APP_NOT_OWNED -> "App not owned - install from Play Store"
        AssetPackErrorCode.INTERNAL_ERROR -> "Internal error"
        else -> "Unknown error: $errorCode"
    }
}
