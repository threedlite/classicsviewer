import Foundation

/// Data-driven text normalizer that applies regex patterns from database
/// Used for non-Greek/Latin languages (Hebrew, Arabic, Sanskrit, etc.)
/// Two-phase normalization: NFD decomposition + regex pattern application
class PatternBasedNormalizer {

    /// Compiled regex pattern with priority for sorting
    private struct CompiledPattern {
        let regex: NSRegularExpression
        let replacement: String
        let priority: Int
    }

    /// Cache of compiled patterns by language to avoid recompiling
    private static var patternCache: [String: [CompiledPattern]] = [:]
    private static let cacheLock = NSLock()

    /// Normalize text using database-driven regex patterns
    /// - Parameters:
    ///   - text: The text to normalize
    ///   - language: The language code (e.g., "hebrew", "arabic")
    ///   - patterns: Array of normalization patterns from database
    /// - Returns: Normalized text with patterns applied
    static func normalize(_ text: String, language: String, patterns: [NormalizationPattern]) -> String {
        guard !patterns.isEmpty else {
            return text.lowercased()
        }

        // Phase 1: NFD normalization (Unicode Canonical Decomposition)
        // This separates base characters from diacritics
        var result = text.decomposedStringWithCanonicalMapping

        // Phase 2: Apply regex patterns in priority order (highest priority first)
        let compiledPatterns = getCompiledPatterns(for: language, patterns: patterns)

        for compiled in compiledPatterns {
            let range = NSRange(result.startIndex..., in: result)
            result = compiled.regex.stringByReplacingMatches(
                in: result,
                options: [],
                range: range,
                withTemplate: compiled.replacement
            )
        }

        return result
    }

    /// Get compiled regex patterns from cache or compile them
    /// - Parameters:
    ///   - language: The language code for cache key
    ///   - patterns: The patterns to compile
    /// - Returns: Array of compiled patterns sorted by priority
    private static func getCompiledPatterns(for language: String, patterns: [NormalizationPattern]) -> [CompiledPattern] {
        cacheLock.lock()
        defer { cacheLock.unlock() }

        // Check cache first
        if let cached = patternCache[language] {
            return cached
        }

        // Compile patterns
        var compiled: [CompiledPattern] = []

        for pattern in patterns {
            do {
                let regex = try NSRegularExpression(pattern: pattern.pattern, options: [])
                compiled.append(CompiledPattern(
                    regex: regex,
                    replacement: pattern.replacement,
                    priority: pattern.priority
                ))
            } catch {
                print("Warning: Failed to compile regex pattern '\(pattern.pattern)' for \(language): \(error)")
                continue
            }
        }

        // Sort by priority (lowest number first - matches Android)
        compiled.sort { $0.priority < $1.priority }

        // Cache the compiled patterns
        patternCache[language] = compiled

        return compiled
    }

    /// Clear the pattern cache (useful when patterns are updated)
    /// - Parameter language: Optional language to clear, or nil to clear all
    static func clearCache(for language: String? = nil) {
        cacheLock.lock()
        defer { cacheLock.unlock() }

        if let lang = language {
            patternCache.removeValue(forKey: lang)
        } else {
            patternCache.removeAll()
        }
    }

    /// Normalize text using user-defined patterns (converts UserNormalizationPattern to NormalizationPattern)
    /// - Parameters:
    ///   - text: The text to normalize
    ///   - language: The language code
    ///   - userPatterns: Array of user normalization patterns
    /// - Returns: Normalized text
    static func normalize(_ text: String, language: String, userPatterns: [UserNormalizationPattern]) -> String {
        // Convert UserNormalizationPattern to NormalizationPattern
        let patterns = userPatterns.map { userPattern in
            NormalizationPattern(
                id: userPattern.id,
                language: userPattern.language,
                pattern: userPattern.pattern,
                replacement: userPattern.replacement,
                description: userPattern.description,
                priority: userPattern.priority
            )
        }

        return normalize(text, language: language, patterns: patterns)
    }
}
