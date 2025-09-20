import Foundation

// Comprehensive Greek normalization matching Android implementation
struct GreekNormalizer {
    /// Normalizes Greek text by removing all diacritics and normalizing sigma
    /// Matches the Android implementation using NFD decomposition
    static func normalize(_ text: String) -> String {
        // Remove punctuation first (including all Greek apostrophe/elision variants)
        // U+0027 apostrophe, U+2019 right single quote, U+02BC modifier apostrophe
        // U+1FBD Greek koronis, U+0313 combining comma above, U+1FBF Greek psili
        var noPunctuation = text.replacingOccurrences(of: "[,;.·:!?]", with: "", options: .regularExpression)
        
        // Remove all apostrophe and elision mark variants
        noPunctuation = noPunctuation
            .replacingOccurrences(of: "'", with: "")    // U+0027 apostrophe
            .replacingOccurrences(of: "'", with: "")    // U+2019 right single quote
            .replacingOccurrences(of: "ʼ", with: "")    // U+02BC modifier letter apostrophe
            .replacingOccurrences(of: "᾽", with: "")    // U+1FBD Greek koronis
            .replacingOccurrences(of: "̓", with: "")     // U+0313 combining comma above
            .replacingOccurrences(of: "᾿", with: "")    // U+1FBF Greek psili
        
        // Normalize to NFD (decomposed form) to separate base characters from diacritics
        // This separates characters like ά into α + combining acute accent
        let nfd = noPunctuation.decomposedStringWithCanonicalMapping
        
        // Remove all combining marks (diacritics)
        // This removes accents, breathings, iota subscripts, etc.
        let withoutDiacritics = nfd.unicodeScalars.filter { scalar in
            // Keep only if NOT a combining mark
            let category = CharacterSet.nonBaseCharacters
            return !category.contains(scalar)
        }.map { Character($0) }
        
        let result = String(withoutDiacritics)
        
        // Convert to lowercase
        let lowercased = result.lowercased()
        
        // Replace final sigma with regular sigma
        let normalizedSigma = lowercased.replacingOccurrences(of: "ς", with: "σ")
        
        // Keep only Greek letters (remove any remaining non-letter characters)
        let onlyGreek = normalizedSigma.unicodeScalars.filter { scalar in
            // Greek Unicode ranges: Basic Greek (0370-03FF) and Extended Greek (1F00-1FFF)
            let isGreekLetter = (0x0370...0x03FF).contains(scalar.value) || 
                               (0x1F00...0x1FFF).contains(scalar.value)
            return isGreekLetter && CharacterSet.letters.contains(scalar)
        }.map { Character($0) }
        
        return String(onlyGreek)
    }
    
    /// Alternative simpler normalization for display purposes (keeps more structure)
    static func normalizeForDisplay(_ text: String) -> String {
        // This version keeps word boundaries and some structure
        let noPunctuation = text.replacingOccurrences(of: "[,;.·:!?]", with: "", options: .regularExpression)
        
        // NFD decomposition
        let nfd = noPunctuation.decomposedStringWithCanonicalMapping
        
        // Remove combining marks
        let withoutDiacritics = nfd.unicodeScalars.filter { scalar in
            !CharacterSet.nonBaseCharacters.contains(scalar)
        }.map { Character($0) }
        
        return String(withoutDiacritics)
            .lowercased()
            .replacingOccurrences(of: "ς", with: "σ")
    }
    
    /// Check if a character is a Greek letter
    static func isGreekLetter(_ char: Character) -> Bool {
        guard let scalar = char.unicodeScalars.first else { return false }
        return (0x0370...0x03FF).contains(scalar.value) || 
               (0x1F00...0x1FFF).contains(scalar.value)
    }
}

class TextNormalization {
    
    // MARK: - Word Normalization (matching Android)
    
