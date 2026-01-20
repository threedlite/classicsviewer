import SwiftUI

// MARK: - Tree Data from sentence-aware dependency parsing

/// Tree data from sentence-aware dependency parsing.
/// Parsed from morph field format:
/// - Treebank: "lemma morph ~* POS deprel head sentPos"
/// - Stanza:   "lemma morph ~ POS deprel head sentPos"
struct TreeData {
    let pos: String      // UPOS tag (NOUN, VERB, ADJ, etc.)
    let deprel: String   // Universal Dependencies relation (nsubj, obj, etc.)
    let head: Int        // Sentence position of head word (0 = ROOT)
    let sentPos: Int     // This word's position in the full sentence
    let isTreebank: Bool // True if from original treebank data, false if Stanza-derived
}

/// Parse enhanced morph format:
/// - Treebank: "lemma morph ~* POS deprel head sentPos"
/// - Stanza:   "lemma morph ~ POS deprel head sentPos"
/// Returns the display part (before delimiter) and optional tree data (after delimiter)
func parseEnhancedMorph(_ morphField: String) -> (display: String, treeData: TreeData?) {
    // Check for treebank delimiter (~*) first, then Stanza delimiter (~)
    let isTreebank: Bool
    let parts: [String]

    if morphField.contains(" ~* ") {
        isTreebank = true
        parts = morphField.components(separatedBy: " ~* ")
    } else if morphField.contains(" ~ ") {
        isTreebank = false
        parts = morphField.components(separatedBy: " ~ ")
    } else {
        return (morphField, nil)  // No delimiter found
    }

    let displayMorph = parts[0].trimmingCharacters(in: .whitespaces)

    guard parts.count >= 2 else {
        return (displayMorph, nil)
    }

    let treeParts = parts[1].trimmingCharacters(in: .whitespaces).components(separatedBy: " ")
    guard treeParts.count >= 3 else {
        return (displayMorph, nil)
    }

    let treeData = TreeData(
        pos: treeParts[0],
        deprel: treeParts[1],
        head: Int(treeParts[2]) ?? 0,
        sentPos: treeParts.count > 3 ? (Int(treeParts[3]) ?? 0) : 0,
        isTreebank: isTreebank
    )

    return (displayMorph, treeData)
}

/// Renders interlinear translation text in Markdown table format
/// Matches Android TranslationAdapter.kt lines 76-236
///
/// Format: | greek |\n| **gloss** |\n| lemma morph |  (separated by double space for next word)
/// Only processes tables when translator contains "Interlinear"
struct InterlinearTextView: View {
    let text: String
    let fontSize: CGFloat
    let onWordTapped: ((String) -> Void)?

    // For sentence tree gathering across segments
    let segments: [TranslationSegment]?
    let segmentIndex: Int?

    @Environment(\.colorScheme) var colorScheme
    @AppStorage("wrapInterlinear") private var wrapInterlinear: Bool = false
    @AppStorage("enableDependencyTree") private var enableDependencyTree: Bool = false

    // State for sentence tree popup
    @State private var showingSentenceTree = false
    @State private var sentenceTreeText = ""
    @State private var showingLegend = false

    // Safety limit to prevent crashes from excessively large sentences (e.g., Sanskrit texts)
    private let maxSentenceWords = 2000
    // Maximum words before disabling tree display (prevents crash on very long lines)
    private let maxInterlinearWords = 200

    init(text: String, fontSize: CGFloat, segments: [TranslationSegment]? = nil, segmentIndex: Int? = nil, onWordTapped: ((String) -> Void)? = nil) {
        self.text = text
        self.fontSize = fontSize
        self.segments = segments
        self.segmentIndex = segmentIndex
        self.onWordTapped = onWordTapped
    }

