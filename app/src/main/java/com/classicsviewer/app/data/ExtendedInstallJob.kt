package com.classicsviewer.app.data

import android.content.Context
import android.util.Log
import com.classicsviewer.app.database.PerseusDatabase
import com.classicsviewer.app.utils.PreferencesManager
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.ensureActive
import kotlin.coroutines.coroutineContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import java.io.File
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * The Extended install job, owned by the process rather than by a screen.
 *
 * Design: ANDROID_EXTENDED_LANGUAGE_PACKS_PROPOSAL.md, sections 7, 8 and 10.
 * A screen that is closed must not take the merge down with it (found on
 * the device 2026-09-28: back closed the download screen, the main screen
 * opened over a half-merged database, and the merge coroutine died with the
 * screen). So the job runs here, the download screen only attaches to it
 * to show progress and to ask it to stop, and the main screen refuses to
 * open the database while it is running.
 *
 * Stopping is cooperative: a statement in progress finishes, then the job
 * sees the cancellation, restores the pre-job copy and reports it.
 */
object ExtendedInstallJob {

    private const val TAG = "ExtendedInstallJob"

    data class Status(
        val running: Boolean = false,
        val stage: String = "",
        val percent: Int = 0,
        val done: Boolean = false,          // finished successfully; restart to use it
        val failed: Boolean = false,        // finished with a failure or was stopped
        val message: String = "",           // reason when failed
        val restored: String = ""           // what was put back when failed
    )

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var job: Job? = null
    private var currentPack: String? = null
    private var partsRef: ExtendedPartsManager? = null

    private val _status = MutableStateFlow(Status())
    val status: StateFlow<Status> get() = _status

    val running: Boolean get() = job?.isActive == true

    /** Called by the screen when the user pressed Continue. No-op if running. */
    fun start(context: Context) {
        if (running) return
        val app = context.applicationContext
        _status.value = Status(running = true, stage = "Starting", percent = 0)
        job = scope.launch { run(app) }
    }

    /** Called by the screen on Leave. The job restores the previous database. */
    fun stop() {
        currentPack?.let { partsRef?.cancelDownload(it) }
        job?.cancel(CancellationException("install stopped by the user"))
    }

    /** Clears a finished status so the screen shows its normal state again. */
    fun acknowledge() {
        if (!running) _status.value = Status()
    }

    private fun report(stage: String, percent: Int) {
        _status.value = Status(running = true, stage = stage, percent = percent)
    }

    private suspend fun run(app: Context) {
        val parts = ExtendedPartsManager(app)
        val installer = ExtendedDeltaInstaller(app, parts)
        val fullManager = FullDatabaseDownloadManager(app)
        partsRef = parts
        try {
            // Keep what the user has now, so any failure can put it back exactly.
            if (!PreferencesManager.isExtendedJobActive(app)) {
                report("Keeping a copy of the current database", 0)
                installer.beginJob { report("Keeping a copy of the current database", it) }
            }
            PreferencesManager.setDbTarget(app, "extended")

            // Step A: the full base, when there is none or Play has a newer release.
            if (!PreferencesManager.getUseFullDatabase(app) || installer.updateAvailable()) {
                coroutineContext.ensureActive()
                if (!fullManager.isFullDatabaseDownloaded()) {
                    report("Full database: downloading", 0)
                    downloadFull(fullManager)
                }
                coroutineContext.ensureActive()
                report("Full database: installing", 0)
                installFullBase(app, fullManager, parts, installer)
            }

            // Step B: the parts, in registry order.
            val pending = ExtendedPartsManager.PART_PACKS.filter { parts.partState(it) != ExtendedPartsManager.STATE_INSTALLED }
            for (pack in pending) {
                coroutineContext.ensureActive()
                val label = "Part ${ExtendedPartsManager.PART_PACKS.indexOf(pack) + 1} of ${ExtendedPartsManager.PART_PACKS.size}"
                currentPack = pack
                if (!parts.isDownloaded(pack)) {
                    report("$label: downloading", 0)
                    downloadPart(parts, pack, label)
                }
                coroutineContext.ensureActive()
                report("$label: installing", 0)
                installer.install(pack) { stage, percent -> report("$label: $stage", percent) }
                currentPack = null
            }

            installer.endJobSuccess()
            PreferencesManager.clearExtendedFailures(app)
            _status.value = Status(running = false, done = true, stage = "Installed", percent = 100)
        } catch (e: Throwable) {
            val stopped = e is CancellationException
            val msg = if (stopped) "install stopped by the user" else (e.message ?: e.javaClass.simpleName)
            Log.w(TAG, "job ended: $msg", if (stopped) null else e)
            PreferencesManager.recordExtendedFailure(app, installer.baseBuildTime(), msg)
            // Decided: any failure, and a stop, puts back the database the user
            // had before the job started. The installer restores on its own
            // failures once a merge has begun; everything else is restored here.
            val restored = if (PreferencesManager.isExtendedJobActive(app)) {
                runCatching { installer.restorePrevious(msg) }.getOrElse { "nothing; restore failed: ${it.message}" }
            } else "the previous database"
            _status.value = Status(running = false, failed = true, message = msg, restored = restored)
        } finally {
            currentPack = null
            partsRef = null
        }
    }

