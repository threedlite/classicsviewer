import Foundation
import Compression
import os.log

typealias Logger = os.Logger

class ZIPHandler {
    
    enum ZIPError: LocalizedError {
        case invalidZIPFile
        case noEntryFound
        case extractionFailed(String)
        case compressionFailed
        case invalidCentralDirectory
        case cannotOpenFile
        case cannotCreateFile
        case decompressionFailed

        var errorDescription: String? {
            switch self {
            case .invalidZIPFile:
                return "Invalid or corrupted ZIP file"
            case .noEntryFound:
                return "No matching entry found in ZIP archive"
            case .extractionFailed(let reason):
                return "Extraction failed: \(reason)"
            case .compressionFailed:
                return "Compression failed"
            case .invalidCentralDirectory:
                return "ZIP central directory is invalid"
            case .cannotOpenFile:
                return "Cannot open ZIP file"
            case .cannotCreateFile:
                return "Cannot create output file"
            case .decompressionFailed:
                return "Decompression failed"
            }
        }
    }
    
    // ZIP file structures
    struct LocalFileHeader {
        let signature: UInt32 = 0x04034b50
        let version: UInt16
        let flags: UInt16
        let compression: UInt16
        let modTime: UInt16
        let modDate: UInt16
        let crc32: UInt32
        let compressedSize: UInt64  // Changed to UInt64 for ZIP64 support
        let uncompressedSize: UInt64  // Changed to UInt64 for ZIP64 support
        let fileNameLength: UInt16
        let extraFieldLength: UInt16
        let fileName: String
        let dataOffset: UInt64
    }
    
    struct CentralDirectoryFileHeader {
        let signature: UInt32 = 0x02014b50
        let versionMadeBy: UInt16
        let versionNeeded: UInt16
        let flags: UInt16
        let compression: UInt16
        let modTime: UInt16
        let modDate: UInt16
        let crc32: UInt32
        let compressedSize: UInt64  // Changed to UInt64 for ZIP64 support
        let uncompressedSize: UInt64  // Changed to UInt64 for ZIP64 support
        let fileNameLength: UInt16
        let extraFieldLength: UInt16
        let commentLength: UInt16
        let diskNumberStart: UInt16
        let internalAttributes: UInt16
        let externalAttributes: UInt32
        let localHeaderOffset: UInt64  // Changed to UInt64 for ZIP64 support
        let fileName: String
    }
    
    struct EndOfCentralDirectory {
        let signature: UInt32 = 0x06054b50
        let diskNumber: UInt16
        let diskWithCentralDir: UInt16
        let numEntriesThisDisk: UInt16
        let numEntriesTotal: UInt16
        let centralDirSize: UInt32
        let centralDirOffset: UInt32
        let commentLength: UInt16
    }
    
    // MARK: - Extract Database from ZIP
    
    /// Extract all files from a ZIP archive to a directory
    static func extractAll(from zipURL: URL, to destinationDirectory: URL, progress: ((Double) -> Void)? = nil) throws {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "ZIPExtraction")
        
        logger.info("ZIPHandler - Loading ZIP file from \(zipURL.path)")
        let zipData = try Data(contentsOf: zipURL)
        logger.info("ZIPHandler - ZIP data loaded, size: \(zipData.count) bytes")
        
        // Find End of Central Directory
        logger.info("ZIPHandler - Finding End of Central Directory")
        guard let eocd = findEndOfCentralDirectory(in: zipData) else {
            logger.error("ZIPHandler - Failed to find End of Central Directory")
            throw ZIPError.invalidZIPFile
        }
        logger.info("ZIPHandler - Found EOCD, entries: \(eocd.numEntriesTotal)")
        
        // Parse Central Directory
        logger.info("ZIPHandler - Parsing Central Directory")
        let entries = try parseCentralDirectory(in: zipData, eocd: eocd)
        logger.info("ZIPHandler - Found \(entries.count) entries in ZIP")
        
        // Create destination directory if needed
        try FileManager.default.createDirectory(at: destinationDirectory, withIntermediateDirectories: true)
        
        // Extract each file
        for (index, entry) in entries.enumerated() {
            let entryProgress = Double(index) / Double(entries.count)
            progress?(entryProgress)
            
            // Skip directories
            if entry.fileName.hasSuffix("/") {
                continue
            }
            
            logger.info("ZIPHandler - Extracting: \(entry.fileName)")
            
            // Create full path for the file
            let filePath = destinationDirectory.appendingPathComponent(entry.fileName)
            
            // Create parent directories if needed
            let parentDir = filePath.deletingLastPathComponent()
            try FileManager.default.createDirectory(at: parentDir, withIntermediateDirectories: true)
            
            // Extract the file
            try extractEntry(entry, from: zipData, to: filePath, progress: nil)
        }
        
