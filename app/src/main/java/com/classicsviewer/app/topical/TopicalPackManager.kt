package com.classicsviewer.app.topical

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
 * Facade over Play Asset Delivery for the on-demand "topical_pack" (Greek +
 * Latin topical-link DBs). Mirrors [com.classicsviewer.app.data.ReferencesPackManager].
 *
 * In debug builds, if the pack is not installed but the per-language zips exist
 * under `app/src/debug/assets/topical/`, they are copied to cacheDir on first
 * access so the in-app feature works without a Play Store install.
 */
class TopicalPackManager(private val context: Context) {

    companion object {
        private const val TAG = "TopicalPackManager"
        const val ASSET_PACK_NAME = "topical_pack"
        const val DEBUG_ASSET_SUBDIR = "topical"
        private const val CACHE_DIR_NAME = "topical_pack_cache"
        // The file names the pack is expected to contain. Used by the debug
        // fallback to know what to copy out of assets/topical/.
        val PACK_FILES = listOf("topical_greek.db.zip", "topical_latin.db.zip")
    }

    private val assetPackManager: AssetPackManager =
        AssetPackManagerFactory.getInstance(context)
    private var stateUpdateListener: AssetPackStateUpdateListener? = null

    /** True if the topical pack is usable (installed via Play, or seeded in debug assets). */
    fun isInstalled(): Boolean {
        if (packAssetsPath() != null) return true
        return BuildConfig.DEBUG && hasDebugAssets()
    }

    /** Side-effect-free check for a specific per-language pack zip. Does NOT
     *  trigger the debug-cache copy (which moves ~500 MB of zips out of APK
     *  assets). Used by icon-visibility gating that must return fast. */
    fun hasPackZip(stem: String): Boolean {
        val zipName = "$stem.db.zip"
        // Release: Play asset pack location.
        packAssetsPath()?.let { return File(it, zipName).exists() }
        // Debug: check bundled APK assets directly via AssetManager (no copy).
        if (BuildConfig.DEBUG) {
            return try {
                val files = context.assets.list(DEBUG_ASSET_SUBDIR) ?: return false
                zipName in files
            } catch (e: Exception) {
                false
            }
        }
        return false
    }

    /**
     * Filesystem directory containing the per-language `topical_<lang>.db.zip`
     * files. Null if not installed. For release builds this is the pack's own
     * assets dir; for debug it is a cache dir seeded from the debug assets.
     */
    fun getAssetsPath(): String? {
        packAssetsPath()?.let { return it }
        if (BuildConfig.DEBUG && hasDebugAssets()) {
            return ensureDebugCacheDir().absolutePath
        }
        return null
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
                    handleStateUpdate(packState, onProgress, onComplete, onError,
                        onRequiresConfirmation)
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
            AssetPackStatus.WAITING_FOR_WIFI,
            AssetPackStatus.REQUIRES_USER_CONFIRMATION -> {
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
            val files = context.assets.list(DEBUG_ASSET_SUBDIR) ?: return false
            // any of the expected pack files present is enough
            PACK_FILES.any { it in files }
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
            try {
                context.assets.open("$DEBUG_ASSET_SUBDIR/$name").use { input ->
                    outFile.outputStream().use { output -> input.copyTo(output) }
                }
            } catch (e: Exception) {
                Log.w(TAG, "Failed to seed $name from debug assets", e)
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
        AssetPackErrorCode.APP_NOT_OWNED -> "App not owned — install from Play Store"
        AssetPackErrorCode.INTERNAL_ERROR -> "Internal error"
        else -> "Unknown error: $errorCode"
    }
}
