package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import android.view.MenuItem
import android.view.View
import android.view.WindowManager
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.IntentSenderRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.classicsviewer.app.data.ExtendedDeltaInstaller
import com.classicsviewer.app.data.ExtendedInstallJob
import com.classicsviewer.app.data.ExtendedPartsManager
import com.classicsviewer.app.data.FullDatabaseDownloadManager
import com.classicsviewer.app.database.PerseusDatabase
import com.classicsviewer.app.databinding.ActivityFullDatabaseDownloadBinding
import com.classicsviewer.app.utils.PreferencesManager
import kotlinx.coroutines.launch
import java.io.File

/**
 * The Extended database screen. Starts and shows [ExtendedInstallJob], which
 * owns the work; this screen can be closed and reopened while the job runs.
 *
 * Design: ANDROID_EXTENDED_LANGUAGE_PACKS_PROPOSAL.md, sections 8 and 10.
 * One tap installs everything: the full pack first if the base is the
 * sample or an older release, then the parts. Back while the job runs asks
 * Leave or Stay; Leave stops the job, which restores the database the user
 * had before. Any failure does the same.
 */
class ExtendedDatabaseDownloadActivity : AppCompatActivity() {

    private lateinit var binding: ActivityFullDatabaseDownloadBinding
    private lateinit var parts: ExtendedPartsManager
    private lateinit var installer: ExtendedDeltaInstaller
    private lateinit var fullManager: FullDatabaseDownloadManager
    private var confirmationDialogShown = false
    private var finishDialogShown = false

