import Foundation

class BookmarkCSVHandler {
    
    // MARK: - CSV Export
    
    static func exportBookmarks(_ bookmarks: [Bookmark]) -> String {
        // Match Android CSV format exactly
        var csvContent = "work_id,book_id,line_number,sequence_number,author_name,work_title,book_label,line_text,note,created_at,last_accessed\n"
        
        for bookmark in bookmarks {
            let workId = escapeCSVField(bookmark.workId)
            let bookId = escapeCSVField(bookmark.bookId)
            let lineNumber = String(bookmark.lineNumber)
            let sequenceNumber = String(bookmark.sequenceNumber)  // Now properly tracked
            let authorName = escapeCSVField(bookmark.authorName)
            let workTitle = escapeCSVField(bookmark.workTitle)
            let bookLabel = escapeCSVField(bookmark.bookLabel ?? "")
            let lineText = escapeCSVField(bookmark.lineText)
            let note = escapeCSVField(bookmark.note ?? "")
            // Use Unix timestamp in milliseconds for Android compatibility
            let createdAt = String(Int64(bookmark.createdAt.timeIntervalSince1970 * 1000))
            let lastAccessed = String(Int64(bookmark.lastAccessed.timeIntervalSince1970 * 1000))
            
            let row = "\(workId),\(bookId),\(lineNumber),\(sequenceNumber),\(authorName),\(workTitle),\(bookLabel),\(lineText),\(note),\(createdAt),\(lastAccessed)"
            csvContent += row + "\n"
        }
        
        return csvContent
    }
    
