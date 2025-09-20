package com.classicsviewer.app.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "books",
    foreignKeys = [
        ForeignKey(
            entity = WorkEntity::class,
            parentColumns = ["id"],
            childColumns = ["work_id"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index(value = ["work_id"], name = "idx_books_work")]
)
data class BookEntity(
    @PrimaryKey
    val id: String,
    @ColumnInfo(name = "work_id")
    val workId: String,
    @ColumnInfo(name = "book_number")
    val bookNumber: Int,
    @ColumnInfo(name = "label")
    val label: String?,
    @ColumnInfo(name = "start_line")
    val startLine: Int?,
    @ColumnInfo(name = "end_line")
    val endLine: Int?,
    @ColumnInfo(name = "line_count")
    val lineCount: Int?
)