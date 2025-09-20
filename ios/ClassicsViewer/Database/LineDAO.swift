import Foundation
import SQLite3

protocol LineDAOProtocol {
    func getLines(bookId: String, startLine: Int, endLine: Int) async throws -> [TextLine]
    func getTotalLines(bookId: String) async throws -> Int
}

class LineDAO: LineDAOProtocol {
    // Use async database manager

    func getLines(bookId: String, startLine: Int, endLine: Int) async throws -> [TextLine] {
        let query = """
            SELECT id, book_id, line_number, sequence_number, line_text, line_xml, speaker
            FROM text_lines
            WHERE book_id = ? AND line_number >= ? AND line_number <= ?
            ORDER BY line_number, sequence_number
        """

        print("DEBUG: Getting lines for book \(bookId), lines \(startLine)-\(endLine)")
        let lines = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [bookId, startLine, endLine]) { statement in
            self.lineFromStatement(statement)
        }
        print("DEBUG: Retrieved \(lines.count) lines")
        return lines
    }

    func getTotalLines(bookId: String) async throws -> Int {
        let query = """
            SELECT COUNT(*) FROM text_lines WHERE book_id = ?
        """

        let counts = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [bookId]) { statement in
            Int(sqlite3_column_int(statement, 0))
        }

        return counts.first ?? 0
    }
    
    private func lineFromStatement(_ statement: OpaquePointer) -> TextLine? {
        let id = Int(sqlite3_column_int(statement, 0))
        
        guard let bookIdCString = sqlite3_column_text(statement, 1),
              let lineTextCString = sqlite3_column_text(statement, 4) else {
            return nil
        }
        
        let bookId = String(cString: bookIdCString)
        let lineNumber = Int(sqlite3_column_int(statement, 2))
        let sequenceNumber = Int(sqlite3_column_int(statement, 3))
        let lineText = String(cString: lineTextCString)
        
        var lineXml: String? = nil
        if let lineXmlCString = sqlite3_column_text(statement, 5) {
            lineXml = String(cString: lineXmlCString)
        }
        
        var speaker: String? = nil
        if let speakerCString = sqlite3_column_text(statement, 6) {
            speaker = String(cString: speakerCString)
        }
        
        return TextLine(id: id, bookId: bookId, lineNumber: lineNumber,
                       sequenceNumber: sequenceNumber, lineText: lineText,
                       lineXml: lineXml, speaker: speaker)
    }
}