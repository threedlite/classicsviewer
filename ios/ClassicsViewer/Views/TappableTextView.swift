import SwiftUI
import UIKit

struct TappableTextView: UIViewRepresentable {
    let text: String
    let fontSize: CGFloat
    let isGreek: Bool
    let bookId: String
    let lineNumber: Int
    let sequenceNumber: Int
    let onWordTapped: (Word) -> Void
    var wordsWithoutDefinitions: Set<String> = []
    var wordsWithMorphologyOnly: Set<String> = []
    var searchHighlightedWords: Set<String> = []
    
    func makeUIView(context: Context) -> UITextView {
        let textView = UITextView()
        textView.isEditable = false
        textView.isScrollEnabled = false
        textView.backgroundColor = .clear
        textView.textContainerInset = .zero
        textView.textContainer.lineFragmentPadding = 0
        
        // Create attributed text with highlighting if needed
        let attributedText = createAttributedText()
        textView.attributedText = attributedText
        
        // Important: Set content compression resistance to ensure text displays properly
        textView.setContentCompressionResistancePriority(.required, for: .horizontal)
        textView.setContentCompressionResistancePriority(.required, for: .vertical)
        textView.setContentHuggingPriority(.required, for: .horizontal)
        textView.setContentHuggingPriority(.defaultLow, for: .vertical)
        
        // Add tap gesture
        let tapGesture = UITapGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.handleTap(_:)))
        textView.addGestureRecognizer(tapGesture)
        
        return textView
    }
    
    func updateUIView(_ uiView: UITextView, context: Context) {
        // Update attributed text if changed
        let newAttributedText = createAttributedText()
        if uiView.attributedText != newAttributedText {
            uiView.attributedText = newAttributedText
        }
        
        // Simple approach: ensure we have exactly one tap gesture recognizer
        let existingGestures = uiView.gestureRecognizers ?? []
        let tapGestures = existingGestures.filter { $0 is UITapGestureRecognizer }
        
        // If we have more than one tap gesture, remove all and add one
        if tapGestures.count != 1 {
            print("DEBUG: TappableTextView has \(tapGestures.count) tap gestures, resetting to 1")
            
            // Remove all tap gestures
            for gesture in tapGestures {
                uiView.removeGestureRecognizer(gesture)
            }
            
            // Add our gesture
            let tapGesture = UITapGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.handleTap(_:)))
            uiView.addGestureRecognizer(tapGesture)
            print("DEBUG: Added new tap gesture to TappableTextView")
        }
    }
    
    func sizeThatFits(_ proposal: ProposedViewSize, uiView: UITextView, context: Context) -> CGSize? {
        // Let the text view size itself based on its content
        let size = uiView.sizeThatFits(CGSize(
            width: proposal.width ?? .greatestFiniteMagnitude,
            height: .greatestFiniteMagnitude
        ))
        return size
    }
    
    static func dismantleUIView(_ uiView: UITextView, coordinator: Coordinator) {
        // Clean up gesture recognizers when view is destroyed
        if let gestureRecognizers = uiView.gestureRecognizers {
            for gesture in gestureRecognizers {
                uiView.removeGestureRecognizer(gesture)
            }
        }
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }
    
    private func createAttributedText() -> NSAttributedString {
        // Use Times New Roman for Greek, system font for other scripts
        // System font handles Devanagari, Arabic, Hebrew, etc. properly
        let font = isGreek ?
            UIFont(name: "Times New Roman", size: fontSize) ?? UIFont.systemFont(ofSize: fontSize) :
            UIFont.systemFont(ofSize: fontSize)

        let attributedString = NSMutableAttributedString(string: text)

        // IMPORTANT: Use NSString length for NSRange, not Swift String count
        // This prevents range errors with multi-byte Unicode like Devanagari
        let nsText = text as NSString
        let fullRange = NSRange(location: 0, length: nsText.length)

        // Set base font and color
        attributedString.addAttribute(.font, value: font, range: fullRange)
        attributedString.addAttribute(.foregroundColor, value: UIColor.label, range: fullRange)
        
        // Apply highlighting if we have words to highlight
        if !wordsWithoutDefinitions.isEmpty || !wordsWithMorphologyOnly.isEmpty || !searchHighlightedWords.isEmpty {
            // Process each character to find word boundaries
            var currentWordStart: String.Index? = nil
            var i = text.startIndex
            
            while i < text.endIndex {
                let char = text[i]
                let isWordChar = char.isLetter || (char == "'" || char == "'" || char == "ʼ")
                
                if isWordChar {
                    if currentWordStart == nil {
                        currentWordStart = i
                    }
                } else if let start = currentWordStart {
                    // We've found the end of a word
                    let wordString = String(text[start..<i])
                    let nsRange = NSRange(start..<i, in: text)
                    
                    // Check for search highlighting first (highest priority)
                    if isSearchHighlighted(wordString) {
                        // Bold yellow background for search terms
                        let boldFont = isGreek ?
                            UIFont(name: "Times New Roman Bold", size: fontSize) ?? UIFont.boldSystemFont(ofSize: fontSize) :
                            UIFont.boldSystemFont(ofSize: fontSize)
                        attributedString.addAttribute(.font, value: boldFont, range: nsRange)
                        attributedString.addAttribute(.backgroundColor, value: UIColor.yellow.withAlphaComponent(0.6), range: nsRange)
                    } else if wordsWithoutDefinitions.contains(wordString) {
                        // Bold red for no definition
                        let boldFont = isGreek ?
                            UIFont(name: "Times New Roman Bold", size: fontSize) ?? UIFont.boldSystemFont(ofSize: fontSize) :
                            UIFont.boldSystemFont(ofSize: fontSize)
                        attributedString.addAttribute(.font, value: boldFont, range: nsRange)
                        attributedString.addAttribute(.foregroundColor, value: UIColor.red, range: nsRange)
                    } else if wordsWithMorphologyOnly.contains(wordString) {
                        // Italic orange for morphology only
                        let italicFont = isGreek ?
                            UIFont(name: "Times New Roman Italic", size: fontSize) ?? UIFont.italicSystemFont(ofSize: fontSize) :
                            UIFont.italicSystemFont(ofSize: fontSize)
                        attributedString.addAttribute(.font, value: italicFont, range: nsRange)
                        attributedString.addAttribute(.foregroundColor, value: UIColor.orange, range: nsRange)
                    }
                    currentWordStart = nil
                }
                
                i = text.index(after: i)
            }
            
            // Handle last word if text ends with a word character
            if let start = currentWordStart {
                let wordString = String(text[start..<text.endIndex])
                let nsRange = NSRange(start..<text.endIndex, in: text)
                
                // Check for search highlighting first (highest priority)
                if isSearchHighlighted(wordString) {
                    // Bold yellow background for search terms
                    let boldFont = isGreek ?
                        UIFont(name: "Times New Roman Bold", size: fontSize) ?? UIFont.boldSystemFont(ofSize: fontSize) :
                        UIFont.boldSystemFont(ofSize: fontSize)
                    attributedString.addAttribute(.font, value: boldFont, range: nsRange)
                    attributedString.addAttribute(.backgroundColor, value: UIColor.yellow.withAlphaComponent(0.6), range: nsRange)
                } else if wordsWithoutDefinitions.contains(wordString) {
                    let boldFont = isGreek ?
                        UIFont(name: "Times New Roman Bold", size: fontSize) ?? UIFont.boldSystemFont(ofSize: fontSize) :
                        UIFont.boldSystemFont(ofSize: fontSize)
                    attributedString.addAttribute(.font, value: boldFont, range: nsRange)
                    attributedString.addAttribute(.foregroundColor, value: UIColor.red, range: nsRange)
                } else if wordsWithMorphologyOnly.contains(wordString) {
                    let italicFont = isGreek ?
                        UIFont(name: "Times New Roman Italic", size: fontSize) ?? UIFont.italicSystemFont(ofSize: fontSize) :
                        UIFont.italicSystemFont(ofSize: fontSize)
                    attributedString.addAttribute(.font, value: italicFont, range: nsRange)
                    attributedString.addAttribute(.foregroundColor, value: UIColor.orange, range: nsRange)
                }
            }
        }
        
        return attributedString
    }

    private func isSearchHighlighted(_ word: String) -> Bool {
        // Check exact match first
        if searchHighlightedWords.contains(word) {
            return true
        }

        // Check normalized versions for Greek text
        if isGreek {
            let normalizedWord = TextNormalization.normalizeWord(word, isGreek: true)
            if searchHighlightedWords.contains(normalizedWord) {
                return true
            }

            // Check if any highlight word matches this word when normalized
            for highlightWord in searchHighlightedWords {
                if TextNormalization.normalizeWord(highlightWord, isGreek: true) == normalizedWord {
                    return true
                }
            }
        }

        return false
    }
    
    class Coordinator: NSObject {
        let parent: TappableTextView
        
        init(_ parent: TappableTextView) {
            self.parent = parent
        }
        
        @objc func handleTap(_ gesture: UITapGestureRecognizer) {
            print("DEBUG: TappableTextView handleTap called")
            
            // Dictionary now works for both Greek and Latin texts
            print("DEBUG: TappableTextView - handling tap for \(parent.isGreek ? "Greek" : "Latin") text")
            
            guard let textView = gesture.view as? UITextView else { 
                print("DEBUG: TappableTextView handleTap - no textView")
                return 
            }
            
            // Get tap location
            let location = gesture.location(in: textView)
            
            // Use NSLayoutManager for precise character hit testing
            let layoutManager = textView.layoutManager
            let textContainer = textView.textContainer
            let textStorage = textView.textStorage
            
            // Convert tap location to character index
            let characterIndex = layoutManager.characterIndex(for: location,
                                                             in: textContainer,
                                                             fractionOfDistanceBetweenInsertionPoints: nil)
            
            // Make sure we're within text bounds
            guard characterIndex < textStorage.length else { return }
            
            let text = parent.text

            // Convert characterIndex (UTF-16 position) to String.Index
            guard let tappedIndex = text.utf16Index(at: characterIndex) else {
                print("DEBUG: Could not convert character index")
                return
            }

            // Find word boundaries around the tapped character
            var wordStart = tappedIndex
            var wordEnd = tappedIndex < text.endIndex ? text.index(after: tappedIndex) : text.endIndex

            // Move backward to find word start
            while wordStart > text.startIndex {
                let prevIndex = text.index(before: wordStart)
                let char = text[prevIndex]
                // Include hyphen for Akkadian/cuneiform transliteration (e.g., "it-bi-e-ma")
                // Include apostrophe variants
                let isWordChar = char.isLetter || char == "-" || char == "'" || char == "'" || char == "ʼ"
                if !isWordChar {
                    break
                }
                wordStart = prevIndex
            }

            // Move forward to find word end
            while wordEnd < text.endIndex {
                let char = text[wordEnd]
                // Include hyphen for Akkadian/cuneiform transliteration (e.g., "it-bi-e-ma")
                // Include apostrophe variants
                let isWordChar = char.isLetter || char == "-" || char == "'" || char == "'" || char == "ʼ"
                if !isWordChar {
                    break
                }
                wordEnd = text.index(after: wordEnd)
            }
            
            // Extract the word (wordStart and wordEnd are already String.Index)
            let tappedWord = String(text[wordStart..<wordEnd]).trimmingCharacters(in: .whitespacesAndNewlines)
            
            if !tappedWord.isEmpty {
                // Clean the word of punctuation but keep apostrophes and hyphens within words
                let cleanWord = tappedWord.filter { $0.isLetter || $0 == "'" || $0 == "'" || $0 == "ʼ" || $0 == "-" }
                
                if !cleanWord.isEmpty {
                    let normalizedWord = parent.isGreek ? normalizeGreek(cleanWord) : cleanWord.lowercased()
                    
                    let wordObject = Word(
                        id: 0,
                        word: cleanWord,
                        bookId: parent.bookId,
                        lineNumber: parent.lineNumber,
                        sequenceNumber: parent.sequenceNumber,
                        wordPosition: 0
                    )
                    
                    print("DEBUG: TappableTextView found word: '\(cleanWord)' normalized: '\(normalizedWord)'")
                    
                    // Call on main thread
                    if Thread.isMainThread {
                        print("DEBUG: TappableTextView calling onWordTapped on main thread")
                        parent.onWordTapped(wordObject)
                    } else {
                        print("DEBUG: TappableTextView calling onWordTapped async")
                        DispatchQueue.main.async {
                            self.parent.onWordTapped(wordObject)
                        }
                    }
                } else {
                    print("DEBUG: TappableTextView - cleanWord is empty")
                }
            }
        }
        
        private func normalizeGreek(_ word: String) -> String {
            // Use comprehensive normalization matching Android version
            // This uses NFD decomposition to handle ALL diacritic combinations
            return GreekNormalizer.normalize(word)
        }
    }
}

