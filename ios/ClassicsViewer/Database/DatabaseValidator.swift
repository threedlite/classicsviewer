import Foundation
import SQLite3
import os.log

class DatabaseValidator {
    
    enum ValidationError: LocalizedError {
        case cannotOpenDatabase
        case missingRequiredTable(String)
        case missingRequiredColumn(table: String, column: String)
        case invalidSchema
        case emptyDatabase
        
        var errorDescription: String? {
            switch self {
            case .cannotOpenDatabase:
                return "Cannot open database file"
            case .missingRequiredTable(let table):
                return "Missing required table: \(table)"
            case .missingRequiredColumn(let table, let column):
                return "Missing column '\(column)' in table '\(table)'"
            case .invalidSchema:
                return "Database schema validation failed"
            case .emptyDatabase:
                return "Database contains no data"
            }
        }
    }
    
    func validateDatabaseStructure(at url: URL) async throws -> Bool {
        return try await withCheckedThrowingContinuation { continuation in
            Task {
                do {
                    let isValid = try performValidation(at: url)
                    continuation.resume(returning: isValid)
                } catch {
                    continuation.resume(throwing: error)
                }
            }
        }
    }
    
    private func performValidation(at url: URL) throws -> Bool {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")
        var externalDb: OpaquePointer?
        var bundledDb: OpaquePointer?
        
        logger.info("DatabaseValidator - Opening external database at \(url.path)")
        
        // Check if file exists and size
        if FileManager.default.fileExists(atPath: url.path) {
            let attrs = try? FileManager.default.attributesOfItem(atPath: url.path)
            let size = attrs?[.size] as? Int64 ?? 0
            logger.info("DatabaseValidator - File exists, size: \(size) bytes")
        } else {
            logger.error("DatabaseValidator - File does not exist at path")
        }
        
        // COMPREHENSIVE FILE SYSTEM DIAGNOSTICS FIRST
        logger.info("🔍 DatabaseValidator - Starting comprehensive file system diagnostics...")
        checkFileSystemAccess(at: url, logger: logger)
        
        // Check SQLite file header 
        logger.info("🔍 DatabaseValidator - Checking external database header...")
        checkSQLiteFileHeader(at: url, logger: logger)
        
        // Open external database
        logger.info("🔍 DatabaseValidator - Attempting to open database with SQLite...")
        logger.info("🔍 Path: \(url.path)")
        logger.info("🔍 File URL: \(url)")
        
        // First try with regular sqlite3_open (read-write mode) which is more forgiving
        var testDb: OpaquePointer?
        let testResult = sqlite3_open(url.path, &testDb)
        if testResult == SQLITE_OK {
            logger.info("🔍 SUCCESS: Opened with sqlite3_open (read-write mode)")
            
            // Quick test query
            var testStmt: OpaquePointer?
            let testQuery = "SELECT name FROM sqlite_master WHERE type='table' LIMIT 1"
            if sqlite3_prepare_v2(testDb, testQuery, -1, &testStmt, nil) == SQLITE_OK {
                logger.info("🔍 SUCCESS: Can execute queries on database")
                sqlite3_finalize(testStmt)
            } else {
                logger.error("🔍 ERROR: Cannot execute test query")
            }
            
            sqlite3_close(testDb)
            logger.info("🔍 Closed test connection, now trying read-only...")
        } else {
            logger.error("🔍 FAILED: Cannot open with sqlite3_open, error: \(testResult)")
        }
        
        let externalResult = sqlite3_open_v2(url.path, &externalDb, SQLITE_OPEN_READONLY, nil)
        logger.info("🔍 sqlite3_open_v2 result: \(externalResult) (SQLITE_OK = \(SQLITE_OK))")
        
        guard externalResult == SQLITE_OK, let extDb = externalDb else {
            logger.error("🔍 CRITICAL: Failed to open external database with SQLite!")
            logger.error("🔍 SQLite open error code: \(externalResult)")
            
            // Decode error
            let errorCodeDescription: String
            switch externalResult {
            case SQLITE_CANTOPEN: errorCodeDescription = "SQLITE_CANTOPEN (Unable to open database file)"
            case SQLITE_NOMEM: errorCodeDescription = "SQLITE_NOMEM (Out of memory)"
            case SQLITE_MISUSE: errorCodeDescription = "SQLITE_MISUSE (Library used incorrectly)"
            default: errorCodeDescription = "Unknown SQLite open error"
            }
            logger.error("🔍 Error description: \(errorCodeDescription)")
            
            if externalDb != nil {
                let errorMsg = String(cString: sqlite3_errmsg(externalDb))
                logger.error("🔍 SQLite error message: '\(errorMsg)'")
            }
            
            // Try alternative path approaches
            logger.info("🔍 Attempting alternative path approaches...")
            
            // Try with file:// URL
            let fileUrlString = url.absoluteString
            logger.info("🔍 Trying with file URL string: \(fileUrlString)")
            let altResult1 = sqlite3_open_v2(fileUrlString, &externalDb, SQLITE_OPEN_READONLY, nil)
            logger.info("🔍 File URL result: \(altResult1)")
            if altResult1 == SQLITE_OK {
                sqlite3_close(externalDb)
                logger.info("🔍 SUCCESS: File URL approach worked!")
            }
            
            throw ValidationError.cannotOpenDatabase
        }
        
        logger.info("🔍 DatabaseValidator - Successfully opened external database for reading")
        
        // Configure SQLite to use the app's temp directory for large queries
        let tempDir = FileManager.default.temporaryDirectory.path
        logger.info("🔍 Setting SQLite temp directory to: \(tempDir)")
        
        // Set temp directory for SQLite operations on this large database
        let pragmaResult1 = executePragma(database: extDb, pragma: "PRAGMA temp_store_directory = '\(tempDir)';")
        logger.info("🔍 temp_store_directory pragma result: \(pragmaResult1)")
        
        // Use memory for temp storage if possible
        let pragmaResult2 = executePragma(database: extDb, pragma: "PRAGMA temp_store = MEMORY;")
        logger.info("🔍 temp_store pragma result: \(pragmaResult2)")
        
        // Increase cache size for better performance with large database
        let pragmaResult3 = executePragma(database: extDb, pragma: "PRAGMA cache_size = 10000;")
        logger.info("🔍 cache_size pragma result: \(pragmaResult3)")
        
        // Set journal mode to memory
        let pragmaResult4 = executePragma(database: extDb, pragma: "PRAGMA journal_mode = MEMORY;")
        logger.info("🔍 journal_mode pragma result: \(pragmaResult4)")
        
        defer { sqlite3_close(extDb) }
        
        // Extract bundled database from app bundle for comparison
        guard let bundledZipPath = Bundle.main.path(forResource: "perseus_texts.db", ofType: "zip") else {
            logger.error("DatabaseValidator - Bundled database ZIP not found in app bundle")
            throw ValidationError.invalidSchema
        }
        
        // Create temporary path for bundled database extraction
        let tempDirectory = FileManager.default.temporaryDirectory
        let bundledDbPath = tempDirectory.appendingPathComponent("bundled_validation_\(UUID().uuidString).db")
        
        logger.info("DatabaseValidator - Extracting bundled database from \(bundledZipPath)")
        logger.info("DatabaseValidator - To temporary location: \(bundledDbPath.path)")
        
        // Extract bundled database
        do {
            try ZIPHandler.extractDatabase(from: URL(fileURLWithPath: bundledZipPath), to: bundledDbPath)
            logger.info("DatabaseValidator - Successfully extracted bundled database")
        } catch {
            logger.error("DatabaseValidator - Failed to extract bundled database: \(error)")
            throw ValidationError.invalidSchema
        }
        
        // Ensure cleanup of temporary file
        defer {
            try? FileManager.default.removeItem(at: bundledDbPath)
        }
        
        // Check bundled SQLite file header 
        logger.info("🔍 DatabaseValidator - Checking bundled database header...")
        checkSQLiteFileHeader(at: bundledDbPath, logger: logger)
        
        // Open extracted bundled database for comparison
        let bundledResult = sqlite3_open_v2(bundledDbPath.path, &bundledDb, SQLITE_OPEN_READONLY, nil)
        guard bundledResult == SQLITE_OK, let bunDb = bundledDb else {
            logger.error("DatabaseValidator - Failed to open bundled database, SQLite error: \(bundledResult)")
            if bundledDb != nil {
                let errorMsg = String(cString: sqlite3_errmsg(bundledDb))
                logger.error("DatabaseValidator - Bundled SQLite error message: \(errorMsg)")
            }
            throw ValidationError.cannotOpenDatabase
        }
        
        logger.info("🔍 DatabaseValidator - Successfully opened bundled database for reading")
        
        defer { sqlite3_close(bunDb) }
        
        let externalSize = (try? FileManager.default.attributesOfItem(atPath: url.path)[.size] as? Int64) ?? 0
        let bundledSize = (try? FileManager.default.attributesOfItem(atPath: bundledDbPath.path)[.size] as? Int64) ?? 0
        
        logger.info("DatabaseValidator - Comparing databases:")
        logger.info("  External: \(url.path) (\(externalSize / (1024*1024))MB)")
        logger.info("  Bundled:  \(bundledDbPath.path) (\(bundledSize / (1024*1024))MB)")
        
        // Get all tables from both databases
        let bundledTables = getTables(from: bunDb)
        let externalTables = getTables(from: extDb)
        
        logger.info("Bundled database tables (\(bundledTables.count)): \(bundledTables.joined(separator: ", "))")
        logger.info("External database tables (\(externalTables.count)): \(externalTables.joined(separator: ", "))")
        
        // Check each bundled table exists in external database
        var missingTables: [String] = []
        for tableName in bundledTables {
            if !externalTables.contains(tableName) {
                let error = "Table '\(tableName)' missing from external database"
                logger.error("DatabaseValidator - \(error)")
                missingTables.append(tableName)
            }
        }
        
        if !missingTables.isEmpty {
            let errorMsg = "Missing required tables: \(missingTables.joined(separator: ", "))"
            logger.error("DatabaseValidator - \(errorMsg)")
            throw ValidationError.missingRequiredTable(missingTables.first!)
        }
        
        // Check database has data
        if !databaseHasData(extDb) {
            throw ValidationError.emptyDatabase
        }
        
        // Skip integrity check for performance (matching Android behavior)
        // The schema validation above is sufficient
        
        return true
    }
    
