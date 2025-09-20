package com.classicsviewer.app.data

data class DictionaryResultMultiple(
    val entries: List<DictionaryEntry>
)

data class DictionaryEntry(
    val lemma: String,
    val definition: String,
    val morphInfo: String? = null,
    val isDirectMatch: Boolean = false,
    val confidence: Double? = null,
    val source: String? = null,
    val hasNonTreebankPath: Boolean = true // true means it has at least one non-treebank source path
)