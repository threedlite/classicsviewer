import Foundation

enum SearchType: String, CaseIterable {
    case exact = "Exact"
    case normalized = "Normalized"
    case lemma = "Lemma"
}