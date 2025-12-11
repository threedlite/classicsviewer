import SwiftUI

/// Renders interlinear translation text in Markdown table format
/// Matches Android TranslationAdapter.kt lines 76-236
///
/// Format: | greek |\n| **gloss** |\n| lemma morph |  (separated by double space for next word)
/// Only processes tables when translator contains "Interlinear"
struct InterlinearTextView: View {
    let text: String
    let fontSize: CGFloat
    let onWordTapped: ((String) -> Void)?

    @Environment(\.colorScheme) var colorScheme
    @AppStorage("wrapInterlinear") private var wrapInterlinear: Bool = false

    init(text: String, fontSize: CGFloat, onWordTapped: ((String) -> Void)? = nil) {
        self.text = text
        self.fontSize = fontSize
        self.onWordTapped = onWordTapped
    }

    var body: some View {
        if wrapInterlinear {
            // For wrapping, we need to be very conservative about size
            // Parse tables and check count
            let tables = parseMarkdownTables(text)
            let validTables = tables.filter { $0.count == 3 }

            if validTables.count <= 100 {
                // Small enough for wrapping
                ScrollView {
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 100, maximum: 150), spacing: 8)], alignment: .leading, spacing: 8) {
                        ForEach(Array(validTables.enumerated()), id: \.offset) { index, rows in
                            createWordTable(rows: rows)
                        }
                    }
                    .padding(.horizontal)
                }
            } else {
                // Too large - fall back to horizontal with message
                VStack(alignment: .leading, spacing: 8) {
                    Text("⚠️ \(validTables.count) words - too large for wrapping. Using horizontal scroll.")
                        .font(.caption)
                        .foregroundColor(.orange)
                        .padding(.horizontal)
                        .padding(.bottom, 4)

                    horizontalScrollView(validTables: validTables)
                }
            }
        } else {
            // Horizontal scroll mode
            let tables = parseMarkdownTables(text)
            let validTables = tables.filter { $0.count == 3 }
            horizontalScrollView(validTables: validTables)
        }
    }

    /// Horizontal scroll view for interlinear text
    @ViewBuilder
    private func horizontalScrollView(validTables: [[String]]) -> some View {
        ScrollView(.horizontal, showsIndicators: false) {
            LazyHStack(alignment: .top, spacing: 16) {
                ForEach(Array(validTables.enumerated()), id: \.offset) { index, rows in
                    createWordTable(rows: rows)
                }
            }
            .padding(.horizontal)
        }
    }

    /// Parse Markdown table structure
    /// Expected format: | greek |\n| **gloss** |\n| lemma morph |  (separated by double space for next word)
    /// Only supports tables and bold (**text**) - no other Markdown syntax
    private func parseMarkdownTables(_ markdown: String) -> [[String]] {
        var tables: [[String]] = []

        // Split by double space to get individual word tables
        let wordTables = markdown.components(separatedBy: "  ")

        for wordTable in wordTables {
            var rows: [String] = []

            // Split by newline to get individual rows
            let lines = wordTable.trimmingCharacters(in: .whitespacesAndNewlines).components(separatedBy: "\n")

            for line in lines {
                // Extract content between pipes: | content |
                let trimmedLine = line.trimmingCharacters(in: .whitespaces)
                if let range = trimmedLine.range(of: #"\|\s*(.*?)\s*\|"#, options: .regularExpression) {
                    var content = String(trimmedLine[range])

                    // Remove the pipes
                    content = content.trimmingCharacters(in: CharacterSet(charactersIn: "|"))
                        .trimmingCharacters(in: .whitespaces)

                    // Handle bold: **text** -> text (we'll apply bold styling in createWordTable)
                    // Only allow bold, nothing else
                    content = content.replacingOccurrences(of: "**", with: "")

                    rows.append(content)
                }
            }

            if rows.count == 3 {  // Only add if we have exactly 3 rows (greek, gloss, morph)
                tables.append(rows)
            }
        }

        return tables
    }

    /// Create a table view for a single word's interlinear data
    /// rows[0] = Greek word
    /// rows[1] = English gloss (bold)
    /// rows[2] = lemma + morphology
    @ViewBuilder
    private func createWordTable(rows: [String]) -> some View {
        let isLight = colorScheme == .light

        VStack(spacing: 0) {
            // Row 0: Greek word - slightly larger
            Text(rows[0])
                .font(.system(size: fontSize * 1.1))
                .foregroundColor(isLight ? .black : .white)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .frame(maxWidth: .infinity)
                .background(isLight ? .white : .black)

            // Row 1: English gloss - bold
            Text(rows[1])
                .font(.system(size: fontSize * 0.9, weight: .bold))
                .foregroundColor(isLight ? .black : .white)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .frame(maxWidth: .infinity)
                .background(isLight ? .white : .black)

            // Row 2: Morphology - italic, smaller
            Text(rows[2])
                .font(.system(size: fontSize * 0.8))
                .italic()
                .foregroundColor(isLight ? Color(hex: "#666666") : Color(hex: "#999999"))
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .frame(maxWidth: .infinity)
                .background(isLight ? .white : .black)
        }
        .background(isLight ? Color(hex: "#EEEEEE") : Color(hex: "#222222"))
        .cornerRadius(4)
        .padding(4)
        .onTapGesture {
            // Tap on the word table to look up the Greek word (rows[0])
            onWordTapped?(rows[0])
        }
    }
}

