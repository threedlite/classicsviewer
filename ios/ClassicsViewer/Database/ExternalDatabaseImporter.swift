import Foundation
import UniformTypeIdentifiers
import os.log

class ExternalDatabaseImporter: ObservableObject {
    static let shared = ExternalDatabaseImporter()
    private init() {}
    
    @Published var isImporting = false
    @Published var importProgress: Double = 0.0
    @Published var importStatus: String = ""
    @Published var validationReport: DatabaseValidator.ValidationReport?
    
    enum ImportError: LocalizedError {
        case invalidFileType
        case fileTooSmall
        case validationFailed(String)
        case extractionFailed(String)
        case importCancelled
        
        var errorDescription: String? {
            switch self {
            case .invalidFileType:
                return "Invalid file type. Please select a .db or .zip file."
            case .fileTooSmall:
                return "File is too small to be a valid database"
            case .validationFailed(let reason):
                return "Database validation failed: \(reason)"
            case .extractionFailed(let reason):
                return "Failed to extract database: \(reason)"
            case .importCancelled:
                return "Import was cancelled"
            }
        }
    }
    
    // MARK: - Import External Database
    
    func importDatabaseFromDownloads(fileName: String) async throws {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")

        // Try different possible paths for Downloads
        let paths = [
            FileManager.default.urls(for: .downloadsDirectory, in: .userDomainMask).first,
            FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first?.appendingPathComponent("Downloads"),
            URL(fileURLWithPath: NSHomeDirectory()).appendingPathComponent("Downloads"),
            URL(fileURLWithPath: "/var/mobile/Downloads"),
            FileManager.default.temporaryDirectory.appendingPathComponent("Downloads")
        ]

        var foundURL: URL?
        for basePath in paths {
            guard let path = basePath else { continue }
            let fileURL = path.appendingPathComponent(fileName)
            logger.error("🔵 Checking for file at: \(fileURL.path)")
            if FileManager.default.fileExists(atPath: fileURL.path) {
                foundURL = fileURL
                logger.error("🔵 Found file at: \(fileURL.path)")
                break
            }
        }

        guard let url = foundURL else {
            logger.error("🔵 File not found in any Downloads location")
            throw ImportError.invalidFileType
        }

        try await importDatabase(from: url)
    }

