import SwiftUI
import SQLite3
import Combine

struct WorksListView: View {
    let author: Author
    @StateObject private var viewModel: WorksListViewModel
    @State private var debugMessage = ""
    @State private var showingDebugAlert = false
    @State private var searchText = ""
    @State private var showOnlyTranslated = false
    
    init(author: Author) {
        self.author = author
        _viewModel = StateObject(wrappedValue: WorksListViewModel(author: author))
    }
    
    var body: some View {
        VStack {
            if viewModel.isLoading {
                LoadingView(message: "Loading works...")
            } else if let error = viewModel.errorMessage {
                ErrorView(message: error) {
                    viewModel.loadWorks()
                }
            } else if viewModel.works.isEmpty {
                VStack {
                    Text("No works found for this author")
                        .foregroundColor(.secondary)
                        .padding()
                    
                    Text("Author: \(author.name)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    Text("ID: '\(author.id)'")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    Button("Debug: Test Direct Query") {
                        Task {
                            await testDirectQuery()
                        }
                    }
                    .padding()
                    .foregroundColor(.blue)
                }
            } else {
                VStack(spacing: 0) {
                    searchBar
                    worksList
                }
            }
        }
        .navigationTitle(author.name)
        .navigationBarTitleDisplayMode(.large)
        .task {
            viewModel.loadWorks()
        }
        .alert("Debug Results", isPresented: $showingDebugAlert) {
            Button("OK", role: .cancel) { }
        } message: {
            Text(debugMessage)
        }
    }
    
    @MainActor
    private func testDirectQuery() async {
        debugMessage = "Direct Query Test\n\n"
        
        do {
                // Database lifecycle managed by async architecture
            
            // Simple direct query - no parameters
            let query = "SELECT id, author_id, title FROM works WHERE author_id = 'tlg0086' LIMIT 5"

            let results = try await DatabaseManagerAsync.shared.executeQuery(
                query,
                parameters: []
            ) { statement in
                if let titleC = sqlite3_column_text(statement, 2) {
                    return String(cString: titleC)
                }
                return nil
            }.compactMap { $0 }

            debugMessage += "Hardcoded query for Aristotle (tlg0086):\n"
            if results.isEmpty {
                debugMessage += "No results!\n"
            } else {
                for title in results {
                    debugMessage += "- \(title)\n"
                }
            }

            // Now test with the actual author id
            debugMessage += "\nNow testing with author.id = '\(author.id)':\n"
            let query2 = "SELECT COUNT(*) FROM works WHERE author_id = ?"
            let count = try await DatabaseManagerAsync.shared.executeQuery(
                query2,
                parameters: [author.id]
            ) { statement in
                return Int(sqlite3_column_int(statement, 0))
            }
            debugMessage += "Count: \(count.first ?? 0)\n"
            
        } catch {
            debugMessage += "Error: \(error)\n"
        }
        
        showingDebugAlert = true
    }
    
    @MainActor
    private func testDatabaseQuery() async {
        debugMessage = "Testing database for author: \(author.name)\nAuthor ID: '\(author.id)'\n\n"
        
        do {
                // Database lifecycle managed by async architecture
            
            // Test 1: Check exact author ID
            let checkAuthor = "SELECT id, name FROM authors WHERE id = ?"
            let authorCheck = try await DatabaseManagerAsync.shared.executeQuery(
                checkAuthor,
                parameters: [author.id]
            ) { statement in
                if let idCString = sqlite3_column_text(statement, 0),
                   let nameCString = sqlite3_column_text(statement, 1) {
                    return "ID: '\(String(cString: idCString))', Name: \(String(cString: nameCString))"
                }
                return nil
            }.compactMap { $0 }
            debugMessage += "Author in DB: \(authorCheck.first ?? "NOT FOUND")\n\n"

            // Test 2: Direct SQL query for works count
            let testQuery = "SELECT COUNT(*) FROM works WHERE author_id = ?"
            let counts = try await DatabaseManagerAsync.shared.executeQuery(
                testQuery,
                parameters: [author.id]
            ) { statement in
                Int(sqlite3_column_int(statement, 0))
            }
            debugMessage += "Works count for '\(author.id)': \(counts.first ?? 0)\n\n"

            // Test 3: Get sample author IDs from works table
            let allAuthorsQuery = "SELECT DISTINCT author_id FROM works LIMIT 5"
            let authorIds = try await DatabaseManagerAsync.shared.executeQuery(
                allAuthorsQuery,
                parameters: []
            ) { statement in
                if let cString = sqlite3_column_text(statement, 0) {
                    return String(cString: cString)
                }
                return nil
            }.compactMap { $0 }
            debugMessage += "Sample author IDs in works table:\n"
            for id in authorIds {
                debugMessage += "  - \(id)\n"
            }

            // Test 4: Try to get works directly
            let worksQuery = "SELECT id, title FROM works WHERE author_id = ? LIMIT 5"
            let works = try await DatabaseManagerAsync.shared.executeQuery(
                worksQuery,
                parameters: [author.id]
            ) { statement in
                if let idCString = sqlite3_column_text(statement, 0),
                   let titleCString = sqlite3_column_text(statement, 1) {
                    return "\(String(cString: idCString)): \(String(cString: titleCString))"
                }
                return nil
            }.compactMap { $0 }
            
            if !works.isEmpty {
                debugMessage += "\nWorks found:\n"
                for work in works {
                    debugMessage += "  - \(work)\n"
                }
            } else {
                debugMessage += "\nNo works found for this author ID.\n"
            }
            
        } catch {
            debugMessage += "\nERROR: \(error.localizedDescription)"
        }
        
        showingDebugAlert = true
    }
    
