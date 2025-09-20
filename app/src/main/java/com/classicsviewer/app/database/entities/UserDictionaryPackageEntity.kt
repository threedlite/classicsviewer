package com.classicsviewer.app.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "user_dictionary_packages",
    indices = [
        Index(value = ["package_name"], unique = true),
        Index(value = ["is_active"]),
        Index(value = ["import_date"])
    ]
)
data class UserDictionaryPackageEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    
    @ColumnInfo(name = "package_name")
    val packageName: String,
    
    @ColumnInfo(name = "file_name")
    val fileName: String,
    
    @ColumnInfo(name = "description")
    val description: String?,
    
    @ColumnInfo(name = "import_date")
    val importDate: Long = System.currentTimeMillis(),
    
    @ColumnInfo(name = "total_lemmas")
    val totalLemmas: Int = 0,
    
    @ColumnInfo(name = "total_mappings")
    val totalMappings: Int = 0,
    
    @ColumnInfo(name = "greek_lemmas")
    val greekLemmas: Int = 0,
    
    @ColumnInfo(name = "latin_lemmas")
    val latinLemmas: Int = 0,
    
    @ColumnInfo(name = "is_active")
    val isActive: Boolean = false,
    
    @ColumnInfo(name = "source_info")
    val sourceInfo: String? = null
)