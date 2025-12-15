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
import com.classicsviewer.app.data.FullDatabaseDownloadManager
import com.classicsviewer.app.databinding.ActivityFullDatabaseDownloadBinding
import com.classicsviewer.app.utils.PreferencesManager
import com.classicsviewer.app.database.PerseusDatabase
import kotlinx.coroutines.launch

/**
 * Activity for downloading and managing the full database via Play Asset Delivery.
 * Shows download progress and handles extraction to app storage.
 */
class FullDatabaseDownloadActivity : AppCompatActivity() {

    private lateinit var binding: ActivityFullDatabaseDownloadBinding
    private lateinit var downloadManager: FullDatabaseDownloadManager
    private var isDownloading = false
    private var confirmationDialogShown = false

    private val confirmationLauncher: ActivityResultLauncher<IntentSenderRequest> =
        registerForActivityResult(ActivityResultContracts.StartIntentSenderForResult()) { result ->
            if (result.resultCode == RESULT_OK) {
                // User accepted, download will continue
                confirmationDialogShown = false
            } else {
                // User declined
                Toast.makeText(this, "Download requires confirmation to proceed", Toast.LENGTH_LONG).show()
                finish()
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        binding = ActivityFullDatabaseDownloadBinding.inflate(layoutInflater)
        setContentView(binding.root)

        supportActionBar?.title = "Download Full Database"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        ViewCompat.setOnApplyWindowInsetsListener(binding.root) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }

        applyColorInversion()

        downloadManager = FullDatabaseDownloadManager(this)

        // Check current state and show appropriate UI
        when {
            downloadManager.isFullDatabaseActive() -> showAlreadyActive()
            downloadManager.isFullDatabaseDownloaded() -> showReadyToExtract()
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
            extractDatabase()
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

        binding.tvSpaceWarning.text = "Available space: ${availableGB}GB\nRequired: 25GB"
        binding.tvSpaceWarning.visibility = View.VISIBLE

        if (!hasSpace) {
            binding.tvStatus.text = "Insufficient storage space.\n\nPlease free up space before downloading."
            binding.btnStartDownload.isEnabled = false
            binding.tvSpaceWarning.setTextColor(0xFFFF6B6B.toInt()) // Red warning
        } else {
            binding.tvStatus.text = "Ready to download full database.\n\nThe full database contains all Greek and Latin authors from Perseus Digital Library."
            binding.btnStartDownload.isEnabled = true
        }

        binding.btnStartDownload.visibility = View.VISIBLE
        binding.btnCancel.visibility = View.VISIBLE
        binding.btnExtract.visibility = View.GONE
        binding.downloadProgress.visibility = View.GONE
    }

    private fun showReadyToExtract() {
        binding.tvStatus.text = "Full database downloaded.\n\nTap 'Extract' to prepare for use."
        binding.btnStartDownload.visibility = View.GONE
        binding.btnExtract.visibility = View.VISIBLE
        binding.btnCancel.text = "Close"
        binding.tvSpaceWarning.visibility = View.GONE
    }

    private fun showAlreadyActive() {
        binding.tvStatus.text = "Full database is active.\n\nYou are currently using the full database with all Greek and Latin authors."
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
                    binding.tvStatus.text = "Downloading full database..."
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

    private fun extractDatabase() {
        binding.tvStatus.text = "Replacing database...\n\nThis may take a few minutes."
        binding.btnExtract.isEnabled = false
        binding.downloadProgress.progress = 0
        binding.downloadProgress.visibility = View.VISIBLE
        binding.tvProgress.text = "Preparing: 0%"

        lifecycleScope.launch {
            // Close existing database connection
            PerseusDatabase.destroyInstance()

            // Delete existing database file
            val existingDb = getDatabasePath("perseus_texts.db")
            if (existingDb.exists()) {
                existingDb.delete()
                // Also delete WAL and SHM files if they exist
                java.io.File(existingDb.path + "-wal").delete()
                java.io.File(existingDb.path + "-shm").delete()
            }

            val success = downloadManager.extractFullDatabase { progress ->
                runOnUiThread {
                    val percent = (progress * 100).toInt()
                    binding.downloadProgress.progress = percent
                    binding.tvProgress.text = "Extracting: $percent%"
                }
            }

            if (success) {
                // Clear any external database so full database takes effect
                PreferencesManager.clearExternalDatabaseUri(this@FullDatabaseDownloadActivity)

                // Delete external database file if it exists
                val externalDbFile = java.io.File(getDatabasePath("dummy").parent, "external_perseus_texts.db")
                if (externalDbFile.exists()) {
                    externalDbFile.delete()
                }

                // Set preference to indicate full database is now installed
                PreferencesManager.setUseFullDatabase(this@FullDatabaseDownloadActivity, true)

                runOnUiThread {
                    binding.tvStatus.text = "Full database installed!"
                    binding.downloadProgress.progress = 100
                    binding.tvProgress.text = "100%"

                    AlertDialog.Builder(this@FullDatabaseDownloadActivity)
                        .setTitle("Database Replaced")
                        .setMessage("The full database has been installed. The app will restart to use the new database.")
                        .setPositiveButton("Restart") { _, _ ->
                            restartApp()
                        }
                        .setCancelable(false)
                        .show()
                }
            } else {
                runOnUiThread {
                    binding.tvStatus.text = "Extraction failed.\n\nPlease try again."
                    binding.btnExtract.isEnabled = true
                    Toast.makeText(this@FullDatabaseDownloadActivity, "Failed to extract database", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun restartApp() {
        PerseusDatabase.destroyInstance()

        val intent = packageManager.getLaunchIntentForPackage(packageName)
        intent?.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        startActivity(intent)

        finishAffinity()
        android.os.Process.killProcess(android.os.Process.myPid())
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
