package com.classicsviewer.app.references

import android.os.Bundle
import android.view.MenuItem
import android.view.View
import android.widget.Toast
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.IntentSenderRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.classicsviewer.app.R
import com.classicsviewer.app.data.ReferencesPackManager
import com.classicsviewer.app.databinding.ActivityReferencesDownloadBinding

class ReferencesDownloadActivity : AppCompatActivity() {

    private lateinit var binding: ActivityReferencesDownloadBinding
    private lateinit var packManager: ReferencesPackManager
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
        super.onCreate(savedInstanceState)
        binding = ActivityReferencesDownloadBinding.inflate(layoutInflater)
        setContentView(binding.root)

        supportActionBar?.title = getString(R.string.references_download_title)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        packManager = ReferencesPackManager(this)

        if (packManager.isInstalled()) {
            showAlreadyInstalled()
        } else {
            showReadyToDownload()
        }

        binding.btnStartDownload.setOnClickListener { startDownload() }
        binding.btnCancel.setOnClickListener {
            if (isDownloading) packManager.cancelDownload()
            finish()
        }
    }

    private fun showReadyToDownload() {
        binding.tvStatus.text = getString(R.string.references_download_intro)
        binding.btnStartDownload.visibility = View.VISIBLE
        binding.btnCancel.visibility = View.VISIBLE
        binding.downloadProgress.visibility = View.GONE
    }

    private fun showAlreadyInstalled() {
        binding.tvStatus.text = getString(R.string.references_download_already_installed)
        binding.btnStartDownload.visibility = View.GONE
        binding.btnCancel.text = getString(android.R.string.ok)
    }

    private fun startDownload() {
        isDownloading = true
        binding.btnStartDownload.isEnabled = false
        binding.downloadProgress.visibility = View.VISIBLE
        binding.downloadProgress.progress = 0
        binding.tvStatus.text = getString(R.string.references_download_starting)
        binding.tvProgress.text = "0%"

        packManager.startDownload(
            onProgress = { bytesDownloaded, totalBytes, percent ->
                runOnUiThread {
                    binding.downloadProgress.progress = percent
                    val downloadedMB = bytesDownloaded / 1024 / 1024
                    val totalMB = totalBytes / 1024 / 1024
                    binding.tvProgress.text = "$percent% (${downloadedMB}MB / ${totalMB}MB)"
                    binding.tvStatus.text = getString(R.string.references_download_in_progress)
                }
            },
            onComplete = {
                runOnUiThread {
                    isDownloading = false
                    binding.tvStatus.text = getString(R.string.references_download_complete)
                    binding.downloadProgress.progress = 100
                    binding.tvProgress.text = "100%"
                    binding.btnStartDownload.visibility = View.GONE
                    binding.btnCancel.text = getString(android.R.string.ok)
                    Toast.makeText(this, R.string.references_download_complete, Toast.LENGTH_LONG).show()
                }
            },
            onError = { _, message ->
                runOnUiThread {
                    isDownloading = false
                    binding.tvStatus.text = getString(R.string.references_download_failed, message)
                    binding.btnStartDownload.isEnabled = true
                    Toast.makeText(this, message, Toast.LENGTH_LONG).show()
                }
            },
            onRequiresConfirmation = {
                runOnUiThread {
                    if (!confirmationDialogShown) {
                        confirmationDialogShown = true
                        packManager.showConfirmationDialog(confirmationLauncher)
                    }
                }
            },
        )
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
                .setTitle(R.string.references_download_cancel_title)
                .setMessage(R.string.references_download_cancel_message)
                .setPositiveButton(android.R.string.ok) { _, _ ->
                    packManager.cancelDownload()
                    finish()
                }
                .setNegativeButton(android.R.string.cancel, null)
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
