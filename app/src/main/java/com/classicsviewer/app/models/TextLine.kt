package com.classicsviewer.app.models

data class TextLine(
    val lineNumber: Int,
    val text: String,
    val words: List<Word>,
    val speaker: String? = null
)

data class Word(
    val text: String,
    val lemma: String,
    val startOffset: Int,
    val endOffset: Int
)