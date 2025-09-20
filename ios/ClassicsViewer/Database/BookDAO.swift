import Foundation
import SQLite3

protocol BookDAOProtocol {
    func getBooksByWork(workId: String) async throws -> [Book]
    func getBooksByAuthor(authorId: String) async throws -> [Book]
    func getBook(bookId: String) async throws -> Book?
    func getBookDisplay(bookId: String) async throws -> BookDisplay?
}

class BookDAO: BookDAOProtocol {
    // Use async database manager
    
    // Convenience method for ViewModel
    func getBooksForWork(workId: String) async throws -> [Book] {
        return try await getBooksByWork(workId: workId)
    }
    
    func getBooksByWork(workId: String) async throws -> [Book] {
        let query = """
            SELECT id, work_id, book_number, label, start_line, end_line, line_count
            FROM books
            WHERE work_id = ?
            ORDER BY book_number
        """
        
        return try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [workId]) { [self] statement in
            bookFromStatement(statement)
        }
    }
    
    func getBooksByAuthor(authorId: String) async throws -> [Book] {
        let query = """
            SELECT b.id, b.work_id, b.book_number, b.label, b.start_line, b.end_line, b.line_count
            FROM books b
            JOIN works w ON b.work_id = w.id
            WHERE w.author_id = ?
            ORDER BY w.title, b.book_number
        """
        
        return try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [authorId]) { [self] statement in
            bookFromStatement(statement)
        }
    }
    
    func getBook(bookId: String) async throws -> Book? {
        let query = """
            SELECT id, work_id, book_number, label, start_line, end_line, line_count
            FROM books
            WHERE id = ?
        """
        
        let books = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [bookId]) { [self] statement in
            bookFromStatement(statement)
        }
        
        return books.first
    }
    
    func getBookDisplay(bookId: String) async throws -> BookDisplay? {
        // Get book with work and author information joined
        let query = """
            SELECT 
                b.id, b.work_id, b.book_number, b.label, b.start_line, b.end_line, b.line_count,
                w.id, w.author_id, w.title, w.title_alt, w.title_english, w.type, w.urn, w.description,
                a.id, a.name, a.name_alt, a.language, a.has_translations
            FROM books b
            JOIN works w ON b.work_id = w.id
            JOIN authors a ON w.author_id = a.id
            WHERE b.id = ?
        """
        
        let results = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [bookId]) { [self] statement in
            bookDisplayFromStatement(statement)
        }
        
        return results.first
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
    
    private func bookDisplayFromStatement(_ statement: OpaquePointer) -> BookDisplay? {
        // Parse book fields (0-6)
        guard let book = bookFromStatement(statement) else { return nil }
        
        // Parse work fields (7-14)
        guard let workIdCString = sqlite3_column_text(statement, 7),
              let workAuthorIdCString = sqlite3_column_text(statement, 8),
              let workTitleCString = sqlite3_column_text(statement, 9) else {
            return nil
        }
        
        let work = Work(
            id: String(cString: workIdCString),
            authorId: String(cString: workAuthorIdCString),
            title: String(cString: workTitleCString),
            titleAlt: sqlite3_column_text(statement, 10).map { String(cString: $0) },
            titleEnglish: sqlite3_column_text(statement, 11).map { String(cString: $0) },
            type: sqlite3_column_text(statement, 12).map { String(cString: $0) },
            urn: sqlite3_column_text(statement, 13).map { String(cString: $0) },
            description: sqlite3_column_text(statement, 14).map { String(cString: $0) }
        )
        
        // Parse author fields (15-19)
        guard let authorIdCString = sqlite3_column_text(statement, 15),
              let authorNameCString = sqlite3_column_text(statement, 16),
              let authorLanguageCString = sqlite3_column_text(statement, 18) else {
            return nil
        }
        
        let author = Author(
            id: String(cString: authorIdCString),
            name: String(cString: authorNameCString),
            nameAlt: sqlite3_column_text(statement, 17).map { String(cString: $0) },
            language: String(cString: authorLanguageCString),
            hasTranslations: Int(sqlite3_column_int(statement, 19))
        )
        
        return BookDisplay(book: book, work: work, author: author)
    }
}