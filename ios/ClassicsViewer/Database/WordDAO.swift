import Foundation
import SQLite3

protocol WordDAOProtocol {
    func searchWords(query: String, bookId: String?, normalized: Bool) async throws -> [WordOccurrence]
    func getWordsAtPositions(bookId: String, lineNumber: Int, positions: [Int]) async throws -> [Word]
}

class WordDAO: WordDAOProtocol {
    // Use async database manager

    func searchWords(query: String, bookId: String?, normalized: Bool) async throws -> [WordOccurrence] {
        var queryString = """
            SELECT DISTINCT
                w.word as word,
                w.book_id,
                bk.label,
                COALESCE(wo.title_english, wo.title) as work_title,
                a.name as author_name,
                w.line_number,
                tl.line_text,
                GROUP_CONCAT(w.word_position) as positions,
                a.language
            FROM words w
            JOIN books bk ON w.book_id = bk.id
            JOIN works wo ON bk.work_id = wo.id
            JOIN authors a ON wo.author_id = a.id
            JOIN text_lines tl ON w.book_id = tl.book_id AND w.line_number = tl.line_number
            WHERE w.word LIKE ?
        """

        var parameters: [Any?] = ["%\(query)%"]

        if let bookId = bookId {
            queryString += " AND w.book_id = ?"
            parameters.append(bookId)
        }

        queryString += """
            GROUP BY w.book_id, w.line_number, w.word
            ORDER BY a.name, COALESCE(wo.title_english, wo.title), bk.book_number, w.line_number
            LIMIT 500
        """
        
        return try await DatabaseManagerAsync.shared.executeQuery(queryString, parameters: parameters) { [self] statement in
            wordOccurrenceFromStatement(statement)
        }
    }

    func getWordsAtPositions(bookId: String, lineNumber: Int, positions: [Int]) async throws -> [Word] {
        let positionPlaceholders = positions.map { _ in "?" }.joined(separator: ", ")

        let query = """
            SELECT id, word, book_id, line_number, sequence_number, word_position
            FROM words
            WHERE book_id = ? AND line_number = ? AND word_position IN (\(positionPlaceholders))
            ORDER BY word_position
        """

        var parameters: [Any?] = [bookId, lineNumber]
        parameters.append(contentsOf: positions)

        return try await DatabaseManagerAsync.shared.executeQuery(query, parameters: parameters) { [self] statement in
            wordFromStatement(statement)
        }
    }
    
    private func wordOccurrenceFromStatement(_ statement: OpaquePointer) -> WordOccurrence? {
        guard let wordCString = sqlite3_column_text(statement, 0),
              let bookIdCString = sqlite3_column_text(statement, 1),
              let workTitleCString = sqlite3_column_text(statement, 3),
              let authorNameCString = sqlite3_column_text(statement, 4),
              let lineTextCString = sqlite3_column_text(statement, 6),
              let positionsCString = sqlite3_column_text(statement, 7),
              let languageCString = sqlite3_column_text(statement, 8) else {
            return nil
        }

        let word = String(cString: wordCString)
        let bookId = String(cString: bookIdCString)
        let workTitle = String(cString: workTitleCString)
        let authorName = String(cString: authorNameCString)
        let lineNumber = Int(sqlite3_column_int(statement, 5))
        let lineText = String(cString: lineTextCString)
        let language = String(cString: languageCString)

        // Add book label to title if available
        var bookTitle = workTitle
        if let labelCString = sqlite3_column_text(statement, 2) {
            let label = String(cString: labelCString)
            bookTitle = "\(workTitle) - \(label)"
        }

        let positionsString = String(cString: positionsCString)
        let wordPositions = positionsString.split(separator: ",").compactMap { Int($0) }

        return WordOccurrence(
            word: word,
            bookId: bookId,
            bookTitle: bookTitle,
            authorName: authorName,
            lineNumber: lineNumber,
            lineText: lineText,
            wordPositions: wordPositions,
            language: language
        )
    }
    
    private func wordFromStatement(_ statement: OpaquePointer) -> Word? {
        let id = Int(sqlite3_column_int(statement, 0))
        
        guard let wordCString = sqlite3_column_text(statement, 1),
              let bookIdCString = sqlite3_column_text(statement, 2) else {
            return nil
        }
        
        let word = String(cString: wordCString)
        let bookId = String(cString: bookIdCString)
        let lineNumber = Int(sqlite3_column_int(statement, 3))
        let sequenceNumber = Int(sqlite3_column_int(statement, 4))
        let wordPosition = Int(sqlite3_column_int(statement, 5))
        
        return Word(
            id: id,
            word: word,
            bookId: bookId,
            lineNumber: lineNumber,
            sequenceNumber: sequenceNumber,
            wordPosition: wordPosition
        )
    }
}