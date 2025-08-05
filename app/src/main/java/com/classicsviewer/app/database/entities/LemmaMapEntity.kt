package com.classicsviewer.app.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "lemma_map",
    primaryKeys = ["word_form", "lemma"],
    indices = [
        Index(value = ["word_form"], name = "idx_lemma_map_word"),
        Index(value = ["lemma"], name = "idx_lemma_map_lemma")
    ]
)
data class LemmaMapEntity(
    @ColumnInfo(name = "word_form")
    val wordForm: String,
    @ColumnInfo(name = "word_normalized")
    val wordNormalized: String,
    val lemma: String,
    val confidence: Double? = 1.0,
    val source: String? = null,
    @ColumnInfo(name = "morph_info")
    val morphInfo: String? = null
)