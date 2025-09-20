import SwiftUI
import UniformTypeIdentifiers

struct DatabaseManagementView: View {
    @StateObject private var importer = ExternalDatabaseImporter.shared
    @State private var showingFilePicker = false
    @State private var showingValidationReport = false
    @State private var showingRevertConfirmation = false
    @State private var errorMessage: String?
    @State private var showingError = false
    @State private var currentDatabaseInfo: ExternalDatabaseImporter.DatabaseInfo?
    
    var body: some View {
        NavigationView {
            List {
                // Current Database Section
                Section(header: Text("Current Database")) {
                    if let info = currentDatabaseInfo {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text("Size:")
                                    .fontWeight(.medium)
                                Spacer()
                                Text(info.sizeFormatted)
                                    .foregroundColor(.secondary)
                            }
                            
                            HStack {
                                Text("Last Modified:")
                                    .fontWeight(.medium)
                                Spacer()
                                Text(info.lastModified, style: .date)
                                    .foregroundColor(.secondary)
                            }
                            
                            if let report = importer.validationReport {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("Database Statistics")
                                        .font(.headline)
                                        .padding(.top, 8)
                                    
                                    HStack {
                                        Label("\(report.authorCount) Authors", systemImage: "person.2")
                                        Spacer()
                                        Label("\(report.bookCount) Books", systemImage: "book")
                                    }
                                    .font(.caption)
                                    
                                    HStack {
                                        Label("\(report.lineCount) Lines", systemImage: "text.alignleft")
                                        Spacer()
                                        Label("\(report.tableCount) Tables", systemImage: "tablecells")
                                    }
                                    .font(.caption)
                                }
                            }
                        }
                        .padding(.vertical, 4)
                    } else {
                        Text("No database found")
                            .foregroundColor(.secondary)
                    }
                    
                    Button(action: validateCurrentDatabase) {
                        Label("Validate Database", systemImage: "checkmark.shield")
                    }
                }
                
                // Import Section
                Section(header: Text("Import Database")) {
                    Button(action: { showingFilePicker = true }) {
                        Label("Import from Files", systemImage: "doc.badge.plus")
                    }
                    .disabled(importer.isImporting)
                    
                    if importer.isImporting {
                        VStack(alignment: .leading, spacing: 8) {
                            Text(importer.importStatus)
                                .font(.caption)
                                .foregroundColor(.secondary)
                            
                            ProgressView(value: importer.importProgress)
                                .progressViewStyle(.linear)
                        }
                        .padding(.vertical, 4)
                    }
                }
                
                // Restore Section
                Section(header: Text("Restore")) {
                    Button(action: { showingRevertConfirmation = true }) {
                        Label("Revert to Bundled Database", systemImage: "arrow.counterclockwise")
                            .foregroundColor(.orange)
                    }
                    .disabled(importer.isImporting)
                }
                
                // Validation Report Section
                if let report = importer.validationReport {
                    Section(header: Text("Last Validation Report")) {
                        if report.isValid {
                            HStack {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundColor(.green)
                                Text("Database is valid")
                                    .foregroundColor(.green)
                            }
                        } else {
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Image(systemName: "exclamationmark.triangle.fill")
                                        .foregroundColor(.red)
                                    Text("Validation Issues")
                                        .foregroundColor(.red)
                                        .fontWeight(.medium)
                                }
                                
                                ForEach(report.issues, id: \.self) { issue in
                                    Text("• \(issue)")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                        .padding(.leading, 24)
                                }
                            }
                            .padding(.vertical, 4)
                        }
                        