    var body: some View {
        let tables = parseMarkdownTables(text)
        let allValidTables = tables.filter { $0.count == 3 }
        // Limit display to maxSentenceWords to prevent crash on very long lines
        let validTables = allValidTables.count > maxSentenceWords
            ? Array(allValidTables.prefix(maxSentenceWords))
            : allValidTables
        // Disable tree display for very long lines (prevents crash)
        let treeDisabledForLine = allValidTables.count > maxInterlinearWords

        Group {
            if wrapInterlinear {
                // Wrap mode: cells wrap to next line, but text within cells does NOT wrap
                if validTables.count <= 100 {
                    // Use custom wrapping layout
                    ScrollView {
                        WrappingHStack(items: validTables, spacing: 8) { rows in
                            createWordTable(rows: rows, allWords: validTables, forWrapping: true, treeDisabled: treeDisabledForLine)
                        }
                        .padding(.horizontal)
                    }
                } else {
                    // Too large - fall back to horizontal with message
                    VStack(alignment: .leading, spacing: 8) {
                        Text("\(validTables.count) words - too large for wrapping. Using horizontal scroll.")
                            .font(.caption)
                            .foregroundColor(.orange)
                            .padding(.horizontal)
                            .padding(.bottom, 4)

                        horizontalScrollView(validTables: validTables, treeDisabled: treeDisabledForLine)
                    }
                }
            } else {
                // Horizontal scroll mode
                horizontalScrollView(validTables: validTables, treeDisabled: treeDisabledForLine)
            }
        }
        .fullScreenCover(isPresented: $showingSentenceTree) {
            SentenceTreeFullScreen(
                treeText: sentenceTreeText,
                showingLegend: $showingLegend
            )
        }
        .sheet(isPresented: $showingLegend) {
            DeprelLegendSheet()
        }
    }

