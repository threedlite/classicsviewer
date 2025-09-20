import SwiftUI

class SearchNavigationContext: ObservableObject {
    @Published var searchQuery: String = ""
    @Published var searchResults: [WordOccurrence] = []
    @Published var currentResultIndex: Int = 0
    @Published var highlightedWords: Set<String> = []
    @Published var isFromSearch: Bool = false
    @Published var searchType: SearchType = .exact

    var currentResult: WordOccurrence? {
        guard currentResultIndex < searchResults.count else { return nil }
        return searchResults[currentResultIndex]
    }

    var hasNextResult: Bool {
        currentResultIndex < searchResults.count - 1
    }

    var hasPreviousResult: Bool {
        currentResultIndex > 0
    }

    var resultPositionText: String {
        guard !searchResults.isEmpty else { return "0 of 0" }
        return "\(currentResultIndex + 1) of \(searchResults.count)"
    }

    func navigateToNext() {
        if hasNextResult {
            currentResultIndex += 1
            updateHighlightedWords()
        }
    }

    func navigateToPrevious() {
        if hasPreviousResult {
            currentResultIndex -= 1
            updateHighlightedWords()
        }
    }

    func setSearchResults(_ results: [WordOccurrence], query: String, type: SearchType, initialIndex: Int = 0) {
        searchResults = results
        searchQuery = query
        searchType = type
        currentResultIndex = min(initialIndex, results.count - 1)
        isFromSearch = true
        updateHighlightedWords()
    }

    private func updateHighlightedWords() {
        guard let currentResult = currentResult else {
            highlightedWords = []
            return
        }

        var words = Set<String>()

        // Always add the actual word found
        words.insert(currentResult.word)

        // For lemma search, add the original search query and variations
        if searchType == .lemma {
            words.insert(searchQuery)
            // Also add normalized versions
            words.insert(TextNormalization.normalizeWord(searchQuery, isGreek: true))
            words.insert(TextNormalization.normalizeWord(currentResult.word, isGreek: true))
        } else if searchType == .normalized {
            // For normalized search, add both original and normalized forms
            words.insert(searchQuery)
            words.insert(TextNormalization.normalizeWord(searchQuery, isGreek: true))
            words.insert(TextNormalization.normalizeWord(currentResult.word, isGreek: true))
        } else {
            // For exact search, add both the query and the found word
            words.insert(searchQuery)
        }

        highlightedWords = words
    }

    func reset() {
        searchQuery = ""
        searchResults = []
        currentResultIndex = 0
        highlightedWords = []
        isFromSearch = false
        searchType = .exact
    }
}