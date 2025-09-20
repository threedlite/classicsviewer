package com.classicsviewer.app.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "lemma_map",
    indices = [
        Index(value = ["word_form"], name = "idx_lemma_map_word"),
        Index(value = ["word_form_normalized_ultra"], name = "idx_lemma_map_word_ultra"),
        Index(value = ["lemma"], name = "idx_lemma_map_lemma")
    ]
)
data class LemmaMapEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Int = 0,
    @ColumnInfo(name = "word_form")
    val wordForm: String,
    @ColumnInfo(name = "word_form_normalized_ultra")
    val wordFormNormalizedUltra: String?,
    val lemma: String,
    val confidence: Double = 1.0,
    val source: String? = null,
    @ColumnInfo(name = "morph_info")
    val morphInfo: String? = null
)