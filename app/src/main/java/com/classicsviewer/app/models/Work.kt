package com.classicsviewer.app.models

data class Work(
    val id: String,
    val title: String,
    val authorId: String,
    val language: String,
    val hasTranslation: Boolean = false
)