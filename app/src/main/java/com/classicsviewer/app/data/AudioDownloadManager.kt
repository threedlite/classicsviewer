package com.classicsviewer.app.data

import android.content.Context
import android.os.StatFs
import android.util.Log
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.IntentSenderRequest
import com.google.android.play.core.assetpacks.AssetPackManager
import com.google.android.play.core.assetpacks.AssetPackManagerFactory
import com.google.android.play.core.assetpacks.AssetPackState
import com.google.android.play.core.assetpacks.AssetPackStateUpdateListener
import com.google.android.play.core.assetpacks.model.AssetPackStatus
import com.google.android.play.core.assetpacks.model.AssetPackErrorCode
import com.classicsviewer.app.audio.DefaultAudioExtractor
import com.classicsviewer.app.utils.PreferencesManager
import java.io.File

/**
 * Manages on-demand download of the full Homer Iliad audio via Play Asset Delivery.
 */
class AudioDownloadManager(private val context: Context) {

    companion object {
        private const val TAG = "AudioDownloadManager"
        const val ASSET_PACK_NAME = "audio_pack"
        const val AUDIO_ZIP_NAME = "homer_iliad_chamberlain_audio.zip"
        const val REQUIRED_SPACE_BYTES = 2L * 1024 * 1024 * 1024 // 2GB for extraction
        private const val FULL_AUDIO_PACKAGE_ID = -2L // Special ID for full audio (distinct from bundled -1)
        private const val FULL_AUDIO_PACKAGE_NAME = "Homer - Iliad (Chamberlain) [Full]"
        private const val AUDIO_DIR = "audio"
        private const val PACKAGE_DIR = "full_iliad_audio"
    }

    private val assetPackManager: AssetPackManager = AssetPackManagerFactory.getInstance(context)
    private var stateUpdateListener: AssetPackStateUpdateListener? = null
    private val audioExtractor = DefaultAudioExtractor(context)

    /**
     * Check if audio asset pack is already downloaded
     */
    fun isAudioDownloaded(): Boolean {
        val location = assetPackManager.getPackLocation(ASSET_PACK_NAME)
        return location != null && location.assetsPath() != null
    }

    /**
     * Get path to downloaded audio ZIP
     */
    fun getAudioZipPath(): String? {
        val location = assetPackManager.getPackLocation(ASSET_PACK_NAME) ?: return null
        val assetsPath = location.assetsPath() ?: return null
        return "$assetsPath/$AUDIO_ZIP_NAME"
    }

    /**
     * Check if device has enough free space (2GB required for extraction)
     */
    fun hasEnoughFreeSpace(): Boolean {
        val internalPath = context.filesDir
        val stat = StatFs(internalPath.path)
        val availableBytes = stat.availableBytes
        Log.d(TAG, "Available space: ${availableBytes / 1024 / 1024 / 1024}GB, required: ${REQUIRED_SPACE_BYTES / 1024 / 1024 / 1024}GB")
        return availableBytes >= REQUIRED_SPACE_BYTES
    }

    /**
     * Get available free space in GB
     */
    fun getAvailableSpaceGB(): Long {
        val stat = StatFs(context.filesDir.path)
        return stat.availableBytes / 1024 / 1024 / 1024
    }