// MARK: - FlowLayout
/// Custom layout that wraps items to the next line when they don't fit
/// Similar to Android's FlexboxLayout
struct FlowLayout: Layout {
    var spacing: CGFloat = 8
    var containerWidth: CGFloat?

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = containerWidth ?? proposal.replacingUnspecifiedDimensions().width
        let result = FlowResult(in: width, subviews: subviews, spacing: spacing)
        return result.size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let width = containerWidth ?? bounds.width
        let result = FlowResult(in: width, subviews: subviews, spacing: spacing)
        for (index, subview) in subviews.enumerated() {
            subview.place(at: CGPoint(x: bounds.minX + result.positions[index].x, y: bounds.minY + result.positions[index].y), proposal: .unspecified)
        }
    }

    struct FlowResult {
        var size: CGSize = .zero
        var positions: [CGPoint] = []

        init(in containerWidth: CGFloat, subviews: Subviews, spacing: CGFloat) {
            var currentX: CGFloat = 0
            var currentY: CGFloat = 0
            var lineHeight: CGFloat = 0
            var maxWidthUsed: CGFloat = 0

            for subview in subviews {
                let size = subview.sizeThatFits(.unspecified)

                if currentX + size.width > containerWidth && currentX > 0 {
                    // Move to next line
                    currentX = 0
                    currentY += lineHeight + spacing
                    lineHeight = 0
                }

                positions.append(CGPoint(x: currentX, y: currentY))
                currentX += size.width + spacing
                lineHeight = max(lineHeight, size.height)
                maxWidthUsed = max(maxWidthUsed, currentX)
            }

            self.size = CGSize(width: maxWidthUsed, height: currentY + lineHeight)
        }
    }
}

// MARK: - Preview
struct InterlinearTextView_Previews: PreviewProvider {
    static var previews: some View {
        let sampleText = """
| μῆνιν |  | ἄειδε |  | θεά |
| **wrath** |  | **sing** |  | **goddess** |
| μῆνις n-s-f |  | ἀείδω v-2s-pres-imperat-act |  | θεά n-s-f |
"""

        VStack {
            Text("Light Mode")
                .font(.headline)
            InterlinearTextView(text: sampleText, fontSize: 16)
                .preferredColorScheme(.light)

            Divider()

            Text("Dark Mode")
                .font(.headline)
            InterlinearTextView(text: sampleText, fontSize: 16)
                .preferredColorScheme(.dark)
        }
        .padding()
    }
}