    private val confirmationLauncher: ActivityResultLauncher<IntentSenderRequest> =
        registerForActivityResult(ActivityResultContracts.StartIntentSenderForResult()) { result ->
            confirmationDialogShown = false
            if (result.resultCode != RESULT_OK) {
                Toast.makeText(this, "Download requires confirmation to proceed", Toast.LENGTH_LONG).show()
                ExtendedInstallJob.stop()
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        binding = ActivityFullDatabaseDownloadBinding.inflate(layoutInflater)
        setContentView(binding.root)
        supportActionBar?.title = "Download Extended Database"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        ViewCompat.setOnApplyWindowInsetsListener(binding.root) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }
        applyColorInversion()

        parts = ExtendedPartsManager(this)
        installer = ExtendedDeltaInstaller(this, parts)
        fullManager = FullDatabaseDownloadManager(this)
        binding.tvTitle.text = "Extended Database"
        binding.btnExtract.visibility = View.GONE
        binding.btnCancel.setOnClickListener { handleBack() }
        binding.btnStartDownload.setOnClickListener { confirmAndStart() }

        // Back through the dispatcher: the deprecated onBackPressed() override is
        // not called under predictive back (target SDK 36), which on the device
        // let back close this screen with the merge still running.
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() { handleBack() }
        })

        if (!ExtendedInstallJob.running) showState()
        observeJob()
    }

    private fun observeJob() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                launch {
                    ExtendedInstallJob.status.collect { st -> render(st) }
                }
                launch {
                    ExtendedInstallJob.confirmationNeeded.collect { req ->
                        if (req != ExtendedInstallJob.ConfirmationRequest.NONE && !confirmationDialogShown) {
                            confirmationDialogShown = true
                            ExtendedInstallJob.confirmationNeeded.value = ExtendedInstallJob.ConfirmationRequest.NONE
                            val shown = if (req == ExtendedInstallJob.ConfirmationRequest.FULL)
                                fullManager.showConfirmationDialog(confirmationLauncher)
                            else parts.showConfirmationDialog(confirmationLauncher)
                            if (!shown) confirmationDialogShown = false
                        }
                    }
                }
            }
        }
    }

    private fun render(st: ExtendedInstallJob.Status) {
        when {
            st.running -> {
                window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                binding.btnStartDownload.visibility = View.GONE
                binding.tvSpaceWarning.visibility = View.GONE
                binding.downloadProgress.visibility = View.VISIBLE
                binding.downloadProgress.progress = st.percent
                binding.tvProgress.text = "${st.percent}%"
                binding.tvStatus.text = st.stage
                binding.btnCancel.text = "Leave"
            }
            st.done -> {
                window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                binding.downloadProgress.progress = 100
                binding.tvProgress.text = "100%"
                binding.tvStatus.text = "All parts are merged."
                if (!finishDialogShown) {
                    finishDialogShown = true
                    AlertDialog.Builder(this)
                        .setTitle("Extended Database Installed")
                        .setMessage("All parts are merged. The app will restart to use the extended database.")
                        .setPositiveButton("Restart") { _, _ -> ExtendedInstallJob.acknowledge(); restartApp() }
                        .setCancelable(false)
                        .show()
                }
            }
            st.failed -> {
                window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                if (!finishDialogShown) {
                    finishDialogShown = true
                    AlertDialog.Builder(this)
                        .setTitle(if (st.message.startsWith("install stopped")) "Extended Install Stopped" else "Extended Install Failed")
                        .setMessage("${st.message}\n\nThe app has gone back to ${st.restored} and will restart. You can start again from the menu.")
                        .setPositiveButton("Restart") { _, _ -> ExtendedInstallJob.acknowledge(); restartApp() }
                        .setCancelable(false)
                        .show()
                }
            }
            else -> { window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON); showState() }
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

    private fun needsFullStep(): Boolean =
        !PreferencesManager.getUseFullDatabase(this) || installer.updateAvailable()

    /** The idle state of the screen: what would happen, and whether it can. */
    private fun showState() {
        binding.downloadProgress.visibility = View.GONE
        binding.tvProgress.text = ""
        binding.tvSpaceWarning.visibility = View.GONE
        binding.btnCancel.text = "Cancel"
        val lastFailure = PreferencesManager.getExtendedLastFailure(this)
        val failures = PreferencesManager.getExtendedFailures(this, installer.baseBuildTime())
        val failureNote = if (lastFailure != null) {
            "\n\nLast attempt failed: $lastFailure" +
                if (failures >= 2) "\nThis has failed $failures times for this release. Check free space, or wait for the next app update, before trying again." else ""
        } else ""

        when {
            !ExtendedPartsManager.enabled -> {
                binding.tvStatus.text = "The extended database is not available in this version."
                binding.btnStartDownload.visibility = View.GONE
            }
            PreferencesManager.getExternalDatabaseUri(this) != null -> {
                binding.tvStatus.text = "An external database is active. The extended database merges onto the full database only.\n\nReset to the bundled database, then return here."
                binding.btnStartDownload.visibility = View.GONE
            }
            parts.allInstalled() && !installer.updateAvailable() -> {
                binding.tvStatus.text = "The extended database is installed (${ExtendedPartsManager.PART_PACKS.size} parts).\n\nRelease: ${installer.baseBuildTime()}"
                binding.btnStartDownload.visibility = View.GONE
                binding.btnCancel.text = "Close"
            }
            else -> {
                val fullStep = needsFullStep()
                val pending = if (fullStep) ExtendedPartsManager.PART_PACKS
                              else ExtendedPartsManager.PART_PACKS.filter { parts.partState(it) != ExtendedPartsManager.STATE_INSTALLED }
                val partBytes = pending.mapNotNull { parts.partSidecar(it)?.optLong("zip_bytes") }
                val fullBytes = if (fullStep) File(fullManager.getFullDatabaseZipPath() ?: "").length().takeIf { it > 0 } else 0L
                val known = partBytes.size == pending.size && (fullBytes != null)
                val sizeText = if (known) "%.2f GB to download".format(((fullBytes ?: 0L) + partBytes.sum()) / 1e9) else "download size shown once it starts"
                val header = when {
                    installer.updateAvailable() && PreferencesManager.getUseFullDatabase(this) ->
                        "Update available: Google Play has a newer data release (${parts.fullPackBuildTime()}) than this device (${installer.baseBuildTime()}). This will re-download the full database and every part."
                    fullStep ->
                        "The extended database is built on the full database. This downloads the full database first, then the extended parts, and restarts once at the end."
                    else ->
                        "Adds First1K and PTA Greek plus Sanskrit, Pali, Coptic, Hebrew, Syriac, Norse, Chinese, Persian and Arabic to the full database."
                }
                // Peak during the last merge plus the copy of the current database
                // kept for going back (ANDROID_EXTENDED_LANGUAGE_PACKS_PROPOSAL.md, section 14).
                val neededBytes = FullDatabaseDownloadManager.REQUIRED_SPACE_BYTES + getDatabasePath("perseus_texts.db").length()
                val availableBytes = android.os.StatFs(filesDir.path).availableBytes
                val enough = availableBytes >= neededBytes
                binding.tvSpaceWarning.text = "Available space: ${availableBytes / 1_000_000_000} GB\nNeeded during install: about ${neededBytes / 1_000_000_000} GB"
                binding.tvSpaceWarning.visibility = View.VISIBLE
                binding.tvSpaceWarning.setTextColor(if (enough) (if (PreferencesManager.getInvertColors(this)) 0xFF000000.toInt() else 0xFFFFFFFF.toInt()) else 0xFFFF6B6B.toInt())
                binding.tvStatus.text = "$header\n\n${pending.size} part(s), $sizeText. The database grows to about 15 GB and the merge takes some minutes per part; keep the app open. If anything fails, the app goes back to the database you have now.$failureNote"
                binding.btnStartDownload.text = "Download and Install"
                binding.btnStartDownload.visibility = View.VISIBLE
                binding.btnStartDownload.isEnabled = enough
            }
        }
    }

    /**
     * The job is long and must not be interrupted, so it never starts
     * without saying so. Times measured on a Pixel 6 on 2026-09-27: full
     * pack extraction under a minute, part 1 about 13 minutes (7 merging,
     * 6 verifying), part 2 about 8 minutes, plus the downloads.
     */
    private fun confirmAndStart() {
        if (ExtendedInstallJob.running) return
        val fullStep = needsFullStep()
        val outdatedFull = PreferencesManager.getUseFullDatabase(this) && installer.updateAvailable()
        val opening = when {
            outdatedFull ->
                "The full database on this phone is from an older data release than Google Play has now. " +
                "The extended parts must match the full database exactly, so the full database is downloaded and installed again first, then the parts are merged into it.\n\n"
            fullStep ->
                "The full database is downloaded and installed first, then the extended parts are merged into it.\n\n"
            else -> "The extended parts are merged into the full database.\n\n"
        }
        AlertDialog.Builder(this)
            .setTitle("This will take a while")
            .setMessage(
                opening +
                "Expect 30 minutes or more on a typical phone, plus the download time, and longer on older phones. " +
                "Keep the app open and the phone plugged in until it finishes.\n\n" +
                "If it is interrupted or anything fails, the app goes back to the database you have now; nothing is lost."
            )
            .setPositiveButton("Continue") { _, _ -> finishDialogShown = false; ExtendedInstallJob.start(this) }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun restartApp() {
        PerseusDatabase.destroyInstance()
        val intent = packageManager.getLaunchIntentForPackage(packageName)
        intent?.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        startActivity(intent)
        finishAffinity()
        android.os.Process.killProcess(android.os.Process.myPid())
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean = when (item.itemId) {
        android.R.id.home -> { handleBack(); true }
        else -> super.onOptionsItemSelected(item)
    }

    private fun handleBack() {
        if (ExtendedInstallJob.running) {
            AlertDialog.Builder(this)
                .setTitle("Install in progress")
                .setMessage("Leaving now will stop the install and the app will go back to the database you had before. Continue?")
                .setPositiveButton("Leave") { _, _ -> ExtendedInstallJob.stop() }  // the job restores; this screen then shows the result
                .setNegativeButton("Stay", null)
                .show()
        } else finish()
    }
}
