import Foundation
import Combine
import os.log

/// Manages the full audio asset pack download and extraction
/// Matches Android's AudioDownloadManager behavior
@MainActor
class AudioAssetDownloadManager: ObservableObject {
    static let shared = AudioAssetDownloadManager()

    // MARK: - Published State

    @Published var status: AssetDownloadStatus = .unknown
    @Published var downloadProgress: Double = 0
    @Published var extractionProgress: Double = 0
    @Published var errorMessage: String?

    // MARK: - Constants (matching Android AudioDownloadManager)

    private let assetInfo = AssetPackInfo.audioFull
    private let audioZipName = "homer_iliad_chamberlain_audio.zip"

    /// Audio package identifiers (matching Android)
    static let fullAudioPackageId: Int = -2      // Distinct from bundled (-1)
    static let fullAudioPackageName = "full_iliad_audio"
    static let fullAudioDisplayName = "Homer - Iliad (Chamberlain) [Full]"
    static let packageDirName = "full_iliad_audio"

    // MARK: - Private Properties

    private let logger = Logger(subsystem: "com.classicsviewer.app", category: "AudioAssetDownloadManager")
    private let audioDAO = AudioPackageDAO()

    private init() {}

    // MARK: - Status Check

    /// Check current status on init or when needed
    func checkStatus() async {
        // Check if already fully installed
        if isFullAudioInstalled() {
            // Verify the files still exist
            let packageDir = getPackageDirectory()
            if FileManager.default.fileExists(atPath: packageDir.path) {
                status = .installed
                return
            } else {
                // Files were deleted, reset preference
                UserDefaults.standard.fullAudioInstalled = false
            }
        }

        // Check if ODR download is available
        let isDownloaded = await ODRManager.shared.isDownloaded(tag: .audioFull)
        if isDownloaded {
            status = .downloaded
        } else {
            status = .notDownloaded
        }
    }

    // MARK: - Download

    /// Start download from On-Demand Resources
    func startDownload() async {
        guard StorageManager.hasEnoughSpace(for: assetInfo) else {
            errorMessage = "Not enough storage space. Required: \(StorageManager.formatBytes(assetInfo.requiredFreeSpace))"
            status = .failed
            return
        }

        status = .downloading
        downloadProgress = 0
        errorMessage = nil

        do {
            try await ODRManager.shared.download(tag: .audioFull) { [weak self] progress in
                Task { @MainActor in
                    self?.downloadProgress = progress
                }
            }
            status = .downloaded
            logger.info("Audio download completed")
        } catch {
            errorMessage = error.localizedDescription
            status = .failed
            logger.error("Audio download failed: \(error.localizedDescription)")
        }
    }

    // MARK: - Extraction

    /// Extract downloaded ZIP to audio directory and register in database
    /// Creates package entry with ID -2 and directory "full_iliad_audio"
    func extractAudio() async throws {
        status = .extracting
        extractionProgress = 0
        errorMessage = nil

        // Get ZIP path from ODR
        guard let zipURL = await ODRManager.shared.assetPath(tag: .audioFull, filename: audioZipName) else {
            throw AudioAssetError.zipNotFound
        }

        logger.info("Extracting audio from: \(zipURL.path)")

        // Create package directory
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let audioPath = documentsPath.appendingPathComponent("audio")
        let packagePath = audioPath.appendingPathComponent(Self.packageDirName)

        do {
            // Create directories
            try FileManager.default.createDirectory(at: audioPath, withIntermediateDirectories: true)

            // Remove existing package directory if it exists
            if FileManager.default.fileExists(atPath: packagePath.path) {
                try FileManager.default.removeItem(at: packagePath)
            }

            try FileManager.default.createDirectory(at: packagePath, withIntermediateDirectories: true)

            // Extract ZIP with progress
            try await extractZipWithProgress(from: zipURL, to: packagePath)

            // Scan extracted files and register in database
            let audioFiles = try scanExtractedAudioFiles(in: packagePath, documentsPath: documentsPath)

            // Create package metadata
            let metadata: [String: Any] = [
                "package_name": Self.fullAudioPackageName,
                "display_name": Self.fullAudioDisplayName,
                "description": "Full audio narration for Homer's Iliad by David Chamberlain",
                "version": "1.0",
                "created_date": Date()
            ]

            // Import to database
            let packageId = try await audioDAO.importAudioPackage(metadata: metadata, audioFiles: audioFiles)

            // Enable it as the active package
            try await audioDAO.setPackageEnabled(packageId: packageId, enabled: true)

            // Set preference flag
            UserDefaults.standard.fullAudioInstalled = true

            status = .installed
            logger.info("Full audio package imported successfully with \(audioFiles.count) files")

        } catch {
            errorMessage = error.localizedDescription
            status = .failed
            logger.error("Audio extraction failed: \(error.localizedDescription)")
            throw error
        }
    }

    // MARK: - Cancel & Remove

