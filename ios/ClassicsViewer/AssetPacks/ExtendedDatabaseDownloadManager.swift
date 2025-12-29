import Foundation
import Combine
import os.log

/// Manages the extended database asset pack download and switching
/// Matches DatabaseAssetDownloadManager behavior but for extended database
@MainActor
class ExtendedDatabaseDownloadManager: ObservableObject {
    static let shared = ExtendedDatabaseDownloadManager()

    // MARK: - Published State

    @Published var status: AssetDownloadStatus = .unknown
    @Published var downloadProgress: Double = 0
    @Published var extractionProgress: Double = 0
    @Published var errorMessage: String?
    @Published var currentDatabaseType: DatabaseType = .sample

    // MARK: - Constants

    private let assetInfo = AssetPackInfo.databaseExtended
    private let databaseZipName = "perseus_texts_extended.db.zip"
    private let extendedDatabaseFileName = "perseus_texts_extended.db"

    // MARK: - Private Properties

    private let logger = Logger(subsystem: "com.classicsviewer.app", category: "ExtendedDatabaseDownloadManager")

    private init() {}

    // MARK: - Status Check

    /// Check current status
    func checkStatus() async {
        // Determine current database type
        currentDatabaseType = determineCurrentDatabaseType()

        // Check if extended database is already extracted and active
        if currentDatabaseType == .extended {
            status = .active
            return
        }

        // Check if extended database file exists (extracted but not active)
        if extendedDatabaseExists() {
            status = .installed
            return
        }

        // Check if ODR download is available
        let isDownloaded = await ODRManager.shared.isDownloaded(tag: .databaseExtended)
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

        // Priority 2: Extended database (downloaded via ODR)
        if UserDefaults.standard.useExtendedDatabase && extendedDatabaseExists() {
            return .extended
        }

        // Priority 3: Full database (downloaded via ODR)
        if UserDefaults.standard.useFullDatabase && fullDatabaseExists() {
            return .full
        }

        // Priority 4: Bundled sample database
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
            try await ODRManager.shared.download(tag: .databaseExtended) { [weak self] progress in
                Task { @MainActor in
                    self?.downloadProgress = progress
                }
            }
            status = .downloaded
            logger.info("Extended database download completed")
        } catch {
            errorMessage = error.localizedDescription
            status = .failed
            logger.error("Extended database download failed: \(error.localizedDescription)")
        }
    }

    // MARK: - Extraction

    /// Extract downloaded ZIP to Documents directory
    func extractDatabase() async throws {
        status = .extracting
        extractionProgress = 0
        errorMessage = nil

        // Get ZIP path from ODR
        guard let zipURL = await ODRManager.shared.assetPath(tag: .databaseExtended, filename: databaseZipName) else {
            throw DatabaseAssetError.zipNotFound
        }

        logger.info("Extracting extended database from: \(zipURL.path)")

        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let targetPath = documentsPath.appendingPathComponent(extendedDatabaseFileName)

        do {
            // Remove existing extended database if it exists
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
            UserDefaults.standard.extendedDatabaseInstalled = true

            status = .installed
            logger.info("Extended database extracted successfully")

        } catch {
            errorMessage = error.localizedDescription
            status = .failed
            logger.error("Extended database extraction failed: \(error.localizedDescription)")
            throw error
        }
    }

    // MARK: - Activation

    /// Switch to extended database (requires app restart)
    func activateExtendedDatabase() async throws {
        guard extendedDatabaseExists() else {
            throw DatabaseAssetError.databaseNotFound
        }

        // Clear any external database setting
        UserDefaults.standard.externalDatabaseName = nil

        // Clear full database preference
        UserDefaults.standard.useFullDatabase = false

        // Set preference to use extended database
        UserDefaults.standard.useExtendedDatabase = true

        // Update status
        currentDatabaseType = .extended
        status = .active

        logger.info("Extended database activated - restart required")
    }

    /// Switch back to sample database
    func revertToSampleDatabase() async throws {
        // Clear extended database preference
        UserDefaults.standard.useExtendedDatabase = false

        // Update status
        currentDatabaseType = .sample
        status = .installed  // Extended DB still installed, just not active

        logger.info("Reverted to sample database - restart required")
    }

    // MARK: - Cancel & Remove

    /// Cancel ongoing download
    func cancelDownload() {
        Task {
            await ODRManager.shared.cancelDownload(tag: .databaseExtended)
        }
        status = .notDownloaded
        downloadProgress = 0
    }

    /// Remove extended database files
    func removeExtendedDatabase() async {
        do {
            let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
            let extendedDbPath = documentsPath.appendingPathComponent(extendedDatabaseFileName)

            // Delete the database file
            if FileManager.default.fileExists(atPath: extendedDbPath.path) {
                try FileManager.default.removeItem(at: extendedDbPath)
            }

            // Clear preferences
            UserDefaults.standard.extendedDatabaseInstalled = false
            UserDefaults.standard.useExtendedDatabase = false

            // Release ODR resources
            await ODRManager.shared.releaseResources(tag: .databaseExtended)

            // Update status
            currentDatabaseType = .sample
            status = .notDownloaded

            logger.info("Extended database removed successfully")
        } catch {
            errorMessage = error.localizedDescription
            logger.error("Failed to remove extended database: \(error.localizedDescription)")
        }
    }

    // MARK: - Helpers

    /// Check if extended database file exists
    func extendedDatabaseExists() -> Bool {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let extendedDbPath = documentsPath.appendingPathComponent(extendedDatabaseFileName)
        return FileManager.default.fileExists(atPath: extendedDbPath.path)
    }

    /// Check if full database file exists
    func fullDatabaseExists() -> Bool {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let fullDbPath = documentsPath.appendingPathComponent("perseus_texts_full.db")
        return FileManager.default.fileExists(atPath: fullDbPath.path)
    }

    /// Check if external database file exists
    func externalDatabaseExists() -> Bool {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let externalDbPath = documentsPath.appendingPathComponent("external_perseus_texts.db")
        return FileManager.default.fileExists(atPath: externalDbPath.path)
    }

    /// Get path to extended database file
    func extendedDatabasePath() -> URL {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        return documentsPath.appendingPathComponent(extendedDatabaseFileName)
    }

    // MARK: - Private Methods

    private func extractZipWithProgress(from zipURL: URL, to destinationURL: URL) async throws {
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                do {
                    // ZIPHandler extracts to destination directory
                    // The ZIP contains perseus_texts.db, we need to rename to perseus_texts_extended.db
                    let tempDir = destinationURL.appendingPathComponent("temp_extract_extended")

                    try? FileManager.default.removeItem(at: tempDir)
                    try FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)

                    try ZIPHandler.extractAll(from: zipURL, to: tempDir)

                    Task { @MainActor in
                        self?.extractionProgress = 0.8
                    }

                    // Find the extracted database file and rename it
                    let extractedDb = tempDir.appendingPathComponent("perseus_texts.db")
                    let targetDb = destinationURL.appendingPathComponent("perseus_texts_extended.db")

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