    /// Horizontal scroll view for interlinear text
    @ViewBuilder
    private func horizontalScrollView(validTables: [[String]], treeDisabled: Bool = false) -> some View {
        ScrollView(.horizontal, showsIndicators: false) {
            LazyHStack(alignment: .top, spacing: 16) {
                ForEach(Array(validTables.enumerated()), id: \.offset) { index, rows in
                    createWordTable(rows: rows, allWords: validTables, forWrapping: false, treeDisabled: treeDisabled)
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
    /// rows[2] = lemma + morphology (may contain tree data after " ~ ")
    ///
    /// - Parameters:
    ///   - rows: The three rows of word data
    ///   - allWords: All words in this segment (for tree building)
    ///   - forWrapping: when true, cell sizes to content for FlowLayout wrapping
    ///   - treeDisabled: when true, tree tap is disabled (for very long lines that would crash)
    @ViewBuilder
    private func createWordTable(rows: [String], allWords: [[String]], forWrapping: Bool, treeDisabled: Bool = false) -> some View {
        let isLight = colorScheme == .light
        let cellBackground = isLight ? Color.white : Color.black
        let borderBackground = isLight ? Color(hex: "#EEEEEE") : Color(hex: "#222222")

        // Parse tree data from morph field
        let (displayMorph, treeData) = parseEnhancedMorph(rows[2])
        let hasTreeData = treeData != nil

        VStack(alignment: .center, spacing: 0) {
            // Row 0: Greek word - slightly larger, tappable for dictionary
            Text(rows[0])
                .font(.system(size: fontSize * 1.1))
                .foregroundColor(isLight ? .black : .white)
                .lineLimit(1)  // Never wrap text within cell
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .frame(maxWidth: .infinity)
                .background(cellBackground)
                .onTapGesture {
                    onWordTapped?(rows[0])
                }

            // Row 1: English gloss - bold
            Text(rows[1])
                .font(.system(size: fontSize * 0.9, weight: .bold))
                .foregroundColor(isLight ? .black : .white)
                .lineLimit(1)  // Never wrap text within cell
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .frame(maxWidth: .infinity)
                .background(cellBackground)

            // Row 2: Morphology - style depends on data source:
            // Bold for treebank data (~*), italic for Stanza-derived data (~)
            // Skip tree for very long lines (treeDisabled) to prevent crash
            Text(displayMorph)
                .font(.system(size: fontSize * 0.8, weight: treeData?.isTreebank == true ? .bold : .regular))
                .italic(treeData?.isTreebank != true)
                .foregroundColor(isLight ? Color(hex: "#666666") : Color(hex: "#999999"))
                .lineLimit(1)  // Never wrap text within cell
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .frame(maxWidth: .infinity)
                .background(cellBackground)
                .onTapGesture {
                    if enableDependencyTree, hasTreeData, !treeDisabled, let treeData = treeData, let segIdx = segmentIndex {
                        showSentenceTree(clickedWordSentPos: treeData.sentPos)
                    }
                }
        }
        .fixedSize(horizontal: true, vertical: false)  // Width fits content, height flexible
        .background(borderBackground)
        .cornerRadius(4)
    }

    // MARK: - Sentence Tree Functions

    /// Show the sentence tree popup for the clicked word
    private func showSentenceTree(clickedWordSentPos: Int) {
        guard let segments = segments, let segIdx = segmentIndex else { return }

        // Gather all words from segments that form this sentence
        let allSentenceWords = gatherSentenceWords(segments: segments, startSegmentPos: segIdx)

        // Build tree structure from all sentence words
        sentenceTreeText = buildDependencyTree(words: allSentenceWords, highlightSentPos: clickedWordSentPos)
        showingSentenceTree = true
    }

    /// Gather all words from segments that form a complete sentence.
    /// Expands backward and forward from the current segment until sentence boundaries are found.
    /// Sentence boundaries are detected by gaps in sentPos numbering (new sentence starts at 1).
    ///
    /// Note: Segments alternate between English translations and Interlinear, so we must
    /// SKIP non-interlinear segments when expanding (use continue, not break).
    private func gatherSentenceWords(segments: [TranslationSegment], startSegmentPos: Int) -> [[String]] {
        var allWords: [[String]] = []
        var seenSentPositions = Set<Int>()

        // Helper to check if a segment is interlinear
        func isInterlinear(_ segmentPos: Int) -> Bool {
            guard segmentPos >= 0 && segmentPos < segments.count else { return false }
            return segments[segmentPos].translator?.contains("Interlinear") == true
        }

        // Helper to parse words from a segment and extract tree data
        func getWordsWithTreeData(_ segmentPos: Int) -> [(rows: [String], sentPos: Int, head: Int)] {
            guard isInterlinear(segmentPos) else { return [] }

            let tables = parseMarkdownTables(segments[segmentPos].translationText)
            var result: [(rows: [String], sentPos: Int, head: Int)] = []

            for rows in tables {
                guard rows.count >= 3 else { continue }
                let (_, treeData) = parseEnhancedMorph(rows[2])
                if let td = treeData, td.sentPos > 0 {
                    result.append((rows, td.sentPos, td.head))
                }
            }
            return result
        }

        // Start with current segment
        let currentWords = getWordsWithTreeData(startSegmentPos)
        if currentWords.isEmpty { return [] }

        // Add current segment words
        for (rows, sentPos, _) in currentWords {
            if allWords.count >= maxSentenceWords { break }
            seenSentPositions.insert(sentPos)
            allWords.append(rows)
        }

        // Safety check: if we hit the limit, return immediately without expanding
        if allWords.count >= maxSentenceWords {
            return allWords.sorted { word1, word2 in
                guard word1.count >= 3, word2.count >= 3 else { return false }
                let (_, td1) = parseEnhancedMorph(word1[2])
                let (_, td2) = parseEnhancedMorph(word2[2])
                return (td1?.sentPos ?? 0) < (td2?.sentPos ?? 0)
            }
        }

        let currentMinPos = currentWords.map { $0.sentPos }.min() ?? 1
        let currentMaxPos = currentWords.map { $0.sentPos }.max() ?? 1

        // Expand backward to find sentence start (sentPos = 1)
        var prevSegment = startSegmentPos - 1
        var expectedMinPos = currentMinPos
        while prevSegment >= 0 && expectedMinPos > 1 && allWords.count < maxSentenceWords {
            // CRITICAL FIX: Skip non-interlinear segments (use continue, not break)
            if !isInterlinear(prevSegment) {
                prevSegment -= 1
                continue
            }

            let prevWords = getWordsWithTreeData(prevSegment)
            if prevWords.isEmpty {
                prevSegment -= 1
                continue
            }

            let prevMaxPos = prevWords.map { $0.sentPos }.max() ?? 0
            let prevMinPos = prevWords.map { $0.sentPos }.min() ?? 0

            // Check for sentence boundary: if prev segment has sentPos that doesn't connect
            if prevMaxPos < expectedMinPos - 1 || prevMinPos > expectedMinPos {
                break
            }

            // Add words from previous segment (with safety limit)
            for (rows, sentPos, _) in prevWords {
                if allWords.count >= maxSentenceWords { break }
                if !seenSentPositions.contains(sentPos) {
                    seenSentPositions.insert(sentPos)
                    allWords.append(rows)
                }
            }
            expectedMinPos = prevMinPos
            prevSegment -= 1
        }

        // Expand forward to find sentence end
        var nextSegment = startSegmentPos + 1
        var expectedMaxPos = currentMaxPos
        while nextSegment < segments.count && allWords.count < maxSentenceWords {
            // CRITICAL FIX: Skip non-interlinear segments (use continue, not break)
            if !isInterlinear(nextSegment) {
                nextSegment += 1
                continue
            }

            let nextWords = getWordsWithTreeData(nextSegment)
            if nextWords.isEmpty {
                nextSegment += 1
                continue
            }

            let nextMinPos = nextWords.map { $0.sentPos }.min() ?? 0
            let nextMaxPos = nextWords.map { $0.sentPos }.max() ?? 0

            // Check for sentence boundary: if next segment starts at 1 or has a gap
            if nextMinPos == 1 || nextMinPos > expectedMaxPos + 1 {
                break
            }

            // Add words from next segment (with safety limit)
            for (rows, sentPos, _) in nextWords {
                if allWords.count >= maxSentenceWords { break }
                if !seenSentPositions.contains(sentPos) {
                    seenSentPositions.insert(sentPos)
                    allWords.append(rows)
                }
            }
            expectedMaxPos = nextMaxPos
            nextSegment += 1
        }

        // Sort by sentence position
        return allWords.sorted { word1, word2 in
            guard word1.count >= 3, word2.count >= 3 else { return false }
            let (_, td1) = parseEnhancedMorph(word1[2])
            let (_, td2) = parseEnhancedMorph(word2[2])
            return (td1?.sentPos ?? 0) < (td2?.sentPos ?? 0)
        }
    }

    /// Build a text representation of the dependency tree from full sentence words
    /// - Parameters:
    ///   - words: All words in the sentence (gathered from adjacent segments)
    ///   - highlightSentPos: The sentence position of the clicked word (to highlight)
    private func buildDependencyTree(words: [[String]], highlightSentPos: Int) -> String {
        // Parse tree data from each word
        struct WordNode {
            let greek: String
            let gloss: String
            let pos: String
            let deprel: String
            let head: Int           // Sentence position of head word (0 = ROOT)
            let sentPos: Int        // This word's position in full sentence
        }

        var nodes: [WordNode] = []
        for rows in words {
            guard rows.count >= 3 else { continue }
            let (_, treeData) = parseEnhancedMorph(rows[2])
            if let td = treeData, td.sentPos > 0 {
                nodes.append(WordNode(
                    greek: rows[0],
                    gloss: rows[1],
                    pos: td.pos,
                    deprel: td.deprel,
                    head: td.head,
                    sentPos: td.sentPos
                ))
            }
        }

        if nodes.isEmpty {
            return "No tree data available for this sentence."
        }

        // Build tree text
        var lines: [String] = []
        lines.append(String(repeating: "=", count: 50))
        lines.append("Sentence Tree (\(nodes.count) words)")
        lines.append(String(repeating: "=", count: 50))
        lines.append("ROOT")

        // Track visited nodes to prevent infinite recursion from cycles in data
        var visited = Set<Int>()

        // Recursive function to print tree nodes with cycle protection
        func printNode(_ node: WordNode, prefix: String, isLast: Bool, depth: Int) {
            // Prevent infinite recursion: max depth and cycle detection
            if depth > 100 || visited.contains(node.sentPos) {
                if visited.contains(node.sentPos) {
                    lines.append("\(prefix)\(isLast ? "└── " : "├── ")[cycle detected at \(node.sentPos)]")
                }
                return
            }
            visited.insert(node.sentPos)

            let connector = isLast ? "└── " : "├── "
            let highlight = node.sentPos == highlightSentPos ? " ◀" : ""
            lines.append("\(prefix)\(connector)[\(node.sentPos)] \(node.greek)\(highlight) (\(node.pos), \(node.deprel))")

            let childPrefix = prefix + (isLast ? "    " : "│   ")
            // Filter out self-references and already visited nodes
            let children = nodes.filter { $0.head == node.sentPos && $0.sentPos != node.sentPos && !visited.contains($0.sentPos) }
            for (i, child) in children.enumerated() {
                printNode(child, prefix: childPrefix, isLast: i == children.count - 1, depth: depth + 1)
            }
        }

        // Find root nodes (head == 0) and print tree starting from each
        let roots = nodes.filter { $0.head == 0 }
        if roots.isEmpty {
            lines.append("└── (no root found)")
            lines.append("")
            lines.append("Words without tree structure:")
            for node in nodes.sorted(by: { $0.sentPos < $1.sentPos }) {
                let highlight = node.sentPos == highlightSentPos ? " ◀" : ""
                lines.append("  [\(node.sentPos)] \(node.greek)\(highlight) → head \(node.head)")
            }
        } else {
            for (i, root) in roots.enumerated() {
                printNode(root, prefix: "", isLast: i == roots.count - 1, depth: 0)
            }
        }

        lines.append(String(repeating: "=", count: 50))
        return lines.joined(separator: "\n")
    }
}

// MARK: - WrappingHStack
/// A container that wraps items to the next line when they don't fit
/// Similar to Android's FlexboxLayout with wrap
struct WrappingHStack<Item, ItemView: View>: View {
    let items: [Item]
    let spacing: CGFloat
    let content: (Item) -> ItemView

    @State private var totalHeight: CGFloat = .zero

    init(items: [Item], spacing: CGFloat = 8, @ViewBuilder content: @escaping (Item) -> ItemView) {
        self.items = items
        self.spacing = spacing
        self.content = content
    }

    var body: some View {
        GeometryReader { geometry in
            self.generateContent(in: geometry)
        }
        .frame(height: totalHeight)
    }

    private func generateContent(in geometry: GeometryProxy) -> some View {
        var width = CGFloat.zero
        var height = CGFloat.zero

        return ZStack(alignment: .topLeading) {
            ForEach(Array(items.enumerated()), id: \.offset) { index, item in
                content(item)
                    .padding(.trailing, spacing)
                    .padding(.bottom, spacing)
                    .alignmentGuide(.leading) { dimension in
                        if abs(width - dimension.width) > geometry.size.width {
                            width = 0
                            height -= dimension.height + spacing
                        }
                        let result = width
                        if index == items.count - 1 {
                            width = 0  // Reset for next layout pass
                        } else {
                            width -= dimension.width
                        }
                        return result
                    }
                    .alignmentGuide(.top) { dimension in
                        let result = height
                        if index == items.count - 1 {
                            height = 0  // Reset for next layout pass
                        }
                        return result
                    }
            }
        }
        .background(viewHeightReader($totalHeight))
    }

    private func viewHeightReader(_ binding: Binding<CGFloat>) -> some View {
        GeometryReader { geometry -> Color in
            DispatchQueue.main.async {
                binding.wrappedValue = geometry.size.height
            }
            return Color.clear
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

// MARK: - Sentence Tree Full Screen
/// Full-screen view for displaying the dependency tree structure
/// Supports horizontal and vertical scrolling for fixed-font tree layout
struct SentenceTreeFullScreen: View {
    let treeText: String
    @Binding var showingLegend: Bool
    @Environment(\.dismiss) private var dismiss
    @Environment(\.colorScheme) private var colorScheme
    @AppStorage("fontSize") private var fontSize: Double = 20

    var body: some View {
        VStack(spacing: 0) {
            // Header with Close button and Legend link
            HStack {
                Button(action: { dismiss() }) {
                    HStack(spacing: 4) {
                        Image(systemName: "xmark")
                            .font(.body.weight(.semibold))
                        Text("Close")
                            .fontWeight(.semibold)
                    }
                    .foregroundColor(.gray)
                }

                Spacer()

                Button("Legend") {
                    showingLegend = true
                }
                .foregroundColor(.blue)
                .fontWeight(.semibold)
            }
            .padding()
            .background(colorScheme == .dark ? Color.black : Color.white)

            // 2D scrollable tree content
            ScrollView([.horizontal, .vertical], showsIndicators: true) {
                Text(treeText)
                    .font(.system(size: fontSize, design: .monospaced))
                    .foregroundColor(colorScheme == .dark ? .white : .black)
                    .padding()
                    .fixedSize(horizontal: true, vertical: false)
            }
        }
        .background(colorScheme == .dark ? Color.black : Color.white)
    }
}

// MARK: - Dependency Relation Legend Sheet
/// Sheet view explaining dependency relation labels
struct DeprelLegendSheet: View {
    @Environment(\.dismiss) private var dismiss
    @AppStorage("fontSize") private var fontSize: Double = 20

    private let legendText = """
    Dependency Relations (deprel):

    root      = root of the sentence (main verb)
    nsubj     = nominal subject
    obj       = direct object
    iobj      = indirect object
    obl       = oblique nominal (prepositional phrases)
    nmod      = nominal modifier (genitive, predicate nom.)
    amod      = adjectival modifier
    advmod    = adverbial modifier
    appos     = appositional modifier
    conj      = conjunct (coordinated element)
    cc        = coordinating conjunction (καί, τε, δέ)
    det       = determiner
    case      = case marker (preposition)
    mark      = subordinating conjunction
    aux       = auxiliary verb
    advcl     = adverbial clause modifier
    acl       = adnominal clause (relative clause)
    xcomp     = open clausal complement
    ccomp     = clausal complement
    parataxis = loosely connected clause
    vocative  = vocative (direct address)
    discourse = discourse particle (δή, μέν, etc.)
    punct     = punctuation
    dep       = unspecified dependency

    Parts of Speech (POS):

    NOUN  = noun
    VERB  = verb
    ADJ   = adjective
    ADV   = adverb
    PRON  = pronoun
    DET   = determiner
    ADP   = adposition (preposition)
    CCONJ = coordinating conjunction
    SCONJ = subordinating conjunction
    PART  = particle
    NUM   = numeral
    INTJ  = interjection
    X     = other/unknown
    """

    var body: some View {
        NavigationStack {
            ScrollView {
                Text(legendText)
                    .font(.system(size: fontSize * 0.8, design: .monospaced))
                    .padding()
            }
            .navigationTitle("Legend")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") {
                        dismiss()
                    }
                }
            }
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
