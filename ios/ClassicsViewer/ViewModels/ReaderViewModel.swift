import Foundation
import SwiftUI
import Combine

@MainActor
class ReaderViewModel: ObservableObject {
    @Published var lines: [TextLine] = []
    @Published var translationsByTranslator: [String: [TranslationSegment]] = [:]
    @Published var currentPage = 1
    @Published var totalPages = 1
    @Published var isLoading = false
    @Published var currentViewIndex = 0 // 0 = Greek/Latin, 1+ = translations
    @Published var work: Work?
    @Published var hasTranslations = true // Default to true until we check
    @Published var availableTranslators: [String] = []
    // Fixed at 100 lines per page
    let linesPerPage: LinesPerPage = .hundred
    @Published var fontSize: CGFloat = 20
    @Published var lineSpacing: CGFloat = 1.2
    @Published var targetLineNumber: Int?
    @Published var linesWithAudio: Set<Int> = []

    // Cross-book navigation state
    @Published var hasNextBook = false
    @Published var hasPreviousBook = false
    @Published var navigateToBook: Book? = nil
    @Published var navigateToBookStartFromEnd = false

    let book: Book
    let author: Author

    private let lineDAO = LineDAO()
    private let translationDAO = TranslationDAO()
    private let workDAO = WorkDAO()
    private let bookmarkDAO = BookmarkDAO()
    private let audioDAO = AudioPackageDAO()
    private let bookDAO = BookDAO()
    @Published private(set) var totalLines = 0
    private var bookmarkedLines: Set<Int> = []
    private var loadPageTask: Task<Void, Never>?
    
    enum LinesPerPage: Int, CaseIterable {
        case twenty = 20
        case fifty = 50
        case hundred = 100
        
        var displayName: String {
            "\(rawValue) lines"
        }
    }
    
    init(book: Book, author: Author) {
        self.book = book
        self.author = author
        
        // Load saved font size preference
        fontSize = UserDefaults.standard.double(forKey: "fontSize")
        if fontSize == 0 { fontSize = 20 } // Default
    }
    
    func loadInitialData() {
        Task {
            await loadWorkData()
            await loadTotalLines()
            await checkForTranslations()
            await loadAvailableTranslators()
            await loadAvailableAudio()
            await checkAdjacentBooks()

            // If we have a target line number (e.g., from bookmark navigation),
            // calculate and navigate to the correct page before loading
            if let targetLine = targetLineNumber, targetLine > 0 {
                let targetPage = (targetLine - 1) / linesPerPage.rawValue + 1
                if targetPage != currentPage && targetPage <= totalPages {
                    currentPage = targetPage
                    print("DEBUG: Set page to \(targetPage) for target line \(targetLine)")
                }
            }

            await loadCurrentPage()
        }
    }

    private func checkAdjacentBooks() async {
        do {
            let nextBook = try await bookDAO.getNextBook(workId: book.workId, currentBookId: book.id)
            let prevBook = try await bookDAO.getPreviousBook(workId: book.workId, currentBookId: book.id)
            await MainActor.run {
                hasNextBook = nextBook != nil
                hasPreviousBook = prevBook != nil
            }
            print("DEBUG: Adjacent books - hasNext: \(hasNextBook), hasPrevious: \(hasPreviousBook)")
        } catch {
            print("ERROR: Failed to check adjacent books: \(error)")
        }
    }
    
    private func loadWorkData() async {
        do {
            // Database lifecycle managed by async architecture
            work = try await workDAO.getWork(workId: book.workId)
            print("DEBUG: Loaded work: \(work?.title ?? "nil")")
        } catch {
            print("ERROR: Failed to load work data: \(error)")
        }
    }
    
    private func loadTotalLines() async {
        do {
            // Database lifecycle managed by async architecture
            totalLines = try await lineDAO.getTotalLines(bookId: book.id)
            totalPages = Int(ceil(Double(totalLines) / Double(linesPerPage.rawValue)))
            print("DEBUG: Book \(book.id) has \(totalLines) lines, \(totalPages) pages")
            // Don't close database - keep it open for next query
        } catch {
            print("ERROR: Failed to load total lines: \(error)")
        }
    }
    