// Extension to safely convert UTF-16 offsets to String.Index
extension String {
    func utf16Index(at offset: Int) -> String.Index? {
        guard offset >= 0 && offset <= self.utf16.count else { return nil }
        return self.utf16.index(self.utf16.startIndex, offsetBy: offset, limitedBy: self.utf16.endIndex)
            .flatMap { String.Index($0, within: self) }
    }
}

// Alternative implementation using Text instead of UITextView for better stability
struct AlternativeTappableTextView: View {
    let text: String
    let fontSize: CGFloat
    let isGreek: Bool
    let bookId: String
    let lineNumber: Int
    let sequenceNumber: Int
    let onWordTapped: (Word) -> Void
    
    var body: some View {
        Text(text)
            .font(isGreek ? 
                .custom("Times New Roman", size: fontSize) :
                .system(size: fontSize))
            .onTapGesture { location in
                // For now, just return the first word as a test
                let words = text.split(separator: " ").map(String.init)
                if let firstWord = words.first {
                    let cleanWord = firstWord.filter { $0.isLetter }
                    if !cleanWord.isEmpty {
                        _ = isGreek ? normalizeGreek(cleanWord) : cleanWord.lowercased()
                        
                        let wordObject = Word(
                            id: 0,
                            word: cleanWord,
                            bookId: bookId,
                            lineNumber: lineNumber,
                            sequenceNumber: sequenceNumber,
                            wordPosition: 0
                        )
                        
                        onWordTapped(wordObject)
                    }
                }
            }
    }
    
    private func normalizeGreek(_ word: String) -> String {
        let normalized = word.lowercased()
        return normalized.applyingTransform(.stripDiacritics, reverse: false) ?? normalized
    }
}