    static func generateExportFilename() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyyMMdd_HHmmss"
        let timestamp = formatter.string(from: Date())
        return "bookmarks_\(timestamp).csv"
    }
    
    // MARK: - CSV Import

    static func importBookmarks(from csvContent: String) throws -> [Bookmark] {
        // Parse CSV content handling multi-line fields properly
        let records = parseCSVContent(csvContent)

        // Skip header row if present
        let dataRecords = records.count > 0 && records[0].first?.starts(with: "work_id") == true
            ? Array(records.dropFirst())
            : records

        var bookmarks: [Bookmark] = []

        for fields in dataRecords {
            if let bookmark = parseBookmarkFromCSVFields(fields) {
                bookmarks.append(bookmark)
            }
            // Note: parseBookmarkFromCSVFields returns nil for invalid records, doesn't throw
        }

        return bookmarks
    }
    
    // MARK: - Private Helpers
    
    private static func escapeCSVField(_ field: String) -> String {
        // Always quote text fields and escape internal quotes
        let escaped = field.replacingOccurrences(of: "\"", with: "\"\"")
        return "\"\(escaped)\""
    }
    
    private static func parseBookmarkFromCSVFields(_ fields: [String]) -> Bookmark? {
        
        // Android format has 11 fields (includes sequence_number)
        // Accept both 10 fields (old iOS format) and 11 fields (Android format)
        guard fields.count >= 10 else { return nil }
        
        let hasSequenceNumber = fields.count >= 11
        var fieldIndex = 0
        
        // Parse fields in exact order matching Android
        let workId = fields[fieldIndex]; fieldIndex += 1
        let bookId = fields[fieldIndex]; fieldIndex += 1
        guard let lineNumber = Int(fields[fieldIndex]) else { return nil }; fieldIndex += 1
        
        // Parse sequence_number if present (critical for texts with duplicate line numbers)
        var sequenceNumber = 0  // Default for old exports without it
        if hasSequenceNumber {
            sequenceNumber = Int(fields[fieldIndex]) ?? 0
            fieldIndex += 1
        }
        
        let authorName = fields[fieldIndex]; fieldIndex += 1
        let workTitle = fields[fieldIndex]; fieldIndex += 1
        let bookLabel = fields[fieldIndex].isEmpty ? nil : fields[fieldIndex]; fieldIndex += 1
        let lineText = fields[fieldIndex]; fieldIndex += 1
        let note = fields[fieldIndex].isEmpty ? nil : fields[fieldIndex]; fieldIndex += 1
        
        // Parse timestamps - Android uses milliseconds since epoch
        let createdAtString = fields[fieldIndex]; fieldIndex += 1
        let lastAccessedString = fields[fieldIndex]
        
        // Handle both Unix timestamps (from Android) and ISO8601 (from older iOS exports)
        var createdAt: Date
        var lastAccessed: Date
        
        if let createdAtMillis = Int64(createdAtString) {
            // Unix timestamp in milliseconds
            createdAt = Date(timeIntervalSince1970: TimeInterval(createdAtMillis) / 1000.0)
        } else if let isoDate = ISO8601DateFormatter().date(from: createdAtString) {
            // ISO8601 format (backwards compatibility)
            createdAt = isoDate
        } else {
            return nil
        }
        
        if let lastAccessedMillis = Int64(lastAccessedString) {
            // Unix timestamp in milliseconds
            lastAccessed = Date(timeIntervalSince1970: TimeInterval(lastAccessedMillis) / 1000.0)
        } else if let isoDate = ISO8601DateFormatter().date(from: lastAccessedString) {
            // ISO8601 format (backwards compatibility)
            lastAccessed = isoDate
        } else {
            return nil
        }
        
        // Extract authorId from workId (e.g., "tlg0012.tlg001" -> "tlg0012")
        let authorId = String(workId.prefix(7))
        
        return Bookmark(
            authorId: authorId,
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
    
    private static func parseCSVContent(_ content: String) -> [[String]] {
        var records: [[String]] = []
        var currentRecord: [String] = []
        var currentField = ""
        var inQuotes = false
        var i = content.startIndex

        while i < content.endIndex {
            let char = content[i]

            switch char {
            case "\"":
                if inQuotes {
                    // Check if it's an escaped quote (two consecutive quotes)
                    let nextIndex = content.index(after: i)
                    if nextIndex < content.endIndex && content[nextIndex] == "\"" {
                        currentField.append("\"")
                        i = nextIndex  // Skip next quote
                    } else {
                        // Toggle quote state
                        inQuotes = false
                    }
                } else {
                    // Toggle quote state
                    inQuotes = true
                }

            case ",":
                if !inQuotes {
                    // Field separator outside quotes
                    currentRecord.append(currentField)
                    currentField = ""
                } else {
                    // Regular character inside quotes
                    currentField.append(char)
                }

            case "\n", "\r":
                if !inQuotes {
                    // Record separator outside quotes
                    currentRecord.append(currentField)
                    currentField = ""

                    // Add record if it has fields
                    if !currentRecord.isEmpty {
                        records.append(currentRecord)
                        currentRecord = []
                    }

                    // Skip \r\n (Windows line endings)
                    if char == "\r" {
                        let nextIndex = content.index(after: i)
                        if nextIndex < content.endIndex && content[nextIndex] == "\n" {
                            i = nextIndex
                        }
                    }
                } else {
                    // Newline inside quotes - preserve it
                    currentField.append(char)
                }

            default:
                // Regular character
                currentField.append(char)
            }

            i = content.index(after: i)
        }

        // Add last field and record
        currentRecord.append(currentField)
        if !currentRecord.isEmpty {
            records.append(currentRecord)
        }

        return records
    }
}

// MARK: - CSV Import/Export Manager

class BookmarkCSVManager {
    let bookmarkDAO: BookmarkDAO
    
    init(bookmarkDAO: BookmarkDAO = BookmarkDAO()) {
        self.bookmarkDAO = bookmarkDAO
    }
    
    func exportBookmarksToFile() async throws -> URL {
        // Get all bookmarks
        let bookmarks = try await bookmarkDAO.getAllBookmarks()
        
        // Generate CSV content
        let csvContent = BookmarkCSVHandler.exportBookmarks(bookmarks)
        
        // Create file in documents directory
        let documentsURL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let filename = BookmarkCSVHandler.generateExportFilename()
        let fileURL = documentsURL.appendingPathComponent(filename)
        
        // Write to file
        try csvContent.write(to: fileURL, atomically: true, encoding: .utf8)
        
        return fileURL
    }
    
    func importBookmarksFromFile(at url: URL) async throws -> ImportResult {
        // Read CSV content
        let csvContent = try String(contentsOf: url, encoding: .utf8)
        
        // Parse bookmarks
        let bookmarks = try BookmarkCSVHandler.importBookmarks(from: csvContent)
        
        // Import each bookmark
        var successCount = 0
        var failureCount = 0
        
        for bookmark in bookmarks {
            do {
                // Check if bookmark already exists
                if let existing = try await bookmarkDAO.getBookmark(
                    authorId: bookmark.authorId,
                    workId: bookmark.workId,
                    bookId: bookmark.bookId,
                    lineNumber: bookmark.lineNumber
                ) {
                    // Update note if newer
                    if bookmark.createdAt > existing.createdAt || bookmark.note != existing.note {
                        try await bookmarkDAO.updateBookmark(bookmark)
                        successCount += 1
                    } else {
                        failureCount += 1 // Already exists
                    }
                } else {
                    // Insert new bookmark
                    _ = try await bookmarkDAO.insertBookmark(bookmark)
                    successCount += 1
                }
            } catch {
                failureCount += 1
            }
        }
        
        return ImportResult(
            totalCount: bookmarks.count,
            successCount: successCount,
            failureCount: failureCount
        )
    }
}

// MARK: - Supporting Types

struct ImportResult {
    let totalCount: Int
    let successCount: Int
    let failureCount: Int
    
    var message: String {
        if failureCount == 0 {
            return "Successfully imported \(successCount) bookmarks"
        } else {
            return "Imported \(successCount) bookmarks, \(failureCount) duplicates skipped"
        }
    }
}

enum CSVError: LocalizedError {
    case parseError(line: Int, detail: String)
    case invalidFormat
    
    var errorDescription: String? {
        switch self {
        case .parseError(let line, let detail):
            return "Error parsing line \(line): \(detail)"
        case .invalidFormat:
            return "Invalid CSV format"
        }
    }
}