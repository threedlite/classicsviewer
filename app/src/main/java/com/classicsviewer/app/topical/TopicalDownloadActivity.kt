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
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat

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

        supportActionBar?.title = "Topical Links (Beta)"
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
            text = "Beta. Finds passages elsewhere in the corpus related to a " +
                "bookmarked line. Optional ~520 MB download; needs ~2 GB free " +
                "to install."
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

        // targetSdk 36 forces edge-to-edge, so the content draws under the
        // status/action bar unless we inset it. Add the system-bar insets on
        // top of the existing design padding.
        ViewCompat.setOnApplyWindowInsetsListener(root) { v, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(pad + bars.left, pad + bars.top, pad + bars.right, pad + bars.bottom)
            insets
        }

        packManager = TopicalPackManager(this)
        if (packManager.isInstalled()) showAlreadyInstalled()
    }

    private fun showAlreadyInstalled() {
        statusView.text = "Topical Links pack is already installed."
        startBtn.visibility = View.GONE
        cancelBtn.text = "OK"
    }

    private fun startDownload() {
        // The pack downloads ~520 MB and extracts to ~900 MB; both coexist, so
        // require ~2 GB free before starting. Mirrors the full/extended DB and
        // iOS StorageManager guards.
        val requiredBytes = 2L * 1024 * 1024 * 1024
        val stat = android.os.StatFs(filesDir.path)
        if (stat.availableBytes < requiredBytes) {
            val availGb = stat.availableBytes.toDouble() / (1024 * 1024 * 1024)
            AlertDialog.Builder(this)
                .setTitle("Not enough storage")
                .setMessage(String.format(
                    "Topical Links needs about 2 GB free to install (download plus " +
                    "extraction). Only %.1f GB is available.", availGb))
                .setPositiveButton("OK", null)
                .show()
            return
        }

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
