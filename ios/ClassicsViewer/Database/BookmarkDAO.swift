import Foundation
import SQLite3

protocol BookmarkDAOProtocol {
    func createBookmarksTableIfNeeded() async throws
    func insertBookmark(_ bookmark: Bookmark) async throws -> Bookmark
    func updateBookmark(_ bookmark: Bookmark) async throws
    func deleteBookmark(id: Int) async throws
    func getBookmark(authorId: String, workId: String, bookId: String, lineNumber: Int, sequenceNumber: Int) async throws -> Bookmark?
    func getAllBookmarks() async throws -> [Bookmark]
    func getBookmarksByWork(workId: String) async throws -> [Bookmark]
    func getRecentBookmarks(limit: Int) async throws -> [Bookmark]
    func getBookmarksWithNotes() async throws -> [Bookmark]
    func updateLastAccessed(id: Int) async throws
}

class BookmarkDAO: BookmarkDAOProtocol {
    // Use async database manager
    
    func createBookmarksTableIfNeeded() async throws {
        // First check if sequence_number column exists, add it if not (for migration)
        let checkColumnQuery = "PRAGMA table_info(bookmarks)"
        let columnExists = try await UserDatabaseManagerAsync.shared.executeQuery(checkColumnQuery) { statement in
            if let columnNameCString = sqlite3_column_text(statement, 1) {
                let columnName = String(cString: columnNameCString)
                return columnName == "sequence_number"
            }
            return false
        }.contains(true)
        
        if !columnExists {
            // Table exists but doesn't have sequence_number column - add it
            do {
                let addColumnQuery = "ALTER TABLE bookmarks ADD COLUMN sequence_number INTEGER NOT NULL DEFAULT 0"
                try await UserDatabaseManagerAsync.shared.execute(addColumnQuery)
                NSLog("Added sequence_number column to existing bookmarks table")
            } catch {
                // Table might not exist at all, continue to create it
                NSLog("Could not add sequence_number column, will create new table")
            }
        }
        
        // Create the table if it doesn't exist
        // Using IF NOT EXISTS prevents errors if table already exists
        
        let createTableQuery = """
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                work_id TEXT NOT NULL,
                book_id TEXT NOT NULL,
                line_number INTEGER NOT NULL,
                sequence_number INTEGER NOT NULL,
                author_name TEXT NOT NULL,
                work_title TEXT NOT NULL,
                book_label TEXT,
                line_text TEXT NOT NULL,
                note TEXT,
                created_at INTEGER NOT NULL,
                last_accessed INTEGER NOT NULL
            )
        """
        
        let createIndexQuery = """
            CREATE UNIQUE INDEX IF NOT EXISTS index_bookmarks_book_id_line_number_sequence_number ON bookmarks(book_id, line_number, sequence_number)
        """

        let createAuthorIndexQuery = """
            CREATE INDEX IF NOT EXISTS index_bookmarks_created_at ON bookmarks(created_at)
        """

        let createLastAccessedIndexQuery = """
            CREATE INDEX IF NOT EXISTS index_bookmarks_last_accessed ON bookmarks(last_accessed)
        """
        
        try await UserDatabaseManagerAsync.shared.execute(createTableQuery)
        try await UserDatabaseManagerAsync.shared.execute(createIndexQuery)
        try await UserDatabaseManagerAsync.shared.execute(createAuthorIndexQuery)
        try await UserDatabaseManagerAsync.shared.execute(createLastAccessedIndexQuery)
    }
    
