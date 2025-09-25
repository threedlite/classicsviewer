import Foundation
import Combine

@MainActor
class AuthorListViewModel: ObservableObject {
    @Published var authors: [Author] = []
    @Published var filteredAuthors: [Author] = []
    @Published var searchText = ""
    @Published var showOnlyTranslated = false
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    private let authorDAO = AuthorDAO()
    private var cancellables = Set<AnyCancellable>()
    
    var isGreek: Bool
    var language: String = "greek"

    init(isGreek: Bool) {
        self.isGreek = isGreek
        self.language = isGreek ? "greek" : "latin"

        // Set up search filtering
        Publishers.CombineLatest($searchText, $showOnlyTranslated)
            .debounce(for: .milliseconds(300), scheduler: RunLoop.main)
            .sink { [weak self] searchText, showOnlyTranslated in
                self?.filterAuthors(searchText: searchText, showOnlyTranslated: showOnlyTranslated)
            }
            .store(in: &cancellables)
    }

    init(language: String) {
        self.language = language
        self.isGreek = language == "greek"

        // Set up search filtering
        Publishers.CombineLatest($searchText, $showOnlyTranslated)
            .debounce(for: .milliseconds(300), scheduler: RunLoop.main)
            .sink { [weak self] searchText, showOnlyTranslated in
                self?.filterAuthors(searchText: searchText, showOnlyTranslated: showOnlyTranslated)
            }
            .store(in: &cancellables)
    }

    func loadAuthors() {
        Task {
            await loadAuthorsAsync()
        }
    }

    private func loadAuthorsAsync() async {
        isLoading = true
        errorMessage = nil

        print("DEBUG: Loading authors for language: '\(language)'")

        do {
            // No need to open database - async architecture handles it
            authors = try await authorDAO.getAuthorsByLanguage(language)
            print("DEBUG: Loaded \(authors.count) authors for language: '\(language)'")
            filteredAuthors = authors

            // No need to close database - async architecture handles it
        } catch {
            errorMessage = error.localizedDescription
            print("ERROR: Failed to load authors for language '\(language)': \(error)")
            print("ERROR: Full error details: \(String(describing: error))")
        }

        isLoading = false
    }
    
    private func filterAuthors(searchText: String, showOnlyTranslated: Bool) {
        var results = authors

        // Apply translation filter
        if showOnlyTranslated {
            results = results.filter { $0.hasTranslations == 1 }
        }

        // Apply text search filter
        if !searchText.isEmpty {
            results = results.filter { author in
                author.name.localizedCaseInsensitiveContains(searchText) ||
                (author.nameAlt?.localizedCaseInsensitiveContains(searchText) ?? false)
            }
        }

        filteredAuthors = results
    }
    
    func authorsByFirstLetter() -> [(String, [Author])] {
        let grouped = Dictionary(grouping: filteredAuthors) { author in
            String(author.name.prefix(1).uppercased())
        }
        
        return grouped
            .sorted { $0.key < $1.key }
            .map { ($0.key, $0.value.sorted { $0.name < $1.name }) }
    }
}