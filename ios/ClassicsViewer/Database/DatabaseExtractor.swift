import Foundation
import Compression

class DatabaseExtractor {
    static let shared = DatabaseExtractor()
    private init() {}
    
    private let minimumDatabaseSize: Int64 = 1000 // 1KB minimum
    private let bufferSize = 1_048_576 // 1MB buffer for extraction
    
    enum ExtractionError: LocalizedError {
        case resourceNotFound
        case invalidZipFile
        case noDatabaseInZip
        case extractionFailed(String)
        case databaseTooSmall
        case invalidDatabase
        
        var errorDescription: String? {
            switch self {
            case .resourceNotFound:
                return "Database resource not found in app bundle"
            case .invalidZipFile:
                return "Invalid or corrupted ZIP file"
            case .noDatabaseInZip:
                return "No database file found in ZIP archive"
            case .extractionFailed(let detail):
                return "Extraction failed: \(detail)"
            case .databaseTooSmall:
                return "Extracted database is too small (possibly corrupted)"
            case .invalidDatabase:
                return "Database validation failed"
            }
        }
    }
    
    // MARK: - Bundle Database Extraction
    
    func extractBundledDatabase(progress: ((Double) -> Void)? = nil) async throws {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let databasePath = documentsPath.appendingPathComponent("perseus_texts.db")
        
        print("DEBUG: Database path: \(databasePath.path)")
        
        // Check if already extracted
        if FileManager.default.fileExists(atPath: databasePath.path) {
            print("DEBUG: Database already exists, validating...")
            // Validate existing database
            if try await validateDatabase(at: databasePath) {
                print("DEBUG: Existing database is valid, skipping extraction")
                return
            } else {
                print("DEBUG: Existing database is invalid, removing...")
                // Remove invalid database
                try? FileManager.default.removeItem(at: databasePath)
            }
        }
        
        print("DEBUG: Looking for bundled database ZIP...")
        // Find bundled database ZIP - try both names
        var zipURL = Bundle.main.url(forResource: "perseus_texts_sample.db", withExtension: "zip")
        if zipURL == nil {
            zipURL = Bundle.main.url(forResource: "perseus_texts.db", withExtension: "zip")
        }
        
        guard let zipURL = zipURL else {
            print("DEBUG: ERROR - Database ZIP not found in bundle!")
            print("DEBUG: Searched for perseus_texts_sample.db.zip and perseus_texts.db.zip")
            throw ExtractionError.resourceNotFound
        }
        
        print("DEBUG: Found database ZIP at: \(zipURL.path)")
        print("DEBUG: Starting extraction...")
        
        // Extract database
        try await extractZipDatabase(from: zipURL, to: databasePath, progress: progress)
        
        // Validate extracted database
        guard try await validateDatabase(at: databasePath) else {
            try? FileManager.default.removeItem(at: databasePath)
            throw ExtractionError.invalidDatabase
        }
    }
    
    // MARK: - ZIP Extraction
    
    private func extractZipDatabase(from sourceURL: URL, to destinationURL: URL, progress: ((Double) -> Void)? = nil) async throws {
        // Create temporary file for extraction
        let tempURL = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".db")
        
        do {
            // Extract database from ZIP
            try ZIPHandler.extractDatabase(from: sourceURL, to: tempURL, progress: progress)
            
            // Verify size
            let attributes = try FileManager.default.attributesOfItem(atPath: tempURL.path)
            let fileSize = attributes[.size] as? Int64 ?? 0
            
            if fileSize < minimumDatabaseSize {
                try? FileManager.default.removeItem(at: tempURL)
                throw ExtractionError.databaseTooSmall
            }
            
            // Move to final location
            try? FileManager.default.removeItem(at: destinationURL)
            try FileManager.default.moveItem(at: tempURL, to: destinationURL)
            
        } catch {
            // Clean up temp file on error
            try? FileManager.default.removeItem(at: tempURL)
            
            if let zipError = error as? ZIPHandler.ZIPError {
                throw ExtractionError.extractionFailed(zipError.localizedDescription)
            } else {
                throw error
            }
        }
    }
    
    // MARK: - Database Validation
    
    func validateDatabase(at url: URL) async throws -> Bool {
        // Check file exists and size
        let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
        let fileSize = attributes[.size] as? Int64 ?? 0
        
        print("DEBUG: Validating database at \(url.path)")
        print("DEBUG: Database file size: \(fileSize) bytes")
        
        if fileSize < minimumDatabaseSize {
            print("DEBUG: Database too small! Expected at least \(minimumDatabaseSize) bytes")
            return false
        }
        
        // Open database and check basic structure
        let validator = DatabaseValidator()
        let isValid = try await validator.validateDatabaseStructure(at: url)
        print("DEBUG: Database validation result: \(isValid)")
        return isValid
    }
}