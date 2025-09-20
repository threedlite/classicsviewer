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
    
    init(isGreek: Bool) {
        self.isGreek = isGreek
        
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

        do {
            // No need to open database - async architecture handles it

            if isGreek {
                authors = try await authorDAO.getGreekAuthors()
            } else {
                authors = try await authorDAO.getLatinAuthors()
            }

            filteredAuthors = authors

            // No need to close database - async architecture handles it
        } catch {
            errorMessage = error.localizedDescription
            print("ERROR: Failed to load authors: \(error)")
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