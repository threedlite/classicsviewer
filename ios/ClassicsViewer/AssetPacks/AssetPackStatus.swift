import Foundation

/// Information about an asset pack
struct AssetPackInfo {
    let tag: ODRManager.AssetTag
    let displayName: String
    let description: String
    let compressedSize: Int64      // Size to download (ZIP)
    let extractedSize: Int64       // Size after extraction
    let requiredFreeSpace: Int64   // Minimum free space needed

    // MARK: - Predefined Asset Packs (matching Android values)

    /// Full Homer Iliad audio narration by David Chamberlain
    static let audioFull = AssetPackInfo(
        tag: .audioFull,
        displayName: "Homer Iliad Full Audio",
        description: "Complete audio narration by David Chamberlain",
        compressedSize: 1_024_000_000,      // ~1GB
        extractedSize: 1_100_000_000,       // ~1.1GB
        requiredFreeSpace: 4_294_967_296    // 4GB (matches Android REQUIRED_SPACE_BYTES)
    )

    /// Full Perseus database with all Greek and Latin authors
    static let databaseFull = AssetPackInfo(
        tag: .databaseFull,
        displayName: "Full Perseus Database",
        description: "All 100+ Greek and Latin authors",
        compressedSize: 1_300_000_000,      // ~1.3GB compressed ZIP
        extractedSize: 7_000_000_000,       // ~7GB uncompressed
        requiredFreeSpace: 25_000_000_000   // 25GB (matches Android REQUIRED_SPACE_BYTES)
    )

    /// Extended database with all languages and sources
    static let databaseExtended = AssetPackInfo(
        tag: .databaseExtended,
        displayName: "Extended Database",
        description: "All 14 languages, 778 authors, 2,723 works",
        compressedSize: 3_612_000_000,      // ~3.6GB compressed ZIP
        extractedSize: 18_028_000_000,      // ~18GB uncompressed
        requiredFreeSpace: 55_000_000_000   // 55GB for safe extraction
    )
}

// MARK: - Download Status Enum

/// Status of an asset pack download/installation
enum AssetDownloadStatus: Equatable {
    case unknown
    case notDownloaded
    case downloading
    case downloaded          // ZIP available, not extracted
    case extracting
    case installed           // Fully installed and ready
    case active              // Currently in use (for database)
    case failed

    var displayText: String {
        switch self {
        case .unknown: return "Checking..."
        case .notDownloaded: return "Not Downloaded"
        case .downloading: return "Downloading..."
        case .downloaded: return "Ready to Extract"
        case .extracting: return "Extracting..."
        case .installed: return "Installed"
        case .active: return "Active"
        case .failed: return "Failed"
        }
    }

    var isAvailable: Bool {
        switch self {
        case .installed, .active:
            return true
        default:
            return false
        }
    }
}

// MARK: - Database Type Enum

/// Type of database currently in use
enum DatabaseType: String, CaseIterable {
    case sample = "sample"        // Bundled sample database
    case full = "full"            // Downloaded full database
    case extended = "extended"    // Downloaded extended database (Perseus + First1K + PTA)
    case external = "external"    // User-imported database

    var displayName: String {
        switch self {
        case .sample: return "Sample Database"
        case .full: return "Full Database"
        case .extended: return "Extended Database"
        case .external: return "External Database"
        }
    }

    var description: String {
        switch self {
        case .sample:
            return "Includes selected Greek and Latin authors"
        case .full:
            return "All 100+ Greek and Latin authors from Perseus"
        case .extended:
            return "All 14 languages, 778 authors, 2,723 works"
        case .external:
            return "User-imported custom database"
        }
    }

    var iconName: String {
        switch self {
        case .sample: return "cylinder"
        case .full: return "cylinder.split.1x2.fill"
        case .extended: return "cylinder.split.1x2.fill"
        case .external: return "doc.badge.arrow.up"
        }
    }
}

// MARK: - UserDefaults Keys

/// UserDefaults keys for asset pack management
enum AssetPackKeys {
    // Database keys
    static let useFullDatabase = "use_full_database"
    static let fullDatabaseInstalled = "full_database_installed"
    static let useExtendedDatabase = "use_extended_database"
    static let extendedDatabaseInstalled = "extended_database_installed"
    static let externalDatabaseName = "externalDatabaseName"

    // Audio keys
    static let fullAudioInstalled = "full_audio_installed"
}

// MARK: - UserDefaults Extension

extension UserDefaults {
    /// Whether the full database is currently enabled
    var useFullDatabase: Bool {
        get { bool(forKey: AssetPackKeys.useFullDatabase) }
        set { set(newValue, forKey: AssetPackKeys.useFullDatabase) }
    }

    /// Whether the full database has been downloaded and extracted
    var fullDatabaseInstalled: Bool {
        get { bool(forKey: AssetPackKeys.fullDatabaseInstalled) }
        set { set(newValue, forKey: AssetPackKeys.fullDatabaseInstalled) }
    }

    /// Whether the extended database is currently enabled
    var useExtendedDatabase: Bool {
        get { bool(forKey: AssetPackKeys.useExtendedDatabase) }
        set { set(newValue, forKey: AssetPackKeys.useExtendedDatabase) }
    }

    /// Whether the extended database has been downloaded and extracted
    var extendedDatabaseInstalled: Bool {
        get { bool(forKey: AssetPackKeys.extendedDatabaseInstalled) }
        set { set(newValue, forKey: AssetPackKeys.extendedDatabaseInstalled) }
    }

    /// Whether the full audio pack has been downloaded and extracted
    var fullAudioInstalled: Bool {
        get { bool(forKey: AssetPackKeys.fullAudioInstalled) }
        set { set(newValue, forKey: AssetPackKeys.fullAudioInstalled) }
    }

    /// Name of externally imported database (if any)
    var externalDatabaseName: String? {
        get { string(forKey: AssetPackKeys.externalDatabaseName) }
        set { set(newValue, forKey: AssetPackKeys.externalDatabaseName) }
    }
}