    /// Cancel ongoing download
    func cancelDownload() {
        Task {
            await ODRManager.shared.cancelDownload(tag: .audioFull)
        }
        status = .notDownloaded
        downloadProgress = 0
    }

    /// Remove downloaded/extracted audio (deletes package)
    func removeAudio() async {
        do {
            // Delete from database
            let packages = try await audioDAO.getPackages()
            if let fullPackage = packages.first(where: { $0.packageName == Self.fullAudioPackageName }) {
                try await audioDAO.deletePackage(packageId: fullPackage.id)
            }

            // Delete files
            let packageDir = getPackageDirectory()
            if FileManager.default.fileExists(atPath: packageDir.path) {
                try FileManager.default.removeItem(at: packageDir)
            }

            // Clear preference
            UserDefaults.standard.fullAudioInstalled = false

            // Release ODR resources
            await ODRManager.shared.releaseResources(tag: .audioFull)

            status = .notDownloaded
            logger.info("Full audio removed successfully")
        } catch {
            errorMessage = error.localizedDescription
            logger.error("Failed to remove audio: \(error.localizedDescription)")
        }
    }

    // MARK: - Helpers

    /// Check if full audio is installed
    func isFullAudioInstalled() -> Bool {
        return UserDefaults.standard.fullAudioInstalled
    }

    /// Get the package directory path
    func getPackageDirectory() -> URL {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        return documentsPath
            .appendingPathComponent("audio")
            .appendingPathComponent(Self.packageDirName)
    }

    // MARK: - Private Methods

    private func extractZipWithProgress(from zipURL: URL, to destinationURL: URL) async throws {
        // Use ZIPHandler for extraction with progress updates
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                do {
                    try ZIPHandler.extractAll(from: zipURL, to: destinationURL)

                    Task { @MainActor in
                        self?.extractionProgress = 0.9
                    }

                    continuation.resume()
                } catch {
                    continuation.resume(throwing: error)
                }
            }
        }
    }

    /// Scan extracted audio files and build metadata for database registration
    /// Handles full Iliad structure: Homer/Iliad/book_N/line_M.mp4
    private func scanExtractedAudioFiles(in packagePath: URL, documentsPath: URL) throws -> [[String: Any]] {
        var audioFiles: [[String: Any]] = []
        let fileManager = FileManager.default

        // The ZIP structure is: Homer/Iliad/book_N/line_M.mp4
        let iliadPath = packagePath.appendingPathComponent("Homer/Iliad")

        guard fileManager.fileExists(atPath: iliadPath.path) else {
            logger.warning("Iliad path not found: \(iliadPath.path)")
            return audioFiles
        }

        // Iterate through all book directories
        let bookDirs = try fileManager.contentsOfDirectory(at: iliadPath, includingPropertiesForKeys: nil)

        for bookDir in bookDirs {
            guard bookDir.hasDirectoryPath,
                  bookDir.lastPathComponent.hasPrefix("book_") else {
                continue
            }

            // Extract book number from directory name (e.g., "book_1" -> 1)
            let bookStr = bookDir.lastPathComponent.replacingOccurrences(of: "book_", with: "")
            guard let bookNumber = Int(bookStr) else { continue }

            // Scan audio files in this book directory
            let files = try fileManager.contentsOfDirectory(at: bookDir, includingPropertiesForKeys: [.fileSizeKey])

            for file in files {
                let ext = file.pathExtension.lowercased()
                guard ext == "mp4" || ext == "mp3" else { continue }

                // Extract line number from filename (e.g., "line_42.mp4" -> 42)
                let filename = file.deletingPathExtension().lastPathComponent
                guard filename.hasPrefix("line_"),
                      let lineNumber = Int(filename.replacingOccurrences(of: "line_", with: "")) else {
                    continue
                }

                // Get file size
                let attributes = try fileManager.attributesOfItem(atPath: file.path)
                let fileSize = attributes[.size] as? Int ?? 0

                // Create relative path from Documents directory
                let relativePath = file.path.replacingOccurrences(of: documentsPath.path + "/", with: "")

                audioFiles.append([
                    "work_id": "homer_iliad",
                    "book_id": String(bookNumber),
                    "line_start": lineNumber,
                    "line_end": lineNumber,
                    "file_path": relativePath,
                    "file_size": fileSize,
                    "mime_type": ext == "mp4" ? "audio/mp4" : "audio/mp3"
                ])
            }
        }

        extractionProgress = 1.0
        logger.info("Scanned \(audioFiles.count) audio files from full package")
        return audioFiles
    }
}

// MARK: - Errors

enum AudioAssetError: LocalizedError {
    case zipNotFound
    case extractionFailed
    case insufficientStorage

    var errorDescription: String? {
        switch self {
        case .zipNotFound:
            return "Audio ZIP file not found. Please try downloading again."
        case .extractionFailed:
            return "Failed to extract audio files."
        case .insufficientStorage:
            return "Not enough storage space available."
        }
    }
}
