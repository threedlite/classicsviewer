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
    val language: String,
    val matchingWords: List<WordMatch> = emptyList()
)

data class WordMatch(
    val word: String,
    val position: Int
)