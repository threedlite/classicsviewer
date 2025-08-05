package com.classicsviewer.app.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "dictionary_entries",
    indices = [
        Index(value = ["headword_normalized", "language"], name = "idx_dictionary_headword_normalized")
    ]
)
data class DictionaryEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Int = 0,
    val headword: String,
    @ColumnInfo(name = "headword_normalized")
    val headwordNormalized: String,
    val language: String,
    @ColumnInfo(name = "entry_xml")
    val entryXml: String?,
    @ColumnInfo(name = "entry_html")
    val entryHtml: String?,
    @ColumnInfo(name = "entry_plain")
    val entryPlain: String?,
    val source: String?
)