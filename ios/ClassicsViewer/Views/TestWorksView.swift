import SwiftUI

struct TestWorksView: View {
    @State private var works: [Work] = []
    @State private var message = "Loading..."
    
    var body: some View {
        VStack {
            Text("Test Works for Aristotle (tlg0086)")
                .font(.title)
                .padding()
            
            Text(message)
                .padding()
            
            if !works.isEmpty {
                List(works) { work in
                    VStack(alignment: .leading) {
                        Text(work.title)
                            .font(.headline)
                        if let titleEnglish = work.titleEnglish {
                            Text(titleEnglish)
                                .font(.caption)
                        }
                    }
                }
            }
        }
        .onAppear {
            Task {
                await loadWorks()
            }
        }
    }
    
    @MainActor
    private func loadWorks() async {
        do {
            // Create test author
            let aristotle = Author(
                id: "tlg0086",
                name: "Aristotle",
                nameAlt: nil,
                language: "greek",
                hasTranslations: 1
            )
            
            message = "Opening database..."
                // Database lifecycle managed by async architecture
            
            message = "Loading works..."
            let workDAO = WorkDAO()
            works = try await workDAO.getWorksByAuthor(authorId: aristotle.id)
            
            message = "Found \(works.count) works"
            
        } catch {
            message = "Error: \(error.localizedDescription)"
        }
    }
}