package com.classicsviewer.app.database.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "bookmarks",
    indices = [
        Index(value = ["book_id", "line_number"], unique = true),
        Index(value = ["created_at"]),
        Index(value = ["last_accessed"])
    ]
)
data class BookmarkEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    
    @ColumnInfo(name = "work_id")
    val workId: String,
    
    @ColumnInfo(name = "book_id")
    val bookId: String,
    
    @ColumnInfo(name = "line_number")
    val lineNumber: Int,
    
    @ColumnInfo(name = "author_name")
    val authorName: String,
    
    @ColumnInfo(name = "work_title")
    val workTitle: String,
    
    @ColumnInfo(name = "book_label")
    val bookLabel: String?,
    
    @ColumnInfo(name = "line_text")
    val lineText: String,
    
    @ColumnInfo(name = "note")
    val note: String? = null,
    
    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis(),
    
    @ColumnInfo(name = "last_accessed")
    val lastAccessed: Long = System.currentTimeMillis()
)