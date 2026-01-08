import Foundation
import SQLite3

protocol WorkDAOProtocol {
    func getWorksByAuthor(authorId: String) async throws -> [Work]
    func getWork(workId: String) async throws -> Work?
    func getWorkWithBooks(workId: String) async throws -> WorkWithBooks?
    func getWorksWithTranslationStatus(authorId: String) async throws -> [(work: Work, hasTranslations: Bool)]
}

class WorkDAO: WorkDAOProtocol {
    // Use async database manager
    
    func getWorksByAuthor(authorId: String) async throws -> [Work] {
        // Direct query without parameter binding to test
        let query = """
            SELECT id, author_id, title, title_alt, title_english, type, urn, description
            FROM works
            WHERE author_id = '\(authorId)'
            ORDER BY id
        """
        
        // print("DEBUG WorkDAO: Executing query: \(query)")
        
        return try await DatabaseManagerAsync.shared.executeQuery(query) { statement in
            self.workFromStatement(statement)
        }
    }
    
    func getWork(workId: String) async throws -> Work? {
        let query = """
            SELECT id, author_id, title, title_alt, title_english, type, urn, description
            FROM works
            WHERE id = ?
        """
        
        let works = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [workId]) { statement in
            self.workFromStatement(statement)
        }
        
        return works.first
    }
    
    func getWorkWithBooks(workId: String) async throws -> WorkWithBooks? {
        // First get the work
        guard let work = try await getWork(workId: workId) else { return nil }
        
        // Then get the books
        let booksQuery = """
            SELECT id, work_id, book_number, label, start_line, end_line, line_count
            FROM books
            WHERE work_id = ?
            ORDER BY book_number
        """
        
        let books = try await DatabaseManagerAsync.shared.executeQuery(booksQuery, parameters: [workId]) { statement in
            self.bookFromStatement(statement)
        }
        
        return WorkWithBooks(work: work, books: books)
    }
    
    func getWorksWithTranslationStatus(authorId: String) async throws -> [(work: Work, hasTranslations: Bool)] {
        // Get all works for the author
        let works = try await getWorksByAuthor(authorId: authorId)
        
        // For each work, check if it has translations
        var worksWithStatus: [(work: Work, hasTranslations: Bool)] = []
        
        for work in works {
            // Query to check if any book of this work has non-interlinear translations
            let query = """
                SELECT EXISTS(
                    SELECT 1 FROM translation_segments ts
                    INNER JOIN books b ON ts.book_id = b.id
                    WHERE b.work_id = ?
                    AND ts.translation_text IS NOT NULL
                    AND LENGTH(TRIM(ts.translation_text)) > 10
                    AND (ts.translator IS NULL OR ts.translator NOT LIKE '%Interlinear%')
                )
            """

            let hasTranslations = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [work.id]) { statement in
                sqlite3_column_int(statement, 0) == 1
            }.first ?? false

            worksWithStatus.append((work: work, hasTranslations: hasTranslations))
        }
        
        return worksWithStatus
    }
    
    private func workFromStatement(_ statement: OpaquePointer) -> Work? {
        guard let idCString = sqlite3_column_text(statement, 0),
              let authorIdCString = sqlite3_column_text(statement, 1),
              let titleCString = sqlite3_column_text(statement, 2) else {
            return nil
        }
        
        let id = String(cString: idCString)
        let authorId = String(cString: authorIdCString)
        let title = String(cString: titleCString)
        
        var titleAlt: String? = nil
        if let titleAltCString = sqlite3_column_text(statement, 3) {
            titleAlt = String(cString: titleAltCString)
        }
        
        var titleEnglish: String? = nil
        if let titleEnglishCString = sqlite3_column_text(statement, 4) {
            titleEnglish = String(cString: titleEnglishCString)
        }
        
        var type: String? = nil
        if let typeCString = sqlite3_column_text(statement, 5) {
            type = String(cString: typeCString)
        }
        
        var urn: String? = nil
        if let urnCString = sqlite3_column_text(statement, 6) {
            urn = String(cString: urnCString)
        }
        
        var description: String? = nil
        if let descriptionCString = sqlite3_column_text(statement, 7) {
            description = String(cString: descriptionCString)
        }
        
        return Work(id: id, authorId: authorId, title: title, titleAlt: titleAlt, 
                   titleEnglish: titleEnglish, type: type, urn: urn, description: description)
    }
    
    private func bookFromStatement(_ statement: OpaquePointer) -> Book? {
        guard let idCString = sqlite3_column_text(statement, 0),
              let workIdCString = sqlite3_column_text(statement, 1) else {
            return nil
        }
        
        let id = String(cString: idCString)
        let workId = String(cString: workIdCString)
        let bookNumber = Int(sqlite3_column_int(statement, 2))
        
        var label: String? = nil
        if let labelCString = sqlite3_column_text(statement, 3) {
            label = String(cString: labelCString)
        }
        
        var startLine: Int? = nil
        if sqlite3_column_type(statement, 4) != SQLITE_NULL {
            startLine = Int(sqlite3_column_int(statement, 4))
        }
        
        var endLine: Int? = nil
        if sqlite3_column_type(statement, 5) != SQLITE_NULL {
            endLine = Int(sqlite3_column_int(statement, 5))
        }
        
        var lineCount: Int? = nil
        if sqlite3_column_type(statement, 6) != SQLITE_NULL {
            lineCount = Int(sqlite3_column_int(statement, 6))
        }
        
        return Book(id: id, workId: workId, bookNumber: bookNumber, label: label,
                   startLine: startLine, endLine: endLine, lineCount: lineCount)
    }
}