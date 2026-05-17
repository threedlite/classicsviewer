package com.classicsviewer.app.rhetoric

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import com.classicsviewer.app.BuildConfig
import java.io.File
import java.util.zip.ZipInputStream

/**
 * Read-only access to the bundled rhetoric reference database (rhetoric.db).
 *
 * This is deliberately separate from the Room PerseusDatabase: rhetoric.db is a
 * small standalone SQLite file with its own schema, so it cannot trigger Room
 * schema validation. Access is raw SQL only -- no Room entities, no DAOs.
 *
 * rhetoric.db.zip ships in assets/ and is extracted to the app databases dir on
 * first use, and re-extracted after an app update (version code change).
 */
class RhetoricDbHelper(private val context: Context) {

    companion object {
        private const val DB_NAME = "rhetoric.db"
        private const val ZIP_NAME = "rhetoric.db.zip"
        private const val PREFS = "rhetoric_db"
        private const val KEY_VERSION = "extracted_version"
    }

    private var db: SQLiteDatabase? = null

    private fun database(): SQLiteDatabase {
        db?.let { if (it.isOpen) return it }
        val dbFile = context.getDatabasePath(DB_NAME)
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        if (!dbFile.exists() || prefs.getInt(KEY_VERSION, -1) != BuildConfig.VERSION_CODE) {
            extractFromAssets(dbFile)
            prefs.edit().putInt(KEY_VERSION, BuildConfig.VERSION_CODE).apply()
        }
        return SQLiteDatabase.openDatabase(dbFile.path, null, SQLiteDatabase.OPEN_READONLY)
            .also { db = it }
    }

    private fun extractFromAssets(target: File) {
        target.parentFile?.mkdirs()
        context.assets.open(ZIP_NAME).buffered().use { input ->
            ZipInputStream(input).use { zip ->
                var entry = zip.nextEntry
                while (entry != null) {
                    if (entry.name == DB_NAME) {
                        target.outputStream().buffered().use { zip.copyTo(it) }
                        return
                    }
                    entry = zip.nextEntry
                }
            }
        }
        throw IllegalStateException("$DB_NAME not found inside $ZIP_NAME")
    }

    /** Sections, in display order, each with its entry count. */
    fun getSections(): List<RhetoricSection> {
        val out = ArrayList<RhetoricSection>()
        database().rawQuery(
            "SELECT s.id, s.title, COUNT(e.id) " +
                "FROM rhetoric_sections s " +
                "LEFT JOIN rhetoric_entries e ON e.section_id = s.id " +
                "GROUP BY s.id, s.title, s.sort_order " +
                "ORDER BY s.sort_order", null
        ).use { c ->
            while (c.moveToNext()) {
                out.add(RhetoricSection(c.getString(0), c.getString(1), c.getInt(2)))
            }
        }
        return out
    }

    /** Entry id + name for one section, alphabetical by name. */
    fun getEntryList(sectionId: String): List<RhetoricListItem> {
        val out = ArrayList<RhetoricListItem>()
        database().rawQuery(
            "SELECT id, name FROM rhetoric_entries " +
                "WHERE section_id = ? ORDER BY name COLLATE NOCASE", arrayOf(sectionId)
        ).use { c ->
            while (c.moveToNext()) out.add(RhetoricListItem(c.getString(0), c.getString(1)))
        }
        return out
    }

    /** A single entry, or null if the id is unknown (defensive -- see proposal sec. 4). */
    fun getEntry(id: String): RhetoricEntry? {
        database().rawQuery(
            "SELECT id, section_id, name, etymology_greek, etymology, definition, examples " +
                "FROM rhetoric_entries WHERE id = ?", arrayOf(id)
        ).use { c ->
            if (!c.moveToFirst()) return null
            return RhetoricEntry(
                id = c.getString(0),
                sectionId = c.getString(1),
                name = c.getString(2),
                etymologyGreek = c.getString(3),
                etymology = c.getString(4),
                definition = c.getString(5),
                examples = c.getString(6)
            )
        }
    }

    /** Cross-references out of an entry, joined to the target name. */
    fun getCrossRefs(fromId: String): List<RhetoricCrossRef> {
        val out = ArrayList<RhetoricCrossRef>()
        database().rawQuery(
            "SELECT cr.to_id, e.name, cr.kind, cr.note " +
                "FROM rhetoric_cross_refs cr " +
                "JOIN rhetoric_entries e ON e.id = cr.to_id " +
                "WHERE cr.from_id = ? " +
                "ORDER BY cr.kind, e.name COLLATE NOCASE", arrayOf(fromId)
        ).use { c ->
            while (c.moveToNext()) {
                out.add(RhetoricCrossRef(c.getString(0), c.getString(1),
                    c.getString(2), c.getString(3)))
            }
        }
        return out
    }

    fun close() {
        db?.let { if (it.isOpen) it.close() }
        db = null
    }
}

data class RhetoricSection(val id: String, val title: String, val entryCount: Int)

data class RhetoricListItem(val id: String, val label: String)

data class RhetoricEntry(
    val id: String,
    val sectionId: String,
    val name: String,
    val etymologyGreek: String?,
    val etymology: String?,
    val definition: String,
    val examples: String?
)

data class RhetoricCrossRef(
    val toId: String,
    val toName: String,
    val kind: String,   // "related" | "see_also"
    val note: String?
)
