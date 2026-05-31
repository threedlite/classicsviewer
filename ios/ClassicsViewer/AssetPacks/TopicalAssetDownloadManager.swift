import Foundation
import Combine
import os.log

/// Manages the Topical-links ODR pack download and on-device access.
/// Mirrors ReferencesAssetDownloadManager in shape.
///
/// Companion Android class: `TopicalPackManager` (Kotlin), which wraps Play
/// Asset Delivery for the on-demand `topical_pack`. The pack ships the
/// per-language `topical_<lang>.db.zip` files tagged "topical" in the Xcode
/// resource-tag configuration. `TopicalReader` extracts a given language's zip
/// (fetched here) into Application Support and reads the mmap'd bin files.
@MainActor
class TopicalAssetDownloadManager: ObservableObject {
    static let shared = TopicalAssetDownloadManager()

    // MARK: - Published State

    @Published var status: AssetDownloadStatus = .unknown
    @Published var downloadProgress: Double = 0
    @Published var errorMessage: String?

    // MARK: - Constants

    private let assetInfo = AssetPackInfo.topical

    // MARK: - Private Properties

    private let logger = Logger(subsystem: "com.classicsviewer.app", category: "TopicalAssetDownloadManager")

    private init() {}

    // MARK: - Status Check

    /// Re-check whether the topical pack is on-device.
    func checkStatus() async {
        let downloaded = await ODRManager.shared.isDownloaded(tag: .topical)
        if downloaded {
            UserDefaults.standard.topicalInstalled = true
            status = .installed
        } else {
            UserDefaults.standard.topicalInstalled = false
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
            try await ODRManager.shared.download(tag: .topical) { [weak self] progress in
                Task { @MainActor in
                    self?.downloadProgress = progress
                }
            }
            UserDefaults.standard.topicalInstalled = true
            status = .installed
        } catch {
            logger.error("Topical download failed: \(error.localizedDescription)")
            errorMessage = error.localizedDescription
            status = .failed
        }
    }

    func cancelDownload() async {
        await ODRManager.shared.cancelDownload(tag: .topical)
        status = .notDownloaded
    }

    // MARK: - Access

    /// URL of an installed per-language topical zip (e.g. "topical_greek.db.zip"),
    /// or nil if the pack is not on-device. `base` is the pack stem from
    /// `TopicalRegistry.dbBaseName` (e.g. "topical_greek").
    func zipURL(base: String) async -> URL? {
        return await ODRManager.shared.assetPath(tag: .topical, filename: "\(base).db.zip")
    }
}
