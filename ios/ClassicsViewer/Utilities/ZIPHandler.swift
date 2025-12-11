import Foundation
import os.log
import ZIPFoundation

typealias Logger = os.Logger

/// ZIPHandler - Uses ZIPFoundation library for reliable ZIP extraction
/// Supports ZIP64 format for large files (>4GB)
class ZIPHandler {

    enum ZIPError: LocalizedError {
        case invalidZIPFile
        case noEntryFound
        case extractionFailed(String)
        case cannotOpenFile
        case cannotCreateFile

        var errorDescription: String? {
            switch self {
            case .invalidZIPFile:
                return "Invalid or corrupted ZIP file"
            case .noEntryFound:
                return "No matching entry found in ZIP archive"
            case .extractionFailed(let reason):
                return "Extraction failed: \(reason)"
            case .cannotOpenFile:
                return "Cannot open ZIP file"
            case .cannotCreateFile:
                return "Cannot create output file"
            }
        }
    }

    // MARK: - Extract Database from ZIP

    /// Extract a .db file from a ZIP archive to the destination URL
    /// Uses ZIPFoundation for reliable extraction with ZIP64 support
    static func extractDatabase(from zipURL: URL, to destinationURL: URL, progress: ((Double) -> Void)? = nil) throws {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "ZIPHandler")

        logger.info("ZIPHandler.extractDatabase - Source: \(zipURL.path)")
        logger.info("ZIPHandler.extractDatabase - Destination: \(destinationURL.path)")

        // Check if source exists
        guard FileManager.default.fileExists(atPath: zipURL.path) else {
            logger.error("ZIPHandler.extractDatabase - Source file does not exist")
            throw ZIPError.extractionFailed("Source file does not exist")
        }

        // Get file size for logging
        let attributes = try? FileManager.default.attributesOfItem(atPath: zipURL.path)
        let fileSize = attributes?[.size] as? Int64 ?? 0
        logger.info("ZIPHandler.extractDatabase - ZIP file size: \(fileSize) bytes (\(fileSize / 1_000_000) MB)")

        // Open the archive using ZIPFoundation
        let archive: Archive
        do {
            archive = try Archive(url: zipURL, accessMode: .read)
        } catch {
            logger.error("ZIPHandler.extractDatabase - Failed to open archive: \(error.localizedDescription)")
            throw ZIPError.cannotOpenFile
        }

        // Find the .db file in the archive
        var dbEntry: Entry? = nil
        for entry in archive {
            if entry.path.hasSuffix(".db") {
                dbEntry = entry
                logger.info("ZIPHandler.extractDatabase - Found database: \(entry.path)")
                logger.info("ZIPHandler.extractDatabase - Compressed size: \(entry.compressedSize)")
                logger.info("ZIPHandler.extractDatabase - Uncompressed size: \(entry.uncompressedSize)")
                break
            }
        }

        guard let entry = dbEntry else {
            logger.error("ZIPHandler.extractDatabase - No .db file found in archive")
            throw ZIPError.noEntryFound
        }

        // Remove existing file if present
        if FileManager.default.fileExists(atPath: destinationURL.path) {
            try FileManager.default.removeItem(at: destinationURL)
        }

        // Create parent directory if needed
        let parentDir = destinationURL.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: parentDir, withIntermediateDirectories: true)

        // Extract using ZIPFoundation with streaming I/O
        // ZIPFoundation reads/writes in chunks - keeps memory usage constant regardless of file size
        logger.info("ZIPHandler.extractDatabase - Starting streaming extraction...")
        logger.info("ZIPHandler.extractDatabase - Using chunked I/O for memory efficiency")

        do {
            // bufferSize controls how much data is processed at a time
            // 64KB is a good balance between performance and memory usage
            let bufferSize: Int = 64 * 1024

            // ZIPFoundation streams data in chunks - memory efficient
            _ = try archive.extract(entry, to: destinationURL, bufferSize: bufferSize, skipCRC32: false)

            // Progress is tracked separately since ZIPFoundation uses Progress objects
            progress?(1.0)
        } catch {
            logger.error("ZIPHandler.extractDatabase - Extraction failed: \(error.localizedDescription)")
            throw ZIPError.extractionFailed(error.localizedDescription)
        }

        // Verify the extracted file
        guard FileManager.default.fileExists(atPath: destinationURL.path) else {
            logger.error("ZIPHandler.extractDatabase - Extracted file not found")
            throw ZIPError.extractionFailed("Extracted file not found")
        }

        let extractedAttributes = try FileManager.default.attributesOfItem(atPath: destinationURL.path)
        let extractedSize2 = extractedAttributes[.size] as? Int64 ?? 0

        logger.info("ZIPHandler.extractDatabase - Successfully extracted \(extractedSize2) bytes")
        logger.info("ZIPHandler.extractDatabase - Expected \(entry.uncompressedSize) bytes")

        // Verify size matches
        if extractedSize2 != Int64(entry.uncompressedSize) {
            logger.error("ZIPHandler.extractDatabase - Size mismatch: got \(extractedSize2), expected \(entry.uncompressedSize)")
            throw ZIPError.extractionFailed("Size mismatch: got \(extractedSize2), expected \(entry.uncompressedSize)")
        }

        progress?(1.0)
        logger.info("ZIPHandler.extractDatabase - Extraction complete")
    }

    /// Extract all files from a ZIP archive to a directory
    static func extractAll(from zipURL: URL, to destinationDirectory: URL, progress: ((Double) -> Void)? = nil) throws {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "ZIPHandler")

        logger.info("ZIPHandler.extractAll - Source: \(zipURL.path)")
        logger.info("ZIPHandler.extractAll - Destination: \(destinationDirectory.path)")

        // Check if source exists
        guard FileManager.default.fileExists(atPath: zipURL.path) else {
            throw ZIPError.extractionFailed("Source file does not exist")
        }

        // Create destination directory if needed
        try FileManager.default.createDirectory(at: destinationDirectory, withIntermediateDirectories: true)

        // Use ZIPFoundation's built-in extraction
        try FileManager.default.unzipItem(at: zipURL, to: destinationDirectory)

        progress?(1.0)
        logger.info("ZIPHandler.extractAll - Extraction complete")
    }
}