    private func checkForTranslations() async {
        do {
            // Database lifecycle managed by async architecture
            print("DEBUG ReaderViewModel: Checking translations for book: \(book.id)")
            hasTranslations = try await translationDAO.hasTranslations(bookId: book.id)
            print("DEBUG ReaderViewModel: Book \(book.id) has translations: \(hasTranslations)")
            
            // Double-check by trying to load translations
            if !hasTranslations {
                let testTranslations = try await translationDAO.getTranslations(
                    bookId: book.id,
                    startLine: 1,
                    endLine: 10
                )
                print("DEBUG ReaderViewModel: Test load found \(testTranslations.count) translations")
                if !testTranslations.isEmpty {
                    print("WARNING: hasTranslations returned false but translations exist!")
                    hasTranslations = true
                }
            }
        } catch {
            print("ERROR: Failed to check for translations: \(error)")
            // Default to true to not disable the button on error
            hasTranslations = true
        }
    }
    
    private func loadAvailableTranslators() async {
        do {
            // Database lifecycle managed by async architecture
            var translators = try await translationDAO.getAvailableTranslators(bookId: book.id)
            print("DEBUG: Found \(translators.count) translator(s): \(translators)")

            // Reorder translators based on user preference for interlinear position
            let showInterlinearFirst = UserDefaults.standard.bool(forKey: "showInterlinearFirst")
            if let interlinearIndex = translators.firstIndex(where: { $0.localizedCaseInsensitiveContains("Interlinear") }),
               translators.count > 1 {
                let interlinear = translators.remove(at: interlinearIndex)
                if showInterlinearFirst {
                    translators.insert(interlinear, at: 0)
                } else {
                    translators.append(interlinear)
                }
                print("DEBUG: Reordered translators (interlinear first: \(showInterlinearFirst)): \(translators)")
            }

            availableTranslators = translators
        } catch {
            print("ERROR: Failed to load available translators: \(error)")
        }
    }
    
    func switchToView(index: Int) {
        let maxIndex = availableTranslators.isEmpty ? 0 : availableTranslators.count
        guard index >= 0 && index <= maxIndex else { return }
        currentViewIndex = index
    }

    func navigateToNextView() {
        let maxIndex = availableTranslators.count
        if currentViewIndex < maxIndex {
            currentViewIndex += 1
        } else {
            // Cycle back to beginning
            currentViewIndex = 0
        }
    }

    func navigateToPreviousView() {
        if currentViewIndex > 0 {
            currentViewIndex -= 1
        }
    }

    var currentViewLabel: String {
        if currentViewIndex == 0 {
            return author.language.prefix(1).uppercased() + author.language.dropFirst()
        } else if currentViewIndex - 1 < availableTranslators.count {
            let translator = availableTranslators[currentViewIndex - 1]
            // Remove parenthetical content from translator name
            if let parenIndex = translator.firstIndex(of: "(") {
                return translator[..<parenIndex].trimmingCharacters(in: .whitespaces)
            }
            return translator
        }
        return "English"
    }
    
