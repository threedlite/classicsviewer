import SwiftUI
import WebKit
import SQLite3

struct ImprovedWordDetailView: View {
    let word: Word
    let viewModel: ReaderViewModel  // Pass the viewModel directly
    @StateObject private var detailViewModel = ImprovedWordDetailViewModel()
    @Environment(\.dismiss) private var dismiss
    @State private var selectedTab = 0
    @State private var hasRequestedOccurrences = false
    @State private var navigateToWord: Word?
    @State private var showingSearchDialog = false
    @State private var searchText = ""
    @State private var searchedWord: Word?
    @AppStorage("fontSize") private var fontSize: Double = 20
    
    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // Word header
                VStack(spacing: 8) {
                    Text(word.word)
                        .font(.system(size: fontSize * 2))
                        .fontWeight(.bold)
                    
                    // Show morphological info if available
                    if let morphInfo = detailViewModel.wordMorphInfo, !morphInfo.isEmpty {
                        Text(formatMorphInfo(morphInfo))
                            .font(.system(size: fontSize * 0.85, weight: .medium))
                            .foregroundColor(.blue)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 4)
                            .background(Color.blue.opacity(0.1))
                            .cornerRadius(4)
                    }
                    
                    if !detailViewModel.lemma.isEmpty && detailViewModel.lemma != word.word {
                        HStack {
                            Text("Lemma:")
                                .foregroundColor(.secondary)
                            Text(detailViewModel.lemma)
                                .fontWeight(.medium)
                        }
                        .font(.system(size: fontSize))
                    }
                    
