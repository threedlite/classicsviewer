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
        Index(value = ["word"], name = "idx_words_word"),
        Index(value = ["book_id", "line_number", "sequence_number"], name = "idx_words_book_line_seq")
    ]
)
data class WordEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val word: String,
    @ColumnInfo(name = "book_id")
    val bookId: String,
    @ColumnInfo(name = "line_number")
    val lineNumber: Int,
    @ColumnInfo(name = "sequence_number")
    val sequenceNumber: Int,
    @ColumnInfo(name = "word_position")
    val wordPosition: Int
)