    /**
     * Start download of audio asset pack
     */
    fun startDownload(
        onProgress: (bytesDownloaded: Long, totalBytes: Long, percent: Int) -> Unit,
        onComplete: () -> Unit,
        onError: (errorCode: Int, message: String) -> Unit,
        onRequiresConfirmation: () -> Unit
    ) {
        stateUpdateListener = AssetPackStateUpdateListener { state ->
            handleStateUpdate(state, onProgress, onComplete, onError, onRequiresConfirmation)
        }

        assetPackManager.registerListener(stateUpdateListener!!)

        assetPackManager.fetch(listOf(ASSET_PACK_NAME))
            .addOnSuccessListener { states ->
                Log.d(TAG, "Fetch initiated successfully")
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

    private fun handleStateUpdate(
        state: AssetPackState,
        onProgress: (bytesDownloaded: Long, totalBytes: Long, percent: Int) -> Unit,
        onComplete: () -> Unit,
        onError: (errorCode: Int, message: String) -> Unit,
        onRequiresConfirmation: () -> Unit
    ) {
        val status = state.status()
        Log.d(TAG, "Asset pack status: $status")

        when (status) {
            AssetPackStatus.PENDING -> {
                Log.d(TAG, "Download pending...")
            }
            AssetPackStatus.DOWNLOADING -> {
                val downloaded = state.bytesDownloaded()
                val total = state.totalBytesToDownload()
                val percent = if (total > 0) ((downloaded * 100) / total).toInt() else 0
                Log.d(TAG, "Downloading: $percent% ($downloaded / $total)")
                onProgress(downloaded, total, percent)
            }
            AssetPackStatus.TRANSFERRING -> {
                Log.d(TAG, "Transferring to storage...")
                onProgress(state.bytesDownloaded(), state.totalBytesToDownload(), 99)
            }
            AssetPackStatus.COMPLETED -> {
                Log.d(TAG, "Download completed!")
                unregisterListener()
                onComplete()
            }
            AssetPackStatus.FAILED -> {
                val errorCode = state.errorCode()
                val errorMessage = getErrorMessage(errorCode)
                Log.e(TAG, "Download failed: $errorCode - $errorMessage")
                unregisterListener()
                onError(errorCode, errorMessage)
            }
            AssetPackStatus.CANCELED -> {
                Log.d(TAG, "Download canceled")
                unregisterListener()
                onError(AssetPackErrorCode.ACCESS_DENIED, "Download was canceled")
            }
            AssetPackStatus.WAITING_FOR_WIFI -> {
                Log.d(TAG, "Waiting for WiFi - requires user confirmation")
                onRequiresConfirmation()
            }
            AssetPackStatus.REQUIRES_USER_CONFIRMATION -> {
                Log.d(TAG, "Requires user confirmation for large download")
                onRequiresConfirmation()
            }
            AssetPackStatus.NOT_INSTALLED -> {
                Log.d(TAG, "Asset pack not installed")
            }
            else -> {
                Log.d(TAG, "Unknown status: $status")
            }
        }
    }

    /**
     * Show confirmation dialog for large downloads or WiFi requirement
     */
    fun showConfirmationDialog(launcher: ActivityResultLauncher<IntentSenderRequest>): Boolean {
        return assetPackManager.showConfirmationDialog(launcher)
    }

    /**
     * Cancel ongoing download
     */
    fun cancelDownload() {
        assetPackManager.cancel(listOf(ASSET_PACK_NAME))
        unregisterListener()
    }

    /**
     * Remove downloaded asset pack
     */
    fun removeAssetPack() {
        assetPackManager.removePack(ASSET_PACK_NAME)
    }

    private fun unregisterListener() {
        stateUpdateListener?.let {
            assetPackManager.unregisterListener(it)
            stateUpdateListener = null
        }
    }

    private fun getErrorMessage(errorCode: Int): String {
        return when (errorCode) {
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

    /**
     * Extract downloaded audio to app's files directory and register in audio database.
     * Delegates to DefaultAudioExtractor for the actual extraction and registration.
     */
    suspend fun extractAudio(
        progressCallback: ((Float) -> Unit)? = null
    ): Boolean {
        val zipPath = getAudioZipPath()
        if (zipPath == null) {
            Log.e(TAG, "Audio ZIP path is null")
            return false
        }

        val zipFile = File(zipPath)
        if (!zipFile.exists()) {
            Log.e(TAG, "Audio ZIP does not exist at: $zipPath")
            return false
        }

        Log.d(TAG, "Extracting audio from: $zipPath (${zipFile.length() / 1024 / 1024}MB)")

        // Use shared extraction logic from DefaultAudioExtractor
        val success = audioExtractor.extractAudioFromZip(
            zipFile = zipFile,
            packageId = FULL_AUDIO_PACKAGE_ID,
            packageName = FULL_AUDIO_PACKAGE_NAME,
            packageDirName = PACKAGE_DIR,
            progressCallback = progressCallback
        )

        if (success) {
            PreferencesManager.setFullAudioInstalled(context, true)
        }

        return success
    }

    /**
     * Check if full audio is installed and extracted
     */
    fun isFullAudioInstalled(): Boolean {
        return PreferencesManager.getFullAudioInstalled(context)
    }
}
