import SwiftUI
import UniformTypeIdentifiers
import SQLite3

struct AudioManagementView: View {
    @State private var packages: [AudioPackage] = []
    @State private var isLoading = false
    @State private var isImporting = false
    @State private var importProgress: Double = 0
    @State private var importStatus = ""
    @State private var errorMessage = ""
    @State private var showingAlert = false
    @State private var showingImporter = false
    @State private var showingDeleteConfirmation: AudioPackage? = nil
    @State private var showingManualImport = false
    @State private var manualFilePath = "homer_iliad_chamberlain_audio.zip"
    @State private var debugInfo = ""

    private let audioDAO = AudioPackageDAO()
    
    var body: some View {
        ZStack {
            List {
            if packages.isEmpty && !isLoading {
                VStack(spacing: 20) {
                    Image(systemName: "speaker.slash")
                        .font(.system(size: 50))
                        .foregroundColor(.secondary)
                    
                    Text("No Audio Packages")
                        .font(.title2)
                        .foregroundColor(.secondary)
                    
                    Text("Import audio packages to enable audio playback")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                    
                    Button(action: {
                        showingImporter = true
                    }) {
                        Label("Import Audio Package", systemImage: "plus.circle.fill")
                            .font(.body)
                    }
                    .buttonStyle(.borderedProminent)
                    
                    Button(action: {
                        showingManualImport = true
                    }) {
                        Label("Import from Path", systemImage: "doc.text")
                            .font(.body)
                    }
                    .buttonStyle(.bordered)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 50)
            } else {
                ForEach(packages) { package in
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(package.displayName)
                                    .font(.headline)
                                
                                Text(package.packageName)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                
                                if let version = package.version {
                                    Text("Version: \(version)")
                                        .font(.caption2)
                                        .foregroundColor(.secondary)
                                }
                                
                                Text("\(package.fileCount) files • \(formatBytes(package.totalSize))")
                                    .font(.caption2)
                                    .foregroundColor(.secondary)
                            }
                            
                            Spacer()

                            // Only show delete button for user-imported packages, not the default bundled one
                            // The bundled package is named "bundled_chamberlain_iliad"
                            if package.packageName != "bundled_chamberlain_iliad" {
                                Button(action: {
                                    showingDeleteConfirmation = package
                                }) {
                                    Image(systemName: "trash")
                                        .foregroundColor(.red)
                                        .font(.body)
                                }
                                .padding(.trailing, 8)
                            }

                            Button(action: {
                                togglePackageEnabled(package)
                            }) {
                                Image(systemName: package.isEnabled ? "checkmark.circle.fill" : "circle")
                                    .foregroundColor(package.isEnabled ? .green : .secondary)
                                    .font(.title2)
                            }
                        }
                    }
                    .padding(.vertical, 4)
                    .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                        Button(role: .destructive) {
                            showingDeleteConfirmation = package
                        } label: {
                            Label("Delete", systemImage: "trash")
                        }
                    }
                }
            }
            
            if isImporting {
                VStack(alignment: .leading, spacing: 8) {
                    Text(importStatus)
                        .font(.caption)
                        .foregroundColor(.secondary)

                    ProgressView(value: importProgress)
                }
                .padding(.vertical)
            }

            // Debug section - show first few audio files
            Section(header: Text("Debug: Audio Files in Database")) {
                Button("Show Audio Files") {
                    Task {
                        await showDebugInfo()
                    }
                }
                if !debugInfo.isEmpty {
                    ScrollView(.horizontal) {
                        Text(debugInfo)
                            .font(.system(.caption, design: .monospaced))
                            .foregroundColor(.secondary)
                            .padding(8)
                            .background(Color.gray.opacity(0.1))
                            .cornerRadius(4)
                    }
                }
            }
        }
        .navigationTitle("Audio Packages")
        .navigationBarTitleDisplayMode(.large)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Menu {
                    Button(action: {
                        showingImporter = true
                    }) {
                        Label("Import from Files", systemImage: "doc.badge.plus")
                    }
                    
                    Button(action: {
                        showingManualImport = true
                    }) {
                        Label("Import from Path", systemImage: "doc.text")
                    }
                } label: {
                    Image(systemName: "plus")
                }
                .disabled(isImporting)
            }
        }
        .onAppear {
            loadPackages()
        }
        .refreshable {
            loadPackages()
        }
        .fileImporter(
            isPresented: $showingImporter,
            allowedContentTypes: [
                UTType(filenameExtension: "zip") ?? .archive
            ],
            allowsMultipleSelection: false
        ) { result in
            switch result {
            case .success(let urls):
                guard let url = urls.first else {
                    errorMessage = "No file was selected"
                    showingAlert = true
                    return
                }

                // Copy the file immediately while we have access
                Task {
                    // Start security-scoped access
                    let accessing = url.startAccessingSecurityScopedResource()
                    defer {
                        if accessing {
                            url.stopAccessingSecurityScopedResource()
                        }
                    }

                    // Copy to a temporary location we control
                    let tempURL = FileManager.default.temporaryDirectory.appendingPathComponent("import_\(UUID().uuidString)_\(url.lastPathComponent)")

                    do {
                        try FileManager.default.copyItem(at: url, to: tempURL)
                        print("DEBUG: File copied to temporary location: \(tempURL.path)")

                        // Now import from the temp copy
                        await importAudioPackage(from: tempURL)

                        // Clean up temp file
                        try? FileManager.default.removeItem(at: tempURL)
                    } catch {
                        print("ERROR: Failed to copy file: \(error)")
                        await MainActor.run {
                            errorMessage = "Failed to access file: \(error.localizedDescription)"
                            showingAlert = true
                        }
                    }
                }
            case .failure(let error):
                print("ERROR: File selection failed: \(error)")
                errorMessage = "Failed to select file: \(error.localizedDescription)"
                showingAlert = true
            }
        }
        .alert("Delete Audio Package", isPresented: .constant(showingDeleteConfirmation != nil)) {
            Button("Cancel", role: .cancel) {
                showingDeleteConfirmation = nil
            }
            Button("Delete", role: .destructive) {
                if let package = showingDeleteConfirmation {
                    deletePackage(package)
                }
                showingDeleteConfirmation = nil
            }
        } message: {
            if let package = showingDeleteConfirmation {
                Text("Are you sure you want to delete '\(package.displayName)'? This action cannot be undone.")
            }
        }
        .alert("Error", isPresented: $showingAlert) {
            Button("OK") { }
        } message: {
            Text(errorMessage)
        }
        .sheet(isPresented: $showingManualImport) {
            NavigationView {
                VStack(alignment: .leading, spacing: 20) {
                    Text("Manual File Import")
                        .font(.headline)
                        .padding(.top)
                    
                    Text("Enter the filename (relative to Documents folder):")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    TextField("File path", text: $manualFilePath)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                        .autocapitalization(.none)
                        .disableAutocorrection(true)
                    
                    Text("Files in Documents folder:")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    Text("homer_iliad_chamberlain_audio.zip")
                        .font(.caption2)
                        .foregroundColor(.blue)
                        .padding(.horizontal)
                    
                    Spacer()
                }
                .padding()
                .navigationBarTitle("Import from Path", displayMode: .inline)
                .navigationBarItems(
                    leading: Button("Cancel") {
                        showingManualImport = false
                    },
                    trailing: Button("Import") {
                        showingManualImport = false
                        Task {
                            await importFromManualPath()
                        }
                    }
                    .disabled(manualFilePath.isEmpty)
                )
            }
        }
            
            // Progress overlay
            if isImporting {
                Color.black.opacity(0.3)
                    .ignoresSafeArea()
                
                VStack(spacing: 20) {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle())
                        .scaleEffect(1.5)
                    
                    Text(importStatus)
                        .font(.headline)
                        .foregroundColor(.white)
                    
                    ProgressView(value: importProgress)
                        .progressViewStyle(LinearProgressViewStyle())
                        .frame(width: 250)
                        .accentColor(.blue)
                    
                    Text("\(Int(importProgress * 100))%")
                        .font(.caption)
                        .foregroundColor(.white)
                }
                .padding(30)
                .background(Color.black.opacity(0.8))
                .cornerRadius(15)
                .shadow(radius: 10)
            }
        }
    }
    
    private func loadPackages() {
        isLoading = true
        Task {
            do {
                // Fix any incorrect paths first (one-time migration)
                try await audioDAO.fixIncorrectAudioPaths()
                packages = try await audioDAO.getPackages()
            } catch {
                await MainActor.run {
                    errorMessage = "Failed to load audio packages: \(error.localizedDescription)"
                    showingAlert = true
                }
            }
            await MainActor.run {
                isLoading = false
            }
        }
    }
    
    private func togglePackageEnabled(_ package: AudioPackage) {
        Task {
            do {
                // Radio button behavior - only one package can be enabled at a time
                if !package.isEnabled {
                    // Disable all other packages first
                    for pkg in packages where pkg.isEnabled && pkg.id != package.id {
                        try await audioDAO.setPackageEnabled(packageId: pkg.id!, enabled: false)
                    }
                    // Enable this package
                    try await audioDAO.setPackageEnabled(packageId: package.id!, enabled: true)
                    loadPackages()
                }
                // If already enabled, do nothing (can't disable the only enabled package)
            } catch {
                await MainActor.run {
                    errorMessage = "Failed to update package: \(error.localizedDescription)"
                    showingAlert = true
                }
            }
        }
    }
    
    private func deletePackage(_ package: AudioPackage) {
        Task {
            do {
                try await audioDAO.deletePackage(packageId: package.id!)
                loadPackages()
            } catch {
                await MainActor.run {
                    errorMessage = "Failed to delete package: \(error.localizedDescription)"
                    showingAlert = true
                }
            }
        }
    }
    
