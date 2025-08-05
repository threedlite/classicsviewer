package com.classicsviewer.app.models

data class Occurrence(
    val author: String,
    val authorId: String,
    val work: String,
    val workId: String,
    val book: String,
    val bookId: String,
    val lineNumber: Int,
    val lineText: String,
    val wordForm: String,
    val language: String
)