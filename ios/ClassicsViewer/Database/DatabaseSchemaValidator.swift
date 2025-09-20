import Foundation
import SQLite3

/// Comprehensive database schema validator that validates EVERY table and EVERY field
class DatabaseSchemaValidator {
    static let shared = DatabaseSchemaValidator()
    
    private init() {}
    
    // MARK: - Expected Tables
    
    /// All tables that MUST exist in the database
    private let requiredTables = [
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
    
    // MARK: - Schema Structures
    
    struct TableSchema {
        let name: String
        let columns: [ColumnSchema]
        let indexes: [IndexSchema]
        let primaryKeys: Set<String>
        let foreignKeys: [ForeignKeySchema]
    }
    
    struct ColumnSchema: Equatable {
        let cid: Int
        let name: String
        let type: String
        let notNull: Bool
        let defaultValue: String?
        let primaryKey: Int
        
        static func == (lhs: ColumnSchema, rhs: ColumnSchema) -> Bool {
            return lhs.name == rhs.name &&
                   lhs.type == rhs.type &&
                   lhs.notNull == rhs.notNull &&
                   lhs.defaultValue == rhs.defaultValue &&
                   lhs.primaryKey == rhs.primaryKey
        }
    }
    
    struct IndexSchema: Equatable {
        let name: String
        let tableName: String
        let columns: [String]
        let isUnique: Bool
    }
    
    struct ForeignKeySchema: Equatable {
        let id: Int
        let fromColumn: String
        let toTable: String
        let toColumn: String
        let onUpdate: String
        let onDelete: String
    }
    
    struct ValidationResult {
        let isValid: Bool
        let errors: [String]
        let warnings: [String]
    }
    
    // MARK: - Main Validation Method
    
    /// Validates that the extracted database has ALL required tables and fields
    func validateDatabaseSchema() async throws -> ValidationResult {
        print("🔍 Starting COMPREHENSIVE database schema validation...")
        
        var errors: [String] = []
        var warnings: [String] = []
        
        let extractedDbPath = getExtractedDatabasePath()
        
        // First, check if database exists
        if !FileManager.default.fileExists(atPath: extractedDbPath) {
            throw ValidationError.databaseNotFound("Extracted database not found at \(extractedDbPath)")
        }
        
        // Open the database
        var db: OpaquePointer?
        guard sqlite3_open_v2(extractedDbPath, &db, SQLITE_OPEN_READONLY, nil) == SQLITE_OK else {
            throw ValidationError.cannotOpenDatabase(extractedDbPath)
        }
        defer { sqlite3_close(db) }
        
        print("📊 Validating ALL required tables and fields...")
        
        // 1. Validate all required tables exist
        let tableValidation = try validateRequiredTables(db: db)
        errors.append(contentsOf: tableValidation.errors)
        warnings.append(contentsOf: tableValidation.warnings)
        
        // 2. Validate data integrity and counts
        let dataValidation = try validateDataIntegrity(db: db)
        errors.append(contentsOf: dataValidation.errors)
        warnings.append(contentsOf: dataValidation.warnings)
        
        // 3. Validate essential indexes exist
        let indexValidation = try validateCriticalIndexes(db: db)
        errors.append(contentsOf: indexValidation.errors)
        warnings.append(contentsOf: indexValidation.warnings)
        
        let isValid = errors.isEmpty
        
        if isValid {
            print("✅ Database schema validation PASSED! All \(requiredTables.count) tables validated.")
        } else {
            print("❌ Database schema validation FAILED with \(errors.count) errors:")
            for error in errors {
                print("  ❌ \(error)")
            }
        }
        
        if !warnings.isEmpty {
            print("⚠️ Database schema validation warnings (\(warnings.count)):")
            for warning in warnings {
                print("  ⚠️ \(warning)")
            }
        }
        
        return ValidationResult(isValid: isValid, errors: errors, warnings: warnings)
    }
    
    // MARK: - Table Validation
    
    private func validateRequiredTables(db: OpaquePointer?) throws -> (errors: [String], warnings: [String]) {
        var errors: [String] = []
        let warnings: [String] = []
        
        print("🔍 Checking all required tables...")
        
        // Get all table names
        let actualTables = try getTableNames(db: db)
        let actualTableSet = Set(actualTables)
        
        // Check for missing required tables
        for requiredTable in requiredTables {
            if !actualTableSet.contains(requiredTable) {
                errors.append("CRITICAL: Required table '\(requiredTable)' is missing")
                continue
            }
            
            // Validate each table's schema
            let tableErrors = try validateTableSchema(tableName: requiredTable, db: db)
            errors.append(contentsOf: tableErrors)
        }
        
        print("📋 Found \(actualTables.count) tables, \(requiredTables.count) required")
        
        return (errors, warnings)
    }
    
    private func validateTableSchema(tableName: String, db: OpaquePointer?) throws -> [String] {
        var errors: [String] = []
        
        print("🔍 Validating table '\(tableName)'...")
        
        switch tableName {
        case "authors":
            errors.append(contentsOf: try validateAuthorsTable(db: db))
        case "works":
            errors.append(contentsOf: try validateWorksTable(db: db))
        case "books":
            errors.append(contentsOf: try validateBooksTable(db: db))
        case "text_lines":
            errors.append(contentsOf: try validateTextLinesTable(db: db))
        case "translation_segments":
            errors.append(contentsOf: try validateTranslationSegmentsTable(db: db))
        case "translation_lookup":
            errors.append(contentsOf: try validateTranslationLookupTable(db: db))
        case "words":
            errors.append(contentsOf: try validateWordsTable(db: db))
        case "dictionary_entries":
            errors.append(contentsOf: try validateDictionaryEntriesTable(db: db))
        case "lemma_map":
            errors.append(contentsOf: try validateLemmaMapTable(db: db))
        default:
            break // Unknown table, not critical
        }
        
        return errors
    }
    
    // MARK: - Individual Table Validators
    
    private func validateAuthorsTable(db: OpaquePointer?) throws -> [String] {
        let requiredColumns = [
            ("id", "TEXT", true, true),      // name, type, notNull, isPrimaryKey
            ("name", "TEXT", true, false),
            ("name_alt", "TEXT", false, false),
            ("language", "TEXT", true, false),
            ("has_translations", "INTEGER", true, false)
        ]
        return try validateTableColumns(tableName: "authors", requiredColumns: requiredColumns, db: db)
    }
    
    private func validateWorksTable(db: OpaquePointer?) throws -> [String] {
        let requiredColumns = [
            ("id", "TEXT", true, true),
            ("author_id", "TEXT", true, false),
            ("title", "TEXT", true, false),
            ("title_alt", "TEXT", false, false),
            ("title_english", "TEXT", false, false),
            ("type", "TEXT", false, false),
            ("urn", "TEXT", false, false),
            ("description", "TEXT", false, false)
        ]
        return try validateTableColumns(tableName: "works", requiredColumns: requiredColumns, db: db)
    }
    
    private func validateBooksTable(db: OpaquePointer?) throws -> [String] {
        let requiredColumns = [
            ("id", "TEXT", true, true),
            ("work_id", "TEXT", true, false),
            ("book_number", "INTEGER", true, false),
            ("label", "TEXT", false, false),
            ("start_line", "INTEGER", false, false),
            ("end_line", "INTEGER", false, false),
            ("line_count", "INTEGER", false, false)
        ]
        return try validateTableColumns(tableName: "books", requiredColumns: requiredColumns, db: db)
    }
    
    private func validateTextLinesTable(db: OpaquePointer?) throws -> [String] {
        let requiredColumns = [
            ("id", "INTEGER", true, true),
            ("book_id", "TEXT", true, false),
            ("line_number", "INTEGER", true, false),
            ("sequence_number", "INTEGER", true, false),
            ("line_text", "TEXT", true, false),
            ("line_xml", "TEXT", false, false),
            ("speaker", "TEXT", false, false)
        ]
        return try validateTableColumns(tableName: "text_lines", requiredColumns: requiredColumns, db: db)
    }
    
    private func validateTranslationSegmentsTable(db: OpaquePointer?) throws -> [String] {
        let requiredColumns = [
            ("id", "INTEGER", true, true),
            ("book_id", "TEXT", true, false),
            ("start_line", "INTEGER", true, false),
            ("end_line", "INTEGER", false, false),
            ("translation_text", "TEXT", true, false),
            ("translator", "TEXT", false, false),
            ("speaker", "TEXT", false, false)
        ]
        return try validateTableColumns(tableName: "translation_segments", requiredColumns: requiredColumns, db: db)
    }
    
    private func validateTranslationLookupTable(db: OpaquePointer?) throws -> [String] {
        let requiredColumns = [
            ("book_id", "TEXT", true, false),
            ("line_number", "INTEGER", true, false),
            ("segment_id", "INTEGER", true, false)
        ]
        return try validateTableColumns(tableName: "translation_lookup", requiredColumns: requiredColumns, db: db)
    }
    
    private func validateWordsTable(db: OpaquePointer?) throws -> [String] {
        let requiredColumns = [
            ("id", "INTEGER", true, true),
            ("word", "TEXT", true, false),
            ("book_id", "TEXT", true, false),
            ("line_number", "INTEGER", true, false),
            ("sequence_number", "INTEGER", true, false),
            ("word_position", "INTEGER", true, false)
        ]
        var errors = try validateTableColumns(tableName: "words", requiredColumns: requiredColumns, db: db)
        
        // Ensure word_normalized column does NOT exist (it's a known issue)
        let columns = try getColumnsForTable("words", db: db)
        for column in columns {
            if column.name == "word_normalized" {
                errors.append("Table 'words': Column 'word_normalized' should not exist")
            }
        }
        
        return errors
    }
    
    private func validateDictionaryEntriesTable(db: OpaquePointer?) throws -> [String] {
        let requiredColumns = [
            ("id", "INTEGER", true, true),
            ("headword", "TEXT", true, false),
            ("headword_normalized_ultra", "TEXT", false, false),
            ("language", "TEXT", true, false),
            ("entry_xml", "TEXT", false, false),
            ("entry_html", "TEXT", false, false),
            ("entry_plain", "TEXT", false, false),
            ("source", "TEXT", false, false)
        ]
        return try validateTableColumns(tableName: "dictionary_entries", requiredColumns: requiredColumns, db: db)
    }
    
    private func validateLemmaMapTable(db: OpaquePointer?) throws -> [String] {
        let requiredColumns = [
            ("id", "INTEGER", true, true),
            ("word_form", "TEXT", true, false),
            ("word_form_normalized_ultra", "TEXT", false, false),
            ("lemma", "TEXT", true, false),
            ("confidence", "REAL", false, false),
            ("source", "TEXT", false, false),
            ("morph_info", "TEXT", false, false)
        ]
        return try validateTableColumns(tableName: "lemma_map", requiredColumns: requiredColumns, db: db)
    }
    
    // MARK: - Column Validation Helper
    
    private func validateTableColumns(tableName: String, requiredColumns: [(String, String, Bool, Bool)], db: OpaquePointer?) throws -> [String] {
        var errors: [String] = []
        
        let actualColumns = try getColumnsForTable(tableName, db: db)
        let actualColumnDict = Dictionary(uniqueKeysWithValues: actualColumns.map { ($0.name, $0) })
        
        for (columnName, expectedType, expectedNotNull, expectedPrimaryKey) in requiredColumns {
            guard let actualColumn = actualColumnDict[columnName] else {
                errors.append("Table '\(tableName)': Missing required column '\(columnName)'")
                continue
            }
            
            // Validate column type (allow some flexibility for INTEGER/TEXT)
            if !isCompatibleType(expected: expectedType, actual: actualColumn.type) {
                errors.append("Table '\(tableName)', Column '\(columnName)': Type mismatch. Expected '\(expectedType)', got '\(actualColumn.type)'")
            }
            
            // Validate NOT NULL constraint
            if expectedNotNull && !actualColumn.notNull {
                errors.append("Table '\(tableName)', Column '\(columnName)': Should be NOT NULL")
            }
            
            // Validate primary key
            if expectedPrimaryKey && actualColumn.primaryKey == 0 {
                errors.append("Table '\(tableName)', Column '\(columnName)': Should be PRIMARY KEY")
            }
        }
        
        return errors
    }
    
    private func isCompatibleType(expected: String, actual: String) -> Bool {
        let expectedUpper = expected.uppercased()
        let actualUpper = actual.uppercased()
        
        // Exact match
        if expectedUpper == actualUpper {
            return true
        }
        
        // Common compatible types
        if (expectedUpper == "INTEGER" && actualUpper == "INT") ||
           (expectedUpper == "TEXT" && actualUpper == "VARCHAR") ||
           (expectedUpper == "REAL" && actualUpper == "FLOAT") ||
           (expectedUpper == "REAL" && actualUpper == "DOUBLE") {
            return true
        }
        
        return false
    }
    
    // MARK: - Data Integrity Validation
    
    private func validateDataIntegrity(db: OpaquePointer?) throws -> (errors: [String], warnings: [String]) {
        var errors: [String] = []
        var warnings: [String] = []
        
        print("🔍 Validating data integrity...")
        
        // Check that tables have data
        for tableName in requiredTables {
            let count = try getTableRowCount(tableName: tableName, db: db)
            print("📊 Table '\(tableName)': \(count) rows")
            
            if count == 0 {
                if tableName == "authors" || tableName == "works" || tableName == "books" {
                    errors.append("Table '\(tableName)' is empty - database appears to be corrupted")
                } else {
                    warnings.append("Table '\(tableName)' is empty")
                }
            }
        }
        
        // Validate foreign key relationships
        try validateForeignKeyRelationships(db: db, errors: &errors, warnings: &warnings)
        
        return (errors, warnings)
    }
    
    private func validateForeignKeyRelationships(db: OpaquePointer?, errors: inout [String], warnings: inout [String]) throws {
        // Check works.author_id references authors.id
        let orphanedWorksQuery = """
            SELECT COUNT(*) FROM works w 
            LEFT JOIN authors a ON w.author_id = a.id 
            WHERE a.id IS NULL
        """
        let orphanedWorks = try executeCountQuery(query: orphanedWorksQuery, db: db)
        if orphanedWorks > 0 {
            errors.append("Found \(orphanedWorks) works with invalid author_id references")
        }
        
        // Check books.work_id references works.id
        let orphanedBooksQuery = """
            SELECT COUNT(*) FROM books b 
            LEFT JOIN works w ON b.work_id = w.id 
            WHERE w.id IS NULL
        """
        let orphanedBooks = try executeCountQuery(query: orphanedBooksQuery, db: db)
        if orphanedBooks > 0 {
            errors.append("Found \(orphanedBooks) books with invalid work_id references")
        }
        
        // Check text_lines.book_id references books.id
        let orphanedLinesQuery = """
            SELECT COUNT(*) FROM text_lines tl 
            LEFT JOIN books b ON tl.book_id = b.id 
            WHERE b.id IS NULL
        """
        let orphanedLines = try executeCountQuery(query: orphanedLinesQuery, db: db)
        if orphanedLines > 0 {
            errors.append("Found \(orphanedLines) text lines with invalid book_id references")
        }
    }
    
    // MARK: - Index Validation
    
    private func validateCriticalIndexes(db: OpaquePointer?) throws -> (errors: [String], warnings: [String]) {
        let errors: [String] = []
        var warnings: [String] = []
        
        print("🔍 Validating critical indexes...")
        
        let criticalIndexes = [
            ("authors", ["id"]),
            ("works", ["id", "author_id"]),
            ("books", ["id", "work_id"]),
            ("text_lines", ["book_id", "line_number"]),
            ("words", ["book_id", "line_number"])
        ]
        
        for (tableName, expectedIndexColumns) in criticalIndexes {
            let hasIndex = try hasIndexOnColumns(tableName: tableName, columns: expectedIndexColumns, db: db)
            if !hasIndex {
                warnings.append("Table '\(tableName)' missing index on columns: \(expectedIndexColumns.joined(separator: ", "))")
            }
        }
        
        return (errors, warnings)
    }
    
    private func hasIndexOnColumns(tableName: String, columns: [String], db: OpaquePointer?) throws -> Bool {
        let indexes = try getIndexesForTable(tableName, db: db)
        
        for index in indexes {
            if Set(index.columns) == Set(columns) {
                return true
            }
        }
        
        return false
    }
    
    // MARK: - Helper Methods
    
    private func getExtractedDatabasePath() -> String {
        let documentsPath = NSSearchPathForDirectoriesInDomains(.documentDirectory, .userDomainMask, true).first!
        return (documentsPath as NSString).appendingPathComponent("perseus_texts.db")
    }
    
    private func getTableRowCount(tableName: String, db: OpaquePointer?) throws -> Int {
        return try executeCountQuery(query: "SELECT COUNT(*) FROM \(tableName)", db: db)
    }
    
    private func executeCountQuery(query: String, db: OpaquePointer?) throws -> Int {
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, query, -1, &statement, nil) == SQLITE_OK else {
            throw ValidationError.queryFailed("Failed to prepare count query: \(query)")
        }
        
        defer { sqlite3_finalize(statement) }
        
        if sqlite3_step(statement) == SQLITE_ROW {
            return Int(sqlite3_column_int(statement, 0))
        }
        
        return 0
    }
    