    func loadCurrentPage() async {
        // Cancel any existing page load task
        loadPageTask?.cancel()
        
        // Create new task for loading this page
        loadPageTask = Task {
            guard !Task.isCancelled else { return }
            
            await MainActor.run {
                isLoading = true
            }
            
            let startLine = (currentPage - 1) * linesPerPage.rawValue + 1
            let endLine = min(currentPage * linesPerPage.rawValue, totalLines)
            
            print("DEBUG: Loading page \(currentPage) (lines \(startLine)-\(endLine)) for book \(book.id)")
            
            guard !Task.isCancelled else { 
                await MainActor.run { isLoading = false }
                return 
            }
            
            do {
            // Database lifecycle managed by async architecture
                
                guard !Task.isCancelled else { 
                    await MainActor.run { isLoading = false }
                    return 
                }
                
                // Load lines
                let newLines = try await lineDAO.getLines(
                    bookId: book.id,
                    startLine: startLine,
                    endLine: endLine
                )
                
                guard !Task.isCancelled else { 
                    await MainActor.run { isLoading = false }
                    return 
                }
                
                print("DEBUG: Loaded \(newLines.count) lines")

                // Load translations for all translators
                var translationsMap: [String: [TranslationSegment]] = [:]
                for translator in availableTranslators {
                    let segments = try await translationDAO.getTranslationsByTranslator(
                        bookId: book.id,
                        translator: translator,
                        startLine: startLine,
                        endLine: endLine
                    )
                    translationsMap[translator] = segments
                    print("DEBUG: Loaded \(segments.count) segments for \(translator)")
                }

                guard !Task.isCancelled else {
                    await MainActor.run { isLoading = false }
                    return
                }

                // Update UI on main thread
                await MainActor.run {
                    self.lines = newLines
                    self.translationsByTranslator = translationsMap
                }
                
                // Load bookmarks for current page
                await loadBookmarksForCurrentPage()
                
                // Don't close database - keep it open
            } catch {
                print("ERROR: Failed to load page: \(error)")
            }
            
            await MainActor.run {
                isLoading = false
            }
        }
        
        await loadPageTask?.value
    }
    
    func nextPage() {
        guard !isLoading else { return }

        if currentPage < totalPages {
            // Navigate within current book
            currentPage += 1
            Task {
                await loadCurrentPage()
            }
        } else if hasNextBook {
            // At end of book, navigate to next book
            Task {
                await navigateToNextBook()
            }
        }
    }

    func previousPage() {
        guard !isLoading else { return }

        if currentPage > 1 {
            // Navigate within current book
            currentPage -= 1
            Task {
                await loadCurrentPage()
            }
        } else if hasPreviousBook {
            // At start of book, navigate to previous book
            Task {
                await navigateToPreviousBook()
            }
        }
    }

    private func navigateToNextBook() async {
        do {
            if let nextBook = try await bookDAO.getNextBook(workId: book.workId, currentBookId: book.id) {
                await MainActor.run {
                    navigateToBookStartFromEnd = false
                    navigateToBook = nextBook
                }
            }
        } catch {
            print("ERROR: Failed to navigate to next book: \(error)")
        }
    }

    private func navigateToPreviousBook() async {
        do {
            if let prevBook = try await bookDAO.getPreviousBook(workId: book.workId, currentBookId: book.id) {
                await MainActor.run {
                    navigateToBookStartFromEnd = true
                    navigateToBook = prevBook
                }
            }
        } catch {
            print("ERROR: Failed to navigate to previous book: \(error)")
        }
    }
    
    func goToPage(_ page: Int) {
        guard !isLoading && page > 0 && page <= totalPages else { return }
        currentPage = page
        Task {
            await loadCurrentPage()
        }
    }
    
    func getCurrentTranslations() -> [TranslationSegment] {
        if currentViewIndex == 0 {
            return []
        }
        let translatorIndex = currentViewIndex - 1
        if translatorIndex < availableTranslators.count {
            let translator = availableTranslators[translatorIndex]
            return translationsByTranslator[translator] ?? []
        }
        return []
    }

    var isShowingTranslation: Bool {
        return currentViewIndex > 0
    }
    
    // MARK: - Title and Subtitle for Navigation
    
    var navigationTitle: String {
        let workTitle = work?.titleEnglish ?? work?.title ?? "Loading..."
        return "\(author.name) - \(workTitle)"
    }
    
    var navigationSubtitle: String {
        let currentStartLine = (currentPage - 1) * linesPerPage.rawValue + 1
        let currentEndLine = min(currentPage * linesPerPage.rawValue, totalLines)
        let bookLabel = book.label ?? "Book \(book.bookNumber)"
        return "\(bookLabel), lines \(currentStartLine)-\(currentEndLine)"
    }
    
    // MARK: - Bookmark Management
    
    func hasBookmark(for lineNumber: Int) -> Bool {
        return bookmarkedLines.contains(lineNumber)
    }
    
