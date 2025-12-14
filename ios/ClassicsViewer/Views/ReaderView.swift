import SwiftUI
import AVFoundation

struct ReaderView: View {
    @StateObject private var viewModel: ReaderViewModel
    @StateObject private var audioPlayer = AudioPlayer.shared
    @State private var showingPagePicker = false
    @State private var selectedWord: Word?
    @State private var selectedLineForNote: TextLine?
    @State private var targetLineNumber: Int = 0
    @State private var shouldNavigate = false
    @State private var navigateToHesiod = false
    @State private var navigateToOccurrence = false
    @State private var occurrenceDestination: (bookId: String, lineNumber: Int)?
    @State private var showingCheckDefinitions = false
    @State private var checkingDefinitions = false
    @State private var wordsWithoutDefinitions: Set<String> = []
    @State private var wordsWithMorphologyOnly: Set<String> = []
    @State private var definitionCheckProgress: Float = 0.0
    @State private var definitionCheckCancelled = false
    // Find in text state
    @State private var showingFindInText = false
    @State private var findQuery: String = ""
    @State private var lastFindQuery: String = ""
    @State private var findResults: [FindResult] = []
    @State private var currentFindIndex: Int = -1
    @State private var isSearching = false
    @EnvironmentObject var searchContext: SearchNavigationContext
    @Environment(\.colorScheme) private var colorScheme

    init(book: Book, author: Author, initialPage: Int? = nil, targetLineNumber: Int? = nil) {
        let vm = ReaderViewModel(book: book, author: author)
        if let page = initialPage {
            vm.currentPage = page
        }
        if let targetLine = targetLineNumber {
            vm.targetLineNumber = targetLine
        }
        _viewModel = StateObject(wrappedValue: vm)
    }
    
