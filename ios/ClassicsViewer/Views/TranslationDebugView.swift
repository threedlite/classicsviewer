import SwiftUI

/// Debug view to test and verify translation lookup table functionality
struct TranslationDebugView: View {
    let book: Book
    @State private var lookupResults: [TranslationLookupResult] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var selectedLine = 1
    @State private var hasLookupTable = false
    
    struct TranslationLookupResult: Identifiable {
        let id = UUID()
        let lineNumber: Int
        let segmentIds: [Int]
        let translationTexts: [String]
    }
    
    var body: some View {
        VStack(spacing: 20) {
            // Book info
            VStack(alignment: .leading, spacing: 8) {
                Text("Book: \(book.id)")
                    .font(.headline)
                Text("Lines: \(book.startLine ?? 0) - \(book.endLine ?? 0)")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                if hasLookupTable {
                    Label("Has Translation Lookup Table", systemImage: "checkmark.circle.fill")
                        .foregroundColor(.green)
                } else {
                    Label("No Translation Lookup Table", systemImage: "xmark.circle.fill")
                        .foregroundColor(.red)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
            .background(Color(.systemGray6))
            .cornerRadius(10)
            
            // Line selector
            VStack(alignment: .leading, spacing: 8) {
                Text("Test specific line:")
                    .font(.headline)
                
                HStack {
                    Slider(
                        value: Binding(
                            get: { Double(selectedLine) },
                            set: { selectedLine = Int($0) }
                        ),
                        in: Double(book.startLine ?? 1)...Double(book.endLine ?? 100),
                        step: 1
                    )
                    
                    Text("\(selectedLine)")
                        .frame(width: 50)
                        .padding(8)
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                }
                
                Button(action: testSpecificLine) {
                    Label("Test Line \(selectedLine)", systemImage: "magnifyingglass")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(10)
                }
            }
            .padding()
            .background(Color(.systemGray6))
            .cornerRadius(10)
            
            // Results
            if isLoading {
                ProgressView("Loading...")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let error = errorMessage {
                VStack {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.largeTitle)
                        .foregroundColor(.red)
                    Text(error)
                        .multilineTextAlignment(.center)
                        .padding()
                }
            } else if !lookupResults.isEmpty {
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        ForEach(lookupResults) { result in
                            VStack(alignment: .leading, spacing: 8) {
                                HStack {
                                    Text("Line \(result.lineNumber)")
                                        .font(.headline)
                                    Spacer()
                                    Text("Segments: \(result.segmentIds.map(String.init).joined(separator: ", "))")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                                
                                ForEach(Array(result.translationTexts.enumerated()), id: \.offset) { index, text in
                                    Text(text)
                                        .font(.system(.body))
                                        .padding(8)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .background(Color(.systemGray6))
                                        .cornerRadius(8)
                                }
                            }
                            .padding()
                            .background(Color(.systemBackground))
                            .cornerRadius(10)
                            .shadow(radius: 2)
                        }
                    }
                    .padding()
                }
            } else {
                VStack {
                    Image(systemName: "doc.text.magnifyingglass")
                        .font(.largeTitle)
                        .foregroundColor(.secondary)
                    Text("Test translation lookup for this book")
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .navigationTitle("Translation Debug")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            checkForLookupTable()
        }
    }
    
    private func checkForLookupTable() {
        Task {
            do {
                let lookupDAO = TranslationLookupDAO()
                hasLookupTable = try await lookupDAO.hasTranslationLookup(bookId: book.id)
            } catch {
                print("Error checking lookup table: \(error)")
            }
        }
    }
    
    private func testSpecificLine() {
        Task {
            await testLine(selectedLine)
        }
    }
    
    private func testLine(_ lineNumber: Int) async {
        isLoading = true
        errorMessage = nil
        lookupResults = []
        
        do {
            let lookupDAO = TranslationLookupDAO()
            let translationDAO = TranslationDAO()
            
            // Get segment IDs for this line
            let segmentIds = try await lookupDAO.getTranslationSegmentIds(
                bookId: book.id,
                lineNumber: lineNumber
            )
            
            if segmentIds.isEmpty {
                // Try range-based lookup
                let translations = try await translationDAO.getTranslations(
                    bookId: book.id,
                    startLine: lineNumber,
                    endLine: lineNumber
                )
                
                if translations.isEmpty {
                    errorMessage = "No translations found for line \(lineNumber)"
                } else {
                    let result = TranslationLookupResult(
                        lineNumber: lineNumber,
                        segmentIds: translations.map { $0.id },
                        translationTexts: translations.map { $0.translationText }
                    )
                    lookupResults = [result]
                }
            } else {
                // Get actual translation texts
                let translations = try await translationDAO.getTranslations(
                    bookId: book.id,
                    startLine: lineNumber,
                    endLine: lineNumber
                )
                
                let result = TranslationLookupResult(
                    lineNumber: lineNumber,
                    segmentIds: segmentIds,
                    translationTexts: translations.map { $0.translationText }
                )
                lookupResults = [result]
            }
            
            isLoading = false
        } catch {
            errorMessage = "Error: \(error.localizedDescription)"
            isLoading = false
        }
    }
}

// Helper view to access debug functionality
struct TranslationDebugButton: View {
    let book: Book
    @State private var showingDebugView = false
    
    var body: some View {
        Button(action: { showingDebugView = true }) {
            Label("Debug Translations", systemImage: "ladybug")
        }
        .sheet(isPresented: $showingDebugView) {
            NavigationView {
                TranslationDebugView(book: book)
                    .toolbar {
                        ToolbarItem(placement: .navigationBarTrailing) {
                            Button("Done") {
                                showingDebugView = false
                            }
                        }
                    }
            }
        }
    }
}