    func importDatabase(from url: URL) async throws {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")
        
        logger.error("🟢 === START DATABASE IMPORT ===")
        logger.error("🟢 URL: \(url.absoluteString)")
        logger.error("🟢 FULL PATH: \(url.path)")
        logger.error("🟢 Extension: \(url.pathExtension)")
        logger.error("🟢 File exists: \(FileManager.default.fileExists(atPath: url.path))")
        
        await MainActor.run {
            isImporting = true
            importProgress = 0.0
            importStatus = "Preparing import..."
        }
        
        defer {
            Task { @MainActor in
                isImporting = false
            }
        }
        
        // Check file extension
        let fileExtension = url.pathExtension.lowercased()
        guard fileExtension == "db" || fileExtension == "zip" else {
            logger.error("Invalid file extension: \(fileExtension)")
            throw ImportError.invalidFileType
        }
        
        // Start security-scoped access if needed
        // With asCopy: true in UIDocumentPickerViewController, this might not be needed
        // but we'll keep it for safety
        let accessing = url.startAccessingSecurityScopedResource()
        defer {
            if accessing {
                url.stopAccessingSecurityScopedResource()
            }
        }

        logger.error("🟢 Security-scoped resource access started: \(accessing)")

        // Verify the file exists and is readable
        guard FileManager.default.fileExists(atPath: url.path) else {
            logger.error("File does not exist at path: \(url.path)")
            throw ImportError.invalidFileType
        }

        // Check file size
        let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
        let fileSize = attributes[.size] as? Int64 ?? 0
        logger.info("File size: \(fileSize) bytes")

        // Allow files as small as 1KB to match Android functionality
        // Custom language databases can be very small
        if fileSize < 1000 {
            logger.error("File is too small: \(fileSize) bytes (minimum 1KB)")
            throw ImportError.fileTooSmall
        }

        // Read first few bytes to check file type
        do {
            let fileHandle = try FileHandle(forReadingFrom: url)
            defer {
                try? fileHandle.close()
            }

            let headerData = fileHandle.readData(ofLength: 16)

            if headerData.count >= 4 {
                let signature = headerData.withUnsafeBytes { bytes in
                    bytes.loadUnaligned(as: UInt32.self)
                }
                logger.error("🟢 File signature: 0x\(String(format: "%08X", signature))")

                // Check common file signatures
                switch signature {
                case 0x04034B50:
                    logger.error("🟢 Detected: Standard ZIP file")
                case 0x06054B50:
                    logger.error("🟢 Detected: Empty ZIP file")
                case 0x08074B50:
                    logger.error("🟢 Detected: Spanned ZIP file")
                case 0x1F8B0800, 0x1F8B0808:
                    logger.error("🟢 Detected: GZIP file (not ZIP)")
                case 0x53514C69:
                    logger.error("🟢 Detected: SQLite database file")
                default:
                    // Check if it's ASCII text (HTML from failed download)
                    if let str = String(data: headerData, encoding: .utf8) {
                        logger.error("🟢 File appears to be text: \(str.prefix(50))")
                    } else {
                        logger.error("🟢 Unknown file format")
                    }
                }
            }

            // Also check the last part of the file
            let fileSize = try fileHandle.seekToEnd()
            if fileSize > 100 {
                try fileHandle.seek(toOffset: fileSize - 100)
                let tailData = fileHandle.readData(ofLength: 100)
                let tailHex = tailData.map { String(format: "%02X", $0) }.joined(separator: " ")
                logger.error("🟢 Last 100 bytes: \(tailHex)")

                // Check for ZIP end signature
                let eocdSig: UInt32 = 0x06054B50
                var foundEOCD = false
                for i in 0..<(tailData.count - 4) {
                    let sig = tailData.withUnsafeBytes { bytes in
                        bytes.loadUnaligned(fromByteOffset: i, as: UInt32.self)
                    }
                    if sig == eocdSig {
                        logger.error("🟢 Found EOCD signature at offset \(i) from end")
                        foundEOCD = true
                        break
                    }
                }
                if !foundEOCD {
                    logger.error("🟢 No EOCD signature found in last 100 bytes")
                }
            }
        } catch {
            logger.error("🟢 Failed to read file for analysis: \(error)")
        }

        // Copy the file to our app's temporary directory to ensure we maintain access
        // CRITICAL: Use streaming copy to avoid loading entire file into memory
        let tempInputURL: URL
        if fileExtension == "zip" {
            tempInputURL = FileManager.default.temporaryDirectory.appendingPathComponent("import_\(UUID().uuidString).zip")
            logger.error("🟢 Copying ZIP file to temporary location: \(tempInputURL.path)")

            do {
                logger.error("🟢 About to copy from: \(url.path)")
                logger.error("🟢 About to copy to: \(tempInputURL.path)")

                // Use streaming copy to avoid memory pressure on large files
                // This copies in 1MB chunks instead of loading entire file into memory
                try streamingCopyFile(from: url, to: tempInputURL)

                let copiedSize = (try? FileManager.default.attributesOfItem(atPath: tempInputURL.path)[.size] as? Int64) ?? 0
                logger.error("🟢 ZIP file copied successfully (streaming), size: \(copiedSize) bytes")

                // Verify the copy matches original
                if copiedSize != fileSize {
                    logger.error("🟢 WARNING: Size mismatch! Original: \(fileSize), Copied: \(copiedSize)")
                }
            } catch {
                logger.error("🟢 Failed to copy ZIP file: \(error)")
                logger.error("🟢 Error type: \(type(of: error))")
                logger.error("🟢 Error details: \(error)")
                throw ImportError.extractionFailed("Cannot copy file: \(error.localizedDescription)")
            }
        } else {
            tempInputURL = url // For non-ZIP files, use the original URL
        }

        // Clean up temp input file when done (only if we created a copy)
        defer {
            if fileExtension == "zip" {
                try? FileManager.default.removeItem(at: tempInputURL)
            }
        }

        // Get destination path
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let destinationPath = documentsPath.appendingPathComponent("perseus_texts.db")
        let tempPath = documentsPath.appendingPathComponent("perseus_texts_temp.db")
        
        logger.error("🟢 Documents path: \(documentsPath.path)")
        logger.error("🟢 Destination DB path: \(destinationPath.path)")
        logger.error("🟢 Temp DB path: \(tempPath.path)")
        logger.error("🟢 Import starting for file: \(url.lastPathComponent)")
        logger.error("🟢 File extension: \(fileExtension)")
        
        // Clean up any existing temp file
        try? FileManager.default.removeItem(at: tempPath)
        
        do {
            if fileExtension == "zip" {
                // Extract ZIP file
                await MainActor.run {
                    importStatus = "Extracting database from ZIP..."
                }

                logger.info("Starting ZIP extraction from \(tempInputURL.path)")
                let zipSize = try FileManager.default.attributesOfItem(atPath: tempInputURL.path)[.size] as? Int64 ?? 0
                logger.info("ZIP file size: \(zipSize) bytes (\(zipSize / 1024 / 1024) MB)")

                await MainActor.run {
                    importStatus = "Extracting \(zipSize / 1024 / 1024) MB database..."
                }

                // Check if we have enough free space
                let fileManager = FileManager.default
                if let attributes = try? fileManager.attributesOfFileSystem(forPath: NSTemporaryDirectory()),
                   let freeSpace = attributes[.systemFreeSize] as? Int64 {
                    logger.info("Free space available: \(freeSpace / 1024 / 1024) MB")
                    // Need at least 2GB for extraction (compressed + uncompressed)
                    if freeSpace < 2_000_000_000 {
                        throw ImportError.extractionFailed("Insufficient storage space. Need at least 2GB free.")
                    }
                }

                do {
                    try await extractDatabaseFromZip(tempInputURL, to: tempPath) { progress in
                        logger.debug("Extraction progress: \(progress * 100)%")
                        Task { @MainActor in
                            self.importProgress = progress * 0.5 // First 50% is extraction
                            let percentComplete = Int(progress * 100)
                            self.importStatus = "Extracting database: \(percentComplete)%"
                        }
                    }
                } catch {
                    logger.error("ZIP extraction failed with error: \(error)")

                    // Check if it's a ZIP integrity issue
                    if error.localizedDescription.contains("Cannot find End of Central Directory") {
                        // Try to provide helpful guidance
                        let helpMessage = """
                        The ZIP file appears to be corrupted or incomplete.

                        Possible causes:
                        1. Download was interrupted
                        2. File is still downloading
                        3. Browser modified the file

                        Solutions:
                        1. Delete the file and re-download
                        2. Try downloading with a different browser
                        3. Use the 'Files' app to verify the ZIP extracts properly
                        """
                        throw ImportError.extractionFailed(helpMessage)
                    } else {
                        throw ImportError.extractionFailed("ZIP extraction failed: \(error.localizedDescription)")
                    }
                }

                // Verify extracted file
                if !FileManager.default.fileExists(atPath: tempPath.path) {
                    logger.error("Extracted file does not exist at: \(tempPath.path)")
                    throw ImportError.extractionFailed("Extraction produced no output file")
                }

                let extractedSize = try FileManager.default.attributesOfItem(atPath: tempPath.path)[.size] as? Int64 ?? 0
                logger.info("Extracted database size: \(extractedSize) bytes (\(extractedSize / 1024 / 1024) MB)")

                if extractedSize < 1000 { // Less than 1KB is too small
                    logger.error("Extracted database is too small: \(extractedSize) bytes")
                    throw ImportError.extractionFailed("Extracted database is corrupted or incomplete")
                }
                
            } else {
                // Copy DB file directly
                await MainActor.run {
                    importStatus = "Reading database file..."
                    importProgress = 0.25
                }

                logger.info("Copying database from \(url.path) to \(tempPath.path)")

                let dbSize = try FileManager.default.attributesOfItem(atPath: url.path)[.size] as? Int64 ?? 0
                await MainActor.run {
                    importStatus = "Copying \(dbSize / 1024 / 1024) MB database..."
                    importProgress = 0.3
                }

                try FileManager.default.copyItem(at: url, to: tempPath)

                // Verify copied file
                let copiedSize = try FileManager.default.attributesOfItem(atPath: tempPath.path)[.size] as? Int64 ?? 0
                logger.info("Copied database size: \(copiedSize) bytes")

                await MainActor.run {
                    importStatus = "Database copied successfully"
                    importProgress = 0.5
                }
            }
            
            // Validate the database
            await MainActor.run {
                importStatus = "Opening database for validation..."
                importProgress = 0.6
            }
            
            // Ensure file is fully written and accessible
            if !FileManager.default.fileExists(atPath: tempPath.path) {
                throw ImportError.validationFailed("Temporary database file not found")
            }

            await MainActor.run {
                importStatus = "Checking database file integrity..."
                importProgress = 0.62
            }
            
            let tempSize = try FileManager.default.attributesOfItem(atPath: tempPath.path)[.size] as? Int64 ?? 0
            logger.info("Validating database at \(tempPath.path), size: \(tempSize) bytes")
            
            // Force file system sync to ensure all writes are completed
            let fd = open(tempPath.path, O_RDONLY)
            if fd != -1 {
                _ = fcntl(fd, F_FULLFSYNC)
                close(fd)
                logger.info("File system sync completed for \(tempPath.path)")
            }

            await MainActor.run {
                importStatus = "Preparing database for validation..."
                importProgress = 0.64
            }

            // Additional delay to ensure file system has finished writing
            logger.info("Waiting for file system to complete all operations...")
            try await Task.sleep(nanoseconds: 1_000_000_000) // 1 second
            
            // Verify the file is really there and readable
            let verifySize = try FileManager.default.attributesOfItem(atPath: tempPath.path)[.size] as? Int64 ?? 0
            logger.info("Re-verified database size after sync: \(verifySize) bytes")
            
            if verifySize != tempSize {
                logger.error("File size changed after sync! Was: \(tempSize), now: \(verifySize)")
            }
            
            // Log the exact path we're about to validate
            logger.error("🔵 === ABOUT TO VALIDATE ===")
            logger.error("🔵 Will validate database at URL: \(tempPath)")
            logger.error("🔵 Will validate database at path: \(tempPath.path)")
            logger.error("🔵 Absolute string: \(tempPath.absoluteString)")
            logger.error("🔵 Last path component: \(tempPath.lastPathComponent)")
            logger.error("🔵 File exists check BEFORE validation: \(FileManager.default.fileExists(atPath: tempPath.path))")
            let tempFileSize = try? FileManager.default.attributesOfItem(atPath: tempPath.path)[.size] as? Int64 ?? 0
            logger.error("🔵 File size BEFORE validation: \(tempFileSize ?? 0) bytes")
            
            await MainActor.run {
                importStatus = "Starting database validation..."
                importProgress = 0.66
            }

            let validator = DatabaseValidator()
            logger.error("🔵 === CALLING validator.generateValidationReport ===")
            let report = try await validator.generateValidationReport(for: tempPath) { status in
                Task { @MainActor in
                    self.importStatus = status
                    // Update progress based on which stage we're at
                    if status.contains("table structures") {
                        self.importProgress = 0.68
                    } else if status.contains("Counting rows") {
                        self.importProgress = 0.72
                    } else if status.contains("integrity check") {
                        self.importProgress = 0.75
                    }
                }
            }
            logger.error("🔵 === RETURNED from validator.generateValidationReport ===")
            
            await MainActor.run {
                self.validationReport = report
                importProgress = 0.8
            }
            
            logger.info("Validation report:")
            logger.info("  - Valid: \(report.isValid)")
            logger.info("  - Table count: \(report.tableCount)")
            logger.info("  - Author count: \(report.authorCount)")
            logger.info("  - Book count: \(report.bookCount)")
            logger.info("  - Line count: \(report.lineCount)")
            logger.info("  - Issues: \(report.issues.joined(separator: ", "))")
            
            if !report.isValid {
                logger.error("🔵 Validation failed, about to clean up temp file")
                logger.error("🔵 File exists BEFORE cleanup: \(FileManager.default.fileExists(atPath: tempPath.path))")
                // Clean up temp file
                try? FileManager.default.removeItem(at: tempPath)
                logger.error("🔵 File exists AFTER cleanup: \(FileManager.default.fileExists(atPath: tempPath.path))")
                
                // Format detailed validation errors
                var detailedMessage = "Database validation failed:\n\n"
                for issue in report.issues {
                    detailedMessage += "• \(issue)\n"
                }
                
                logger.error("Validation failed with \(report.issues.count) issues")
                for issue in report.issues {
                    logger.error("  - \(issue)")
                }
                
                throw ImportError.validationFailed(detailedMessage)
            }
            
            // Check minimum data requirements
            if report.authorCount < 1 || report.bookCount < 1 || report.lineCount < 100 {
                logger.error("🔵 Insufficient data, about to clean up temp file")
                logger.error("🔵 File exists BEFORE cleanup: \(FileManager.default.fileExists(atPath: tempPath.path))")
                try? FileManager.default.removeItem(at: tempPath)
                logger.error("🔵 File exists AFTER cleanup: \(FileManager.default.fileExists(atPath: tempPath.path))")
                throw ImportError.validationFailed("Database contains insufficient data")
            }
            
            // Remove existing database if present
            if FileManager.default.fileExists(atPath: destinationPath.path) {
                await MainActor.run {
                    importStatus = "Backing up current database..."
                    importProgress = 0.82
                }

                // Close all database connections before removing the file
                logger.info("Closing all database connections before replacement")
                await DatabaseManagerAsync.shared.close()
                await UserDatabaseManagerAsync.shared.close()

                // Small delay to ensure SQLite has fully released the file
                try await Task.sleep(nanoseconds: 500_000_000) // 0.5 seconds

                await MainActor.run {
                    importStatus = "Removing old database..."
                    importProgress = 0.85
                }

                logger.info("Removing old database file")
                try FileManager.default.removeItem(at: destinationPath)
            }
            
            // Move validated database to final location
            await MainActor.run {
                importStatus = "Installing new database..."
                importProgress = 0.90
            }
            
            try FileManager.default.moveItem(at: tempPath, to: destinationPath)

            await MainActor.run {
                importStatus = "Verifying installation..."
                importProgress = 0.95
            }

            // Quick verification that the database is in place
            let finalSize = try FileManager.default.attributesOfItem(atPath: destinationPath.path)[.size] as? Int64 ?? 0
            logger.info("Final database size: \(finalSize) bytes")

            await MainActor.run {
                importStatus = "Import successful!"
                importProgress = 1.0
            }

            logger.info("Database import completed successfully")
            
        } catch {
            // Clean up temp file on error
            try? FileManager.default.removeItem(at: tempPath)
            throw error
        }
    }
    