                    if !detailViewModel.morphInfo.isEmpty {
                        Text(detailViewModel.morphInfo)
                            .font(.system(size: fontSize * 0.8))
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                    }
                }
                .padding()
                
                // Tab selection
                Picker("", selection: $selectedTab) {
                    Text("Dictionary").tag(0)
                    Text("Occurrences").tag(1)
                }
                .pickerStyle(SegmentedPickerStyle())
                .padding(.horizontal)
                
                // Content - Use conditional rendering instead of TabView to avoid gesture conflicts
                if selectedTab == 0 {
                    // Dictionary tab
                    if detailViewModel.isLoadingDictionary {
                        VStack {
                            Spacer()
                            ProgressView("Loading dictionary...")
                            Spacer()
                        }
                    } else if !detailViewModel.dictionaryEntries.isEmpty {
                        ScrollView {
                            VStack(alignment: .leading, spacing: 20) {
                                // Show multiple entries if available
                                if detailViewModel.dictionaryEntries.count > 1 {
                                    Text("Found \(detailViewModel.dictionaryEntries.count) possible matches:")
                                        .font(.system(size: fontSize * 0.9))
                                        .foregroundColor(.secondary)
                                        .padding(.horizontal)
                                }
                                
                                ForEach(Array(detailViewModel.dictionaryEntries.enumerated()), id: \.offset) { index, entry in
                                    VStack(alignment: .leading, spacing: 8) {
                                        // Header with lemma, source and confidence
                                        HStack {
                                            if entry.isDirectMatch {
                                                Label(entry.lemma, systemImage: "checkmark.circle.fill")
                                                    .font(.system(size: fontSize * 1.1, weight: .semibold))
                                                    .foregroundColor(.blue)
                                            } else {
                                                Text(entry.lemma)
                                                    .font(.system(size: fontSize * 1.1, weight: .semibold))
                                            }
                                            
                                            Spacer()
                                            
                                            // Show source label
                                            if let source = entry.source {
                                                let sourceDisplay = formatSourceName(source)
                                                Text("[\(sourceDisplay)]")
                                                    .font(.system(size: fontSize * 0.85, weight: .medium))
                                                    .foregroundColor(sourceColor(for: source))
                                                    .padding(.horizontal, 6)
                                                    .padding(.vertical, 2)
                                                    .background(sourceColor(for: source).opacity(0.1))
                                                    .cornerRadius(4)
                                            }
                                            
                                        }
                                        .padding(.horizontal)
                                        
                                        // Dictionary content
                                        if entry.definition.contains("<") {
                                            // HTML content
                                            SafeDictionaryWebView(
                                                htmlContent: entry.definition,
                                                fontSize: fontSize,
                                                onGreekWordTapped: { tappedWord in
                                                    handleGreekWordTapped(tappedWord)
                                                }
                                            )
                                            .frame(minHeight: 150)
                                        } else {
                                            // Plain text
                                            Text(entry.definition)
                                                .font(.system(size: fontSize))
                                                .padding(.horizontal)
                                        }
                                        
                                        if index < detailViewModel.dictionaryEntries.count - 1 {
                                            Divider()
                                                .padding(.horizontal)
                                        }
                                    }
                                }
                            }
                            .padding(.vertical)
                        }
                    } else if !detailViewModel.dictionaryHtml.isEmpty {
                        // Fallback for single entry
                        SafeDictionaryWebView(
                            htmlContent: detailViewModel.dictionaryHtml,
                            fontSize: fontSize,
                            onGreekWordTapped: { tappedWord in
                                handleGreekWordTapped(tappedWord)
                            }
                        )
                    } else if !detailViewModel.dictionaryPlain.isEmpty {
                        ScrollView {
                            Text(detailViewModel.dictionaryPlain)
                                .font(.system(size: fontSize))
                                .padding()
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    } else {
                        VStack {
                            Spacer()
                            Text("No dictionary entry found")
                                .foregroundColor(.secondary)
                                .italic()
                            Spacer()
                        }
                    }
                } else {
                    // Occurrences tab
                    if detailViewModel.isLoadingOccurrences || (!detailViewModel.hasLoadedOccurrences && detailViewModel.occurrences.isEmpty) {
                        VStack(spacing: 20) {
                            Spacer()
                            ProgressView()
                                .scaleEffect(1.5)
                                .progressViewStyle(CircularProgressViewStyle(tint: .blue))
                            Text("Loading occurrences...")
                                .font(.system(size: fontSize))
                                .foregroundColor(.secondary)
                            Spacer()
                        }
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                    } else if detailViewModel.occurrences.isEmpty && detailViewModel.hasLoadedOccurrences {
                        VStack {
                            Spacer()
                            Text("No occurrences found")
                                .foregroundColor(.secondary)
                                .italic()
                            Spacer()
                        }
                    } else {
                        ScrollView {
                            VStack(alignment: .leading, spacing: 16) {
                                // Show actual total count, and indicate if list is limited
                                if detailViewModel.totalOccurrenceCount > 500 {
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text("\(detailViewModel.totalOccurrenceCount) occurrence\(detailViewModel.totalOccurrenceCount == 1 ? "" : "s") across all texts")
                                            .font(.system(size: fontSize * 1.1, weight: .semibold))
                                        Text("(Showing first 500)")
                                            .font(.system(size: fontSize * 0.9))
                                            .foregroundColor(.secondary)
                                    }
                                    .padding(.horizontal)
                                } else {
                                    Text("\(detailViewModel.totalOccurrenceCount) occurrence\(detailViewModel.totalOccurrenceCount == 1 ? "" : "s") across all texts")
                                        .font(.system(size: fontSize * 1.1, weight: .semibold))
                                        .padding(.horizontal)
                                }
                                
                                ForEach(Array(detailViewModel.occurrences.enumerated()), id: \.offset) { index, occurrence in
                                    if occurrence.bookId == word.bookId {
                                        // Same book - use Button for direct navigation
                                        Button(action: {
                                            print("DEBUG: Same book - navigating to line \(occurrence.lineNumber)")
                                            let targetPage = (occurrence.lineNumber - 1) / 100 + 1
                                            // Set target line on the current view model
                                            viewModel.targetLineNumber = occurrence.lineNumber
                                            viewModel.goToPage(targetPage)
                                            dismiss()
                                        }) {
                                            WordOccurrenceRow(occurrence: occurrence, index: index, totalCount: detailViewModel.occurrences.count, fontSize: fontSize)
                                        }
                                        .buttonStyle(PlainButtonStyle())
                                    } else {
                                        // Different book - use NavigationLink
                                        NavigationLink(destination: {
                                            // Parse the book ID to get work ID
                                            let components = occurrence.bookId.split(separator: ".")
                                            let workId = components.count >= 3 ? "\(components[0]).\(components[1])" : ""
                                            let authorId = components.count >= 1 ? String(components[0]) : ""
                                            let language = occurrence.bookId.hasPrefix("tlg") ? "greek" : "latin"
                                            
                                            // Calculate target page for initial navigation
                                            let targetPage = (occurrence.lineNumber - 1) / 100 + 1
                                            
                                            return ReaderView(
                                                book: Book(
                                                    id: occurrence.bookId,
                                                    workId: workId,
                                                    bookNumber: 1,
                                                    label: "Book",
                                                    startLine: 1,
                                                    endLine: nil,
                                                    lineCount: nil
                                                ),
                                                author: Author(
                                                    id: authorId,
                                                    name: occurrence.authorName,
                                                    nameAlt: nil,
                                                    language: language,
                                                    hasTranslations: 1
                                                ),
                                                initialPage: targetPage,
                                                targetLineNumber: occurrence.lineNumber
                                            )
                                        }()) {
                                            WordOccurrenceRow(occurrence: occurrence, index: index, totalCount: detailViewModel.occurrences.count, fontSize: fontSize)
                                        }
                                        .buttonStyle(PlainButtonStyle())
                                    }
                                }
                            }
                            .padding(.vertical)
                        }
                    }
                }
            }
            .navigationTitle("Word Details")
            .navigationBarTitleDisplayMode(.inline)
            .navigationBarBackButtonHidden()
            .toolbar(content: toolbarContent)
        }
        .onAppear {
            // Only load dictionary on initial appear
            print("DEBUG ImprovedWordDetailView: onAppear called for word: '\(word.word)'")
            Task {
                print("DEBUG ImprovedWordDetailView: Starting loadDictionary task")
                await detailViewModel.loadDictionary(for: word)
                print("DEBUG ImprovedWordDetailView: loadDictionary task completed")
            }

            // Prepopulate search text with cleaned current word (matching Android behavior)
            let cleanedWord = word.word.replacingOccurrences(of: "[.,;:!?·]", with: "", options: .regularExpression)
            searchText = cleanedWord
        }
        .onChange(of: selectedTab) { newValue in
            // Load occurrences only when user switches to that tab
            if newValue == 1 && !hasRequestedOccurrences {
                hasRequestedOccurrences = true
                Task {
                    await detailViewModel.loadOccurrences(for: word)
                }
            }
        }
        .sheet(item: $navigateToWord) { newWord in
            ImprovedWordDetailView(
                word: newWord,
                viewModel: viewModel
            )
        }
        .alert("Search Greek Dictionary", isPresented: $showingSearchDialog) {
            TextField("Enter Greek word (e.g., λόγος, και, θεα)", text: $searchText)
                .keyboardType(.default)
                .autocorrectionDisabled(true)
            Button("Search") {
                if !searchText.trimmingCharacters(in: .whitespaces).isEmpty {
                    // Create a new WordDetailView with the searched word
                    searchedWord = Word(
                        id: 0,
                        word: searchText.trimmingCharacters(in: .whitespaces),
                        bookId: word.bookId, // Use same book context
                        lineNumber: 0,
                        sequenceNumber: 0,
                        wordPosition: 0
                    )
                    searchText = ""
                }
            }
            Button("Cancel", role: .cancel) {
                searchText = ""
            }
        } message: {
            Text("Enter a Greek word to look up:")
        }
        .sheet(item: $searchedWord) { word in
            ImprovedWordDetailView(word: word, viewModel: viewModel)
        }
    }

    @ToolbarContentBuilder
    private func toolbarContent() -> some ToolbarContent {
        ToolbarItem(placement: .navigationBarLeading) {
            HStack {
                Button(action: {
                    showingSearchDialog = true
                }) {
                    Image(systemName: "magnifyingglass")
                }

                Button("Done") {
                    dismiss()
                }
            }
        }
    }

    private func formatSourceName(_ source: String) -> String {
        // Check if source has "(via Treebank)" suffix
        let hasTreebankSuffix = source.contains("(via Treebank)")
        let baseSource = source.replacingOccurrences(of: " (via Treebank)", with: "")

        // Normalize the base source name
        let normalizedSource: String
        switch baseSource.lowercased() {
        case "lsj":
            normalizedSource = "LSJ"
        case "cunliffe":
            normalizedSource = "Cunliffe"
        case "wiktionary":
            normalizedSource = "Wiktionary"
        default:
            normalizedSource = baseSource.capitalized
        }

        // Re-add the suffix if it was present
        return hasTreebankSuffix ? "\(normalizedSource) (via Treebank)" : normalizedSource
    }
    
    private func sourceColor(for source: String) -> Color {
        // Remove "(via Treebank)" suffix to get base source for color
        let baseSource = source.replacingOccurrences(of: " (via Treebank)", with: "")

        switch baseSource.lowercased() {
        case "lsj":
            return .blue
        case "cunliffe":
            return .green
        case "wiktionary":
            return .purple
        default:
            return .gray
        }
    }
    
    private func formatMorphInfo(_ morphInfo: String) -> String {
        // Format morphological information to be more readable
        let info = morphInfo.trimmingCharacters(in: .whitespacesAndNewlines)
        
        // If empty or very short, return as-is
        if info.isEmpty || info.count < 3 {
            return info
        }
        
        // Common abbreviation expansions
        let expansions: [String: String] = [
            "acc": "accusative",
            "gen": "genitive",
            "dat": "dative",
            "nom": "nominative",
            "voc": "vocative",
            "abl": "ablative",
            "s": "singular",
            "p": "plural",
            "d": "dual",
            "m": "masculine",
            "f": "feminine",
            "n": "neuter",
            "pres": "present",
            "imperf": "imperfect",
            "fut": "future",
            "aor": "aorist",
            "perf": "perfect",
            "plup": "pluperfect",
            "actv": "active",
            "mid": "middle",
            "pass": "passive",
            "ind": "indicative",
            "subj": "subjunctive",
            "opt": "optative",
            "impr": "imperative",
            "inf": "infinitive",
            "part": "participle",
            "1": "1st person",
            "2": "2nd person",
            "3": "3rd person"
        ]
        
        // Split the morphInfo by spaces and expand each part
        let parts = info.split(separator: " ")
        let expandedParts = parts.map { part in
            let partStr = String(part).lowercased()
            return expansions[partStr] ?? String(part)
        }
        
        // Join with commas for readability
        return expandedParts.joined(separator: " ")
    }
    
    private func handleGreekWordTapped(_ greekWord: String) {
        print("DEBUG: handleGreekWordTapped called with: '\(greekWord)'")
        
        // Clean the word of any punctuation
        let cleanWord = greekWord.filter { $0.isLetter || $0 == "'" || $0 == "'" || $0 == "ʼ" }
        print("DEBUG: Cleaned word: '\(cleanWord)'")
        
        if !cleanWord.isEmpty {
            // Create a Word object for the tapped Greek word
            let newWord = Word(
                id: 0,
                word: cleanWord,
                bookId: word.bookId,  // Use same book context
                lineNumber: 0,  // Not from a specific line
                sequenceNumber: 0,  // Default sequence
                wordPosition: 0
            )
            
            print("DEBUG: Created new Word object: \(newWord.word)")
            print("DEBUG: Setting navigateToWord")
            
            // Navigate to the new word
            navigateToWord = newWord
        } else {
            print("DEBUG: Cleaned word is empty")
        }
    }
}

