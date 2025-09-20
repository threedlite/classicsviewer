package com.classicsviewer.app.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "morphological_forms",
    indices = [
        Index(value = ["word_normalized"], name = "idx_morphological_word_normalized"),
        Index(value = ["lemma"], name = "idx_morphological_lemma"),
        Index(value = ["word_form"], name = "idx_morphological_word_form")
    ]
)
data class MorphologicalFormEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Int = 0,
    @ColumnInfo(name = "word_form")
    val wordForm: String,
    @ColumnInfo(name = "word_normalized")
    val wordNormalized: String,
    val lemma: String,
    val morphology: String,
    @ColumnInfo(name = "morphology_type")
    val morphologyType: String? = null,
    val source: String? = null
)