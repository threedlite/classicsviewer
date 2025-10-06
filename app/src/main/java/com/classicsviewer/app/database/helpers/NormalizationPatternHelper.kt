package com.classicsviewer.app.database.helpers

import androidx.sqlite.db.SupportSQLiteDatabase
import com.classicsviewer.app.database.entities.NormalizationPatternEntity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Helper class for accessing normalization_patterns table via raw SQL.
 * This table is created dynamically and not tracked by Room to avoid version increments.
 */
class NormalizationPatternHelper(private val database: SupportSQLiteDatabase) {

    suspend fun insertAll(patterns: List<NormalizationPatternEntity>) = withContext(Dispatchers.IO) {
        database.beginTransaction()
        try {
            patterns.forEach { pattern ->
                database.execSQL(
                    """
                    INSERT OR REPLACE INTO normalization_patterns
                    (language, pattern, replacement, description, priority, package_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """.trimIndent(),
                    arrayOf(
                        pattern.language,
                        pattern.pattern,
                        pattern.replacement,
                        pattern.description,
                        pattern.priority,
                        pattern.packageId
                    )
                )
            }
            database.setTransactionSuccessful()
        } finally {
            database.endTransaction()
        }
    }

    suspend fun getPatternsForLanguage(language: String): List<NormalizationPatternEntity> =
        withContext(Dispatchers.IO) {
            val patterns = mutableListOf<NormalizationPatternEntity>()
            val cursor = database.query(
                "SELECT * FROM normalization_patterns WHERE language = ? ORDER BY priority ASC",
                arrayOf(language)
            )

            cursor.use {
                while (it.moveToNext()) {
                    patterns.add(
                        NormalizationPatternEntity(
                            id = it.getLong(it.getColumnIndexOrThrow("id")),
                            language = it.getString(it.getColumnIndexOrThrow("language")),
                            pattern = it.getString(it.getColumnIndexOrThrow("pattern")),
                            replacement = it.getString(it.getColumnIndexOrThrow("replacement")),
                            description = it.getString(it.getColumnIndexOrThrow("description")),
                            priority = it.getInt(it.getColumnIndexOrThrow("priority")),
                            packageId = it.getLong(it.getColumnIndexOrThrow("package_id"))
                        )
                    )
                }
            }
            patterns
        }

    suspend fun getPatternsForPackage(packageId: Long): List<NormalizationPatternEntity> =
        withContext(Dispatchers.IO) {
            val patterns = mutableListOf<NormalizationPatternEntity>()
            val cursor = database.query(
                "SELECT * FROM normalization_patterns WHERE package_id = ? ORDER BY language, priority ASC",
                arrayOf(packageId.toString())
            )

            cursor.use {
                while (it.moveToNext()) {
                    patterns.add(
                        NormalizationPatternEntity(
                            id = it.getLong(it.getColumnIndexOrThrow("id")),
                            language = it.getString(it.getColumnIndexOrThrow("language")),
                            pattern = it.getString(it.getColumnIndexOrThrow("pattern")),
                            replacement = it.getString(it.getColumnIndexOrThrow("replacement")),
                            description = it.getString(it.getColumnIndexOrThrow("description")),
                            priority = it.getInt(it.getColumnIndexOrThrow("priority")),
                            packageId = it.getLong(it.getColumnIndexOrThrow("package_id"))
                        )
                    )
                }
            }
            patterns
        }

    suspend fun deleteByPackageId(packageId: Long) = withContext(Dispatchers.IO) {
        database.execSQL(
            "DELETE FROM normalization_patterns WHERE package_id = ?",
            arrayOf(packageId)
        )
    }

    suspend fun countPatternsForLanguage(language: String): Int = withContext(Dispatchers.IO) {
        val cursor = database.query(
            "SELECT COUNT(*) FROM normalization_patterns WHERE language = ?",
            arrayOf(language)
        )
        cursor.use {
            if (it.moveToFirst()) {
                it.getInt(0)
            } else {
                0
            }
        }
    }

    suspend fun deleteAll() = withContext(Dispatchers.IO) {
        database.execSQL("DELETE FROM normalization_patterns")
    }
}
