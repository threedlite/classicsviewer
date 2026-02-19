import Foundation
import SQLite3

protocol LemmaDAOProtocol {
    func getLemmaMap(wordForm: String) async throws -> LemmaMap?
    func getAllLemmaMaps(wordForm: String) async throws -> [LemmaMap]
    func searchLemmas(query: String) async throws -> [LemmaMap]
    func getDictionaryEntry(headword: String, language: String) async throws -> DictionaryEntry?
    func getAllDictionaryEntries(word: String, isGreek: Bool) async throws -> [DictionaryEntryResult]
}

struct DictionaryEntryResult {
    let entry: DictionaryEntry
    let lemmaMap: LemmaMap?
    let isDirect: Bool // true if word matches headword directly
}

class LemmaDAO: LemmaDAOProtocol {
    // Use async database manager

    func getLemmaMap(wordForm: String) async throws -> LemmaMap? {
        let query = """
            SELECT word_form, word_form_normalized_ultra, lemma, confidence, source, morph_info
            FROM lemma_map
            WHERE word_form = ?
            ORDER BY confidence DESC
            LIMIT 1
        """

        let lemmaMaps = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [wordForm]) { [self] statement in
            lemmaMapFromStatement(statement)
        }

        return lemmaMaps.first
    }
    
    func searchLemmas(query: String) async throws -> [LemmaMap] {
        let query = """
            SELECT DISTINCT word_form, word_form_normalized_ultra, lemma, confidence, source, morph_info
            FROM lemma_map
            WHERE lemma LIKE ? OR word_form LIKE ?
            ORDER BY lemma, confidence DESC
            LIMIT 100
        """

        let searchPattern = "%\(query)%"

        return try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [searchPattern, searchPattern]) { [self] statement in
            lemmaMapFromStatement(statement)
        }
    }
    
    func getAllLemmaMaps(wordForm: String) async throws -> [LemmaMap] {
        let query = """
            SELECT word_form, word_form_normalized_ultra, lemma, confidence, source, morph_info
            FROM lemma_map
            WHERE word_form = ?
            ORDER BY confidence DESC
        """

        return try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [wordForm]) { [self] statement in
            lemmaMapFromStatement(statement)
        }
    }

    func getDictionaryEntry(headword: String, language: String) async throws -> DictionaryEntry? {
        let query = """
            SELECT id, headword, headword_normalized_ultra, language, entry_xml, entry_html, entry_plain, source
            FROM dictionary_entries
            WHERE headword = ? AND language = ?
            LIMIT 1
        """

        let entries = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [headword, language]) { [self] statement in
            dictionaryEntryFromStatement(statement)
        }

        return entries.first
    }
    
    func getAllDictionaryEntries(word: String, isGreek: Bool) async throws -> [DictionaryEntryResult] {
        let language = isGreek ? "greek" : "latin"
        let normalizedWord = TextNormalization.normalizeWord(word, isGreek: isGreek)
        var results: [DictionaryEntryResult] = []
        var addedLemmas = Set<String>()
        
        // 1. First check for direct dictionary match
        if let directEntry = try await getDictionaryEntry(headword: normalizedWord, language: language) {
            results.append(DictionaryEntryResult(
                entry: directEntry,
                lemmaMap: nil,
                isDirect: true
            ))
            addedLemmas.insert(normalizedWord)
        }
        
        // 2. For Greek, look up lemmas in lemma_map
        if isGreek {
            let lemmaMaps = try await getAllLemmaMaps(wordForm: normalizedWord)
            
            // Group by lemma and keep highest confidence for each
            var bestByLemma: [String: LemmaMap] = [:]
            for lemmaMap in lemmaMaps {
                if let existing = bestByLemma[lemmaMap.lemma] {
                    if (lemmaMap.confidence ?? 0) > (existing.confidence ?? 0) {
                        bestByLemma[lemmaMap.lemma] = lemmaMap
                    }
                } else {
                    bestByLemma[lemmaMap.lemma] = lemmaMap
                }
            }
            
            // Get dictionary entries for each unique lemma
            for (lemma, lemmaMap) in bestByLemma.sorted(by: { 
                ($0.value.confidence ?? 0) > ($1.value.confidence ?? 0)
            }) {
                if !addedLemmas.contains(lemma) {
                    if let entry = try await getDictionaryEntry(headword: lemma, language: language) {
                        results.append(DictionaryEntryResult(
                            entry: entry,
                            lemmaMap: lemmaMap,
                            isDirect: false
                        ))
                        addedLemmas.insert(lemma)
                    }
                }
            }
        }
        
        return results
    }
    
    private func lemmaMapFromStatement(_ statement: OpaquePointer) -> LemmaMap? {
        guard let wordFormCString = sqlite3_column_text(statement, 0),
              let wordNormalizedCString = sqlite3_column_text(statement, 1),
              let lemmaCString = sqlite3_column_text(statement, 2) else {
            return nil
        }
        
        let wordForm = String(cString: wordFormCString)
        let wordNormalized = String(cString: wordNormalizedCString)
        let lemma = String(cString: lemmaCString)
        
        var confidence: Double? = nil
        if sqlite3_column_type(statement, 3) != SQLITE_NULL {
            confidence = sqlite3_column_double(statement, 3)
        }
        
        var source: String? = nil
        if let sourceCString = sqlite3_column_text(statement, 4) {
            source = String(cString: sourceCString)
        }
        
        var morphInfo: String? = nil
        if let morphInfoCString = sqlite3_column_text(statement, 5) {
            morphInfo = String(cString: morphInfoCString)
        }
        
        return LemmaMap(id: nil, wordForm: wordForm, wordFormNormalizedUltra: wordNormalized, lemma: lemma,
                       confidence: confidence, source: source, morphInfo: morphInfo)
    }
    
    private func dictionaryEntryFromStatement(_ statement: OpaquePointer) -> DictionaryEntry? {
        let id = Int(sqlite3_column_int(statement, 0))
        
        guard let headwordCString = sqlite3_column_text(statement, 1),
              let headwordNormalizedCString = sqlite3_column_text(statement, 2),
              let languageCString = sqlite3_column_text(statement, 3) else {
            return nil
        }
        
        let headword = String(cString: headwordCString)
        let headwordNormalized = String(cString: headwordNormalizedCString)
        let language = String(cString: languageCString)
        
        var entryXml: String? = nil
        if let entryXmlCString = sqlite3_column_text(statement, 4) {
            entryXml = String(cString: entryXmlCString)
        }
        
        var entryHtml: String? = nil
        if let entryHtmlCString = sqlite3_column_text(statement, 5) {
            entryHtml = String(cString: entryHtmlCString)
        }
        
        var entryPlain: String? = nil
        if let entryPlainCString = sqlite3_column_text(statement, 6) {
            entryPlain = String(cString: entryPlainCString)
        }
        
        var source: String? = nil
        if let sourceCString = sqlite3_column_text(statement, 7) {
            source = String(cString: sourceCString)
        }
        
        return DictionaryEntry(id: id, headword: headword, headwordNormalizedUltra: headwordNormalized,
                             language: language, entryXml: entryXml, entryHtml: entryHtml,
                             entryPlain: entryPlain, source: source)
    }
}