import Foundation
import SQLite3

protocol UserDictionaryDAOProtocol {
    func importDictionaryPackage(metadata: [String: Any], lemmas: [[String: Any]], mappings: [[String: Any]]?, normalizationPatterns: [[String: Any]]?) async throws -> Int
    func getPackages(language: String?) async throws -> [UserDictionaryPackage]
    func getEnabledPackages(language: String) async throws -> [UserDictionaryPackage]
    func setPackageEnabled(packageId: Int, enabled: Bool) async throws
    func deletePackage(packageId: Int) async throws
    func searchUserDictionary(lemma: String, language: String) async throws -> [UserDictionaryLemma]
    func searchUserMappings(inflectedForm: String, language: String) async throws -> [String]
}

class UserDictionaryDAO: UserDictionaryDAOProtocol {
    
    func importDictionaryPackage(metadata: [String: Any], lemmas: [[String: Any]], mappings: [[String: Any]]?, normalizationPatterns: [[String: Any]]?) async throws -> Int {

        // Insert package
        let packageName = metadata["package_name"] as? String ?? "Unknown Package"
        let displayName = metadata["display_name"] as? String ?? packageName
        let description = metadata["description"] as? String
        let language = metadata["language"] as? String ?? "greek"
        let sourceInfo = metadata["source_info"] as? String
        let fileSize = metadata["file_size"] as? Int
        let lemmaCount = lemmas.count
        let importDate = Date()

        try await UserDatabaseManagerAsync.shared.execute("""
            INSERT INTO user_dictionary_packages
            (package_name, display_name, description, language, source_info, import_date, file_size, lemma_count, is_enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, parameters: [packageName, displayName, description, language, sourceInfo, importDate, fileSize, lemmaCount])

        let packageId = Int(await UserDatabaseManagerAsync.shared.getLastInsertRowId())

        // Insert lemmas
        for lemmaData in lemmas {
            let lemma = lemmaData["lemma"] as? String ?? ""
            let lemmaNormalizedUltra = lemmaData["lemma_normalized_ultra"] as? String
            let definitionPlain = lemmaData["definition_plain"] as? String ?? ""
            let definitionHtml = lemmaData["definition_html"] as? String
            let sourceName = lemmaData["source_name"] as? String ?? "User Import"
            let importFileName = lemmaData["import_file_name"] as? String ?? packageName

            try await UserDatabaseManagerAsync.shared.execute("""
                INSERT INTO user_dictionary_lemmas
                (package_id, lemma, lemma_normalized_ultra, language, definition_plain, definition_html,
                 source_name, import_file_name, import_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, parameters: [packageId, lemma, lemmaNormalizedUltra, language, definitionPlain, definitionHtml,
                            sourceName, importFileName, importDate, importDate])
        }

        // Insert mappings if provided
        if let mappings = mappings {
            for mappingData in mappings {
                let inflectedForm = mappingData["inflected_form"] as? String ?? ""
                let lemma = mappingData["lemma"] as? String ?? ""
                let source = mappingData["source"] as? String ?? "User Import"

                try await UserDatabaseManagerAsync.shared.execute("""
                    INSERT INTO user_lemma_mappings
                    (inflected_form, lemma, language, source, package_id)
                    VALUES (?, ?, ?, ?, ?)
                """, parameters: [inflectedForm, lemma, language, source, packageId])
            }
        }

        // Insert normalization patterns if provided
        if let normalizationPatterns = normalizationPatterns, !normalizationPatterns.isEmpty {
            print("UserDictionaryDAO: Importing \(normalizationPatterns.count) normalization patterns")

            let helper = UserNormalizationPatternHelper()
            let patterns = normalizationPatterns.map { patternData -> UserNormalizationPattern in
                UserNormalizationPattern(
                    id: nil,
                    packageId: packageId,
                    language: patternData["language"] as? String ?? language,
                    pattern: patternData["pattern"] as? String ?? "",
                    replacement: patternData["replacement"] as? String ?? "",
                    description: patternData["description"] as? String,
                    priority: patternData["priority"] as? Int ?? 999,
                    createdAt: importDate
                )
            }

            try await helper.insertPatterns(patterns)
            print("UserDictionaryDAO: Successfully imported \(patterns.count) normalization patterns")
        }

        return packageId
    }
    
