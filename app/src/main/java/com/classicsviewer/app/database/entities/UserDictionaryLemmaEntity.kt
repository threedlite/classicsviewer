package com.classicsviewer.app.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "user_dictionary_lemmas",
    indices = [
        Index(value = ["lemma", "language", "package_id"]),
        Index(value = ["lemma_normalized_ultra", "language", "package_id"]),
        Index(value = ["package_id"]),
        Index(value = ["import_file_name"]),
        Index(value = ["created_at"])
    ]
)
data class UserDictionaryLemmaEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    
    @ColumnInfo(name = "package_id")
    val packageId: Long,
    
    @ColumnInfo(name = "lemma")
    val lemma: String,
    
    @ColumnInfo(name = "lemma_normalized_ultra")
    val lemmaNormalizedUltra: String?,
    
    @ColumnInfo(name = "language")
    val language: String,
    
    @ColumnInfo(name = "definition_plain")
    val definitionPlain: String,
    
    @ColumnInfo(name = "definition_html")
    val definitionHtml: String? = null,
    
    @ColumnInfo(name = "source_name")
    val sourceName: String = "User Import",
    
    @ColumnInfo(name = "import_file_name")
    val importFileName: String,
    
    @ColumnInfo(name = "import_date")
    val importDate: Long,
    
    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis()
)