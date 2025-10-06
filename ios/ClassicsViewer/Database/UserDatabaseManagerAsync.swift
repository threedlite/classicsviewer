import Foundation
import SQLite3

/// Thread-safe user database manager using actor pattern for concurrent access
actor UserDatabaseManagerAsync {
    static let shared = UserDatabaseManagerAsync()

    private let databaseName = "user_data.db"
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
            print("UserDatabaseManagerAsync: Already initialized")
            return
        case .initializing:
            print("UserDatabaseManagerAsync: Already initializing, waiting...")
            // Wait for ongoing initialization
            while state == .initializing {
                try await Task.sleep(nanoseconds: 10_000_000) // 10ms
            }
            try await ensureReady()
            return
        case .error(let error):
            print("UserDatabaseManagerAsync: Previous error, retrying: \(error)")
            state = .uninitialized
        case .uninitialized:
            break
        }

        state = .initializing

        do {
            print("UserDatabaseManagerAsync: Opening database connection...")
            try await openDatabaseConnection()
            print("UserDatabaseManagerAsync: Creating tables...")
            try await createTablesIfNeeded()
            state = .ready
            print("UserDatabaseManagerAsync: Database initialized successfully with tables created")
        } catch {
            state = .error(error)
            print("UserDatabaseManagerAsync: Failed to initialize: \(error)")
            print("UserDatabaseManagerAsync: Error details: \(error.localizedDescription)")
            throw error
        }
    }

    private func openDatabaseConnection() async throws {
        // Check if file exists and is readable
        let fileManager = FileManager.default
        let fileExists = fileManager.fileExists(atPath: databasePath)

        if fileExists {
            // Check if file is readable and not corrupted
            guard fileManager.isReadableFile(atPath: databasePath) else {
                print("UserDatabaseManagerAsync: Database file exists but is not readable: \(databasePath)")
                throw DatabaseError.cannotOpen
            }

            // Check file size - if it's too small, it might be corrupted
            do {
                let attributes = try fileManager.attributesOfItem(atPath: databasePath)
                let fileSize = attributes[.size] as? Int64 ?? 0
                if fileSize < 1024 { // Less than 1KB is suspicious for a SQLite database
                    print("UserDatabaseManagerAsync: Database file is too small (\(fileSize) bytes), possibly corrupted")
                    // Delete corrupted file so it can be recreated
                    try? fileManager.removeItem(atPath: databasePath)
                }
            } catch {
                print("UserDatabaseManagerAsync: Could not read file attributes: \(error)")
                throw DatabaseError.cannotOpen
            }
        }

        // Open database with extended result codes for better error reporting
        var result = sqlite3_open_v2(databasePath, &db, SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE, nil)
        if result != SQLITE_OK {
            print("UserDatabaseManagerAsync: Failed to open database, result code: \(result)")
            if let db = db {
                let errorMessage = String(cString: sqlite3_errmsg(db))
                print("UserDatabaseManagerAsync: SQLite error: \(errorMessage)")
                sqlite3_close(db)
                self.db = nil
            }
            throw DatabaseError.cannotOpen
        }

        // Enable extended result codes for better error diagnostics
        sqlite3_extended_result_codes(db, 1)

        // Test basic database functionality with a simple query
        var testStatement: OpaquePointer?
        result = sqlite3_prepare_v2(db, "SELECT sqlite_version()", -1, &testStatement, nil)
        if result != SQLITE_OK {
            let errorMessage = String(cString: sqlite3_errmsg(db!))
            print("UserDatabaseManagerAsync: Database integrity test failed: \(errorMessage)")
            sqlite3_close(db)
            self.db = nil
            throw DatabaseError.cannotOpen
        }
        sqlite3_finalize(testStatement)

        print("UserDatabaseManagerAsync: Database opened and validated successfully")
    }

    private func createTablesIfNeeded() async throws {
        print("UserDatabaseManagerAsync: Starting table creation...")

        // User Dictionary Tables
        try await execute("""
            CREATE TABLE IF NOT EXISTS user_dictionary_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_name TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                description TEXT,
                language TEXT NOT NULL,
                source_info TEXT,
                import_date INTEGER NOT NULL,
                file_size INTEGER,
                lemma_count INTEGER,
                is_enabled INTEGER DEFAULT 1
            )
        """)

        try await execute("""
            CREATE TABLE IF NOT EXISTS user_dictionary_lemmas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_id INTEGER NOT NULL,
                lemma TEXT NOT NULL,
                lemma_normalized_ultra TEXT,
                language TEXT NOT NULL,
                definition_plain TEXT NOT NULL,
                definition_html TEXT,
                source_name TEXT DEFAULT 'User Import',
                import_file_name TEXT NOT NULL,
                import_date INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (package_id) REFERENCES user_dictionary_packages(id) ON DELETE CASCADE
            )
        """)

        try await execute("""
            CREATE TABLE IF NOT EXISTS user_lemma_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inflected_form TEXT NOT NULL,
                lemma TEXT NOT NULL,
                language TEXT NOT NULL,
                source TEXT NOT NULL,
                package_id INTEGER,
                FOREIGN KEY (package_id) REFERENCES user_dictionary_packages(id) ON DELETE CASCADE
            )
        """)

        // Audio Package Tables
        try await execute("""
            CREATE TABLE IF NOT EXISTS audio_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_name TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                description TEXT,
                version TEXT,
                created_date INTEGER,
                import_date INTEGER NOT NULL,
                file_count INTEGER DEFAULT 0,
                total_size INTEGER DEFAULT 0,
                is_enabled INTEGER DEFAULT 1
            )
        """)

        try await execute("""
            CREATE TABLE IF NOT EXISTS audio_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_id INTEGER NOT NULL,
                work_id TEXT NOT NULL,
                book_id TEXT,
                line_start INTEGER NOT NULL,
                line_end INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                duration_ms INTEGER,
                file_size INTEGER,
                mime_type TEXT DEFAULT 'audio/mpeg',
                FOREIGN KEY (package_id) REFERENCES audio_packages(id) ON DELETE CASCADE
            )
        """)

        // Normalization Patterns Table (dynamic creation - NOT tracked as Room entity in Android)
        // This matches Android's UserDatabase pattern: created via callback, not as an entity
        try await execute("""
            CREATE TABLE IF NOT EXISTS normalization_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                package_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                pattern TEXT NOT NULL,
                replacement TEXT NOT NULL,
                description TEXT,
                priority INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (package_id) REFERENCES user_dictionary_packages(id) ON DELETE CASCADE
            )
        """)

        // Create indexes
        try await execute("CREATE INDEX IF NOT EXISTS idx_user_dictionary_lemmas_package ON user_dictionary_lemmas(package_id)")
        try await execute("CREATE INDEX IF NOT EXISTS idx_user_dictionary_lemmas_lemma ON user_dictionary_lemmas(lemma)")
        try await execute("CREATE INDEX IF NOT EXISTS idx_user_lemma_mappings_inflected ON user_lemma_mappings(inflected_form)")
        try await execute("CREATE INDEX IF NOT EXISTS idx_user_lemma_mappings_package ON user_lemma_mappings(package_id)")
        try await execute("CREATE INDEX IF NOT EXISTS idx_audio_files_package ON audio_files(package_id)")
        try await execute("CREATE INDEX IF NOT EXISTS idx_audio_files_work ON audio_files(work_id)")
        try await execute("CREATE INDEX IF NOT EXISTS idx_audio_files_book ON audio_files(book_id)")

        // Normalization patterns indexes
        try await execute("CREATE INDEX IF NOT EXISTS idx_normalization_patterns_language ON normalization_patterns(language)")
        try await execute("CREATE INDEX IF NOT EXISTS idx_normalization_patterns_package ON normalization_patterns(package_id)")
        try await execute("CREATE INDEX IF NOT EXISTS idx_normalization_patterns_lang_pkg_pri ON normalization_patterns(language, package_id, priority)")

        print("UserDatabaseManagerAsync: All tables and indexes created successfully")
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
            print("UserDatabaseManagerAsync: Failed to prepare query: \(errorMessage)")
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
            case let value as Date:
                sqlite3_bind_int64(statement, paramIndex, Int64(value.timeIntervalSince1970 * 1000))
            case nil:
                sqlite3_bind_null(statement, paramIndex)
            default:
                print("UserDatabaseManagerAsync: Unknown parameter type: \(String(describing: parameter))")
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
        // Don't call ensureReady() if we're in the middle of initialization
        if state != .initializing {
            try await ensureReady()
        }

        guard let db = db else {
            print("UserDatabaseManagerAsync: Database not initialized when trying to execute: \(query.prefix(50))...")
            throw DatabaseError.notInitialized
        }

        print("UserDatabaseManagerAsync: Executing: \(query.prefix(100))...")

        var statement: OpaquePointer?

        // Prepare statement
        guard sqlite3_prepare_v2(db, query, -1, &statement, nil) == SQLITE_OK else {
            let errorMessage = String(cString: sqlite3_errmsg(db))
            print("UserDatabaseManagerAsync: Failed to prepare query: \(errorMessage)")
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
            case let value as Date:
                sqlite3_bind_int64(statement, paramIndex, Int64(value.timeIntervalSince1970 * 1000))
            case nil:
                sqlite3_bind_null(statement, paramIndex)
            default:
                print("UserDatabaseManagerAsync: Unknown parameter type: \(String(describing: parameter))")
                throw DatabaseError.invalidParameter
            }
        }

        // Execute
        let result = sqlite3_step(statement)
        // SQLITE_DONE means successful completion, SQLITE_ROW means there are results (for SELECT)
        guard result == SQLITE_DONE || result == SQLITE_ROW else {
            let errorMessage = String(cString: sqlite3_errmsg(db))
            print("UserDatabaseManagerAsync: Failed to execute query: \(query.prefix(100))...")
            print("UserDatabaseManagerAsync: SQLite error: \(errorMessage)")
            print("UserDatabaseManagerAsync: Result code: \(result)")
            throw DatabaseError.executionFailed
        }

        // For SELECT queries with results, consume all rows
        if result == SQLITE_ROW {
            while sqlite3_step(statement) == SQLITE_ROW {
                // Just consume the rows
            }
        }

        print("UserDatabaseManagerAsync: Successfully executed: \(query.prefix(50))...")
    }

    /// Get the last inserted row ID
    func getLastInsertRowId() async -> Int64 {
        guard let db = db else { return 0 }
        return sqlite3_last_insert_rowid(db)
    }

    /// Begin a transaction
    func beginTransaction() async throws {
        try await execute("BEGIN TRANSACTION")
    }

    /// Commit a transaction
    func commit() async throws {
        try await execute("COMMIT")
    }

    /// Rollback a transaction
    func rollback() async throws {
        try await execute("ROLLBACK")
    }

    /// Check if database exists and is valid
    func isDatabaseValid() async -> Bool {
        let fileManager = FileManager.default

        // Check if file exists
        guard fileManager.fileExists(atPath: databasePath) else {
            return false
        }

        // Check file size
        do {
            let attributes = try fileManager.attributesOfItem(atPath: databasePath)
            let fileSize = attributes[.size] as? Int64 ?? 0
            return fileSize >= 1024 // At least 1KB
        } catch {
            return false
        }
    }

    /// Close the database connection
    func close() async {
        if let db = db {
            sqlite3_close_v2(db)
            self.db = nil
        }
        state = .uninitialized
        print("UserDatabaseManagerAsync: Database closed")
    }
}