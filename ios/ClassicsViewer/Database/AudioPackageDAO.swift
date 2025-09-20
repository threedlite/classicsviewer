import Foundation
import SQLite3

protocol AudioPackageDAOProtocol {
    func importAudioPackage(metadata: [String: Any], audioFiles: [[String: Any]]) async throws -> Int
    func getPackages() async throws -> [AudioPackage]
    func getEnabledPackages() async throws -> [AudioPackage]
    func setPackageEnabled(packageId: Int, enabled: Bool) async throws
    func deletePackage(packageId: Int) async throws
    func getAudioFiles(workId: String, bookId: String?, lineStart: Int, lineEnd: Int) async throws -> [AudioFile]
    func getAudioFilePath(audioFileId: Int) async throws -> String?
}

class AudioPackageDAO: AudioPackageDAOProtocol {

    /// Fix any incorrect paths in the database that contain "privateaudio" instead of "audio"
    func fixIncorrectAudioPaths() async throws {
        // Fix file paths that have "privateaudio" instead of "audio"
        let updatePathQuery = """
            UPDATE audio_files
            SET file_path = REPLACE(file_path, 'privateaudio/', 'audio/')
            WHERE file_path LIKE 'privateaudio/%'
        """
        try await UserDatabaseManagerAsync.shared.execute(updatePathQuery)

        // Fix work_ids that have "private" prefix (e.g., "privatehomer_iliad" -> "homer_iliad")
        let updateWorkIdQuery = """
            UPDATE audio_files
            SET work_id = REPLACE(work_id, 'private', '')
            WHERE work_id LIKE 'private%'
        """
        try await UserDatabaseManagerAsync.shared.execute(updateWorkIdQuery)

        print("DEBUG: Fixed incorrect audio paths and work_ids")
    }

    func importAudioPackage(metadata: [String: Any], audioFiles: [[String: Any]]) async throws -> Int {

        // Insert package
        let packageName = metadata["package_name"] as? String ?? "Unknown Audio Package"
        let displayName = metadata["display_name"] as? String ?? packageName
        let description = metadata["description"] as? String
        let version = metadata["version"] as? String
        let createdDate = metadata["created_date"] as? Date
        let importDate = Date()
        let fileCount = audioFiles.count
        let totalSize = audioFiles.reduce(0) { sum, file in
            sum + (file["file_size"] as? Int ?? 0)
        }

        print("DEBUG AudioPackageDAO: Inserting package '\(packageName)' with \(fileCount) files")

        try await UserDatabaseManagerAsync.shared.execute("""
            INSERT INTO audio_packages
            (package_name, display_name, description, version, created_date, import_date, file_count, total_size, is_enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, parameters: [packageName, displayName, description, version, createdDate, importDate, fileCount, totalSize])

        let packageId = Int(await UserDatabaseManagerAsync.shared.getLastInsertRowId())
        print("DEBUG AudioPackageDAO: Package inserted with ID \(packageId)")

        // Insert audio files
        var insertedCount = 0
        for audioFile in audioFiles {
            let workId = audioFile["work_id"] as? String ?? ""
            let bookId = audioFile["book_id"] as? String
            let lineStart = audioFile["line_start"] as? Int ?? 0
            let lineEnd = audioFile["line_end"] as? Int ?? 0
            let filePath = audioFile["file_path"] as? String ?? ""
            let durationMs = audioFile["duration_ms"] as? Int
            let fileSize = audioFile["file_size"] as? Int
            let mimeType = audioFile["mime_type"] as? String ?? "audio/mpeg"
            
            try await UserDatabaseManagerAsync.shared.execute("""
                INSERT INTO audio_files
                (package_id, work_id, book_id, line_start, line_end, file_path, duration_ms, file_size, mime_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, parameters: [packageId, workId, bookId, lineStart, lineEnd, filePath, durationMs, fileSize, mimeType])
            insertedCount += 1
        }

        print("DEBUG AudioPackageDAO: Inserted \(insertedCount) audio files")
        return packageId
    }
    
    func getPackages() async throws -> [AudioPackage] {
        // Database lifecycle managed by async architecture
        
        let query = "SELECT * FROM audio_packages ORDER BY display_name"
        
        return try await UserDatabaseManagerAsync.shared.executeQuery(query) { [self] statement in
            packageFromStatement(statement)
        }
    }
    