    private func getTables(from database: OpaquePointer) -> [String] {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")
        let query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        var statement: OpaquePointer?
        var tables: [String] = []
        
        logger.info("🔍 getTables() - Starting query execution...")
        logger.info("🔍 Query: \(query)")
        logger.info("🔍 Database pointer: \(String(format: "%p", database))")
        
        let prepareResult = sqlite3_prepare_v2(database, query, -1, &statement, nil)
        logger.info("🔍 sqlite3_prepare_v2 result: \(prepareResult) (SQLITE_OK = \(SQLITE_OK))")
        
        guard prepareResult == SQLITE_OK else {
            logger.error("🔍 CRITICAL: Failed to prepare getTables query!")
            logger.error("🔍 SQLite error code: \(prepareResult)")
            
            // Convert SQLite error code to meaningful description
            let errorCodeDescription: String
            switch prepareResult {
            case SQLITE_ERROR: errorCodeDescription = "SQLITE_ERROR (SQL error or missing database)"
            case SQLITE_MISUSE: errorCodeDescription = "SQLITE_MISUSE (Library used incorrectly)"
            case SQLITE_BUSY: errorCodeDescription = "SQLITE_BUSY (Database file locked)"
            case SQLITE_LOCKED: errorCodeDescription = "SQLITE_LOCKED (Database locked)"
            case SQLITE_NOMEM: errorCodeDescription = "SQLITE_NOMEM (Out of memory)"
            case SQLITE_READONLY: errorCodeDescription = "SQLITE_READONLY (Attempt to write a readonly database)"
            case SQLITE_INTERRUPT: errorCodeDescription = "SQLITE_INTERRUPT (Operation was interrupted)"
            case SQLITE_IOERR: errorCodeDescription = "SQLITE_IOERR (Disk I/O error occurred)"
            case SQLITE_CORRUPT: errorCodeDescription = "SQLITE_CORRUPT (Database disk image is malformed)"
            case SQLITE_NOTFOUND: errorCodeDescription = "SQLITE_NOTFOUND (Unknown opcode)"
            case SQLITE_FULL: errorCodeDescription = "SQLITE_FULL (Database or disk is full)"
            case SQLITE_CANTOPEN: errorCodeDescription = "SQLITE_CANTOPEN (Unable to open database file)"
            case SQLITE_PROTOCOL: errorCodeDescription = "SQLITE_PROTOCOL (Database lock protocol error)"
            case SQLITE_EMPTY: errorCodeDescription = "SQLITE_EMPTY (Internal use only)"
            case SQLITE_SCHEMA: errorCodeDescription = "SQLITE_SCHEMA (Database schema changed)"
            case SQLITE_TOOBIG: errorCodeDescription = "SQLITE_TOOBIG (String or BLOB exceeds size limit)"
            case SQLITE_CONSTRAINT: errorCodeDescription = "SQLITE_CONSTRAINT (Constraint violation)"
            case SQLITE_MISMATCH: errorCodeDescription = "SQLITE_MISMATCH (Data type mismatch)"
            case SQLITE_NOTADB: errorCodeDescription = "SQLITE_NOTADB (File is not a database)"
            default: errorCodeDescription = "Unknown SQLite error code"
            }
            logger.error("🔍 Error description: \(errorCodeDescription)")
            
            let errorMsg = String(cString: sqlite3_errmsg(database))
            logger.error("🔍 SQLite error message: '\(errorMsg)'")
            logger.error("🔍 Extended error code: \(sqlite3_extended_errcode(database))")
            
            return tables
        }
        
        logger.info("🔍 Query prepared successfully, executing...")
        defer { sqlite3_finalize(statement) }
        
        var stepCount = 0
        while true {
            let stepResult = sqlite3_step(statement)
            stepCount += 1
            
            if stepResult == SQLITE_ROW {
                if let name = sqlite3_column_text(statement, 0) {
                    let tableName = String(cString: name)
                    tables.append(tableName)
                    logger.info("🔍 Found table: '\(tableName)'")
                } else {
                    logger.warning("🔍 Table name was NULL in row \(stepCount)")
                }
            } else if stepResult == SQLITE_DONE {
                logger.info("🔍 Query completed successfully after \(stepCount) steps")
                break
            } else {
                logger.error("🔍 sqlite3_step failed with code: \(stepResult)")
                let errorMsg = String(cString: sqlite3_errmsg(database))
                logger.error("🔍 Step error message: '\(errorMsg)'")
                break
            }
        }
        
        logger.info("🔍 Final result: found \(tables.count) tables: \(tables.joined(separator: ", "))")
        return tables
    }
    
