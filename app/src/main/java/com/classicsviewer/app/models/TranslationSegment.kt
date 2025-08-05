package com.classicsviewer.app.models

data class TranslationSegment(
    val id: Long,
    val bookId: String,
    val startLine: Int,
    val endLine: Int?,
    val translationText: String,
    val translator: String?
)