    var body: some View {
        ZStack {
            VStack(spacing: 0) {
                // Search navigation bar (if from search)
                if searchContext.isFromSearch {
                    SearchNavigationBar()
                }

                // Content area
                if viewModel.isLoading {
                    LoadingView(message: "Loading text...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    contentView
                }

                // Bottom navigation bar
                ReaderBottomBar(
                    currentPage: viewModel.currentPage,
                    totalPages: viewModel.totalPages,
                    currentViewLabel: viewModel.currentViewLabel,
                    hasTranslations: viewModel.hasTranslations,
                    isLoading: viewModel.isLoading,
                    onPreviousPage: viewModel.previousPage,
                    onNextPage: viewModel.nextPage,
                    onPageTap: { showingPagePicker = true },
                    onCycleView: viewModel.navigateToNextView
                )
            }
            
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .principal) {
                VStack(spacing: 2) {
                    Text(viewModel.navigationTitle)
                        .font(.headline)
                        .fontWeight(.semibold)
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)

                    Text(viewModel.navigationSubtitle)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .lineLimit(1)
                }
            }

            ToolbarItemGroup(placement: .navigationBarTrailing) {
                // Find in text button
                Button(action: {
                    showingFindInText = true
                }) {
                    Image(systemName: "magnifyingglass")
                }

                // Check definitions button
                Button(action: {
                    if checkingDefinitions {
                        // If already checking, cancel the operation
                        definitionCheckCancelled = true
                        wordsWithoutDefinitions.removeAll()
                        wordsWithMorphologyOnly.removeAll()
                        checkingDefinitions = false
                    } else {
                        // Start checking definitions
                        showingCheckDefinitions = true
                    }
                }) {
                    Image(systemName: checkingDefinitions ? "at.circle.fill" : "at.circle")
                        .foregroundColor(checkingDefinitions ? .blue : nil)
                }
            }
        }
        .onAppear {
            viewModel.loadInitialData()
            // Handle search navigation if coming from search
            handleSearchNavigation()
        }
        .onChange(of: searchContext.currentResultIndex) {
            handleSearchNavigation()
        }
        .onReceive(NotificationCenter.default.publisher(for: .navigateToReader)) { notification in
            handleReaderNavigation(notification)
        }
        .onChange(of: shouldNavigate) {
            if shouldNavigate && targetLineNumber > 0 {
                print("DEBUG: onChange triggered - navigating to line \(targetLineNumber)")
                let targetPage = (targetLineNumber - 1) / 100 + 1
                print("DEBUG: Calculated target page: \(targetPage)")
                viewModel.goToPage(targetPage)
                // Reset the flags
                shouldNavigate = false
                targetLineNumber = 0
            }
        }
        .sheet(isPresented: $showingPagePicker) {
            PagePickerView(
                currentPage: viewModel.currentPage,
                totalPages: viewModel.totalPages,
                onPageSelected: { page in
                    viewModel.goToPage(page)
                    showingPagePicker = false
                }
            )
        }
        .navigationDestination(isPresented: $navigateToHesiod) {
            ReaderView(
                book: Book(
                    id: "tlg0020.tlg001.001",  // Correct database ID format
                    workId: "tlg0020.tlg001",
                    bookNumber: 1,
                    label: "Book 1",
                    startLine: 1,
                    endLine: 1022,
                    lineCount: 1022
                ),
                author: Author(
                    id: "tlg0020",
                    name: "Hesiod",
                    nameAlt: "Ἡσίοδος",
                    language: "greek",
                    hasTranslations: 1
                )
            )
        }
        .sheet(item: $selectedWord) { word in
            ImprovedWordDetailView(
                word: word,
                viewModel: viewModel
            )
        }
        .sheet(item: $selectedLineForNote) { line in
            NoteEditDialog(
                author: viewModel.author,
                work: viewModel.work ?? Work(id: viewModel.book.workId, authorId: viewModel.author.id, title: "Unknown Work", titleAlt: nil, titleEnglish: nil, type: nil, urn: nil, description: nil),
                book: viewModel.book,
                line: line,
                onBookmarkSaved: {
                    viewModel.refreshBookmarks()
                }
            )
        }
        .sheet(isPresented: $showingFindInText) {
            FindInTextSheet(
                query: $findQuery,
                lastQuery: lastFindQuery,
                resultsCount: findResults.count,
                currentIndex: currentFindIndex,
                isSearching: isSearching,
                onFind: { query in
                    Task {
                        await performFindInText(query: query)
                    }
                },
                onFindNext: {
                    navigateToNextFindResult()
                },
                onFindPrevious: {
                    navigateToPreviousFindResult()
                }
            )
            .presentationDetents([.height(280)])
        }
        .alert("Check Definitions", isPresented: $showingCheckDefinitions) {
            Button("Cancel", role: .cancel) { }
            Button("Yes") {
                Task {
                    await checkDefinitionsForCurrentPage()
                }
            }
        } message: {
            Text("Find all words without definitions on this page?")
        }
        .overlay(
            // Loading overlay when checking definitions
            checkingDefinitions ? 
            ZStack {
                Color.black.opacity(0.4)
                    .ignoresSafeArea()
                    .allowsHitTesting(true) // Prevent interaction with underlying views
                
                VStack(spacing: 20) {
                    ProgressView()
                        .scaleEffect(1.5)
                        .tint(.white)
                    
                    VStack(spacing: 8) {
                        Text("Checking Definitions...")
                            .font(.headline)
                            .foregroundColor(.white)
                        
                        if definitionCheckProgress > 0 {
                            ProgressView(value: definitionCheckProgress)
                                .progressViewStyle(LinearProgressViewStyle(tint: .blue))
                                .frame(width: 200)
                        }
                        
                        Button("Cancel") {
                            definitionCheckCancelled = true
                        }
                        .buttonStyle(.bordered)
                        .foregroundColor(.white)
                        .background(Color.red.opacity(0.7))
                        .cornerRadius(8)
                    }
                }
                .padding(30)
                .background(Color.black.opacity(0.7))
                .cornerRadius(15)
            } : nil
        )
    }
    
    private var contentView: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    if viewModel.currentViewIndex == 0 {
                        greekTextView
                    } else {
                        translationView
                    }
                }
                .padding()
                .onAppear {
                    // Scroll to target line if specified
                    if let targetLine = viewModel.targetLineNumber {
                        // Find the relative position within the current page
                        let startLine = (viewModel.currentPage - 1) * viewModel.linesPerPage.rawValue + 1
                        let relativeLineIndex = targetLine - startLine

                        if relativeLineIndex >= 0 && relativeLineIndex < viewModel.lines.count {
                            let targetLineId = viewModel.lines[relativeLineIndex].id
                            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                                withAnimation(.easeInOut(duration: 0.5)) {
                                    proxy.scrollTo(targetLineId, anchor: .center)
                                }
                            }
                        }
                    }
                }
                .onChange(of: viewModel.lines) {
                    // Also scroll when lines are updated (e.g., page changes)
                    if let targetLine = viewModel.targetLineNumber {
                        let startLine = (viewModel.currentPage - 1) * viewModel.linesPerPage.rawValue + 1
                        let relativeLineIndex = targetLine - startLine

                        if relativeLineIndex >= 0 && relativeLineIndex < viewModel.lines.count {
                            let targetLineId = viewModel.lines[relativeLineIndex].id
                            DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
                                withAnimation(.easeInOut(duration: 0.5)) {
                                    proxy.scrollTo(targetLineId, anchor: .center)
                                }
                            }
                            // Clear the target after scrolling to it once
                            viewModel.targetLineNumber = nil
                        }
                    }
                }
            }
        }
    }
    
    private var greekTextView: some View {
        VStack(alignment: .leading, spacing: viewModel.lineSpacing) {
            if viewModel.lines.isEmpty {
                VStack(spacing: 20) {
                    Image(systemName: "doc.text.magnifyingglass")
                        .font(.system(size: 60))
                        .foregroundColor(.secondary)
                    Text("No text available")
                        .font(.headline)
                        .foregroundColor(.secondary)
                    Text("Book: \(viewModel.book.id)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text("Total lines: \(viewModel.totalPages * viewModel.linesPerPage.rawValue)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .padding(40)
            }
            ForEach(Array(viewModel.lines.enumerated()), id: \.element.id) { index, line in
                LineTextView(
                    line: line,
                    book: viewModel.book,
                    author: viewModel.author,
                    fontSize: viewModel.fontSize,
                    isGreek: viewModel.author.language == "greek",
                    showSpeaker: shouldShowSpeaker(at: index),
                    hasBookmark: viewModel.hasBookmark(for: line.lineNumber),
                    hasAudio: viewModel.hasAudioForLine(line.lineNumber),
                    isPlayingAudio: audioPlayer.isPlaying && audioPlayer.currentLineNumber == line.lineNumber,
                    wordsWithoutDefinitions: wordsWithoutDefinitions,
                    wordsWithMorphologyOnly: wordsWithMorphologyOnly,
                    highlightedWords: searchContext.highlightedWords,
                    isHighlightedLine: isHighlightedLine(line) || isFindHighlightedLine(line),
                    onWordTapped: { word in
                        print("DEBUG: greekTextView onWordTapped called with word: \(word.word)")
                        selectedWord = word
                        print("DEBUG: selectedWord set to: \(word.word)")
                    },
                    onLineNumberTapped: {
                        selectedLineForNote = line
                    },
                    onBookmarkTapped: {
                        selectedLineForNote = line
                    },
                    onAudioTapped: {
                        Task {
                            // Map work ID to audio format
                            let audioWorkId = if viewModel.book.workId.contains("tlg0012.tlg001") {
                                "homer_iliad"
                            } else {
                                viewModel.book.workId.replacingOccurrences(of: ".001", with: "")
                                    .replacingOccurrences(of: ".002", with: "")
                                    .replacingOccurrences(of: ".003", with: "")
                            }
                            let bookNumber = String(viewModel.book.bookNumber)

                            if audioPlayer.isPlaying && audioPlayer.currentLineNumber == line.lineNumber {
                                audioPlayer.stop()
                            } else {
                                await audioPlayer.playAudioForLine(
                                    workId: audioWorkId,
                                    bookId: bookNumber,
                                    lineNumber: line.lineNumber
                                )
                            }
                        }
                    }
                )
            }
        }
    }
    
    private func shouldShowSpeaker(at index: Int) -> Bool {
        let line = viewModel.lines[index]
        guard let speaker = line.speaker, !speaker.isEmpty else { return false }
        
        // Show speaker if it's the first line or if speaker changed
        if index == 0 { return true }
        
        let previousLine = viewModel.lines[index - 1]
        return previousLine.speaker != speaker
    }
    
    private var translationView: some View {
        let translations = viewModel.getCurrentTranslations()
        return VStack(alignment: .leading, spacing: 20) {
            ForEach(Array(translations.enumerated()), id: \.element.id) { index, segment in
                VStack(alignment: .leading, spacing: 8) {
                    // Show speaker if present and different from previous
                    if shouldShowTranslationSpeaker(at: index),
                       let speaker = segment.speaker, !speaker.isEmpty {
                        Text(speaker.uppercased())
                            .font(.system(size: viewModel.fontSize * 1.5, weight: .bold))
                            .foregroundColor(speakerColor)
                            .padding(.bottom, 4)
                    }

                    Text("Lines \(segment.startLine)-\(segment.endLine ?? segment.startLine)")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    // Check for interlinear format (contains Markdown tables with pipe syntax)
                    // Only process as interlinear if translator is "Interlinear" to avoid processing other translations
                    if segment.translationText.contains("| ") && segment.translator?.contains("Interlinear") == true {
                        // This is interlinear format with Markdown tables
                        InterlinearTextView(
                            text: segment.translationText,
                            fontSize: viewModel.fontSize,
                            onWordTapped: { greekWord in
                                // Create a Word object for dictionary lookup
                                // Use line number from the segment
                                let word = Word(
                                    id: 0,
                                    word: greekWord,
                                    bookId: viewModel.book.id,
                                    lineNumber: segment.startLine,
                                    sequenceNumber: 0,
                                    wordPosition: 0
                                )
                                selectedWord = word
                            }
                        )
                    } else {
                        // Regular translation text
                        Text(segment.translationText)
                            .font(.system(size: viewModel.fontSize))
                            .lineSpacing(4)
                    }
                }
            }

            if translations.isEmpty {
                Text("No translation available for this section")
                    .font(.body)
                    .foregroundColor(.secondary)
                    .italic()
                    .padding(.vertical, 40)
            }
        }
    }

    private func shouldShowTranslationSpeaker(at index: Int) -> Bool {
        let translations = viewModel.getCurrentTranslations()
        guard index < translations.count else { return false }
        let segment = translations[index]
        guard let speaker = segment.speaker, !speaker.isEmpty else { return false }
        
        // Show speaker if it's the first segment or if speaker changed
        if index == 0 { return true }

        let previousSegment = translations[index - 1]
        return previousSegment.speaker != speaker
    }
    
    private var speakerColor: Color {
        // Match Android colors for speakers in translations
        return colorScheme == .dark ? Color(hex: "#66B2FF") : Color(hex: "#0066CC")
    }
}

struct LineTextView: View {
    let line: TextLine
    let book: Book
    let author: Author
    let fontSize: CGFloat
    let isGreek: Bool
    let showSpeaker: Bool
    let hasBookmark: Bool
    let hasAudio: Bool
    let isPlayingAudio: Bool
    let wordsWithoutDefinitions: Set<String>
    let wordsWithMorphologyOnly: Set<String>
    let highlightedWords: Set<String>
    let isHighlightedLine: Bool
    let onWordTapped: (Word) -> Void
    let onLineNumberTapped: () -> Void
    let onBookmarkTapped: () -> Void
    let onAudioTapped: () -> Void
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            // Speaker name if present and should be shown
            if showSpeaker, let speaker = line.speaker, !speaker.isEmpty {
                Text(speaker.uppercased())
                    .font(.system(size: fontSize + 2, weight: .bold))
                    .padding(.leading, 52) // Align with text (40 + 12 spacing)
                    .padding(.top, 8)
                    .onTapGesture {
                        // Treat speaker as a word for dictionary lookup
                        let speakerWord = Word(
                            id: 0,
                            word: speaker,
                            bookId: book.id,
                            lineNumber: line.lineNumber,
                            sequenceNumber: line.sequenceNumber,
                            wordPosition: 0
                        )
                        onWordTapped(speakerWord)
                    }
            }
            
            HStack(alignment: .top, spacing: 8) {
                // Bookmark indicator on the left - clickable
                if hasBookmark {
                    Button(action: onBookmarkTapped) {
                        Image(systemName: "bookmark.fill")
                            .font(.system(size: 10))
                            .foregroundColor(.blue)
                    }
                } else {
                    Color.clear
                        .frame(width: 0)
                }

                // Audio button if available
                if hasAudio {
                    Button(action: onAudioTapped) {
                        Image(systemName: isPlayingAudio ? "stop.fill" : "play.fill")
                            .font(.system(size: 12))
                            .foregroundColor(.black)
                    }
                } else {
                    Color.clear
                        .frame(width: 0)
                }

                // Line number - tappable for notes
                Text("\(line.lineNumber)")
                    .font(.system(size: 16, design: .monospaced))
                    .foregroundColor(.secondary)
                    .frame(width: 45, alignment: .trailing)
                    .onTapGesture {
                        onLineNumberTapped()
                    }

                // Line text - now without spacer disruption
                TappableTextView(
                    text: line.lineText,
                    fontSize: fontSize,
                    isGreek: isGreek,
                    bookId: book.id,
                    lineNumber: line.lineNumber,
                    sequenceNumber: line.sequenceNumber,
                    onWordTapped: onWordTapped,
                    wordsWithoutDefinitions: wordsWithoutDefinitions,
                    wordsWithMorphologyOnly: wordsWithMorphologyOnly,
                    searchHighlightedWords: highlightedWords
                )
                .background(isHighlightedLine ? Color.yellow.opacity(0.2) : Color.clear)
            }
        }
    }
    
}

