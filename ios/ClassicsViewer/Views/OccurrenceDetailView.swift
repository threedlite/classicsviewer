import SwiftUI

struct OccurrenceDetailView: View {
    let occurrence: WordOccurrence
    @State private var contextLines: [TextLine] = []
    @State private var isLoading = true
    
    private let lineDAO = LineDAO()
    private let contextRange = 5 // Lines before and after
    
    var body: some View {
        ScrollView {
            if isLoading {
                LoadingView(message: "Loading context...")
                    .padding(.top, 100)
            } else {
                VStack(alignment: .leading, spacing: 20) {
                    // Header info
                    VStack(alignment: .leading, spacing: 8) {
                        Text(occurrence.bookTitle)
                            .font(.title2)
                            .fontWeight(.bold)
                        
                        Text("by \(occurrence.authorName)")
                            .font(.body)
                            .foregroundColor(.secondary)
                        
                        Text("Line \(occurrence.lineNumber)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .padding(.horizontal)
                    .padding(.top)
                    
                    Divider()
                    
                    // Context lines
                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(contextLines) { line in
                            HStack(alignment: .top, spacing: 12) {
                                Text("\(line.lineNumber)")
                                    .font(.system(size: 12, design: .monospaced))
                                    .foregroundColor(.secondary)
                                    .frame(width: 40, alignment: .trailing)
                                
                                if line.lineNumber == occurrence.lineNumber {
                                    Text(line.lineText)
                                        .fontWeight(.medium)
                                        .background(Color.yellow.opacity(0.3))
                                } else {
                                    Text(line.lineText)
                                        .foregroundColor(.primary.opacity(0.8))
                                }
                                
                                Spacer()
                            }
                        }
                    }
                    .padding(.horizontal)
                    
                    Spacer(minLength: 50)
                }
            }
        }
        .navigationTitle("Occurrence")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                NavigationLink(destination: ReaderView(
                    book: Book(
                        id: occurrence.bookId,
                        workId: "",
                        bookNumber: 1,
                        label: occurrence.bookTitle,
                        startLine: nil,
                        endLine: nil,
                        lineCount: nil
                    ),
                    author: Author(
                        id: "",
                        name: occurrence.authorName,
                        nameAlt: nil,
                        language: "greek",
                        hasTranslations: 0
                    )
                )) {
                    Label("Open Book", systemImage: "book")
                }
            }
        }
        .onAppear {
            loadContext()
        }
    }
    
    private func loadContext() {
        Task {
            await loadContextLines()
        }
    }
    
    @MainActor
    private func loadContextLines() async {
        isLoading = true

        let startLine = max(1, occurrence.lineNumber - contextRange)
        let endLine = occurrence.lineNumber + contextRange

        do {
            contextLines = try await lineDAO.getLines(
                bookId: occurrence.bookId,
                startLine: startLine,
                endLine: endLine
            )
        } catch {
            print("Failed to load context: \(error)")
        }

        isLoading = false
    }
}

struct OccurrenceDetailView_Previews: PreviewProvider {
    static var previews: some View {
        NavigationView {
            OccurrenceDetailView(occurrence: WordOccurrence(
                word: "ἀνήρ",
                bookId: "hom.il",
                bookTitle: "Iliad",
                authorName: "Homer",
                lineNumber: 100,
                lineText: "ἄνδρα μοι ἔννεπε, Μοῦσα, πολύτροπον, ὃς μάλα πολλὰ",
                wordPositions: [1]
            ))
        }
    }
}