import Foundation
import SQLite3

enum DatabaseError: LocalizedError {
    case fileNotFound
    case cannotOpen
    case corruptedDatabase
    case notInitialized
    case prepareFailed(String)
    case executionFailed
    case invalidParameter
    case extractionFailed

    var errorDescription: String? {
        switch self {
        case .fileNotFound:
            return "Database file not found"
        case .cannotOpen:
            return "Cannot open database"
        case .corruptedDatabase:
            return "Database is corrupted"
        case .notInitialized:
            return "Database not initialized"
        case .prepareFailed(let query):
            return "Failed to prepare query: \(query)"
        case .executionFailed:
            return "Failed to execute query"
        case .invalidParameter:
            return "Invalid parameter"
        case .extractionFailed:
            return "Failed to extract database"
        }
    }
}

/// Thread-safe database manager using actor pattern for concurrent access
actor DatabaseManagerAsync {
    static let shared = DatabaseManagerAsync()

    /// Database filename depends on which database is active
    /// - Sample: perseus_texts.db (bundled)
    /// - Full: perseus_texts_full.db (downloaded via ODR)
    /// - External: perseus_texts.db (user-imported, replaces sample)
    private var databaseName: String {
        // Check if full database is enabled
        if UserDefaults.standard.useFullDatabase {
            return "perseus_texts_full.db"
        }
        // Default to sample/external database
        return "perseus_texts.db"
    }

    private var db: OpaquePointer?
    private var state: ConnectionState = .uninitialized

    private enum ConnectionState: Equatable {
        case uninitialized
        case initializing
        case ready
        case error(Error)

        static func == (lhs: ConnectionState, rhs: ConnectionState) -> Bool {
            switch (lhs, rhs) {
            case (.uninitialized, .uninitialized),
                 (.initializing, .initializing),
                 (.ready, .ready):
                return true
            case (.error(_), .error(_)):
                return true
            default:
                return false
            }
        }
    }

    var databasePath: String {
        let documentsPath = NSSearchPathForDirectoriesInDomains(.documentDirectory, .userDomainMask, true).first!
        return (documentsPath as NSString).appendingPathComponent(databaseName)
    }

    private init() {}

    /// Initialize database connection once at app startup
    func initialize() async throws {
        switch state {
        case .ready:
            print("DatabaseManagerAsync: Already initialized")
            return
        case .initializing:
            print("DatabaseManagerAsync: Already initializing, waiting...")
            // Wait for ongoing initialization
            while state == .initializing {
                try await Task.sleep(nanoseconds: 10_000_000) // 10ms
            }
            try await ensureReady()
            return
        case .error(let error):
            print("DatabaseManagerAsync: Previous error, retrying: \(error)")
            state = .uninitialized
        case .uninitialized:
            break
        }

        state = .initializing

        do {
            try openDatabaseConnection()
            state = .ready
            print("DatabaseManagerAsync: Database initialized successfully")
        } catch {
            state = .error(error)
            print("DatabaseManagerAsync: Failed to initialize: \(error)")
            throw error
        }
    }

    private func openDatabaseConnection() throws {
        // Check if database file exists
        let fileManager = FileManager.default
        guard fileManager.fileExists(atPath: databasePath) else {
            print("DatabaseManagerAsync: Database file not found at \(databasePath)")
            throw DatabaseError.fileNotFound
        }

        // Check file size
        let attributes = try fileManager.attributesOfItem(atPath: databasePath)
        let fileSize = attributes[.size] as? Int64 ?? 0
        print("DatabaseManagerAsync: Opening database at \(databasePath)")
        print("DatabaseManagerAsync: Database file size: \(fileSize) bytes (\(Double(fileSize) / 1_000_000_000.0) GB)")
        if fileSize < 1000 { // Less than 1KB is too small
            print("DatabaseManagerAsync: Database file too small (\(fileSize) bytes)")
            throw DatabaseError.corruptedDatabase
        }

        // Open database
        var tempDb: OpaquePointer?
        let result = sqlite3_open_v2(
            databasePath,
            &tempDb,
            SQLITE_OPEN_READWRITE | SQLITE_OPEN_FULLMUTEX, // Thread-safe mode
            nil
        )

        guard result == SQLITE_OK, let tempDb = tempDb else {
            let errorMessage = String(cString: sqlite3_errmsg(tempDb))
            print("DatabaseManagerAsync: Failed to open database: \(errorMessage)")
            if let tempDb = tempDb {
                sqlite3_close(tempDb)
            }
            throw DatabaseError.cannotOpen
        }

        self.db = tempDb

        // Enable extended result codes
        sqlite3_extended_result_codes(db, 1)

        // Set busy timeout to 5 seconds
        sqlite3_busy_timeout(db, 5000)

        // Test database
        var testStatement: OpaquePointer?
        let testResult = sqlite3_prepare_v2(db, "SELECT sqlite_version()", -1, &testStatement, nil)
        guard testResult == SQLITE_OK else {
            let errorMessage = String(cString: sqlite3_errmsg(db))
            print("DatabaseManagerAsync: Database test failed: \(errorMessage)")
            sqlite3_close(db)
            self.db = nil
            throw DatabaseError.corruptedDatabase
        }
        sqlite3_finalize(testStatement)

        print("DatabaseManagerAsync: Database opened successfully")
    }

    /// Ensure database is ready before operations
    private func ensureReady() async throws {
        switch state {
        case .ready:
            guard db != nil else {
                state = .uninitialized
                try await initialize()
                return
            }
            return
        case .uninitialized:
            try await initialize()
        case .initializing:
            while state == .initializing {
                try await Task.sleep(nanoseconds: 10_000_000) // 10ms
            }
            try await ensureReady()
        case .error(let error):
            throw error
        }
    }

    /// Execute a query that returns results
    func executeQuery<T>(
        _ query: String,
        parameters: [Any?] = [],
        mapper: @escaping (OpaquePointer) -> T?
    ) async throws -> [T] {
        try await ensureReady()

        guard let db = db else {
            throw DatabaseError.notInitialized
        }

        var statement: OpaquePointer?

        // Prepare statement
        guard sqlite3_prepare_v2(db, query, -1, &statement, nil) == SQLITE_OK else {
            let errorMessage = String(cString: sqlite3_errmsg(db))
            print("DatabaseManagerAsync: Failed to prepare query: \(errorMessage)")
            print("Query: \(query)")
            throw DatabaseError.prepareFailed(query)
        }

        defer { sqlite3_finalize(statement) }

        // Bind parameters
        for (index, parameter) in parameters.enumerated() {
            let paramIndex = Int32(index + 1)

            switch parameter {
            case let value as String:
                let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)
                sqlite3_bind_text(statement, paramIndex, value, -1, SQLITE_TRANSIENT)
            case let value as Int:
                sqlite3_bind_int(statement, paramIndex, Int32(value))
            case let value as Int32:
                sqlite3_bind_int(statement, paramIndex, value)
            case let value as Int64:
                sqlite3_bind_int64(statement, paramIndex, value)
            case let value as Double:
                sqlite3_bind_double(statement, paramIndex, value)
            case nil:
                sqlite3_bind_null(statement, paramIndex)
            default:
                print("DatabaseManagerAsync: Unknown parameter type: \(String(describing: parameter))")
                throw DatabaseError.invalidParameter
            }
        }

        // Execute and collect results
        var results: [T] = []

        while sqlite3_step(statement) == SQLITE_ROW {
            if let result = mapper(statement!) {
                results.append(result)
            }
        }

        return results
    }

    /// Execute a query that doesn't return results
    func execute(_ query: String, parameters: [Any?] = []) async throws {
        try await ensureReady()

        guard let db = db else {
            throw DatabaseError.notInitialized
        }

        var statement: OpaquePointer?

        guard sqlite3_prepare_v2(db, query, -1, &statement, nil) == SQLITE_OK else {
            let errorMessage = String(cString: sqlite3_errmsg(db))
            print("DatabaseManagerAsync: Failed to prepare statement: \(errorMessage)")
            throw DatabaseError.prepareFailed(query)
        }

        defer { sqlite3_finalize(statement) }

        // Bind parameters
        for (index, parameter) in parameters.enumerated() {
            let paramIndex = Int32(index + 1)

            switch parameter {
            case let value as String:
                let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)
                sqlite3_bind_text(statement, paramIndex, value, -1, SQLITE_TRANSIENT)
            case let value as Int:
                sqlite3_bind_int(statement, paramIndex, Int32(value))
            case let value as Int32:
                sqlite3_bind_int(statement, paramIndex, value)
            case let value as Int64:
                sqlite3_bind_int64(statement, paramIndex, value)
            case let value as Double:
                sqlite3_bind_double(statement, paramIndex, value)
            case nil:
                sqlite3_bind_null(statement, paramIndex)
            default:
                throw DatabaseError.invalidParameter
            }
        }

        guard sqlite3_step(statement) == SQLITE_DONE else {
            let errorMessage = String(cString: sqlite3_errmsg(db))
            print("DatabaseManagerAsync: Execution failed: \(errorMessage)")
            throw DatabaseError.executionFailed
        }
    }

    /// Check if database is ready
    func isReady() async -> Bool {
        switch state {
        case .ready:
            return db != nil
        default:
            return false
        }
    }

    /// Get database status
    func getStatus() async -> String {
        switch state {
        case .uninitialized:
            return "Uninitialized"
        case .initializing:
            return "Initializing..."
        case .ready:
            return "Ready"
        case .error(let error):
            return "Error: \(error.localizedDescription)"
        }
    }

    /// Recover from error state
    func recover() async throws {
        print("DatabaseManagerAsync: Attempting recovery...")

        // Close existing connection if any
        if let db = db {
            sqlite3_close_v2(db)
            self.db = nil
        }

        // Reset state and reinitialize
        state = .uninitialized
        try await initialize()
    }

    /// Extract database from bundle
    /// Uses memory-efficient streaming extraction via ZIPHandler
    func extractDatabase(progress: Progress? = nil) async throws {
        print("DatabaseManagerAsync: Starting database extraction...")

        guard let bundleURL = Bundle.main.url(forResource: "perseus_texts", withExtension: "db.zip") else {
            print("DatabaseManagerAsync: Database not found in bundle")
            throw DatabaseError.fileNotFound
        }

        let documentsPath = NSSearchPathForDirectoriesInDomains(.documentDirectory, .userDomainMask, true).first!
        let documentsURL = URL(fileURLWithPath: documentsPath)
        let databaseURL = documentsURL.appendingPathComponent(databaseName)

        // Remove existing database if present
        if FileManager.default.fileExists(atPath: databaseURL.path) {
            try FileManager.default.removeItem(at: databaseURL)
        }

        // Extract using memory-efficient streaming via ZIPHandler
        // This is critical for large databases (100MB+ compressed, 1GB+ uncompressed)
        progress?.totalUnitCount = 100
        progress?.completedUnitCount = 10

        do {
            try ZIPHandler.extractDatabase(from: bundleURL, to: databaseURL) { extractProgress in
                progress?.completedUnitCount = Int64(10 + extractProgress * 90)
            }
            progress?.completedUnitCount = 100

            print("DatabaseManagerAsync: Database extracted successfully to \(databaseURL.path)")
        } catch {
            print("DatabaseManagerAsync: Failed to extract database: \(error)")
            throw DatabaseError.cannotOpen
        }
    }

    /// Close database (only for app termination)
    func close() async {
        if let db = db {
            sqlite3_close_v2(db)
            self.db = nil
        }
        state = .uninitialized
        print("DatabaseManagerAsync: Database closed")
    }
}