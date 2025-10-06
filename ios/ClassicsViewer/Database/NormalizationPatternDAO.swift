import Foundation
import SQLite3

/// DAO for reading normalization patterns from the Perseus database
/// Uses raw SQLite3 API to match iOS project patterns
class NormalizationPatternDAO {

    /// Get all normalization patterns for a specific language
    /// - Parameter lang: The language code (e.g., "hebrew", "arabic", "sanskrit")
    /// - Returns: Array of normalization patterns sorted by priority (highest first)
    func getPatternsByLanguage(_ lang: String) async throws -> [NormalizationPattern] {
        let query = """
            SELECT id, language, pattern, replacement, description, priority
            FROM normalization_patterns
            WHERE language = ?
            ORDER BY priority DESC
        """

        return try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [lang]) { [self] statement in
            normalizationPatternFromStatement(statement)
        }
    }

    /// Get all normalization patterns from the database
    /// - Returns: Array of all normalization patterns sorted by language then priority
    func getAllPatterns() async throws -> [NormalizationPattern] {
        let query = """
            SELECT id, language, pattern, replacement, description, priority
            FROM normalization_patterns
            ORDER BY language, priority DESC
        """

        return try await DatabaseManagerAsync.shared.executeQuery(query, parameters: []) { [self] statement in
            normalizationPatternFromStatement(statement)
        }
    }

    /// Check if patterns exist for a given language
    /// - Parameter lang: The language code
    /// - Returns: True if at least one pattern exists for the language
    func hasPatterns(for lang: String) async throws -> Bool {
        let query = """
            SELECT COUNT(*) FROM normalization_patterns WHERE language = ?
        """

        let counts = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [lang]) { statement in
            Int(sqlite3_column_int(statement, 0))
        }

        return (counts.first ?? 0) > 0
    }

    /// Get list of all languages that have normalization patterns
    /// - Returns: Array of language codes
    func getAvailableLanguages() async throws -> [String] {
        let query = """
            SELECT DISTINCT language FROM normalization_patterns ORDER BY language
        """

        return try await DatabaseManagerAsync.shared.executeQuery(query, parameters: []) { statement in
            String(cString: sqlite3_column_text(statement, 0))
        }
    }

    // MARK: - Helper Methods

    private func normalizationPatternFromStatement(_ statement: OpaquePointer) -> NormalizationPattern? {
        let id = Int(sqlite3_column_int(statement, 0))

        guard let languagePtr = sqlite3_column_text(statement, 1),
              let patternPtr = sqlite3_column_text(statement, 2) else {
            return nil
        }

        let language = String(cString: languagePtr)
        let pattern = String(cString: patternPtr)

        var replacement = ""
        if let replacementPtr = sqlite3_column_text(statement, 3) {
            replacement = String(cString: replacementPtr)
        }

        var description: String?
        if let descPtr = sqlite3_column_text(statement, 4) {
            description = String(cString: descPtr)
        }

        let priority = Int(sqlite3_column_int(statement, 5))

        return NormalizationPattern(
            id: id,
            language: language,
            pattern: pattern,
            replacement: replacement,
            description: description,
            priority: priority
        )
    }
}