// Helper view for occurrence row
struct WordOccurrenceRow: View {
    let occurrence: (bookId: String, authorName: String, workTitle: String, lineNumber: Int, lineText: String, matchingPositions: [Int])
    let index: Int
    let totalCount: Int
    let fontSize: Double
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            // Author and work header
            HStack {
                Text("\(occurrence.authorName) - \(occurrence.workTitle)")
                    .font(.system(size: fontSize * 0.8))
                    .fontWeight(.medium)
                    .foregroundColor(.blue)
                
                Spacer()
                
                Text("Line \(occurrence.lineNumber)")
                    .font(.system(size: fontSize * 0.8))
                    .foregroundColor(.secondary)
            }
            .padding(.horizontal)
            
            // Line text with highlighting
            highlightedLineText()
                .font(.system(size: fontSize))
                .foregroundColor(.primary)
                .multilineTextAlignment(.leading)
                .padding(.horizontal)
                .padding(.bottom, 4)
            
            if index < totalCount - 1 {
                Divider()
                    .padding(.horizontal)
            }
        }
    }
    
    @ViewBuilder
    private func highlightedLineText() -> some View {
        if occurrence.matchingPositions.isEmpty {
            // No positions to highlight, show plain text
            Text(occurrence.lineText)
        } else {
            // Build an attributed string with highlighting
            let attributedString = buildHighlightedAttributedString()
            Text(attributedString)
        }
    }
    
    private func buildHighlightedAttributedString() -> AttributedString {
        var result = AttributedString()
        let words = occurrence.lineText.split(separator: " ", omittingEmptySubsequences: false).map(String.init)
        
        for (index, word) in words.enumerated() {
            let wordPosition = index + 1  // Word positions are 1-based in database
            
            var wordAttr = AttributedString(word)
            if occurrence.matchingPositions.contains(wordPosition) {
                // Highlighted word
                wordAttr.font = .body.bold()
                wordAttr.backgroundColor = Color.yellow.opacity(0.3)
            }
            
            result.append(wordAttr)
            
            // Add space after word (except for last word)
            if index < words.count - 1 {
                result.append(AttributedString(" "))
            }
        }
        
        return result
    }
}