    private func loadBookmarksForCurrentPage() async {
        let startLine = (currentPage - 1) * linesPerPage.rawValue + 1
        let endLine = min(currentPage * linesPerPage.rawValue, totalLines)
        
        do {
            // Database lifecycle managed by async architecture
            
            // Get all bookmarks for this work to check which lines have bookmarks
            let workBookmarks = try await bookmarkDAO.getBookmarksByWork(workId: book.workId)
            
            // Filter bookmarks for current book and page range
            let currentPageBookmarks = workBookmarks.filter { bookmark in
                bookmark.bookId == book.id &&
                bookmark.lineNumber >= startLine &&
                bookmark.lineNumber <= endLine
            }
            
            // Update bookmarked lines set
            let newBookmarkedLines = Set(currentPageBookmarks.map { $0.lineNumber })
            
            await MainActor.run {
                self.bookmarkedLines = newBookmarkedLines
            }
            
        } catch {
            print("ERROR: Failed to load bookmarks: \(error)")
        }
    }
    
    func refreshBookmarks() {
        Task {
            await loadBookmarksForCurrentPage()
        }
    }
    
    private func loadAvailableAudio() async {
        do {
            // Map work ID to audio format based on author and work
            // The audio files use format like "homer_iliad" while the database uses "tlg0012.tlg001"
            var audioWorkId = ""

            // Get author name and work title for mapping
            let authorName = author.name.lowercased()
            let workTitle = (work?.title ?? "").lowercased()

            // Create audio work ID from author and work
            // Handle various formats
            if authorName.contains("homer") {
                if workTitle.contains("iliad") {
                    audioWorkId = "homer_iliad"
                } else if workTitle.contains("odyssey") {
                    audioWorkId = "homer_odyssey"
                }
            } else {
                // Generic format: author_work
                let cleanAuthor = authorName.replacingOccurrences(of: " ", with: "_")
                let cleanWork = workTitle.replacingOccurrences(of: " ", with: "_")
                audioWorkId = "\(cleanAuthor)_\(cleanWork)"
            }

            // Also try the original work ID format
            let alternateWorkId = book.workId

            // Get book number from book ID
            let bookNumber = String(book.bookNumber)
            
            // Check which lines have audio available - try primary work ID first
            var audioFiles = try await audioDAO.getAudioFiles(
                workId: audioWorkId,
                bookId: bookNumber,
                lineStart: 1,
                lineEnd: totalLines
            )

            // If no files found, try alternate work ID format
            if audioFiles.isEmpty {
                print("DEBUG: No audio found for work ID '\(audioWorkId)', trying alternate '\(alternateWorkId)'")
                audioFiles = try await audioDAO.getAudioFiles(
                    workId: alternateWorkId,
                    bookId: bookNumber,
                    lineStart: 1,
                    lineEnd: totalLines
                )
            }

            // Build set of line numbers that have audio
            var audioLines = Set<Int>()
            for file in audioFiles {
                for line in file.lineStart...file.lineEnd {
                    audioLines.insert(line)
                }
            }

            await MainActor.run {
                self.linesWithAudio = audioLines
            }

            print("DEBUG: Found audio for \(audioLines.count) lines in book \(book.id) using work ID '\(audioFiles.isEmpty ? "none" : audioWorkId)'")
            
        } catch {
            print("ERROR: Failed to load audio availability: \(error)")
        }
    }
    
    func hasAudioForLine(_ lineNumber: Int) -> Bool {
        return linesWithAudio.contains(lineNumber)
    }

    // MARK: - Export Data Access

    func getLines(startLine: Int, endLine: Int) async throws -> [TextLine] {
        return try await lineDAO.getLines(bookId: book.id, startLine: startLine, endLine: endLine)
    }

    func getTranslations(translator: String, startLine: Int, endLine: Int) async throws -> [TranslationSegment] {
        return try await translationDAO.getTranslationsByTranslator(
            bookId: book.id,
            translator: translator,
            startLine: startLine,
            endLine: endLine
        )
    }
}