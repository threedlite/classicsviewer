package com.classicsviewer.app.models

data class Book(
    val id: String,
    val number: String,
    val workId: String,
    val lineCount: Int,
    val label: String? = null,
    val hasTranslation: Boolean = false
) {
    val title: String
        get() = label ?: "Book $number"
}