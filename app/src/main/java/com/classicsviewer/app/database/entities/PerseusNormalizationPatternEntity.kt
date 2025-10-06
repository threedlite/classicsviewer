package com.classicsviewer.app.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * Normalization patterns bundled with the Perseus database for non-Greek/Latin languages.
 * These are read-only patterns from the lexicon ZIP files.
 */
@Entity(
    tableName = "normalization_patterns",
    indices = [
        Index(value = ["language", "priority"])
    ]
)
data class PerseusNormalizationPatternEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    @ColumnInfo(name = "language")
    val language: String,

    @ColumnInfo(name = "pattern")
    val pattern: String,

    @ColumnInfo(name = "replacement")
    val replacement: String,

    @ColumnInfo(name = "description")
    val description: String?,

    @ColumnInfo(name = "priority")
    val priority: Int
)
