import Foundation
import SQLite3

protocol LemmaMapDAOProtocol {
    func getLemmaForWord(_ word: String) async throws -> String?
    func getLemmaMapEntry(_ word: String) async throws -> LemmaMapEntry?
    func getAllLemmaMappings(_ word: String) async throws -> [LemmaMapEntry]
}

struct LemmaMapEntry {
    let wordForm: String
    let lemma: String
    let morphInfo: String?
    let confidence: Double?
}

class LemmaMapDAO: LemmaMapDAOProtocol {
    // Use async database manager
    
    func getLemmaForWord(_ word: String) async throws -> String? {
        let query = """
            SELECT lemma FROM lemma_map 
            WHERE word_form_normalized_ultra = ? 
            LIMIT 1
        """
        
        let results = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [word]) { statement in
            if let lemmaCString = sqlite3_column_text(statement, 0) {
                return String(cString: lemmaCString)
            }
            return nil
        }
        
        return results.first
    }
    
    func getLemmaMapEntry(_ word: String) async throws -> LemmaMapEntry? {
        let query = """
            SELECT word_form, lemma, morph_info 
            FROM lemma_map 
            WHERE word_form_normalized_ultra = ? 
            LIMIT 1
        """
        
        let results: [LemmaMapEntry] = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [word]) { statement in
            guard let wordFormCString = sqlite3_column_text(statement, 0),
                  let lemmaCString = sqlite3_column_text(statement, 1) else {
                return LemmaMapEntry(wordForm: "", lemma: "", morphInfo: nil, confidence: nil)
            }
            
            let wordForm = String(cString: wordFormCString)
            let lemma = String(cString: lemmaCString)
            
            var morphInfo: String? = nil
            if let morphCString = sqlite3_column_text(statement, 2) {
                morphInfo = String(cString: morphCString)
            }
            
            return LemmaMapEntry(
                wordForm: wordForm,
                lemma: lemma,
                morphInfo: morphInfo,
                confidence: nil
            )
        }
        
        // Filter out empty entries and return first valid one
        return results.first { !$0.wordForm.isEmpty && !$0.lemma.isEmpty }
    }
    
    /// Get ALL lemma mappings for a word with confidence scores
    func getAllLemmaMappings(_ word: String) async throws -> [LemmaMapEntry] {
        print("LemmaMapDAO: Looking up word_form = '\(word)'")
        
        // First try exact match on word_form (like Android does)
        let query = """
            SELECT word_form, lemma, morph_info, confidence
            FROM lemma_map 
            WHERE word_form = ?
            ORDER BY confidence DESC
        """
        
        print("LemmaMapDAO: Executing query with parameter: '\(word)'")
        let results: [LemmaMapEntry] = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [word]) { statement in
            guard let wordFormCString = sqlite3_column_text(statement, 0),
                  let lemmaCString = sqlite3_column_text(statement, 1) else {
                return nil
            }
            
            let wordForm = String(cString: wordFormCString)
            let lemma = String(cString: lemmaCString)
            
            var morphInfo: String? = nil
            if let morphCString = sqlite3_column_text(statement, 2) {
                morphInfo = String(cString: morphCString)
            }
            
            var confidence: Double? = nil
            if sqlite3_column_type(statement, 3) != SQLITE_NULL {
                confidence = sqlite3_column_double(statement, 3)
            }
            
            return LemmaMapEntry(
                wordForm: wordForm,
                lemma: lemma,
                morphInfo: morphInfo,
                confidence: confidence
            )
        }.compactMap { $0 }
        
        print("LemmaMapDAO: Found \(results.count) raw results")
        
        // Filter out empty entries
        let filtered = results.filter { !$0.wordForm.isEmpty && !$0.lemma.isEmpty }
        print("LemmaMapDAO: Returning \(filtered.count) valid results")
        for (index, entry) in filtered.enumerated() {
            print("  [\(index)]: lemma='\(entry.lemma)', morph='\(entry.morphInfo ?? "none")', confidence=\(entry.confidence ?? 0)")
        }
        return filtered
    }
}