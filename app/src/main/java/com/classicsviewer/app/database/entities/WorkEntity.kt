package com.classicsviewer.app.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "works",
    foreignKeys = [
        ForeignKey(
            entity = AuthorEntity::class,
            parentColumns = ["id"],
            childColumns = ["author_id"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index(value = ["author_id"], name = "idx_works_author")]
)
data class WorkEntity(
    @PrimaryKey
    val id: String,
    @ColumnInfo(name = "author_id")
    val authorId: String,
    val title: String,
    @ColumnInfo(name = "title_alt")
    val titleAlt: String?,
    @ColumnInfo(name = "title_english")
    val titleEnglish: String?,
    @ColumnInfo(name = "type")
    val type: String?,
    val urn: String?,
    val description: String?
)