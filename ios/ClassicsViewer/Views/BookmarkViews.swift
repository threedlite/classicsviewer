import SwiftUI
import UniformTypeIdentifiers

// Define CSV type properly
extension UTType {
    static var csv: UTType {
        UTType(importedAs: "public.comma-separated-values-text")
    }
}

// MARK: - Bookmarks List View

struct BookmarksView: View {
    @StateObject private var viewModel = BookmarksViewModel()
    @State private var selectedTab = 0
    @State private var showingImportSheet = false
    @State private var showingExportSheet = false
    @State private var csvDocument: CSVDocument?
    @State private var showingAlert = false
    @State private var alertMessage = ""
    
    var body: some View {
        VStack {
            // Tab selector
            Picker("View", selection: $selectedTab) {
                Text("All").tag(0)
                Text("Recent").tag(1)
                Text("With Notes").tag(2)
            }
            .pickerStyle(SegmentedPickerStyle())
            .padding(.horizontal)
            
            // Bookmarks list
            if viewModel.isLoading {
                LoadingView(message: "Loading bookmarks...")
            } else if viewModel.bookmarks.isEmpty {
                emptyView
            } else {
                bookmarksList
            }
        }
        .navigationTitle("Bookmarks")
        .navigationBarTitleDisplayMode(.large)
        .toolbar {
            ToolbarItemGroup(placement: .navigationBarTrailing) {
                Menu {
                    Button(action: { showingImportSheet = true }) {
                        Label("Import CSV", systemImage: "square.and.arrow.down")
                    }
                    
                    Button(action: { 
                        Task { 
                            await prepareExportContent()
                        }
                    }) {
                        Label("Export CSV", systemImage: "square.and.arrow.up")
                    }
                } label: {
                    Image(systemName: "ellipsis.circle")
                }
            }
        }
        .onAppear {
            viewModel.loadBookmarks(filter: bookmarkFilter)
        }
        .onChange(of: selectedTab) {
            viewModel.loadBookmarks(filter: bookmarkFilter)
        }
        .fileImporter(
            isPresented: $showingImportSheet,
            allowedContentTypes: [.csv, .plainText],
            allowsMultipleSelection: false
        ) { result in
            handleFileImport(result)
        }
        .fileExporter(
            isPresented: $showingExportSheet,
            document: csvDocument,
            contentType: .csv,
            defaultFilename: BookmarkCSVHandler.generateExportFilename()
        ) { result in
            handleExportResult(result)
        }
        .alert(isPresented: $showingAlert) {
            Alert(
                title: Text("Bookmarks"),
                message: Text(alertMessage),
                dismissButton: .default(Text("OK"))
            )
        }
    }
    
    private var bookmarkFilter: BookmarkFilter {
        switch selectedTab {
        case 1: return .recent
        case 2: return .withNotes
        default: return .all
        }
    }
    
