import Foundation

/// Utility for managing storage space checks
struct StorageManager {

    // MARK: - Storage Space

    /// Get available free space on device in bytes
    /// Uses volumeAvailableCapacityForImportantUsage for accurate available space
    static func availableFreeSpace() -> Int64 {
        let fileURL = URL(fileURLWithPath: NSHomeDirectory())
        do {
            let values = try fileURL.resourceValues(forKeys: [.volumeAvailableCapacityForImportantUsageKey])
            return values.volumeAvailableCapacityForImportantUsage ?? 0
        } catch {
            print("StorageManager: Failed to get available space: \(error)")
            return 0
        }
    }

    /// Get available free space in GB
    static func availableFreeSpaceGB() -> Int64 {
        return availableFreeSpace() / 1024 / 1024 / 1024
    }

    /// Check if there's enough space for an asset pack
    /// - Parameter assetPack: The asset pack info to check against
    /// - Returns: true if enough space is available
    static func hasEnoughSpace(for assetPack: AssetPackInfo) -> Bool {
        let available = availableFreeSpace()
        let hasSpace = available >= assetPack.requiredFreeSpace
        print("StorageManager: Available: \(formatBytes(available)), Required: \(formatBytes(assetPack.requiredFreeSpace)), HasSpace: \(hasSpace)")
        return hasSpace
    }

    /// Check if there's enough space for a specific byte requirement
    /// - Parameter bytes: Required bytes
    /// - Returns: true if enough space is available
    static func hasEnoughSpace(bytes: Int64) -> Bool {
        return availableFreeSpace() >= bytes
    }

    // MARK: - Formatting

    /// Format bytes to human-readable string (KB, MB, GB)
    /// - Parameter bytes: Number of bytes
    /// - Returns: Formatted string like "1.5 GB"
    static func formatBytes(_ bytes: Int64) -> String {
        let formatter = ByteCountFormatter()
        formatter.allowedUnits = [.useKB, .useMB, .useGB]
        formatter.countStyle = .file
        return formatter.string(fromByteCount: bytes)
    }

    // MARK: - Directory Sizes

    /// Get size of app's Documents directory in bytes
    static func documentsDirectorySize() -> Int64 {
        guard let documentsURL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else {
            return 0
        }
        return directorySize(at: documentsURL)
    }

    /// Get size of app's Caches directory in bytes
    static func cachesDirectorySize() -> Int64 {
        guard let cachesURL = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first else {
            return 0
        }
        return directorySize(at: cachesURL)
    }

    /// Calculate total size of a directory and its contents
    /// - Parameter url: Directory URL
    /// - Returns: Total size in bytes
    static func directorySize(at url: URL) -> Int64 {
        let fileManager = FileManager.default
        var totalSize: Int64 = 0

        guard let enumerator = fileManager.enumerator(
            at: url,
            includingPropertiesForKeys: [.fileSizeKey, .isDirectoryKey],
            options: [.skipsHiddenFiles],
            errorHandler: nil
        ) else {
            return 0
        }

        for case let fileURL as URL in enumerator {
            do {
                let resourceValues = try fileURL.resourceValues(forKeys: [.fileSizeKey, .isDirectoryKey])
                if resourceValues.isDirectory == false {
                    totalSize += Int64(resourceValues.fileSize ?? 0)
                }
            } catch {
                // Skip files we can't read
                continue
            }
        }

        return totalSize
    }

    // MARK: - File Existence

    /// Check if a file exists at the given path
    static func fileExists(at path: String) -> Bool {
        return FileManager.default.fileExists(atPath: path)
    }

    /// Check if a file exists at the given URL
    static func fileExists(at url: URL) -> Bool {
        return FileManager.default.fileExists(atPath: url.path)
    }

    /// Get file size in bytes, or nil if file doesn't exist
    static func fileSize(at url: URL) -> Int64? {
        do {
            let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
            return attributes[.size] as? Int64
        } catch {
            return nil
        }
    }

    // MARK: - Common Paths

    /// Get the Documents directory URL
    static var documentsDirectory: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
    }

    /// Get the Caches directory URL
    static var cachesDirectory: URL {
        FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first!
    }

    /// Get path to database file
    /// - Parameter name: Database filename (e.g., "perseus_texts.db")
    /// - Returns: Full URL to database in Documents
    static func databasePath(named name: String) -> URL {
        return documentsDirectory.appendingPathComponent(name)
    }

    /// Get path to audio directory
    static var audioDirectory: URL {
        return documentsDirectory.appendingPathComponent("audio")
    }
}
