package com.classicsviewer.app.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index

@Entity(
    tableName = "word_forms",
    primaryKeys = ["book_id", "line_number", "word_position"],
    foreignKeys = [
        ForeignKey(
            entity = BookEntity::class,
            parentColumns = ["id"],
            childColumns = ["book_id"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [
        Index(value = ["book_id", "line_number"], name = "idx_word_forms_book_line"),
        Index(value = ["word_normalized"], name = "idx_word_forms_normalized")
    ]
)
data class WordFormEntity(
    val word: String,
    @ColumnInfo(name = "word_normalized")
    val wordNormalized: String,
    @ColumnInfo(name = "book_id")
    val bookId: String,
    @ColumnInfo(name = "line_number")
    val lineNumber: Int,
    @ColumnInfo(name = "word_position")
    val wordPosition: Int,
    @ColumnInfo(name = "char_start")
    val charStart: Int,
    @ColumnInfo(name = "char_end")
    val charEnd: Int
)