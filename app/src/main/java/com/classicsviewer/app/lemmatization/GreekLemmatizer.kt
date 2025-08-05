package com.classicsviewer.app.lemmatization

/**
 * Basic Greek lemmatizer for dictionary lookups
 * This is a simple rule-based implementation that covers common cases
 */
class GreekLemmatizer {
    
    /**
     * Generate possible lemma forms for a Greek word
     * Returns a list of candidates ordered by likelihood
     */
    fun generateLemmaCandidates(word: String): List<String> {
        val candidates = mutableListOf<String>()
        val normalized = normalizeGreek(word)
        
        // Always include the original normalized form
        candidates.add(normalized)
        
        // Try removing common endings
        candidates.addAll(removeNounEndings(normalized))
        candidates.addAll(removeVerbEndings(normalized))
        
        // Try handling contractions
        candidates.addAll(expandContractions(normalized))
        
        // Remove duplicates while preserving order
        return candidates.distinct()
    }
    
    /**
     * Normalize Greek text for dictionary lookup
     * Removes accents and normalizes sigma
     */
    private fun normalizeGreek(text: String): String {
        return text
            .lowercase()
            // Normalize final sigma
            .replace("ς", "σ")
            // Remove acute accent
            .replace("ά", "α")
            .replace("έ", "ε")
            .replace("ή", "η")
            .replace("ί", "ι")
            .replace("ό", "ο")
            .replace("ύ", "υ")
            .replace("ώ", "ω")
            // Remove grave accent
            .replace("ὰ", "α")
            .replace("ὲ", "ε")
            .replace("ὴ", "η")
            .replace("ὶ", "ι")
            .replace("ὸ", "ο")
            .replace("ὺ", "υ")
            .replace("ὼ", "ω")
            // Remove circumflex
            .replace("ᾶ", "α")
            .replace("ῆ", "η")
            .replace("ῖ", "ι")
            .replace("ῦ", "υ")
            .replace("ῶ", "ω")
            // Remove breathing marks and other diacritics
            .replace(Regex("[᾿῾῍῎῏᾽΄΅`´'ʼ]"), "")
            // Remove iota subscript
            .replace("ᾳ", "α")
            .replace("ῃ", "η")
            .replace("ῳ", "ω")
    }
    
    private fun removeNounEndings(word: String): List<String> {
        val candidates = mutableListOf<String>()
        
        // Second declension endings (masculine/neuter)
        val secondDeclEndings = listOf(
            "οσ", "ου", "ῳ", "ον", "ε",      // singular
            "οι", "ων", "οισ", "ουσ",        // plural
            "οιν"                             // dual
        )
        
        // First declension endings
        val firstDeclEndings = listOf(
            "α", "ασ", "ᾳ", "αν",            // singular -α
            "η", "ησ", "ῃ", "ην",            // singular -η
            "αι", "ων", "αισ", "ασ"          // plural
        )
        
        // Third declension endings (common ones)
        val thirdDeclEndings = listOf(
            "σ", "οσ", "ι", "α", "ε",        // singular
            "εσ", "ων", "σι", "ασ", "α"      // plural
        )
        
        // Try removing each ending
        for (ending in secondDeclEndings + firstDeclEndings + thirdDeclEndings) {
            if (word.endsWith(ending) && word.length > ending.length + 2) {
                val stem = word.dropLast(ending.length)
                candidates.add(stem)
                
                // For second declension, try adding back -οσ
                if (ending in secondDeclEndings && !ending.endsWith("οσ")) {
                    candidates.add("${stem}οσ")
                }
                
                // For first declension, try both -α and -η forms
                if (ending in firstDeclEndings) {
                    if (!ending.endsWith("α")) candidates.add("${stem}α")
                    if (!ending.endsWith("η")) candidates.add("${stem}η")
                }
            }
        }
        
        return candidates
    }
    
    private fun removeVerbEndings(word: String): List<String> {
        val candidates = mutableListOf<String>()
        
        // Present tense endings
        val presentEndings = listOf(
            "ω", "εισ", "ει", "ομεν", "ετε", "ουσι",     // active
            "ομαι", "ῃ", "εται", "ομεθα", "εσθε", "ονται" // middle/passive
        )
        
        // Aorist endings
        val aoristEndings = listOf(
            "α", "ασ", "ε", "αμεν", "ατε", "αν",         // active
            "ον", "εσ", "ε", "ομεν", "ετε", "ον"         // active (imperfect)
        )
        
        // Contract verb endings
        val contractEndings = listOf(
            "ῶ", "εῖσ", "εῖ", "οῦμεν", "εῖτε", "οῦσι",  // -έω contracted
            "ῶ", "ᾷσ", "ᾷ", "ῶμεν", "ᾶτε", "ῶσι"        // -άω contracted
        )
        
        for (ending in presentEndings + aoristEndings + contractEndings) {
            if (word.endsWith(ending) && word.length > ending.length + 2) {
                val stem = word.dropLast(ending.length)
                candidates.add(stem)
                
                // Try adding back common verb endings
                candidates.add("${stem}ω")
                candidates.add("${stem}ειν")  // infinitive
                
                // Handle augment for past tenses
                if (stem.startsWith("ε") && stem.length > 3) {
                    val unaugmented = stem.drop(1)
                    candidates.add(unaugmented)
                    candidates.add("${unaugmented}ω")
                }
            }
        }
        
        return candidates
    }
    
    private fun expandContractions(word: String): List<String> {
        val candidates = mutableListOf<String>()
        
        // Common contractions
        val contractions = mapOf(
            "οῦ" to listOf("εου", "οου"),
            "ῶ" to listOf("εω", "αω"),
            "ᾷ" to listOf("αει", "αῃ"),
            "εῖ" to listOf("εει"),
            "οῖ" to listOf("εοι", "οοι")
        )
        
        for ((contracted, expansions) in contractions) {
            if (word.contains(contracted)) {
                for (expansion in expansions) {
                    candidates.add(word.replace(contracted, expansion))
                }
            }
        }
        
        return candidates
    }
}

/**
 * Extension function for easy use
 */
fun String.toGreekLemmas(): List<String> {
    return GreekLemmatizer().generateLemmaCandidates(this)
}