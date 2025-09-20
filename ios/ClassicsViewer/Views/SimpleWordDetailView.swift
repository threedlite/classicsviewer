import SwiftUI

// Minimal word detail view that avoids all potential crash points
struct SimpleWordDetailView: View {
    let word: Word
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                // Word information
                VStack(alignment: .leading, spacing: 10) {
                    HStack {
                        Text("Word:")
                            .font(.headline)
                        Text(word.word)
                            .font(.title2)
                    }
                    
                    HStack {
                        Text("Normalized:")
                            .font(.headline)
                        Text(GreekNormalizer.normalize(word.word))
                            .font(.body)
                    }
                    
                    HStack {
                        Text("Line Number:")
                            .font(.headline)
                        Text("\(word.lineNumber)")
                            .font(.body)
                    }
                    
                    HStack {
                        Text("Book ID:")
                            .font(.headline)
                        Text(word.bookId)
                            .font(.caption)
                    }
                }
                .padding()
                .background(Color.gray.opacity(0.1))
                .cornerRadius(10)
                
                Spacer()
                
                // Placeholder for future features
                Text("Dictionary lookup coming soon...")
                    .italic()
                    .foregroundColor(.secondary)
                
                Spacer()
            }
            .padding()
            .navigationTitle("Word Details")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
        }
    }
}