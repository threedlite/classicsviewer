import SwiftUI
import UniformTypeIdentifiers
import os.log
import SwiftCSV

struct UserDictionaryManagementView: View {
    @State private var packages: [UserDictionaryPackage] = []
    @State private var isImporting = false
    @State private var showingImportPicker = false
    @State private var showingManualImport = false
    @State private var manualImportPath = ""
    @State private var showingAlert = false
    @State private var alertMessage = ""
    @State private var importProgress: Double = 0
    @State private var importStatus = ""
    @State private var showingDeleteConfirmation: UserDictionaryPackage? = nil
    
    private let userDictDAO = UserDictionaryDAO()
    private let logger = Logger(subsystem: "com.classicsviewer.app", category: "UserDictionary")
    
    var body: some View {
        List {
            if packages.isEmpty && !isImporting {
                VStack(spacing: 20) {
                    Image(systemName: "book.closed")
                        .font(.system(size: 60))
                        .foregroundColor(.gray)
                    
                    Text("No User Dictionaries")
                        .font(.title2)
                        .foregroundColor(.secondary)
                    
                    Text("Import custom dictionary packages to extend the built-in dictionary")
                        .font(.body)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                    
                    Button(action: {
                        showImportMenu()
                    }) {
                        Label("Import Dictionary", systemImage: "plus.circle.fill")
                            .font(.body)
                    }
                    .buttonStyle(.borderedProminent)
                }
                .frame(maxWidth: .infinity, minHeight: 400)
                .listRowBackground(Color.clear)
                .listRowInsets(EdgeInsets())
            } else {
                // Package list
                ForEach(packages) { package in
                    DictionaryPackageRow(
                        package: package,
                        isSelected: package.isEnabled,
                        onSelect: {
                            Task {
                                await selectPackage(package)
                            }
                        },
                        onDelete: {
                            showingDeleteConfirmation = package
                        }
                    )
                }
            }
            
            // Import progress
            if isImporting {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Importing Dictionary...")
                        .font(.headline)
                    
                    Text(importStatus)
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    ProgressView(value: importProgress)
                        .progressViewStyle(LinearProgressViewStyle())
                }
                .padding()
                .background(Color.gray.opacity(0.1))
                .cornerRadius(10)
            }
        }
        .navigationTitle("User Dictionaries")
        .navigationBarTitleDisplayMode(.large)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Menu {
                    Button(action: {
                        showingImportPicker = true
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
        .sheet(isPresented: $showingImportPicker) {
            DictionaryDocumentPicker { url in
                Task {
                    await importDictionary(from: url)
                }
            }
        }
        .sheet(isPresented: $showingManualImport) {
            ManualDictionaryImportView(path: $manualImportPath) {
                Task {
                    await importDictionaryFromPath(manualImportPath)
                }
            }
        }
        .alert("Dictionary Import", isPresented: $showingAlert) {
            Button("OK") { }
        } message: {
            Text(alertMessage)
        }
        .alert("Delete Dictionary Package", isPresented: .constant(showingDeleteConfirmation != nil)) {
            Button("Cancel", role: .cancel) {
                showingDeleteConfirmation = nil
            }
            Button("Delete", role: .destructive) {
                if let package = showingDeleteConfirmation {
                    Task {
                        await deletePackage(package)
                    }
                }
                showingDeleteConfirmation = nil
            }
        } message: {
            if let package = showingDeleteConfirmation {
                Text("Are you sure you want to delete '\(package.displayName)'? This action cannot be undone.")
            }
        }
        .task {
            await loadPackages()
        }
    }
    
    private func showImportMenu() {
        // On iOS, we need to use the toolbar menu instead
        showingImportPicker = true
    }
    
    private func loadPackages() async {
        do {
            packages = try await userDictDAO.getPackages(language: nil)
            logger.info("Loaded \(packages.count) dictionary packages")
        } catch {
            logger.error("Failed to load packages: \(error)")
        }
    }
    
    private func importDictionary(from url: URL) async {
        await MainActor.run {
            isImporting = true
            importProgress = 0.1
            importStatus = "Reading ZIP file..."
        }
        
        do {
            // Read ZIP file
            let data = try Data(contentsOf: url)
            let fileName = url.lastPathComponent  // Get the actual filename
            
            await MainActor.run {
                importProgress = 0.2
                importStatus = "Extracting contents..."
            }
            
            // Extract and parse ZIP contents
            var (metadata, lemmas, mappings) = try await extractDictionaryZip(data)
            
            // Override package_name with actual filename and display name
            metadata["package_name"] = fileName
            metadata["display_name"] = fileName.replacingOccurrences(of: ".zip", with: "").replacingOccurrences(of: "_", with: " ").capitalized
            
            await MainActor.run {
                importProgress = 0.5
                importStatus = "Importing \(lemmas.count) lemmas..."
            }
            
            // Check if a package with the same name already exists
            let existingPackage = packages.first { $0.packageName == fileName }
            if let existing = existingPackage {
                // Delete the existing package (this will cascade delete lemmas and mappings)
                try await userDictDAO.deletePackage(packageId: existing.id!)
                logger.info("Replacing existing dictionary package: \(fileName)")
            }
            
            // Import to database
            let packageId = try await userDictDAO.importDictionaryPackage(
                metadata: metadata,
                lemmas: lemmas,
                mappings: mappings
            )
            
            // Disable all other packages and enable the new one (radio button behavior)
            for pkg in packages where pkg.isEnabled && pkg.packageName != fileName {
                try await userDictDAO.setPackageEnabled(packageId: pkg.id!, enabled: false)
            }
            try await userDictDAO.setPackageEnabled(packageId: packageId, enabled: true)
            
            await MainActor.run {
                importProgress = 1.0
                importStatus = "Import complete!"
            }
            
            // Reload packages
            await loadPackages()
            
            await MainActor.run {
                isImporting = false
                alertMessage = "Successfully imported dictionary package with \(lemmas.count) entries"
                showingAlert = true
            }
            
        } catch {
            logger.error("Import failed: \(error)")
            await MainActor.run {
                isImporting = false
                alertMessage = "Import failed: \(error.localizedDescription)"
                showingAlert = true
            }
        }
    }
    
    private func importDictionaryFromPath(_ path: String) async {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let url = documentsPath.appendingPathComponent(path)
        
        guard FileManager.default.fileExists(atPath: url.path) else {
            await MainActor.run {
                alertMessage = "File not found at path: \(path)"
                showingAlert = true
            }
            return
        }
        
        await importDictionary(from: url)
    }
    
    private func extractDictionaryZip(_ data: Data) async throws -> ([String: Any], [[String: Any]], [[String: Any]]?) {
        // Extract ZIP and parse CSV files
        let tempDir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
        defer {
            try? FileManager.default.removeItem(at: tempDir)
        }
        
        // Save ZIP to temp file
        let zipPath = tempDir.appendingPathComponent("dict.zip")
        try data.write(to: zipPath)
        
        // Extract ZIP
        try ZIPHandler.extractAll(from: zipPath, to: tempDir)
        
        // Parse dictionary.csv
        let dictPath = tempDir.appendingPathComponent("dictionary.csv")
        guard FileManager.default.fileExists(atPath: dictPath.path) else {
            throw NSError(domain: "DictionaryImport", code: 1, userInfo: [NSLocalizedDescriptionKey: "Missing dictionary.csv in ZIP file"])
        }
        
        let dictCSV = try String(contentsOf: dictPath, encoding: .utf8)
        let lemmas = try parseDictionaryCSV(dictCSV)
        
        // Parse morphology.csv (optional)
        var mappings: [[String: Any]]? = nil
        let morphPath = tempDir.appendingPathComponent("morphology.csv")
        if FileManager.default.fileExists(atPath: morphPath.path) {
            let morphCSV = try String(contentsOf: morphPath, encoding: .utf8)
            mappings = try parseMorphologyCSV(morphCSV)
        }
        
        // Extract language from first lemma or default to greek
        let language = (lemmas.first?["language"] as? String) ?? "greek"
        
        // Create metadata from the parsed data
        let metadata: [String: Any] = [
            "package_name": "user_dict_\(Date().timeIntervalSince1970)",
            "display_name": "User Dictionary",
            "description": "Imported dictionary with \(lemmas.count) entries",
            "language": language,
            "source_info": "CSV Import"
        ]
        
        return (metadata, lemmas, mappings)
    }
    
    private func parseDictionaryCSV(_ csv: String) throws -> [[String: Any]] {
        var result: [[String: Any]] = []
        
        // Use SwiftCSV to parse
        let parsedCSV = try CSV<Named>(string: csv)
        
        // Check required columns
        guard parsedCSV.header.contains("lemma"),
              parsedCSV.header.contains("language"),
              parsedCSV.header.contains("definition") else {
            throw NSError(domain: "DictionaryImport", code: 2, userInfo: [NSLocalizedDescriptionKey: "Invalid CSV header - missing required columns"])
        }
        
        // Parse each row
        for row in parsedCSV.rows {
            guard let lemma = row["lemma"],
                  let language = row["language"],
                  let definition = row["definition"],
                  !lemma.isEmpty,
                  !definition.isEmpty else {
                continue
            }
            
            var entry: [String: Any] = [
                "lemma": lemma,
                "language": language.lowercased(),
                "definition_plain": definition
            ]
            
            if let htmlDef = row["html_definition"], !htmlDef.isEmpty {
                entry["definition_html"] = htmlDef
            }
            
            if let source = row["source_name"], !source.isEmpty {
                entry["source_name"] = source
            } else {
                entry["source_name"] = "User Import"
            }
            
            // Add normalized form for Greek
            if language.lowercased() == "greek" {
                entry["lemma_normalized_ultra"] = GreekNormalizer.normalize(lemma)
            }
            
            entry["import_file_name"] = "user_import.csv"
            
            result.append(entry)
        }
        
        return result
    }
    
    private func parseMorphologyCSV(_ csv: String) throws -> [[String: Any]] {
        var result: [[String: Any]] = []
        
        // Use SwiftCSV to parse
        let parsedCSV = try CSV<Named>(string: csv)
        
        // Check required columns
        guard parsedCSV.header.contains("word_form"),
              parsedCSV.header.contains("lemma"),
              parsedCSV.header.contains("language") else {
            throw NSError(domain: "DictionaryImport", code: 3, userInfo: [NSLocalizedDescriptionKey: "Invalid morphology CSV header - missing required columns"])
        }
        
        // Parse each row
        for row in parsedCSV.rows {
            guard let wordForm = row["word_form"],
                  let lemma = row["lemma"],
                  let language = row["language"],
                  !wordForm.isEmpty,
                  !lemma.isEmpty else {
                continue
            }
            
            var entry: [String: Any] = [
                "inflected_form": wordForm,
                "lemma": lemma,
                "language": language.lowercased()
            ]
            
            if let source = row["source_name"], !source.isEmpty {
                entry["source"] = source
            } else {
                entry["source"] = "User Import"
            }
            
            result.append(entry)
        }
        
        return result
    }
    
    private func selectPackage(_ package: UserDictionaryPackage) async {
        do {
            // If package is already enabled, disable it
            if package.isEnabled {
                try await userDictDAO.setPackageEnabled(packageId: package.id!, enabled: false)
            } else {
                // Disable all other packages first (only one can be active)
                for pkg in packages where pkg.id != package.id && pkg.isEnabled {
                    try await userDictDAO.setPackageEnabled(packageId: pkg.id!, enabled: false)
                }
                // Enable the selected package
                try await userDictDAO.setPackageEnabled(packageId: package.id!, enabled: true)
            }
            await loadPackages()
        } catch {
            logger.error("Failed to select package: \(error)")
        }
    }
    
    private func deletePackage(_ package: UserDictionaryPackage) async {
        do {
            try await userDictDAO.deletePackage(packageId: package.id!)
            await loadPackages()
        } catch {
            logger.error("Failed to delete package: \(error)")
        }
    }
}

struct DictionaryPackageRow: View {
    let package: UserDictionaryPackage
    let isSelected: Bool
    let onSelect: () -> Void
    let onDelete: () -> Void
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(package.displayName)
                        .font(.headline)
                    
                    if let description = package.description {
                        Text(description)
                            .font(.caption)
                            .foregroundColor(.secondary)
                            .lineLimit(2)
                    }
                }
                
                Spacer()

                // Delete button
                Button(action: onDelete) {
                    Image(systemName: "trash")
                        .foregroundColor(.red)
                        .font(.body)
                }
                .padding(.trailing, 8)

                // Radio button
                Button(action: onSelect) {
                    Image(systemName: isSelected ? "largecircle.fill.circle" : "circle")
                        .foregroundColor(isSelected ? .blue : .gray)
                        .font(.title2)
                }
                .buttonStyle(PlainButtonStyle())
            }
            
