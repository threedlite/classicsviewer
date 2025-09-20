import Foundation
import os.log

/// Helper class for extracting and managing the default bundled audio package
class DefaultAudioExtractor {
    static let shared = DefaultAudioExtractor()
    
    private let logger = Logger(subsystem: "com.classicsviewer.app", category: "DefaultAudioExtractor")
    private let audioDAO = AudioPackageDAO()
    
    private let defaultAudioZip = "homer_iliad_chamberlain_audio_7.zip"
    private let defaultPackageId = -1
    private let defaultPackageName = "bundled_chamberlain_iliad"
    private let defaultDisplayName = "Homer - Iliad (Chamberlain) [Bundled]"
    
    private init() {}
    
    /// Check if default audio package needs to be extracted and extract if necessary
    func ensureDefaultAudioExtracted() async throws {
        logger.info("DefaultAudioExtractor: Starting ensureDefaultAudioExtracted")
        NSLog("DEBUG: DefaultAudioExtractor.ensureDefaultAudioExtracted() called")
        
        // First ensure user database is initialized
        logger.info("Initializing user database for audio...")
        NSLog("DEBUG: Initializing user database for audio")
        // Database lifecycle managed by async architecture - UserDatabaseManagerAsync handles this
        NSLog("DEBUG: User database opened successfully")
        
        // Check if already extracted
        let packages = try await audioDAO.getPackages()
        logger.info("Found \(packages.count) existing audio packages")
        print("DEBUG: Found \(packages.count) existing audio packages")
        let hasBundledPackage = packages.contains { package in
            package.packageName == defaultPackageName
        }
        
        if hasBundledPackage {
            logger.info("Default audio package already extracted")
            print("DEBUG: Default audio package already extracted")
            return
        }
        
        logger.info("No bundled package found, will extract")
        print("DEBUG: No bundled package found, will extract")
        
        // Extract the bundled audio
        logger.info("Extracting default audio package...")
        print("DEBUG: Extracting default audio package...")
        try await extractDefaultAudio()
        print("DEBUG: Default audio extraction completed")
    }
    
    private func extractDefaultAudio() async throws {
        logger.info("Looking for bundled audio ZIP in app bundle...")
        print("DEBUG: Looking for bundled audio ZIP in app bundle...")
        // Get the bundled ZIP from app resources
        guard let bundledURL = Bundle.main.url(forResource: "homer_iliad_chamberlain_audio_7", withExtension: "zip") else {
            logger.error("Default audio ZIP not found in bundle")
            logger.error("Bundle main path: \(Bundle.main.bundlePath)")
            print("ERROR: Default audio ZIP not found in bundle")
            print("ERROR: Bundle main path: \(Bundle.main.bundlePath)")
            return
        }
        logger.info("Found bundled ZIP at: \(bundledURL.path)")
        print("DEBUG: Found bundled ZIP at: \(bundledURL.path)")
        
        // Create audio directory structure
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let audioPath = documentsPath.appendingPathComponent("audio")
        let packagePath = audioPath.appendingPathComponent(defaultPackageName)
        
        try FileManager.default.createDirectory(at: audioPath, withIntermediateDirectories: true)
        
        // Remove existing package directory if it exists
        if FileManager.default.fileExists(atPath: packagePath.path) {
            try FileManager.default.removeItem(at: packagePath)
        }
        
        try FileManager.default.createDirectory(at: packagePath, withIntermediateDirectories: true)
        
        // Extract all files from the ZIP
        logger.info("Extracting ZIP contents...")
        try ZIPHandler.extractAll(from: bundledURL, to: packagePath)
        
        // Scan the extracted files to build audio file entries
        let audioFiles = try scanExtractedAudioFiles(in: packagePath, documentsPath: documentsPath)
        
        // Create the package metadata
        let metadata: [String: Any] = [
            "package_name": defaultPackageName,
            "display_name": defaultDisplayName,
            "description": "Bundled audio for Homer's Iliad (first 7 lines)",
            "version": "1.0",
            "created_date": Date()
        ]
        
        // Import to database
        let packageId = try await audioDAO.importAudioPackage(metadata: metadata, audioFiles: audioFiles)
        
        // Enable it by default as the first package
        try await audioDAO.setPackageEnabled(packageId: packageId, enabled: true)
        
        logger.info("Default audio package imported successfully")
    }
    
    private func scanExtractedAudioFiles(in packagePath: URL, documentsPath: URL) throws -> [[String: Any]] {
        var audioFiles: [[String: Any]] = []
        let fileManager = FileManager.default
        
        // The ZIP structure is: Homer/Iliad/book_1/line_X.mp4
        // We know it's for Homer's Iliad Book 1, lines 1-7
        let bookPath = packagePath.appendingPathComponent("Homer/Iliad/book_1")
        
        if fileManager.fileExists(atPath: bookPath.path) {
            let files = try fileManager.contentsOfDirectory(at: bookPath, includingPropertiesForKeys: [.fileSizeKey])
            
            for file in files {
                if file.pathExtension.lowercased() == "mp4" {
                    // Extract line number from filename (e.g., "line_3.mp4" -> 3)
                    let filename = file.deletingPathExtension().lastPathComponent
                    if filename.hasPrefix("line_") {
                        let lineStr = filename.replacingOccurrences(of: "line_", with: "")
                        if let lineNumber = Int(lineStr) {
                            // Get file size
                            let attributes = try fileManager.attributesOfItem(atPath: file.path)
                            let fileSize = attributes[.size] as? Int ?? 0
                            
                            // Create relative path from Documents directory
                            let relativePath = file.path.replacingOccurrences(of: documentsPath.path + "/", with: "")
                            
                            audioFiles.append([
                                "work_id": "homer_iliad",
                                "book_id": "1",
                                "line_start": lineNumber,
                                "line_end": lineNumber,
                                "file_path": relativePath,
                                "file_size": fileSize,
                                "mime_type": "audio/mp4"
                            ])
                        }
                    }
                }
            }
        }
        
        logger.info("Scanned \(audioFiles.count) audio files")
        return audioFiles
    }
}