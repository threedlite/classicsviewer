package com.classicsviewer.app.data

import android.content.Context
import android.os.StatFs
import android.util.Log
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.IntentSenderRequest
import com.google.android.play.core.assetpacks.AssetPackLocation
import com.google.android.play.core.assetpacks.AssetPackManager
import com.google.android.play.core.assetpacks.AssetPackManagerFactory
import com.google.android.play.core.assetpacks.AssetPackState
import com.google.android.play.core.assetpacks.AssetPackStateUpdateListener
import com.google.android.play.core.assetpacks.model.AssetPackStatus
import com.google.android.play.core.assetpacks.model.AssetPackErrorCode
import com.classicsviewer.app.utils.PreferencesManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.util.zip.ZipInputStream

/**
 * Manages on-demand download of the full database via Play Asset Delivery.
 *
 * Database priority hierarchy:
 * 1. External database (user-imported) - highest priority
 * 2. Full database (on-demand download) - if downloaded and enabled
 * 3. Bundled database (sample) - default fallback
 */
class FullDatabaseDownloadManager(private val context: Context) {

    companion object {
        private const val TAG = "FullDatabaseDownload"
        const val ASSET_PACK_NAME = "full_database_pack"
        const val FULL_DB_ZIP_NAME = "perseus_texts_full.db.zip"
        const val DB_NAME = "perseus_texts.db"  // Same name as bundled - replaces it
        const val REQUIRED_SPACE_BYTES = 25L * 1024 * 1024 * 1024 // 25GB
    }

    private val assetPackManager: AssetPackManager = AssetPackManagerFactory.getInstance(context)
    private var stateUpdateListener: AssetPackStateUpdateListener? = null

    /**
     * Check if full database asset pack is already downloaded
     */
    fun isFullDatabaseDownloaded(): Boolean {
        val location = assetPackManager.getPackLocation(ASSET_PACK_NAME)
        return location != null && location.assetsPath() != null
    }

    /**
     * Get path to downloaded full database ZIP
     */
    fun getFullDatabaseZipPath(): String? {
        val location = assetPackManager.getPackLocation(ASSET_PACK_NAME) ?: return null
        val assetsPath = location.assetsPath() ?: return null
        return "$assetsPath/$FULL_DB_ZIP_NAME"
    }

    /**
     * Check if device has enough free space (25GB required)
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
     * Start download of full database asset pack
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

        // Fetch the asset pack
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
     * Extract downloaded full database to app's database directory
     */
    suspend fun extractFullDatabase(
        progressCallback: ((Float) -> Unit)? = null
    ): Boolean = withContext(Dispatchers.IO) {
        try {
            val zipPath = getFullDatabaseZipPath()
            if (zipPath == null) {
                Log.e(TAG, "Full database ZIP path is null")
                return@withContext false
            }

            val zipFile = File(zipPath)
            if (!zipFile.exists()) {
                Log.e(TAG, "Full database ZIP does not exist at: $zipPath")
                return@withContext false
            }

            Log.d(TAG, "Extracting full database from: $zipPath (${zipFile.length() / 1024 / 1024}MB)")

            val targetDb = context.getDatabasePath(DB_NAME)
            targetDb.parentFile?.mkdirs()

            // Delete existing file if present
            if (targetDb.exists()) {
                targetDb.delete()
            }

            zipFile.inputStream().buffered(8 * 1024).use { fileInput ->
                ZipInputStream(fileInput).use { zipInput ->
                    val entry = zipInput.nextEntry
                    if (entry != null) {
                        val totalBytes = entry.size
                        var bytesCopied = 0L

                        targetDb.outputStream().buffered(1024 * 1024).use { output ->
                            val buffer = ByteArray(1024 * 1024) // 1MB buffer
                            var bytesRead: Int

                            while (zipInput.read(buffer).also { bytesRead = it } != -1) {
                                output.write(buffer, 0, bytesRead)
                                bytesCopied += bytesRead
                                if (totalBytes > 0) {
                                    progressCallback?.invoke(bytesCopied.toFloat() / totalBytes.toFloat())
                                }
                            }
                        }
                        Log.d(TAG, "Full database extracted: ${targetDb.length() / 1024 / 1024}MB to ${targetDb.absolutePath}")
                    } else {
                        Log.e(TAG, "No valid database entry found in ZIP")
                        return@withContext false
                    }
                }
            }

            true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to extract full database", e)
            false
        }
    }

    /**
     * Check if full database is currently active (extracted and enabled)
     * Must also verify no external database is overriding it
     */
    fun isFullDatabaseActive(): Boolean {
        val hasExternalDb = PreferencesManager.getExternalDatabaseUri(context) != null
        return !hasExternalDb && PreferencesManager.getUseFullDatabase(context)
    }

    /**
     * Check if an external database is currently active
     */
    fun isExternalDatabaseActive(): Boolean {
        return PreferencesManager.getExternalDatabaseUri(context) != null
    }
}

