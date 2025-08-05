package com.classicsviewer.app.utils

import java.text.Normalizer

object GreekNormalizer {
    fun normalize(text: String): String {
        // Normalize to NFD (decomposed form) to separate base characters from diacritics
        val nfd = Normalizer.normalize(text, Normalizer.Form.NFD)
        
        // Remove diacritical marks
        val withoutDiacritics = nfd.replace(Regex("\\p{Mn}"), "")
        
        // Convert to lowercase
        val lowercased = withoutDiacritics.lowercase()
        
        // Replace final sigma with regular sigma
        return lowercased.replace('ς', 'σ')
    }
}