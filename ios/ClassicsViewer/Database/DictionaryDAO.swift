import Foundation
import SQLite3

protocol DictionaryDAOProtocol {
    func getDictionaryEntry(_ word: String, language: String) async throws -> DictionaryResult?
    func getDictionaryEntryByHeadword(_ headword: String, language: String) async throws -> DictionaryResult?
    func getAllDictionaryEntries(_ word: String, language: String, skipCompoundDecomposition: Bool) async throws -> [DictionaryMatchEntry]
    func getMainDictionaryEntriesOnly(_ word: String, language: String) async throws -> [DictionaryMatchEntry]
}

struct DictionaryResult {
    let id: Int?
    let word: String
    let entryPlain: String?
    let entryHtml: String?
    let language: String
    let source: String?
}

struct DictionaryMatchEntry {
    let lemma: String
    let definition: String
    let morphInfo: String?
    let isDirectMatch: Bool
    let confidence: Double?
    let source: String?
    let hasNonTreebankPath: Bool // true means it has at least one non-treebank source path
}

class DictionaryDAO: DictionaryDAOProtocol {
    // Use async database manager
    private let userDictDAO = UserDictionaryDAO()
    private let normalizationDAO = NormalizationPatternDAO()
    private let userNormalizationHelper = UserNormalizationPatternHelper()

    func getDictionaryEntry(_ word: String, language: String) async throws -> DictionaryResult? {
        print("DictionaryDAO: Looking up word='\(word)', language='\(language)'")

        // For dictionary lookup: only normalize Greek text
        // For other languages, use exact word (matches Android approach)
        let normalizedWord: String
        if language == "greek" {
            normalizedWord = GreekNormalizer.normalize(word)
        } else if language == "latin" {
            normalizedWord = word.lowercased()
        } else {
            // Sanskrit and others: use exact word without normalization
            normalizedWord = word
        }

        print("DictionaryDAO: Normalized '\(word)' to '\(normalizedWord)'")

        // FIRST: Check user dictionary (if enabled)
        do {
            let userEntries = try await userDictDAO.searchUserDictionary(lemma: normalizedWord, language: language)
            if let userEntry = userEntries.first {
                print("DictionaryDAO: Found entry in user dictionary for '\(normalizedWord)'")
                return DictionaryResult(
                    id: userEntry.id,
                    word: userEntry.lemma,
                    entryPlain: userEntry.definitionPlain,
                    entryHtml: userEntry.definitionHtml,
                    language: userEntry.language,
                    source: userEntry.sourceName
                )
            }
            
            // Also check user lemma mappings
            let userLemmas = try await userDictDAO.searchUserMappings(inflectedForm: word, language: language)
            for userLemma in userLemmas {
                let lemmaEntries = try await userDictDAO.searchUserDictionary(lemma: userLemma, language: language)
                if let lemmaEntry = lemmaEntries.first {
                    print("DictionaryDAO: Found lemma '\(userLemma)' in user mappings for '\(word)'")
                    return DictionaryResult(
                        id: lemmaEntry.id,
                        word: lemmaEntry.lemma,
                        entryPlain: lemmaEntry.definitionPlain,
                        entryHtml: lemmaEntry.definitionHtml,
                        language: lemmaEntry.language,
                        source: lemmaEntry.sourceName
                    )
                }
            }
        } catch {
            // User database might not be initialized, continue with main dictionary
            print("DictionaryDAO: User dictionary check failed: \(error)")
        }
        
        // First try direct dictionary lookup (matching Android's approach)
        // For Greek: use headword_normalized_ultra for fallback
        // For other languages: use exact headword match
        let query: String
        let queryParam: String

        if language == "greek" {
            // Greek can use ultra-normalized column
            query = """
                SELECT id, headword, entry_plain, entry_html, language, source
                FROM dictionary_entries
                WHERE headword_normalized_ultra = ? AND language = ?
                ORDER BY
                    CASE source
                        WHEN 'lsj' THEN 1
                        WHEN 'cunliffe' THEN 2
                        WHEN 'wiktionary' THEN 3
                        ELSE 4
                    END
                LIMIT 1
            """
            queryParam = normalizedWord
        } else {
            // Non-Greek languages: match exact headword (Android approach)
            query = """
                SELECT id, headword, entry_plain, entry_html, language, source
                FROM dictionary_entries
                WHERE headword = ? AND language = ?
                ORDER BY
                    CASE source
                        WHEN 'lsj' THEN 1
                        WHEN 'cunliffe' THEN 2
                        WHEN 'wiktionary' THEN 3
                        ELSE 4
                    END
                LIMIT 1
            """
            queryParam = normalizedWord
        }

        print("DictionaryDAO: Executing query with word '\(queryParam)' and language '\(language)'")

        let results: [DictionaryResult] = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [queryParam, language]) { statement in
            let id = Int(sqlite3_column_int(statement, 0))
            
            guard let wordCString = sqlite3_column_text(statement, 1),
                  let languageCString = sqlite3_column_text(statement, 4) else {
                // Return dummy result that will be filtered out
                return DictionaryResult(id: nil, word: "", entryPlain: nil, entryHtml: nil, language: "", source: nil)
            }
            
            let word = String(cString: wordCString)
            let language = String(cString: languageCString)
            
            var entryPlain: String? = nil
            if let plainCString = sqlite3_column_text(statement, 2) {
                entryPlain = String(cString: plainCString)
            }
            
            var entryHtml: String? = nil
            if let htmlCString = sqlite3_column_text(statement, 3) {
                entryHtml = String(cString: htmlCString)
            }
            
            var source: String? = nil
            if let sourceCString = sqlite3_column_text(statement, 5) {
                source = String(cString: sourceCString)
            }
            
            return DictionaryResult(
                id: id,
                word: word,
                entryPlain: entryPlain,
                entryHtml: entryHtml,
                language: language,
                source: source
            )
        }
        
        // Filter out empty entries and return if found
        if let result = results.first(where: { !$0.word.isEmpty }) {
            print("DictionaryDAO: FOUND direct entry for '\(normalizedWord)'")
            return result
        }
        
        print("DictionaryDAO: No direct entry found for '\(normalizedWord)'")
        
