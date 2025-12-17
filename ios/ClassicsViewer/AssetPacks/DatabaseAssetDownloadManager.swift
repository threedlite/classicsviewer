import Foundation
import Combine
import os.log

/// Manages the full database asset pack download and switching
/// Matches Android's FullDatabaseDownloadManager behavior
@MainActor
class DatabaseAssetDownloadManager: ObservableObject {
    static let shared = DatabaseAssetDownloadManager()

    // MARK: - Published State

    @Published var status: AssetDownloadStatus = .unknown
    @Published var downloadProgress: Double = 0
    @Published var extractionProgress: Double = 0
    @Published var errorMessage: String?
    @Published var currentDatabaseType: DatabaseType = .sample

    // MARK: - Constants

    private let assetInfo = AssetPackInfo.databaseFull
    private let databaseZipName = "perseus_texts_full.db.zip"
    private let fullDatabaseFileName = "perseus_texts_full.db"
    private let sampleDatabaseFileName = "perseus_texts.db"

    // MARK: - Private Properties

    private let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseAssetDownloadManager")

    private init() {}

    // MARK: - Status Check

    /// Check current status
    func checkStatus() async {
        // Determine current database type
        currentDatabaseType = determineCurrentDatabaseType()

        // Check if full database is already extracted and active
        if currentDatabaseType == .full {
            status = .active
            return
        }

        // Check if full database file exists (extracted but not active)
        if fullDatabaseExists() {
            status = .installed
            return
        }

        // Check if ODR download is available
        let isDownloaded = await ODRManager.shared.isDownloaded(tag: .databaseFull)
        if isDownloaded {
            status = .downloaded
        } else {
            status = .notDownloaded
        }
    }