// Extension for ReaderView functions
extension ReaderView {
    private func isHighlightedLine(_ line: TextLine) -> Bool {
        guard let currentResult = searchContext.currentResult else { return false }
        return line.lineNumber == currentResult.lineNumber
    }

    private func handleSearchNavigation() {
        guard searchContext.isFromSearch,
              let currentResult = searchContext.currentResult else { return }

        // Navigate to the page containing the current search result
        let targetPage = (currentResult.lineNumber - 1) / viewModel.linesPerPage.rawValue + 1
        if viewModel.currentPage != targetPage {
            viewModel.goToPage(targetPage)
        }

        // Set target line for scrolling
        viewModel.targetLineNumber = currentResult.lineNumber
    }

    private func handleReaderNavigation(_ notification: Notification) {
        guard let userInfo = notification.userInfo,
              let bookId = userInfo["bookId"] as? String,
              let lineNumber = userInfo["lineNumber"] as? Int,
              let fromSearch = userInfo["fromSearch"] as? Bool,
              fromSearch == true else { return }

        // Check if this is the correct book
        if bookId == viewModel.book.id {
            // Navigate to the correct page and line
            let targetPage = (lineNumber - 1) / viewModel.linesPerPage.rawValue + 1
            viewModel.goToPage(targetPage)
            viewModel.targetLineNumber = lineNumber
        }
    }
    private func checkDefinitionsForCurrentPage() async {
        // Only works on Greek/Latin text view, not translation
        guard viewModel.currentViewIndex == 0 else {
            return
        }
        
        // Reset state
        definitionCheckCancelled = false
        definitionCheckProgress = 0.0
        checkingDefinitions = true
        wordsWithoutDefinitions.removeAll()
        wordsWithMorphologyOnly.removeAll()
        
        defer {
            // Always clean up when function ends
            Task { @MainActor in
                checkingDefinitions = false
                definitionCheckProgress = 0.0
            }
        }
        
        let language = viewModel.author.language
        
        // Collect all unique words first to show accurate progress
        var allWords: Set<String> = []
        for line in viewModel.lines {
            let words = line.lineText.split { !$0.isLetter && $0 != "'" && $0 != "'" && $0 != "ʼ" }
                .map { String($0) }
                .filter { !$0.isEmpty }
            allWords.formUnion(words)
        }
        
        let totalWords = allWords.count
        guard totalWords > 0 else { return }
        
        var processedCount = 0
        
        // Process words one at a time to avoid concurrent database access
        for word in allWords {
            // Check for cancellation
            if definitionCheckCancelled {
                print("Definition check cancelled by user")
                return
            }
            
            // Update progress on main thread
            await MainActor.run {
                definitionCheckProgress = Float(processedCount) / Float(totalWords)
            }
            
            do {
                // Use a single database connection and proper error handling
                let dictionaryDAO = DictionaryDAO()
                
                // Use safe method that only checks main dictionary (no user database)
                let mainEntries = try await dictionaryDAO.getMainDictionaryEntriesOnly(word, language: language)
                
                // Update UI on main thread
                await MainActor.run {
                    if mainEntries.isEmpty {
                        // No main dictionary definitions - highlight as no definition
                        wordsWithoutDefinitions.insert(word)
                    } else {
                        // Check if word has substantial dictionary definitions
                        let hasRealDefinition = mainEntries.contains { entry in
                            // Check if this is a real definition (not just morphological info)
                            !entry.definition.isEmpty && 
                            entry.definition.count > 3 &&
                            !entry.definition.contains("Morphological entry")
                        }
                        
                        if !hasRealDefinition {
                            // Has entries but no substantial definition - highlight as morphology only
                            wordsWithMorphologyOnly.insert(word)
                        }
                        // Otherwise word has real definition, don't highlight
                    }
                }
                
                processedCount += 1
                
                // Small delay to allow UI updates and prevent overwhelming the database
                try await Task.sleep(nanoseconds: 1_000_000) // 1 millisecond
                
            } catch {
                print("Error checking definition for '\(word)': \(error)")
                // On error, don't highlight the word - continue processing others
                processedCount += 1
                continue
            }
        }
        
        // Final progress update
        await MainActor.run {
            definitionCheckProgress = 1.0
        }
        
        print("Check definitions complete:")
        print("- Words without definitions: \(wordsWithoutDefinitions.count)")
        print("- Words with morphology only: \(wordsWithMorphologyOnly.count)")
    }

