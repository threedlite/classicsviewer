package com.classicsviewer.app.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "normalization_patterns",
    indices = [
        Index(value = ["language"]),
        Index(value = ["package_id"]),
        Index(value = ["language", "package_id", "priority"])
    ]
)
data class NormalizationPatternEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    @ColumnInfo(name = "package_id")
    val packageId: Long,

    @ColumnInfo(name = "language")
    val language: String,

    @ColumnInfo(name = "pattern")
    val pattern: String,

    @ColumnInfo(name = "replacement")
    val replacement: String,

    @ColumnInfo(name = "description")
    val description: String?,

    @ColumnInfo(name = "priority")
    val priority: Int,

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis()
)
