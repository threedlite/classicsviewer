package com.classicsviewer.app.data

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.os.StatFs
import android.util.Log
import com.classicsviewer.app.database.PerseusDatabase
import com.classicsviewer.app.utils.PreferencesManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.util.zip.ZipFile

/**
 * Merges one extended-delta part into the on-device full database.
 *
 * Design: ANDROID_EXTENDED_LANGUAGE_PACKS_PROPOSAL.md, sections 6 and 7.
 * Every check here is a hard failure, and every failure ends the same way:
 * the app returns to the sample database ([recoverToSample]), records the
 * reason, and the user may start Extended again from the menu. There is no
 * in-place repair, no partial-delete logic, and nothing retries on its own.
 *
 * The merge statements are read from assets/delta_merge.sql, a build-time
 * copy of shared/delta_merge.sql, which is the same SQL the data build's
 * desktop round trip proved equals the extended DB.
 */
class ExtendedDeltaInstaller(private val context: Context, private val parts: ExtendedPartsManager) {

    companion object {
        private const val TAG = "ExtendedDelta"
        const val MANIFEST_VERSION = 1
        private const val DB_NAME = "perseus_texts.db"
        private const val MERGE_SQL_ASSET = "delta_merge.sql"
        private const val LOOKUP_TABLE = "translation_lookup"

        /** First line of the build marker row: `Build Time: <timestamp>`. */
        fun readBuildTime(dbFile: File): String? {
            if (!dbFile.exists()) return null
            return runCatching {
                SQLiteDatabase.openDatabase(dbFile.path, null, SQLiteDatabase.OPEN_READONLY).use { db ->
                    db.rawQuery(
                        "SELECT entry_plain FROM dictionary_entries WHERE language = 'system' AND headword = 'build_time'",
                        null
                    ).use { c ->
                        if (!c.moveToFirst()) return null
                        val first = (c.getString(0) ?: "").lineSequence().firstOrNull() ?: ""
                        first.removePrefix("Build Time: ").trim().ifEmpty { null }
                    }
                }
            }.getOrNull()
        }

        /**
         * sha256 over the canonical schema, computed exactly as the build does
         * (`_schema_sha256` in assemble_database.py): `name\nsql` pairs from
         * sqlite_master sorted by name, joined with `\n`.
         */
        fun schemaSha256(db: SQLiteDatabase): String {
            val rows = ArrayList<Pair<String, String>>()
            // Only the canonical objects: Android adds android_metadata on the first
            // read-write open and Room adds room_master_table; neither is part of
            // the schema the build hashed (found on the device 2026-09-27, when
            // part 2 was refused after part 1's merge had created android_metadata).
            db.rawQuery(
                "SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' " +
                    "AND name NOT IN ('android_metadata', 'room_master_table') ORDER BY name",
                null
            ).use { c -> while (c.moveToNext()) rows.add(c.getString(0) to c.getString(1)) }
            val text = rows.joinToString("\n") { "${it.first}\n${it.second}" }
            return MessageDigest.getInstance("SHA-256").digest(text.toByteArray(Charsets.UTF_8))
                .joinToString("") { "%02x".format(it) }
        }
    }

    class InstallException(message: String) : Exception(message)

    private val baseDb: File get() = context.getDatabasePath(DB_NAME)

    /** The database the user had before the job began, kept until the job ends. */
    val backupDb: File get() = context.getDatabasePath("$DB_NAME.pre_extended")

    // ---- the job: what to go back to ------------------------------------------