        // If not found, try lemma map (works for any language)
        if !language.isEmpty {
            print("DictionaryDAO: Trying lemma lookup for \(language) word '\(word)'")
            
            // First try with the original word
            let lemmaQuery = """
                SELECT DISTINCT lemma FROM lemma_map 
                WHERE word_form = ? 
                ORDER BY confidence DESC
                LIMIT 10
            """
            
            print("DictionaryDAO: Querying lemma_map with word_form = '\(word)'")
            var lemmaResults = try await DatabaseManagerAsync.shared.executeQuery(lemmaQuery, parameters: [word]) { statement in
                if let lemmaCString = sqlite3_column_text(statement, 0) {
                    return String(cString: lemmaCString)
                }
                return nil
            }
            
            // If no results with original word, try with normalized form
            if lemmaResults.isEmpty {
                print("DictionaryDAO: No lemma found with word_form, trying word_form_normalized_ultra = '\(normalizedWord)'")
                let normalizedLemmaQuery = """
                    SELECT DISTINCT lemma FROM lemma_map 
                    WHERE word_form_normalized_ultra = ? 
                    ORDER BY confidence DESC
                    LIMIT 10
                """
                
                lemmaResults = try await DatabaseManagerAsync.shared.executeQuery(normalizedLemmaQuery, parameters: [normalizedWord]) { statement in
                    if let lemmaCString = sqlite3_column_text(statement, 0) {
                        return String(cString: lemmaCString)
                    }
                    return nil
                }
            }
            
            // Try each lemma in order, skipping self-referential mappings
            for lemma in lemmaResults.compactMap({ $0 }) {
                // Skip self-referential mappings (where lemma equals the original word or its cleaned form)
                let cleanedWord = word.replacingOccurrences(of: "'", with: "")
                    .replacingOccurrences(of: "'", with: "")
                    .replacingOccurrences(of: "ʼ", with: "")
                    .replacingOccurrences(of: "᾽", with: "")
                    .replacingOccurrences(of: "̓", with: "")
                    .replacingOccurrences(of: "᾿", with: "")
                
                if lemma == word || lemma == cleanedWord || lemma.contains("'") || lemma.contains("'") {
                    print("DictionaryDAO: Skipping self-referential lemma '\(lemma)' for word '\(word)'")
                    continue
                }
                
                print("DictionaryDAO: Found lemma '\(lemma)' for word '\(word)'")
                
                // Now look up dictionary entry for this lemma
                // Use the exact headword lookup since lemmas are already in headword form
                if let result = try await getDictionaryEntryByHeadword(lemma, language: language) {
                    return result
                }
            }
            
            print("DictionaryDAO: No valid lemma found for '\(word)' in lemma_map table")
        }
        
