package com.classicsviewer.app.models

data class TextSearchResult(
    val bookId: String,
    val bookNumber: String,
    val lineNumber: Int,
    val sequenceNumber: Int,
    val lineText: String,
    val matchStartIndex: Int,
    val matchEndIndex: Int,
    val resultIndex: Int,
    val totalResults: Int
)