    /**
     * Called once before the first change. Copies the current database aside
     * and records the preferences that describe it, so [restorePrevious] can
     * put back exactly what the user had, sample or full, whatever release.
     */
    suspend fun beginJob(onProgress: (Int) -> Unit) = withContext(Dispatchers.IO) {
        PerseusDatabase.destroyInstance()
        if (backupDb.exists()) backupDb.delete()
        val src = baseDb
        if (src.exists()) {
            // Fold any WAL content into the main file so the copy is the whole
            // database, not the main file minus the last uncheckpointed pages.
            SQLiteDatabase.openDatabase(src.path, null, SQLiteDatabase.OPEN_READWRITE).use { db ->
                db.rawQuery("PRAGMA wal_checkpoint(TRUNCATE)", null).use { it.moveToFirst() }
            }
            val total = src.length().coerceAtLeast(1)
            var done = 0L
            src.inputStream().buffered(1 shl 20).use { input ->
                backupDb.outputStream().buffered(1 shl 20).use { out ->
                    val buf = ByteArray(1 shl 20)
                    var n: Int
                    while (input.read(buf).also { n = it } != -1) {
                        out.write(buf, 0, n)
                        done += n
                        onProgress(((done * 100) / total).toInt())
                    }
                }
            }
            if (backupDb.length() != src.length()) throw InstallException("could not copy the current database aside")
        }
        PreferencesManager.beginExtendedJob(context)
    }

    /** The job finished: the previous database is no longer needed. */
    fun endJobSuccess() {
        backupDb.delete()
        PreferencesManager.endExtendedJob(context)
    }

    /**
     * Decided: on any failure, and after an interrupted job, the app goes
     * back to the database it had before the job started. The copy taken by
     * [beginJob] is moved back into place and the preferences that describe
     * it restored. If no copy exists (nothing had been changed yet, or the
     * copy itself is missing) the fallback is the sample database.
     * Returns a short description of what was restored.
     */
    suspend fun restorePrevious(reason: String): String = withContext(NonCancellable + Dispatchers.IO) {
        // NonCancellable: this runs from a job that may already be cancelled
        // (Leave), and a cancelled coroutine cannot otherwise switch
        // dispatchers. Found on the device 2026-09-28: the in-job restore
        // threw at once and only the launch-time recovery put the database back.
        Log.w(TAG, "restoring the previous database: $reason")
        PerseusDatabase.destroyInstance()
        File(context.filesDir, "packs/tmp").listFiles()?.forEach { it.delete() }
        parts.clearState()
        val main = baseDb
        if (backupDb.exists() && backupDb.length() > 0) {
            if (main.exists()) main.delete()
            for (suffix in listOf("-wal", "-shm", "-journal")) File(main.path + suffix).delete()
            if (!backupDb.renameTo(main)) {
                // The copy cannot be put back: the one case the copy does not
                // cover. Fall through to the sample rather than leave the job
                // open, which would repeat this on every launch.
                Log.e(TAG, "could not move the previous database back; falling back to the sample")
                backupDb.delete()
                PreferencesManager.endExtendedJob(context)
                recoverToSample("$reason (previous copy could not be restored)")
                return@withContext "the sample database"
            }
            val prevFull = PreferencesManager.extendedJobPrevFull(context)
            val prevTarget = PreferencesManager.extendedJobPrevTarget(context)
            PreferencesManager.setUseFullDatabase(context, prevFull)
            PreferencesManager.setDbTarget(context, if (prevTarget == "extended") "full" else prevTarget)
            PreferencesManager.endExtendedJob(context)
            if (prevFull) "the full database" else "the sample database"
        } else {
            PreferencesManager.endExtendedJob(context)
            recoverToSample(reason)
            "the sample database"
        }
    }

    /** The base's release identity, read from the file each time, never cached. */
    fun baseBuildTime(): String? = readBuildTime(baseDb)

    /** True when Play holds a newer full pack than the one extracted on this device. */
    fun updateAvailable(): Boolean {
        val playBt = parts.fullPackBuildTime() ?: return false
        val baseBt = baseBuildTime() ?: return false
        return playBt != baseBt
    }

    // ---- the merge --------------------------------------------------------------

    /**
     * Merge one part. Throws [InstallException] on any failure AFTER having
     * returned the device to the sample database, so the caller only has to
     * report the message and restart.
     */
    suspend fun install(pack: String, onProgress: (stage: String, percent: Int) -> Unit) =
        withContext(Dispatchers.IO) {
            var mergingStarted = false
            try {
                doInstall(pack, onProgress) { mergingStarted = true }
            } catch (e: Exception) {
                Log.e(TAG, "install($pack) failed", e)
                val reason = "${pack}: ${e.message ?: e.javaClass.simpleName}"
                // The failure is counted once, by the screen that owns the job.
                if (mergingStarted) {
                    restorePrevious(reason)
                } else {
                    parts.setPartState(pack, ExtendedPartsManager.STATE_ABSENT, null)
                }
                throw InstallException(reason)
            }
        }