    func insertBookmark(_ bookmark: Bookmark) async throws -> Bookmark {
        let query = """
            INSERT OR REPLACE INTO bookmarks (work_id, book_id, line_number, sequence_number, author_name,
                                 work_title, book_label, line_text, note, created_at, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        // Convert dates to milliseconds since epoch (matching Android)
        let createdAtMillis = Int64(bookmark.createdAt.timeIntervalSince1970 * 1000)
        let lastAccessedMillis = Int64(bookmark.lastAccessed.timeIntervalSince1970 * 1000)

        let parameters: [Any?] = [
            bookmark.workId,
            bookmark.bookId,
            bookmark.lineNumber,
            bookmark.sequenceNumber,
            bookmark.authorName,
            bookmark.workTitle,
            bookmark.bookLabel,
            bookmark.lineText,
            bookmark.note,
            createdAtMillis,
            lastAccessedMillis
        ]
        
        NSLog("SAVE_DEBUG: INSERT parameters:")
        NSLog("SAVE_DEBUG: - workId: '%@'", bookmark.workId)
        NSLog("SAVE_DEBUG: - bookId: '%@'", bookmark.bookId)
        NSLog("SAVE_DEBUG: - lineNumber: %d", bookmark.lineNumber)
        NSLog("SAVE_DEBUG: - sequenceNumber: %d", bookmark.sequenceNumber)
        NSLog("SAVE_DEBUG: - authorName: '%@'", bookmark.authorName)
        NSLog("SAVE_DEBUG: - workTitle: '%@'", bookmark.workTitle)
        NSLog("SAVE_DEBUG: - bookLabel: '%@'", bookmark.bookLabel ?? "nil")
        NSLog("SAVE_DEBUG: - lineText: '%@'", bookmark.lineText)
        NSLog("SAVE_DEBUG: - note: '%@'", bookmark.note ?? "nil")
        NSLog("SAVE_DEBUG: - createdAtMillis: %lld", createdAtMillis)
        NSLog("SAVE_DEBUG: - lastAccessedMillis: %lld", lastAccessedMillis)
        
        do {
            try await UserDatabaseManagerAsync.shared.execute(query, parameters: parameters)
            NSLog("SAVE_DEBUG: Database execute completed successfully")
        } catch {
            NSLog("SAVE_ERROR: Database execute failed: %@", error.localizedDescription)
            throw error
        }
        
        // Debug: Check total bookmark count
        let countQuery = "SELECT COUNT(*) FROM bookmarks"
        let countResults = try await UserDatabaseManagerAsync.shared.executeQuery(countQuery) { statement in
            return Int(sqlite3_column_int(statement, 0))
        }
        let totalCount = countResults.first ?? 0
        NSLog("SAVE_DEBUG: Total bookmarks in database after insert: %d", totalCount)
        
        // Check ALL bookmarks to see what's actually in the database
        let allQuery = "SELECT work_id, book_id, line_number, note, author_name FROM bookmarks ORDER BY id DESC LIMIT 5"
        let allResults = try await UserDatabaseManagerAsync.shared.executeQuery(allQuery) { statement in
            let workId = String(cString: sqlite3_column_text(statement, 0))
            let bookId = String(cString: sqlite3_column_text(statement, 1))
            let lineNumber = Int(sqlite3_column_int(statement, 2))
            let note = sqlite3_column_text(statement, 3) != nil ? String(cString: sqlite3_column_text(statement, 3)) : "nil"
            let authorName = String(cString: sqlite3_column_text(statement, 4))
            return "WorkId: '\(workId)', BookId: '\(bookId)', LineNumber: \(lineNumber), Note: '\(note)', Author: '\(authorName)'"
        }
        NSLog("SAVE_DEBUG: Last 5 bookmarks in database:")
        for result in allResults {
            NSLog("SAVE_DEBUG: - %@", result)
        }
        
        // Now show what we're searching for
        NSLog("SAVE_DEBUG: Searching for - WorkId: '%@', BookId: '%@', LineNumber: %d",
              bookmark.workId, bookmark.bookId, bookmark.lineNumber)

        // Get the inserted bookmark with its ID
        if let inserted = try await getBookmark(authorId: bookmark.authorId, workId: bookmark.workId, bookId: bookmark.bookId, lineNumber: bookmark.lineNumber, sequenceNumber: bookmark.sequenceNumber) {
            return inserted
        }
        
        throw BookmarkError.insertFailed
    }
    
    func updateBookmark(_ bookmark: Bookmark) async throws {
        guard let id = bookmark.id else {
            throw BookmarkError.invalidBookmark
        }

        let query = """
            UPDATE bookmarks
            SET note = ?, last_accessed = ?
            WHERE id = ?
        """

        let lastAccessedMillis = Int64(Date().timeIntervalSince1970 * 1000)

        try await UserDatabaseManagerAsync.shared.execute(query, parameters: [bookmark.note, lastAccessedMillis, id])
    }
    
    func deleteBookmark(id: Int) async throws {
        let query = "DELETE FROM bookmarks WHERE id = ?"
        try await UserDatabaseManagerAsync.shared.execute(query, parameters: [id])
    }
    
    func getBookmark(authorId: String, workId: String, bookId: String, lineNumber: Int, sequenceNumber: Int = 0) async throws -> Bookmark? {
        // Android stores author_name in bookmarks, need to get that from authorId
        let authorName = try await getAuthorName(authorId: authorId)

        let query = """
            SELECT id, work_id, book_id, line_number, sequence_number, author_name, work_title,
                   book_label, line_text, note, created_at, last_accessed
            FROM bookmarks
            WHERE work_id = ? AND book_id = ? AND line_number = ? AND sequence_number = ? AND author_name = ?
        """

        NSLog("SAVE_DEBUG: Querying for bookmark - authorName: %@, workId: %@, bookId: %@, lineNumber: %d, sequenceNumber: %d", authorName, workId, bookId, lineNumber, sequenceNumber)

        let bookmarks = try await UserDatabaseManagerAsync.shared.executeQuery(query, parameters: [workId, bookId, lineNumber, sequenceNumber, authorName]) { [self] statement in
            bookmarkFromStatement(statement)
        }
        
        NSLog("SAVE_DEBUG: Query returned %d bookmarks", bookmarks.count)
        
        return bookmarks.first
    }
    
    func getAllBookmarks() async throws -> [Bookmark] {
        let query = """
            SELECT id, work_id, book_id, line_number, sequence_number, author_name, work_title,
                   book_label, line_text, note, created_at, last_accessed
            FROM bookmarks
            ORDER BY created_at DESC
        """
        
        return try await UserDatabaseManagerAsync.shared.executeQuery(query) { [self] statement in
            bookmarkFromStatement(statement)
        }
    }
    
    func getBookmarksByWork(workId: String) async throws -> [Bookmark] {
        let query = """
            SELECT id, work_id, book_id, line_number, sequence_number, author_name, work_title,
                   book_label, line_text, note, created_at, last_accessed
            FROM bookmarks
            WHERE work_id = ?
            ORDER BY sequence_number, line_number
        """
        
        return try await UserDatabaseManagerAsync.shared.executeQuery(query, parameters: [workId]) { [self] statement in
            bookmarkFromStatement(statement)
        }
    }
    
    func getRecentBookmarks(limit: Int) async throws -> [Bookmark] {
        let query = """
            SELECT id, work_id, book_id, line_number, sequence_number, author_name, work_title,
                   book_label, line_text, note, created_at, last_accessed
            FROM bookmarks
            ORDER BY last_accessed DESC
            LIMIT ?
        """
        
        return try await UserDatabaseManagerAsync.shared.executeQuery(query, parameters: [limit]) { [self] statement in
            bookmarkFromStatement(statement)
        }
    }
    
    func getBookmarksWithNotes() async throws -> [Bookmark] {
        let query = """
            SELECT id, work_id, book_id, line_number, sequence_number, author_name, work_title,
                   book_label, line_text, note, created_at, last_accessed
            FROM bookmarks
            WHERE note IS NOT NULL AND note != ''
            ORDER BY created_at DESC
        """
        
        return try await UserDatabaseManagerAsync.shared.executeQuery(query) { [self] statement in
            bookmarkFromStatement(statement)
        }
    }
    
    func updateLastAccessed(id: Int) async throws {
        let query = """
            UPDATE bookmarks
            SET last_accessed = ?
            WHERE id = ?
        """

        let lastAccessedMillis = Int64(Date().timeIntervalSince1970 * 1000)

        try await UserDatabaseManagerAsync.shared.execute(query, parameters: [lastAccessedMillis, id])
    }
    
    private func bookmarkFromStatement(_ statement: OpaquePointer) -> Bookmark? {
        let id = Int(sqlite3_column_int(statement, 0))

        guard let workIdCString = sqlite3_column_text(statement, 1),
              let bookIdCString = sqlite3_column_text(statement, 2),
              let authorNameCString = sqlite3_column_text(statement, 5),
              let workTitleCString = sqlite3_column_text(statement, 6),
              let lineTextCString = sqlite3_column_text(statement, 8) else {
            NSLog("SAVE_DEBUG: bookmarkFromStatement failed - missing required fields")
            return nil
        }

        let workId = String(cString: workIdCString)
        let bookId = String(cString: bookIdCString)
        let lineNumber = Int(sqlite3_column_int(statement, 3))
        let sequenceNumber = Int(sqlite3_column_int(statement, 4))
        let authorName = String(cString: authorNameCString)
        let workTitle = String(cString: workTitleCString)
        let lineText = String(cString: lineTextCString)

        var bookLabel: String? = nil
        if let bookLabelCString = sqlite3_column_text(statement, 7) {
            bookLabel = String(cString: bookLabelCString)
        }

        var note: String? = nil
        if let noteCString = sqlite3_column_text(statement, 9) {
            note = String(cString: noteCString)
        }

        // Get timestamps as milliseconds and convert to Date
        let createdAtMillis = sqlite3_column_int64(statement, 10)
        let lastAccessedMillis = sqlite3_column_int64(statement, 11)

        let createdAt = Date(timeIntervalSince1970: Double(createdAtMillis) / 1000.0)
        let lastAccessed = Date(timeIntervalSince1970: Double(lastAccessedMillis) / 1000.0)

        NSLog("SAVE_DEBUG: Parsing timestamps - createdAtMillis: %lld, lastAccessedMillis: %lld", createdAtMillis, lastAccessedMillis)

        return Bookmark(
            id: id,
            authorId: "", // Will be filled by caller if needed
            workId: workId,
            bookId: bookId,
            lineNumber: lineNumber,
            sequenceNumber: sequenceNumber,
            authorName: authorName,
            workTitle: workTitle,
            bookLabel: bookLabel,
            lineText: lineText,
            note: note,
            createdAt: createdAt,
            lastAccessed: lastAccessed
        )
    }

    private func getAuthorName(authorId: String) async throws -> String {
        // Query the main database to get author name from author ID
        let query = "SELECT name FROM authors WHERE id = ?"
        let results = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [authorId]) { statement in
            if let nameCString = sqlite3_column_text(statement, 0) {
                return String(cString: nameCString)
            }
            return nil
        }

        guard let authorName = results.first else {
            throw BookmarkError.invalidAuthor
        }

        return authorName
    }
}

enum BookmarkError: LocalizedError {
    case insertFailed
    case invalidBookmark
    case invalidAuthor
    
    var errorDescription: String? {
        switch self {
        case .insertFailed:
            return "Failed to insert bookmark"
        case .invalidBookmark:
            return "Invalid bookmark - missing required fields"
        case .invalidAuthor:
            return "Invalid author ID - author not found"
        }
    }
}