    static func normalizeWord(_ word: String, isGreek: Bool) -> String {
        // Remove punctuation
        var normalized = word.replacingOccurrences(
            of: "[.,;:!?·]", 
            with: "", 
            options: .regularExpression
        )
        
        if isGreek {
            // For Greek: NFD normalization, remove diacriticals, lowercase, fix final sigma
            normalized = normalized.decomposedStringWithCanonicalMapping
            
            // Remove all diacritical marks
            normalized = normalized.replacingOccurrences(
                of: "[\\u{0300}-\\u{036f}]", 
                with: "", 
                options: .regularExpression
            )
            
            // Lowercase
            normalized = normalized.lowercased()
            
            // Replace final sigma (ς) with regular sigma (σ)
            normalized = normalized.replacingOccurrences(of: "ς", with: "σ")
            
            // Keep only Greek letters (removes apostrophes, etc.)
            normalized = normalized.replacingOccurrences(
                of: "[^α-ωΑ-Ω]", 
                with: "", 
                options: .regularExpression
            )
        } else {
            // For Latin: just lowercase and remove non-letters
            normalized = normalized.lowercased()
            normalized = normalized.replacingOccurrences(
                of: "[^a-zA-Z]", 
                with: "", 
                options: .regularExpression
            )
        }
        
        return normalized
    }
    
    // MARK: - Morphological Code Formatting (matching Android)
    
    static func formatMorphologicalCode(_ code: String) -> String {
        // Split by underscore and process each part
        let parts = code.split(separator: "_").map(String.init)
        var formatted: [String] = []
        
        for part in parts {
            switch part {
            // Tense
            case "pres": formatted.append("present")
            case "imperf": formatted.append("imperfect")
            case "fut": formatted.append("future")
            case "aor": formatted.append("aorist")
            case "perf": formatted.append("perfect")
            case "plup": formatted.append("pluperfect")
            
            // Voice
            case "act": formatted.append("active")
            case "mid": formatted.append("middle")
            case "pass": formatted.append("passive")
            case "mp": formatted.append("middle/passive")
            
            // Mood
            case "ind": formatted.append("indicative")
            case "subj": formatted.append("subjunctive")
            case "opt": formatted.append("optative")
            case "imp": formatted.append("imperative")
            case "inf": formatted.append("infinitive")
            case "part": formatted.append("participle")
            
            // Person
            case "1": formatted.append("1st person")
            case "2": formatted.append("2nd person")
            case "3": formatted.append("3rd person")
            
            // Number
            case "s": formatted.append("singular")
            case "d": formatted.append("dual")
            case "p": formatted.append("plural")
            
            // Gender
            case "m": formatted.append("masculine")
            case "f": formatted.append("feminine")
            case "n": formatted.append("neuter")
            
            // Case
            case "nom": formatted.append("nominative")
            case "gen": formatted.append("genitive")
            case "dat": formatted.append("dative")
            case "acc": formatted.append("accusative")
            case "voc": formatted.append("vocative")
            
            // Other
            case "comp": formatted.append("comparative")
            case "super": formatted.append("superlative")
            
            default:
                // Keep unrecognized parts as-is
                formatted.append(part)
            }
        }
        
        return formatted.joined(separator: " ")
    }
    
    // MARK: - Dictionary Entry Formatting
    
    static func formatDictionaryEntry(
        word: String,
        lemma: String,
        definition: String?,
        morphInfo: String?,
        confidence: Double?
    ) -> AttributedString {
        var result = AttributedString()
        
        // If lemma differs from word, show "Dictionary form:"
        if lemma != word {
            var dictForm = AttributedString("Dictionary form: ")
            dictForm.font = .caption
            dictForm.foregroundColor = .secondary
            result.append(dictForm)
            
            var lemmaText = AttributedString(lemma)
            lemmaText.font = .headline
            lemmaText.foregroundColor = .primary
            result.append(lemmaText)
            
            result.append(AttributedString("\n"))
        }
        
        // Add morphological information if present
        if let morphInfo = morphInfo, !morphInfo.isEmpty {
            let formatted = formatMorphologicalCode(morphInfo)
            var morphText = AttributedString("(\(formatted))")
            morphText.font = .caption
            morphText.foregroundColor = .secondary
            result.append(morphText)
            result.append(AttributedString("\n\n"))
        }
        
        // Add definition
        if let definition = definition, !definition.isEmpty {
            var defText = AttributedString(definition)
            defText.font = .body
            result.append(defText)
        } else {
            var noDefText = AttributedString("No definition found")
            noDefText.font = .body.italic()
            noDefText.foregroundColor = .secondary
            result.append(noDefText)
        }
        
        // Add confidence if less than 100%
        if let confidence = confidence, confidence < 1.0 {
            result.append(AttributedString("\n\n"))
            var confText = AttributedString("Confidence: \(Int(confidence * 100))%")
            confText.font = .caption2
            confText.foregroundColor = .secondary
            result.append(confText)
        }
        
        return result
    }
}