package com.classicsviewer.app.data

data class DictionaryResult(
    val definition: String,
    val morphInfo: String? = null,
    val lemma: String? = null
)