    // MARK: - ZIP Extraction
    
    private func extractDatabaseFromZip(_ zipURL: URL, to destinationURL: URL, progress: @escaping (Double) -> Void) async throws {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")
        do {
            logger.info("Starting ZIPHandler.extractDatabase from \(zipURL.path) to \(destinationURL.path)")
            
            // Check source file exists
            if !FileManager.default.fileExists(atPath: zipURL.path) {
                throw ImportError.extractionFailed("Source ZIP file does not exist")
            }
            
            let zipSize = try FileManager.default.attributesOfItem(atPath: zipURL.path)[.size] as? Int64 ?? 0
            logger.info("ZIP file size: \(zipSize) bytes")
            
            // Use the ZIPHandler for proper extraction
            try ZIPHandler.extractDatabase(from: zipURL, to: destinationURL, progress: progress)
            
            // Verify extraction
            if FileManager.default.fileExists(atPath: destinationURL.path) {
                let extractedSize = try FileManager.default.attributesOfItem(atPath: destinationURL.path)[.size] as? Int64 ?? 0
                logger.info("ZIPHandler.extractDatabase completed successfully, extracted size: \(extractedSize) bytes")
            } else {
                logger.error("Extraction completed but file not found at destination")
                throw ImportError.extractionFailed("Extraction failed - no output file")
            }
        } catch {
            logger.error("ZIP extraction failed: \(error, privacy: .public)")
            if let zipError = error as? ZIPHandler.ZIPError {
                throw ImportError.extractionFailed(zipError.localizedDescription)
            } else {
                throw ImportError.extractionFailed(error.localizedDescription)
            }
        }
    }
    
    
    // MARK: - Revert to Bundled Database
    
