import SwiftUI
import UniformTypeIdentifiers
import os.log
import UIKit

struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    @AppStorage("fontSize") private var fontSize: Double = 20
    @AppStorage("colorScheme") private var colorScheme: ColorScheme = .system
    @AppStorage("wrapInterlinear") private var wrapInterlinear: Bool = false

    @State private var showingDatabaseImporter = false
    @State private var showingImportAlert = false
    @State private var importAlertMessage = ""
    @State private var showingRestartConfirmation = false
    @State private var pendingRestartAction: (() -> Void)?
    @StateObject private var databaseImporter = ExternalDatabaseImporter.shared
    @State private var documentPickerPresented = false
    @State private var showingManualDBImport = false
    @State private var manualDBPath = "perseus_texts_full.db.zip"
    @AppStorage("externalDatabaseName") private var externalDatabaseName = ""
    
    enum ColorScheme: String, CaseIterable {
        case system = "System"
        case light = "Light"
        case dark = "Dark"
        case inverted = "Inverted"
        
        var displayName: String { rawValue }
    }
    
    private var databaseSource: String {
        if !externalDatabaseName.isEmpty {
            return externalDatabaseName
        } else {
            return "Bundled"
        }
    }
    
    var body: some View {
        NavigationView {
            Form {
                // Display Section - only font size and color scheme like Android
                Section(header: Text("Display")) {
                    // Font Size
                    VStack(alignment: .leading) {
                        Text("Font Size: \(Int(fontSize))pt")
                            .font(.caption)
                            .foregroundColor(.secondary)

                        Slider(value: $fontSize, in: 20...40, step: 1)
                    }

                    // Color scheme
                    Picker("Color Scheme", selection: $colorScheme) {
                        ForEach(ColorScheme.allCases, id: \.self) { scheme in
                            Text(scheme.displayName).tag(scheme)
                        }
                    }

                    // Wrap Interlinear Text
                    Toggle("Wrap Interlinear Text", isOn: $wrapInterlinear)
                }

                // Languages Section
                Section(header: Text("Languages")) {
                    NavigationLink(destination: ManageLanguagesView()) {
                        HStack {
                            Image(systemName: "globe")
                            Text("Manage Languages")
                        }
                    }
                }

                // Database Section
                Section(header: Text("Database")) {
                    HStack {
                        Text("Database Source")
                        Spacer()
                        Text(databaseSource)
                            .foregroundColor(.secondary)
                    }
                    
                    Menu {
                        Button(action: {
                            documentPickerPresented = true
                        }) {
                            Label("Import from Files", systemImage: "doc.badge.plus")
                        }
                        
                        Button(action: {
                            showingManualDBImport = true
                        }) {
                            Label("Import from Path", systemImage: "doc.text")
                        }
                    } label: {
                        HStack {
                            Image(systemName: "square.and.arrow.down")
                            Text("Import External Database")
                            Spacer()
                        }
                    }
                    
                    if databaseImporter.isImporting {
                        VStack(alignment: .leading, spacing: 8) {
                            Text(databaseImporter.importStatus)
                                .font(.caption)
                                .foregroundColor(.secondary)

                            ProgressView(value: databaseImporter.importProgress)
                        }
                    }

                    // Show revert option only if using external database
                    if !externalDatabaseName.isEmpty {
                        Button(action: {
                            revertToBundledDatabase()
                        }) {
                            HStack {
                                Image(systemName: "arrow.uturn.backward")
                                Text("Revert to Bundled Database")
                                Spacer()
                            }
                            .foregroundColor(.red)
                        }
                    }

                    NavigationLink(destination: UserDictionaryManagementView()) {
                        HStack {
                            Image(systemName: "book.closed")
                            Text("Manage User Dictionaries")
                        }
                    }
                }
                
                // Audio Section
                Section(header: Text("Audio")) {
                    NavigationLink(destination: AudioManagementView()) {
                        HStack {
                            Image(systemName: "speaker.wave.2")
                            Text("Manage Audio Packages")
                        }
                    }
                }

                // About Section
                Section(header: Text("About")) {
                    HStack {
                        Text("Version")
                        Spacer()
                        Text("0.8.53")
                            .foregroundColor(.secondary)
                    }

                    NavigationLink(destination: LicenseView()) {
                        Text("Licenses & Credits")
                    }

                    Link(destination: URL(string: "https://github.com/threedlite/classicsviewer")!) {
                        Text("View on GitHub")
                    }
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.large)
            .sheet(isPresented: $documentPickerPresented) {
                DatabaseDocumentPicker(onPick: { url in
                    handleDatabaseImportFromURL(url)
                })
            }
            .alert("Database Import", isPresented: $showingImportAlert) {
                Button("OK") { }
            } message: {
                Text(importAlertMessage)
            }
            .alert("Restart Required", isPresented: $showingRestartConfirmation) {
                Button("OK") {
                    // Execute the pending restart action
                    pendingRestartAction?()
                }
            } message: {
                Text("The app needs to restart to apply the database changes. Please relaunch the app after it closes.")
            }
            .sheet(isPresented: $showingManualDBImport) {
                NavigationView {
                    VStack(alignment: .leading, spacing: 20) {
                        Text("Manual Database Import")
                            .font(.headline)
                            .padding(.top)
                        
                        Text("Enter the filename (relative to Documents folder):")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        
                        TextField("Database file path", text: $manualDBPath)
                            .textFieldStyle(RoundedBorderTextFieldStyle())
                            .autocapitalization(.none)
                            .disableAutocorrection(true)
                        
                        Text("Available databases in Documents:")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text("• perseus_texts_full.db.zip (Full database)")
                                .font(.caption2)
                                .foregroundColor(.blue)
                            Text("• perseus_texts.db.zip (Sample database)")
                                .font(.caption2)
                                .foregroundColor(.blue)
                        }
                        .padding(.horizontal)
                        
                        Spacer()
                    }
                    .padding()
                    .navigationBarTitle("Import from Path", displayMode: .inline)
                    .navigationBarItems(
                        leading: Button("Cancel") {
                            showingManualDBImport = false
                        },
                        trailing: Button("Import") {
                            showingManualDBImport = false
                            handleManualDatabaseImport()
                        }
                        .disabled(manualDBPath.isEmpty)
                    )
                }
            }
        }
    }
    
    private func handleManualDatabaseImport() {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")
        logger.info("Manual database import from path: \(manualDBPath)")
        
        // Handle relative paths from Documents directory
        let url: URL
        if manualDBPath.starts(with: "/") {
            // Absolute path
            url = URL(fileURLWithPath: manualDBPath)
        } else {
            // Relative path - assume relative to Documents directory
            let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
            url = documentsPath.appendingPathComponent(manualDBPath)
        }
        
        logger.info("Full path to import: \(url.path)")
        
        // Check if file exists
        guard FileManager.default.fileExists(atPath: url.path) else {
            importAlertMessage = "File not found at path: \(url.path)"
            showingImportAlert = true
            return
        }
        
        // Check if it's a database file
        guard url.pathExtension.lowercased() == "zip" || url.pathExtension.lowercased() == "db" else {
            importAlertMessage = "File must be a .db or .zip database file"
            showingImportAlert = true
            return
        }
        
        // Use the existing import function
        handleDatabaseImportFromURL(url)
    }
    
    private func revertToBundledDatabase() {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseRevert")
        logger.info("Reverting to bundled database")

        // Delete the external database
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let databasePath = documentsPath.appendingPathComponent("perseus_texts.db")

        do {
            // Remove the external database file
            if FileManager.default.fileExists(atPath: databasePath.path) {
                try FileManager.default.removeItem(at: databasePath)
                logger.info("External database removed successfully")
            }

            // Clear the external database name
            UserDefaults.standard.removeObject(forKey: "externalDatabaseName")
            externalDatabaseName = ""

            // Show restart confirmation
            pendingRestartAction = {
                exit(0)
            }
            showingRestartConfirmation = true
        } catch {
            logger.error("Failed to revert to bundled database: \(error)")
            importAlertMessage = "Failed to revert: \(error.localizedDescription)"
            showingImportAlert = true
        }
    }

    private func handleDatabaseImportFromURL(_ url: URL) {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")
        logger.info("handleDatabaseImportFromURL called with: \(url.path)")
        
        Task {
            do {
                logger.info("Starting database import task")
                try await databaseImporter.importDatabase(from: url)
                
                // Save the filename (without path) for display
                let filename = url.lastPathComponent
                
                await MainActor.run {
                    // Store the external database filename
                    externalDatabaseName = filename

                    // Show restart confirmation
                    pendingRestartAction = {
                        exit(0)
                    }
                    showingRestartConfirmation = true
                }
            } catch {
                logger.error("Import failed with error: \(error, privacy: .public)")
                await MainActor.run {
                    importAlertMessage = "Import failed: \(error.localizedDescription)"
                    showingImportAlert = true
                }
            }
        }
    }
}