    private suspend fun downloadFull(fullManager: FullDatabaseDownloadManager) =
        suspendCancellableCoroutine<Unit> { cont ->
            var done = false
            fullManager.startDownload(
                onProgress = { got, total, percent -> report("Full database: downloading (${got / 1_000_000} MB / ${total / 1_000_000} MB)", percent) },
                onComplete = { if (!done) { done = true; cont.resume(Unit) } },
                onError = { _, message -> if (!done) { done = true; cont.resumeWithException(ExtendedDeltaInstaller.InstallException("full database download failed: $message")) } },
                onRequiresConfirmation = { confirmationNeeded.value = ConfirmationRequest.FULL }
            )
            cont.invokeOnCancellation { fullManager.cancelDownload() }
        }

    private suspend fun downloadPart(parts: ExtendedPartsManager, pack: String, label: String) =
        suspendCancellableCoroutine<Unit> { cont ->
            var done = false
            parts.startDownload(
                pack,
                onProgress = { got, total, percent -> report("$label: downloading (${got / 1_000_000} MB / ${total / 1_000_000} MB)", percent) },
                onComplete = { if (!done) { done = true; cont.resume(Unit) } },
                onError = { _, message -> if (!done) { done = true; cont.resumeWithException(ExtendedDeltaInstaller.InstallException("download failed: $message")) } },
                onRequiresConfirmation = { confirmationNeeded.value = ConfirmationRequest.PART }
            )
            cont.invokeOnCancellation { parts.cancelDownload(pack) }
        }

    /**
     * Play's Wi-Fi and large-download consent needs an Activity to show its
     * dialog. The job signals; the attached screen shows it and clears this.
     */
    enum class ConfirmationRequest { NONE, FULL, PART }
    val confirmationNeeded = MutableStateFlow(ConfirmationRequest.NONE)

    /**
     * Step A, second half: the existing whole-file replacement
     * (FullDatabaseDownloadActivity.extractDatabase) without its restart.
     * Any merged parts go with the old file, so their state is cleared.
     */
    private suspend fun installFullBase(
        app: Context, fullManager: FullDatabaseDownloadManager,
        parts: ExtendedPartsManager, installer: ExtendedDeltaInstaller
    ) {
        PerseusDatabase.destroyInstance()
        val existing = app.getDatabasePath("perseus_texts.db")
        if (existing.exists()) existing.delete()
        for (suffix in listOf("-wal", "-shm", "-journal")) File(existing.path + suffix).delete()
        val ok = fullManager.extractFullDatabase { progress -> report("Full database: extracting", (progress * 100).toInt()) }
        if (!ok) throw IllegalStateException("full database extraction failed")
        PreferencesManager.clearExternalDatabaseUri(app)
        File(app.getDatabasePath("dummy").parent, "external_perseus_texts.db").delete()
        PreferencesManager.setUseFullDatabase(app, true)
        PreferencesManager.setExtendedPackState(app, "{}")
        parts.clearState()
        val baseBt = installer.baseBuildTime() ?: throw IllegalStateException("extracted full database has no build marker")
        val playBt = parts.fullPackBuildTime()
        if (playBt != null && playBt != baseBt) throw IllegalStateException("extracted full database is release $baseBt but its sidecar says $playBt")
    }
}