// Safer WebView implementation with Greek word tap handling
struct SafeDictionaryWebView: UIViewRepresentable {
    let htmlContent: String
    let fontSize: Double
    let onGreekWordTapped: ((String) -> Void)?
    
    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.userContentController = WKUserContentController()
        
        // Enable JavaScript console logging for debugging
        configuration.preferences.setValue(true, forKey: "developerExtrasEnabled")
        
        // Add message handler for Greek word taps
        configuration.userContentController.add(context.coordinator, name: "greekWordHandler")
        
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        webView.scrollView.isScrollEnabled = true
        
        // Enable inspection for debugging
        #if DEBUG
        if #available(iOS 16.4, *) {
            webView.isInspectable = true
        }
        #endif
        
        return webView
    }
    
    func updateUIView(_ webView: WKWebView, context: Context) {
        // JavaScript to detect clicks on Greek words
        let greekWordScript = """
        <script>
        // Wait for DOM to be ready
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Greek word click handler initialized');
            
            // Function to check if character is Greek
            function isGreekChar(char) {
                const code = char.charCodeAt(0);
                return (code >= 0x0370 && code <= 0x03FF) || (code >= 0x1F00 && code <= 0x1FFF);
            }
            
            // Function to extract Greek word at click position
            function extractGreekWordFromClick(event) {
                const x = event.clientX;
                const y = event.clientY;
                
                // Try to get the word at the click position
                if (document.caretRangeFromPoint) {
                    const range = document.caretRangeFromPoint(x, y);
                    if (range && range.startContainer.nodeType === Node.TEXT_NODE) {
                        const text = range.startContainer.textContent;
                        const offset = range.startOffset;
                        
                        // Find word boundaries
                        let start = offset;
                        let end = offset;
                        
                        // Expand backwards to find start of word
                        while (start > 0 && isGreekChar(text[start - 1])) {
                            start--;
                        }
                        
                        // Expand forwards to find end of word
                        while (end < text.length && isGreekChar(text[end])) {
                            end++;
                        }
                        
                        if (start < end) {
                            const word = text.substring(start, end);
                            if (word.length > 0) {
                                console.log('Greek word found:', word);
                                return word;
                            }
                        }
                    }
                }
                
                // Fallback: check the clicked element's text
                const element = event.target;
                const text = element.textContent || '';
                const greekWords = text.match(/[\\u0370-\\u03FF\\u1F00-\\u1FFF]+/g);
                if (greekWords && greekWords.length > 0) {
                    console.log('Greek word found (fallback):', greekWords[0]);
                    return greekWords[0];
                }
                
                return null;
            }
            
            // Add click handler to entire document
            document.addEventListener('click', function(event) {
                console.log('Click detected at', event.clientX, event.clientY);
                
                // Check if we clicked on a span with greek-word class
                let target = event.target;
                if (target.classList && target.classList.contains('greek-word')) {
                    const greekWord = target.textContent;
                    console.log('Greek word span clicked:', greekWord);
                    try {
                        window.webkit.messageHandlers.greekWordHandler.postMessage(greekWord);
                        event.preventDefault();
                        event.stopPropagation();
                        return;
                    } catch (error) {
                        console.error('Error sending message:', error);
                        alert('Error: ' + error.message);
                    }
                }
                
                // Fallback to word extraction
                const greekWord = extractGreekWordFromClick(event);
                if (greekWord) {
                    console.log('Sending Greek word to Swift:', greekWord);
                    try {
                        window.webkit.messageHandlers.greekWordHandler.postMessage(greekWord);
                    } catch (error) {
                        console.error('Error sending message:', error);
                        alert('Error: ' + error.message);
                    }
                }
            });
            
            // Also handle touch events for iOS
            document.addEventListener('touchend', function(event) {
                if (event.changedTouches && event.changedTouches.length > 0) {
                    const touch = event.changedTouches[0];
                    const clickEvent = new MouseEvent('click', {
                        clientX: touch.clientX,
                        clientY: touch.clientY
                    });
                    
                    const greekWord = extractGreekWordFromClick(clickEvent);
                    if (greekWord) {
                        console.log('Sending Greek word to Swift (touch):', greekWord);
                        try {
                            window.webkit.messageHandlers.greekWordHandler.postMessage(greekWord);
                        } catch (error) {
                            console.error('Error sending message:', error);
                        }
                    }
                }
            });
        });
        </script>
        """
        
        // Process HTML to wrap Greek words in clickable spans
        let processedHTML = wrapGreekWordsInHTML(htmlContent)
        
        // Wrap HTML with proper styling and JavaScript
        let styledHTML = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                    font-size: \(Int(fontSize))px;
                    line-height: 1.5;
                    padding: 16px;
                    color: #000;
                    background-color: #FFF;
                    -webkit-user-select: none;
                    user-select: none;
                }
                @media (prefers-color-scheme: dark) {
                    body {
                        color: #FFF;
                        background-color: #000;
                    }
                }
                .entry { margin-bottom: 16px; }
                .headword { font-weight: bold; font-size: \(Int(fontSize * 1.2))px; }
                .definition { margin-top: 8px; }
                .etymology { font-style: italic; color: #666; }
                .example { margin-left: 20px; font-style: italic; }
                
                /* Make Greek text appear clickable */
                .greek-word {
                    color: #007AFF;
                    cursor: pointer;
                    -webkit-tap-highlight-color: rgba(0, 122, 255, 0.2);
                }
                .greek-word:hover {
                    text-decoration: underline;
                }
            </style>
        </head>
        <body>
            \(processedHTML)
            \(greekWordScript)
        </body>
        </html>
        """
        
        webView.loadHTMLString(styledHTML, baseURL: nil)
    }
    
    private func wrapGreekWordsInHTML(_ html: String) -> String {
        // Regular expression to match Greek words
        let greekPattern = "[\\u0370-\\u03FF\\u1F00-\\u1FFF]+"
        
        do {
            let regex = try NSRegularExpression(pattern: greekPattern, options: [])
            let nsString = html as NSString
            let matches = regex.matches(in: html, options: [], range: NSRange(location: 0, length: nsString.length))
            
            var result = html
            var offset = 0
            
            for match in matches {
                let matchRange = match.range
                let word = nsString.substring(with: matchRange)
                let replacement = "<span class='greek-word' data-word='\(word)' onclick='window.webkit.messageHandlers.greekWordHandler.postMessage(\"\(word)\"); event.stopPropagation(); return false;'>\(word)</span>"
                
                let adjustedRange = NSRange(location: matchRange.location + offset, length: matchRange.length)
                if let range = Range(adjustedRange, in: result) {
                    result.replaceSubrange(range, with: replacement)
                    offset += replacement.count - word.count
                }
            }
            
            return result
        } catch {
            // If regex fails, return original HTML
            return html
        }
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator(onGreekWordTapped: onGreekWordTapped)
    }
    
    class Coordinator: NSObject, WKNavigationDelegate, WKScriptMessageHandler {
        let onGreekWordTapped: ((String) -> Void)?
        
        init(onGreekWordTapped: ((String) -> Void)?) {
            self.onGreekWordTapped = onGreekWordTapped
        }
        
        func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            // Only allow the initial load
            if navigationAction.navigationType == .other {
                decisionHandler(.allow)
            } else {
                decisionHandler(.cancel)
            }
        }
        
        // Handle messages from JavaScript
        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            print("DEBUG: Received message: \(message.name) with body: \(message.body)")
            
            if message.name == "greekWordHandler" {
                if let greekWord = message.body as? String {
                    print("DEBUG: Greek word tapped in dictionary: '\(greekWord)'")
                    
                    // Call the callback on the main thread
                    DispatchQueue.main.async {
                        print("DEBUG: Calling onGreekWordTapped callback")
                        self.onGreekWordTapped?(greekWord)
                    }
                } else {
                    print("DEBUG: Message body is not a string: \(type(of: message.body))")
                }
            }
        }
    }
}

// Dictionary entry with confidence score
struct DictionaryMatch {
    let lemma: String
    let definition: String
    let morphInfo: String?
    let isDirectMatch: Bool
    let confidence: Double?
    let source: String?
}

// Improved ViewModel with better error handling
@MainActor
class ImprovedWordDetailViewModel: ObservableObject {
    @Published var dictionaryHtml = ""
    @Published var dictionaryPlain = ""
    @Published var lemma = ""
    @Published var morphInfo = ""
    @Published var wordMorphInfo: String? = nil  // Morphological info for the actual word tapped
    @Published var dictionaryEntries: [DictionaryMatch] = []
    @Published var normalizedConfidences: [Int] = []
    @Published var occurrences: [(bookId: String, authorName: String, workTitle: String, lineNumber: Int, lineText: String, matchingPositions: [Int])] = []
    @Published var totalOccurrenceCount = 0
    @Published var isLoadingDictionary = false
    @Published var isLoadingOccurrences = false
    @Published var hasLoadedOccurrences = false
    @Published var errorMessage = ""
    
    private let dictionaryDAO = DictionaryDAO()
    private let lemmaMapDAO = LemmaMapDAO()
    
    func loadDictionary(for word: Word) async {
        isLoadingDictionary = true
        errorMessage = ""
        dictionaryEntries = []
        
        do {
                // Database lifecycle managed by async architecture
            
            // Determine language from book ID
            let language = word.bookId.contains("tlg") ? "greek" : "latin"
            
            // Dictionary lookup now works for both Greek and Latin
            // (removed the Greek-only check)
            
            // First, get morphological info for the word if it's Greek
            if language == "greek" {
                // Query lemma_map directly for morphological info
                let morphQuery = "SELECT morph_info FROM lemma_map WHERE word_form = ? AND morph_info IS NOT NULL AND morph_info != '' ORDER BY confidence DESC LIMIT 1"
                let morphResults = try await DatabaseManagerAsync.shared.executeQuery(
                    morphQuery,
                    parameters: [word.word]
                ) { statement in
                    if let morphCString = sqlite3_column_text(statement, 0) {
                        return String(cString: morphCString)
                    }
                    return nil
                }

                if let morphInfo = morphResults.compactMap({ $0 }).first {
                    print("Found morphInfo for word '\(word.word)': '\(morphInfo)'")
                    await MainActor.run {
                        wordMorphInfo = morphInfo
                    }
                }
            }
            
            // Use the new getAllDictionaryEntries method to get ALL entries from all sources
            print("=== IMPROVED WORD DETAIL DEBUG ===")
            print("Getting all dictionary entries for word: '\(word.word)'")
            print("About to call getAllDictionaryEntries with word='\(word.word)', language='\(language)'")
            
            let allEntries = try await dictionaryDAO.getAllDictionaryEntries(word.word, language: language)
            
            print("getAllDictionaryEntries returned \(allEntries.count) entries")
            for entry in allEntries.prefix(3) {
                print("DEBUG loadDictionary: Entry - lemma: '\(entry.lemma)', morphInfo: '\(entry.morphInfo ?? "nil")', isDirectMatch: \(entry.isDirectMatch)")
            }
            
            if !allEntries.isEmpty {
                print("Found \(allEntries.count) dictionary entries from various sources")
                
                // Convert DictionaryEntry to DictionaryMatch for the view
                let mappedEntries = allEntries.map { entry in
                    DictionaryMatch(
                        lemma: entry.lemma,
                        definition: entry.definition,
                        morphInfo: entry.morphInfo,
                        isDirectMatch: entry.isDirectMatch,
                        confidence: entry.confidence,
                        source: entry.source
                    )
                }
                
                // Calculate normalized confidences if we have multiple entries with confidence scores
                let confidenceEntries = mappedEntries.compactMap { entry -> (DictionaryMatch, Double)? in
                    if let conf = entry.confidence {
                        return (entry, conf)
                    }
                    return nil
                }
                
                var normalizedConfidenceValues: [Int] = []
                if !confidenceEntries.isEmpty {
                    let totalConfidence = confidenceEntries.reduce(0.0) { $0 + $1.1 }
                    if totalConfidence > 0 {
                        normalizedConfidenceValues = confidenceEntries.map { entry in
                            Int(round((entry.1 / totalConfidence) * 100))
                        }
                    }
                }
                
                await MainActor.run {
                    print("DEBUG: Setting dictionaryEntries with \(mappedEntries.count) entries")
                    dictionaryEntries = mappedEntries
                    normalizedConfidences = normalizedConfidenceValues
                    
                    // For UI compatibility, set the main fields from the first/best entry
                    if let firstEntry = mappedEntries.first {
                        lemma = firstEntry.lemma
                        morphInfo = firstEntry.morphInfo ?? ""
                        if firstEntry.definition.contains("<") {
                            dictionaryHtml = firstEntry.definition
                        } else {
                            dictionaryPlain = firstEntry.definition
                        }
                        print("DEBUG: First entry - lemma: '\(firstEntry.lemma)', has definition: \(!firstEntry.definition.isEmpty)")
                    }
                    
                    print("DEBUG: After setting - dictionaryEntries.count = \(dictionaryEntries.count)")
                    print("DEBUG: dictionaryEntries.isEmpty = \(dictionaryEntries.isEmpty)")
                    isLoadingDictionary = false
                }
            } else {
                print("No dictionary entries found for '\(word.word)'")
                await MainActor.run {
                    errorMessage = "No dictionary entry found"
                    isLoadingDictionary = false
                }
            }
        } catch {
            print("!!! ERROR IN loadDictionary: \(error) !!!")
            print("ERROR: Failed to load dictionary: \(error)")
            print("Error type: \(type(of: error))")
            print("Full error: \(String(describing: error))")
            await MainActor.run {
                errorMessage = "Failed to load dictionary: \(error.localizedDescription)"
                isLoadingDictionary = false
            }
        }
    }
    
    private func findMorphologicallyRelatedForms(_ word: String) -> [String] {
        // Comprehensive Greek morphological patterns for finding related forms
        var relatedForms: Set<String> = [] // Use Set to avoid duplicates
        
        // 2nd Declension Masculine/Neuter patterns (like λαός)
        if word.hasSuffix("ων") {
            // Genitive plural → other forms
            let stem = String(word.dropLast(2))
            if stem.count >= 2 {
                relatedForms.insert(stem + "οι")   // nom pl
                relatedForms.insert(stem + "ος")   // nom sg
                relatedForms.insert(stem + "ους")  // acc pl
                relatedForms.insert(stem + "ον")   // acc sg
                relatedForms.insert(stem + "οις")  // dat pl
                relatedForms.insert(stem + "ῳ")    // dat sg
                relatedForms.insert(stem + "ου")   // gen sg
                relatedForms.insert(stem + "ε")    // voc sg
            }
        } else if word.hasSuffix("ους") {
            // Accusative plural → other forms
            let stem = String(word.dropLast(3))
            if stem.count >= 2 {
                relatedForms.insert(stem + "οι")   // nom pl
                relatedForms.insert(stem + "ος")   // nom sg
                relatedForms.insert(stem + "ον")   // acc sg
                relatedForms.insert(stem + "ων")   // gen pl
                relatedForms.insert(stem + "ου")   // gen sg
                relatedForms.insert(stem + "οις")  // dat pl
                relatedForms.insert(stem + "ῳ")    // dat sg
            }
        } else if word.hasSuffix("οις") {
            // Dative plural → other forms
            let stem = String(word.dropLast(3))
            if stem.count >= 2 {
                relatedForms.insert(stem + "οι")   // nom pl
                relatedForms.insert(stem + "ος")   // nom sg
                relatedForms.insert(stem + "ους")  // acc pl
                relatedForms.insert(stem + "ον")   // acc sg
                relatedForms.insert(stem + "ων")   // gen pl
                relatedForms.insert(stem + "ου")   // gen sg
                relatedForms.insert(stem + "ῳ")    // dat sg
            }
        } else if word.hasSuffix("ου") {
            // Genitive singular → other forms
            let stem = String(word.dropLast(2))
            if stem.count >= 2 {
                relatedForms.insert(stem + "ος")   // nom sg
                relatedForms.insert(stem + "ον")   // acc sg
                relatedForms.insert(stem + "ῳ")    // dat sg
                relatedForms.insert(stem + "ε")    // voc sg
                relatedForms.insert(stem + "οι")   // nom pl
                relatedForms.insert(stem + "ους")  // acc pl
                relatedForms.insert(stem + "ων")   // gen pl
                relatedForms.insert(stem + "οις")  // dat pl
            }
        } else if word.hasSuffix("ῳ") || word.hasSuffix("ωι") {
            // Dative singular (with or without iota subscript) → other forms
            let stem = String(word.dropLast(word.hasSuffix("ωι") ? 2 : 1))
            if stem.count >= 2 {
                relatedForms.insert(stem + "ος")   // nom sg
                relatedForms.insert(stem + "ον")   // acc sg
                relatedForms.insert(stem + "ου")   // gen sg
                relatedForms.insert(stem + "ε")    // voc sg
                relatedForms.insert(stem + "οι")   // nom pl
                relatedForms.insert(stem + "ους")  // acc pl
                relatedForms.insert(stem + "ων")   // gen pl
                relatedForms.insert(stem + "οις")  // dat pl
            }
        } else if word.hasSuffix("ον") {
            // Accusative singular → other forms
            let stem = String(word.dropLast(2))
            if stem.count >= 2 {
                relatedForms.insert(stem + "ος")   // nom sg
                relatedForms.insert(stem + "ου")   // gen sg
                relatedForms.insert(stem + "ῳ")    // dat sg
                relatedForms.insert(stem + "ε")    // voc sg
                relatedForms.insert(stem + "οι")   // nom pl
                relatedForms.insert(stem + "ους")  // acc pl
                relatedForms.insert(stem + "ων")   // gen pl
                relatedForms.insert(stem + "οις")  // dat pl
            }
        } else if word.hasSuffix("ε") {
            // Vocative singular → other forms
            let stem = String(word.dropLast(1))
            if stem.count >= 2 {
                relatedForms.insert(stem + "ος")   // nom sg
                relatedForms.insert(stem + "ον")   // acc sg
                relatedForms.insert(stem + "ου")   // gen sg
                relatedForms.insert(stem + "ῳ")    // dat sg
                relatedForms.insert(stem + "οι")   // nom pl
                relatedForms.insert(stem + "ους")  // acc pl
                relatedForms.insert(stem + "ων")   // gen pl
                relatedForms.insert(stem + "οις")  // dat pl
            }
        }
        
        // 1st Declension Feminine patterns
        if word.hasSuffix("ας") {
            // Accusative plural → other forms
            let stem = String(word.dropLast(2))
            if stem.count >= 2 {
                relatedForms.insert(stem + "αι")   // nom pl
                relatedForms.insert(stem + "α")    // nom/acc sg (alpha-pure)
                relatedForms.insert(stem + "η")    // nom sg (eta-type)
                relatedForms.insert(stem + "ην")   // acc sg (eta-type)
                relatedForms.insert(stem + "ων")   // gen pl
                relatedForms.insert(stem + "ης")   // gen sg
                relatedForms.insert(stem + "ῃ")    // dat sg
                relatedForms.insert(stem + "αις")  // dat pl
            }
        } else if word.hasSuffix("αις") {
            // Dative plural → other forms
            let stem = String(word.dropLast(3))
            if stem.count >= 2 {
                relatedForms.insert(stem + "αι")   // nom pl
                relatedForms.insert(stem + "ας")   // acc pl
                relatedForms.insert(stem + "ων")   // gen pl
                relatedForms.insert(stem + "α")    // nom/acc sg
                relatedForms.insert(stem + "η")    // nom sg (eta-type)
                relatedForms.insert(stem + "ης")   // gen sg
                relatedForms.insert(stem + "ῃ")    // dat sg
            }
        } else if word.hasSuffix("ης") {
            // Genitive singular (1st decl) → other forms
            let stem = String(word.dropLast(2))
            if stem.count >= 2 {
                relatedForms.insert(stem + "α")    // nom sg (alpha-type)
                relatedForms.insert(stem + "η")    // nom sg (eta-type)
                relatedForms.insert(stem + "αν")   // acc sg (alpha-type)
                relatedForms.insert(stem + "ην")   // acc sg (eta-type)
                relatedForms.insert(stem + "ῃ")    // dat sg
                relatedForms.insert(stem + "αι")   // nom pl
                relatedForms.insert(stem + "ας")   // acc pl
                relatedForms.insert(stem + "ων")   // gen pl
                relatedForms.insert(stem + "αις")  // dat pl
            }
        } else if word.hasSuffix("ῃ") || word.hasSuffix("ηι") {
            // Dative singular (1st decl) → other forms
            let stem = String(word.dropLast(word.hasSuffix("ηι") ? 2 : 1))
            if stem.count >= 2 {
                relatedForms.insert(stem + "α")    // nom sg (alpha-type)
                relatedForms.insert(stem + "η")    // nom sg (eta-type)
                relatedForms.insert(stem + "αν")   // acc sg
                relatedForms.insert(stem + "ην")   // acc sg (eta-type)
                relatedForms.insert(stem + "ης")   // gen sg
                relatedForms.insert(stem + "αι")   // nom pl
                relatedForms.insert(stem + "ας")   // acc pl
                relatedForms.insert(stem + "ων")   // gen pl
                relatedForms.insert(stem + "αις")  // dat pl
            }
        } else if word.hasSuffix("αν") || word.hasSuffix("ην") {
            // Accusative singular (1st decl) → other forms
            let stem = String(word.dropLast(2))
            if stem.count >= 2 {
                relatedForms.insert(stem + "α")    // nom sg (alpha-type)
                relatedForms.insert(stem + "η")    // nom sg (eta-type)
                relatedForms.insert(stem + "ης")   // gen sg
                relatedForms.insert(stem + "ῃ")    // dat sg
                relatedForms.insert(stem + "αι")   // nom pl
                relatedForms.insert(stem + "ας")   // acc pl
                relatedForms.insert(stem + "ων")   // gen pl
                relatedForms.insert(stem + "αις")  // dat pl
            }
        }
        
        // 3rd Declension common patterns (simplified)
        if word.hasSuffix("ος") && word.count > 3 {
            // Could be 3rd decl genitive singular
            let stem = String(word.dropLast(2))
            if stem.count >= 2 {
                // Try common 3rd declension nominative endings
                relatedForms.insert(stem)          // consonant stem
                relatedForms.insert(stem + "ς")    // sigma ending
                relatedForms.insert(stem + "ων")   // gen pl
                relatedForms.insert(stem + "σι")   // dat pl
                relatedForms.insert(stem + "ας")   // acc pl
                relatedForms.insert(stem + "ες")   // nom/acc pl (some types)
                relatedForms.insert(stem + "α")    // acc sg (some types)
                relatedForms.insert(stem + "ι")    // dat sg
            }
        } else if word.hasSuffix("σι") || word.hasSuffix("σιν") {
            // Dative plural (3rd decl) → other forms
            let stem = String(word.dropLast(word.hasSuffix("σιν") ? 3 : 2))
            if stem.count >= 2 {
                relatedForms.insert(stem + "ες")   // nom pl
                relatedForms.insert(stem + "ας")   // acc pl
                relatedForms.insert(stem + "ων")   // gen pl
                relatedForms.insert(stem)          // nom sg (consonant stem)
                relatedForms.insert(stem + "ς")    // nom sg (sigma)
                relatedForms.insert(stem + "ος")   // gen sg
                relatedForms.insert(stem + "α")    // acc sg
                relatedForms.insert(stem + "ι")    // dat sg
            }
        }
        
        // Remove the original word from related forms
        relatedForms.remove(word)
        
        // Convert back to array and limit results for performance
        return Array(relatedForms.prefix(20)) // Limit to 20 forms to avoid too many lookups
    }
    
    func loadOccurrences(for word: Word) async {
        await MainActor.run {
            isLoadingOccurrences = true
        }
        
        do {
                // Database lifecycle managed by async architecture
            
            // Determine language
            let language = word.bookId.contains("tlg") ? "greek" : "latin"
            
            // Occurrences lookup now works for both Greek and Latin
            // (removed the Greek-only check)
            
            // Get the search term
            let searchTerm = lemma.isEmpty ? word.word : lemma  // Use original word or lemma
            
            print("DEBUG: Searching for occurrences of '\(searchTerm)' across entire corpus")
            print("DEBUG: Word: '\(word.word)', Lemma: '\(lemma)'")
            
            // Build search condition based on whether we have a lemma
            var searchCondition: String
            var searchParams: [String]
            
            if !lemma.isEmpty {
                // If we have a lemma, search for all forms of that lemma (for any language)
                print("DEBUG: Searching for all forms of lemma '\(lemma)' (language: \(language))")
                
                // Get all word forms that map to this lemma
                let lemmaFormsQuery = """
                    SELECT DISTINCT word_form FROM lemma_map
                    WHERE lemma = ?
                """
                var lemmaForms = try await DatabaseManagerAsync.shared.executeQuery(
                    lemmaFormsQuery,
                    parameters: [lemma]
                ) { statement in
                    if let formCString = sqlite3_column_text(statement, 0) {
                        return String(cString: formCString)
                    }
                    return ""
                }.filter { !$0.isEmpty }
                
                // Also include the lemma itself as a word form (in case it appears as a word)
                if !lemmaForms.contains(lemma) {
                    lemmaForms.append(lemma)
                }
                
                // Also include the original word if not already in the list
                if !lemmaForms.contains(word.word) {
                    lemmaForms.append(word.word)
                }
                
                print("DEBUG: Found \(lemmaForms.count) word forms for lemma '\(lemma)': \(lemmaForms)")
                
                if !lemmaForms.isEmpty {
                    // Search for any of these word forms
                    let placeholders = lemmaForms.map { _ in "?" }.joined(separator: ", ")
                    searchCondition = "wd.word IN (\(placeholders))"
                    searchParams = lemmaForms
                } else {
                    // Fallback to just the lemma itself
                    searchCondition = "wd.word = ?"
                    searchParams = [lemma]
                }
            } else {
                // Direct word search (no lemma or Latin)
                searchCondition = "wd.word = ?"
                searchParams = [word.word]
            }
            
            // First, get the total count of occurrences
            let countQuery = """
                SELECT COUNT(DISTINCT tl.book_id || '-' || tl.line_number)
                FROM text_lines tl
                JOIN words wd ON wd.book_id = tl.book_id AND wd.line_number = tl.line_number
                WHERE \(searchCondition)
            """

            let countResults = try await DatabaseManagerAsync.shared.executeQuery(
                countQuery,
                parameters: searchParams
            ) { statement in
                return Int(sqlite3_column_int(statement, 0))
            }

            totalOccurrenceCount = countResults.first ?? 0
            print("DEBUG: Total occurrences found: \(totalOccurrenceCount)")
            
            // Find all occurrences across the entire corpus with author and work info (limited to 500)
            // Also get word positions for highlighting
            let query = """
                SELECT DISTINCT
                    tl.book_id,
                    a.name as author_name,
                    COALESCE(w.title_english, w.title) as work_title,
                    tl.line_number,
                    tl.line_text,
                    GROUP_CONCAT(wd.word_position) as matching_positions
                FROM text_lines tl
                JOIN words wd ON wd.book_id = tl.book_id AND wd.line_number = tl.line_number
                JOIN books b ON b.id = tl.book_id
                JOIN works w ON w.id = b.work_id
                JOIN authors a ON a.id = w.author_id
                WHERE \(searchCondition)
                GROUP BY tl.book_id, tl.line_number
                ORDER BY a.name, COALESCE(w.title_english, w.title), tl.line_number
                LIMIT 500
            """

            let results = try await DatabaseManagerAsync.shared.executeQuery(
                query,
                parameters: searchParams
            ) { statement in
                var bookId = ""
                var authorName = ""
                var workTitle = ""
                var lineText = ""
                var matchingPositions: [Int] = []

                if let bookIdCString = sqlite3_column_text(statement, 0) {
                    bookId = String(cString: bookIdCString)
                }
                if let authorCString = sqlite3_column_text(statement, 1) {
                    authorName = String(cString: authorCString)
                }
                if let workCString = sqlite3_column_text(statement, 2) {
                    workTitle = String(cString: workCString)
                }
                let lineNumber = Int(sqlite3_column_int(statement, 3))
                if let textCString = sqlite3_column_text(statement, 4) {
                    lineText = String(cString: textCString)
                }
                if let positionsCString = sqlite3_column_text(statement, 5) {
                    let positionsString = String(cString: positionsCString)
                    matchingPositions = positionsString.split(separator: ",").compactMap { Int($0) }
                }

                return (
                    bookId: bookId,
                    authorName: authorName,
                    workTitle: workTitle,
                    lineNumber: lineNumber,
                    lineText: lineText,
                    matchingPositions: matchingPositions
                )
            }

            occurrences = results
            print("DEBUG: Displaying \(results.count) occurrences (out of \(totalOccurrenceCount) total)")
            
        } catch {
            print("DEBUG: Failed to load occurrences: \(error)")
        }
        
        await MainActor.run {
            isLoadingOccurrences = false
            hasLoadedOccurrences = true
        }
    }
}