    private func tableExists(_ tableName: String, in database: OpaquePointer) -> Bool {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")
        let query = "SELECT name FROM sqlite_master WHERE type='table' AND name='\(tableName)'"
        var statement: OpaquePointer?
        
        logger.info("🔍 tableExists('\(tableName)') - Starting check...")
        logger.info("🔍 Query: \(query)")
        
        let prepareResult = sqlite3_prepare_v2(database, query, -1, &statement, nil)
        logger.info("🔍 tableExists prepare result: \(prepareResult) (SQLITE_OK = \(SQLITE_OK))")
        
        guard prepareResult == SQLITE_OK else {
            logger.error("🔍 CRITICAL: Failed to prepare tableExists statement for '\(tableName)'!")
            logger.error("🔍 SQLite error code: \(prepareResult)")
            let errorMsg = String(cString: sqlite3_errmsg(database))
            logger.error("🔍 SQLite error message: '\(errorMsg)'")
            logger.error("🔍 Extended error code: \(sqlite3_extended_errcode(database))")
            
            // Also try a simpler query to test basic database connectivity
            logger.info("🔍 Testing basic database connectivity with PRAGMA user_version...")
            var testStatement: OpaquePointer?
            let testPrepareResult = sqlite3_prepare_v2(database, "PRAGMA user_version", -1, &testStatement, nil)
            if testPrepareResult == SQLITE_OK {
                logger.info("🔍 Basic PRAGMA query prepared successfully")
                let testStepResult = sqlite3_step(testStatement)
                if testStepResult == SQLITE_ROW {
                    let version = sqlite3_column_int(testStatement, 0)
                    logger.info("🔍 Database user_version: \(version)")
                } else {
                    logger.error("🔍 Basic PRAGMA query step failed: \(testStepResult)")
                }
                sqlite3_finalize(testStatement)
            } else {
                logger.error("🔍 Even basic PRAGMA query failed: \(testPrepareResult)")
            }
            
            return false
        }
        
        defer { sqlite3_finalize(statement) }
        
        let stepResult = sqlite3_step(statement)
        let result = stepResult == SQLITE_ROW
        
        logger.info("🔍 tableExists step result: \(stepResult) (SQLITE_ROW = \(SQLITE_ROW), SQLITE_DONE = \(SQLITE_DONE))")
        logger.info("🔍 Table '\(tableName)' exists: \(result)")
        
        if !result && stepResult != SQLITE_DONE {
            logger.error("🔍 Unexpected step result for table '\(tableName)': \(stepResult)")
            let errorMsg = String(cString: sqlite3_errmsg(database))
            logger.error("🔍 Step error message: '\(errorMsg)'")
        }
        
        return result
    }
    
