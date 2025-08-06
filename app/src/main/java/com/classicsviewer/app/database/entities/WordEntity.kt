package com.classicsviewer.app.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "words",
    foreignKeys = [
        ForeignKey(
            entity = BookEntity::class,
            parentColumns = ["id"],
            childColumns = ["book_id"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [
        Index(value = ["word_normalized"], name = "idx_words_normalized"),
        Index(value = ["book_id", "line_number"], name = "idx_words_book_line")
    ]
)
data class WordEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val word: String,
    @ColumnInfo(name = "word_normalized")
    val wordNormalized: String,
    @ColumnInfo(name = "book_id")
    val bookId: String,
    @ColumnInfo(name = "line_number")
    val lineNumber: Int,
    @ColumnInfo(name = "word_position")
    val wordPosition: Int
)