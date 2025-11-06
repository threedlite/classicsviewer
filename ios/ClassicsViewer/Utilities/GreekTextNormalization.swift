import Foundation

/// Advanced Greek text normalization utilities
/// Matches Android PerseusRepository.kt lines 1377-1427
class GreekTextNormalization {

    // MARK: - Apostrophe Normalization

    /// Normalize apostrophes for Greek text with NFC Unicode normalization
    /// CRITICAL: First normalizes Unicode to NFC (precomposed) form
    /// This converts combining accents (e.g., ε + combining acute) to precomposed characters (έ)
    /// Fixes issue where οὐδέ with combining accent doesn't match database entries
    ///
    /// Matches Android PerseusRepository.kt lines 1377-1391
    static func normalizeApostrophes(_ word: String) -> String {
        // CRITICAL: First normalize Unicode to NFC (precomposed) form
        // In Swift, this is done with precomposedStringWithCanonicalMapping
        let nfcNormalized = word.precomposedStringWithCanonicalMapping

        // Then normalize all apostrophe variants to the standard form used in the database (U+02BC)
        // This handles different apostrophe types that might come from the UI
        return nfcNormalized
            .replacingOccurrences(of: "'", with: "ʼ")  // U+0027 APOSTROPHE → U+02BC
            .replacingOccurrences(of: "'", with: "ʼ")  // U+2019 RIGHT SINGLE QUOTATION MARK → U+02BC
            .replacingOccurrences(of: "᾿", with: "ʼ")  // U+1FBF GREEK PSILI → U+02BC
            .replacingOccurrences(of: "′", with: "ʼ")  // U+2032 PRIME → U+02BC
            .replacingOccurrences(of: "´", with: "ʼ")  // U+00B4 ACUTE ACCENT → U+02BC
    }

    // MARK: - Grave Accent Detection

    /// Check if word contains any Greek grave accent characters
    /// Matches Android PerseusRepository.kt lines 1400-1408
    static func hasGraveAccent(_ word: String) -> Bool {
        // Check if word contains any Greek grave accent characters
        let graveChars: Set<Character> = [
            // Simple grave
            "ὰ", "ὲ", "ὴ", "ὶ", "ὸ", "ὺ", "ὼ",
            // With smooth breathing
            "ἂ", "ἒ", "ἢ", "ἲ", "ὂ", "ὒ", "ὢ",
            // With rough breathing
            "ἃ", "ἓ", "ἣ", "ἳ", "ὃ", "ὓ", "ὣ"
        ]
        return word.contains(where: { graveChars.contains($0) })
    }

    // MARK: - Grave to Acute Conversion

    /// Convert grave accents to acute accents
    /// Matches Android PerseusRepository.kt lines 1410-1427
    static func convertGraveToAcute(_ word: String) -> String {
        // Convert grave accents to acute accents
        let graveToAcuteMap: [Character: Character] = [
            // Simple vowels
            "ὰ": "ά", "ὲ": "έ", "ὴ": "ή", "ὶ": "ί",
            "ὸ": "ό", "ὺ": "ύ", "ὼ": "ώ",
            // With smooth breathing
            "ἂ": "ἄ", "ἒ": "ἔ", "ἢ": "ἤ", "ἲ": "ἴ",
            "ὂ": "ὄ", "ὒ": "ὔ", "ὢ": "ὤ",
            // With rough breathing
            "ἃ": "ἅ", "ἓ": "ἕ", "ἣ": "ἥ", "ἳ": "ἵ",
            "ὃ": "ὅ", "ὓ": "ὕ", "ὣ": "ὥ"
        ]

        return String(word.map { char in
            graveToAcuteMap[char] ?? char
        })
    }

    // MARK: - Combined Cleaning for Dictionary Lookup

    /// Clean and normalize Greek word for dictionary lookup
    /// Applies all normalization steps in correct order:
    /// 1. Remove punctuation (but preserve apostrophes)
    /// 2. NFC normalize and fix apostrophes
    /// 3. Optionally convert grave to acute
    ///
    /// Matches the sequence in Android PerseusRepository.kt lines 284-298
    static func prepareForDictionaryLookup(_ word: String, convertGrave: Bool = false) -> (cleaned: String, acuteVariant: String?) {
        // Clean punctuation first, but preserve apostrophes for elided forms
        var cleanedWord = word.replacingOccurrences(of: "[.,;:!?·]", with: "", options: .regularExpression)

        // Normalize apostrophes (includes NFC normalization)
        cleanedWord = normalizeApostrophes(cleanedWord)

        // Create acute accent variant if word has grave accents
        let acuteVariant: String?
        if convertGrave && hasGraveAccent(cleanedWord) {
            acuteVariant = convertGraveToAcute(cleanedWord)
        } else {
            acuteVariant = nil
        }

        return (cleaned: cleanedWord, acuteVariant: acuteVariant)
    }
}