    private var emptyView: some View {
        VStack(spacing: 20) {
            Image(systemName: "bookmark")
                .font(.system(size: 60))
                .foregroundColor(.secondary)
            
            Text("No bookmarks yet")
                .font(.title3)
                .foregroundColor(.secondary)
            
            Text("Long press on any line while reading to create a bookmark")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
    
    private var bookmarksList: some View {
        List {
            ForEach(viewModel.bookmarks) { bookmark in
                NavigationLink(destination: ReaderView(
                    book: Book(
                        id: bookmark.bookId,
                        workId: bookmark.workId,
                        bookNumber: extractBookNumber(from: bookmark.bookId),
                        label: bookmark.bookLabel,
                        startLine: nil,
                        endLine: nil,
                        lineCount: nil
                    ),
                    author: Author(
                        id: bookmark.authorId,
                        name: bookmark.authorName,
                        nameAlt: nil,
                        language: "greek", // Default, could be enhanced later
                        hasTranslations: 1
                    ),
                    targetLineNumber: bookmark.lineNumber
                )) {
                    BookmarkRow(bookmark: bookmark)
                }
            }
            .onDelete(perform: deleteBookmarks)
        }
    }
    
    private func deleteBookmarks(at offsets: IndexSet) {
        Task {
            for index in offsets {
                let bookmark = viewModel.bookmarks[index]
                if let id = bookmark.id {
                    await viewModel.deleteBookmark(id: id)
                }
            }
        }
    }
    
    private func prepareExportContent() async {
        let bookmarks = await viewModel.getAllBookmarksForExport()
        
        if bookmarks.isEmpty {
            await MainActor.run {
                alertMessage = "No bookmarks to export"
                showingAlert = true
            }
            return
        }
        
        let csvContent = BookmarkCSVHandler.exportBookmarks(bookmarks)
        
        await MainActor.run {
            // Create the document and show the save dialog
            csvDocument = CSVDocument(content: csvContent)
            showingExportSheet = true
        }
    }
    
    private func handleExportResult(_ result: Result<URL, Error>) {
        switch result {
        case .success(let url):
            print("Export successful to: \(url)")
            alertMessage = "Bookmarks exported successfully!\n\nFile saved as: \(url.lastPathComponent)"
            showingAlert = true
        case .failure(let error):
            print("Export failed: \(error)")
            if case CocoaError.userCancelled = error as NSError {
                // User cancelled, don't show alert
                return
            }
            alertMessage = "Export failed: \(error.localizedDescription)"
            showingAlert = true
        }
    }
    
    private func handleFileImport(_ result: Result<[URL], Error>) {
        switch result {
        case .success(let urls):
            guard let url = urls.first else { return }
            Task {
                await viewModel.importBookmarks(from: url)
            }
        case .failure(let error):
            print("Import failed: \(error)")
        }
    }
    
    private func extractBookNumber(from bookId: String) -> Int {
        // Extract book number from bookId like "tlg0012.tlg001.001" -> 1
        let parts = bookId.components(separatedBy: ".")
        if parts.count >= 3, let bookNumber = Int(parts[2]) {
            return bookNumber
        }
        return 1 // Default
    }
}

// MARK: - Bookmark Row

struct BookmarkRow: View {
    let bookmark: Bookmark
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Author and work
            HStack {
                Text(bookmark.authorName)
                    .font(.caption)
                    .fontWeight(.medium)
                
                Text("•")
                    .foregroundColor(.secondary)
                
                Text(bookmark.workTitle)
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                if let label = bookmark.bookLabel {
                    Text("•")
                        .foregroundColor(.secondary)
                    
                    Text(label)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                Text("Line \(bookmark.lineNumber)")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
            
            // Line text
            Text(bookmark.lineText)
                .font(.system(size: 16))
                // .fontDesign(bookmark.language == "greek" ? .serif : .default) // iOS 16.1+
                .lineLimit(2)
            
            // Note preview if exists
            if let note = bookmark.note, !note.isEmpty {
                HStack {
                    Image(systemName: "note.text")
                        .font(.caption)
                        .foregroundColor(.blue)
                    
                    Text(note)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .lineLimit(1)
                }
            }
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Bookmark Detail View

struct BookmarkDetailView: View {
    let bookmark: Bookmark
    @State private var note: String = ""
    @State private var isEditing = false
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // Book info
                VStack(alignment: .leading, spacing: 8) {
                    Text(bookmark.workTitle)
                        .font(.title2)
                        .fontWeight(.bold)
                    
                    if let label = bookmark.bookLabel {
                        Text(label)
                            .font(.body)
                            .foregroundColor(.secondary)
                    }
                    
                    Text("by \(bookmark.authorName)")
                        .font(.body)
                        .foregroundColor(.secondary)
                    
                    Text("Line \(bookmark.lineNumber)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .padding(.horizontal)
                .padding(.top)
                
                Divider()
                
                // Line text
                VStack(alignment: .leading, spacing: 12) {
                    Text("Text")
                        .font(.headline)
                    
                    Text(bookmark.lineText)
                        .font(.system(size: 18))
                        // .fontDesign(bookmark.language == "greek" ? .serif : .default) // iOS 16.1+
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(10)
                }
                .padding(.horizontal)
                
                // Note section
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Text("Note")
                            .font(.headline)
                        
                        Spacer()
                        
                        Button(action: { isEditing.toggle() }) {
                            Text(isEditing ? "Done" : "Edit")
                        }
                    }
                    
                    if isEditing {
                        TextEditor(text: $note)
                            .padding(8)
                            .background(Color(.systemGray6))
                            .cornerRadius(10)
                            .frame(minHeight: 100)
                    } else {
                        Text(note.isEmpty ? "No note added" : note)
                            .foregroundColor(note.isEmpty ? .secondary : .primary)
                            .padding()
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(Color(.systemGray6))
                            .cornerRadius(10)
                    }
                }
                .padding(.horizontal)
                
                // Metadata
                VStack(alignment: .leading, spacing: 8) {
                    Label("Created \(bookmark.createdAt.formatted())", systemImage: "calendar")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    Label("Last accessed \(bookmark.lastAccessed.formatted())", systemImage: "clock")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .padding(.horizontal)
                .padding(.bottom, 20)
            }
        }
        .navigationTitle("Bookmark")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                NavigationLink(destination: ReaderView(
                    book: Book(id: bookmark.bookId, workId: bookmark.workId, 
                              bookNumber: 1, label: bookmark.bookLabel,
                              startLine: nil, endLine: nil, lineCount: nil),
                    author: Author(id: "", name: bookmark.authorName, 
                                 nameAlt: nil, language: bookmark.language, hasTranslations: 0)
                )) {
                    Label("Open Book", systemImage: "book")
                }
            }
        }
        .onAppear {
            note = bookmark.note ?? ""
        }
        .onDisappear {
            saveNote()
        }
    }
    
    private func saveNote() {
        guard let id = bookmark.id else { return }
        
        if note != bookmark.note {
            Task {
                let updatedBookmark = Bookmark(
                    id: id,
                    authorId: bookmark.authorId,
                    workId: bookmark.workId,
                    bookId: bookmark.bookId,
                    lineNumber: bookmark.lineNumber,
                    sequenceNumber: bookmark.sequenceNumber,
                    authorName: bookmark.authorName,
                    workTitle: bookmark.workTitle,
                    bookLabel: bookmark.bookLabel,
                    lineText: bookmark.lineText,
                    note: note.isEmpty ? nil : note,
                    createdAt: bookmark.createdAt,
                    lastAccessed: Date()
                )
                
                try? await BookmarkDAO().updateBookmark(updatedBookmark)
            }
        }
    }
}

// MARK: - View Model

@MainActor
class BookmarksViewModel: ObservableObject {
    @Published var bookmarks: [Bookmark] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    private let bookmarkDAO = BookmarkDAO()
    private let csvManager = BookmarkCSVManager()
    