                        Button("View Full Report") {
                            showingValidationReport = true
                        }
                        .font(.caption)
                    }
                }
            }
            .navigationTitle("Database Management")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        // Dismiss view
                    }
                }
            }
        }
        .fileImporter(
            isPresented: $showingFilePicker,
            allowedContentTypes: [
                UTType(filenameExtension: "db") ?? .database,
                UTType(filenameExtension: "zip") ?? .archive,
                UTType.zip,
                UTType.archive,
                UTType.data
            ],
            allowsMultipleSelection: false,
            onCompletion: handleFileImport
        )
        .alert("Revert to Bundled Database", isPresented: $showingRevertConfirmation) {
            Button("Cancel", role: .cancel) {}
            Button("Revert", role: .destructive) {
                revertToBundledDatabase()
            }
        } message: {
            Text("This will replace the current database with the original bundled database. The app will need to restart after this change. Continue?")
        }
        .alert("Database Import Failed", isPresented: $showingError) {
            Button("OK") {}
            Button("Copy Error Details") {
                UIPasteboard.general.string = errorMessage ?? "Unknown error"
            }
        } message: {
            // Use ScrollView for long error messages with schema details
            if let message = errorMessage {
                Text(message)
                    .font(.caption)
                    .fixedSize(horizontal: false, vertical: true)
            } else {
                Text("An unknown error occurred")
            }
        }
        .sheet(isPresented: $showingValidationReport) {
            ValidationReportView(report: importer.validationReport)
        }
        .onAppear {
            loadDatabaseInfo()
        }
    }
    
    private func loadDatabaseInfo() {
        currentDatabaseInfo = importer.getCurrentDatabaseInfo()
    }
    
    private func validateCurrentDatabase() {
        Task {
            do {
                let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
                let databasePath = documentsPath.appendingPathComponent("perseus_texts.db")
                
                let validator = DatabaseValidator()
                let report = try await validator.generateValidationReport(for: databasePath)
                
                await MainActor.run {
                    importer.validationReport = report
                    if !report.isValid {
                        showingValidationReport = true
                    }
                }
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    showingError = true
                }
            }
        }
    }
    
    private func handleFileImport(_ result: Result<[URL], Error>) {
        switch result {
        case .success(let urls):
            guard let url = urls.first else { return }
            
            Task {
                do {
                    try await importer.importDatabase(from: url)
                    await MainActor.run {
                        loadDatabaseInfo()
                    }
                } catch {
                    await MainActor.run {
                        // Show detailed error message for validation failures
                        if let importError = error as? ExternalDatabaseImporter.ImportError,
                           case .validationFailed(let details) = importError {
                            errorMessage = details
                        } else {
                            errorMessage = error.localizedDescription
                        }
                        showingError = true
                    }
                }
            }
            
        case .failure(let error):
            errorMessage = error.localizedDescription
            showingError = true
        }
    }
    
    private func revertToBundledDatabase() {
        Task {
            do {
                try await importer.revertToBundledDatabase()
                // App will restart automatically
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                    showingError = true
                }
            }
        }
    }
}

// MARK: - Validation Report View