private func importFromManualPath() async {
        print("DEBUG: Attempting to import from manual path: \(manualFilePath)")
        
        // Handle relative paths from Documents directory
        let url: URL
        if manualFilePath.starts(with: "/") {
            // Absolute path
            url = URL(fileURLWithPath: manualFilePath)
        } else {
            // Relative path - assume relative to Documents directory
            let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
            url = documentsPath.appendingPathComponent(manualFilePath)
        }
        
        print("DEBUG: Full path to check: \(url.path)")
        
        // Check if file exists
        if !FileManager.default.fileExists(atPath: url.path) {
            await MainActor.run {
                errorMessage = "File not found at path: \(url.path)"
                showingAlert = true
            }
            return
        }
        
        // Check if it's a ZIP file
        guard url.pathExtension.lowercased() == "zip" else {
            await MainActor.run {
                errorMessage = "File must be a ZIP archive"
                showingAlert = true
            }
            return
        }
        
        // Use the existing import function
        await importAudioPackage(from: url)
    }
    
    private func importAudioPackage(from url: URL) async {
        print("DEBUG: importAudioPackage called with URL: \(url)")
        print("DEBUG: File exists: \(FileManager.default.fileExists(atPath: url.path))")

        // Show progress immediately - MUST be first thing
        await MainActor.run {
            isImporting = true
            importStatus = "Loading \(url.lastPathComponent)..."
            importProgress = 0.01
        }

        // Small delay to ensure UI updates
        try? await Task.sleep(nanoseconds: 100_000_000) // 0.1 seconds

        // Declare these outside the do block so they're accessible in catch
        let isAlreadyTemp = url.path.contains("/tmp/") || url.path.contains("/private/var/mobile/Containers/Data/Application") && url.path.contains("/tmp/")
        var workingURL: URL? = nil

        do {

            if isAlreadyTemp {
                // Already a temp file, use it directly
                print("DEBUG: Using existing temp file: \(url.path)")
                workingURL = url

                // Check if file exists
                guard FileManager.default.fileExists(atPath: url.path) else {
                    print("ERROR: Temp file does not exist at path: \(url.path)")
                    throw ImportError.cannotAccessFile
                }
            } else {
                // Not a temp file, need to copy it
                let needsSecurityScope = url.startAccessingSecurityScopedResource()
                print("DEBUG: Security-scoped resource access: \(needsSecurityScope)")
                defer {
                    if needsSecurityScope {
                        url.stopAccessingSecurityScopedResource()
                    }
                }

                // Check if file is accessible
                guard FileManager.default.fileExists(atPath: url.path) else {
                    print("ERROR: File does not exist at path: \(url.path)")
                    throw ImportError.cannotAccessFile
                }

                // Check file permissions
                guard FileManager.default.isReadableFile(atPath: url.path) else {
                    print("ERROR: File is not readable at path: \(url.path)")
                    throw ImportError.cannotAccessFile
                }

                // Update status before copying
                await MainActor.run {
                    importStatus = "Copying file to temporary location..."
                    importProgress = 0.05
                }

                // Copy to temp location
                let tempURL = FileManager.default.temporaryDirectory.appendingPathComponent(url.lastPathComponent)
                try? FileManager.default.removeItem(at: tempURL) // Remove if exists
                try FileManager.default.copyItem(at: url, to: tempURL)
                workingURL = tempURL
            }
            
            await MainActor.run {
                importStatus = "Analyzing package..."
                importProgress = 0.1
            }

            // Make sure we have a valid working URL
            guard let finalWorkingURL = workingURL else {
                throw ImportError.cannotAccessFile
            }

            // Extract package name from ZIP
            let packageName = finalWorkingURL.deletingPathExtension().lastPathComponent
            let displayName = packageName.replacingOccurrences(of: "_", with: " ")
                .replacingOccurrences(of: "-", with: " ")
                .capitalized
            
            // Create audio directory
            let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
            let audioPath = documentsPath.appendingPathComponent("audio")
            let packagePath = audioPath.appendingPathComponent(packageName)
            
            try FileManager.default.createDirectory(at: audioPath, withIntermediateDirectories: true)
            
            // Remove existing package directory if it exists
            if FileManager.default.fileExists(atPath: packagePath.path) {
                try FileManager.default.removeItem(at: packagePath)
            }
            
            try FileManager.default.createDirectory(at: packagePath, withIntermediateDirectories: true)
            
            await MainActor.run {
                importStatus = "Extracting audio files..."
                importProgress = 0.2
            }
            
            // Extract all files from the ZIP
            print("DEBUG: Starting ZIP extraction from \(finalWorkingURL) to \(packagePath)")
            try ZIPHandler.extractAll(from: finalWorkingURL, to: packagePath) { progress in
                print("DEBUG: Extraction progress: \(Int(progress * 100))%")
                Task { @MainActor in
                    self.importProgress = 0.2 + (progress * 0.5) // 20% to 70%
                    self.importStatus = "Extracting: \(Int(progress * 100))%"
                }
            }
            print("DEBUG: ZIP extraction complete")
            
            await MainActor.run {
                importStatus = "Scanning audio files..."
                importProgress = 0.7
            }
            
            // Scan the extracted files to build audio file entries
            let audioFiles = try scanAudioFiles(in: packagePath, packageName: packageName, documentsPath: documentsPath)
            
            await MainActor.run {
                importStatus = "Saving to database..."
                importProgress = 0.85
            }
            
            // Prepare metadata
            let metadata: [String: Any] = [
                "package_name": packageName,
                "display_name": displayName,
                "description": "Imported from \(url.lastPathComponent)",
                "version": "1.0",
                "created_date": Date()
            ]
            
            // Import to database
            let packageId = try await audioDAO.importAudioPackage(metadata: metadata, audioFiles: audioFiles)
            
            // Disable all other packages and enable this new one (radio button behavior)
            let currentPackages = try await audioDAO.getPackages()
            for pkg in currentPackages where pkg.isEnabled {
                try await audioDAO.setPackageEnabled(packageId: pkg.id!, enabled: false)
            }
            // Enable the newly imported package
            try await audioDAO.setPackageEnabled(packageId: packageId, enabled: true)

            // Clean up temp file if we created one (not if it was already temp)
            if !isAlreadyTemp, let tempFile = workingURL, FileManager.default.fileExists(atPath: tempFile.path) {
                try? FileManager.default.removeItem(at: tempFile)
                print("DEBUG: Cleaned up temp file: \(tempFile.path)")
            }

            await MainActor.run {
                importStatus = "Import complete! Found \(audioFiles.count) audio files."
                importProgress = 1.0
            }
            
            // Reload packages
            loadPackages()
            
            // Clear import status after delay
            try? await Task.sleep(nanoseconds: 3_000_000_000) // 3 seconds
            
            await MainActor.run {
                isImporting = false
                importStatus = ""
                importProgress = 0
            }

        } catch {
            await MainActor.run {
                errorMessage = "Import failed: \(error.localizedDescription)"
                showingAlert = true
                isImporting = false
                importStatus = ""
                importProgress = 0
            }

            // Clean up temp file on error too
            if !isAlreadyTemp, let tempFile = workingURL, FileManager.default.fileExists(atPath: tempFile.path) {
                try? FileManager.default.removeItem(at: tempFile)
                print("DEBUG: Cleaned up temp file after error: \(tempFile.path)")
            }
        }
    }
    
    private func scanAudioFiles(in packagePath: URL, packageName: String, documentsPath: URL) throws -> [[String: Any]] {
        var audioFiles: [[String: Any]] = []
        let fileManager = FileManager.default
        
        // Expected structure: Author/Work/book_X/line_Y.mp4 or .mp3
        // For Chamberlain: Homer/Iliad/book_1/line_1.mp4
        
        // Recursively scan for audio files
        let enumerator = fileManager.enumerator(at: packagePath, includingPropertiesForKeys: [.fileSizeKey, .isRegularFileKey])
        
        while let fileURL = enumerator?.nextObject() as? URL {
            let pathExtension = fileURL.pathExtension.lowercased()
            
            // Check if it's an audio file
            if pathExtension == "mp3" || pathExtension == "mp4" || pathExtension == "m4a" {
                // Parse the path to extract metadata
                // Get the full path and find the relevant part
                let fullPath = fileURL.path
                print("DEBUG scanAudioFiles: Full file path: \(fullPath)")
                print("DEBUG scanAudioFiles: Package path: \(packagePath.path)")

                // Extract the relative path from the package directory
                var relativePath: String
                if let packageRange = fullPath.range(of: packagePath.path) {
                    // Get everything after the package path
                    let afterPackage = String(fullPath[packageRange.upperBound...])
                    // Remove leading slash if present
                    relativePath = afterPackage.hasPrefix("/") ? String(afterPackage.dropFirst()) : afterPackage
                } else {
                    // Fallback: try to find known patterns like "Homer/Iliad"
                    if let homerRange = fullPath.range(of: "Homer/", options: .caseInsensitive) {
                        relativePath = String(fullPath[homerRange.lowerBound...])
                    } else {
                        print("WARNING: Could not extract relative path from: \(fullPath)")
                        continue
                    }
                }

                print("DEBUG scanAudioFiles: Extracted relative path: \(relativePath)")

                // Split into components and filter out any "private" artifacts
                let rawComponents = relativePath.split(separator: "/").map(String.init)
                // Filter out any "private" component that might have snuck in
                let components = rawComponents.filter { !$0.contains("private") }
                print("DEBUG scanAudioFiles: Path components after filtering: \(components)")

                // Try to parse the structure
                if components.count >= 3 {
                    // Expected: Author/Work/book_X/line_Y.mp4
                    let author = components[0].lowercased().replacingOccurrences(of: "private", with: "")
                    let work = components[1].lowercased().replacingOccurrences(of: "private", with: "")

                    // Map to work_id format - ensure no "private" prefix
                    var workId = "\(author)_\(work)"
                    // Final cleanup - remove any "private" that might have been concatenated
                    if workId.hasPrefix("private") {
                        workId = String(workId.dropFirst(7)) // Remove "private" prefix
                    }
                    workId = workId.replacingOccurrences(of: "private", with: "")

                    // Extract book number if present
                    var bookId: String? = nil
                    var lineStart = 0
                    var lineEnd = 0

                    // Check for book folder - try different positions in case path structure varies
                    for (index, component) in components.enumerated() {
                        if component.starts(with: "book_") {
                            bookId = String(component.dropFirst(5))
                            print("DEBUG: Found book folder '\(component)' at index \(index), extracted book ID: '\(bookId ?? "nil")'")

                            // Parse line number from next component if it exists
                            if index + 1 < components.count {
                                let filename = components[index + 1]
                                if filename.starts(with: "line_") {
                                    let lineStr = filename.dropFirst(5).split(separator: ".")[0]
                                    if let lineNum = Int(lineStr) {
                                        lineStart = lineNum
                                        lineEnd = lineNum
                                    }
                                }
                            }
                            break
                        }
                    }
                    
                    // Get file size
                    let attributes = try fileManager.attributesOfItem(atPath: fileURL.path)
                    let fileSize = attributes[.size] as? Int ?? 0
                    
                    // Create relative path from Documents directory
                    let fullRelativePath = fileURL.path.replacingOccurrences(of: documentsPath.path + "/", with: "")
                    
                    // Determine MIME type
                    let mimeType = pathExtension == "mp3" ? "audio/mpeg" : "audio/mp4"
                    
                    if lineStart > 0 {
                        print("DEBUG: Adding audio file - work_id: '\(workId)', book_id: '\(bookId ?? "1")', lines: \(lineStart)-\(lineEnd), path: \(fullRelativePath)")
                        audioFiles.append([
                            "work_id": workId,
                            "book_id": bookId ?? "1",
                            "line_start": lineStart,
                            "line_end": lineEnd,
                            "file_path": fullRelativePath,
                            "file_size": fileSize,
                            "mime_type": mimeType
                        ])
                    }
                }
            }
        }
        
        return audioFiles
    }
    
    private func formatBytes(_ bytes: Int) -> String {
        let formatter = ByteCountFormatter()
        formatter.countStyle = .file
        return formatter.string(fromByteCount: Int64(bytes))
    }

    private func showDebugInfo() async {
        await MainActor.run {
            debugInfo = "Loading..."
        }

        do {
            // First check if we have any audio files at all
            let countQuery = "SELECT COUNT(*) FROM audio_files"
            let count = try await UserDatabaseManagerAsync.shared.executeQuery(countQuery) { statement in
                return Int(sqlite3_column_int(statement, 0))
            }.first ?? 0

            if count == 0 {
                await MainActor.run {
                    debugInfo = "No audio files in database at all!"
                }
                return
            }

            // Get sample audio files from database - show different books
            let query = """
                SELECT DISTINCT f.work_id, f.book_id, COUNT(*) as cnt, MIN(f.line_start) as min_line, MAX(f.line_end) as max_line, p.package_name, p.is_enabled
                FROM audio_files f
                JOIN audio_packages p ON f.package_id = p.id
                GROUP BY f.work_id, f.book_id, p.package_name, p.is_enabled
                LIMIT 10
            """

            let results = try await UserDatabaseManagerAsync.shared.executeQuery(query) { statement in
                let workIdPtr = sqlite3_column_text(statement, 0)
                let workId = workIdPtr != nil ? String(cString: workIdPtr!) : "NULL"
                let bookIdPtr = sqlite3_column_text(statement, 1)
                let bookId = bookIdPtr != nil ? String(cString: bookIdPtr!) : "NULL"
                let lineStart = Int(sqlite3_column_int(statement, 2))
                let lineEnd = Int(sqlite3_column_int(statement, 3))
                let packageNamePtr = sqlite3_column_text(statement, 4)
                let packageName = packageNamePtr != nil ? String(cString: packageNamePtr!) : "NULL"
                let isEnabled = sqlite3_column_int(statement, 5) != 0
                return "Pkg: \(packageName) (on:\(isEnabled))\nWork: '\(workId)' Book: '\(bookId)' L:\(lineStart)-\(lineEnd)"
            }

            await MainActor.run {
                if results.isEmpty {
                    debugInfo = "Query returned 0 rows (count was \(count))"
                } else {
                    debugInfo = "Total: \(count) files\n\n" + results.joined(separator: "\n---\n")
                }
            }
        } catch {
            await MainActor.run {
                debugInfo = "Error: \(error.localizedDescription)\n\(error)"
            }
        }
    }
}

enum ImportError: LocalizedError {
    case cannotAccessFile
    case extractionFailed
    case invalidPackage
    
    var errorDescription: String? {
        switch self {
        case .cannotAccessFile:
            return "Cannot access the selected file"
        case .extractionFailed:
            return "Failed to extract audio package"
        case .invalidPackage:
            return "Invalid audio package format"
        }
    }
}