    func getPackages(language: String?) async throws -> [UserDictionaryPackage] {
        
        var query = "SELECT * FROM user_dictionary_packages"
        var parameters: [Any?] = []
        
        if let language = language {
            query += " WHERE language = ?"
            parameters.append(language)
        }
        
        query += " ORDER BY display_name"
        
        return try await UserDatabaseManagerAsync.shared.executeQuery(query, parameters: parameters) { [self] statement in
            packageFromStatement(statement)
        }
    }
    
    func getEnabledPackages(language: String) async throws -> [UserDictionaryPackage] {
        
        let query = """
            SELECT * FROM user_dictionary_packages
            WHERE language = ? AND is_enabled = 1
            ORDER BY display_name
        """
        
        return try await UserDatabaseManagerAsync.shared.executeQuery(query, parameters: [language]) { [self] statement in
            packageFromStatement(statement)
        }
    }
    
    func setPackageEnabled(packageId: Int, enabled: Bool) async throws {
        // Database lifecycle managed by async architecture
        
        try await UserDatabaseManagerAsync.shared.execute("""
            UPDATE user_dictionary_packages
            SET is_enabled = ?
            WHERE id = ?
        """, parameters: [enabled ? 1 : 0, packageId])
    }
    
    func deletePackage(packageId: Int) async throws {
        // Database lifecycle managed by async architecture
        
        // Cascade delete will remove associated lemmas and mappings
        try await UserDatabaseManagerAsync.shared.execute("DELETE FROM user_dictionary_packages WHERE id = ?", parameters: [packageId])
    }
    
    func searchUserDictionary(lemma: String, language: String) async throws -> [UserDictionaryLemma] {
        // Database lifecycle managed by async architecture
        
        let query = """
            SELECT l.* FROM user_dictionary_lemmas l
            JOIN user_dictionary_packages p ON l.package_id = p.id
            WHERE l.language = ? 
            AND p.is_enabled = 1
            AND (l.lemma = ? OR l.lemma_normalized_ultra = ?)
            ORDER BY l.lemma
        """
        
        return try await UserDatabaseManagerAsync.shared.executeQuery(query, parameters: [language, lemma, lemma]) { [self] statement in
            lemmaFromStatement(statement)
        }
    }
    
    func searchUserMappings(inflectedForm: String, language: String) async throws -> [String] {
        // Database lifecycle managed by async architecture
        
        // Verify that the required tables exist before querying
        do {
            let tableCheckQuery = """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('user_lemma_mappings', 'user_dictionary_packages')
            """
            let existingTables = try await UserDatabaseManagerAsync.shared.executeQuery(tableCheckQuery, parameters: []) { statement in
                if let tableCString = sqlite3_column_text(statement, 0) {
                    return String(cString: tableCString)
                }
                return nil
            }.compactMap { $0 }
            
            if !existingTables.contains("user_lemma_mappings") {
                print("UserDictionaryDAO: user_lemma_mappings table does not exist, returning empty results")
                return []
            }
        } catch {
            print("UserDictionaryDAO: Failed to check table existence: \(error)")
            return []
        }
        
        // First try exact match
        var query = """
            SELECT DISTINCT m.lemma FROM user_lemma_mappings m
            LEFT JOIN user_dictionary_packages p ON m.package_id = p.id
            WHERE m.language = ?
            AND m.inflected_form = ?
            AND (p.id IS NULL OR p.is_enabled = 1)
        """
        
        var results = try await UserDatabaseManagerAsync.shared.executeQuery(query, parameters: [language, inflectedForm]) { statement in
            if let lemmaCString = sqlite3_column_text(statement, 0) {
                return String(cString: lemmaCString)
            }
            return nil
        }.compactMap { $0 }
        
        // If no exact match and it's Greek, try normalized form (only for Greek)
        if results.isEmpty && language == "greek" {
            let normalizedForm = GreekNormalizer.normalize(inflectedForm)
            if normalizedForm != inflectedForm {
                query = """
                    SELECT DISTINCT m.lemma FROM user_lemma_mappings m
                    LEFT JOIN user_dictionary_packages p ON m.package_id = p.id
                    WHERE m.language = ?
                    AND m.inflected_form = ?
                    AND (p.id IS NULL OR p.is_enabled = 1)
                """
                
                results = try await UserDatabaseManagerAsync.shared.executeQuery(query, parameters: [language, normalizedForm]) { statement in
                    if let lemmaCString = sqlite3_column_text(statement, 0) {
                        return String(cString: lemmaCString)
                    }
                    return nil
                }.compactMap { $0 }
            }
        }
        
        return results
    }
    
