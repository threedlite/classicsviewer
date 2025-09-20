import SwiftUI

struct SearchNavigationBar: View {
    @EnvironmentObject var searchContext: SearchNavigationContext

    var body: some View {
        HStack {
            // Search query and type info
            VStack(alignment: .leading, spacing: 2) {
                Text("Search: \(searchContext.searchQuery)")
                    .font(.caption)
                    .fontWeight(.medium)
                    .lineLimit(1)

                Text("\(searchContext.searchType.rawValue) search")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }

            Spacer()

            // Result position
            Text(searchContext.resultPositionText)
                .font(.caption)
                .fontWeight(.medium)

            // Navigation buttons
            Button(action: searchContext.navigateToPrevious) {
                Image(systemName: "chevron.up")
                    .font(.system(size: 14, weight: .medium))
                    .frame(width: 32, height: 32)
                    .background(Color.secondary.opacity(0.1))
                    .clipShape(Circle())
            }
            .disabled(!searchContext.hasPreviousResult)

            Button(action: searchContext.navigateToNext) {
                Image(systemName: "chevron.down")
                    .font(.system(size: 14, weight: .medium))
                    .frame(width: 32, height: 32)
                    .background(Color.secondary.opacity(0.1))
                    .clipShape(Circle())
            }
            .disabled(!searchContext.hasNextResult)

            // Done button
            Button("Done") {
                searchContext.reset()
            }
            .font(.caption)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Color.blue)
            .foregroundColor(.white)
            .clipShape(Capsule())
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .background(Color(.systemGray6))
        .overlay(
            Rectangle()
                .frame(height: 0.5)
                .foregroundColor(Color(.separator)),
            alignment: .bottom
        )
    }
}