struct AboutView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // App Icon and Name
                VStack(spacing: 16) {
                    Image(systemName: "books.vertical.fill")
                        .font(.system(size: 80))
                        .foregroundColor(.blue)
                    
                    Text("Classics Viewer")
                        .font(.largeTitle)
                        .fontWeight(.bold)
                    
                    Text("Read classical Greek and Latin texts offline")
                        .font(.body)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 30)
                
                // Description
                VStack(alignment: .leading, spacing: 12) {
                    Text("About")
                        .font(.headline)
                    
                    Text("Classics Viewer provides offline access to the Perseus Digital Library collection of classical Greek and Latin texts. Read works by Homer, Plato, Virgil, and many other ancient authors with integrated translations and search capabilities.")
                        .font(.body)
                }
                .padding(.horizontal)
                
                // Features
                VStack(alignment: .leading, spacing: 12) {
                    Text("Features")
                        .font(.headline)
                    
                    FeatureRow(icon: "book.fill", text: "100+ Greek and Latin authors")
                    FeatureRow(icon: "globe", text: "Integrated English translations")
                    FeatureRow(icon: "magnifyingglass", text: "Full-text search with lemmatization")
                    FeatureRow(icon: "textformat", text: "Customizable reading experience")
                    FeatureRow(icon: "wifi.slash", text: "100% offline functionality")
                }
                .padding(.horizontal)
                
                // Credits
                VStack(alignment: .leading, spacing: 12) {
                    Text("Credits")
                        .font(.headline)
                    
                    Text("Texts provided by the Perseus Digital Library at Tufts University.")
                        .font(.body)
                    
                    Text("Morphological data from Wiktionary.")
                        .font(.body)
                }
                .padding(.horizontal)
                .padding(.bottom, 40)
            }
        }
        .navigationTitle("About")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct FeatureRow: View {
    let icon: String
    let text: String
    
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundColor(.blue)
                .frame(width: 24)
            
            Text(text)
                .font(.body)
        }
    }
}

