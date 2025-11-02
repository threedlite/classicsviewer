import Foundation

/// Result of compound word decomposition
struct CompoundParts {
    let prefix: String
    let prefixMeaning: String
    let stem: String
    let stemLemma: String?
}

/// Helper class for advanced dictionary lookup operations
/// Matches Android PerseusRepository.kt lines 1639-1781
class DictionaryLookupHelper {

    private let prefixDAO = PrefixAssimilationRuleDAO()

    // MARK: - Compound Word Decomposition

    /// Decompose a compound word using prefix assimilation rules
    /// Algorithm matches Android PerseusRepository.kt:1639-1693
    ///
    /// - Parameters:
    ///   - word: The compound word to decompose (e.g., "κατορθόω")
    ///   - language: "greek" or "latin"
    ///   - dictionaryDAO: DAO for looking up stems
    /// - Returns: CompoundParts if successfully decomposed, nil otherwise
    func decomposeCompoundWord(
        word: String,
        language: String,
        dictionaryDAO: DictionaryDAO
    ) async throws -> CompoundParts? {

        // Load prefix rules (cached)
        let prefixGroups: [PrefixGroup]
        do {
            prefixGroups = try await prefixDAO.getPrefixAssimilationRules(language: language)
        } catch {
            // If database doesn't have rules, try fallback
            return try await decomposeCompoundWordFallback(
                word: word,
                language: language,
                dictionaryDAO: dictionaryDAO
            )
        }

        // Try each prefix group and its assimilated forms
        for prefixGroup in prefixGroups {
            let basePrefix = prefixGroup.basePrefix
            let meaning = prefixGroup.meaning

            // Try each assimilated form for this prefix
            for assimilatedForm in prefixGroup.assimilatedForms {

                // Normalize both for comparison (case-insensitive, diacritic-aware)
                let normalizedWord = normalizeForComparison(word, language: language)
                let normalizedPrefix = normalizeForComparison(assimilatedForm, language: language)

                // Check if word starts with this assimilated form
                if normalizedWord.hasPrefix(normalizedPrefix) {

                    // Extract stem from ORIGINAL word (preserve diacritics)
                    let prefixLength = assimilatedForm.count
                    if prefixLength >= word.count {
                        continue  // Prefix too long
                    }

                    let stemStartIndex = word.index(word.startIndex, offsetBy: prefixLength)
                    let stem = String(word[stemStartIndex...])

                    // Stem must be long enough to be meaningful
                    if stem.count < 3 {
                        continue
                    }

                    // Try to find the stem in dictionary
                    let stemLemma = try await findStemLemma(
                        stem: stem,
                        language: language,
                        dictionaryDAO: dictionaryDAO
                    )

                    // If stem found, return the decomposition
                    if let stemLemma = stemLemma {
                        return CompoundParts(
                            prefix: basePrefix,
                            prefixMeaning: meaning,
                            stem: stem,
                            stemLemma: stemLemma
                        )
                    }

                    // If not found, try vowel restoration for Greek
                    if language.lowercased() == "greek" {
                        if let restoredStem = try await findStemWithVowelRestoration(
                            stem: stem,
                            language: language,
                            dictionaryDAO: dictionaryDAO
                        ) {
                            return CompoundParts(
                                prefix: basePrefix,
                                prefixMeaning: meaning,
                                stem: restoredStem.stem,
                                stemLemma: restoredStem.lemma
                            )
                        }
                    }
                }
            }
        }

        return nil
    }

