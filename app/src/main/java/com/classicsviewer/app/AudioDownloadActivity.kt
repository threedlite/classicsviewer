package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import android.view.MenuItem
import android.view.View
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.IntentSenderRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.lifecycleScope
import com.classicsviewer.app.data.AudioDownloadManager
import com.classicsviewer.app.databinding.ActivityAudioDownloadBinding
import com.classicsviewer.app.utils.PreferencesManager
import kotlinx.coroutines.launch

/**
 * Activity for downloading and managing the full Homer Iliad audio via Play Asset Delivery.
 * Shows download progress and handles extraction to app storage.
 */
class AudioDownloadActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAudioDownloadBinding
    private lateinit var downloadManager: AudioDownloadManager
    private var isDownloading = false
    private var confirmationDialogShown = false

    private val confirmationLauncher: ActivityResultLauncher<IntentSenderRequest> =
        registerForActivityResult(ActivityResultContracts.StartIntentSenderForResult()) { result ->
            if (result.resultCode == RESULT_OK) {
                confirmationDialogShown = false
            } else {
                Toast.makeText(this, "Download requires confirmation to proceed", Toast.LENGTH_LONG).show()
                finish()
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        binding = ActivityAudioDownloadBinding.inflate(layoutInflater)
        setContentView(binding.root)

        supportActionBar?.title = "Download Iliad Full Audio"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        ViewCompat.setOnApplyWindowInsetsListener(binding.root) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }

        applyColorInversion()

        downloadManager = AudioDownloadManager(this)

        when {
            downloadManager.isFullAudioInstalled() -> showAlreadyInstalled()
            downloadManager.isAudioDownloaded() -> showReadyToExtract()
            else -> setupDownloadUI()
        }

        binding.btnStartDownload.setOnClickListener {
            startDownload()
        }

        binding.btnCancel.setOnClickListener {
            if (isDownloading) {
                downloadManager.cancelDownload()
            }
            finish()
        }

        binding.btnExtract.setOnClickListener {
            extractAudio()
        }
    }

    private fun applyColorInversion() {
        val inverted = PreferencesManager.getInvertColors(this)
        val textColor = if (inverted) 0xFF000000.toInt() else 0xFFFFFFFF.toInt()
        val bgColor = if (inverted) 0xFFFFFFFF.toInt() else 0xFF000000.toInt()

        binding.root.setBackgroundColor(bgColor)
        binding.tvTitle.setTextColor(textColor)
        binding.tvStatus.setTextColor(textColor)
        binding.tvProgress.setTextColor(textColor)
        binding.tvSpaceWarning.setTextColor(textColor)
    }

    private fun setupDownloadUI() {
        val availableGB = downloadManager.getAvailableSpaceGB()
        val hasSpace = downloadManager.hasEnoughFreeSpace()

        binding.tvSpaceWarning.text = "Available space: ${availableGB}GB\nRequired: 2GB"
        binding.tvSpaceWarning.visibility = View.VISIBLE

        if (!hasSpace) {
            binding.tvStatus.text = "Insufficient storage space.\n\nPlease free up space before downloading."
            binding.btnStartDownload.isEnabled = false
            binding.tvSpaceWarning.setTextColor(0xFFFF6B6B.toInt())
        } else {
            binding.tvStatus.text = "Ready to download full audio.\n\nThe full audio contains Stanley Lombardo's reading of Homer's Iliad (~975MB)."
            binding.btnStartDownload.isEnabled = true
        }

        binding.btnStartDownload.visibility = View.VISIBLE
        binding.btnCancel.visibility = View.VISIBLE
        binding.btnExtract.visibility = View.GONE
        binding.downloadProgress.visibility = View.GONE
    }

    private fun showReadyToExtract() {
        binding.tvStatus.text = "Full audio downloaded.\n\nTap 'Extract' to prepare for use."
        binding.btnStartDownload.visibility = View.GONE
        binding.btnExtract.visibility = View.VISIBLE
        binding.btnCancel.text = "Close"
        binding.tvSpaceWarning.visibility = View.GONE
    }

    private fun showAlreadyInstalled() {
        binding.tvStatus.text = "Full audio is installed.\n\nYou can listen to Stanley Lombardo's complete reading of Homer's Iliad."
        binding.btnStartDownload.visibility = View.GONE
        binding.btnExtract.visibility = View.GONE
        binding.btnCancel.text = "Close"
        binding.tvSpaceWarning.visibility = View.GONE
    }

    private fun startDownload() {
        isDownloading = true
        binding.btnStartDownload.isEnabled = false
        binding.downloadProgress.visibility = View.VISIBLE
        binding.downloadProgress.progress = 0
        binding.tvStatus.text = "Starting download..."
        binding.tvProgress.text = "0%"

        downloadManager.startDownload(
            onProgress = { bytesDownloaded, totalBytes, percent ->
                runOnUiThread {
                    binding.downloadProgress.progress = percent
                    val downloadedMB = bytesDownloaded / 1024 / 1024
                    val totalMB = totalBytes / 1024 / 1024
                    binding.tvProgress.text = "$percent% (${downloadedMB}MB / ${totalMB}MB)"
                    binding.tvStatus.text = "Downloading full audio..."
                }
            },
            onComplete = {
                runOnUiThread {
                    isDownloading = false
                    binding.tvStatus.text = "Download complete!"
                    binding.downloadProgress.progress = 100
                    binding.tvProgress.text = "100%"
                    binding.btnExtract.visibility = View.VISIBLE
                    binding.btnStartDownload.visibility = View.GONE
                    Toast.makeText(this, "Download complete! Tap 'Extract' to continue.", Toast.LENGTH_LONG).show()
                }
            },
            onError = { errorCode, message ->
                runOnUiThread {
                    isDownloading = false
                    binding.tvStatus.text = "Download failed:\n$message"
                    binding.btnStartDownload.isEnabled = true
                    binding.btnStartDownload.visibility = View.VISIBLE
                    Toast.makeText(this, "Error: $message", Toast.LENGTH_LONG).show()
                }
            },
            onRequiresConfirmation = {
                runOnUiThread {
                    if (!confirmationDialogShown) {
                        confirmationDialogShown = true
                        downloadManager.showConfirmationDialog(confirmationLauncher)
                    }
                }
            }
        )
    }

    private fun extractAudio() {
        binding.tvStatus.text = "Extracting audio...\n\nThis may take a few minutes."
        binding.btnExtract.isEnabled = false
        binding.downloadProgress.progress = 0
        binding.downloadProgress.visibility = View.VISIBLE
        binding.tvProgress.text = "Preparing: 0%"

        lifecycleScope.launch {
            val success = downloadManager.extractAudio { progress ->
                runOnUiThread {
                    val percent = (progress * 100).toInt()
                    binding.downloadProgress.progress = percent
                    binding.tvProgress.text = "Extracting: $percent%"
                }
            }

            if (success) {
                runOnUiThread {
                    binding.tvStatus.text = "Full audio installed!"
                    binding.downloadProgress.progress = 100
                    binding.tvProgress.text = "100%"

                    AlertDialog.Builder(this@AudioDownloadActivity)
                        .setTitle("Audio Installed")
                        .setMessage("The full Homer Iliad audio has been installed. You can now listen to all 24 books.")
                        .setPositiveButton("OK") { _, _ ->
                            finish()
                        }
                        .setCancelable(false)
                        .show()
                }
            } else {
                runOnUiThread {
                    binding.tvStatus.text = "Extraction failed.\n\nPlease try again."
                    binding.btnExtract.isEnabled = true
                    Toast.makeText(this@AudioDownloadActivity, "Failed to extract audio", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            android.R.id.home -> {
                handleBack()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    private fun handleBack() {
        if (isDownloading) {
            AlertDialog.Builder(this)
                .setTitle("Cancel Download?")
                .setMessage("A download is in progress. Are you sure you want to cancel?")
                .setPositiveButton("Yes") { _, _ ->
                    downloadManager.cancelDownload()
                    finish()
                }
                .setNegativeButton("No", null)
                .show()
        } else {
            finish()
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        handleBack()
    }
}