    func revertToBundledDatabase() async throws {
        await MainActor.run {
            isImporting = true
            importProgress = 0.0
            importStatus = "Reverting to bundled database..."
        }
        
        defer {
            Task { @MainActor in
                isImporting = false
            }
        }
        
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let destinationPath = documentsPath.appendingPathComponent("perseus_texts.db")
        
        // Remove current database
        await MainActor.run {
            importStatus = "Removing current database..."
            importProgress = 0.2
        }

        if FileManager.default.fileExists(atPath: destinationPath.path) {
            // Close all database connections before removing the file
            await DatabaseManagerAsync.shared.close()
            await UserDatabaseManagerAsync.shared.close()

            // Small delay to ensure SQLite has fully released the file
            try await Task.sleep(nanoseconds: 500_000_000) // 0.5 seconds

            try FileManager.default.removeItem(at: destinationPath)
        }
        
        // Extract bundled database
        await MainActor.run {
            importStatus = "Extracting bundled database..."
            importProgress = 0.4
        }
        
        let extractor = DatabaseExtractor.shared
        try await extractor.extractBundledDatabase { progress in
            Task { @MainActor in
                self.importProgress = 0.4 + (progress * 0.5)
            }
        }
        
        await MainActor.run {
            importStatus = "Bundled database restored!"
            importProgress = 1.0
        }
    }
    