    // MARK: - Find in Text Functions

    private func performFindInText(query: String) async {
        guard !query.isEmpty else { return }

        await MainActor.run {
            isSearching = true
            findResults = []
            currentFindIndex = -1
            lastFindQuery = query
        }

        // Fetch all lines from the book
        let lineDAO = LineDAO()
        do {
            let endLine = viewModel.book.lineCount ?? viewModel.book.endLine ?? 10000
            let allLines = try await lineDAO.getLines(
                bookId: viewModel.book.id,
                startLine: 1,
                endLine: endLine
            )

            var results: [FindResult] = []
            let lowercaseQuery = query.lowercased()

            for line in allLines {
                let lowercaseText = line.lineText.lowercased()
                var searchStart = lowercaseText.startIndex

                // Find all occurrences in this line
                while let range = lowercaseText.range(of: lowercaseQuery, range: searchStart..<lowercaseText.endIndex) {
                    results.append(FindResult(
                        lineNumber: line.lineNumber,
                        sequenceNumber: line.sequenceNumber,
                        lineText: line.lineText,
                        matchStartIndex: lowercaseText.distance(from: lowercaseText.startIndex, to: range.lowerBound),
                        matchEndIndex: lowercaseText.distance(from: lowercaseText.startIndex, to: range.upperBound)
                    ))
                    searchStart = range.upperBound
                }
            }

            await MainActor.run {
                findResults = results
                isSearching = false
                if !results.isEmpty {
                    currentFindIndex = 0
                    navigateToFindResult(at: 0)
                }
            }
        } catch {
            print("Error searching text: \(error)")
            await MainActor.run {
                isSearching = false
            }
        }
    }

