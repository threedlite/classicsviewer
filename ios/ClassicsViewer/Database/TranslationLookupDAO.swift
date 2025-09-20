import Foundation
import SQLite3

protocol TranslationLookupDAOProtocol {
    func getTranslationSegmentIds(bookId: String, lineNumber: Int) async throws -> [Int]
    func getTranslationLookups(bookId: String, startLine: Int, endLine: Int) async throws -> [TranslationLookup]
    func hasTranslationLookup(bookId: String) async throws -> Bool
    func getLineRangeForSegment(bookId: String, segmentId: Int) async throws -> (minLine: Int, maxLine: Int)?
}

class TranslationLookupDAO: TranslationLookupDAOProtocol {
    // Use async database manager
    
    /// Get all translation segment IDs for a specific line
    func getTranslationSegmentIds(bookId: String, lineNumber: Int) async throws -> [Int] {
        let query = """
            SELECT DISTINCT segment_id 
            FROM translation_lookup 
            WHERE book_id = ? AND line_number = ?
            ORDER BY segment_id
        """
        
        return try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [bookId, lineNumber]) { statement in
            Int(sqlite3_column_int(statement, 0))
        }
    }
    
    /// Get all translation lookups for a line range
    func getTranslationLookups(bookId: String, startLine: Int, endLine: Int) async throws -> [TranslationLookup] {
        let query = """
            SELECT book_id, line_number, segment_id
            FROM translation_lookup
            WHERE book_id = ? AND line_number BETWEEN ? AND ?
            ORDER BY line_number, segment_id
        """
        
        return try await DatabaseManagerAsync.shared.executeQuery(
            query, 
            parameters: [bookId, startLine, endLine]
        ) { statement in
            self.lookupFromStatement(statement)
        }.compactMap { $0 }
    }
    
    /// Check if a book has any translation lookup entries
    func hasTranslationLookup(bookId: String) async throws -> Bool {
        let query = """
            SELECT EXISTS(
                SELECT 1 FROM translation_lookup 
                WHERE book_id = ? 
                LIMIT 1
            )
        """
        
        let results = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [bookId]) { statement in
            sqlite3_column_int(statement, 0) == 1
        }
        
        return results.first ?? false
    }
    
    /// Get the line range that a specific segment covers
    func getLineRangeForSegment(bookId: String, segmentId: Int) async throws -> (minLine: Int, maxLine: Int)? {
        let query = """
            SELECT MIN(line_number) as min_line, MAX(line_number) as max_line
            FROM translation_lookup
            WHERE book_id = ? AND segment_id = ?
        """
        
        let results = try await DatabaseManagerAsync.shared.executeQuery(
            query,
            parameters: [bookId, segmentId]
        ) { statement in
            if sqlite3_column_type(statement, 0) != SQLITE_NULL {
                let minLine = Int(sqlite3_column_int(statement, 0))
                let maxLine = Int(sqlite3_column_int(statement, 1))
                return (minLine: minLine, maxLine: maxLine)
            }
            return nil
        }
        
        return results.first ?? nil
    }
    
    private func lookupFromStatement(_ statement: OpaquePointer) -> TranslationLookup? {
        guard let bookIdCString = sqlite3_column_text(statement, 0) else {
            return nil
        }
        
        let bookId = String(cString: bookIdCString)
        let lineNumber = Int(sqlite3_column_int(statement, 1))
        let segmentId = Int(sqlite3_column_int(statement, 2))
        
        return TranslationLookup(
            bookId: bookId,
            lineNumber: lineNumber,
            segmentId: segmentId
        )
    }
}