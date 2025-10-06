import Foundation
import SQLite3

/// Helper class for managing user-specific normalization patterns
/// Uses raw SQLite3 API and is NOT a Room entity (matches Android pattern)
/// Table is created dynamically in UserDatabaseManagerAsync
class UserNormalizationPatternHelper {

    /// Get normalization patterns for a specific language from user database
    /// - Parameters:
    ///   - language: The language code (e.g., "hebrew", "arabic")
    ///   - packageId: Optional package ID to filter by
    /// - Returns: Array of user normalization patterns sorted by priority
    func getPatternsByLanguage(_ language: String, packageId: Int? = nil) async throws -> [UserNormalizationPattern] {
        var query = """
            SELECT id, package_id, language, pattern, replacement, description, priority, created_at
            FROM normalization_patterns
            WHERE language = ?
        """

        var parameters: [Any?] = [language]

        if let pkgId = packageId {
            query += " AND package_id = ?"
            parameters.append(pkgId)
        }

        query += " ORDER BY priority DESC"

        return try await UserDatabaseManagerAsync.shared.executeQuery(query, parameters: parameters) { [self] statement in
            userNormalizationPatternFromStatement(statement)
        }
    }

    /// Get all normalization patterns for a specific package
    /// - Parameter packageId: The package ID
    /// - Returns: Array of user normalization patterns
    func getPatternsByPackageId(_ packageId: Int) async throws -> [UserNormalizationPattern] {
        let query = """
            SELECT id, package_id, language, pattern, replacement, description, priority, created_at
            FROM normalization_patterns
            WHERE package_id = ?
            ORDER BY priority DESC
        """

        return try await UserDatabaseManagerAsync.shared.executeQuery(query, parameters: [packageId]) { [self] statement in
            userNormalizationPatternFromStatement(statement)
        }
    }

    /// Insert normalization patterns into the user database
    /// - Parameter patterns: Array of patterns to insert
    func insertPatterns(_ patterns: [UserNormalizationPattern]) async throws {
        guard !patterns.isEmpty else { return }

        for pattern in patterns {
            let query = """
                INSERT INTO normalization_patterns
                (package_id, language, pattern, replacement, description, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """

            let timestamp = Int64(pattern.createdAt.timeIntervalSince1970 * 1000)

            try await UserDatabaseManagerAsync.shared.execute(
                query,
                parameters: [
                    pattern.packageId,
                    pattern.language,
                    pattern.pattern,
                    pattern.replacement,
                    pattern.description as Any?,
                    pattern.priority,
                    timestamp
                ]
            )
        }
    }

    /// Delete a specific normalization pattern
    /// - Parameter id: The pattern ID to delete
    func deletePattern(id: Int) async throws {
        let query = "DELETE FROM normalization_patterns WHERE id = ?"
        try await UserDatabaseManagerAsync.shared.execute(query, parameters: [id])
    }

    /// Delete all normalization patterns for a specific package
    /// - Parameter packageId: The package ID
    func deletePatternsForPackage(packageId: Int) async throws {
        let query = "DELETE FROM normalization_patterns WHERE package_id = ?"
        try await UserDatabaseManagerAsync.shared.execute(query, parameters: [packageId])
    }

    // MARK: - Helper Methods

    private func userNormalizationPatternFromStatement(_ statement: OpaquePointer) -> UserNormalizationPattern? {
        let id = Int(sqlite3_column_int(statement, 0))
        let pkgId = Int(sqlite3_column_int(statement, 1))

        guard let languagePtr = sqlite3_column_text(statement, 2),
              let patternPtr = sqlite3_column_text(statement, 3) else {
            return nil
        }

        let language = String(cString: languagePtr)
        let pattern = String(cString: patternPtr)

        var replacement = ""
        if let replacementPtr = sqlite3_column_text(statement, 4) {
            replacement = String(cString: replacementPtr)
        }

        var description: String?
        if let descPtr = sqlite3_column_text(statement, 5) {
            description = String(cString: descPtr)
        }

        let priority = Int(sqlite3_column_int(statement, 6))
        let createdAtTimestamp = sqlite3_column_int64(statement, 7)
        let createdAt = Date(timeIntervalSince1970: TimeInterval(createdAtTimestamp) / 1000.0)

        return UserNormalizationPattern(
            id: id,
            packageId: pkgId,
            language: language,
            pattern: pattern,
            replacement: replacement,
            description: description,
            priority: priority,
            createdAt: createdAt
        )
    }
}