    // MARK: - Schema Extraction Helpers
    
    private func getTableNames(db: OpaquePointer?) throws -> [String] {
        let query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name NOT LIKE 'sqlite_%'
            AND name NOT LIKE 'android_%'
            ORDER BY name
        """
        
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, query, -1, &statement, nil) == SQLITE_OK else {
            throw ValidationError.queryFailed("Failed to get table names")
        }
        
        defer { sqlite3_finalize(statement) }
        
        var tables: [String] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            if let namePtr = sqlite3_column_text(statement, 0) {
                tables.append(String(cString: namePtr))
            }
        }
        
        return tables
    }
    
    private func getColumnsForTable(_ tableName: String, db: OpaquePointer?) throws -> [ColumnSchema] {
        let query = "PRAGMA table_info('\(tableName)')"
        
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, query, -1, &statement, nil) == SQLITE_OK else {
            throw ValidationError.queryFailed("Failed to get columns for table \(tableName)")
        }
        
        defer { sqlite3_finalize(statement) }
        
        var columns: [ColumnSchema] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            let cid = Int(sqlite3_column_int(statement, 0))
            let name = String(cString: sqlite3_column_text(statement, 1))
            let type = String(cString: sqlite3_column_text(statement, 2))
            let notNull = sqlite3_column_int(statement, 3) != 0
            
            var defaultValue: String? = nil
            if let defaultPtr = sqlite3_column_text(statement, 4) {
                defaultValue = String(cString: defaultPtr)
            }
            
            let primaryKey = Int(sqlite3_column_int(statement, 5))
            
            columns.append(ColumnSchema(
                cid: cid,
                name: name,
                type: type,
                notNull: notNull,
                defaultValue: defaultValue,
                primaryKey: primaryKey
            ))
        }
        
        return columns
    }
    
    private func getIndexesForTable(_ tableName: String, db: OpaquePointer?) throws -> [IndexSchema] {
        let query = "PRAGMA index_list('\(tableName)')"
        
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, query, -1, &statement, nil) == SQLITE_OK else {
            throw ValidationError.queryFailed("Failed to get indexes for table \(tableName)")
        }
        
        defer { sqlite3_finalize(statement) }
        
        var indexes: [IndexSchema] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            let indexName = String(cString: sqlite3_column_text(statement, 1))
            let isUnique = sqlite3_column_int(statement, 2) != 0
            
            // Get columns for this index
            let indexColumns = try getIndexColumns(indexName, db: db)
            
            indexes.append(IndexSchema(
                name: indexName,
                tableName: tableName,
                columns: indexColumns,
                isUnique: isUnique
            ))
        }
        
        return indexes
    }
    
    private func getIndexColumns(_ indexName: String, db: OpaquePointer?) throws -> [String] {
        let query = "PRAGMA index_info('\(indexName)')"
        
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, query, -1, &statement, nil) == SQLITE_OK else {
            return []
        }
        
        defer { sqlite3_finalize(statement) }
        
        var columns: [String] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            if let columnPtr = sqlite3_column_text(statement, 2) {
                columns.append(String(cString: columnPtr))
            }
        }
        
        return columns
    }
    
    private func getPrimaryKeysForTable(_ tableName: String, db: OpaquePointer?) throws -> Set<String> {
        let columns = try getColumnsForTable(tableName, db: db)
        return Set(columns.filter { $0.primaryKey > 0 }.map { $0.name })
    }
    
    private func getForeignKeysForTable(_ tableName: String, db: OpaquePointer?) throws -> [ForeignKeySchema] {
        let query = "PRAGMA foreign_key_list('\(tableName)')"
        
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, query, -1, &statement, nil) == SQLITE_OK else {
            throw ValidationError.queryFailed("Failed to get foreign keys for table \(tableName)")
        }
        
        defer { sqlite3_finalize(statement) }
        
        var foreignKeys: [ForeignKeySchema] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            let id = Int(sqlite3_column_int(statement, 0))
            let toTable = String(cString: sqlite3_column_text(statement, 2))
            let fromColumn = String(cString: sqlite3_column_text(statement, 3))
            let toColumn = String(cString: sqlite3_column_text(statement, 4))
            let onUpdate = String(cString: sqlite3_column_text(statement, 5) ?? sqlite3_column_text(statement, 0))
            let onDelete = String(cString: sqlite3_column_text(statement, 6) ?? sqlite3_column_text(statement, 0))
            
            foreignKeys.append(ForeignKeySchema(
                id: id,
                fromColumn: fromColumn,
                toTable: toTable,
                toColumn: toColumn,
                onUpdate: onUpdate,
                onDelete: onDelete
            ))
        }
        
        return foreignKeys
    }
    
    
    // MARK: - Error Types
    
    enum ValidationError: LocalizedError {
        case bundledDatabaseNotFound
        case databaseNotFound(String)
        case cannotOpenDatabase(String)
        case queryFailed(String)
        
        var errorDescription: String? {
            switch self {
            case .bundledDatabaseNotFound:
                return "Bundled database not found in app resources"
            case .databaseNotFound(let message):
                return "Database not found: \(message)"
            case .cannotOpenDatabase(let path):
                return "Cannot open database at path: \(path)"
            case .queryFailed(let message):
                return "Query failed: \(message)"
            }
        }
    }
}

// MARK: - DatabaseExtractor Extension

extension DatabaseExtractor {
    /// Extract database from ZIP to specific path (for validation purposes)
    func extractDatabaseFromZip(at zipURL: URL, to destinationPath: String) async throws {
        _ = FileManager.default
        
        // Read ZIP file
        guard let zipData = try? Data(contentsOf: zipURL) else {
            throw ExtractionError.resourceNotFound
        }
        
        // Extract using the same logic as main extraction
        guard let decompressedData = try? (zipData as NSData).decompressed(using: .zlib) as Data else {
            throw ExtractionError.extractionFailed("Failed to decompress ZIP data")
        }
        
        // Write to destination
        try decompressedData.write(to: URL(fileURLWithPath: destinationPath))
    }
}