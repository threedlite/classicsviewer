package com.classicsviewer.app.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "text_lines",
    foreignKeys = [
        ForeignKey(
            entity = BookEntity::class,
            parentColumns = ["id"],
            childColumns = ["book_id"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [
        Index(value = ["book_id"], name = "idx_text_lines_book")
    ]
)
data class TextLineEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    @ColumnInfo(name = "book_id")
    val bookId: String,
    @ColumnInfo(name = "line_number")
    val lineNumber: Int,
    @ColumnInfo(name = "line_text")
    val lineText: String,
    @ColumnInfo(name = "line_xml")
    val lineXml: String?,
    val speaker: String?
)