    private fun doInstall(pack: String, onProgress: (String, Int) -> Unit, markMerging: () -> Unit) {
        // 1. Preconditions.
        if (!PreferencesManager.isExtendedJobActive(context)) fail("no install job is open; beginJob() must run first")
        if (PreferencesManager.getExternalDatabaseUri(context) != null) fail("an external database is active; parts merge only onto the full pack")
        if (!PreferencesManager.getUseFullDatabase(context)) fail("the full database is not installed; Extended needs it first")
        val zip = parts.partZip(pack) ?: fail("part not downloaded")
        val manifest = readManifest(zip)
        // The zip's own hash cannot live inside the zip; it is in the sidecar
        // that ships beside it in the same pack (proposal section 5).
        val sidecar = parts.partSidecar(pack) ?: fail("no sidecar manifest beside the part")
        val expectedZipSha = sidecar.optString("zip_sha256").ifEmpty { fail("sidecar has no zip_sha256") }
        if (sidecar.optString("build_time") != manifest.optString("build_time")) fail("sidecar and part disagree on the release")
        if (manifest.optInt("manifest_version", -1) != MANIFEST_VERSION) fail("manifest version ${manifest.opt("manifest_version")} is not $MANIFEST_VERSION; update the app")
        if (manifest.optString("pack_id") != pack) fail("manifest is for ${manifest.optString("pack_id")}, not $pack")
        val baseBt = baseBuildTime() ?: fail("the full database has no build marker")
        val partBt = manifest.optString("build_time")
        if (partBt != baseBt) fail("release mismatch: the full database is $baseBt but this part is $partBt; Google Play has not finished updating both")
        SQLiteDatabase.openDatabase(baseDb.path, null, SQLiteDatabase.OPEN_READONLY).use { db ->
            val have = schemaSha256(db)
            if (have != manifest.optString("schema_sha256")) fail("schema mismatch; update the app")
        }
        val dbBytes = manifest.optLong("db_bytes")
        val need = dbBytes + baseDb.length() / 10 + 500L * 1024 * 1024  // the backup copy already exists
        val free = StatFs(context.filesDir.path).availableBytes
        if (free < need) fail("not enough free space: ${need / 1_000_000_000.0} GB needed, ${free / 1_000_000_000.0} GB free")

        // 2. No Room connection may be open.
        PerseusDatabase.destroyInstance()

        // 3. Verify the zip and inflate the part next to the database, not in
        //    cacheDir (the system may clear cache files under an attached DB).
        onProgress("Verifying download", 0)
        val sha = sha256(zip) { onProgress("Verifying download", it) }
        if (sha != expectedZipSha) fail("downloaded file is corrupt (checksum mismatch)")
        val tmpDir = File(context.filesDir, "packs/tmp").apply { mkdirs() }
        val partDb = File(tmpDir, "$pack.db")
        inflate(zip, "$pack.db", partDb, dbBytes) { onProgress("Unpacking", it) }
        if (partDb.length() != dbBytes) fail("unpacked size ${partDb.length()} != manifest ${dbBytes}")

        // 4. Record 'merging' before the first write to the base.
        parts.setPartState(pack, ExtendedPartsManager.STATE_MERGING, baseBt)
        markMerging()
        val db = SQLiteDatabase.openDatabase(baseDb.path, null, SQLiteDatabase.OPEN_READWRITE)
        try {
            db.execSQL("PRAGMA foreign_keys = OFF")
            // No journal for the merge: a crash mid-way leaves the file unusable
            // either way (decided: recovery is the rebuild), and a WAL would
            // grow to the size of the largest table being copied.
            db.rawQuery("PRAGMA journal_mode = OFF", null).use { it.moveToFirst() }
            db.execSQL("PRAGMA synchronous = OFF")
            db.execSQL("ATTACH DATABASE ? AS part", arrayOf(partDb.path))

            // Expected row counts, from the attached part itself.
            val before = tableCounts(db, "main")
            val partCounts = tableCounts(db, "part")
            val expectedRows = manifest.optJSONObject("rows") ?: JSONObject()
            for (t in partCounts.keys) {
                if (expectedRows.has(t) && expectedRows.optLong(t) != partCounts[t]) {
                    fail("part $t holds ${partCounts[t]} rows but its manifest says ${expectedRows.optLong(t)}")
                }
            }
            val existingAuthors = count(db, "SELECT COUNT(*) FROM part.authors WHERE id IN (SELECT id FROM main.authors)")
            val partSystemRows = count(db, "SELECT COUNT(*) FROM part.dictionary_entries WHERE language = 'system'")
            val orphansBefore = count(db, "SELECT COUNT(*) FROM main.translation_segments WHERE book_id NOT IN (SELECT id FROM main.books)")

            // Indexes stay in place and are maintained by the inserts. Android
            // builds SQLite with SQLITE_TEMP_STORE=3 (temporary storage always in
            // memory), so CREATE INDEX over tens of millions of rows sorts in RAM
            // and killed the process on a Pixel 6 (2026-09-27, native crash in
            // sqlite3MemMalloc during the rebuild). Incremental index maintenance
            // is slower but its memory is bounded, and it is what the build's
            // desktop round trip does too.
            db.execSQL("PRAGMA cache_size = -131072")  // 128 MB page cache
            // Guard: if any SQLite allocation on this connection ever grew past
            // this, SQLite returns SQLITE_NOMEM, which is a catchable exception
            // that the installer turns into the restore of the previous database,
            // instead of the process being killed.
            db.rawQuery("PRAGMA hard_heap_limit = 402653184", null).use { it.moveToFirst() }  // 384 MB

            // 5. The shared merge statements, one transaction each.
            val statements = mergeStatements()
            statements.forEachIndexed { i, st ->
                onProgress("Merging", (i * 90) / statements.size)
                db.beginTransaction()
                try {
                    db.execSQL(st)
                    db.setTransactionSuccessful()
                } finally {
                    db.endTransaction()
                }
            }
            // 6. Verify.
            onProgress("Verifying", 95)
            val after = tableCounts(db, "main")
            for (t in after.keys) {
                var expectedAdded = partCounts[t] ?: 0L
                if (t == "authors") expectedAdded -= existingAuthors
                if (t == "dictionary_entries") expectedAdded -= partSystemRows
                val expected = (before[t] ?: 0L) + expectedAdded
                if (after[t] != expected) fail("$t has ${after[t]} rows after the merge, expected $expected")
            }
            for (t in after.keys) {
                if (t == "translation_segments") continue  // orphan segments are in the data by design
                val bad = count(db, "PRAGMA main.foreign_key_check($t)", countRows = true)
                if (bad > 0L) fail("$t: $bad foreign key violations after the merge")
            }
            val orphansNow = count(db, "SELECT COUNT(*) FROM main.translation_segments WHERE book_id NOT IN (SELECT id FROM main.books)")
            val orphansPart = count(db, "SELECT COUNT(*) FROM part.translation_segments WHERE book_id NOT IN (SELECT id FROM part.books)")
            if (manifest.has("orphan_segments") && manifest.optLong("orphan_segments") != orphansPart) {
                fail("part orphan segments $orphansPart != manifest ${manifest.optLong("orphan_segments")}")
            }
            if (orphansNow < orphansPart + orphansBefore) fail("orphan translation segments were lost in the merge")
            db.rawQuery("PRAGMA main.quick_check", null).use { c ->
                if (!c.moveToFirst() || c.getString(0) != "ok") fail("quick_check failed: ${if (c.count > 0) c.getString(0) else "no result"}")
            }
            db.execSQL("DETACH DATABASE part")
            db.rawQuery("PRAGMA journal_mode = WAL", null).use { it.moveToFirst() }
            db.execSQL("PRAGMA foreign_keys = ON")
        } finally {
            db.close()
        }

        // 7. Done: drop the inflated copy, mark installed, delete the pack.
        partDb.delete()
        parts.setPartState(pack, ExtendedPartsManager.STATE_INSTALLED, baseBt)
        parts.removePack(pack)
        onProgress("Installed", 100)
    }