    /// Determine which database is currently active
    func determineCurrentDatabaseType() -> DatabaseType {
        // Priority 1: External database (user-imported)
        if let externalName = UserDefaults.standard.externalDatabaseName,
           !externalName.isEmpty,
           externalDatabaseExists() {
            return .external
        }

        // Priority 2: Full database (downloaded via ODR)
        if UserDefaults.standard.useFullDatabase && fullDatabaseExists() {
            return .full
        }

        // Priority 3: Bundled sample database
        return .sample
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
            try await ODRManager.shared.download(tag: .databaseFull) { [weak self] progress in
                Task { @MainActor in
                    self?.downloadProgress = progress
                }
            }
            status = .downloaded
            logger.info("Database download completed")
        } catch {
            errorMessage = error.localizedDescription
            status = .failed
            logger.error("Database download failed: \(error.localizedDescription)")
        }
    }

    // MARK: - Extraction

    /// Extract downloaded ZIP to Documents directory
    func extractDatabase() async throws {
        status = .extracting
        extractionProgress = 0
        errorMessage = nil

        // Get ZIP path from ODR
        guard let zipURL = await ODRManager.shared.assetPath(tag: .databaseFull, filename: databaseZipName) else {
            throw DatabaseAssetError.zipNotFound
        }

        logger.info("Extracting database from: \(zipURL.path)")

        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let targetPath = documentsPath.appendingPathComponent(fullDatabaseFileName)

        do {
            // Remove existing full database if it exists
            if FileManager.default.fileExists(atPath: targetPath.path) {
                try FileManager.default.removeItem(at: targetPath)
            }

            // Extract ZIP
            try await extractZipWithProgress(from: zipURL, to: documentsPath)

            // Verify extraction succeeded
            guard FileManager.default.fileExists(atPath: targetPath.path) else {
                throw DatabaseAssetError.extractionFailed
            }

            // Mark as installed
            UserDefaults.standard.fullDatabaseInstalled = true

            status = .installed
            logger.info("Full database extracted successfully")

        } catch {
            errorMessage = error.localizedDescription
            status = .failed
            logger.error("Database extraction failed: \(error.localizedDescription)")
            throw error
        }
    }

    // MARK: - Activation

    /// Switch to full database (requires app restart)
    func activateFullDatabase() async throws {
        guard fullDatabaseExists() else {
            throw DatabaseAssetError.databaseNotFound
        }

        // Clear any external database setting
        UserDefaults.standard.externalDatabaseName = nil

        // Set preference to use full database
        UserDefaults.standard.useFullDatabase = true

        // Update status
        currentDatabaseType = .full
        status = .active

        logger.info("Full database activated - restart required")
    }

    /// Switch back to sample database
    func revertToSampleDatabase() async throws {
        // Clear full database preference
        UserDefaults.standard.useFullDatabase = false

        // Update status
        currentDatabaseType = .sample
        status = .installed  // Full DB still installed, just not active

        logger.info("Reverted to sample database - restart required")
    }

    // MARK: - Cancel & Remove

    /// Cancel ongoing download
    func cancelDownload() {
        Task {
            await ODRManager.shared.cancelDownload(tag: .databaseFull)
        }
        status = .notDownloaded
        downloadProgress = 0
    }

    /// Remove full database files
    func removeFullDatabase() async {
        do {
            let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
            let fullDbPath = documentsPath.appendingPathComponent(fullDatabaseFileName)

            // Delete the database file
            if FileManager.default.fileExists(atPath: fullDbPath.path) {
                try FileManager.default.removeItem(at: fullDbPath)
            }

            // Clear preferences
            UserDefaults.standard.fullDatabaseInstalled = false
            UserDefaults.standard.useFullDatabase = false

            // Release ODR resources
            await ODRManager.shared.releaseResources(tag: .databaseFull)

            // Update status
            currentDatabaseType = .sample
            status = .notDownloaded

            logger.info("Full database removed successfully")
        } catch {
            errorMessage = error.localizedDescription
            logger.error("Failed to remove database: \(error.localizedDescription)")
        }
    }

    // MARK: - Helpers

    /// Check if full database file exists
    func fullDatabaseExists() -> Bool {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let fullDbPath = documentsPath.appendingPathComponent(fullDatabaseFileName)
        return FileManager.default.fileExists(atPath: fullDbPath.path)
    }

    /// Check if external database file exists
    func externalDatabaseExists() -> Bool {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let externalDbPath = documentsPath.appendingPathComponent("external_perseus_texts.db")
        return FileManager.default.fileExists(atPath: externalDbPath.path)
    }

    /// Check if full database is available (downloaded or installed)
    func isFullDatabaseAvailable() -> Bool {
        return fullDatabaseExists() || UserDefaults.standard.fullDatabaseInstalled
    }

    /// Get path to full database file
    func fullDatabasePath() -> URL {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        return documentsPath.appendingPathComponent(fullDatabaseFileName)
    }

    // MARK: - Private Methods

    private func extractZipWithProgress(from zipURL: URL, to destinationURL: URL) async throws {
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                do {
                    // ZIPHandler extracts to destination directory
                    // The ZIP contains perseus_texts.db, we need to rename to perseus_texts_full.db
                    let tempDir = destinationURL.appendingPathComponent("temp_extract")

                    try? FileManager.default.removeItem(at: tempDir)
                    try FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)

                    try ZIPHandler.extractAll(from: zipURL, to: tempDir)

                    Task { @MainActor in
                        self?.extractionProgress = 0.8
                    }

                    // Find the extracted database file and rename it
                    let extractedDb = tempDir.appendingPathComponent("perseus_texts.db")
                    let targetDb = destinationURL.appendingPathComponent("perseus_texts_full.db")

                    if FileManager.default.fileExists(atPath: extractedDb.path) {
                        // Remove existing target if exists
                        try? FileManager.default.removeItem(at: targetDb)
                        // Move and rename
                        try FileManager.default.moveItem(at: extractedDb, to: targetDb)
                    }

                    // Cleanup temp directory
                    try? FileManager.default.removeItem(at: tempDir)

                    Task { @MainActor in
                        self?.extractionProgress = 1.0
                    }

                    continuation.resume()
                } catch {
                    continuation.resume(throwing: error)
                }
            }
        }
    }
}

// MARK: - Errors

enum DatabaseAssetError: LocalizedError {
    case zipNotFound
    case extractionFailed
    case databaseNotFound
    case insufficientStorage

    var errorDescription: String? {
        switch self {
        case .zipNotFound:
            return "Database ZIP file not found. Please try downloading again."
        case .extractionFailed:
            return "Failed to extract database file."
        case .databaseNotFound:
            return "Full database file not found."
        case .insufficientStorage:
            return "Not enough storage space available."
        }
    }
}