    private func navigateToNextFindResult() {
        guard !findResults.isEmpty else { return }
        currentFindIndex = (currentFindIndex + 1) % findResults.count
        navigateToFindResult(at: currentFindIndex)
    }

    private func navigateToPreviousFindResult() {
        guard !findResults.isEmpty else { return }
        currentFindIndex = currentFindIndex <= 0 ? findResults.count - 1 : currentFindIndex - 1
        navigateToFindResult(at: currentFindIndex)
    }

    private func navigateToFindResult(at index: Int) {
        guard index >= 0 && index < findResults.count else { return }
        let result = findResults[index]

        // Calculate target page
        let targetPage = (result.lineNumber - 1) / viewModel.linesPerPage.rawValue + 1

        if viewModel.currentPage != targetPage {
            viewModel.goToPage(targetPage)
        }

        // Set target line for scrolling
        viewModel.targetLineNumber = result.lineNumber
    }

    private func isFindHighlightedLine(_ line: TextLine) -> Bool {
        guard currentFindIndex >= 0 && currentFindIndex < findResults.count else { return false }
        return line.lineNumber == findResults[currentFindIndex].lineNumber
    }
}

// MARK: - Find Result Model

struct FindResult: Identifiable {
    let id = UUID()
    let lineNumber: Int
    let sequenceNumber: Int
    let lineText: String
    let matchStartIndex: Int
    let matchEndIndex: Int
}

// MARK: - Find In Text Sheet

struct FindInTextSheet: View {
    @Binding var query: String
    let lastQuery: String
    let resultsCount: Int
    let currentIndex: Int
    let isSearching: Bool
    let onFind: (String) -> Void
    let onFindNext: () -> Void
    let onFindPrevious: () -> Void

    @Environment(\.dismiss) private var dismiss
    @FocusState private var isQueryFocused: Bool

    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                // Search field
                HStack {
                    TextField("Enter text to find", text: $query)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                        .focused($isQueryFocused)
                        .onSubmit {
                            if !query.isEmpty {
                                onFind(query)
                            }
                        }

                    if !query.isEmpty {
                        Button(action: { query = "" }) {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundColor(.secondary)
                        }
                    }
                }
                .padding(.horizontal)

                // Results info
                if isSearching {
                    HStack {
                        ProgressView()
                            .scaleEffect(0.8)
                        Text("Searching...")
                            .foregroundColor(.secondary)
                    }
                } else if resultsCount > 0 {
                    Text("Result \(currentIndex + 1) of \(resultsCount)")
                        .foregroundColor(.secondary)
                } else if !lastQuery.isEmpty {
                    Text("No matches found for '\(lastQuery)'")
                        .foregroundColor(.secondary)
                }

                // Buttons
                HStack(spacing: 16) {
                    // Previous result
                    Button(action: onFindPrevious) {
                        Image(systemName: "chevron.up")
                            .font(.title2)
                    }
                    .disabled(resultsCount == 0 || isSearching)
                    .frame(width: 44, height: 44)
                    .background(Color(.systemGray5))
                    .cornerRadius(8)

                    // Find button
                    Button(action: {
                        if !query.isEmpty {
                            onFind(query)
                        }
                    }) {
                        Text("Find")
                            .font(.headline)
                            .frame(maxWidth: .infinity)
                            .frame(height: 44)
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(query.isEmpty || isSearching)

                    // Next result
                    Button(action: onFindNext) {
                        Image(systemName: "chevron.down")
                            .font(.title2)
                    }
                    .disabled(resultsCount == 0 || isSearching)
                    .frame(width: 44, height: 44)
                    .background(Color(.systemGray5))
                    .cornerRadius(8)
                }
                .padding(.horizontal)

                Spacer()
            }
            .padding(.top)
            .navigationTitle("Find in Text")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
            .onAppear {
                // Pre-fill with last query if exists
                if query.isEmpty && !lastQuery.isEmpty {
                    query = lastQuery
                }
                isQueryFocused = true
            }
        }
    }
}

// MARK: - Note Edit Dialog

struct NoteEditDialog: View {
    let author: Author
    let work: Work
    let book: Book
    let line: TextLine
    let onBookmarkSaved: (() -> Void)?
    
