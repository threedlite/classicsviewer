import SwiftUI

/// Renders interlinear translation text in Markdown table format
/// Matches Android TranslationAdapter.kt lines 76-236
///
/// Format: | greek |\n| **gloss** |\n| lemma morph |  (separated by double space for next word)
/// Only processes tables when translator contains "Interlinear"
struct InterlinearTextView: View {
    let text: String
    let fontSize: CGFloat

    @Environment(\.colorScheme) var colorScheme

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(alignment: .top, spacing: 16) {
                ForEach(Array(parseMarkdownTables(text).enumerated()), id: \.offset) { index, rows in
                    if rows.count == 3 {
                        createWordTable(rows: rows)
                    }
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
                .font(.system(size: fontSize * 1.1, design: .serif))
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