    func loadBookmarks(filter: BookmarkFilter) {
        Task {
            await loadBookmarksAsync(filter: filter)
        }
    }
    
    private func loadBookmarksAsync(filter: BookmarkFilter) async {
        isLoading = true
        errorMessage = nil
        
        do {
                // Database lifecycle managed by async architecture
            try await bookmarkDAO.createBookmarksTableIfNeeded()
            
            switch filter {
            case .all:
                bookmarks = try await bookmarkDAO.getAllBookmarks()
            case .recent:
                bookmarks = try await bookmarkDAO.getRecentBookmarks(limit: 50)
            case .withNotes:
                bookmarks = try await bookmarkDAO.getBookmarksWithNotes()
            }
            
        } catch {
            errorMessage = error.localizedDescription
            print("Failed to load bookmarks: \(error)")
        }
        
        isLoading = false
    }
    
    func deleteBookmark(id: Int) async {
        do {
                // Database lifecycle managed by async architecture
            try await bookmarkDAO.deleteBookmark(id: id)
            
            // Remove from local array
            bookmarks.removeAll { $0.id == id }
        } catch {
            print("Failed to delete bookmark: \(error)")
        }
    }
    
    func getAllBookmarksForExport() async -> [Bookmark] {
        do {
                // Database lifecycle managed by async architecture
            let bookmarks = try await bookmarkDAO.getAllBookmarks()
            return bookmarks
        } catch {
            print("Failed to get bookmarks for export: \(error)")
            return []
        }
    }
    
    func exportBookmarks() async throws -> URL {
                // Database lifecycle managed by async architecture
        let url = try await csvManager.exportBookmarksToFile()
        return url
    }
    
    func importBookmarks(from url: URL) async {
        do {
                // Database lifecycle managed by async architecture
            try await bookmarkDAO.createBookmarksTableIfNeeded()
            let result = try await csvManager.importBookmarksFromFile(at: url)
            
            print(result.message)
            
            // Reload bookmarks
            await loadBookmarksAsync(filter: .all)
        } catch {
            print("Import failed: \(error)")
        }
    }
}

enum BookmarkFilter {
    case all
    case recent
    case withNotes
}

// MARK: - CSV Document

struct CSVDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.csv, .plainText] }
    
    var content: String
    
    init(content: String) {
        self.content = content
    }
    
    init(configuration: ReadConfiguration) throws {
        guard let data = configuration.file.regularFileContents else {
            throw CocoaError(.fileReadCorruptFile)
        }
        content = String(data: data, encoding: .utf8) ?? ""
    }
    
    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        let data = content.data(using: .utf8) ?? Data()
        return FileWrapper(regularFileWithContents: data)
    }
}