    @State private var noteText: String = ""
    @State private var existingBookmark: Bookmark?
    @StateObject private var bookmarkChecker = BookmarkChecker()
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationView {
            VStack(alignment: .leading, spacing: 20) {
                // Line info
                VStack(alignment: .leading, spacing: 8) {
                    Text("\(work.title)")
                        .font(.headline)
                    Text("Line \(line.lineNumber)")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    
                    Text(line.lineText)
                        .font(.system(size: 16))
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                }
                .padding(.horizontal)
                .padding(.top)
                
                // Note field
                VStack(alignment: .leading, spacing: 8) {
                    Text("Note")
                        .font(.headline)
                    
                    TextEditor(text: $noteText)
                        .padding(8)
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                        .frame(minHeight: 150)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                }
                .padding(.horizontal)
                
                Spacer()
                
                if existingBookmark != nil {
                    Button(action: deleteNote) {
                        Label("Delete Note", systemImage: "trash")
                            .foregroundColor(.red)
                            .frame(maxWidth: .infinity)
                            .padding()
                    }
                    .padding(.horizontal)
                }
            }
            .navigationTitle(existingBookmark != nil ? "Edit Note" : "Add Note")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Save") {
                        saveNote()
                    }
                }
            }
        }
        .onAppear {
            Task {
                await loadExistingNote()
            }
        }
    }
    
    @MainActor
    private func loadExistingNote() async {
        NSLog("LOAD_DEBUG: Loading existing note for line %d", line.lineNumber)
        
        do {
                // Database lifecycle managed by async architecture
            let dao = BookmarkDAO()
            
            if let existingBookmark = try await dao.getBookmark(
                authorId: author.id,
                workId: work.id, 
                bookId: book.id,
                lineNumber: line.lineNumber,
                sequenceNumber: line.sequenceNumber
            ) {
                NSLog("LOAD_DEBUG: Found existing bookmark with note: %@", existingBookmark.note ?? "nil")
                noteText = existingBookmark.note ?? ""
                self.existingBookmark = existingBookmark
            } else {
                NSLog("LOAD_DEBUG: No existing bookmark found")
                noteText = ""
                existingBookmark = nil
            }
        } catch {
            NSLog("LOAD_ERROR: Failed to load existing note: %@", error.localizedDescription)
            noteText = ""
            existingBookmark = nil
        }
    }
    
    private func saveNote() {
        NSLog("SAVE_DEBUG: Save button pressed")
        NSLog("SAVE_DEBUG: Note text: %@", noteText)
        NSLog("SAVE_DEBUG: Line number: %d", line.lineNumber)
        NSLog("SAVE_DEBUG: Author ID: %@", author.id)
        NSLog("SAVE_DEBUG: Work ID: %@", work.id)
        NSLog("SAVE_DEBUG: Book ID: %@", book.id)
        
        // Simple synchronous save
        Task {
            let bookmark = Bookmark(
                authorId: author.id,
                workId: work.id,
                bookId: book.id,
                lineNumber: line.lineNumber,
                sequenceNumber: line.sequenceNumber,
                authorName: author.name,
                workTitle: work.title,
                bookLabel: book.label,
                lineText: line.lineText,
                note: noteText.isEmpty ? nil : noteText
            )
            
            NSLog("SAVE_DEBUG: Created bookmark object successfully")
            
            do {
                NSLog("SAVE_DEBUG: Opening database...")
                // Database lifecycle managed by async architecture
                NSLog("SAVE_DEBUG: Database opened")
                
                let dao = BookmarkDAO()
                NSLog("SAVE_DEBUG: Creating table...")
                try await dao.createBookmarksTableIfNeeded()
                NSLog("SAVE_DEBUG: Table created")
                
                NSLog("SAVE_DEBUG: Inserting bookmark...")
                let insertedBookmark = try await dao.insertBookmark(bookmark)
                NSLog("SAVE_DEBUG: Bookmark inserted with ID: %d", insertedBookmark.id ?? -1)
                
                NSLog("SAVE_DEBUG: Note saved successfully")
                
                // Immediately test retrieval
                NSLog("SAVE_DEBUG: Testing immediate retrieval...")
                if let retrievedBookmark = try await dao.getBookmark(
                    authorId: author.id,
                    workId: work.id,
                    bookId: book.id,
                    lineNumber: line.lineNumber,
                    sequenceNumber: line.sequenceNumber
                ) {
                    NSLog("SAVE_DEBUG: Retrieved bookmark immediately after save - note: %@", retrievedBookmark.note ?? "nil")
                } else {
                    NSLog("SAVE_ERROR: Could not retrieve bookmark immediately after save!")
                }
                
                // Debug: List all bookmarks in database
                NSLog("SAVE_DEBUG: Listing all bookmarks in database:")
                let allBookmarks = try await dao.getAllBookmarks()
                NSLog("SAVE_DEBUG: Found %d total bookmarks", allBookmarks.count)
                for bookmark in allBookmarks {
                    NSLog("SAVE_DEBUG: Bookmark - Author: %@, Work: %@, Book: %@, Line: %d, Note: %@", bookmark.authorId, bookmark.workId, bookmark.bookId, bookmark.lineNumber, bookmark.note ?? "nil")
                }
                
                
                // Notify that bookmark was saved
                onBookmarkSaved?()
                
            } catch {
                NSLog("SAVE_ERROR: Failed to save bookmark: %@", error.localizedDescription)
                NSLog("SAVE_ERROR: Error type: %@", String(describing: type(of: error)))
                if let dbError = error as? DatabaseError {
                    NSLog("SAVE_ERROR: Database error: %@", dbError.localizedDescription)
                }
            }
        }
        
        dismiss()
    }
    
    private func deleteNote() {
        NSLog("DELETE_DEBUG: Delete button pressed for line %d", line.lineNumber)
        
        guard let existingBookmark = existingBookmark,
              let bookmarkId = existingBookmark.id else {
            NSLog("DELETE_ERROR: No existing bookmark to delete")
            dismiss()
            return
        }
        
        Task {
            do {
                NSLog("DELETE_DEBUG: Opening database...")
                // Database lifecycle managed by async architecture
                NSLog("DELETE_DEBUG: Database opened")
                
                let dao = BookmarkDAO()
                NSLog("DELETE_DEBUG: Deleting bookmark with ID: %d", bookmarkId)
                try await dao.deleteBookmark(id: bookmarkId)
                NSLog("DELETE_DEBUG: Bookmark deleted successfully")
                
                
                // Notify that bookmark was deleted
                onBookmarkSaved?()
                
            } catch {
                NSLog("DELETE_ERROR: Failed to delete bookmark: %@", error.localizedDescription)
            }
        }
        
        dismiss()
    }
}

// MARK: - Bookmark Edit Sheet

struct BookmarkEditSheet: View {
    let line: TextLine
    let book: Book
    let work: Work
    let author: Author
    let existingNote: String
    let hasBookmark: Bool
    let onSave: (String?) -> Void
    let onDelete: () -> Void
    
