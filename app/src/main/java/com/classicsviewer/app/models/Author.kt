package com.classicsviewer.app.models

data class Author(
    val id: String,
    val name: String,
    val language: String,
    val hasTranslatedWorks: Boolean = false
)