    // MARK: - Database Info
    
    func getCurrentDatabaseInfo() -> DatabaseInfo? {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let databasePath = documentsPath.appendingPathComponent("perseus_texts.db")
        
        guard FileManager.default.fileExists(atPath: databasePath.path) else {
            return nil
        }
        
        do {
            let attributes = try FileManager.default.attributesOfItem(atPath: databasePath.path)
            let fileSize = attributes[.size] as? Int64 ?? 0
            let modificationDate = attributes[.modificationDate] as? Date ?? Date()
            
            return DatabaseInfo(
                path: databasePath.path,
                size: fileSize,
                lastModified: modificationDate
            )
        } catch {
            return nil
        }
    }
    
    struct DatabaseInfo {
        let path: String
        let size: Int64
        let lastModified: Date

        var sizeFormatted: String {
            let formatter = ByteCountFormatter()
            formatter.countStyle = .file
            return formatter.string(fromByteCount: size)
        }
    }

    // MARK: - Streaming File Copy

    /// Copies a file using streaming to avoid loading the entire file into memory.
    /// Critical for large database ZIP files (300MB+) that would cause out-of-memory crashes.
    private func streamingCopyFile(from sourceURL: URL, to destinationURL: URL) throws {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")

        // Remove destination if it exists
        if FileManager.default.fileExists(atPath: destinationURL.path) {
            try FileManager.default.removeItem(at: destinationURL)
        }

        // Open source for reading
        guard let inputStream = InputStream(url: sourceURL) else {
            throw ImportError.extractionFailed("Cannot open source file for reading")
        }

        // Create and open output stream
        guard let outputStream = OutputStream(url: destinationURL, append: false) else {
            throw ImportError.extractionFailed("Cannot create destination file for writing")
        }

        inputStream.open()
        outputStream.open()

        defer {
            inputStream.close()
            outputStream.close()
        }

        // Check streams opened successfully
        if inputStream.streamStatus == .error {
            throw ImportError.extractionFailed("Failed to open source file: \(inputStream.streamError?.localizedDescription ?? "unknown error")")
        }
        if outputStream.streamStatus == .error {
            throw ImportError.extractionFailed("Failed to create destination file: \(outputStream.streamError?.localizedDescription ?? "unknown error")")
        }

        // Use 1MB buffer for efficient streaming (same as Android approach)
        let bufferSize = 1024 * 1024
        let buffer = UnsafeMutablePointer<UInt8>.allocate(capacity: bufferSize)
        defer { buffer.deallocate() }

        var totalBytesCopied: Int64 = 0

        while inputStream.hasBytesAvailable {
            let bytesRead = inputStream.read(buffer, maxLength: bufferSize)

            if bytesRead < 0 {
                throw ImportError.extractionFailed("Error reading source file: \(inputStream.streamError?.localizedDescription ?? "unknown error")")
            }

            if bytesRead == 0 {
                break // End of file
            }

            var bytesWritten = 0
            while bytesWritten < bytesRead {
                let writeResult = outputStream.write(buffer.advanced(by: bytesWritten), maxLength: bytesRead - bytesWritten)
                if writeResult < 0 {
                    throw ImportError.extractionFailed("Error writing destination file: \(outputStream.streamError?.localizedDescription ?? "unknown error")")
                }
                bytesWritten += writeResult
            }

            totalBytesCopied += Int64(bytesRead)
        }

        logger.info("Streaming copy completed: \(totalBytesCopied) bytes copied")
    }
}