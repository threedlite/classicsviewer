package com.classicsviewer.app.topical

import android.os.Bundle
import android.view.MenuItem
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.IntentSenderRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity

/**
 * On-demand install UI for the topical-links asset pack
 * ([TopicalPackManager.ASSET_PACK_NAME]). Mirrors the references pack's
 * download activity but with a self-contained programmatic layout so it adds
 * no new XML/string resources.
 */
class TopicalDownloadActivity : AppCompatActivity() {

    private lateinit var packManager: TopicalPackManager
    private lateinit var statusView: TextView
    private lateinit var progressBar: ProgressBar
    private lateinit var progressText: TextView
    private lateinit var startBtn: Button
    private lateinit var cancelBtn: Button

    private var isDownloading = false
    private var confirmationDialogShown = false

    private val confirmationLauncher: ActivityResultLauncher<IntentSenderRequest> =
        registerForActivityResult(ActivityResultContracts.StartIntentSenderForResult()) { result ->
            if (result.resultCode == RESULT_OK) {
                confirmationDialogShown = false
            } else {
                Toast.makeText(this, "Download requires confirmation to proceed",
                    Toast.LENGTH_LONG).show()
                finish()
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        supportActionBar?.title = "Topical Links"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        val pad = (24 * resources.displayMetrics.density).toInt()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(pad, pad, pad, pad)
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT)
        }
        statusView = TextView(this).apply {
            textSize = 16f
            text = "Topical Links surface passages semantically related to a " +
                "bookmarked line. The data is delivered as an optional download " +
                "(~410 MB)."
        }
        progressBar = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100
            visibility = View.GONE
        }
        progressText = TextView(this).apply {
            textSize = 14f
            visibility = View.GONE
        }
        startBtn = Button(this).apply {
            text = "Download Topical Links"
            setOnClickListener { startDownload() }
        }
        cancelBtn = Button(this).apply {
            text = "Cancel"
            setOnClickListener {
                if (isDownloading) packManager.cancelDownload()
                finish()
            }
        }
        listOf(statusView, progressBar, progressText, startBtn, cancelBtn).forEach { v ->
            root.addView(v, LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply { topMargin = pad / 2 })
        }
        setContentView(root)

        packManager = TopicalPackManager(this)
        if (packManager.isInstalled()) showAlreadyInstalled()
    }

    private fun showAlreadyInstalled() {
        statusView.text = "Topical Links pack is already installed."
        startBtn.visibility = View.GONE
        cancelBtn.text = "OK"
    }

    private fun startDownload() {
        isDownloading = true
        startBtn.isEnabled = false
        progressBar.visibility = View.VISIBLE
        progressBar.progress = 0
        progressText.visibility = View.VISIBLE
        progressText.text = "0%"
        statusView.text = "Starting download…"

        packManager.startDownload(
            onProgress = { downloaded, total, percent ->
                runOnUiThread {
                    progressBar.progress = percent
                    val mb = downloaded / 1024 / 1024
                    val totalMb = total / 1024 / 1024
                    progressText.text = "$percent%  (${mb}MB / ${totalMb}MB)"
                    statusView.text = "Downloading…"
                }
            },
            onComplete = {
                runOnUiThread {
                    isDownloading = false
                    statusView.text = "Download complete."
                    progressBar.progress = 100
                    progressText.text = "100%"
                    startBtn.visibility = View.GONE
                    cancelBtn.text = "OK"
                    Toast.makeText(this, "Topical Links installed", Toast.LENGTH_LONG).show()
                }
            },
            onError = { _, message ->
                runOnUiThread {
                    isDownloading = false
                    statusView.text = "Download failed: $message"
                    startBtn.isEnabled = true
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
        if (item.itemId == android.R.id.home) { handleBack(); return true }
        return super.onOptionsItemSelected(item)
    }

    private fun handleBack() {
        if (isDownloading) {
            AlertDialog.Builder(this)
                .setTitle("Cancel download?")
                .setMessage("The download will be aborted. You can restart it later.")
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
