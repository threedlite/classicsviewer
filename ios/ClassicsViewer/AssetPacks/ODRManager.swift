import Foundation

/// Manages On-Demand Resource requests and lifecycle
/// This is the iOS equivalent of Android's Play Asset Delivery
actor ODRManager {
    static let shared = ODRManager()

    // MARK: - Asset Pack Tags

    /// Asset pack tags (must match Xcode resource tag configuration)
    enum AssetTag: String, CaseIterable {
        case audioFull = "audio_full"
        case databaseFull = "database_full"
        case databaseExtended = "database_extended"
        case references = "references"
    }

    // MARK: - Download Status

    enum DownloadStatus: Equatable {
        case notDownloaded
        case downloading(progress: Double)
        case downloaded
        case failed(Error)

        static func == (lhs: DownloadStatus, rhs: DownloadStatus) -> Bool {
            switch (lhs, rhs) {
            case (.notDownloaded, .notDownloaded): return true
            case (.downloaded, .downloaded): return true
            case (.downloading(let p1), .downloading(let p2)): return p1 == p2
            case (.failed, .failed): return true
            default: return false
            }
        }
    }

    // MARK: - Properties

    private var activeRequests: [String: NSBundleResourceRequest] = [:]
    private var progressObservations: [String: NSKeyValueObservation] = [:]

    // MARK: - Public Methods

    /// Check if asset pack is available locally (already downloaded)
    /// Returns true if resources are on device, false if download required
    func isDownloaded(tag: AssetTag) async -> Bool {
        let request = NSBundleResourceRequest(tags: [tag.rawValue])
        let available = await request.conditionallyBeginAccessingResources()

        if available {
            // Resources are available - end access since we're just checking
            request.endAccessingResources()
        }

        return available
    }

    /// Start downloading asset pack with progress callback
    /// - Parameters:
    ///   - tag: The asset tag to download
    ///   - progressCallback: Called with download progress (0.0 to 1.0)
    /// - Throws: Error if download fails
    func download(tag: AssetTag, progressCallback: @escaping (Double) -> Void) async throws {
        let tagString = tag.rawValue
        let request = NSBundleResourceRequest(tags: [tagString])

        // Store reference to allow cancellation
        activeRequests[tagString] = request

        // Set up progress observation using KVO
        let observation = request.progress.observe(\.fractionCompleted) { progress, _ in
            Task { @MainActor in
                progressCallback(progress.fractionCompleted)
            }
        }
        progressObservations[tagString] = observation

        defer {
            // Clean up observation when done
            progressObservations[tagString]?.invalidate()
            progressObservations.removeValue(forKey: tagString)
        }

        // Check if already available first (recommended pattern per Apple docs)
        let alreadyAvailable = await request.conditionallyBeginAccessingResources()

        if !alreadyAvailable {
            // Not on device - download from App Store
            try await request.beginAccessingResources()
        }

        // Resources now accessible via request.bundle
        // Keep request alive in activeRequests for later access
    }

    /// Get URL for a file within the downloaded ODR bundle
    /// - Parameters:
    ///   - tag: The asset tag
    ///   - filename: The filename including extension (e.g., "audio.zip")
    /// - Returns: URL to the resource, or nil if not available
    func assetPath(tag: AssetTag, filename: String) async -> URL? {
        guard let request = activeRequests[tag.rawValue] else {
            // Try to access the resource if not already active
            let newRequest = NSBundleResourceRequest(tags: [tag.rawValue])
            let available = await newRequest.conditionallyBeginAccessingResources()

            if available {
                activeRequests[tag.rawValue] = newRequest
                return getResourceURL(from: newRequest, filename: filename)
            }
            return nil
        }

        return getResourceURL(from: request, filename: filename)
    }

    /// Release resources - allows system to purge when storage is low
    /// Call this when done using the resources
    func releaseResources(tag: AssetTag) {
        let tagString = tag.rawValue

        // Cancel any progress observation
        progressObservations[tagString]?.invalidate()
        progressObservations.removeValue(forKey: tagString)

        // End resource access
        if let request = activeRequests.removeValue(forKey: tagString) {
            request.endAccessingResources()
        }
    }

    /// Cancel ongoing download
    func cancelDownload(tag: AssetTag) {
        let tagString = tag.rawValue

        // Cancel progress observation
        progressObservations[tagString]?.invalidate()
        progressObservations.removeValue(forKey: tagString)

        // Cancel and release the request
        if let request = activeRequests.removeValue(forKey: tagString) {
            request.progress.cancel()
            request.endAccessingResources()
        }
    }

    /// Get estimated size of asset pack in bytes
    func estimatedSize(tag: AssetTag) -> Int64 {
        switch tag {
        case .audioFull:
            return AssetPackInfo.audioFull.compressedSize
        case .databaseFull:
            return AssetPackInfo.databaseFull.compressedSize
        case .databaseExtended:
            return AssetPackInfo.databaseExtended.compressedSize
        case .references:
            return AssetPackInfo.references.compressedSize
        }
    }

    // MARK: - Private Methods

    private func getResourceURL(from request: NSBundleResourceRequest, filename: String) -> URL? {
        // Parse filename and extension
        let name = (filename as NSString).deletingPathExtension
        let ext = (filename as NSString).pathExtension

        // IMPORTANT: ODR resources are in the request's bundle, NOT Bundle.main
        return request.bundle.url(forResource: name, withExtension: ext)
    }
}

// MARK: - Low Disk Space Notification

extension ODRManager {
    /// Register for low disk space notifications
    /// Call this from app initialization
    @MainActor
    static func registerForLowDiskSpaceNotifications() {
        // NSBundleResourceRequestLowDiskSpaceNotification is the Objective-C constant name
        let lowDiskSpaceNotification = Notification.Name("NSBundleResourceRequestLowDiskSpaceNotification")

        NotificationCenter.default.addObserver(
            forName: lowDiskSpaceNotification,
            object: nil,
            queue: .main
        ) { _ in
            // System is purging on-demand resources
            // Extracted files in Documents are safe, but ODR ZIPs may be removed
            print("ODRManager: Low disk space - ODR resources may be purged")

            // Post notification for UI to handle
            NotificationCenter.default.post(
                name: .odrResourcesMayBePurged,
                object: nil
            )
        }
    }
}

// MARK: - Notification Names

extension Notification.Name {
    static let odrResourcesMayBePurged = Notification.Name("ODRResourcesMayBePurged")
}
