import Foundation

// MARK: - Database Models matching exact SQL schema

struct Author: Identifiable, Hashable {
    let id: String
    let name: String
    let nameAlt: String?
    let language: String
    let hasTranslations: Int
    
    var isGreek: Bool {
        language == "greek"
    }
}

struct Work: Identifiable, Hashable {
    let id: String
    let authorId: String
    let title: String
    let titleAlt: String?
    let titleEnglish: String?
    let type: String?
    let urn: String?
    let description: String?
}

struct Book: Identifiable, Hashable {
    let id: String
    let workId: String
    let bookNumber: Int
    let label: String?
    let startLine: Int?
    let endLine: Int?
    let lineCount: Int?
}

struct TextLine: Identifiable, Hashable {
    let id: Int
    let bookId: String
    let lineNumber: Int
    let sequenceNumber: Int  // Required for texts with duplicate line numbers (e.g., Homeric Epigrams)
    let lineText: String
    let lineXml: String?
    let speaker: String?
}

struct Word: Identifiable, Hashable {
    let id: Int
    let word: String
    // Note: word_normalized column doesn't exist in actual database
    let bookId: String
    let lineNumber: Int
    let sequenceNumber: Int  // Required for texts with duplicate line numbers
    let wordPosition: Int
}

struct TranslationSegment: Identifiable, Hashable {
    let id: Int
    let bookId: String
    let startLine: Int
    let endLine: Int?
    let translationText: String
    let translator: String?
    let speaker: String?
}

struct LemmaMap: Hashable {
    let id: Int?
    let wordForm: String
    let wordFormNormalizedUltra: String?
    let lemma: String
    let confidence: Double?
    let source: String?
    let morphInfo: String?
}

struct DictionaryEntry: Identifiable, Hashable {
    let id: Int
    let headword: String
    let headwordNormalizedUltra: String?
    let language: String
    let entryXml: String?
    let entryHtml: String?
    let entryPlain: String?
    let source: String?
}

struct TranslationLookup: Hashable {
    let bookId: String
    let lineNumber: Int
    let segmentId: Int
}

// MARK: - Bookmark Model (app-created table)

struct Bookmark: Identifiable, Hashable, Codable {
    let id: Int?
    let authorId: String
    let workId: String
    let bookId: String
    let lineNumber: Int
    let sequenceNumber: Int  // Required for texts with duplicate line numbers
    let authorName: String
    let workTitle: String
    let bookLabel: String?
    let lineText: String
    let note: String?
    let createdAt: Date
    let lastAccessed: Date
    
    // For new bookmarks before saving
    init(authorId: String, workId: String, bookId: String, lineNumber: Int, sequenceNumber: Int = 0, 
         authorName: String, workTitle: String, bookLabel: String?,
         lineText: String, note: String? = nil) {
        self.id = nil
        self.authorId = authorId
        self.workId = workId
        self.bookId = bookId
        self.lineNumber = lineNumber
        self.sequenceNumber = sequenceNumber
        self.authorName = authorName
        self.workTitle = workTitle
        self.bookLabel = bookLabel
        self.lineText = lineText
        self.note = note
        self.createdAt = Date()
        self.lastAccessed = Date()
    }
    
    // For loading from database
    init(id: Int, authorId: String, workId: String, bookId: String, lineNumber: Int, sequenceNumber: Int,
         authorName: String, workTitle: String, bookLabel: String?,
         lineText: String, note: String?, createdAt: Date, lastAccessed: Date) {
        self.id = id
        self.authorId = authorId
        self.workId = workId
        self.bookId = bookId
        self.lineNumber = lineNumber
        self.sequenceNumber = sequenceNumber
        self.authorName = authorName
        self.workTitle = workTitle
        self.bookLabel = bookLabel
        self.lineText = lineText
        self.note = note
        self.createdAt = createdAt
        self.lastAccessed = lastAccessed
    }
    
    // For CSV import with dates
    init(authorId: String, workId: String, bookId: String, lineNumber: Int, sequenceNumber: Int = 0,
         authorName: String, workTitle: String, bookLabel: String?,
         lineText: String, note: String? = nil, createdAt: Date, lastAccessed: Date) {
        self.id = nil
        self.authorId = authorId
        self.workId = workId
        self.bookId = bookId
        self.lineNumber = lineNumber
        self.sequenceNumber = sequenceNumber
        self.authorName = authorName
        self.workTitle = workTitle
        self.bookLabel = bookLabel
        self.lineText = lineText
        self.note = note
        self.createdAt = createdAt
        self.lastAccessed = lastAccessed
    }
    
    var language: String {
        if bookId.contains("tlg") {
            return "greek"
        } else if bookId.contains("phi") {
            return "latin"
        }
        return "greek" // default
    }
}

// MARK: - Compound Models for UI

struct AuthorWithWorks: Identifiable {
    let author: Author
    let works: [Work]
    
    var id: String { author.id }
}

struct WorkWithBooks: Identifiable {
    let work: Work
    let books: [Book]
    
    var id: String { work.id }
}

struct BookDisplay: Identifiable {
    let book: Book
    let work: Work
    let author: Author
    
    var id: String { book.id }
    
    var displayTitle: String {
        var title = work.title
        if let label = book.label {
            title += " - \(label)"
        }
        return title
    }
}

struct WordOccurrence: Identifiable, Hashable {
    var id: String { "\(bookId)_\(lineNumber)_\(word)" }
    let word: String
    let bookId: String
    let bookTitle: String
    let authorName: String
    let lineNumber: Int
    let lineText: String
    let wordPositions: [Int]

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }

    static func == (lhs: WordOccurrence, rhs: WordOccurrence) -> Bool {
        lhs.id == rhs.id
    }
}

// MARK: - User Dictionary Models

struct UserDictionaryPackage: Identifiable, Hashable {
    let id: Int?
    let packageName: String
    let displayName: String
    let description: String?
    let language: String
    let sourceInfo: String?
    let importDate: Date
    let fileSize: Int?
    let lemmaCount: Int?
    let isEnabled: Bool
}

struct UserDictionaryLemma: Identifiable, Hashable {
    let id: Int?
    let packageId: Int
    let lemma: String
    let lemmaNormalizedUltra: String?
    let language: String
    let definitionPlain: String
    let definitionHtml: String?
    let sourceName: String
    let importFileName: String
    let importDate: Date
    let createdAt: Date
}

struct UserLemmaMapping: Identifiable, Hashable {
    let id: Int?
    let inflectedForm: String
    let lemma: String
    let language: String
    let source: String
    let packageId: Int?
}

// MARK: - Audio Package Models

struct AudioPackage: Identifiable, Hashable {
    let id: Int?
    let packageName: String
    let displayName: String
    let description: String?
    let version: String?
    let createdDate: Date?
    let importDate: Date
    let fileCount: Int
    let totalSize: Int
    let isEnabled: Bool
}

struct AudioFile: Identifiable, Hashable {
    let id: Int?
    let packageId: Int
    let workId: String
    let bookId: String?
    let lineStart: Int
    let lineEnd: Int
    let filePath: String
    let durationMs: Int?
    let fileSize: Int?
    let mimeType: String
}

// MARK: - Search Results

struct SearchResult: Identifiable {
    let id = UUID()
    let query: String
    let occurrences: [WordOccurrence]
    let searchType: SearchType
    
    enum SearchType {
        case exact
        case normalized
        case lemma
    }
}