    @State private var note: String = ""
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationView {
            VStack(alignment: .leading, spacing: 20) {
                // Line info
                VStack(alignment: .leading, spacing: 8) {
                    Text("\(work.title) - Line \(line.lineNumber)")
                        .font(.headline)
                    
                    Text(line.lineText)
                        .font(.system(size: 16))
                        // .fontDesign(author.isGreek ? .serif : .default)
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                }
                .padding(.horizontal)
                .padding(.top)
                
                // Note field
                VStack(alignment: .leading, spacing: 8) {
                    Text("Note (optional)")
                        .font(.headline)
                    
                    TextEditor(text: $note)
                        .padding(8)
                        .background(Color(.systemGray6))
                        .cornerRadius(8)
                        .frame(minHeight: 100)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                }
                .padding(.horizontal)
                
                Spacer()
                
                if hasBookmark {
                    Button(action: {
                        onDelete()
                        dismiss()
                    }) {
                        Label("Remove Bookmark", systemImage: "bookmark.slash")
                            .foregroundColor(.red)
                            .frame(maxWidth: .infinity)
                            .padding()
                    }
                    .padding(.horizontal)
                }
            }
            .navigationTitle(hasBookmark ? "Edit Bookmark" : "Add Bookmark")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Save") {
                        onSave(note.isEmpty ? nil : note)
                        dismiss()
                    }
                }
            }
        }
        .onAppear {
            note = existingNote
        }
    }
}

// MARK: - Bookmark Checker Helper

@MainActor
class BookmarkChecker: ObservableObject {
    private let bookmarkDAO = BookmarkDAO()
    
    func hasBookmark(authorId: String, workId: String, bookId: String, lineNumber: Int) async -> Bool {
        do {
                // Database lifecycle managed by async architecture
            try await bookmarkDAO.createBookmarksTableIfNeeded()
            let bookmark = try await bookmarkDAO.getBookmark(authorId: authorId, workId: workId, bookId: bookId, lineNumber: lineNumber, sequenceNumber: 0)
            // Don't close database
            return bookmark != nil
        } catch {
            return false
        }
    }
    
    func getBookmark(authorId: String, workId: String, bookId: String, lineNumber: Int) async -> Bookmark? {
        do {
                // Database lifecycle managed by async architecture
            let bookmark = try await bookmarkDAO.getBookmark(authorId: authorId, workId: workId, bookId: bookId, lineNumber: lineNumber, sequenceNumber: 0)
            // Don't close database
            return bookmark
        } catch {
            return nil
        }
    }
    
    func saveBookmark(_ bookmark: Bookmark) async {
        do {
            print("DEBUG: BookmarkChecker.saveBookmark - Starting save")
                // Database lifecycle managed by async architecture
            print("DEBUG: Database opened")
            
            try await bookmarkDAO.createBookmarksTableIfNeeded()
            print("DEBUG: Table created/verified")
            
            // For now, just use INSERT OR REPLACE behavior
            print("DEBUG: Inserting/replacing bookmark")
            _ = try await bookmarkDAO.insertBookmark(bookmark)
            print("DEBUG: Bookmark saved successfully")
            
        } catch {
            print("Failed to save bookmark: \(error)")
        }
    }
    
    func deleteBookmark(authorId: String, workId: String, bookId: String, lineNumber: Int) async {
        do {
                // Database lifecycle managed by async architecture
            if let bookmark = try await bookmarkDAO.getBookmark(authorId: authorId, workId: workId, bookId: bookId, lineNumber: lineNumber, sequenceNumber: 0),
               let id = bookmark.id {
                try await bookmarkDAO.deleteBookmark(id: id)
            }
            // Don't close database
        } catch {
            print("Failed to delete bookmark: \(error)")
        }
    }
}

struct ReaderBottomBar: View {
    let currentPage: Int
    let totalPages: Int
    let currentViewLabel: String
    let hasTranslations: Bool
    let isLoading: Bool
    let onPreviousPage: () -> Void
    let onNextPage: () -> Void
    let onPageTap: () -> Void
    let onCycleView: () -> Void

    var body: some View {
        VStack(spacing: 8) {
            // View indicator (Greek / English (Translator))
            Button(action: onCycleView) {
                HStack(spacing: 4) {
                    Text(currentViewLabel)
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(.secondary)
                    if hasTranslations {
                        Image(systemName: "arrow.right.circle.fill")
                            .font(.system(size: 12))
                            .foregroundColor(.blue)
                    }
                }
            }
            .disabled(!hasTranslations || isLoading)

            HStack {
                Button(action: onPreviousPage) {
                    Image(systemName: "chevron.left")
                        .font(.system(size: 20, weight: .medium))
                }
                .disabled(currentPage <= 1 || isLoading)

                Spacer()

                Button(action: onPageTap) {
                    Text("Page \(currentPage) of \(totalPages)")
                        .font(.system(size: 16, weight: .medium))
                }
                .disabled(isLoading)

                Spacer()

                Button(action: onNextPage) {
                    Image(systemName: "chevron.right")
                        .font(.system(size: 20, weight: .medium))
                }
                .disabled(currentPage >= totalPages || isLoading)
            }
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 12)
        .background(Color(.systemGray6))
        .overlay(
            Rectangle()
                .frame(height: 0.5)
                .foregroundColor(Color(.separator)),
            alignment: .top
        )
    }
}

struct PagePickerView: View {
    let currentPage: Int
    let totalPages: Int
    let onPageSelected: (Int) -> Void
    
    @State private var selectedPage: Int
    
    init(currentPage: Int, totalPages: Int, onPageSelected: @escaping (Int) -> Void) {
        self.currentPage = currentPage
        self.totalPages = totalPages
        self.onPageSelected = onPageSelected
        _selectedPage = State(initialValue: currentPage)
    }
    
    var body: some View {
        NavigationView {
            VStack {
                Picker("Page", selection: $selectedPage) {
                    ForEach(1...totalPages, id: \.self) { page in
                        Text("Page \(page)").tag(page)
                    }
                }
                .pickerStyle(WheelPickerStyle())
                .labelsHidden()
            }
            .navigationTitle("Go to Page")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        onPageSelected(currentPage)
                    }
                }
                
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Go") {
                        onPageSelected(selectedPage)
                    }
                }
            }
        }
    }
}