struct ValidationReportView: View {
    let report: DatabaseValidator.ValidationReport?
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationView {
            List {
                if let report = report {
                    Section(header: Text("Validation Status")) {
                        HStack {
                            Text("Status:")
                                .fontWeight(.medium)
                            Spacer()
                            if report.isValid {
                                Label("Valid", systemImage: "checkmark.circle.fill")
                                    .foregroundColor(.green)
                            } else {
                                Label("Invalid", systemImage: "xmark.circle.fill")
                                    .foregroundColor(.red)
                            }
                        }
                    }
                    
                    Section(header: Text("Database Statistics")) {
                        StatisticRow(label: "Database Size", value: formatBytes(report.databaseSize))
                        StatisticRow(label: "Tables", value: "\(report.tableCount)")
                        StatisticRow(label: "Authors", value: "\(report.authorCount)")
                        StatisticRow(label: "Books", value: "\(report.bookCount)")
                        StatisticRow(label: "Lines", value: "\(report.lineCount)")
                    }
                    
                    if !report.issues.isEmpty {
                        Section(header: Text("Schema Validation Issues (\(report.issues.count))")) {
                            ForEach(Array(report.issues.enumerated()), id: \.offset) { index, issue in
                                VStack(alignment: .leading, spacing: 4) {
                                    HStack(alignment: .top) {
                                        Text("\(index + 1).")
                                            .font(.caption2)
                                            .foregroundColor(.secondary)
                                            .frame(width: 20)
                                        
                                        VStack(alignment: .leading, spacing: 2) {
                                            Text(formatIssueTitle(issue))
                                                .font(.caption)
                                                .fontWeight(.medium)
                                                .foregroundColor(.red)
                                            
                                            Text(formatIssueDetail(issue))
                                                .font(.caption2)
                                                .foregroundColor(.secondary)
                                                .fixedSize(horizontal: false, vertical: true)
                                        }
                                        
                                        Spacer()
                                        
                                        Image(systemName: getIssueIcon(issue))
                                            .foregroundColor(getIssueColor(issue))
                                            .font(.caption)
                                    }
                                    
                                    if index < report.issues.count - 1 {
                                        Divider()
                                    }
                                }
                                .padding(.vertical, 2)
                            }
                            
                            Button(action: {
                                let issueText = report.issues.enumerated().map { index, issue in
                                    "\(index + 1). \(issue)"
                                }.joined(separator: "\n\n")
                                UIPasteboard.general.string = issueText
                            }) {
                                Label("Copy All Issues", systemImage: "doc.on.doc")
                                    .font(.caption)
                                    .foregroundColor(.blue)
                            }
                            .padding(.top, 8)
                        }
                    }
                    
                    Section(header: Text("Expected Schema")) {
                        Text("The database must contain the following tables:")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        
                        ForEach(expectedTables, id: \.self) { table in
                            HStack {
                                Image(systemName: "tablecells")
                                    .foregroundColor(.blue)
                                Text(table)
                                    .font(.system(.caption, design: .monospaced))
                            }
                        }
                    }
                } else {
                    Text("No validation report available")
                        .foregroundColor(.secondary)
                }
            }
            .navigationTitle("Validation Report")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
        }
    }
    
    private var expectedTables: [String] {
        ["authors", "books", "lines", "translation_segments", "translation_lookup",
         "words", "lemmas", "morphology", "dictionary_entries", "author_stats",
         "book_sections", "drama_speakers"]
    }
    
    private func formatBytes(_ bytes: Int64) -> String {
        let formatter = ByteCountFormatter()
        formatter.countStyle = .file
        return formatter.string(fromByteCount: bytes)
    }
    
    private func formatIssueTitle(_ issue: String) -> String {
        // Extract the main problem from the issue
        if issue.contains("Missing required table") {
            return "Missing Table"
        } else if issue.contains("Missing required column") {
            return "Missing Column"
        } else if issue.contains("Type mismatch") {
            return "Type Mismatch"
        } else if issue.contains("NOT NULL mismatch") {
            return "Constraint Mismatch"
        } else if issue.contains("Primary key mismatch") {
            return "Primary Key Issue"
        } else if issue.contains("Column count mismatch") {
            return "Column Count Error"
        } else if issue.contains("Unexpected extra column") {
            return "Extra Column"
        } else if issue.contains("No authors found") || issue.contains("No books found") {
            return "Empty Table"
        } else if issue.contains("integrity check failed") {
            return "Integrity Check Failed"
        }
        return "Schema Issue"
    }
    
    private func formatIssueDetail(_ issue: String) -> String {
        // Return the full issue text but formatted better
        return issue
            .replacingOccurrences(of: "Table '", with: "")
            .replacingOccurrences(of: "', Column '", with: " → ")
            .replacingOccurrences(of: "':", with: ":")
            .replacingOccurrences(of: "Missing required table:", with: "")
            .replacingOccurrences(of: "Missing required column", with: "Column missing")
    }
    
    private func getIssueIcon(_ issue: String) -> String {
        if issue.contains("Missing required table") {
            return "tablecells.badge.ellipsis"
        } else if issue.contains("column") || issue.contains("Column") {
            return "rectangle.badge.xmark"
        } else if issue.contains("Type mismatch") {
            return "textformat.size"
        } else if issue.contains("NOT NULL") || issue.contains("constraint") {
            return "exclamationmark.shield"
        } else if issue.contains("Primary key") {
            return "key"
        } else if issue.contains("empty") || issue.contains("No ") {
            return "tray"
        }
        return "exclamationmark.triangle"
    }
    
    private func getIssueColor(_ issue: String) -> Color {
        if issue.contains("Missing required table") {
            return .red
        } else if issue.contains("Missing required column") {
            return .orange
        } else if issue.contains("Type mismatch") {
            return .purple
        } else if issue.contains("NOT NULL") || issue.contains("Primary key") {
            return .pink
        } else if issue.contains("Extra column") {
            return .yellow
        }
        return .orange
    }
}

struct StatisticRow: View {
    let label: String
    let value: String
    
    var body: some View {
        HStack {
            Text(label)
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
                .fontWeight(.medium)
        }
    }
}

#Preview {
    DatabaseManagementView()
}