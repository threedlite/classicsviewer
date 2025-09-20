package com.classicsviewer.app.database.entities

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index

@Entity(
    tableName = "translation_lookup",
    primaryKeys = ["book_id", "line_number", "segment_id"],
    foreignKeys = [
        ForeignKey(
            entity = BookEntity::class,
            parentColumns = ["id"],
            childColumns = ["book_id"],
            onDelete = ForeignKey.CASCADE
        ),
        ForeignKey(
            entity = TranslationSegmentEntity::class,
            parentColumns = ["id"],
            childColumns = ["segment_id"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [
        Index(value = ["book_id", "line_number"], name = "index_translation_lookup_book_id_line_number"),
        Index(value = ["segment_id"], name = "index_translation_lookup_segment_id")
    ]
)
data class TranslationLookupEntity(
    val book_id: String,
    val line_number: Int,
    val segment_id: Int
)