    func getEnabledPackages() async throws -> [AudioPackage] {
        // Database lifecycle managed by async architecture
        
        let query = """
            SELECT * FROM audio_packages
            WHERE is_enabled = 1
            ORDER BY display_name
        """
        
        return try await UserDatabaseManagerAsync.shared.executeQuery(query) { [self] statement in
            packageFromStatement(statement)
        }
    }
    
    func setPackageEnabled(packageId: Int, enabled: Bool) async throws {
        // Database lifecycle managed by async architecture
        
        try await UserDatabaseManagerAsync.shared.execute("""
            UPDATE audio_packages
            SET is_enabled = ?
            WHERE id = ?
        """, parameters: [enabled ? 1 : 0, packageId])
    }
    
    func deletePackage(packageId: Int) async throws {
        // Database lifecycle managed by async architecture
        
        // Get file paths to delete physical files
        let files = try await UserDatabaseManagerAsync.shared.executeQuery(
            "SELECT file_path FROM audio_files WHERE package_id = ?",
            parameters: [packageId]
        ) { statement in
            if let pathCString = sqlite3_column_text(statement, 0) {
                return String(cString: pathCString)
            }
            return nil
        }.compactMap { $0 }
        
        // Delete physical files
        let fileManager = FileManager.default
        let documentsPath = NSSearchPathForDirectoriesInDomains(.documentDirectory, .userDomainMask, true).first!
        
        for filePath in files {
            let fullPath = (documentsPath as NSString).appendingPathComponent(filePath)
            try? fileManager.removeItem(atPath: fullPath)
        }
        
        // Cascade delete will remove associated audio files from database
        try await UserDatabaseManagerAsync.shared.execute("DELETE FROM audio_packages WHERE id = ?", parameters: [packageId])
    }
    
    func getAudioFiles(workId: String, bookId: String?, lineStart: Int, lineEnd: Int) async throws -> [AudioFile] {
        // Database lifecycle managed by async architecture

        // First, let's see what work IDs we actually have in the database
        let debugQuery = """
            SELECT DISTINCT f.work_id, f.book_id, COUNT(*) as file_count
            FROM audio_files f
            JOIN audio_packages p ON f.package_id = p.id
            WHERE p.is_enabled = 1
            GROUP BY f.work_id, f.book_id
        """

        let availableWorkIds = try await UserDatabaseManagerAsync.shared.executeQuery(debugQuery) { statement in
            let workId = String(cString: sqlite3_column_text(statement, 0))
            let bookIdPtr = sqlite3_column_text(statement, 1)
            let bookId = bookIdPtr != nil ? String(cString: bookIdPtr!) : "NULL"
            let count = Int(sqlite3_column_int(statement, 2))
            return "\(workId) (book: \(bookId), files: \(count))"
        }

        print("DEBUG AudioPackageDAO: Available work IDs in enabled packages: \(availableWorkIds)")
        print("DEBUG AudioPackageDAO: Looking for work_id='\(workId)', book_id='\(bookId ?? "nil")', lines \(lineStart)-\(lineEnd)")

        // Also show exact query and parameters
        print("DEBUG AudioPackageDAO: Query will check work_id = '\(workId)' AND book_id = '\(bookId ?? "ANY")'")

        var query = """
            SELECT f.* FROM audio_files f
            JOIN audio_packages p ON f.package_id = p.id
            WHERE p.is_enabled = 1
            AND f.work_id = ?
        """

        var parameters: [Any?] = [workId]

        if let bookId = bookId {
            query += " AND (f.book_id = ? OR f.book_id IS NULL)"
            parameters.append(bookId)
        }

        query += """
            AND f.line_start <= ?
            AND f.line_end >= ?
            ORDER BY f.line_start
        """

        parameters.append(contentsOf: [lineEnd, lineStart])
        
        return try await UserDatabaseManagerAsync.shared.executeQuery(query, parameters: parameters) { [self] statement in
            audioFileFromStatement(statement)
        }
    }
    
