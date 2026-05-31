import Foundation
import Combine
import os.log

/// Manages the References ODR pack download and on-device access.
/// Mirrors AudioAssetDownloadManager / FullDatabaseDownloadManager in shape.
///
/// Companion Android class: `ReferencesPackManager` (Kotlin).
/// The references pack ships two PDFs + `references_manifest.json` tagged
/// "references" in the Xcode resource-tag configuration.
@MainActor
class ReferencesAssetDownloadManager: ObservableObject {
    static let shared = ReferencesAssetDownloadManager()

    // MARK: - Published State

    @Published var status: AssetDownloadStatus = .unknown
    @Published var downloadProgress: Double = 0
    @Published var errorMessage: String?
    @Published private(set) var manifest: ReferencesManifest?

    // MARK: - Constants

    private let assetInfo = AssetPackInfo.references
    static let manifestFilename = "references_manifest.json"

    // MARK: - Private Properties

    private let logger = Logger(subsystem: "com.classicsviewer.app", category: "ReferencesAssetDownloadManager")

    private init() {}

    // MARK: - Status Check

    /// Re-check whether the references pack is on-device.
    func checkStatus() async {
        let downloaded = await ODRManager.shared.isDownloaded(tag: .references)
        if downloaded {
            UserDefaults.standard.referencesInstalled = true
            status = .installed
            await loadManifestIfNeeded()
        } else {
            UserDefaults.standard.referencesInstalled = false
            status = .notDownloaded
        }
    }

    // MARK: - Download

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
            try await ODRManager.shared.download(tag: .references) { [weak self] progress in
                Task { @MainActor in
                    self?.downloadProgress = progress
                }
            }
            UserDefaults.standard.referencesInstalled = true
            await loadManifestIfNeeded()
            status = .installed
        } catch {
            logger.error("References download failed: \(error.localizedDescription)")
            errorMessage = error.localizedDescription
            status = .failed
        }
    }

    func cancelDownload() async {
        await ODRManager.shared.cancelDownload(tag: .references)
        status = .notDownloaded
    }

    // MARK: - Access

    /// URL of an installed reference PDF, or nil if the pack is not on-device.
    func pdfURL(for entry: ReferenceEntry) async -> URL? {
        return await ODRManager.shared.assetPath(tag: .references, filename: entry.filename)
    }

    /// Load and cache the manifest from the installed pack.
    @discardableResult
    func loadManifestIfNeeded() async -> ReferencesManifest? {
        if let manifest = manifest { return manifest }
        guard let url = await ODRManager.shared.assetPath(
            tag: .references,
            filename: Self.manifestFilename
        ) else {
            return nil
        }
        do {
            let data = try Data(contentsOf: url)
            let parsed = try JSONDecoder().decode(ReferencesManifest.self, from: data)
            manifest = parsed
            return parsed
        } catch {
            logger.error("Failed to parse references manifest: \(error.localizedDescription)")
            return nil
        }
    }
}