// UIViewRepresentable for accurate tap detection  
// (Removed - using TappableTextView from separate file)
/*
struct TappableTextView_Duplicate: UIViewRepresentable {
    let text: String
    let fontSize: CGFloat
    let isGreek: Bool
    let bookId: String
    let lineNumber: Int
    let onWordTapped: (Word) -> Void
    let onLongPress: () -> Void
    let maxWidth: CGFloat
    
    func makeUIView(context: Context) -> UILabel {
        let label = UILabel()
        label.numberOfLines = 0
        label.lineBreakMode = .byWordWrapping
        label.isUserInteractionEnabled = true
        
        // Set font
        if isGreek {
            label.font = UIFont(name: "Times New Roman", size: fontSize) ?? UIFont.systemFont(ofSize: fontSize)
        } else {
            label.font = UIFont.systemFont(ofSize: fontSize)
        }
        
        label.text = text
        label.preferredMaxLayoutWidth = maxWidth
        
        // Add tap gesture
        let tapGesture = UITapGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.handleTap(_:)))
        label.addGestureRecognizer(tapGesture)
        
        // Add long press gesture
        let longPressGesture = UILongPressGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.handleLongPress(_:)))
        label.addGestureRecognizer(longPressGesture)
        
        return label
    }
    
    func updateUIView(_ label: UILabel, context: Context) {
        label.text = text
        label.preferredMaxLayoutWidth = maxWidth
        if isGreek {
            label.font = UIFont(name: "Times New Roman", size: fontSize) ?? UIFont.systemFont(ofSize: fontSize)
        } else {
            label.font = UIFont.systemFont(ofSize: fontSize)
        }
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }
    
    class Coordinator: NSObject {
        let parent: TappableTextView
        
        init(_ parent: TappableTextView) {
            self.parent = parent
        }
        
        @objc func handleTap(_ gesture: UITapGestureRecognizer) {
            guard let label = gesture.view as? UILabel,
                  let text = label.text else { return }
            
            let location = gesture.location(in: label)
            
            // Create text storage and layout manager for accurate hit testing
            let textStorage = NSTextStorage(string: text)
            let layoutManager = NSLayoutManager()
            let textContainer = NSTextContainer(size: label.bounds.size)
            
            textContainer.lineFragmentPadding = 0
            textContainer.maximumNumberOfLines = label.numberOfLines
            textContainer.lineBreakMode = label.lineBreakMode
            
            layoutManager.addTextContainer(textContainer)
            textStorage.addLayoutManager(layoutManager)
            
            // Apply font attributes
            let range = NSRange(location: 0, length: text.count)
            textStorage.addAttribute(.font, value: label.font!, range: range)
            
            // Find character index at tap location
            let characterIndex = layoutManager.characterIndex(
                for: location,
                in: textContainer,
                fractionOfDistanceBetweenInsertionPoints: nil
            )
            
            // Find word at character index
            if characterIndex < text.count {
                let nsString = text as NSString
                let wordRange = nsString.rangeOfComposedCharacterSequences(for: NSRange(location: characterIndex, length: 1))
                
                // Expand to find word boundaries
                var start = wordRange.location
                var end = NSMaxRange(wordRange)
                
                // Find start of word
                while start > 0 {
                    let prevChar = nsString.character(at: start - 1)
                    if !CharacterSet.letters.contains(UnicodeScalar(prevChar)!) &&
                       prevChar != 39 && // apostrophe '
                       prevChar != 8217 && // right single quote '
                       prevChar != 700 { // Greek apostrophe ʼ
                        break
                    }
                    start -= 1
                }
                
                // Find end of word
                while end < nsString.length {
                    let nextChar = nsString.character(at: end)
                    if !CharacterSet.letters.contains(UnicodeScalar(nextChar)!) &&
                       nextChar != 39 && // apostrophe '
                       nextChar != 8217 && // right single quote '
                       nextChar != 700 { // Greek apostrophe ʼ
                        break
                    }
                    end += 1
                }
                
                // Extract the word
                let wordRange = NSRange(location: start, length: end - start)
                let word = nsString.substring(with: wordRange)
                
                if !word.isEmpty {
                    // Calculate word position (which word number in the line)
                    let wordsBeforeTap = nsString.substring(to: start)
                        .split { !$0.isLetter && $0 != "'" && $0 != "'" && $0 != "ʼ" }
                        .filter { !$0.isEmpty }
                    let wordPosition = wordsBeforeTap.count + 1
                    
                    print("DEBUG: Tapped word '\(word)' at position \(wordPosition) in line \(parent.lineNumber)")
                    
                    // Normalize the word
                    let normalizedWord: String
                    if parent.isGreek {
                        normalizedWord = word.lowercased()
                            .replacingOccurrences(of: "ά", with: "α")
                            .replacingOccurrences(of: "έ", with: "ε")
                            .replacingOccurrences(of: "ή", with: "η")
                            .replacingOccurrences(of: "ί", with: "ι")
                            .replacingOccurrences(of: "ό", with: "ο")
                            .replacingOccurrences(of: "ύ", with: "υ")
                            .replacingOccurrences(of: "ώ", with: "ω")
                            .applyingTransform(.stripDiacritics, reverse: false) ?? word.lowercased()
                    } else {
                        normalizedWord = word.lowercased()
                    }
                    
                    // Create Word object
                    let wordObject = Word(
                        id: 0,
                        word: word,
                        bookId: parent.bookId,
                        lineNumber: parent.lineNumber,
                        wordPosition: wordPosition
                    )
                    
                    parent.onWordTapped(wordObject)
                }
            }
        }
        
        @objc func handleLongPress(_ gesture: UILongPressGestureRecognizer) {
            if gesture.state == .began {
                parent.onLongPress()
            }
        }
    }
}
*/

struct ReaderView_Previews: PreviewProvider {
    static var previews: some View {
        NavigationView {
            ReaderView(
                book: Book(
                    id: "plat.rep.1",
                    workId: "plat.rep",
                    bookNumber: 1,
                    label: "Book 1",
                    startLine: 1,
                    endLine: 500,
                    lineCount: 500
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