    private func packageFromStatement(_ statement: OpaquePointer) -> UserDictionaryPackage? {
        let id = Int(sqlite3_column_int(statement, 0))
        
        guard let packageNameCString = sqlite3_column_text(statement, 1),
              let displayNameCString = sqlite3_column_text(statement, 2),
              let languageCString = sqlite3_column_text(statement, 4) else {
            return nil
        }
        
        let packageName = String(cString: packageNameCString)
        let displayName = String(cString: displayNameCString)
        let language = String(cString: languageCString)
        
        var description: String? = nil
        if let descCString = sqlite3_column_text(statement, 3) {
            description = String(cString: descCString)
        }
        
        var sourceInfo: String? = nil
        if let sourceCString = sqlite3_column_text(statement, 5) {
            sourceInfo = String(cString: sourceCString)
        }
        
        let importDateMillis = sqlite3_column_int64(statement, 6)
        let importDate = Date(timeIntervalSince1970: Double(importDateMillis) / 1000.0)
        
        var fileSize: Int? = nil
        if sqlite3_column_type(statement, 7) != SQLITE_NULL {
            fileSize = Int(sqlite3_column_int(statement, 7))
        }
        
        var lemmaCount: Int? = nil
        if sqlite3_column_type(statement, 8) != SQLITE_NULL {
            lemmaCount = Int(sqlite3_column_int(statement, 8))
        }
        
        let isEnabled = sqlite3_column_int(statement, 9) != 0
        
        return UserDictionaryPackage(
            id: id,
            packageName: packageName,
            displayName: displayName,
            description: description,
            language: language,
            sourceInfo: sourceInfo,
            importDate: importDate,
            fileSize: fileSize,
            lemmaCount: lemmaCount,
            isEnabled: isEnabled
        )
    }
    
    private func lemmaFromStatement(_ statement: OpaquePointer) -> UserDictionaryLemma? {
        let id = Int(sqlite3_column_int(statement, 0))
        let packageId = Int(sqlite3_column_int(statement, 1))
        
        guard let lemmaCString = sqlite3_column_text(statement, 2),
              let languageCString = sqlite3_column_text(statement, 4),
              let definitionPlainCString = sqlite3_column_text(statement, 5),
              let sourceNameCString = sqlite3_column_text(statement, 7),
              let importFileNameCString = sqlite3_column_text(statement, 8) else {
            return nil
        }
        
        let lemma = String(cString: lemmaCString)
        let language = String(cString: languageCString)
        let definitionPlain = String(cString: definitionPlainCString)
        let sourceName = String(cString: sourceNameCString)
        let importFileName = String(cString: importFileNameCString)
        
        var lemmaNormalizedUltra: String? = nil
        if let ultraCString = sqlite3_column_text(statement, 3) {
            lemmaNormalizedUltra = String(cString: ultraCString)
        }
        
        var definitionHtml: String? = nil
        if let htmlCString = sqlite3_column_text(statement, 6) {
            definitionHtml = String(cString: htmlCString)
        }
        
        let importDateMillis = sqlite3_column_int64(statement, 9)
        let importDate = Date(timeIntervalSince1970: Double(importDateMillis) / 1000.0)
        
        let createdAtMillis = sqlite3_column_int64(statement, 10)
        let createdAt = Date(timeIntervalSince1970: Double(createdAtMillis) / 1000.0)
        
        return UserDictionaryLemma(
            id: id,
            packageId: packageId,
            lemma: lemma,
            lemmaNormalizedUltra: lemmaNormalizedUltra,
            language: language,
            definitionPlain: definitionPlain,
            definitionHtml: definitionHtml,
            sourceName: sourceName,
            importFileName: importFileName,
            importDate: importDate,
            createdAt: createdAt
        )
    }
}