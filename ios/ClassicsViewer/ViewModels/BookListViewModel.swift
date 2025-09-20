import Foundation
import SwiftUI

@MainActor
class BookListViewModel: ObservableObject {
    @Published var books: [Book] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    
    private let bookDAO = BookDAO()
    
    func loadBooks(for workId: String) {
        Task {
            await loadBooksAsync(for: workId)
        }
    }
    
    private func loadBooksAsync(for workId: String) async {
        isLoading = true
        errorMessage = nil
        
        do {
            print("DEBUG: Loading books for work \(workId)")
            // Database lifecycle managed by async architecture
            
            books = try await bookDAO.getBooksForWork(workId: workId)
            print("DEBUG: Loaded \(books.count) books")
            
        } catch {
            errorMessage = error.localizedDescription
            print("ERROR: Failed to load books: \(error)")
        }
        
        isLoading = false
    }
}

// Extension to provide a computed title property for Book
extension Book {
    var title: String {
        return label ?? "Book \(bookNumber)"
    }
    
    var lineCountValue: Int {
        return self.lineCount ?? 0
    }
}