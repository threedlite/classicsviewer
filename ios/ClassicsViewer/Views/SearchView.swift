import SwiftUI
import SQLite3

struct SearchView: View {
    let bookId: String?
    @StateObject private var viewModel: SearchViewModel
    @State private var searchText = ""
    @State private var searchType: SearchType = .exact
    @FocusState private var isSearchFieldFocused: Bool
    @EnvironmentObject var searchContext: SearchNavigationContext
    @Environment(\.dismiss) private var dismiss
    
    
    init(bookId: String? = nil) {
        self.bookId = bookId
        _viewModel = StateObject(wrappedValue: SearchViewModel(bookId: bookId))
    }
    
    var body: some View {
        VStack(spacing: 0) {
            // Search bar
            VStack(spacing: 12) {
                HStack {
                    Image(systemName: "magnifyingglass")
                        .foregroundColor(.secondary)
                    
                    TextField("Search for words...", text: $searchText)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                        .autocapitalization(.none)
                        .disableAutocorrection(true)
                        .focused($isSearchFieldFocused)
                        .onSubmit {
                            performSearch()
                        }
                    
                    if !searchText.isEmpty {
                        Button(action: {
                            searchText = ""
                            viewModel.clearResults()
                        }) {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundColor(.secondary)
                        }
                    }
                }
                
                // Search type picker
                Picker("Search Type", selection: $searchType) {
                    ForEach(SearchType.allCases, id: \.self) { type in
                        Text(type.rawValue).tag(type)
                    }
                }
                .pickerStyle(SegmentedPickerStyle())
                
                // Search button
                Button(action: performSearch) {
                    Text("Search")
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .background(searchText.isEmpty ? Color.gray : Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(8)
                }
                .disabled(searchText.isEmpty)
            }
            .padding()
            .background(Color(.systemGray6))
            
            // Results
            if viewModel.isSearching {
                LoadingView(message: "Searching...")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let error = viewModel.errorMessage {
                ErrorView(message: error) {
                    performSearch()
                }
            } else if viewModel.hasSearched && viewModel.occurrences.isEmpty {
                noResultsView
            } else if !viewModel.occurrences.isEmpty {
                resultsList
            } else {
                instructionsView
            }
        }
        .navigationTitle(bookId != nil ? "Search in Book" : "Search All Texts")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            isSearchFieldFocused = true
        }
    }
    
    private func performSearch() {
        guard !searchText.isEmpty else { return }

        isSearchFieldFocused = false

        viewModel.search(query: searchText, searchType: searchType)
    }
    
    private var instructionsView: some View {
        VStack(spacing: 20) {
            Image(systemName: "magnifyingglass.circle")
                .font(.system(size: 60))
                .foregroundColor(.secondary)
            
            Text("Enter a word to search")
                .font(.title3)
                .foregroundColor(.secondary)
            
            VStack(alignment: .leading, spacing: 10) {
                Label("Exact: Search for exact word forms", systemImage: "textformat")
                Label("Normalized: Ignore accents and breathings", systemImage: "textformat.alt")
                Label("Lemma: Search by dictionary form", systemImage: "book")
            }
            .font(.caption)
            .foregroundColor(.secondary)
            .padding(.top, 20)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
    
    private var noResultsView: some View {
        VStack(spacing: 20) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 50))
                .foregroundColor(.secondary)
            
            Text("No results found")
                .font(.title3)
                .fontWeight(.medium)
            
            Text("Try searching with normalized text or check your spelling")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
    
    private var resultsList: some View {
        List {
            Section(header: Text("\(viewModel.occurrences.count) occurrences found")) {
                ForEach(viewModel.occurrences.indices, id: \.self) { index in
                    Button(action: {
                        navigateToResult(at: index)
                    }) {
                        OccurrenceRow(occurrence: viewModel.occurrences[index], searchTerm: searchText)
                            .foregroundColor(.primary)
                    }
                    .buttonStyle(PlainButtonStyle())
                }
            }
        }
        .listStyle(InsetGroupedListStyle())
    }

    private func navigateToResult(at index: Int) {
        // Set up navigation context
        searchContext.setSearchResults(
            viewModel.occurrences,
            query: searchText,
            type: searchType,
            initialIndex: index
        )

        // Post navigation notification
        NotificationCenter.default.post(
            name: .navigateToReader,
            object: nil,
            userInfo: [
                "bookId": viewModel.occurrences[index].bookId,
                "lineNumber": viewModel.occurrences[index].lineNumber,
                "fromSearch": true
            ]
        )

        // Dismiss search view
        dismiss()
    }
}

struct OccurrenceRow: View {
    let occurrence: WordOccurrence
    let searchTerm: String
    
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            // Book and author info
            HStack {
                Text(occurrence.authorName)
                    .font(.caption)
                    .fontWeight(.medium)
                
                Text("•")
                    .foregroundColor(.secondary)
                
                Text(occurrence.bookTitle)
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                Text("Line \(occurrence.lineNumber)")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
            
            // Line text with highlighted word
            HighlightedLineText(
                lineText: occurrence.lineText,
                wordPositions: occurrence.wordPositions,
                highlightColor: .yellow.opacity(0.3)
            )
            .font(.system(size: 15))
            .lineLimit(2)
        }
        .padding(.vertical, 4)
    }
}

struct HighlightedLineText: View {
    let lineText: String
    let wordPositions: [Int]
    let highlightColor: Color
    