            HStack {
                Label(package.packageName, systemImage: "doc.zipper")
                    .font(.caption)
                    .foregroundColor(.blue)
                
                if let lemmaCount = package.lemmaCount {
                    Label("\(lemmaCount) entries", systemImage: "text.book.closed")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                if let fileSize = package.fileSize {
                    Label(formatFileSize(fileSize), systemImage: "doc")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
        .padding(.vertical, 8)
        .swipeActions(edge: .trailing) {
            Button(role: .destructive) {
                onDelete()
            } label: {
                Label("Delete", systemImage: "trash")
            }
        }
    }
    
    private func formatFileSize(_ bytes: Int) -> String {
        let formatter = ByteCountFormatter()
        formatter.countStyle = .file
        return formatter.string(fromByteCount: Int64(bytes))
    }
}

struct ManualDictionaryImportView: View {
    @Binding var path: String
    let onImport: () -> Void
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Manual Dictionary Import")
                    .font(.headline)
                    .padding(.top)
                
                Text("Enter the filename (relative to Documents folder):")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                TextField("Dictionary ZIP file path", text: $path)
                    .textFieldStyle(RoundedBorderTextFieldStyle())
                    .autocapitalization(.none)
                    .disableAutocorrection(true)
                
                Text("Example: custom_greek_dictionary.zip")
                    .font(.caption2)
                    .foregroundColor(.blue)
                    .padding(.horizontal)
                
                Spacer()
            }
            .padding()
            .navigationBarTitle("Import from Path", displayMode: .inline)
            .navigationBarItems(
                leading: Button("Cancel") {
                    dismiss()
                },
                trailing: Button("Import") {
                    dismiss()
                    onImport()
                }
                .disabled(path.isEmpty)
            )
        }
    }
}

struct DictionaryDocumentPicker: UIViewControllerRepresentable {
    let onPick: (URL) -> Void
    
    func makeUIViewController(context: Context) -> UIDocumentPickerViewController {
        let types: [UTType] = [.zip]
        let picker = UIDocumentPickerViewController(forOpeningContentTypes: types, asCopy: true)
        picker.delegate = context.coordinator
        picker.allowsMultipleSelection = false
        picker.shouldShowFileExtensions = true
        return picker
    }
    
    func updateUIViewController(_ uiViewController: UIDocumentPickerViewController, context: Context) {}
    
    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }
    
    class Coordinator: NSObject, UIDocumentPickerDelegate {
        let parent: DictionaryDocumentPicker
        
        init(_ parent: DictionaryDocumentPicker) {
            self.parent = parent
        }
        
        func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
            guard let url = urls.first else { return }
            parent.onPick(url)
        }
        
        func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) {}
    }
}