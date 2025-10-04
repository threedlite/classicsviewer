package com.classicsviewer.app.utils

import android.util.Log
import com.classicsviewer.app.database.entities.NormalizationPatternEntity
import java.text.Normalizer
import java.util.concurrent.ConcurrentHashMap

/**
 * Data-driven text normalizer that applies regex patterns from the database.
 *
 * NOTE: This normalizer is NOT used for Greek or Latin.
 * - Greek uses GreekNormalizer (hardcoded)
 * - Latin has no normalization
 * - Other languages (Hebrew, Arabic, etc.) use this normalizer
 *
 * Normalization happens in two phases:
 * 1. NFD (Unicode Canonical Decomposition) - separates base chars from combining marks
 * 2. Apply custom regex patterns in priority order
 *
 * Example (Hebrew):
 *   Input: "דָּבָר" (with nikud)
 *   After NFD: "דָּבָר" (nikud separated as combining marks)
 *   After pattern [\u0591-\u05C7] → "": "דבר" (nikud removed)
 */
object PatternBasedNormalizer {
    private const val TAG = "PatternNormalizer"

    // Cache compiled regex patterns per language for performance
    private data class CompiledPattern(
        val regex: Regex,
        val replacement: String,
        val priority: Int,
        val description: String?
    )

    private val compiledCache = ConcurrentHashMap<String, List<CompiledPattern>>()

    /**
     * Normalize text using database-driven patterns for the given language.
     *
     * @param text The text to normalize
     * @param language The language code (e.g., "hebrew", "arabic") - NOT "greek" or "latin"
     * @param patterns The normalization patterns to apply (fetched from database)
     * @return Normalized text
     */
    fun normalize(text: String, language: String, patterns: List<NormalizationPatternEntity>): String {
        if (text.isEmpty()) return text

        val compiledPatterns = getCompiledPatterns(language, patterns)

        if (compiledPatterns.isEmpty()) {
            // No normalization rules for this language - return as-is
            return text
        }

        var result = text
        Log.d(TAG, "[$language] Input: '$result' (${result.length} chars)")

        // Step 1: Apply NFD normalization (separates base chars from diacritics)
        result = Normalizer.normalize(result, Normalizer.Form.NFD)
        Log.d(TAG, "[$language] After NFD: '$result' (${result.length} chars)")

        // Step 2: Apply custom regex patterns in priority order
        for ((index, compiled) in compiledPatterns.withIndex()) {
            try {
                val before = result
                result = compiled.regex.replace(result, compiled.replacement)
                if (before != result) {
                    Log.d(TAG, "[$language] Pattern ${index + 1}: '$before' -> '$result' (pattern: ${compiled.regex.pattern})")
                }
            } catch (e: Exception) {
                Log.w(TAG, "Error applying pattern '${compiled.regex.pattern}' for $language: ${e.message}")
            }
        }

        Log.d(TAG, "[$language] Final result: '$result' (${result.length} chars)")
        return result
    }

    /**
     * Convenience method that takes a single pattern (for testing)
     */
    fun normalize(text: String, language: String, pattern: NormalizationPatternEntity): String {
        return normalize(text, language, listOf(pattern))
    }

    /**
     * Get compiled regex patterns for a language, using cache for performance.
     */
    private fun getCompiledPatterns(language: String, patterns: List<NormalizationPatternEntity>): List<CompiledPattern> {
        // Create cache key from pattern contents (so cache updates if patterns change)
        val cacheKey = "$language:${patterns.size}:${patterns.hashCode()}"

        return compiledCache.getOrPut(cacheKey) {
            patterns
                .sortedBy { it.priority }  // Apply in priority order
                .mapNotNull { pattern ->
                    try {
                        CompiledPattern(
                            regex = Regex(pattern.pattern),
                            replacement = pattern.replacement,
                            priority = pattern.priority,
                            description = pattern.description
                        )
                    } catch (e: Exception) {
                        Log.w(TAG, "Failed to compile pattern '${pattern.pattern}' for $language: ${e.message}")
                        null
                    }
                }
        }
    }

    /**
     * Clear the compiled pattern cache (useful when patterns are updated)
     */
    fun clearCache() {
        compiledCache.clear()
        Log.d(TAG, "Normalization pattern cache cleared")
    }

    /**
     * Clear cache for a specific language
     */
    fun clearCache(language: String) {
        compiledCache.keys.removeIf { it.startsWith("$language:") }
        Log.d(TAG, "Normalization pattern cache cleared for $language")
    }
}