struct SettingsView_Previews: PreviewProvider {
    static var previews: some View {
        SettingsView()
            .environmentObject(AppState())
    }
}

// MARK: - Document Picker for Database Import

struct DatabaseDocumentPicker: UIViewControllerRepresentable {
    let onPick: (URL) -> Void
    
    func makeUIViewController(context: Context) -> UIDocumentPickerViewController {
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")
        logger.info("Creating UIDocumentPickerViewController")
        
        // Support both .db and .zip files
        let types: [UTType] = [
            UTType(filenameExtension: "db") ?? .database,
            UTType.zip
        ]
        
        let picker = UIDocumentPickerViewController(forOpeningContentTypes: types, asCopy: true)
        picker.delegate = context.coordinator
        picker.allowsMultipleSelection = false
        picker.shouldShowFileExtensions = true
        
        return picker
    }
    
    func updateUIViewController(_ uiViewController: UIDocumentPickerViewController, context: Context) {
        // No updates needed
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }
    
    class Coordinator: NSObject, UIDocumentPickerDelegate {
        let parent: DatabaseDocumentPicker
        let logger = Logger(subsystem: "com.classicsviewer.app", category: "DatabaseImport")
        
        init(_ parent: DatabaseDocumentPicker) {
            self.parent = parent
        }
        
        func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
            logger.info("Document picker didPickDocumentsAt called")
            guard let url = urls.first else {
                logger.error("No URL in picked documents")
                return
            }
            
            logger.info("Picked document URL: \(url.path)")
            logger.info("File exists: \(FileManager.default.fileExists(atPath: url.path))")
            
            // Since we're using asCopy: true, the file is already copied to our sandbox
            // We can directly use it without security scoped resource access
            parent.onPick(url)
        }
        
        func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) {
            logger.info("Document picker was cancelled")
        }
    }
}