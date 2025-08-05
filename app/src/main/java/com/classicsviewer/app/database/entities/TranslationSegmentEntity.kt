package com.classicsviewer.app.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "translation_segments",
    foreignKeys = [
        ForeignKey(
            entity = BookEntity::class,
            parentColumns = ["id"],
            childColumns = ["book_id"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [
        Index(value = ["book_id"], name = "idx_translation_segments_book"),
        Index(value = ["book_id", "start_line"], name = "idx_translation_segments_lines")
    ]
)
data class TranslationSegmentEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    @ColumnInfo(name = "book_id")
    val bookId: String,
    @ColumnInfo(name = "start_line")
    val startLine: Int,
    @ColumnInfo(name = "end_line")
    val endLine: Int?,
    @ColumnInfo(name = "translation_text")
    val translationText: String,
    val translator: String?
)