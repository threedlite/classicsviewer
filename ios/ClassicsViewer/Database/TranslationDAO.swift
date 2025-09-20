import Foundation
import SQLite3

protocol TranslationDAOProtocol {
    func getTranslations(bookId: String, startLine: Int, endLine: Int) async throws -> [TranslationSegment]
    func getTranslationsByTranslator(bookId: String, translator: String, startLine: Int, endLine: Int) async throws -> [TranslationSegment]
    func getAvailableTranslators(bookId: String) async throws -> [String]
    func hasTranslations(bookId: String) async throws -> Bool
}

class TranslationDAO: TranslationDAOProtocol {
    // Use async database manager
    
    func hasTranslations(bookId: String) async throws -> Bool {
        let query = "SELECT COUNT(*) FROM translation_segments WHERE book_id = ? LIMIT 1"
        
        let results = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [bookId]) { statement in
            let count = sqlite3_column_int(statement, 0)
            print("DEBUG TranslationDAO: Book \(bookId) has \(count) translations")
            return count > 0
        }
        
        let hasTranslations = results.first ?? false
        print("DEBUG TranslationDAO: Returning hasTranslations = \(hasTranslations) for book \(bookId)")
        return hasTranslations
    }
    
    func getTranslations(bookId: String, startLine: Int, endLine: Int) async throws -> [TranslationSegment] {
        // Get available translators first
        let translators = try await getAvailableTranslators(bookId: bookId)
        
        // If there's only one or no translators, return all translations
        if translators.count <= 1 {
            return try await getAllTranslations(bookId: bookId, startLine: startLine, endLine: endLine)
        }
        
        // If multiple translators, use the first one by default
        // This matches Android behavior of selecting one translator
        if let firstTranslator = translators.first {
            return try await getTranslationsByTranslator(
                bookId: bookId,
                translator: firstTranslator,
                startLine: startLine,
                endLine: endLine
            )
        }
        
        return []
    }
    
    private func getAllTranslations(bookId: String, startLine: Int, endLine: Int) async throws -> [TranslationSegment] {
        let query = """
            SELECT DISTINCT ts.id, ts.book_id, ts.start_line, ts.end_line, 
                   ts.translation_text, ts.translator, ts.speaker
            FROM translation_segments ts
            WHERE ts.book_id = ?
            AND (
                (ts.start_line <= ? AND (ts.end_line IS NULL OR ts.end_line >= ?))
                OR
                EXISTS (
                    SELECT 1 FROM translation_lookup tl
                    WHERE tl.book_id = ?
                    AND tl.segment_id = ts.id
                    AND tl.line_number BETWEEN ? AND ?
                )
            )
            ORDER BY ts.start_line
        """
        
        let results = try await DatabaseManagerAsync.shared.executeQuery(
            query,
            parameters: [bookId, endLine, startLine, bookId, startLine, endLine]
        ) { statement in
            self.translationFromStatement(statement)
        }
        
        // Debug logging for translation alignment
        if results.isEmpty {
            print("DEBUG TranslationDAO: No translations found for \(bookId) lines \(startLine)-\(endLine)")
            print("DEBUG TranslationDAO: Checking if lookup table exists...")
            
            // Check if there's a lookup table for this book
            let lookupCheckQuery = "SELECT COUNT(*) FROM translation_lookup WHERE book_id = ? LIMIT 1"
            let lookupCount = try await DatabaseManagerAsync.shared.executeQuery(lookupCheckQuery, parameters: [bookId]) { statement in
                Int(sqlite3_column_int(statement, 0))
            }.first ?? 0
            
            print("DEBUG TranslationDAO: Lookup table entries for \(bookId): \(lookupCount)")
        } else {
            print("DEBUG TranslationDAO: Found \(results.count) translations for \(bookId) lines \(startLine)-\(endLine)")
        }
        
        return results
    }
    
    func getTranslationsByTranslator(bookId: String, translator: String, startLine: Int, endLine: Int) async throws -> [TranslationSegment] {
        let query = """
            SELECT DISTINCT ts.id, ts.book_id, ts.start_line, ts.end_line, 
                   ts.translation_text, ts.translator, ts.speaker
            FROM translation_segments ts
            WHERE ts.book_id = ?
            AND ts.translator = ?
            AND (
                (ts.start_line <= ? AND (ts.end_line IS NULL OR ts.end_line >= ?))
                OR
                EXISTS (
                    SELECT 1 FROM translation_lookup tl
                    WHERE tl.book_id = ?
                    AND tl.segment_id = ts.id
                    AND tl.line_number BETWEEN ? AND ?
                )
            )
            ORDER BY ts.start_line
        """
        
        return try await DatabaseManagerAsync.shared.executeQuery(
            query,
            parameters: [bookId, translator, endLine, startLine, bookId, startLine, endLine]
        ) { statement in
            self.translationFromStatement(statement)
        }
    }
    
    func getAvailableTranslators(bookId: String) async throws -> [String] {
        let query = """
            SELECT DISTINCT translator 
            FROM translation_segments 
            WHERE book_id = ? 
            AND translator IS NOT NULL 
            ORDER BY translator
        """
        
        return try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [bookId]) { statement in
            if let translatorCString = sqlite3_column_text(statement, 0) {
                return String(cString: translatorCString)
            }
            return nil
        }.compactMap { $0 }
    }
    
    private func translationFromStatement(_ statement: OpaquePointer) -> TranslationSegment? {
        let id = Int(sqlite3_column_int(statement, 0))
        
        guard let bookIdCString = sqlite3_column_text(statement, 1),
              let translationTextCString = sqlite3_column_text(statement, 4) else {
            return nil
        }
        
        let bookId = String(cString: bookIdCString)
        let startLine = Int(sqlite3_column_int(statement, 2))
        let translationText = String(cString: translationTextCString)
        
        var endLine: Int? = nil
        if sqlite3_column_type(statement, 3) != SQLITE_NULL {
            endLine = Int(sqlite3_column_int(statement, 3))
        }
        
        var translator: String? = nil
        if let translatorCString = sqlite3_column_text(statement, 5) {
            translator = String(cString: translatorCString)
        }
        
        var speaker: String? = nil
        if let speakerCString = sqlite3_column_text(statement, 6) {
            speaker = String(cString: speakerCString)
        }
        
        return TranslationSegment(
            id: id,
            bookId: bookId,
            startLine: startLine,
            endLine: endLine,
            translationText: translationText,
            translator: translator,
            speaker: speaker
        )
    }
}