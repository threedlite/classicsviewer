package com.classicsviewer.app.data

import android.content.Context
import android.util.Log
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.IntentSenderRequest
import com.classicsviewer.app.BuildConfig
import com.classicsviewer.app.utils.PreferencesManager
import com.google.android.play.core.assetpacks.AssetPackManager
import com.google.android.play.core.assetpacks.AssetPackManagerFactory
import com.google.android.play.core.assetpacks.AssetPackState
import com.google.android.play.core.assetpacks.AssetPackStateUpdateListener
import com.google.android.play.core.assetpacks.model.AssetPackErrorCode
import com.google.android.play.core.assetpacks.model.AssetPackStatus
import org.json.JSONObject
import java.io.File

/**
 * Play Asset Delivery facade for the extended-delta parts and the install
 * state the app keeps about them.
 *
 * Design: ANDROID_EXTENDED_LANGUAGE_PACKS_PROPOSAL.md, sections 5 and 8.
 *
 * - The part pack names come from the build (`BuildConfig.EXTENDED_PART_PACKS`,
 *   generated from the same list that puts the modules in the bundle), so the
 *   app and the bundle cannot disagree about which parts exist.
 * - Each pack holds `<pack>.db.zip` and a sidecar `<pack>.manifest.json`;
 *   the full pack holds `full.manifest.json` beside its zip. The sidecars are
 *   only for display and for the "update available" check; the installer
 *   trusts the manifest inside the zip.
 * - In debug builds, which cannot carry asset packs, a part is read from
 *   `getExternalFilesDir("packs")` if its zip has been pushed there.
 * - State lives in PreferencesManager as one JSON object, replaced whole.
 */
class ExtendedPartsManager(private val context: Context) {

    companion object {
        private const val TAG = "ExtendedParts"
        const val FULL_PACK_NAME = FullDatabaseDownloadManager.ASSET_PACK_NAME
        const val DEBUG_PACKS_DIR = "packs"
        const val STATE_ABSENT = "absent"
        const val STATE_MERGING = "merging"
        const val STATE_INSTALLED = "installed"

        val PART_PACKS: List<String> =
            BuildConfig.EXTENDED_PART_PACKS.split(',').map { it.trim() }.filter { it.isNotEmpty() }

        val enabled: Boolean get() = BuildConfig.EXTENDED_PARTS_ENABLED && PART_PACKS.isNotEmpty()
    }

    private val assetPackManager: AssetPackManager = AssetPackManagerFactory.getInstance(context)
    private var stateUpdateListener: AssetPackStateUpdateListener? = null

    // ---- locating packs ------------------------------------------------------

    /** Directory holding the pack's files, or null if the pack is not on the device. */
    fun packDir(pack: String): File? {
        assetPackManager.getPackLocation(pack)?.assetsPath()?.let { return File(it) }
        if (BuildConfig.DEBUG) {
            val dir = context.getExternalFilesDir(DEBUG_PACKS_DIR) ?: return null
            if (File(dir, "$pack.db.zip").exists() || File(dir, "full.manifest.json").exists()) return dir
        }
        return null
    }

    fun partZip(pack: String): File? =
        packDir(pack)?.let { File(it, "$pack.db.zip") }?.takeIf { it.exists() }

    fun isDownloaded(pack: String): Boolean = partZip(pack) != null

    /** The sidecar manifest beside a part's zip, for display before download. */
    fun partSidecar(pack: String): JSONObject? =
        packDir(pack)?.let { File(it, "$pack.manifest.json") }?.takeIf { it.exists() }
            ?.let { runCatching { JSONObject(it.readText()) }.getOrNull() }

    /** The full pack's sidecar `build_time`, i.e. the data release Play currently holds. */
    fun fullPackBuildTime(): String? =
        packDir(FULL_PACK_NAME)?.let { File(it, "full.manifest.json") }?.takeIf { it.exists() }
            ?.let { runCatching { JSONObject(it.readText()).optString("build_time", null) }.getOrNull() }

    // ---- downloads ----------------------------------------------------------