        progress?(1.0)
        logger.info("ZIPHandler - All files extracted successfully")
    }
    
    static func extractDatabase(from zipURL: URL, to destinationURL: URL, progress: ((Double) -> Void)? = nil) throws {
        print(" ZIPHandler.extractDatabase CALLED")
        print(" Source: \(zipURL.path)")
        print(" Destination: \(destinationURL.path)")
        
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")
        
        logger.error(" ZIPHandler.extractDatabase - ENTRY POINT CALLED")
        logger.error(" ZIPHandler.extractDatabase - Source: \(zipURL.path)")
        logger.error(" ZIPHandler.extractDatabase - Destination: \(destinationURL.path)")
        
        // Check if source exists
        if !FileManager.default.fileExists(atPath: zipURL.path) {
            logger.error(" ZIPHandler.extractDatabase - SOURCE FILE DOES NOT EXIST!")
            throw ZIPError.extractionFailed("Source file does not exist")
        }
        
        // For large files (>1GB), use the system unzip command which handles ZIP64 properly
        // Check file size first
        let attributes = try FileManager.default.attributesOfItem(atPath: zipURL.path)
        let fileSize = attributes[.size] as? Int64 ?? 0
        logger.error(" ZIPHandler.extractDatabase - ZIP file size: \(fileSize) bytes (\(fileSize / 1_000_000) MB)")
        
        // Use streaming extraction for database-sized files to avoid memory pressure
        // Any database ZIP >10MB should use streaming to stay memory-safe
        if fileSize > 10_000_000 { // > 10MB
            logger.error(" ZIPHandler.extractDatabase - File >10MB detected, using streaming extraction")
            do {
                logger.error(" ZIPHandler.extractDatabase - About to call extractDatabaseUsingSystemUnzip")
                try extractDatabaseUsingSystemUnzip(from: zipURL, to: destinationURL, progress: progress)
                logger.error(" ZIPHandler.extractDatabase - extractDatabaseUsingSystemUnzip returned successfully")
                
                // Verify the file was created
                if FileManager.default.fileExists(atPath: destinationURL.path) {
                    let extractedSize = try FileManager.default.attributesOfItem(atPath: destinationURL.path)[.size] as? Int64 ?? 0
                    logger.error(" ZIPHandler.extractDatabase - Successfully extracted \(extractedSize) bytes to \(destinationURL.path)")
                } else {
                    logger.error(" ZIPHandler.extractDatabase - Extraction completed but file not created at \(destinationURL.path)")
                    throw ZIPError.extractionFailed("No output file created")
                }
                return
            } catch {
                logger.error(" ZIPHandler.extractDatabase - Streaming extraction failed with error: \(error)")
                logger.error(" ZIPHandler.extractDatabase - Error type: \(type(of: error))")
                logger.error(" ZIPHandler.extractDatabase - Error localized: \(error.localizedDescription)")
                throw error
            }
        }
        
        // For smaller files, use our implementation
        logger.info("ZIPHandler - Loading ZIP file from \(zipURL.path)")
        let zipData = try Data(contentsOf: zipURL)
        logger.info("ZIPHandler - ZIP data loaded, size: \(zipData.count) bytes")
        
        // Find End of Central Directory
        logger.info("ZIPHandler - Finding End of Central Directory")
        guard let eocd = findEndOfCentralDirectory(in: zipData) else {
            logger.error("ZIPHandler - Failed to find End of Central Directory")
            throw ZIPError.invalidZIPFile
        }
        logger.info("ZIPHandler - Found EOCD, entries: \(eocd.numEntriesTotal)")
        
        // Parse Central Directory
        logger.info("ZIPHandler - Parsing Central Directory")
        let entries = try parseCentralDirectory(in: zipData, eocd: eocd)
        logger.info("ZIPHandler - Found \(entries.count) entries in ZIP")
        
        // List all entries
        for entry in entries {
            logger.info("ZIPHandler - Entry: \(entry.fileName), compressed: \(entry.compressedSize), uncompressed: \(entry.uncompressedSize)")
        }
        
        // Find database file
        guard let dbEntry = entries.first(where: { $0.fileName.hasSuffix(".db") }) else {
            logger.error("ZIPHandler - No .db file found in ZIP archive")
            throw ZIPError.noEntryFound
        }
        logger.info("ZIPHandler - Found database file: \(dbEntry.fileName)")
        
        // Extract the database file
        logger.info("ZIPHandler - Starting extraction of \(dbEntry.fileName)")
        try extractEntry(dbEntry, from: zipData, to: destinationURL, progress: progress)
        logger.info("ZIPHandler - Extraction completed successfully")
    }
    
    // MARK: - Apple-approved ZIP extraction using Foundation

    private static func extractDatabaseUsingSystemUnzip(from zipURL: URL, to destinationURL: URL, progress: ((Double) -> Void)? = nil) throws {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")

        logger.error("🔵 extractDatabaseUsingSystemUnzip - USING APPLE APPROVED ZIP EXTRACTION")
        logger.error("🔵 Source: \(zipURL.path)")
        logger.error("🔵 Destination: \(destinationURL.path)")

        // Check file size first
        let fileAttributes = try FileManager.default.attributesOfItem(atPath: zipURL.path)
        let fileSize = fileAttributes[.size] as? Int64 ?? 0
        logger.error("🔵 ZIP file size: \(fileSize) bytes")

        // For files >10MB, use streaming extraction to avoid memory pressure
        // This is critical for database imports which can be 100MB+ compressed
        // The streaming approach uses ~10MB of memory regardless of file size
        if fileSize > 10_000_000 {
            logger.error("🔵 File >10MB detected, using streaming extraction for memory efficiency")
            try extractUsingSystemCommand(from: zipURL, to: destinationURL, progress: progress)
            return
        }

        // Use NSFileCoordinator for thread-safe file access (Apple recommended)
        var coordinatorError: NSError?
        var extractionError: Error?

        let coordinator = NSFileCoordinator()
        coordinator.coordinate(readingItemAt: zipURL, options: [], error: &coordinatorError) { (readingURL) in
            do {
                // Load ZIP data using Foundation (only for small files)
                logger.error("🔵 Loading ZIP file using Apple Foundation frameworks...")
                let zipData = try Data(contentsOf: readingURL)
                logger.error("🔵 ZIP data loaded successfully: \(zipData.count) bytes")
                
                // Find End of Central Directory using Foundation
                guard let eocd = findEndOfCentralDirectory(in: zipData) else {
                    throw ZIPError.invalidZIPFile
                }
                
                // Parse Central Directory using Foundation
                let entries = try parseCentralDirectory(in: zipData, eocd: eocd)
                logger.error("🔵 Found \(entries.count) entries in ZIP using Foundation")
                
                // Find database file entry
                guard let dbEntry = entries.first(where: { $0.fileName.hasSuffix(".db") }) else {
                    throw ZIPError.noEntryFound
                }
                
                logger.error("🔵 Found database file: \(dbEntry.fileName)")
                logger.error("🔵 Compressed: \(dbEntry.compressedSize) bytes, Uncompressed: \(dbEntry.uncompressedSize) bytes")
                
                // Use Foundation's decompression for large files
                // This uses Apple's compression framework properly
                try extractLargeEntryUsingFoundation(dbEntry, from: zipData, to: destinationURL, progress: progress)
                
                logger.error("🔵 Apple Foundation extraction completed successfully")
                logger.error("🔵 About to sync file system")
                logger.error("🔵 Sync destination URL: \(destinationURL)")
                logger.error("🔵 Sync destination path: \(destinationURL.path)")
                logger.error("🔵 Sync absolute string: \(destinationURL.absoluteString)")
                
                // Force file system sync to ensure write is complete
                let fd = open(destinationURL.path, O_RDONLY)
                logger.error("🔵 File descriptor from open(): \(fd)")
                if fd != -1 {
                    let syncResult = fcntl(fd, F_FULLFSYNC)
                    logger.error("🔵 fcntl(F_FULLFSYNC) result: \(syncResult)")
                    let closeResult = close(fd)
                    logger.error("🔵 close() result: \(closeResult)")
                    logger.error("🔵 File system sync completed")
                } else {
                    logger.error("🔵 WARNING: Could not open file for sync, errno: \(errno)")
                }
                
            } catch {
                extractionError = error
                logger.error("🔵 Apple Foundation extraction failed: \(error)")
            }
        }
        
        if let coordinatorError = coordinatorError {
            throw ZIPError.extractionFailed("File coordination failed: \(coordinatorError.localizedDescription)")
        }
        
        if let extractionError = extractionError {
            throw extractionError
        }
        
        progress?(1.0)
    }
    
    // MARK: - Memory-Efficient Streaming Extraction for Large Files

    private static func extractUsingSystemCommand(from zipURL: URL, to destinationURL: URL, progress: ((Double) -> Void)? = nil) throws {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")
        logger.error("🟢 extractUsingSystemCommand - Using streaming extraction for large file")

        // Check if file exists and is readable
        guard FileManager.default.fileExists(atPath: zipURL.path) else {
            logger.error("🟢 File does not exist at path: \(zipURL.path)")
            throw ZIPError.cannotOpenFile
        }

        // Check file header to verify it's a ZIP
        guard let fileHandle = FileHandle(forReadingAtPath: zipURL.path) else {
            logger.error("🟢 Cannot open file for reading: \(zipURL.path)")
            throw ZIPError.cannotOpenFile
        }
        defer { fileHandle.closeFile() }

        // Read first 4 bytes to check ZIP signature
        let headerData = fileHandle.readData(ofLength: 4)
        if headerData.count >= 4 {
            // Check for ZIP signature in both byte orders
            let signatureBE = headerData.withUnsafeBytes { bytes in
                bytes.loadUnaligned(as: UInt32.self).bigEndian
            }
            let signatureLE = headerData.withUnsafeBytes { bytes in
                bytes.loadUnaligned(as: UInt32.self).littleEndian
            }

            logger.error("🟢 File signature BE: 0x\(String(format: "%08X", signatureBE)), LE: 0x\(String(format: "%08X", signatureLE))")

            // Check if it's a valid ZIP signature (PK\x03\x04 or PK\x05\x06)
            let validSignatures: Set<UInt32> = [0x504B0304, 0x504B0506, 0x504B0708]

            if !validSignatures.contains(signatureBE) && !validSignatures.contains(signatureLE) {
                logger.error("🟢 Not a valid ZIP file signature")
                // Check if it might be a different format
                if signatureBE == 0x1F8B0800 || signatureLE == 0x1F8B0800 {
                    logger.error("🟢 This appears to be a GZIP file, not a ZIP file")
                }
                throw ZIPError.invalidZIPFile
            }
        }

        // Read EOCD without loading entire file
        let fileSize = try fileHandle.seekToEnd()
        logger.error("🟢 File size: \(fileSize) bytes")

        if fileSize < 22 {
            logger.error("🟢 File too small to be a valid ZIP")
            throw ZIPError.invalidZIPFile
        }

        // Read last 64KB for EOCD (should be enough for any ZIP)
        let eocdSearchSize = min(65536, Int(fileSize))
        try fileHandle.seek(toOffset: fileSize - UInt64(eocdSearchSize))
        let eocdData = fileHandle.readData(ofLength: eocdSearchSize)

        // Find EOCD - search for the signature bytes "PK\x05\x06"
        var eocdOffset: Int? = nil
        let eocdSignature: [UInt8] = [0x50, 0x4B, 0x05, 0x06]

        for i in 0...(eocdData.count - 22) {
            var match = true
            for j in 0..<4 {
                if eocdData[i + j] != eocdSignature[j] {
                    match = false
                    break
                }
            }
            if match {
                eocdOffset = i
                logger.error("🟢 Found EOCD at offset \(i)")
                break
            }
        }

        guard let eocdOffset = eocdOffset else {
            logger.error("🟢 Cannot find End of Central Directory signature")
            logger.error("🟢 Last 100 bytes of file (hex):")
            let last100 = eocdData.suffix(min(100, eocdData.count))
            let hexString = last100.map { String(format: "%02X", $0) }.joined(separator: " ")
            logger.error("🟢 \(hexString)")
            throw ZIPError.invalidZIPFile
        }

        // Parse EOCD
        let eocdStart = eocdOffset
        guard eocdStart + 22 <= eocdData.count else {
            throw ZIPError.invalidZIPFile
        }

        let eocdBytes = eocdData[eocdStart..<(eocdStart + 22)]
        let centralDirOffset = eocdBytes.withUnsafeBytes { bytes in
            bytes.loadUnaligned(fromByteOffset: 16, as: UInt32.self).littleEndian
        }

        logger.error("🟢 Central directory offset: \(centralDirOffset)")

        // Read central directory
        try fileHandle.seek(toOffset: UInt64(centralDirOffset))
        let centralDirData = fileHandle.readData(ofLength: 100000) // Should be enough for directory

        // Find .db file entry in central directory
        var offset = 0
        var dbEntry: (localHeaderOffset: UInt32, compressedSize: UInt32, uncompressedSize: UInt32, fileName: String)?

        while offset + 46 <= centralDirData.count {
            let signature = centralDirData.withUnsafeBytes { bytes in
                bytes.loadUnaligned(fromByteOffset: offset, as: UInt32.self).littleEndian
            }

            guard signature == 0x02014b50 else { break }

            let compressedSize = centralDirData.withUnsafeBytes { bytes in
                bytes.loadUnaligned(fromByteOffset: offset + 20, as: UInt32.self).littleEndian
            }
            let uncompressedSize = centralDirData.withUnsafeBytes { bytes in
                bytes.loadUnaligned(fromByteOffset: offset + 24, as: UInt32.self).littleEndian
            }
            let fileNameLength = centralDirData.withUnsafeBytes { bytes in
                bytes.loadUnaligned(fromByteOffset: offset + 28, as: UInt16.self).littleEndian
            }
            let localHeaderOffset = centralDirData.withUnsafeBytes { bytes in
                bytes.loadUnaligned(fromByteOffset: offset + 42, as: UInt32.self).littleEndian
            }

            let fileNameStart = offset + 46
            let fileNameEnd = fileNameStart + Int(fileNameLength)
            guard fileNameEnd <= centralDirData.count else { break }

            let fileName = String(data: centralDirData[fileNameStart..<fileNameEnd], encoding: .utf8) ?? ""

            if fileName.hasSuffix(".db") {
                dbEntry = (localHeaderOffset, compressedSize, uncompressedSize, fileName)
                logger.error("🟢 Found database: \(fileName), compressed: \(compressedSize), uncompressed: \(uncompressedSize)")
                break
            }

            // Move to next entry
            let extraFieldLength = centralDirData.withUnsafeBytes { bytes in
                bytes.loadUnaligned(fromByteOffset: offset + 30, as: UInt16.self)
            }
            let fileCommentLength = centralDirData.withUnsafeBytes { bytes in
                bytes.loadUnaligned(fromByteOffset: offset + 32, as: UInt16.self)
            }
            offset += 46 + Int(fileNameLength) + Int(extraFieldLength) + Int(fileCommentLength)
        }

        guard let entry = dbEntry else {
            throw ZIPError.noEntryFound
        }

        // Stream extract the database file
        try streamExtractEntry(from: fileHandle, entry: entry, to: destinationURL, progress: progress)
    }

    private static func streamExtractEntry(from fileHandle: FileHandle, entry: (localHeaderOffset: UInt32, compressedSize: UInt32, uncompressedSize: UInt32, fileName: String), to destinationURL: URL, progress: ((Double) -> Void)? = nil) throws {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")

        // Seek to local header
        try fileHandle.seek(toOffset: UInt64(entry.localHeaderOffset))
        let localHeader = fileHandle.readData(ofLength: 30)

        // Parse local header to get data offset
        let fileNameLength = localHeader.withUnsafeBytes { bytes in
            bytes.loadUnaligned(fromByteOffset: 26, as: UInt16.self)
        }
        let extraFieldLength = localHeader.withUnsafeBytes { bytes in
            bytes.loadUnaligned(fromByteOffset: 28, as: UInt16.self)
        }

        let dataOffset = entry.localHeaderOffset + 30 + UInt32(fileNameLength) + UInt32(extraFieldLength)

        // Seek to compressed data
        try fileHandle.seek(toOffset: UInt64(dataOffset))

        // Create output file
        FileManager.default.createFile(atPath: destinationURL.path, contents: nil)
        guard let outputHandle = FileHandle(forWritingAtPath: destinationURL.path) else {
            throw ZIPError.cannotCreateFile
        }
        defer { outputHandle.closeFile() }

        // Stream decompress using small chunks to avoid memory pressure
        let inputChunkSize = 64 * 1024 // 64KB input chunks
        let outputChunkSize = 256 * 1024 // 256KB output buffer
        var totalRead: UInt32 = 0
        var totalWritten: UInt64 = 0

        // Create decompression stream
        let emptyDstPtr = UnsafeMutablePointer<UInt8>.allocate(capacity: 0)
        let emptySrcPtr = UnsafePointer<UInt8>(emptyDstPtr)
        defer {
            emptyDstPtr.deallocate()
        }

        var stream = compression_stream(
            dst_ptr: emptyDstPtr,
            dst_size: 0,
            src_ptr: emptySrcPtr,
            src_size: 0,
            state: nil
        )

        var status = compression_stream_init(&stream, COMPRESSION_STREAM_DECODE, COMPRESSION_ZLIB)
        guard status == COMPRESSION_STATUS_OK else {
            throw ZIPError.decompressionFailed
        }
        defer { compression_stream_destroy(&stream) }

        // Allocate small buffers for streaming
        let outputBuffer = UnsafeMutablePointer<UInt8>.allocate(capacity: outputChunkSize)
        defer { outputBuffer.deallocate() }

        // Process in chunks
        while totalRead < entry.compressedSize || status == COMPRESSION_STATUS_OK {
            // Read input chunk if needed
            if stream.src_size == 0 && totalRead < entry.compressedSize {
                let remainingBytes = Int(entry.compressedSize - totalRead)
                let bytesToRead = min(inputChunkSize, remainingBytes)
                let chunkData = fileHandle.readData(ofLength: bytesToRead)

                chunkData.withUnsafeBytes { srcBytes in
                    stream.src_ptr = srcBytes.bindMemory(to: UInt8.self).baseAddress!
                    stream.src_size = chunkData.count
                }

                totalRead += UInt32(chunkData.count)
            }

            // Set up output buffer
            stream.dst_ptr = outputBuffer
            stream.dst_size = outputChunkSize

            // Decompress
            let flags: Int32 = (totalRead >= entry.compressedSize && stream.src_size == 0) ? Int32(COMPRESSION_STREAM_FINALIZE.rawValue) : 0
            status = compression_stream_process(&stream, flags)

            // Write decompressed data
            let bytesProduced = outputChunkSize - stream.dst_size
            if bytesProduced > 0 {
                let outputData = Data(bytes: outputBuffer, count: bytesProduced)
                outputHandle.write(outputData)
                totalWritten += UInt64(bytesProduced)
            }

            // Update progress
            progress?(Double(totalRead) / Double(entry.compressedSize))

            // Check for completion
            if status == COMPRESSION_STATUS_END {
                break
            } else if status != COMPRESSION_STATUS_OK {
                throw ZIPError.decompressionFailed
            }
        }

        logger.error("🟢 Successfully extracted \(entry.fileName), written: \(totalWritten) bytes")
    }

    private static func findEOCDOffset(in data: Data) -> Int? {
        // Search for EOCD signature bytes directly: PK\x05\x06 (50 4B 05 06)
        let signatureBytes: [UInt8] = [0x50, 0x4B, 0x05, 0x06]

        // Search from end of file backwards (EOCD is at the end)
        for i in (0...(data.count - 22)).reversed() {
            var found = true
            for j in 0..<4 {
                if data[i + j] != signatureBytes[j] {
                    found = false
                    break
                }
            }
            if found {
                return i
            }
        }
        return nil
    }

    private static func extractLargeZIP64Database(from zipURL: URL, to destinationURL: URL, progress: ((Double) -> Void)? = nil) throws {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")
        logger.error("🔵 ZIP64 extraction - Fallback to system unzip for ZIP64 files")
        
        // For ZIP64 files, the streaming decompression was failing
        // Use the system unzip as it handles ZIP64 properly
        try extractDatabaseUsingSystemUnzip(from: zipURL, to: destinationURL, progress: progress)
    }
    
    private static func parseLocalHeaderFromChunk(_ data: Data) throws -> LocalFileHeader? {
        guard data.count >= 30 else { return nil }
        
        return data.withUnsafeBytes { bytes in
            let base = bytes.baseAddress!
            
            let fileNameLength = base.advanced(by: 26).loadUnaligned(as: UInt16.self)
            let extraFieldLength = base.advanced(by: 28).loadUnaligned(as: UInt16.self)
            
            guard data.count >= 30 + Int(fileNameLength) else { return nil }
            
            let fileNameData = Data(bytes: base.advanced(by: 30), count: Int(fileNameLength))
            guard let fileName = String(data: fileNameData, encoding: .utf8) else { return nil }
            
            // Read sizes (may be ZIP64)
            let compressedSize32 = base.advanced(by: 18).loadUnaligned(as: UInt32.self)
            let uncompressedSize32 = base.advanced(by: 22).loadUnaligned(as: UInt32.self)
            
            var compressedSize = UInt64(compressedSize32)
            var uncompressedSize = UInt64(uncompressedSize32)
            
            // Check for ZIP64
            if compressedSize32 == 0xFFFFFFFF || uncompressedSize32 == 0xFFFFFFFF {
                // Parse ZIP64 extra field
                if extraFieldLength >= 4 && data.count >= 30 + Int(fileNameLength) + Int(extraFieldLength) {
                    let extraData = Data(bytes: base.advanced(by: 30 + Int(fileNameLength)), count: Int(extraFieldLength))
                    
                    extraData.withUnsafeBytes { extraBytes in
                        guard let extraBase = extraBytes.baseAddress else { return }
                        var pos = 0
                        
                        while pos + 4 <= Int(extraFieldLength) {
                            let headerId = extraBase.advanced(by: pos).loadUnaligned(as: UInt16.self)
                            let headerSize = extraBase.advanced(by: pos + 2).loadUnaligned(as: UInt16.self)
                            
                            if headerId == 0x0001 { // ZIP64 extra field
                                var fieldPos = pos + 4
                                if uncompressedSize32 == 0xFFFFFFFF && fieldPos + 8 <= pos + 4 + Int(headerSize) {
                                    uncompressedSize = extraBase.advanced(by: fieldPos).loadUnaligned(as: UInt64.self)
                                    fieldPos += 8
                                }
                                if compressedSize32 == 0xFFFFFFFF && fieldPos + 8 <= pos + 4 + Int(headerSize) {
                                    compressedSize = extraBase.advanced(by: fieldPos).loadUnaligned(as: UInt64.self)
                                }
                                break
                            }
                            pos += 4 + Int(headerSize)
                        }
                    }
                }
            }
            
            return LocalFileHeader(
                version: base.advanced(by: 4).loadUnaligned(as: UInt16.self),
                flags: base.advanced(by: 6).loadUnaligned(as: UInt16.self),
                compression: base.advanced(by: 8).loadUnaligned(as: UInt16.self),
                modTime: base.advanced(by: 10).loadUnaligned(as: UInt16.self),
                modDate: base.advanced(by: 12).loadUnaligned(as: UInt16.self),
                crc32: base.advanced(by: 14).loadUnaligned(as: UInt32.self),
                compressedSize: compressedSize,
                uncompressedSize: uncompressedSize,
                fileNameLength: fileNameLength,
                extraFieldLength: extraFieldLength,
                fileName: fileName,
                dataOffset: UInt64(30 + Int(fileNameLength) + Int(extraFieldLength))
            )
        }
    }
    
    struct SimplifiedEOCD {
        let numEntriesTotal: UInt64
        let centralDirectorySize: UInt64
        let centralDirectoryOffset: UInt64
    }
    
    private static func parseEndOfCentralDirectoryFromData(_ data: Data) -> SimplifiedEOCD? {
        guard data.count >= 22 else { return nil }
        
        return data.withUnsafeBytes { (bytes: UnsafeRawBufferPointer) in
            let base = bytes.baseAddress!
            
            let signature = base.loadUnaligned(as: UInt32.self)
            guard signature == 0x06054b50 else { return nil }
            
            let numEntriesTotal = base.advanced(by: 10).loadUnaligned(as: UInt16.self)
            let centralDirectorySize = base.advanced(by: 12).loadUnaligned(as: UInt32.self)
            let centralDirectoryOffset = base.advanced(by: 16).loadUnaligned(as: UInt32.self)
            
            // Check for ZIP64 - all fields are 0xFFFF or 0xFFFFFFFF for ZIP64
            if numEntriesTotal == 0xFFFF || centralDirectorySize == 0xFFFFFFFF || centralDirectoryOffset == 0xFFFFFFFF {
                // For ZIP64, we need to find and parse the ZIP64 EOCD
                // The real values will be there - for now use the 32-bit values if not maxed out
                var realNumEntries = UInt64(numEntriesTotal)
                var realCDSize = UInt64(centralDirectorySize)
                var realCDOffset = UInt64(centralDirectoryOffset)
                
                // If values are maxed out, we can't use them
                // This is a simplified approach - proper ZIP64 would need to find the ZIP64 EOCD record
                if numEntriesTotal == 0xFFFF {
                    realNumEntries = 1 // Assume at least 1 entry for database file
                }
                if centralDirectorySize == 0xFFFFFFFF {
                    // Can't determine real size without ZIP64 EOCD
                    realCDSize = 0
                }
                if centralDirectoryOffset == 0xFFFFFFFF {
                    // Can't determine real offset without ZIP64 EOCD
                    realCDOffset = 0
                }
                
                // Return what we have - the extraction will handle it
                return SimplifiedEOCD(
                    numEntriesTotal: realNumEntries,
                    centralDirectorySize: realCDSize,
                    centralDirectoryOffset: realCDOffset
                )
            }
            
            return SimplifiedEOCD(
                numEntriesTotal: UInt64(numEntriesTotal),
                centralDirectorySize: UInt64(centralDirectorySize),
                centralDirectoryOffset: UInt64(centralDirectoryOffset)
            )
        }
    }
    
    private static func parseCentralDirectoryData(_ data: Data, numEntries: Int) throws -> [CentralDirectoryFileHeader] {
        var entries: [CentralDirectoryFileHeader] = []
        var offset = 0
        
        for _ in 0..<numEntries {
            guard offset + 46 <= data.count else { break }
            
            let entry = try data.withUnsafeBytes { (bytes: UnsafeRawBufferPointer) in
                let base = bytes.baseAddress!.advanced(by: offset)
                
                let signature = base.loadUnaligned(as: UInt32.self)
                guard signature == 0x02014b50 else {
                    throw ZIPError.invalidCentralDirectory
                }
                
                let fileNameLength = base.advanced(by: 28).loadUnaligned(as: UInt16.self)
                let extraFieldLength = base.advanced(by: 30).loadUnaligned(as: UInt16.self)
                let commentLength = base.advanced(by: 32).loadUnaligned(as: UInt16.self)
                
                let fileNameData = Data(bytes: base.advanced(by: 46), count: Int(fileNameLength))
                let fileName = String(data: fileNameData, encoding: .utf8) ?? ""
                
                // Read standard 32-bit values
                let compressedSize32 = base.advanced(by: 20).loadUnaligned(as: UInt32.self)
                let uncompressedSize32 = base.advanced(by: 24).loadUnaligned(as: UInt32.self)
                let localHeaderOffset32 = base.advanced(by: 42).loadUnaligned(as: UInt32.self)
                
                // Convert to 64-bit, checking for ZIP64 marker
                var compressedSize = UInt64(compressedSize32)
                var uncompressedSize = UInt64(uncompressedSize32)
                var localHeaderOffset = UInt64(localHeaderOffset32)
                
                // Check for ZIP64 (0xFFFFFFFF indicates values in extra field)
                if compressedSize32 == 0xFFFFFFFF || uncompressedSize32 == 0xFFFFFFFF || localHeaderOffset32 == 0xFFFFFFFF {
                    // Parse ZIP64 extra field if present
                    if extraFieldLength >= 4 {
                        let extraStart = 46 + Int(fileNameLength)
                        let extraData = Data(bytes: base.advanced(by: extraStart), count: Int(extraFieldLength))
                        
                        extraData.withUnsafeBytes { extraBytes in
                            guard let extraBase = extraBytes.baseAddress else { return }
                            var pos = 0
                            
                            while pos + 4 <= Int(extraFieldLength) {
                                let headerId = extraBase.advanced(by: pos).loadUnaligned(as: UInt16.self)
                                let headerSize = extraBase.advanced(by: pos + 2).loadUnaligned(as: UInt16.self)
                                
                                if headerId == 0x0001 { // ZIP64 extra field
                                    var fieldPos = pos + 4
                                    
                                    // Read actual 64-bit values
                                    if uncompressedSize32 == 0xFFFFFFFF && fieldPos + 8 <= pos + 4 + Int(headerSize) {
                                        uncompressedSize = extraBase.advanced(by: fieldPos).loadUnaligned(as: UInt64.self)
                                        fieldPos += 8
                                    }
                                    
                                    if compressedSize32 == 0xFFFFFFFF && fieldPos + 8 <= pos + 4 + Int(headerSize) {
                                        compressedSize = extraBase.advanced(by: fieldPos).loadUnaligned(as: UInt64.self)
                                        fieldPos += 8
                                    }
                                    
                                    if localHeaderOffset32 == 0xFFFFFFFF && fieldPos + 8 <= pos + 4 + Int(headerSize) {
                                        localHeaderOffset = extraBase.advanced(by: fieldPos).loadUnaligned(as: UInt64.self)
                                    }
                                    
                                    break
                                }
                                
                                pos += 4 + Int(headerSize)
                            }
                        }
                    }
                }
                
                return CentralDirectoryFileHeader(
                    versionMadeBy: base.advanced(by: 4).loadUnaligned(as: UInt16.self),
                    versionNeeded: base.advanced(by: 6).loadUnaligned(as: UInt16.self),
                    flags: base.advanced(by: 8).loadUnaligned(as: UInt16.self),
                    compression: base.advanced(by: 10).loadUnaligned(as: UInt16.self),
                    modTime: base.advanced(by: 12).loadUnaligned(as: UInt16.self),
                    modDate: base.advanced(by: 14).loadUnaligned(as: UInt16.self),
                    crc32: base.advanced(by: 16).loadUnaligned(as: UInt32.self),
                    compressedSize: compressedSize,
                    uncompressedSize: uncompressedSize,
                    fileNameLength: fileNameLength,
                    extraFieldLength: extraFieldLength,
                    commentLength: commentLength,
                    diskNumberStart: base.advanced(by: 34).loadUnaligned(as: UInt16.self),
                    internalAttributes: base.advanced(by: 36).loadUnaligned(as: UInt16.self),
                    externalAttributes: base.advanced(by: 38).loadUnaligned(as: UInt32.self),
                    localHeaderOffset: localHeaderOffset,
                    fileName: fileName
                )
            }
            
            entries.append(entry)
            offset += 46 + Int(entry.fileNameLength) + Int(entry.extraFieldLength) + Int(entry.commentLength)
        }
        
        return entries
    }
    
    private static func parseLocalHeaderFieldsFromData(_ data: Data, at offset: UInt64) throws -> (fileNameLength: UInt16, extraFieldLength: UInt16) {
        guard data.count >= 30 else {
            throw ZIPError.extractionFailed("Local header too small")
        }
        
        return try data.withUnsafeBytes { bytes in
            let base = bytes.baseAddress!
            
            let signature = base.loadUnaligned(as: UInt32.self)
            guard signature == 0x04034b50 else {
                throw ZIPError.extractionFailed("Invalid local header signature")
            }
            
            let fileNameLength = base.advanced(by: 26).loadUnaligned(as: UInt16.self)
            let extraFieldLength = base.advanced(by: 28).loadUnaligned(as: UInt16.self)
            
            return (fileNameLength, extraFieldLength)
        }
    }
    
    // MARK: - Large Entry Extraction Using Foundation
    
    private static func extractLargeEntryUsingFoundation(_ entry: CentralDirectoryFileHeader, from zipData: Data, to destinationURL: URL, progress: ((Double) -> Void)? = nil) throws {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")
        
        logger.error("🟡 extractLargeEntryUsingFoundation - Starting extraction for \(entry.fileName)")
        logger.error("🟡 extractLargeEntryUsingFoundation - Compressed: \(entry.compressedSize) bytes, Uncompressed: \(entry.uncompressedSize) bytes")
        logger.error("🟡 extractLargeEntryUsingFoundation - Destination: \(destinationURL.path)")
        
        // Read local file header to get the data offset
        let localHeaderOffset = Int(entry.localHeaderOffset)
        guard localHeaderOffset + 30 <= zipData.count else {
            throw ZIPError.extractionFailed("Invalid local header offset")
        }
        
        let localHeader = try parseLocalHeader(at: localHeaderOffset, in: zipData)
        
        // Extract compressed data
        let dataOffset = Int(localHeader.dataOffset)
        let compressedSize = Int(entry.compressedSize)
        
        guard dataOffset + compressedSize <= zipData.count else {
            throw ZIPError.extractionFailed("Invalid data offset or size")
        }
        
        let compressedData = zipData.subdata(in: dataOffset..<(dataOffset + compressedSize))
        
        logger.info("Foundation: Starting decompression of \(compressedSize) bytes using Apple Compression framework")
        
        // Use Apple's compression framework for decompression
        logger.error("🟡 Compression method: \(entry.compression)")
        logger.error("🟡 Compressed data size: \(compressedData.count) bytes")
        
        switch entry.compression {
        case 0: // No compression
            logger.error("🟡 Writing uncompressed data to: \(destinationURL.path)")
            try compressedData.write(to: destinationURL)
            progress?(1.0)
            logger.error("🟡 Foundation: Uncompressed data written directly")
            
        case 8: // Deflate - use Apple's compression framework
            logger.error("🟡 Using DEFLATE decompression")
            // For very large files, we use Apple's single-shot decompression
            // This is more reliable than streaming for files that fit in memory
            logger.error("🟡 Foundation: Using Apple compression framework for deflate decompression")
            
            let sourceBuffer = compressedData.withUnsafeBytes { bytes in
                return bytes.bindMemory(to: UInt8.self)
            }
            
            // Allocate destination buffer for the expected size
            let expectedSize = Int(entry.uncompressedSize)
            let destinationBuffer = UnsafeMutablePointer<UInt8>.allocate(capacity: expectedSize + 1000) // Extra space for safety
            defer { destinationBuffer.deallocate() }
            
            // Use Apple's compression framework
            let decompressedSize = compression_decode_buffer(
                destinationBuffer, expectedSize + 1000,
                sourceBuffer.baseAddress!, compressedSize,
                nil, COMPRESSION_ZLIB
            )
            
            logger.info("Foundation: Decompression completed, got \(decompressedSize) bytes (expected \(expectedSize))")
            
            guard decompressedSize > 0 else {
                throw ZIPError.extractionFailed("Apple compression framework decompression failed")
            }
            
            guard decompressedSize == expectedSize else {
                logger.error("Foundation: Size mismatch! Got \(decompressedSize), expected \(expectedSize)")
                throw ZIPError.extractionFailed("Decompressed size mismatch: got \(decompressedSize), expected \(expectedSize)")
            }
            
            // Write the decompressed data using Foundation
            let decompressedData = Data(bytes: destinationBuffer, count: decompressedSize)
            logger.error("🟡 About to write \(decompressedData.count) bytes")
            logger.error("🟡 Destination URL: \(destinationURL)")
            logger.error("🟡 Destination path: \(destinationURL.path)")
            logger.error("🟡 Absolute string: \(destinationURL.absoluteString)")
            try decompressedData.write(to: destinationURL)
            
            // Verify the file was written
            if FileManager.default.fileExists(atPath: destinationURL.path) {
                let writtenSize = try FileManager.default.attributesOfItem(atPath: destinationURL.path)[.size] as? Int64 ?? 0
                logger.error("🟡 File written successfully, size on disk: \(writtenSize) bytes")
            } else {
                logger.error("🟡 ERROR: File does not exist after write!")
            }
            
            progress?(1.0)
            logger.error("🟡 Foundation: Large file decompression completed successfully using Apple frameworks")
            
        default:
            throw ZIPError.extractionFailed("Unsupported compression method: \(entry.compression)")
        }
    }
    
    private static func parseLocalHeaderFromData(_ data: Data, at offset: UInt64) throws -> LocalFileHeader {
        return try data.withUnsafeBytes { bytes in
            let base = bytes.baseAddress!
            
            let signature = base.loadUnaligned(as: UInt32.self)
            guard signature == 0x04034b50 else {
                throw ZIPError.extractionFailed("Invalid local file header signature")
            }
            
            let fileNameLength = base.advanced(by: 26).loadUnaligned(as: UInt16.self)
            let extraFieldLength = base.advanced(by: 28).loadUnaligned(as: UInt16.self)
            
            // Read standard 32-bit values
            let compressedSize32 = base.advanced(by: 18).loadUnaligned(as: UInt32.self)
            let uncompressedSize32 = base.advanced(by: 22).loadUnaligned(as: UInt32.self)
            
            // For ZIP64, these would be 0xFFFFFFFF, but for now assume standard
            let compressedSize = UInt64(compressedSize32)
            let uncompressedSize = UInt64(uncompressedSize32)
            
            return LocalFileHeader(
                version: base.advanced(by: 4).loadUnaligned(as: UInt16.self),
                flags: base.advanced(by: 6).loadUnaligned(as: UInt16.self),
                compression: base.advanced(by: 8).loadUnaligned(as: UInt16.self),
                modTime: base.advanced(by: 10).loadUnaligned(as: UInt16.self),
                modDate: base.advanced(by: 12).loadUnaligned(as: UInt16.self),
                crc32: base.advanced(by: 14).loadUnaligned(as: UInt32.self),
                compressedSize: compressedSize,
                uncompressedSize: uncompressedSize,
                fileNameLength: fileNameLength,
                extraFieldLength: extraFieldLength,
                fileName: "",
                dataOffset: offset + 30 + UInt64(fileNameLength) + UInt64(extraFieldLength)
            )
        }
    }
    
    private static func extractLargeEntry(_ entry: CentralDirectoryFileHeader, from data: Data, to destinationURL: URL, progress: ((Double) -> Void)? = nil) throws {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "ZIPExtraction")
        
        // Read local file header
        let localHeaderOffset = Int(entry.localHeaderOffset)
        
        guard localHeaderOffset + 30 <= data.count else {
            throw ZIPError.extractionFailed("Invalid local header offset")
        }
        
        // Parse the local header to get the data offset
        let localHeader = try parseLocalHeader(at: localHeaderOffset, in: data)
        
        // Extract compressed data
        let dataOffset = Int(localHeader.dataOffset)
        let compressedSize = Int(entry.compressedSize)
        
        guard dataOffset + compressedSize <= data.count else {
            throw ZIPError.extractionFailed("Invalid data offset or size")
        }
        
        let compressedData = data.subdata(in: dataOffset..<(dataOffset + compressedSize))
        
        // For large files, use streaming decompression
        logger.info("Starting streaming decompression of \(compressedSize) bytes")
        
        switch entry.compression {
        case 0: // No compression
            try compressedData.write(to: destinationURL)
            progress?(1.0)
            
        case 8: // Deflate
            try decompressLargeData(compressedData, to: destinationURL, expectedSize: entry.uncompressedSize, progress: progress)
            
        default:
            throw ZIPError.extractionFailed("Unsupported compression method: \(entry.compression)")
        }
        
        logger.info("Large file extraction completed")
    }
    
    private static func parseLocalHeader(at offset: Int, in data: Data) throws -> LocalFileHeader {
        return try data.withUnsafeBytes { bytes in
            let base = bytes.baseAddress!.advanced(by: offset)
            
            let signature = base.loadUnaligned(as: UInt32.self)
            guard signature == 0x04034b50 else {
                throw ZIPError.extractionFailed("Invalid local file header signature")
            }
            
            let fileNameLength = base.advanced(by: 26).loadUnaligned(as: UInt16.self)
            let extraFieldLength = base.advanced(by: 28).loadUnaligned(as: UInt16.self)
            
            // Read standard 32-bit values
            let compressedSize32 = base.advanced(by: 18).loadUnaligned(as: UInt32.self)
            let uncompressedSize32 = base.advanced(by: 22).loadUnaligned(as: UInt32.self)
            
            // Convert to 64-bit
            var compressedSize = UInt64(compressedSize32)
            var uncompressedSize = UInt64(uncompressedSize32)
            
            // Check for ZIP64
            if compressedSize32 == 0xFFFFFFFF || uncompressedSize32 == 0xFFFFFFFF {
                // Parse ZIP64 extra field if present
                if extraFieldLength >= 4 {
                    let extraStart = 30 + Int(fileNameLength)
                    let extraData = Data(bytes: base.advanced(by: extraStart), count: Int(extraFieldLength))
                    
                    extraData.withUnsafeBytes { extraBytes in
                        guard let extraBase = extraBytes.baseAddress else { return }
                        var pos = 0
                        
                        while pos + 4 <= Int(extraFieldLength) {
                            let headerId = extraBase.advanced(by: pos).loadUnaligned(as: UInt16.self)
                            let headerSize = extraBase.advanced(by: pos + 2).loadUnaligned(as: UInt16.self)
                            
                            if headerId == 0x0001 { // ZIP64 extra field
                                var fieldPos = pos + 4
                                if uncompressedSize32 == 0xFFFFFFFF && fieldPos + 8 <= pos + 4 + Int(headerSize) {
                                    uncompressedSize = extraBase.advanced(by: fieldPos).loadUnaligned(as: UInt64.self)
                                    fieldPos += 8
                                }
                                if compressedSize32 == 0xFFFFFFFF && fieldPos + 8 <= pos + 4 + Int(headerSize) {
                                    compressedSize = extraBase.advanced(by: fieldPos).loadUnaligned(as: UInt64.self)
                                }
                                break
                            }
                            pos += 4 + Int(headerSize)
                        }
                    }
                }
            }
            
            return LocalFileHeader(
                version: base.advanced(by: 4).loadUnaligned(as: UInt16.self),
                flags: base.advanced(by: 6).loadUnaligned(as: UInt16.self),
                compression: base.advanced(by: 8).loadUnaligned(as: UInt16.self),
                modTime: base.advanced(by: 10).loadUnaligned(as: UInt16.self),
                modDate: base.advanced(by: 12).loadUnaligned(as: UInt16.self),
                crc32: base.advanced(by: 14).loadUnaligned(as: UInt32.self),
                compressedSize: compressedSize,
                uncompressedSize: uncompressedSize,
                fileNameLength: fileNameLength,
                extraFieldLength: extraFieldLength,
                fileName: "",
                dataOffset: UInt64(offset + 30 + Int(fileNameLength) + Int(extraFieldLength))
            )
        }
    }
    
    private static func decompressLargeData(_ compressedData: Data, to url: URL, expectedSize: UInt64, progress: ((Double) -> Void)? = nil) throws {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "ZIPExtraction")
        
        logger.info("Decompressing large data: \(compressedData.count) bytes compressed, expecting \(expectedSize) uncompressed")
        
        // For very large files, we'll need to allocate the full buffer
        // This is the limitation we're hitting - iOS can't decompress 3GB in memory
        // Let's try a different approach - decompress in smaller chunks
        
        let sourceBuffer = compressedData.withUnsafeBytes { bytes in
            return bytes.bindMemory(to: UInt8.self)
        }
        
        // Allocate the full expected size
        let bufferSize = Int(expectedSize + 1000) // Add a small buffer
        
        logger.info("Allocating buffer of size: \(bufferSize)")
        
        let destinationBuffer = UnsafeMutablePointer<UInt8>.allocate(capacity: bufferSize)
        
        defer { destinationBuffer.deallocate() }
        
        let decompressedSize = compression_decode_buffer(
            destinationBuffer, bufferSize,
            sourceBuffer.baseAddress!, compressedData.count,
            nil, COMPRESSION_ZLIB
        )
        
        logger.info("Decompressed \(decompressedSize) bytes")
        
        guard decompressedSize > 0 else {
            throw ZIPError.extractionFailed("Decompression failed")
        }
        
        // Write the decompressed data to file
        let decompressedData = Data(bytes: destinationBuffer, count: decompressedSize)
        try decompressedData.write(to: url)
        
        progress?(1.0)
        logger.info("Large data decompression completed")
    }
    
    // MARK: - Find End of Central Directory
    
    private static func findEndOfCentralDirectory(in data: Data) -> EndOfCentralDirectory? {
        let eocdSignature: UInt32 = 0x06054b50
        let minEOCDSize = 22
        
        guard data.count >= minEOCDSize else { return nil }
        
        // Search backwards for EOCD signature
        for i in stride(from: data.count - minEOCDSize, through: 0, by: -1) {
            let signature = data.withUnsafeBytes { bytes in
                bytes.loadUnaligned(fromByteOffset: i, as: UInt32.self)
            }
            
            if signature == eocdSignature {
                // Parse EOCD
                return data.withUnsafeBytes { bytes in
                    let base = bytes.baseAddress!.advanced(by: i)
                    
                    return EndOfCentralDirectory(
                        diskNumber: base.advanced(by: 4).loadUnaligned(as: UInt16.self),
                        diskWithCentralDir: base.advanced(by: 6).loadUnaligned(as: UInt16.self),
                        numEntriesThisDisk: base.advanced(by: 8).loadUnaligned(as: UInt16.self),
                        numEntriesTotal: base.advanced(by: 10).loadUnaligned(as: UInt16.self),
                        centralDirSize: base.advanced(by: 12).loadUnaligned(as: UInt32.self),
                        centralDirOffset: base.advanced(by: 16).loadUnaligned(as: UInt32.self),
                        commentLength: base.advanced(by: 20).loadUnaligned(as: UInt16.self)
                    )
                }
            }
        }
        
        return nil
    }
    
    // MARK: - Parse Central Directory
    
    private static func parseCentralDirectory(in data: Data, eocd: EndOfCentralDirectory) throws -> [CentralDirectoryFileHeader] {
        var entries: [CentralDirectoryFileHeader] = []
        var offset = Int(eocd.centralDirOffset)
        
        for _ in 0..<eocd.numEntriesTotal {
            guard offset + 46 <= data.count else {
                throw ZIPError.invalidCentralDirectory
            }
            
            let entry = try data.withUnsafeBytes { (bytes: UnsafeRawBufferPointer) in
                let base = bytes.baseAddress!.advanced(by: offset)
                
                let signature = base.loadUnaligned(as: UInt32.self)
                guard signature == 0x02014b50 else {
                    throw ZIPError.invalidCentralDirectory
                }
                
                let fileNameLength = base.advanced(by: 28).loadUnaligned(as: UInt16.self)
                let extraFieldLength = base.advanced(by: 30).loadUnaligned(as: UInt16.self)
                let commentLength = base.advanced(by: 32).loadUnaligned(as: UInt16.self)
                
                let fileNameData = Data(bytes: base.advanced(by: 46), count: Int(fileNameLength))
                let fileName = String(data: fileNameData, encoding: .utf8) ?? ""
                
                // Read standard 32-bit values
                let compressedSize32 = base.advanced(by: 20).loadUnaligned(as: UInt32.self)
                let uncompressedSize32 = base.advanced(by: 24).loadUnaligned(as: UInt32.self)
                let localHeaderOffset32 = base.advanced(by: 42).loadUnaligned(as: UInt32.self)
                
                // Convert to 64-bit, checking for ZIP64 marker
                var compressedSize = UInt64(compressedSize32)
                var uncompressedSize = UInt64(uncompressedSize32)
                var localHeaderOffset = UInt64(localHeaderOffset32)
                
                // Check for ZIP64 (0xFFFFFFFF indicates values in extra field)
                if compressedSize32 == 0xFFFFFFFF || uncompressedSize32 == 0xFFFFFFFF || localHeaderOffset32 == 0xFFFFFFFF {
                    // Parse ZIP64 extra field if present
                    if extraFieldLength >= 4 {
                        let extraStart = 46 + Int(fileNameLength)
                        let extraData = Data(bytes: base.advanced(by: extraStart), count: Int(extraFieldLength))
                        
                        extraData.withUnsafeBytes { extraBytes in
                            guard let extraBase = extraBytes.baseAddress else { return }
                            var pos = 0
                            
                            while pos + 4 <= Int(extraFieldLength) {
                                let headerId = extraBase.advanced(by: pos).loadUnaligned(as: UInt16.self)
                                let headerSize = extraBase.advanced(by: pos + 2).loadUnaligned(as: UInt16.self)
                                
                                if headerId == 0x0001 { // ZIP64 extra field
                                    var fieldPos = pos + 4
                                    if uncompressedSize32 == 0xFFFFFFFF && fieldPos + 8 <= pos + 4 + Int(headerSize) {
                                        uncompressedSize = extraBase.advanced(by: fieldPos).loadUnaligned(as: UInt64.self)
                                        fieldPos += 8
                                    }
                                    if compressedSize32 == 0xFFFFFFFF && fieldPos + 8 <= pos + 4 + Int(headerSize) {
                                        compressedSize = extraBase.advanced(by: fieldPos).loadUnaligned(as: UInt64.self)
                                        fieldPos += 8
                                    }
                                    if localHeaderOffset32 == 0xFFFFFFFF && fieldPos + 8 <= pos + 4 + Int(headerSize) {
                                        localHeaderOffset = extraBase.advanced(by: fieldPos).loadUnaligned(as: UInt64.self)
                                    }
                                    break
                                }
                                pos += 4 + Int(headerSize)
                            }
                        }
                    }
                }
                
                return CentralDirectoryFileHeader(
                    versionMadeBy: base.advanced(by: 4).loadUnaligned(as: UInt16.self),
                    versionNeeded: base.advanced(by: 6).loadUnaligned(as: UInt16.self),
                    flags: base.advanced(by: 8).loadUnaligned(as: UInt16.self),
                    compression: base.advanced(by: 10).loadUnaligned(as: UInt16.self),
                    modTime: base.advanced(by: 12).loadUnaligned(as: UInt16.self),
                    modDate: base.advanced(by: 14).loadUnaligned(as: UInt16.self),
                    crc32: base.advanced(by: 16).loadUnaligned(as: UInt32.self),
                    compressedSize: compressedSize,
                    uncompressedSize: uncompressedSize,
                    fileNameLength: fileNameLength,
                    extraFieldLength: extraFieldLength,
                    commentLength: commentLength,
                    diskNumberStart: base.advanced(by: 34).loadUnaligned(as: UInt16.self),
                    internalAttributes: base.advanced(by: 36).loadUnaligned(as: UInt16.self),
                    externalAttributes: base.advanced(by: 38).loadUnaligned(as: UInt32.self),
                    localHeaderOffset: localHeaderOffset,
                    fileName: fileName
                )
            }
            
            entries.append(entry)
            offset += 46 + Int(entry.fileNameLength) + Int(entry.extraFieldLength) + Int(entry.commentLength)
        }
        
        return entries
    }
    
    // MARK: - Extract Entry
    
    private static func extractEntry(_ entry: CentralDirectoryFileHeader, from data: Data, to destinationURL: URL, progress: ((Double) -> Void)? = nil) throws {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "ZIPExtraction")
        // Read local file header
        let localHeaderOffset = Int(entry.localHeaderOffset)
        
        guard localHeaderOffset + 30 <= data.count else {
            throw ZIPError.extractionFailed("Invalid local header offset")
        }
        
        let localHeader = try data.withUnsafeBytes { bytes in
            let base = bytes.baseAddress!.advanced(by: localHeaderOffset)
            
            let signature = base.loadUnaligned(as: UInt32.self)
            guard signature == 0x04034b50 else {
                throw ZIPError.extractionFailed("Invalid local file header signature")
            }
            
            let fileNameLength = base.advanced(by: 26).loadUnaligned(as: UInt16.self)
            let extraFieldLength = base.advanced(by: 28).loadUnaligned(as: UInt16.self)
            
            // Read standard 32-bit values
            let compressedSize32 = base.advanced(by: 18).loadUnaligned(as: UInt32.self)
            let uncompressedSize32 = base.advanced(by: 22).loadUnaligned(as: UInt32.self)
            
            // Convert to 64-bit, checking for ZIP64 marker
            var compressedSize = UInt64(compressedSize32)
            var uncompressedSize = UInt64(uncompressedSize32)
            
            // Check for ZIP64 (0xFFFFFFFF indicates values in extra field)
            if compressedSize32 == 0xFFFFFFFF || uncompressedSize32 == 0xFFFFFFFF {
                // Parse ZIP64 extra field if present
                if extraFieldLength >= 4 {
                    let extraStart = 30 + Int(fileNameLength)
                    let extraData = Data(bytes: base.advanced(by: extraStart), count: Int(extraFieldLength))
                    
                    extraData.withUnsafeBytes { extraBytes in
                        guard let extraBase = extraBytes.baseAddress else { return }
                        var pos = 0
                        
                        while pos + 4 <= Int(extraFieldLength) {
                            let headerId = extraBase.advanced(by: pos).loadUnaligned(as: UInt16.self)
                            let headerSize = extraBase.advanced(by: pos + 2).loadUnaligned(as: UInt16.self)
                            
                            if headerId == 0x0001 { // ZIP64 extra field
                                var fieldPos = pos + 4
                                if uncompressedSize32 == 0xFFFFFFFF && fieldPos + 8 <= pos + 4 + Int(headerSize) {
                                    uncompressedSize = extraBase.advanced(by: fieldPos).loadUnaligned(as: UInt64.self)
                                    fieldPos += 8
                                }
                                if compressedSize32 == 0xFFFFFFFF && fieldPos + 8 <= pos + 4 + Int(headerSize) {
                                    compressedSize = extraBase.advanced(by: fieldPos).loadUnaligned(as: UInt64.self)
                                    fieldPos += 8
                                }
                                break
                            }
                            pos += 4 + Int(headerSize)
                        }
                    }
                }
            }
            
            return LocalFileHeader(
                version: base.advanced(by: 4).loadUnaligned(as: UInt16.self),
                flags: base.advanced(by: 6).loadUnaligned(as: UInt16.self),
                compression: base.advanced(by: 8).loadUnaligned(as: UInt16.self),
                modTime: base.advanced(by: 10).loadUnaligned(as: UInt16.self),
                modDate: base.advanced(by: 12).loadUnaligned(as: UInt16.self),
                crc32: base.advanced(by: 14).loadUnaligned(as: UInt32.self),
                compressedSize: compressedSize,
                uncompressedSize: uncompressedSize,
                fileNameLength: fileNameLength,
                extraFieldLength: extraFieldLength,
                fileName: "",
                dataOffset: UInt64(localHeaderOffset + 30 + Int(fileNameLength) + Int(extraFieldLength))
            )
        }
        
        // Extract compressed data
        let dataOffset = Int(localHeader.dataOffset)
        let compressedSize = Int(entry.compressedSize)
        
        logger.info("Extracting entry: compressed=\(compressedSize), uncompressed=\(entry.uncompressedSize)")
        
        guard dataOffset + compressedSize <= data.count else {
            throw ZIPError.extractionFailed("Invalid data offset or size")
        }
        
        let compressedData = data.subdata(in: dataOffset..<(dataOffset + compressedSize))
        
        // Decompress data based on compression method
        let decompressedData: Data
        switch entry.compression {
        case 0: // No compression
            decompressedData = compressedData
            
        case 8: // Deflate
            guard let decompressed = decompress(data: compressedData, algorithm: .zlib, expectedSize: entry.uncompressedSize) else {
                throw ZIPError.extractionFailed("Decompression failed")
            }
            decompressedData = decompressed
            
        default:
            throw ZIPError.extractionFailed("Unsupported compression method: \(entry.compression)")
        }
        
        // Verify size
        logger.info("Decompressed size: \(decompressedData.count), expected: \(entry.uncompressedSize)")
        guard decompressedData.count == entry.uncompressedSize else {
            logger.error("Size mismatch! Got \(decompressedData.count) bytes, expected \(entry.uncompressedSize)")
            throw ZIPError.extractionFailed("Decompressed size mismatch: got \(decompressedData.count), expected \(entry.uncompressedSize)")
        }
        
        // Write to destination with progress updates
        try writeDataWithProgress(decompressedData, to: destinationURL, progress: progress)
    }
    
    // MARK: - Decompression
    
    private static func decompress(data: Data, algorithm: Algorithm, expectedSize: UInt64 = 0) -> Data? {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "ZIPExtraction")
        
        let sourceBuffer = data.withUnsafeBytes { bytes in
            return bytes.bindMemory(to: UInt8.self)
        }
        
        // Use the expected size if provided, otherwise use a heuristic
        let bufferSize: Int
        if expectedSize > 0 {
            // Add 10% extra just in case
            bufferSize = Int(min(expectedSize + (expectedSize / 10), UInt64(Int.max)))
        } else {
            // Fallback to compressed size * 10 for unknown sizes
            bufferSize = min(data.count * 10, Int.max / 2)
        }
        
        logger.info("Decompressing \(data.count) bytes, buffer size: \(bufferSize), expected: \(expectedSize)")
        
        let destinationBuffer = UnsafeMutablePointer<UInt8>.allocate(capacity: bufferSize)
        defer { destinationBuffer.deallocate() }
        
        let decompressedSize = compression_decode_buffer(
            destinationBuffer, bufferSize,
            sourceBuffer.baseAddress!, data.count,
            nil, algorithm.rawValue
        )
        
        logger.info("Decompression result: \(decompressedSize) bytes")
        
        guard decompressedSize > 0 else { 
            logger.error("Decompression failed - returned 0 bytes")
            return nil 
        }
        
        return Data(bytes: destinationBuffer, count: decompressedSize)
    }
    
    // MARK: - Write with Progress
    
    private static func writeDataWithProgress(_ data: Data, to url: URL, progress: ((Double) -> Void)?) throws {
        // Create parent directory if needed
        let parentDirectory = url.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: parentDirectory, withIntermediateDirectories: true)
        
        // Write in chunks for progress reporting
        FileManager.default.createFile(atPath: url.path, contents: nil)
        guard let fileHandle = try? FileHandle(forWritingTo: url) else {
            throw ZIPError.extractionFailed("Cannot create output file")
        }
        
        defer { fileHandle.closeFile() }
        
        let chunkSize = 1024 * 1024 // 1MB chunks
        var offset = 0
        let totalSize = data.count
        
        while offset < totalSize {
            let endOffset = min(offset + chunkSize, totalSize)
            let chunk = data.subdata(in: offset..<endOffset)
            
            fileHandle.write(chunk)
            
            offset = endOffset
            let progressValue = Double(offset) / Double(totalSize)
            progress?(progressValue)
        }
    }
    
    // MARK: - Compression Algorithm
    
    enum Algorithm {
        case lz4
        case zlib
        case lzma
        case lzfse
        
        var rawValue: compression_algorithm {
            switch self {
            case .lz4: return COMPRESSION_LZ4
            case .zlib: return COMPRESSION_ZLIB
            case .lzma: return COMPRESSION_LZMA
            case .lzfse: return COMPRESSION_LZFSE
            }
        }
    }
}

// MARK: - Unsafe Pointer Extensions

extension UnsafeRawPointer {
    func loadUnaligned<T>(as type: T.Type) -> T where T: FixedWidthInteger {
        return self.loadUnaligned(fromByteOffset: 0, as: type)
    }
    
    func loadUnaligned<T>(fromByteOffset offset: Int = 0, as type: T.Type) -> T where T: FixedWidthInteger {
        return self.advanced(by: offset).assumingMemoryBound(to: type).pointee
    }
}