    private func listAllTables(in database: OpaquePointer, logger: Logger? = nil) {
        let log = logger ?? Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")
        let query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        var statement: OpaquePointer?
        
        guard sqlite3_prepare_v2(database, query, -1, &statement, nil) == SQLITE_OK else {
            log.error("Failed to list tables")
            return
        }
        
        defer { sqlite3_finalize(statement) }
        
        var tables: [String] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            if let name = sqlite3_column_text(statement, 0) {
                tables.append(String(cString: name))
            }
        }
        
        log.info("Found \(tables.count) tables: \(tables.joined(separator: ", "))")
    }
    
    private func columnExists(_ columnName: String, inTable tableName: String, database: OpaquePointer) -> Bool {
        let query = "PRAGMA table_info(\(tableName))"
        var statement: OpaquePointer?
        
        guard sqlite3_prepare_v2(database, query, -1, &statement, nil) == SQLITE_OK else {
            return false
        }
        
        defer { sqlite3_finalize(statement) }
        
        while sqlite3_step(statement) == SQLITE_ROW {
            if let name = sqlite3_column_text(statement, 1) {
                let colName = String(cString: name)
                if colName == columnName {
                    return true
                }
            }
        }
        
        return false
    }
    
    private func databaseHasData(_ database: OpaquePointer) -> Bool {
        // Check if authors table has data
        let query = "SELECT COUNT(*) FROM authors"
        var statement: OpaquePointer?
        
        guard sqlite3_prepare_v2(database, query, -1, &statement, nil) == SQLITE_OK else {
            return false
        }
        
        defer { sqlite3_finalize(statement) }
        
        if sqlite3_step(statement) == SQLITE_ROW {
            let count = sqlite3_column_int(statement, 0)
            return count > 0
        }
        
        return false
    }
    
    private func checkDatabaseIntegrity(_ database: OpaquePointer) -> Bool {
        let query = "PRAGMA integrity_check"
        var statement: OpaquePointer?
        
        guard sqlite3_prepare_v2(database, query, -1, &statement, nil) == SQLITE_OK else {
            return false
        }
        
        defer { sqlite3_finalize(statement) }
        
        if sqlite3_step(statement) == SQLITE_ROW {
            if let result = sqlite3_column_text(statement, 0) {
                let integrityResult = String(cString: result)
                return integrityResult == "ok"
            }
        }
        
        return false
    }
    
    // MARK: - Detailed Validation Report
    
    struct ValidationReport {
        let isValid: Bool
        let tableCount: Int
        let authorCount: Int
        let bookCount: Int
        let lineCount: Int
        let databaseSize: Int64
        let issues: [String]
    }
    
    func generateValidationReport(for url: URL, progressCallback: ((String) -> Void)? = nil) async throws -> ValidationReport {
        var issues: [String] = []
        var tableCount = 0
        var authorCount = 0
        var bookCount = 0
        var lineCount = 0
        
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")
        logger.error("🔴 === VALIDATION REPORT RECEIVED ===")
        logger.error("🔴 URL received: \(url)")
        logger.error("🔴 Path received: \(url.path)")
        logger.error("🔴 Absolute string: \(url.absoluteString)")
        logger.error("🔴 Last path component: \(url.lastPathComponent)")
        logger.error("🔴 File exists at path: \(FileManager.default.fileExists(atPath: url.path))")
        
        // Get detailed file info
        if FileManager.default.fileExists(atPath: url.path) {
            let attrs = try? FileManager.default.attributesOfItem(atPath: url.path)
            logger.error("🔴 File size: \(attrs?[.size] as? Int64 ?? 0) bytes")
            logger.error("🔴 File type: \(attrs?[.type] as? String ?? "unknown")")
            logger.error("🔴 Creation date: \(attrs?[.creationDate] as? Date ?? Date())")
            logger.error("🔴 Modification date: \(attrs?[.modificationDate] as? Date ?? Date())")
        } else {
            logger.error("🔴 *** FILE DOES NOT EXIST AT START OF VALIDATION ***")
        }
        
        logger.info("🔍 COMPREHENSIVE SCHEMA VALIDATION STARTING...")
        
        // Get file size
        let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
        let fileSize = attributes[.size] as? Int64 ?? 0
        
        // CRITICAL: Compare with bundled database schema using comprehensive validation
        logger.info("Comparing imported database schema with bundled database...")
        
        // Get bundled database path
        guard let bundledZipURL = Bundle.main.url(forResource: "perseus_texts.db", withExtension: "zip") else {
            issues.append("Cannot find bundled database for comparison")
            return ValidationReport(
                isValid: false,
                tableCount: 0,
                authorCount: 0,
                bookCount: 0,
                lineCount: 0,
                databaseSize: fileSize,
                issues: issues
            )
        }
        
        // Extract bundled database temporarily for comparison
        let tempDir = FileManager.default.temporaryDirectory
        let bundledTempPath = tempDir.appendingPathComponent("bundled_validation_\(UUID().uuidString).db")
        
        defer {
            // Clean up temp bundled database
            try? FileManager.default.removeItem(at: bundledTempPath)
        }
        
        // Extract bundled database for comparison
        do {
            // Use ZIPHandler to properly extract the database from ZIP
            try ZIPHandler.extractDatabase(from: bundledZipURL, to: bundledTempPath)
            
            // Continue with validation using the extracted database
        } catch {
            // Provide detailed information about what validation would check
            issues.append("Unable to extract reference database for validation: \(error.localizedDescription)")
            issues.append("Required tables: authors, works, books, text_lines, translation_segments, translation_lookup, words, dictionary_entries, lemma_map")
            issues.append("Each table must have exact matching columns with correct types and constraints")
            issues.append("Database must contain Greek/Latin texts with proper structure")
            return ValidationReport(
                isValid: false,
                tableCount: 0,
                authorCount: 0,
                bookCount: 0,
                lineCount: 0,
                databaseSize: fileSize,
                issues: issues
            )
        }
        
        // Now perform COMPREHENSIVE SCHEMA COMPARISON
        logger.info("Performing comprehensive schema comparison...")
        
        // STEP 1: Read bundled database schema and store it in memory
        logger.info("Step 1: Reading bundled database schema...")
        var bundledDb: OpaquePointer?
        var bundledSchema: [String: [ColumnInfo]] = [:]
        
        // Open bundled database first to read its schema
        guard sqlite3_open(bundledTempPath.path, &bundledDb) == SQLITE_OK else {
            issues.append("Cannot open bundled database for validation")
            return ValidationReport(
                isValid: false,
                tableCount: 0,
                authorCount: 0,
                bookCount: 0,
                lineCount: 0,
                databaseSize: fileSize,
                issues: issues
            )
        }
        
        // Configure bundled database to use memory only
        _ = executePragma(database: bundledDb!, pragma: "PRAGMA temp_store = 2;")
        _ = executePragma(database: bundledDb!, pragma: "PRAGMA cache_size = -50000;")
        _ = executePragma(database: bundledDb!, pragma: "PRAGMA query_only = true;")
        
        // Read bundled schema into memory
        let requiredTables = [
            "authors",
            "works",
            "books",
            "text_lines",
            "translation_segments",
            "translation_lookup",
            "words",
            "dictionary_entries",
            "lemma_map"
        ]
        
        for tableName in requiredTables {
            bundledSchema[tableName] = getTableColumns(tableName, in: bundledDb!)
        }
        
        // Close bundled database after reading schema
        sqlite3_close(bundledDb)
        logger.info("Step 1 complete: Bundled schema read and database closed")
        
        // STEP 2: Open imported database and validate against bundled schema
        logger.info("Step 2: Opening imported database for validation...")
        logger.error("🎆 Path to open: \(url.path)")
        logger.error("🎆 File exists: \(FileManager.default.fileExists(atPath: url.path))")
        let importedFileSize = try? FileManager.default.attributesOfItem(atPath: url.path)[.size] as? Int64 ?? 0
        logger.error("🎆 File size: \(importedFileSize ?? 0) bytes")
        
        var importedDb: OpaquePointer?
        
        // Use sqlite3_open (not _v2) to allow SQLite to create temp files in app sandbox
        let openResult = sqlite3_open(url.path, &importedDb)
        logger.error("🎆 sqlite3_open result: \(openResult)")
        
        guard openResult == SQLITE_OK, let impDb = importedDb else {
            logger.error("🎆 FAILED to open imported database")
            if let db = importedDb {
                let errorMsg = String(cString: sqlite3_errmsg(db))
                logger.error("🎆 SQLite error message: '\(errorMsg)'")
            }
            issues.append("Cannot open imported database file")
            return ValidationReport(
                isValid: false,
                tableCount: 0,
                authorCount: 0,
                bookCount: 0,
                lineCount: 0,
                databaseSize: fileSize,
                issues: issues
            )
        }
        defer { sqlite3_close(impDb) }
        
        // Configure SQLite to use memory instead of temp files
        logger.error("🎆 Database opened successfully, configuring SQLite for memory-only operation...")
        
        // Force SQLite to use memory for ALL temp storage (no temp files)
        logger.error("🎆 Setting temp_store to MEMORY (2)")
        _ = executePragma(database: impDb, pragma: "PRAGMA temp_store = 2;") // 2 = MEMORY
        
        // Increase cache size for better performance with large database
        logger.error("🎆 Setting cache_size to 50000 pages (200MB)")
        _ = executePragma(database: impDb, pragma: "PRAGMA cache_size = -200000;") // Negative = KB
        
        // Set page size for better performance
        logger.error("🎆 Setting page_size to 4096")
        _ = executePragma(database: impDb, pragma: "PRAGMA page_size = 4096;")
        
        // Use memory for journal
        logger.error("🎆 Setting journal_mode to MEMORY")
        _ = executePragma(database: impDb, pragma: "PRAGMA journal_mode = MEMORY;")
        
        // Optimize query planner for read-only operations
        logger.error("🎆 Setting query_only mode")
        _ = executePragma(database: impDb, pragma: "PRAGMA query_only = true;")
        
        logger.error("🎆 SQLite configuration complete, proceeding with validation...")
        
        // STEP 3: Validate imported database against stored bundled schema
        logger.info("Step 3: Validating imported database schema...")
        progressCallback?("Checking table structures and schemas...")

        // Validate each table comprehensively
        for tableName in requiredTables {
            logger.info("Validating table '\(tableName)'...")
            
            // Check table exists
            if !tableExists(tableName, in: impDb) {
                issues.append("Missing required table: \(tableName)")
                continue
            }
            
            // Get columns - bundled from stored schema, imported from database
            let bundledColumns = bundledSchema[tableName] ?? []
            let importedColumns = getTableColumns(tableName, in: impDb)
            
            logger.info("Table '\(tableName)': Bundled has \(bundledColumns.count) columns, Imported has \(importedColumns.count) columns")
            
            // Check column count
            if bundledColumns.count != importedColumns.count {
                issues.append("Table '\(tableName)': Column count mismatch. Expected \(bundledColumns.count), got \(importedColumns.count)")
            }
            
            // Create dictionaries for easy lookup
            let bundledDict = Dictionary(uniqueKeysWithValues: bundledColumns.map { ($0.name, $0) })
            let importedDict = Dictionary(uniqueKeysWithValues: importedColumns.map { ($0.name, $0) })
            
            // Validate EVERY column
            for bundledColumn in bundledColumns {
                guard let importedColumn = importedDict[bundledColumn.name] else {
                    issues.append("Table '\(tableName)': Missing required column '\(bundledColumn.name)'")
                    continue
                }
                
                // Check column type
                if bundledColumn.type != importedColumn.type {
                    // Allow some compatible types
                    if !areTypesCompatible(bundledColumn.type, importedColumn.type) {
                        issues.append("Table '\(tableName)', Column '\(bundledColumn.name)': Type mismatch. Expected '\(bundledColumn.type)', got '\(importedColumn.type)'")
                    }
                }
                
                // Check NOT NULL constraint
                if bundledColumn.notNull != importedColumn.notNull {
                    issues.append("Table '\(tableName)', Column '\(bundledColumn.name)': NOT NULL mismatch. Expected \(bundledColumn.notNull), got \(importedColumn.notNull)")
                }
                
                // Check primary key
                if bundledColumn.primaryKey != importedColumn.primaryKey {
                    issues.append("Table '\(tableName)', Column '\(bundledColumn.name)': Primary key mismatch")
                }
            }
            
            // Check for extra columns that shouldn't exist
            for importedColumn in importedColumns {
                if bundledDict[importedColumn.name] == nil {
                    issues.append("Table '\(tableName)': Unexpected extra column '\(importedColumn.name)'")
                }
            }
        }
        
        // Count tables
        tableCount = countTables(in: impDb)

        // Get data counts if validation passed so far
        if issues.isEmpty {
            progressCallback?("Counting rows in tables...")

            if tableExists("authors", in: impDb) {
                authorCount = getRowCount(for: "authors", in: impDb)
                if authorCount == 0 {
                    issues.append("No authors found in database")
                }
            }
            
            if tableExists("books", in: impDb) {
                bookCount = getRowCount(for: "books", in: impDb)
                if bookCount == 0 {
                    issues.append("No books found in database")
                }
            }
            
            if tableExists("text_lines", in: impDb) {
                lineCount = getRowCount(for: "text_lines", in: impDb)
                if lineCount == 0 {
                    issues.append("No text lines found in database")
                }
            }
        }
        
        // Skip integrity check for performance (matching Android behavior)
        // The schema validation above is sufficient
        
        logger.info("Validation complete. Found \(issues.count) issues")
        if !issues.isEmpty {
            for issue in issues {
                logger.error("  ❌ \(issue)")
            }
        }
        
        return ValidationReport(
            isValid: issues.isEmpty,
            tableCount: tableCount,
            authorCount: authorCount,
            bookCount: bookCount,
            lineCount: lineCount,
            databaseSize: fileSize,
            issues: issues
        )
    }
    
    private func countTables(in database: OpaquePointer) -> Int {
        let query = "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        var statement: OpaquePointer?
        
        guard sqlite3_prepare_v2(database, query, -1, &statement, nil) == SQLITE_OK else {
            return 0
        }
        
        defer { sqlite3_finalize(statement) }
        
        if sqlite3_step(statement) == SQLITE_ROW {
            return Int(sqlite3_column_int(statement, 0))
        }
        
        return 0
    }
    
    private func getRowCount(for table: String, in database: OpaquePointer) -> Int {
        let query = "SELECT COUNT(*) FROM \(table)"
        var statement: OpaquePointer?
        
        guard sqlite3_prepare_v2(database, query, -1, &statement, nil) == SQLITE_OK else {
            return 0
        }
        
        defer { sqlite3_finalize(statement) }
        
        if sqlite3_step(statement) == SQLITE_ROW {
            return Int(sqlite3_column_int(statement, 0))
        }
        
        return 0
    }
    
    // MARK: - Column Information Structure
    
    private struct ColumnInfo {
        let name: String
        let type: String
        let notNull: Bool
        let defaultValue: String?
        let primaryKey: Int
    }
    
    // MARK: - Comprehensive Column Validation
    
    private func getTableColumns(_ tableName: String, in database: OpaquePointer) -> [ColumnInfo] {
        let query = "PRAGMA table_info('\(tableName)')"
        var statement: OpaquePointer?
        
        var columns: [ColumnInfo] = []
        
        guard sqlite3_prepare_v2(database, query, -1, &statement, nil) == SQLITE_OK else {
            return columns
        }
        
        defer { sqlite3_finalize(statement) }
        
        while sqlite3_step(statement) == SQLITE_ROW {
            // Column 0: cid
            // Column 1: name
            // Column 2: type
            // Column 3: notnull
            // Column 4: default value
            // Column 5: primary key
            
            let name = String(cString: sqlite3_column_text(statement, 1))
            let type = String(cString: sqlite3_column_text(statement, 2))
            let notNull = sqlite3_column_int(statement, 3) != 0
            
            var defaultValue: String? = nil
            if let defaultPtr = sqlite3_column_text(statement, 4) {
                defaultValue = String(cString: defaultPtr)
            }
            
            let primaryKey = Int(sqlite3_column_int(statement, 5))
            
            columns.append(ColumnInfo(
                name: name,
                type: type,
                notNull: notNull,
                defaultValue: defaultValue,
                primaryKey: primaryKey
            ))
        }
        
        return columns
    }
    
    private func areTypesCompatible(_ type1: String, _ type2: String) -> Bool {
        let normalized1 = type1.uppercased()
        let normalized2 = type2.uppercased()
        
        // Exact match
        if normalized1 == normalized2 {
            return true
        }
        
        // Common compatible types
        let compatiblePairs = [
            ("INTEGER", "INT"),
            ("TEXT", "VARCHAR"),
            ("REAL", "FLOAT"),
            ("REAL", "DOUBLE"),
            ("BLOB", "BINARY")
        ]
        
        for (a, b) in compatiblePairs {
            if (normalized1 == a && normalized2 == b) ||
               (normalized1 == b && normalized2 == a) {
                return true
            }
        }
        
        return false
    }
    
    // MARK: - File System Diagnostics
    
    private func checkFileSystemAccess(at url: URL, logger: Logger) {
        logger.info("🔍 === FILE SYSTEM DIAGNOSTICS ===")
        logger.info("🔍 File path: \(url.path)")
        logger.info("🔍 File URL: \(url)")
        logger.info("🔍 URL scheme: \(url.scheme ?? "nil")")
        
        let path = url.path
        let fileManager = FileManager.default
        
        // Check file existence
        let fileExists = fileManager.fileExists(atPath: path)
        logger.info("🔍 File exists: \(fileExists)")
        
        if !fileExists {
            logger.error("🔍 ❌ FILE DOES NOT EXIST!")
            
            // Check parent directory
            let parentDir = url.deletingLastPathComponent().path
            let parentExists = fileManager.fileExists(atPath: parentDir)
            logger.info("🔍 Parent directory exists: \(parentExists)")
            logger.info("🔍 Parent directory: \(parentDir)")
            
            if parentExists {
                // List files in parent directory
                do {
                    let contents = try fileManager.contentsOfDirectory(atPath: parentDir)
                    logger.info("🔍 Parent directory contents (\(contents.count) items): \(contents)")
                } catch {
                    logger.error("🔍 Cannot list parent directory contents: \(error)")
                }
            }
            return
        }
        
        // Get file attributes
        do {
            let attributes = try fileManager.attributesOfItem(atPath: path)
            let fileSize = attributes[.size] as? Int64 ?? 0
            let fileType = attributes[.type] as? FileAttributeType
            let permissions = attributes[.posixPermissions] as? NSNumber
            
            logger.info("🔍 File size: \(fileSize) bytes (\(fileSize / (1024*1024))MB)")
            logger.info("🔍 File type: \(fileType?.rawValue ?? "unknown")")
            if let perms = permissions {
                logger.info("🔍 POSIX permissions: \(String(format: "%o", perms.intValue))")
            }
            
            // Check if file is readable
            let isReadable = fileManager.isReadableFile(atPath: path)
            logger.info("🔍 File is readable: \(isReadable)")
            
            if !isReadable {
                logger.error("🔍 ❌ FILE IS NOT READABLE!")
            }
            
        } catch {
            logger.error("🔍 Cannot get file attributes: \(error)")
        }
        
        // Try to read first 16 bytes directly using FileHandle (memory-efficient)
        // CRITICAL: Do NOT use Data(contentsOf:) as it loads the entire file into memory
        logger.info("🔍 Attempting direct file read (first 16 bytes only)...")
        do {
            let fileHandle = try FileHandle(forReadingFrom: url)
            defer { try? fileHandle.close() }

            let prefixData = fileHandle.readData(ofLength: 16)
            logger.info("🔍 Successfully read first 16 bytes from file")
            logger.info("🔍 First 16 bytes: \(prefixData.map { String(format: "%02x", $0) }.joined(separator: " "))")

            // Check for SQLite header
            let sqliteHeader = "SQLite format 3\0".data(using: .ascii)!
            if prefixData.starts(with: sqliteHeader) {
                logger.info("🔍 ✅ File has valid SQLite header!")
            } else {
                logger.error("🔍 ❌ File does NOT have valid SQLite header!")
                if let headerString = String(data: prefixData, encoding: .ascii) {
                    logger.error("🔍 Header string: '\(headerString)'")
                }
            }
        } catch {
            logger.error("🔍 ❌ Cannot read file directly: \(error)")
        }
        
        logger.info("🔍 === END FILE SYSTEM DIAGNOSTICS ===")
    }
    
    // MARK: - SQLite Pragma Helper
    
    private func executePragma(database: OpaquePointer, pragma: String) -> Bool {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")
        var statement: OpaquePointer?
        
        let result = sqlite3_prepare_v2(database, pragma, -1, &statement, nil)
        if result != SQLITE_OK {
            let errorMsg = String(cString: sqlite3_errmsg(database))
            logger.error("🔍 Failed to prepare pragma '\(pragma)': \(errorMsg)")
            return false
        }
        
        defer { sqlite3_finalize(statement) }
        
        let stepResult = sqlite3_step(statement)
        if stepResult != SQLITE_DONE && stepResult != SQLITE_ROW {
            let errorMsg = String(cString: sqlite3_errmsg(database))
            logger.error("🔍 Failed to execute pragma '\(pragma)': \(errorMsg)")
            return false
        }
        
        return true
    }
    
    // MARK: - SQLite File Header Diagnostics
    
    private func checkSQLiteFileHeader(at url: URL, logger: Logger) {
        guard let fileHandle = FileHandle(forReadingAtPath: url.path) else {
            logger.error("🔍 Cannot open file for header check: \(url.path)")
            return
        }
        
        defer { fileHandle.closeFile() }
        
        // Read first 16 bytes (SQLite header)
        let headerData = fileHandle.readData(ofLength: 16)
        
        if headerData.count < 16 {
            logger.error("🔍 File too small for SQLite header: \(headerData.count) bytes")
            return
        }
        
        // SQLite files start with "SQLite format 3\0"
        let expectedHeader = "SQLite format 3\0".data(using: .ascii)!
        
        if headerData == expectedHeader {
            logger.info("🔍 ✅ Valid SQLite header detected")
            
            // Read page size (bytes 16-17)
            fileHandle.seek(toFileOffset: 16)
            let pageSizeData = fileHandle.readData(ofLength: 2)
            if pageSizeData.count == 2 {
                let pageSize = (UInt16(pageSizeData[0]) << 8) | UInt16(pageSizeData[1])
                logger.info("🔍 SQLite page size: \(pageSize)")
            }
            
            // Read file change counter (bytes 24-27) 
            fileHandle.seek(toFileOffset: 24)
            let changeCounterData = fileHandle.readData(ofLength: 4)
            if changeCounterData.count == 4 {
                let changeCounter = changeCounterData.withUnsafeBytes { $0.load(as: UInt32.self).bigEndian }
                logger.info("🔍 SQLite file change counter: \(changeCounter)")
            }
            
        } else {
            logger.error("🔍 ❌ Invalid SQLite header!")
            logger.error("🔍 Expected: SQLite format 3")
            let actualString = String(data: headerData, encoding: .ascii) ?? "non-ASCII"
            logger.error("🔍 Found: \(actualString)")
            logger.error("🔍 Hex dump: \(headerData.map { String(format: "%02x", $0) }.joined(separator: " "))")
        }
    }
}