    func getAudioFilePath(audioFileId: Int) async throws -> String? {
        // Database lifecycle managed by async architecture

        let query = "SELECT file_path FROM audio_files WHERE id = ?"

        let results = try await UserDatabaseManagerAsync.shared.executeQuery(query, parameters: [audioFileId]) { statement in
            if let pathCString = sqlite3_column_text(statement, 0) {
                return String(cString: pathCString)
            }
            return nil
        }

        if let relativePath = results.first {
            let documentsPath = NSSearchPathForDirectoriesInDomains(.documentDirectory, .userDomainMask, true).first!

            // Fix for incorrect path: if path contains "privateaudio", replace with "audio"
            let fixedPath = relativePath.replacingOccurrences(of: "privateaudio/", with: "audio/")
            let fullPath = (documentsPath as NSString).appendingPathComponent(fixedPath)

            // If the fixed path doesn't exist, try the original path
            if !FileManager.default.fileExists(atPath: fullPath) {
                let originalPath = (documentsPath as NSString).appendingPathComponent(relativePath)
                if FileManager.default.fileExists(atPath: originalPath) {
                    return originalPath
                }
            }

            return fullPath
        }

        return nil
    }
    
    private func packageFromStatement(_ statement: OpaquePointer) -> AudioPackage? {
        let id = Int(sqlite3_column_int(statement, 0))
        
        guard let packageNameCString = sqlite3_column_text(statement, 1),
              let displayNameCString = sqlite3_column_text(statement, 2) else {
            return nil
        }
        
        let packageName = String(cString: packageNameCString)
        let displayName = String(cString: displayNameCString)
        
        var description: String? = nil
        if let descCString = sqlite3_column_text(statement, 3) {
            description = String(cString: descCString)
        }
        
        var version: String? = nil
        if let versionCString = sqlite3_column_text(statement, 4) {
            version = String(cString: versionCString)
        }
        
        var createdDate: Date? = nil
        if sqlite3_column_type(statement, 5) != SQLITE_NULL {
            let createdMillis = sqlite3_column_int64(statement, 5)
            createdDate = Date(timeIntervalSince1970: Double(createdMillis) / 1000.0)
        }
        
        let importDateMillis = sqlite3_column_int64(statement, 6)
        let importDate = Date(timeIntervalSince1970: Double(importDateMillis) / 1000.0)
        
        let fileCount = Int(sqlite3_column_int(statement, 7))
        let totalSize = Int(sqlite3_column_int(statement, 8))
        let isEnabled = sqlite3_column_int(statement, 9) != 0
        
        return AudioPackage(
            id: id,
            packageName: packageName,
            displayName: displayName,
            description: description,
            version: version,
            createdDate: createdDate,
            importDate: importDate,
            fileCount: fileCount,
            totalSize: totalSize,
            isEnabled: isEnabled
        )
    }
    
    private func audioFileFromStatement(_ statement: OpaquePointer) -> AudioFile? {
        let id = Int(sqlite3_column_int(statement, 0))
        let packageId = Int(sqlite3_column_int(statement, 1))
        
        guard let workIdCString = sqlite3_column_text(statement, 2),
              let filePathCString = sqlite3_column_text(statement, 6) else {
            return nil
        }
        
        let workId = String(cString: workIdCString)
        let filePath = String(cString: filePathCString)
        
        var bookId: String? = nil
        if let bookIdCString = sqlite3_column_text(statement, 3) {
            bookId = String(cString: bookIdCString)
        }
        
        let lineStart = Int(sqlite3_column_int(statement, 4))
        let lineEnd = Int(sqlite3_column_int(statement, 5))
        
        var durationMs: Int? = nil
        if sqlite3_column_type(statement, 7) != SQLITE_NULL {
            durationMs = Int(sqlite3_column_int(statement, 7))
        }
        
        var fileSize: Int? = nil
        if sqlite3_column_type(statement, 8) != SQLITE_NULL {
            fileSize = Int(sqlite3_column_int(statement, 8))
        }
        
        let mimeType = sqlite3_column_text(statement, 9).map { String(cString: $0) } ?? "audio/mpeg"
        
        return AudioFile(
            id: id,
            packageId: packageId,
            workId: workId,
            bookId: bookId,
            lineStart: lineStart,
            lineEnd: lineEnd,
            filePath: filePath,
            durationMs: durationMs,
            fileSize: fileSize,
            mimeType: mimeType
        )
    }
}