    var body: some View {
        let words = lineText.split(separator: " ", omittingEmptySubsequences: false).map(String.init)
        
        HStack(spacing: 4) {
            ForEach(Array(words.enumerated()), id: \.offset) { index, word in
                if wordPositions.contains(index + 1) {
                    Text(word)
                        .fontWeight(.bold)
                        .background(highlightColor)
                } else {
                    Text(word)
                }
            }
        }
    }
}


@MainActor
class SearchViewModel: ObservableObject {
    @Published var occurrences: [WordOccurrence] = []
    @Published var isSearching = false
    @Published var hasSearched = false
    @Published var errorMessage: String?

    private let bookId: String?
    private let wordDAO = WordDAO()
    private let lemmaDAO = LemmaDAO()

    init(bookId: String? = nil) {
        self.bookId = bookId
    }

    func search(query: String, searchType: SearchType) {
        Task {
            await performSearch(query: query, searchType: searchType)
        }
    }

    private func performSearch(query: String, searchType: SearchType) async {
        isSearching = true
        hasSearched = true
        errorMessage = nil

        do {
            switch searchType {
            case .exact:
                occurrences = try await wordDAO.searchWords(
                    query: query,
                    bookId: bookId,
                    normalized: false
                )
            case .normalized:
                occurrences = try await wordDAO.searchWords(
                    query: query,
                    bookId: bookId,
                    normalized: true
                )
            case .lemma:
                occurrences = try await searchLemmaOccurrences(query: query)
            }
        } catch {
            errorMessage = error.localizedDescription
            print("Search failed: \(error)")
        }

        isSearching = false
    }

    private func searchLemmaOccurrences(query: String) async throws -> [WordOccurrence] {
        // Get normalized query for lemma lookup
        let normalizedQuery = TextNormalization.normalizeWord(query, isGreek: true)

        // 1. Find lemma mappings for the query word
        let lemmaMaps = try await lemmaDAO.getAllLemmaMaps(wordForm: normalizedQuery)

        if !lemmaMaps.isEmpty {
            // 2. Get all inflected forms for the lemmas found
            var allForms = Set<String>()

            // Add the original query forms
            allForms.insert(query)
            allForms.insert(normalizedQuery)

            // Get lemmas and find their forms
            let lemmas = Set(lemmaMaps.map { $0.lemma })
            for lemma in lemmas {
                // Find all word forms for this lemma
                let formsForLemma = try await getLemmaForms(lemma: lemma)
                allForms.formUnion(formsForLemma)
            }

            // 3. Search for all inflected forms
            var allOccurrences: [WordOccurrence] = []
            for form in allForms {
                let occurrences = try await wordDAO.searchWords(
                    query: form,
                    bookId: bookId,
                    normalized: false
                )
                allOccurrences.append(contentsOf: occurrences)
            }

            // 4. Remove duplicates and sort
            let uniqueOccurrences = Array(Set(allOccurrences))
            return uniqueOccurrences.sorted {
                if $0.authorName == $1.authorName {
                    if $0.bookTitle == $1.bookTitle {
                        return $0.lineNumber < $1.lineNumber
                    }
                    return $0.bookTitle < $1.bookTitle
                }
                return $0.authorName < $1.authorName
            }
        } else {
            // Fallback to normalized search if no lemma found
            return try await wordDAO.searchWords(
                query: query,
                bookId: bookId,
                normalized: true
            )
        }
    }

    private func getLemmaForms(lemma: String) async throws -> Set<String> {
        // Search for all word forms that have this lemma
        let query = """
            SELECT DISTINCT word_form
            FROM lemma_map
            WHERE lemma = ?
        """

        let forms = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [lemma]) { (statement: OpaquePointer) -> String? in
            guard let wordFormCString = sqlite3_column_text(statement, 0) else { return nil }
            return String(cString: wordFormCString)
        }

        return Set(forms.compactMap { $0 })
    }

    func clearResults() {
        occurrences = []
        hasSearched = false
        errorMessage = nil
    }
}

extension Notification.Name {
    static let navigateToReader = Notification.Name("navigateToReader")
}

struct SearchView_Previews: PreviewProvider {
    static var previews: some View {
        NavigationView {
            SearchView()
        }
        .environmentObject(SearchNavigationContext())
    }
}