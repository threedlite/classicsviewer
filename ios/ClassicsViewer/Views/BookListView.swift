import SwiftUI

struct BookListView: View {
    let work: Work
    let author: Author
    @StateObject private var viewModel = BookListViewModel()
    
    var body: some View {
        VStack {
            if viewModel.isLoading {
                LoadingView(message: "Loading books...")
            } else if let error = viewModel.errorMessage {
                ErrorView(message: error) {
                    viewModel.loadBooks(for: work.id)
                }
            } else {
                bookList
            }
        }
        .navigationTitle(work.titleEnglish ?? work.title)
        .navigationBarTitleDisplayMode(.large)
        .onAppear {
            if viewModel.books.isEmpty {
                viewModel.loadBooks(for: work.id)
            }
        }
    }
    
    private var bookList: some View {
        List(viewModel.booksWithTranslations, id: \.book.id) { item in
            NavigationLink(destination: ReaderView(book: item.book, author: author)) {
                BookRow(book: item.book, hasTranslation: item.hasTranslation)
            }
        }
        .listStyle(InsetGroupedListStyle())
    }
}

struct BookRow: View {
    let book: Book
    let hasTranslation: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(book.title)
                .font(.headline)
                .fontWeight(hasTranslation ? .bold : .regular)
                .lineLimit(2)

            HStack {
                Label("\(book.lineCountValue) lines", systemImage: "text.alignleft")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .padding(.vertical, 6)
    }
}

struct BookListView_Previews: PreviewProvider {
    static var previews: some View {
        NavigationView {
            BookListView(
                work: Work(
                    id: "plat.rep",
                    authorId: "plat",
                    title: "Republic",
                    titleAlt: "Πολιτεία",
                    titleEnglish: "Republic",
                    type: "prose",
                    urn: "urn:cts:greekLit:tlg0059.tlg030",
                    description: nil
                ),
                author: Author(
                    id: "plat",
                    name: "Plato",
                    nameAlt: "Πλάτων",
                    language: "greek",
                    hasTranslations: 1
                )
            )
        }
    }
}