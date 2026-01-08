import Foundation
import SwiftUI

@MainActor
class BookListViewModel: ObservableObject {
    @Published var booksWithTranslations: [(book: Book, hasTranslation: Bool)] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let bookDAO = BookDAO()
    private let translationDAO = TranslationDAO()

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

            // Check if this work exists in works table
            let workDAO = WorkDAO()
            if let work = try await workDAO.getWork(workId: workId) {
                print("DEBUG: Work found in database - id: \(work.id), title: \(work.title)")
            } else {
                print("DEBUG: WARNING - Work NOT found in works table!")
            }

            let books = try await bookDAO.getBooksForWork(workId: workId)
            print("DEBUG: Loaded \(books.count) books")

            // Check translation status for each book
            var booksWithStatus: [(book: Book, hasTranslation: Bool)] = []
            for book in books {
                let hasTranslation = try await translationDAO.hasNonInterlinearTranslationsForBook(bookId: book.id)
                booksWithStatus.append((book: book, hasTranslation: hasTranslation))
            }
            booksWithTranslations = booksWithStatus

        } catch {
            errorMessage = error.localizedDescription
            print("ERROR: Failed to load books: \(error)")
        }

        isLoading = false
    }

    // For backward compatibility
    var books: [Book] {
        booksWithTranslations.map { $0.book }
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