    private var searchBar: some View {
        VStack(spacing: 0) {
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.secondary)
                TextField("Search works...", text: $searchText)
                    .textFieldStyle(RoundedBorderTextFieldStyle())
                    .onChange(of: searchText) { newValue in
                        viewModel.searchText = newValue
                    }
                if !searchText.isEmpty {
                    Button(action: {
                        searchText = ""
                        viewModel.searchText = ""
                    }) {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(.secondary)
                    }
                }
            }
            .padding(.horizontal)
            .padding(.vertical, 8)

            Toggle("Show only with translations", isOn: $showOnlyTranslated)
                .padding(.horizontal)
                .padding(.bottom, 8)
                .onChange(of: showOnlyTranslated) { newValue in
                    viewModel.showOnlyTranslated = newValue
                }

            if viewModel.filteredWorks.count < viewModel.worksWithTranslations.count {
                Text("Showing \(viewModel.filteredWorks.count) of \(viewModel.worksWithTranslations.count) works")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.bottom, 4)
            }

            Divider()
        }
        .background(Color(UIColor.systemBackground))
    }

    private var worksList: some View {
        List {
            ForEach(viewModel.filteredWorks, id: \.work.id) { item in
                NavigationLink(destination: BookListView(work: item.work, author: author)) {
                    WorkRow(work: item.work, hasTranslations: item.hasTranslations)
                }
            }
        }
        .listStyle(InsetGroupedListStyle())
    }
}

struct WorkRow: View {
    let work: Work
    let hasTranslations: Bool
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(work.titleEnglish ?? work.title)
                .font(.headline)
                .fontWeight(hasTranslations ? .bold : .regular)
            
            if let titleAlt = work.titleAlt {
                Text(titleAlt)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            if let description = work.description {
                Text(description)
                    .font(.caption2)
                    .foregroundColor(.secondary)
                    .lineLimit(2)
            }
        }
        .padding(.vertical, 4)
    }
}

@MainActor
class WorksListViewModel: ObservableObject {
    @Published var works: [Work] = []
    @Published var worksWithTranslations: [(work: Work, hasTranslations: Bool)] = []
    @Published var filteredWorks: [(work: Work, hasTranslations: Bool)] = []
    @Published var searchText = ""
    @Published var showOnlyTranslated = false
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let author: Author
    private let workDAO = WorkDAO()

    init(author: Author) {
        self.author = author
        setupFiltering()
    }

    private func setupFiltering() {
        Publishers.CombineLatest($searchText, $showOnlyTranslated)
            .debounce(for: .milliseconds(300), scheduler: RunLoop.main)
            .sink { [weak self] _, _ in
                self?.filterWorks()
            }
            .store(in: &cancellables)
    }

    private var cancellables = Set<AnyCancellable>()
    
    func loadWorks() {
        Task {
            await loadWorksAsync()
        }
    }
    
    @MainActor
    private func loadWorksAsync() async {
        isLoading = true
        errorMessage = nil
        
        do {
            // Open database (will be already open)
                // Database lifecycle managed by async architecture
            
            // Get works with translation status
            worksWithTranslations = try await workDAO.getWorksWithTranslationStatus(authorId: author.id)
            
            // Also populate the works array for backward compatibility
            works = worksWithTranslations.map { $0.work }
            filteredWorks = worksWithTranslations

        } catch {
            errorMessage = error.localizedDescription
            print("ERROR loading works: \(error)")
        }
        
        isLoading = false
    }

    private func filterWorks() {
        var results = worksWithTranslations

        // Apply translation filter
        if showOnlyTranslated {
            results = results.filter { $0.hasTranslations }
        }

        // Apply text search filter
        if !searchText.isEmpty {
            results = results.filter { item in
                let work = item.work
                return (work.titleEnglish ?? work.title).localizedCaseInsensitiveContains(searchText) ||
                       (work.titleAlt?.localizedCaseInsensitiveContains(searchText) ?? false) ||
                       (work.description?.localizedCaseInsensitiveContains(searchText) ?? false)
            }
        }

        filteredWorks = results
    }
}