    // ---- recovery --------------------------------------------------------------

    /**
     * Decided: every failure and every interrupted merge ends on the sample
     * base. Deletes the main database, re-extracts the sample from the APK,
     * clears the extended state and sets the target to sample. The caller
     * restarts the app.
     */
    suspend fun recoverToSample(reason: String): Boolean = withContext(NonCancellable + Dispatchers.IO) {
        Log.w(TAG, "returning to the sample database: $reason")
        PerseusDatabase.destroyInstance()
        PreferencesManager.setUseFullDatabase(context, false)
        PreferencesManager.setDbTarget(context, "sample")
        parts.clearState()
        File(context.filesDir, "packs/tmp").listFiles()?.forEach { it.delete() }
        val main = baseDb
        if (main.exists()) main.delete()
        for (suffix in listOf("-wal", "-shm", "-journal")) File(main.path + suffix).delete()
        AssetPackDatabaseHelper(context).copyDatabaseFromAssetPack(null)
    }

    // ---- helpers ------------------------------------------------------------------

    private fun fail(msg: String): Nothing = throw InstallException(msg)

    private fun readManifest(zip: File): JSONObject = ZipFile(zip).use { z ->
        val entry = z.getEntry("manifest.json") ?: fail("no manifest.json in ${zip.name}")
        JSONObject(z.getInputStream(entry).bufferedReader().readText())
    }