    fun startDownload(
        pack: String,
        onProgress: (bytesDownloaded: Long, totalBytes: Long, percent: Int) -> Unit,
        onComplete: () -> Unit,
        onError: (errorCode: Int, message: String) -> Unit,
        onRequiresConfirmation: () -> Unit
    ) {
        if (BuildConfig.DEBUG && partZip(pack) != null && assetPackManager.getPackLocation(pack) == null) {
            onComplete()  // debug fallback: the zip was pushed by hand
            return
        }
        stateUpdateListener = AssetPackStateUpdateListener { state ->
            if (state.name() == pack) handleStateUpdate(state, onProgress, onComplete, onError, onRequiresConfirmation)
        }
        assetPackManager.registerListener(stateUpdateListener!!)
        assetPackManager.fetch(listOf(pack))
            .addOnSuccessListener { states ->
                states.packStates()[pack]?.let {
                    handleStateUpdate(it, onProgress, onComplete, onError, onRequiresConfirmation)
                }
            }
            .addOnFailureListener { e ->
                Log.e(TAG, "fetch($pack) failed", e)
                unregisterListener()
                onError(-1, e.message ?: "Download failed")
            }
    }

    private fun handleStateUpdate(
        state: AssetPackState,
        onProgress: (Long, Long, Int) -> Unit,
        onComplete: () -> Unit,
        onError: (Int, String) -> Unit,
        onRequiresConfirmation: () -> Unit
    ) {
        when (state.status()) {
            AssetPackStatus.DOWNLOADING -> {
                val done = state.bytesDownloaded()
                val total = state.totalBytesToDownload()
                onProgress(done, total, if (total > 0) ((done * 100) / total).toInt() else 0)
            }
            AssetPackStatus.TRANSFERRING -> onProgress(state.bytesDownloaded(), state.totalBytesToDownload(), 99)
            AssetPackStatus.COMPLETED -> { unregisterListener(); onComplete() }
            AssetPackStatus.FAILED -> { unregisterListener(); onError(state.errorCode(), errorMessage(state.errorCode())) }
            AssetPackStatus.CANCELED -> { unregisterListener(); onError(AssetPackErrorCode.ACCESS_DENIED, "Download was canceled") }
            AssetPackStatus.WAITING_FOR_WIFI, AssetPackStatus.REQUIRES_USER_CONFIRMATION -> onRequiresConfirmation()
            else -> Log.d(TAG, "${state.name()}: status ${state.status()}")
        }
    }

    fun showConfirmationDialog(launcher: ActivityResultLauncher<IntentSenderRequest>): Boolean =
        assetPackManager.showConfirmationDialog(launcher)

    fun cancelDownload(pack: String) {
        assetPackManager.cancel(listOf(pack))
        unregisterListener()
    }

    /** Decided: a part is deleted from the device as soon as it is merged. */
    fun removePack(pack: String) {
        if (assetPackManager.getPackLocation(pack) != null) assetPackManager.removePack(pack)
    }

    private fun unregisterListener() {
        stateUpdateListener?.let { assetPackManager.unregisterListener(it) }
        stateUpdateListener = null
    }

    private fun errorMessage(code: Int): String = when (code) {
        AssetPackErrorCode.NETWORK_ERROR -> "Network error"
        AssetPackErrorCode.INSUFFICIENT_STORAGE -> "Insufficient storage"
        AssetPackErrorCode.APP_NOT_OWNED -> "App not owned - install from Play Store"
        AssetPackErrorCode.PACK_UNAVAILABLE -> "Asset pack unavailable"
        AssetPackErrorCode.API_NOT_AVAILABLE -> "Play Core API not available"
        AssetPackErrorCode.ACCESS_DENIED -> "Access denied"
        else -> "Error $code"
    }

    // ---- install state (PreferencesManager, one JSON object) ------------------

    private fun stateObject(): JSONObject =
        runCatching { JSONObject(PreferencesManager.getExtendedPackState(context)) }.getOrDefault(JSONObject())

    fun partState(pack: String): String =
        stateObject().optJSONObject(pack)?.optString("state", STATE_ABSENT) ?: STATE_ABSENT

    fun setPartState(pack: String, state: String, buildTime: String?) {
        val obj = stateObject()
        obj.put(pack, JSONObject().put("state", state).put("build_time", buildTime ?: "")
            .put("at", System.currentTimeMillis()))
        PreferencesManager.setExtendedPackState(context, obj.toString())
    }

    fun anyMerging(): Boolean {
        val obj = stateObject()
        return obj.keys().asSequence().any { obj.optJSONObject(it)?.optString("state") == STATE_MERGING }
    }

    fun installedParts(): List<String> = PART_PACKS.filter { partState(it) == STATE_INSTALLED }

    fun allInstalled(): Boolean = PART_PACKS.isNotEmpty() && PART_PACKS.all { partState(it) == STATE_INSTALLED }

    fun clearState() = PreferencesManager.setExtendedPackState(context, "{}")
}