    /// Fallback decomposition using basic Greek prefixes
    /// Matches Android PerseusRepository.kt:1698-1724
    private func decomposeCompoundWordFallback(
        word: String,
        language: String,
        dictionaryDAO: DictionaryDAO
    ) async throws -> CompoundParts? {

        // Only for Greek
        guard language.lowercased() == "greek" else {
            return nil
        }

        // Basic Greek prefixes (hardcoded fallback)
        let basicPrefixes: [(prefix: String, meaning: String)] = [
            ("κατα", "down, against"),
            ("συν", "with, together"),
            ("απο", "away from"),
            ("δια", "through"),
            ("επι", "upon, at"),
            ("εκ", "out of"),
            ("εν", "in, on")
        ]

        // Try each basic prefix
        for (prefix, meaning) in basicPrefixes {
            let normalizedWord = normalizeForComparison(word, language: language)
            let normalizedPrefix = normalizeForComparison(prefix, language: language)

            if normalizedWord.hasPrefix(normalizedPrefix) {
                let prefixLength = prefix.count
                if prefixLength >= word.count {
                    continue
                }

                let stemStartIndex = word.index(word.startIndex, offsetBy: prefixLength)
                let stem = String(word[stemStartIndex...])

                if stem.count < 3 {
                    continue
                }

                // Try to find stem
                if let stemLemma = try await findStemLemma(
                    stem: stem,
                    language: language,
                    dictionaryDAO: dictionaryDAO
                ) {
                    return CompoundParts(
                        prefix: prefix,
                        prefixMeaning: meaning,
                        stem: stem,
                        stemLemma: stemLemma
                    )
                }

                // Try vowel restoration
                if let restoredStem = try await findStemWithVowelRestoration(
                    stem: stem,
                    language: language,
                    dictionaryDAO: dictionaryDAO
                ) {
                    return CompoundParts(
                        prefix: prefix,
                        prefixMeaning: meaning,
                        stem: restoredStem.stem,
                        stemLemma: restoredStem.lemma
                    )
                }
            }
        }

        return nil
    }

    // MARK: - Stem Lookup

    /// Find dictionary entry for a stem
    /// Matches Android PerseusRepository.kt:1761-1781
    ///
    /// CRITICAL: Uses skipCompoundDecomposition=true to prevent infinite recursion
    private func findStemLemma(
        stem: String,
        language: String,
        dictionaryDAO: DictionaryDAO
    ) async throws -> String? {

        // CRITICAL: skipCompoundDecomposition = true to prevent infinite loop
        let entries = try await dictionaryDAO.getAllDictionaryEntries(
            stem,
            language: language,
            skipCompoundDecomposition: true  // ⚠️ PREVENTS INFINITE RECURSION
        )

        // Return first entry's lemma if found
        return entries.first?.lemma
    }

    // MARK: - Vowel Restoration

    /// Try to find stem by restoring initial vowels (Greek only)
    /// Matches Android PerseusRepository.kt:1730-1755
    ///
    /// Example: ρθόω → ορθόω (restore initial ο), κτωρ → ἵκτωρ (restore initial ἱ)
    private func findStemWithVowelRestoration(
        stem: String,
        language: String,
        dictionaryDAO: DictionaryDAO
    ) async throws -> (stem: String, lemma: String)? {

        guard language.lowercased() == "greek" else {
            return nil
        }

        // Greek vowels that might be missing at the start
        // Include both plain and with breathing marks (smooth ᾿ and rough ῾)
        let initialVowels = [
            "α", "ἀ", "ἁ",  // alpha with smooth/rough breathing
            "ε", "ἐ", "ἑ",  // epsilon
            "η", "ἠ", "ἡ",  // eta
            "ι", "ἰ", "ἱ",  // iota with smooth/rough breathing
            "ο", "ὀ", "ὁ",  // omicron
            "υ", "ὐ", "ὑ",  // upsilon
            "ω", "ὠ", "ὡ"   // omega
        ]

        for vowel in initialVowels {
            let restoredStem = vowel + stem

            // Try to find this restored form
            let entries = try await dictionaryDAO.getAllDictionaryEntries(
                restoredStem,
                language: language,
                skipCompoundDecomposition: true  // ⚠️ PREVENTS INFINITE RECURSION
            )

            if let firstEntry = entries.first {
                return (stem: restoredStem, lemma: firstEntry.lemma)
            }
        }

        return nil
    }

    // MARK: - Normalization Helpers

    /// Normalize text for prefix comparison
    /// Matches Android PerseusRepository.kt:148-182 behavior
    private func normalizeForComparison(_ text: String, language: String) -> String {
        if language.lowercased() == "greek" {
            // Use GreekNormalizer for Greek
            return GreekNormalizer.normalize(text)
        } else if language.lowercased() == "latin" {
            // Latin: lowercase only
            return text.lowercased()
        } else {
            // Other languages: basic lowercase
            return text.lowercased()
        }
    }
}