    private fun mergeStatements(): List<String> {
        val text = context.assets.open(MERGE_SQL_ASSET).bufferedReader().readText()
        val noComments = text.lineSequence().filterNot { it.trimStart().startsWith("--") }.joinToString("\n")
        val stmts = noComments.split(';').map { it.trim() }.filter { it.isNotEmpty() }
        if (stmts.size != 12) fail("delta_merge.sql has ${stmts.size} statements, expected 12")
        return stmts
    }

    private fun tableCounts(db: SQLiteDatabase, schema: String): Map<String, Long> {
        val names = ArrayList<String>()
        db.rawQuery("SELECT name FROM $schema.sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' AND name NOT IN ('room_master_table', 'android_metadata')", null)
            .use { c -> while (c.moveToNext()) names.add(c.getString(0)) }
        return names.associateWith { count(db, "SELECT COUNT(*) FROM $schema.$it") }
    }

    private fun count(db: SQLiteDatabase, sql: String, countRows: Boolean = false): Long =
        db.rawQuery(sql, null).use { c ->
            if (countRows) c.count.toLong() else if (c.moveToFirst()) c.getLong(0) else 0L
        }

    private fun sha256(file: File, onProgress: (Int) -> Unit): String {
        val md = MessageDigest.getInstance("SHA-256")
        val total = file.length().coerceAtLeast(1)
        var done = 0L
        file.inputStream().buffered(1 shl 20).use { input ->
            val buf = ByteArray(1 shl 20)
            var n: Int
            while (input.read(buf).also { n = it } != -1) {
                md.update(buf, 0, n)
                done += n
                onProgress(((done * 100) / total).toInt())
            }
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }

    private fun inflate(zip: File, entryName: String, dest: File, expectedBytes: Long, onProgress: (Int) -> Unit) {
        if (dest.exists()) dest.delete()
        ZipFile(zip).use { z ->
            val entry = z.getEntry(entryName) ?: fail("no $entryName in ${zip.name}")
            z.getInputStream(entry).buffered(1 shl 20).use { input ->
                dest.outputStream().buffered(1 shl 20).use { out ->
                    val buf = ByteArray(1 shl 20)
                    var n: Int
                    var done = 0L
                    while (input.read(buf).also { n = it } != -1) {
                        out.write(buf, 0, n)
                        done += n
                        if (expectedBytes > 0) onProgress(((done * 100) / expectedBytes).toInt())
                    }
                }
            }
        }
    }
}