        // No entry found
        return nil
    }
    
    // Look up dictionary entry by exact headword (no normalization)
    func getDictionaryEntryByHeadword(_ headword: String, language: String) async throws -> DictionaryResult? {
        print("DictionaryDAO: Looking up by exact headword='\(headword)', language='\(language)'")
        
        // For Sanskrit and other non-Greek languages: only match exact headword
        // For Greek: also try normalized form (for macron variations)
        let query: String
        let queryParams: [Any]

        if language == "greek" {
            query = """
                SELECT id, headword, entry_plain, entry_html, language, source
                FROM dictionary_entries
                WHERE (headword = ? OR headword_normalized_ultra = ?) AND language = ?
                ORDER BY
                    CASE source
                        WHEN 'lsj' THEN 1
                        WHEN 'cunliffe' THEN 2
                        WHEN 'wiktionary' THEN 3
                        ELSE 4
                    END
                LIMIT 1
            """
            let normalizedHeadword = GreekNormalizer.normalize(headword)
            queryParams = [headword, normalizedHeadword, language]
        } else {
            // Non-Greek: exact headword match only (Android approach)
            query = """
                SELECT id, headword, entry_plain, entry_html, language, source
                FROM dictionary_entries
                WHERE headword = ? AND language = ?
                ORDER BY
                    CASE source
                        WHEN 'lsj' THEN 1
                        WHEN 'cunliffe' THEN 2
                        WHEN 'wiktionary' THEN 3
                        ELSE 4
                    END
                LIMIT 1
            """
            queryParams = [headword, language]
        }

        print("DictionaryDAO: Executing query with headword '\(headword)' and language '\(language)'")

        let results: [DictionaryResult] = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: queryParams) { statement in
            let id = Int(sqlite3_column_int(statement, 0))
            
            guard let wordCString = sqlite3_column_text(statement, 1),
                  let languageCString = sqlite3_column_text(statement, 4) else {
                // Return dummy result that will be filtered out
                return DictionaryResult(id: nil, word: "", entryPlain: nil, entryHtml: nil, language: "", source: nil)
            }
            
            let word = String(cString: wordCString)
            let language = String(cString: languageCString)
            
            var entryPlain: String? = nil
            if let plainCString = sqlite3_column_text(statement, 2) {
                entryPlain = String(cString: plainCString)
            }
            
            var entryHtml: String? = nil
            if let htmlCString = sqlite3_column_text(statement, 3) {
                entryHtml = String(cString: htmlCString)
            }
            
            var source: String? = nil
            if let sourceCString = sqlite3_column_text(statement, 5) {
                source = String(cString: sourceCString)
            }
            
            return DictionaryResult(
                id: id,
                word: word,
                entryPlain: entryPlain,
                entryHtml: entryHtml,
                language: language,
                source: source
            )
        }
        
        // Filter out empty entries and return if found
        if let result = results.first(where: { !$0.word.isEmpty }) {
            print("DictionaryDAO: FOUND entry for headword '\(headword)'")
            return result
        } else {
            print("DictionaryDAO: No entry found for headword '\(headword)'")
        }
        
        return nil
    }
    
    // Resolve lemma chain to find canonical form with dictionary entry (like Android)
    private func resolveLemmaChain(_ lemma: String, language: String, visitedLemmas: inout Set<String>, maxDepth: Int = 3) async throws -> String {
        // Prevent infinite loops
        if visitedLemmas.contains(lemma) || visitedLemmas.count >= maxDepth {
            return lemma
        }
        visitedLemmas.insert(lemma)
        
        // Check if this lemma has a MEANINGFUL dictionary entry (not just "Morphological entry")
        let checkQuery = """
            SELECT entry_plain, entry_html FROM dictionary_entries 
            WHERE headword = ? AND language = ?
        """
        
        let entries: [(String?, String?)] = try await DatabaseManagerAsync.shared.executeQuery(checkQuery, parameters: [lemma, language]) { statement in
            var entryPlain: String? = nil
            if let plainCString = sqlite3_column_text(statement, 0) {
                entryPlain = String(cString: plainCString)
            }
            
            var entryHtml: String? = nil
            if let htmlCString = sqlite3_column_text(statement, 1) {
                entryHtml = String(cString: htmlCString)
            }
            
            return (entryPlain, entryHtml)
        }
        
        // Check if any entry has meaningful content
        let hasMeaningfulEntry = entries.contains { (plain, html) in
            let plainText = plain ?? ""
            let htmlText = html ?? ""
            // Check if it's more than just "Morphological entry"
            return (!plainText.isEmpty && plainText != "Morphological entry") ||
                   (!htmlText.isEmpty && !htmlText.contains("Morphological entry"))
        }
        
        if hasMeaningfulEntry {
            return lemma  // Found a real definition, stop here
        }
        
        // Check if this lemma appears as a word_form that maps to another lemma
        let nextLemmaQuery = """
            SELECT DISTINCT lemma, confidence FROM lemma_map 
            WHERE word_form = ? AND lemma != ?
            ORDER BY confidence DESC
            LIMIT 1
        """
        
        let nextMappings: [(String, Double?)] = try await DatabaseManagerAsync.shared.executeQuery(nextLemmaQuery, parameters: [lemma, lemma]) { statement in
            guard let lemmaCString = sqlite3_column_text(statement, 0) else {
                return nil
            }
            
            let nextLemma = String(cString: lemmaCString)
            let confidence = sqlite3_column_type(statement, 1) == SQLITE_NULL ? nil : sqlite3_column_double(statement, 1)
            
            return (nextLemma, confidence)
        }
        
        if let (nextLemma, _) = nextMappings.first {
            // Recursively resolve the chain
            return try await resolveLemmaChain(nextLemma, language: language, visitedLemmas: &visitedLemmas, maxDepth: maxDepth)
        }
        
        return lemma  // No further mapping found
    }
    
    // Get ALL dictionary entries for a word (from all sources, with morphology support)
    func getAllDictionaryEntries(_ word: String, language: String, skipCompoundDecomposition: Bool = false) async throws -> [DictionaryMatchEntry] {
        print("!!! DictionaryDAO.getAllDictionaryEntries CALLED !!!")
        print("DictionaryDAO.getAllDictionaryEntries: Getting all dictionary entries for word='\(word)', language='\(language)'")
        
        var entries: [DictionaryMatchEntry] = []
        let addedLemmas = NSMutableSet()
        
        // Clean punctuation and normalize apostrophes (includes NFC Unicode normalization)
        // Matches Android PerseusRepository.kt lines 284-298
        let normalizedResult: (cleaned: String, acuteVariant: String?) = language == "greek" ?
            GreekTextNormalization.prepareForDictionaryLookup(word, convertGrave: true) :
            (cleaned: word.replacingOccurrences(of: "[.,;:!?·]", with: "", options: .regularExpression), acuteVariant: nil)

        let cleanedWord = normalizedResult.cleaned
        let acuteVariant = normalizedResult.acuteVariant

        print("DictionaryDAO: Cleaned word '\(word)' -> '\(cleanedWord)'")
        if let acute = acuteVariant {
            print("DictionaryDAO: Created acute variant: '\(acute)'")
        }

        // Normalize the word (for user dictionary and lemma lookups - NOT for direct headword match)
        let normalizedWord = language == "greek" ? GreekNormalizer.normalize(cleanedWord) : cleanedWord.lowercased()
        
        // FIRST: Check user dictionary (if enabled) - both direct and via mappings
        // Now using robust UserDatabaseManagerAsync with proper error handling
        do {
            // Check direct user dictionary lookup with normalized word
            let userEntries = try await userDictDAO.searchUserDictionary(lemma: normalizedWord, language: language)
            for userEntry in userEntries {
                print("DictionaryDAO: Found user dictionary entry for '\(normalizedWord)': \(userEntry.lemma)")
                entries.append(DictionaryMatchEntry(
                    lemma: userEntry.lemma,
                    definition: userEntry.definitionHtml ?? userEntry.definitionPlain,
                    morphInfo: nil,
                    isDirectMatch: true,
                    confidence: nil,
                    source: userEntry.sourceName,
                    hasNonTreebankPath: true  // User entries always have non-treebank path
                ))
                addedLemmas.add(userEntry.lemma)
            }
        } catch {
            // User dictionary not available or error occurred - continue without it
            print("DictionaryDAO: User dictionary lookup failed safely: \(error)")
        }
        
        do {
            // Check user lemma mappings
            let userLemmas = try await userDictDAO.searchUserMappings(inflectedForm: cleanedWord, language: language)
            for userLemma in userLemmas {
                if !addedLemmas.contains(userLemma) {
                    do {
                        let lemmaEntries = try await userDictDAO.searchUserDictionary(lemma: userLemma, language: language)
                        for lemmaEntry in lemmaEntries {
                            print("DictionaryDAO: Found user lemma '\(userLemma)' for '\(cleanedWord)'")
                            entries.append(DictionaryMatchEntry(
                                lemma: lemmaEntry.lemma,
                                definition: lemmaEntry.definitionHtml ?? lemmaEntry.definitionPlain,
                                morphInfo: "From user mapping: \(cleanedWord) → \(userLemma)",
                                isDirectMatch: false,
                                confidence: 1.0,
                                source: lemmaEntry.sourceName,
                                hasNonTreebankPath: true  // User entries always have non-treebank path
                            ))
                            addedLemmas.add(userLemma)
                        }
                    } catch {
                        print("DictionaryDAO: Failed to get user dictionary entry for lemma '\(userLemma)': \(error)")
                    }
                }
            }
        } catch {
            // User mappings not available or error occurred - continue without them
            print("DictionaryDAO: User mappings lookup failed safely: \(error)")
        }
        
        // Acute variant is now created above with GreekTextNormalization.prepareForDictionaryLookup
        // This includes support for vowels with breathing marks (smooth/rough)
        // Matches Android PerseusRepository.kt lines 294-298
        
        // First try direct dictionary lookup - get ALL entries from ALL sources
        // Android queries exact headword without normalization
        let directQuery = """
            SELECT headword, entry_plain, entry_html, source
            FROM dictionary_entries
            WHERE headword = ? AND language = ?
            ORDER BY
                CASE source
                    WHEN 'lsj' THEN 1
                    WHEN 'cunliffe' THEN 2
                    WHEN 'wiktionary' THEN 3
                    ELSE 4
                END
        """

        print("DictionaryDAO: Executing direct query for cleanedWord='\(cleanedWord)', language='\(language)'")
        let directResults: [(String, String?, String?, String?)] = try await DatabaseManagerAsync.shared.executeQuery(directQuery, parameters: [cleanedWord, language]) { statement in
            guard let headwordCString = sqlite3_column_text(statement, 0) else {
                print("DictionaryDAO: No headword found in row")
                return nil
            }
            
            let headword = String(cString: headwordCString)
            print("DictionaryDAO: Found headword='\(headword)' in direct query")
            
            var entryPlain: String? = nil
            if let plainCString = sqlite3_column_text(statement, 1) {
                entryPlain = String(cString: plainCString)
            }
            
            var entryHtml: String? = nil
            if let htmlCString = sqlite3_column_text(statement, 2) {
                entryHtml = String(cString: htmlCString)
            }
            
            var source: String? = nil
            if let sourceCString = sqlite3_column_text(statement, 3) {
                source = String(cString: sourceCString)
            }
            
            return (headword, entryPlain, entryHtml, source)
        }
        
        for result in directResults.compactMap({ $0 }) {
            let definition = result.2 ?? result.1 ?? ""
            print("DictionaryDAO: Found direct match - headword='\(result.0)', source='\(result.3 ?? "unknown")'")
            entries.append(DictionaryMatchEntry(
                lemma: result.0,  // Use actual headword from database (matches Android)
                definition: definition,
                morphInfo: nil,  // Base forms don't have morphological info
                isDirectMatch: true,
                confidence: nil,
                source: result.3,
                hasNonTreebankPath: true  // Direct matches always have non-treebank path
            ))
            addedLemmas.add(result.0)  // Track actual headword
        }
        
        // If no direct match and we have an acute variant, try that too
        if entries.isEmpty && acuteVariant != nil && acuteVariant != cleanedWord {
            let acuteResults: [(String, String?, String?, String?)] = try await DatabaseManagerAsync.shared.executeQuery(directQuery, parameters: [acuteVariant!, language]) { statement in
                guard let headwordCString = sqlite3_column_text(statement, 0) else {
                    return nil
                }
                
                let headword = String(cString: headwordCString)
                
                var entryPlain: String? = nil
                if let plainCString = sqlite3_column_text(statement, 1) {
                    entryPlain = String(cString: plainCString)
                }
                
                var entryHtml: String? = nil
                if let htmlCString = sqlite3_column_text(statement, 2) {
                    entryHtml = String(cString: htmlCString)
                }
                
                var source: String? = nil
                if let sourceCString = sqlite3_column_text(statement, 3) {
                    source = String(cString: sourceCString)
                }
                
                return (headword, entryPlain, entryHtml, source)
            }
            
            for result in acuteResults.compactMap({ $0 }) {
                let definition = result.2 ?? result.1 ?? ""
                entries.append(DictionaryMatchEntry(
                    lemma: acuteVariant!,
                    definition: definition,
                    morphInfo: nil,
                    isDirectMatch: true,
                    confidence: 1.0,
                    source: result.3,
                    hasNonTreebankPath: true  // Direct matches always have non-treebank path
                ))
                addedLemmas.add(acuteVariant!)
            }
        }
        
        // Get all possible lemmas from lemma map (works for all languages, not just Greek)
        if language == "greek" || language == "sanskrit" || !language.isEmpty {
            print("DictionaryDAO: Getting all lemmas for \(language) word")
            
            // Get all lemma mappings with confidence scores and source
            let lemmaMapQuery = """
                SELECT DISTINCT lemma, confidence, morph_info, source
                FROM lemma_map
                WHERE word_form = ?
                ORDER BY confidence DESC
            """
            
            print("DictionaryDAO: Executing lemma map query for cleanedWord='\(cleanedWord)'")
            var lemmaMappings: [(String, Double?, String?, String?)] = try await DatabaseManagerAsync.shared.executeQuery(lemmaMapQuery, parameters: [cleanedWord]) { statement in
                guard let lemmaCString = sqlite3_column_text(statement, 0) else {
                    print("DictionaryDAO: No lemma found in row")
                    return nil
                }
                
                let lemma = String(cString: lemmaCString)
                print("DictionaryDAO: Found lemma='\(lemma)' in lemma_map")
                let confidence = sqlite3_column_type(statement, 1) == SQLITE_NULL ? nil : sqlite3_column_double(statement, 1)

                var morphInfo: String? = nil
                if let morphCString = sqlite3_column_text(statement, 2) {
                    morphInfo = String(cString: morphCString)
                    print("DictionaryDAO: Retrieved morphInfo: '\(morphInfo ?? "")'")
                } else {
                    print("DictionaryDAO: No morphInfo in column 2")
                }

                var source: String? = nil
                if let sourceCString = sqlite3_column_text(statement, 3) {
                    source = String(cString: sourceCString)
                }

                return (lemma, confidence, morphInfo, source)
            }
            
            // If no results with original word and we have an acute variant, try that
            if lemmaMappings.isEmpty && acuteVariant != nil && acuteVariant != cleanedWord {
                lemmaMappings = try await DatabaseManagerAsync.shared.executeQuery(lemmaMapQuery, parameters: [acuteVariant!]) { statement in
                    guard let lemmaCString = sqlite3_column_text(statement, 0) else {
                        return nil
                    }

                    let lemma = String(cString: lemmaCString)
                    let confidence = sqlite3_column_type(statement, 1) == SQLITE_NULL ? nil : sqlite3_column_double(statement, 1)

                    var morphInfo: String? = nil
                    if let morphCString = sqlite3_column_text(statement, 2) {
                        morphInfo = String(cString: morphCString)
                    }

                    var source: String? = nil
                    if let sourceCString = sqlite3_column_text(statement, 3) {
                        source = String(cString: sourceCString)
                    }

                    return (lemma, confidence, morphInfo, source)
                }
                print("DictionaryDAO: Found \(lemmaMappings.count) lemma mappings for acute variant: \(acuteVariant!)")
            }
            
            // If no results with word_form, try with ultra-normalized form
            if lemmaMappings.isEmpty {
                print("DictionaryDAO: No lemma found with word_form, trying word_form_normalized_ultra = '\(normalizedWord)'")
                let normalizedLemmaQuery = """
                    SELECT DISTINCT lemma, confidence, morph_info, source
                    FROM lemma_map
                    WHERE word_form_normalized_ultra = ?
                    ORDER BY confidence DESC
                """
                
                lemmaMappings = try await DatabaseManagerAsync.shared.executeQuery(normalizedLemmaQuery, parameters: [normalizedWord]) { statement in
                    guard let lemmaCString = sqlite3_column_text(statement, 0) else {
                        return nil
                    }

                    let lemma = String(cString: lemmaCString)
                    let confidence = sqlite3_column_type(statement, 1) == SQLITE_NULL ? nil : sqlite3_column_double(statement, 1)

                    var morphInfo: String? = nil
                    if let morphCString = sqlite3_column_text(statement, 2) {
                        morphInfo = String(cString: morphCString)
                    }

                    var source: String? = nil
                    if let sourceCString = sqlite3_column_text(statement, 3) {
                        source = String(cString: sourceCString)
                    }

                    return (lemma, confidence, morphInfo, source)
                }
                print("DictionaryDAO: Found \(lemmaMappings.count) lemma mappings for ultra-normalized form")
            }
            
            // If still no exact match and word ends with apostrophe, try prefix search (for elided forms)
            if lemmaMappings.isEmpty && (cleanedWord.hasSuffix("'") || cleanedWord.hasSuffix("'") || cleanedWord.hasSuffix("ʼ")) {
                let prefix = cleanedWord
                    .replacingOccurrences(of: "'", with: "")
                    .replacingOccurrences(of: "'", with: "")
                    .replacingOccurrences(of: "ʼ", with: "")
                
                print("DictionaryDAO: No exact match for apostrophe word '\(cleanedWord)', trying prefix: '\(prefix)'")
                
                let prefixQuery = """
                    SELECT DISTINCT lemma, confidence, morph_info, source
                    FROM lemma_map
                    WHERE word_form LIKE ? || '%'
                    ORDER BY LENGTH(word_form), confidence DESC
                """

                let allPrefixMappings: [(String, Double?, String?, String?)] = try await DatabaseManagerAsync.shared.executeQuery(prefixQuery, parameters: [prefix]) { statement in
                    guard let lemmaCString = sqlite3_column_text(statement, 0) else {
                        return nil
                    }
                    
                    let lemma = String(cString: lemmaCString)
                    let confidence = sqlite3_column_type(statement, 1) == SQLITE_NULL ? nil : sqlite3_column_double(statement, 1)

                    var morphInfo: String? = nil
                    if let morphCString = sqlite3_column_text(statement, 2) {
                        morphInfo = String(cString: morphCString)
                    }

                    var source: String? = nil
                    if let sourceCString = sqlite3_column_text(statement, 3) {
                        source = String(cString: sourceCString)
                    }

                    return (lemma, confidence, morphInfo, source)
                }
                
                // Filter to prefer shorter words and limit results (like Android)
                _ = prefix.count == 1 ? prefix.count + 2 : prefix.count + 4
                lemmaMappings = Array(allPrefixMappings.prefix(10))  // Limit to top 10 matches
                
                print("DictionaryDAO: Found \(allPrefixMappings.count) total matches, filtered to \(lemmaMappings.count)")
            }
            
            print("DictionaryDAO: Found \(lemmaMappings.count) lemma mappings")
            for mapping in lemmaMappings.prefix(3) {
                print("  Mapping: lemma='\(mapping.0)', confidence=\(mapping.1 ?? 0), morphInfo='\(mapping.2 ?? "nil")', source='\(mapping.3 ?? "nil")'")
            }

            // Track lemmas with non-treebank sources
            var lemmasWithNonTreebankSources = Set<String>()
            for mapping in lemmaMappings.compactMap({ $0 }) {
                let source = mapping.3 ?? ""
                if source != "perseus_treebank" {
                    lemmasWithNonTreebankSources.insert(mapping.0)
                }
            }

            // Group by lemma and keep highest confidence mapping for each lemma (like Android bestByLemma)
            var bestByLemma: [String: (String, Double?, String?, String?)] = [:]
            for mapping in lemmaMappings.compactMap({ $0 }) {
                let lemma = mapping.0
                if let existing = bestByLemma[lemma] {
                    if (mapping.1 ?? 0) > (existing.1 ?? 0) {
                        bestByLemma[lemma] = mapping
                    }
                } else {
                    bestByLemma[lemma] = mapping
                }
            }
            
            print("DictionaryDAO: Found \(bestByLemma.count) unique lemmas after grouping")
            
            // For each unique lemma not already added, resolve chain and get dictionary entries
            for (lemma, mapping) in bestByLemma {
                // Skip self-referential mappings (where lemma equals the original word or still contains apostrophes)
                if lemma == cleanedWord || lemma.contains("'") || lemma.contains("'") || lemma.contains("ʼ") {
                    print("DictionaryDAO: Skipping self-referential lemma '\(lemma)' for word '\(cleanedWord)'")
                    continue
                }
                
                let confidence = mapping.1
                let morphInfo = mapping.2
                let source = mapping.3

                // Check if this lemma has non-treebank paths
                let hasNonTreebankPath = lemmasWithNonTreebankSources.contains(lemma)

                if !addedLemmas.contains(lemma) {
                    // Follow lemma chain to find the canonical form with a dictionary entry
                    var visitedLemmas = Set<String>()
                    let resolvedLemma = try await resolveLemmaChain(lemma, language: language, visitedLemmas: &visitedLemmas)
                    let chainFollowed = resolvedLemma != lemma
                    
                    if chainFollowed {
                        print("DictionaryDAO: Resolved lemma chain: \(lemma) → \(resolvedLemma)")
                    }
                    
                    // Get ALL entries for the resolved lemma from ALL sources
                    let lemmaEntriesQuery: String
                    let lemmaQueryParams: [Any]

                    if language == "greek" {
                        // Greek: check both exact headword and normalized form (for macron variations)
                        let resolvedLemmaNormalized = GreekNormalizer.normalize(resolvedLemma)
                        lemmaEntriesQuery = """
                            SELECT headword, entry_plain, entry_html, source
                            FROM dictionary_entries
                            WHERE (headword = ? OR headword_normalized_ultra = ?) AND language = ?
                            ORDER BY
                                CASE source
                                    WHEN 'lsj' THEN 1
                                    WHEN 'cunliffe' THEN 2
                                    WHEN 'wiktionary' THEN 3
                                    ELSE 4
                                END
                        """
                        lemmaQueryParams = [resolvedLemma, resolvedLemmaNormalized, language]
                    } else {
                        // Sanskrit and others: exact headword only
                        lemmaEntriesQuery = """
                            SELECT headword, entry_plain, entry_html, source
                            FROM dictionary_entries
                            WHERE headword = ? AND language = ?
                            ORDER BY
                                CASE source
                                    WHEN 'lsj' THEN 1
                                    WHEN 'cunliffe' THEN 2
                                    WHEN 'wiktionary' THEN 3
                                    ELSE 4
                                END
                        """
                        lemmaQueryParams = [resolvedLemma, language]
                    }

                    let lemmaResults: [(String, String?, String?, String?)] = try await DatabaseManagerAsync.shared.executeQuery(lemmaEntriesQuery, parameters: lemmaQueryParams) { statement in
                        guard let headwordCString = sqlite3_column_text(statement, 0) else {
                            return nil
                        }
                        
                        let headword = String(cString: headwordCString)
                        
                        var entryPlain: String? = nil
                        if let plainCString = sqlite3_column_text(statement, 1) {
                            entryPlain = String(cString: plainCString)
                        }
                        
                        var entryHtml: String? = nil
                        if let htmlCString = sqlite3_column_text(statement, 2) {
                            entryHtml = String(cString: htmlCString)
                        }
                        
                        var source: String? = nil
                        if let sourceCString = sqlite3_column_text(statement, 3) {
                            source = String(cString: sourceCString)
                        }
                        
                        return (headword, entryPlain, entryHtml, source)
                    }
                    
                    for result in lemmaResults.compactMap({ $0 }) {
                        let definition = result.2 ?? result.1 ?? ""
                        print("DictionaryDAO: Adding entry with morphInfo: '\(morphInfo ?? "nil")'")

                        // Determine final source with treebank annotation
                        var finalSource = result.3
                        if !hasNonTreebankPath && source == "perseus_treebank" {
                            finalSource = (finalSource ?? "") + " (via Treebank)"
                        }

                        entries.append(DictionaryMatchEntry(
                            lemma: resolvedLemma,  // Use resolved lemma for display
                            definition: definition,
                            morphInfo: morphInfo,
                            isDirectMatch: false,
                            confidence: confidence,
                            source: finalSource,
                            hasNonTreebankPath: hasNonTreebankPath
                        ))
                    }
                    
                    if !lemmaResults.isEmpty {
                        addedLemmas.add(lemma)  // Mark original lemma as added
                        if chainFollowed {
                            addedLemmas.add(resolvedLemma)  // Also mark resolved lemma
                        }
                    }
                }
            }
        }

        // NEW: Try compound word decomposition if no entries found
        // Matches Android PerseusRepository.kt line 835
        if entries.isEmpty && !skipCompoundDecomposition {
            // Only for Greek and Latin
            if language.lowercased() == "greek" || language.lowercased() == "latin" {
                // Only for words >= 6 characters
                if cleanedWord.count >= 6 {
                    print("DictionaryDAO: No entries found, attempting compound decomposition for '\(cleanedWord)'")

                    let helper = DictionaryLookupHelper()
                    if let compound = try await helper.decomposeCompoundWord(
                        word: cleanedWord,
                        language: language,
                        dictionaryDAO: self
                    ) {
                        print("DictionaryDAO: Successfully decomposed '\(cleanedWord)' → prefix: '\(compound.prefix)' (\(compound.prefixMeaning)), stem: '\(compound.stem)'")

                        // Create synthetic entry showing decomposition
                        let syntheticDefinition = """
                            [Compound Word]
                            Prefix: \(compound.prefix) (\(compound.prefixMeaning))
                            Stem: \(compound.stem)\(compound.stemLemma != nil ? "\n→ See: \(compound.stemLemma!)" : "")
                            """

                        let syntheticEntry = DictionaryMatchEntry(
                            lemma: cleanedWord,
                            definition: syntheticDefinition,
                            morphInfo: "compound word decomposition",
                            isDirectMatch: false,
                            confidence: 0.8,
                            source: "compound_analysis",
                            hasNonTreebankPath: true
                        )

                        entries.append(syntheticEntry)

                        // Also add the stem's dictionary entries if found
                        if let stemLemma = compound.stemLemma {
                            print("DictionaryDAO: Looking up stem lemma '\(stemLemma)'")
                            let stemEntries = try await getAllDictionaryEntries(
                                stemLemma,
                                language: language,
                                skipCompoundDecomposition: true  // Don't recurse
                            )
                            print("DictionaryDAO: Found \(stemEntries.count) entries for stem '\(stemLemma)'")
                            entries.append(contentsOf: stemEntries)
                        }
                    } else {
                        print("DictionaryDAO: Could not decompose '\(cleanedWord)' as compound word")
                    }
                }
            }
        }

        // If no entries found and it's Greek, try ultra-normalized search (like Android)
        if entries.isEmpty && language == "greek" {
            print("DictionaryDAO: No entries found, trying ultra-normalized search for '\(cleanedWord)'")
            print("DictionaryDAO: Original word was: '\(word)'")
            print("DictionaryDAO: Cleaned word is: '\(cleanedWord)'")
            
            // Ultra-normalize the word (remove ALL diacritics)
            let ultraNormalized = GreekNormalizer.normalize(cleanedWord)
            print("DictionaryDAO: Ultra-normalized form: '\(ultraNormalized)'")
            print("DictionaryDAO: Ultra-normalized bytes: \(ultraNormalized.utf8.map { String(format: "%02X", $0) }.joined(separator: " "))")
            
            // Try lemma mappings with ultra-normalized form
            let ultraLemmaQuery = """
                SELECT DISTINCT lemma, confidence, morph_info, source
                FROM lemma_map
                WHERE word_form_normalized_ultra = ?
                ORDER BY confidence DESC
                LIMIT 5
            """

            let ultraLemmaMappings: [(String, Double?, String?, String?)] = try await DatabaseManagerAsync.shared.executeQuery(ultraLemmaQuery, parameters: [ultraNormalized]) { statement in
                guard let lemmaCString = sqlite3_column_text(statement, 0) else {
                    return nil
                }
                
                let lemma = String(cString: lemmaCString)
                let confidence = sqlite3_column_type(statement, 1) == SQLITE_NULL ? nil : sqlite3_column_double(statement, 1)

                var morphInfo: String? = nil
                if let morphCString = sqlite3_column_text(statement, 2) {
                    morphInfo = String(cString: morphCString)
                }

                var source: String? = nil
                if let sourceCString = sqlite3_column_text(statement, 3) {
                    source = String(cString: sourceCString)
                }

                return (lemma, confidence, morphInfo, source)
            }
            
            print("DictionaryDAO: Found \(ultraLemmaMappings.count) ultra-normalized lemma mappings")
            for m in ultraLemmaMappings {
                print("DictionaryDAO: Ultra mapping found - lemma: '\(m.0)', confidence: \(m.1 ?? 0), morphInfo: '\(m.2 ?? "nil")', source: '\(m.3 ?? "nil")'")
            }

            // Track lemmas with non-treebank sources for ultra-normalized mappings
            var ultraLemmasWithNonTreebankSources = Set<String>()
            for mapping in ultraLemmaMappings.compactMap({ $0 }) {
                let source = mapping.3 ?? ""
                if source != "perseus_treebank" {
                    ultraLemmasWithNonTreebankSources.insert(mapping.0)
                }
            }

            for mapping in ultraLemmaMappings.compactMap({ $0 }) {
                let lemma = mapping.0
                let confidence = mapping.1
                let morphInfo = mapping.2
                let source = mapping.3
                
                print("DictionaryDAO: Processing ultra-normalized lemma: '\(lemma)'")
                
                // Skip if we already added this lemma
                if addedLemmas.contains(lemma) {
                    print("DictionaryDAO: Skipping '\(lemma)' - already added")
                    continue
                }
                
                // Get ALL entries for this lemma from ALL sources
                // Check both exact headword match AND normalized match (to handle macron variations like μυρίος vs μῡρίος)
                let lemmaNormalized = GreekNormalizer.normalize(lemma)
                let ultraEntriesQuery = """
                    SELECT headword, entry_plain, entry_html, source 
                    FROM dictionary_entries 
                    WHERE (headword = ? OR headword_normalized_ultra = ?) AND language = ?
                """
                
                let ultraResults: [(String, String?, String?, String?)] = try await DatabaseManagerAsync.shared.executeQuery(ultraEntriesQuery, parameters: [lemma, lemmaNormalized, language]) { statement in
                    guard let headwordCString = sqlite3_column_text(statement, 0) else {
                        return nil
                    }
                    
                    let headword = String(cString: headwordCString)
                    
                    var entryPlain: String? = nil
                    if let plainCString = sqlite3_column_text(statement, 1) {
                        entryPlain = String(cString: plainCString)
                    }
                    
                    var entryHtml: String? = nil
                    if let htmlCString = sqlite3_column_text(statement, 2) {
                        entryHtml = String(cString: htmlCString)
                    }
                    
                    var source: String? = nil
                    if let sourceCString = sqlite3_column_text(statement, 3) {
                        source = String(cString: sourceCString)
                    }
                    
                    return (headword, entryPlain, entryHtml, source)
                }
                
                // Check if this lemma has non-treebank paths
                let hasNonTreebankPath = ultraLemmasWithNonTreebankSources.contains(lemma)

                for result in ultraResults.compactMap({ $0 }) {
                    let definition = result.2 ?? result.1 ?? ""

                    // Determine final source with treebank annotation
                    var finalSource = result.3
                    if !hasNonTreebankPath && source == "perseus_treebank" {
                        finalSource = (finalSource ?? "") + " (via Treebank)"
                    }

                    entries.append(DictionaryMatchEntry(
                        lemma: lemma,
                        definition: definition,
                        morphInfo: morphInfo ?? "found via simplified form",
                        isDirectMatch: false,
                        confidence: confidence ?? 0.7,  // Lower confidence for ultra-normalized matches
                        source: finalSource,
                        hasNonTreebankPath: hasNonTreebankPath
                    ))
                }
                
                if !ultraResults.isEmpty {
                    addedLemmas.add(lemma)
                }
            }
        }
        
        // Sort entries to match Android behavior
        let sortedEntries = entries.sorted { (entry1, entry2) -> Bool in
            // FIRST priority: entries with non-treebank paths come before treebank-only entries
            if entry1.hasNonTreebankPath != entry2.hasNonTreebankPath {
                return entry1.hasNonTreebankPath // true (has non-treebank) comes before false (treebank-only)
            }

            // SECOND priority: Minimal entry penalty
            // Deprioritize entries without actual definition content
            // This ensures entries with real definitions appear before cross-reference stubs
            // Also specifically deprioritize etymology-only entries
            // Matches Android PerseusRepository.kt lines 906-936
            let penalty1 = getEntryQualityPenalty(entry1)
            let penalty2 = getEntryQualityPenalty(entry2)

            if penalty1 != penalty2 {
                return penalty1 < penalty2 // Lower penalty comes first
            }

            // THIRD priority: source ranking
            let source1Priority = getSourcePriority(entry1.source)
            let source2Priority = getSourcePriority(entry2.source)

            if source1Priority != source2Priority {
                return source1Priority < source2Priority
            }

            // FOURTH priority: ascending length of the dictionary form (lemma)
            if entry1.lemma.count != entry2.lemma.count {
                return entry1.lemma.count < entry2.lemma.count
            }

            // FIFTH priority: alphabetical order as tiebreaker for same length
            return entry1.lemma < entry2.lemma
        }
        
        print("DictionaryDAO: About to return \(sortedEntries.count) total dictionary entries")
        for (index, entry) in sortedEntries.prefix(3).enumerated() {
            print("  Entry \(index): lemma='\(entry.lemma)', source='\(entry.source ?? "none")', isDirectMatch=\(entry.isDirectMatch), has definition: \(!entry.definition.isEmpty)")
        }
        print("!!! DictionaryDAO.getAllDictionaryEntries RETURNING \(sortedEntries.count) entries !!!")
        return sortedEntries
    }
    
    func getMainDictionaryEntriesOnly(_ word: String, language: String) async throws -> [DictionaryMatchEntry] {
        print("DictionaryDAO.getMainDictionaryEntriesOnly: Getting main dictionary entries only for word='\(word)', language='\(language)'")
        
        // Call the full getAllDictionaryEntries method to get comprehensive results
        let allEntries = try await getAllDictionaryEntries(word, language: language)
        
        // Filter out user database entries (keep only main dictionary sources)
        let mainDictionaryEntries = allEntries.filter { entry in
            // Keep entries from main dictionary sources (LSJ, Cunliffe, Wiktionary, etc.)
            // Filter out entries from user sources
            guard let source = entry.source else { return true } // Keep entries with no source specified
            return source.lowercased() != "user import" && !source.contains("user")
        }
        
        print("DictionaryDAO.getMainDictionaryEntriesOnly: Filtered \(allEntries.count) total entries down to \(mainDictionaryEntries.count) main dictionary entries for '\(word)'")
        return mainDictionaryEntries
    }
    
    private func getSourcePriority(_ source: String?) -> Int {
        switch source?.lowercased() {
        case "lsj":
            return 0
        case "cunliffe":
            return 1
        case "wiktionary":
            return 2
        default:
            return 3
        }
    }

    /// Get quality penalty for dictionary entry
    /// Matches Android PerseusRepository.kt lines 906-936
    /// Higher penalty = lower quality entry = sorted later
    private func getEntryQualityPenalty(_ entry: DictionaryMatchEntry) -> Int {
        // Strip HTML tags to get plain definition
        let plainDef = entry.definition.replacingOccurrences(of: "<[^>]+>", with: "", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)

        // Check if entry is ONLY etymology (no definition after etymology section)
        let isEtymologyOnly: Bool
        if plainDef.hasPrefix("Etymology:") || plainDef.hasPrefix("†") {
            // Remove etymology prefix and check remaining content
            var contentAfterEtymology = plainDef
            // Remove "Etymology: ..." until we hit definition markers or end
            // Note: Swift's String.range doesn't support dotMatchesLineSeparators, so we use [\s\S] to match any character including newlines
            if let range = contentAfterEtymology.range(of: "^Etymology:[\\s\\S]*?(?=\\n[A-Z]\\.|\\n[IVX]+\\.|\\n\\d+\\.|\\Z)", options: .regularExpression) {
                contentAfterEtymology.removeSubrange(range)
            }
            // Remove "† ..." lines
            if let range = contentAfterEtymology.range(of: "^†[^\\n]*?\\n", options: .regularExpression) {
                contentAfterEtymology.removeSubrange(range)
            }
            contentAfterEtymology = contentAfterEtymology.trimmingCharacters(in: .whitespacesAndNewlines)

            // Check if there's actual definition content
            let hasDefinition = contentAfterEtymology.range(of: "[A-Z]\\.|[IVX]+\\.|^\\d+\\.", options: [.regularExpression, .anchored]) != nil
            isEtymologyOnly = !hasDefinition && contentAfterEtymology.count < 50
        } else {
            isEtymologyOnly = false
        }

        // Check for minimal cross-reference entries
        // Note: Swift's String.range doesn't support dotMatchesLineSeparators, so we use [\s\S] to match any character including newlines
        let contentAfterEtymology = plainDef.replacingOccurrences(of: "^Etymology:[\\s\\S]*?\\n", with: "", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
        let hasActualContent = contentAfterEtymology.range(of: "[a-zA-Z]{3,}", options: .regularExpression) != nil
        let isMinimal = !hasActualContent

        // Heavy penalty for etymology-only, lighter for other minimal entries
        if isEtymologyOnly {
            return 2000
        } else if isMinimal {
            return 1000
        } else {
            return 0
        }
    }

    // MARK: - Normalization Helper

    /// Normalize word for dictionary lookup using pattern-based normalization when available
    private func normalizeForLookup(_ word: String, language: String) async throws -> String {
        if language == "greek" {
            return GreekNormalizer.normalize(word)
        } else if language == "latin" {
            return word.lowercased()
        } else {
            // Try to load patterns for this language (Perseus database first, then user database)
            var patterns: [NormalizationPattern] = []

            // Load from Perseus database
            do {
                patterns = try await normalizationDAO.getPatternsByLanguage(language)
            } catch {
                print("DictionaryDAO: Failed to load Perseus normalization patterns for \(language): \(error)")
            }

            // If no Perseus patterns, try user database
            if patterns.isEmpty {
                do {
                    let userPatterns = try await userNormalizationHelper.getPatternsByLanguage(language)
                    patterns = userPatterns.map { userPattern in
                        NormalizationPattern(
                            id: userPattern.id,
                            language: userPattern.language,
                            pattern: userPattern.pattern,
                            replacement: userPattern.replacement,
                            description: userPattern.description,
                            priority: userPattern.priority
                        )
                    }
                } catch {
                    print("DictionaryDAO: Failed to load user normalization patterns for \(language): \(error)")
                }
            }

            // Apply pattern-based normalization if patterns available
            if !patterns.isEmpty {
                return PatternBasedNormalizer.normalize(word, language: language, patterns: patterns)
            } else {
                // Fallback to basic lowercase
                return word.lowercased()
            }
        }
    }
}