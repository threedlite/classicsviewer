package com.classicsviewer.app.data

data class DictionaryResultMultiple(
    val entries: List<DictionaryEntry>
)

data class DictionaryEntry(
    val lemma: String,
    val definition: String,
    val morphInfo: String? = null,
    val isDirectMatch: Boolean = false,
    val confidence: Double? = null
)