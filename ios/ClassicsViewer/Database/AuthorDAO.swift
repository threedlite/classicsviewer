import Foundation
import SQLite3

protocol AuthorDAOProtocol {
    func getGreekAuthors() async throws -> [Author]
    func getLatinAuthors() async throws -> [Author]
    func getAuthorsByLanguage(_ language: String) async throws -> [Author]
    func getAuthorWithWorks(authorId: String) async throws -> AuthorWithWorks?
}

class AuthorDAO: AuthorDAOProtocol {
    // Remove direct database manager reference - will use async version

    func getGreekAuthors() async throws -> [Author] {
        return try await getAuthorsByLanguage("greek")
    }

    func getLatinAuthors() async throws -> [Author] {
        return try await getAuthorsByLanguage("latin")
    }

    func getAuthorsByLanguage(_ language: String) async throws -> [Author] {
        let query = """
            SELECT id, name, name_alt, language, has_translations
            FROM authors
            WHERE language = ?
            ORDER BY name
        """

        return try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [language]) { [self] statement in
            authorFromStatement(statement)
        }
    }
    
    func getAuthorWithWorks(authorId: String) async throws -> AuthorWithWorks? {
        // First get the author
        let authorQuery = """
            SELECT id, name, name_alt, language, has_translations
            FROM authors
            WHERE id = ?
        """

        let authors = try await DatabaseManagerAsync.shared.executeQuery(authorQuery, parameters: [authorId]) { [self] statement in
            authorFromStatement(statement)
        }
        
        guard let author = authors.first else { return nil }
        
        // Then get the works
        let worksQuery = """
            SELECT id, author_id, title, title_alt, title_english, type, urn, description
            FROM works
            WHERE author_id = ?
            ORDER BY id
        """
        
        let works = try await DatabaseManagerAsync.shared.executeQuery(worksQuery, parameters: [authorId]) { [self] statement in
            workFromStatement(statement)
        }
        
        return AuthorWithWorks(author: author, works: works)
    }
    
    private func authorFromStatement(_ statement: OpaquePointer) -> Author? {
        guard let idCString = sqlite3_column_text(statement, 0),
              let nameCString = sqlite3_column_text(statement, 1),
              let languageCString = sqlite3_column_text(statement, 3) else {
            return nil
        }
        
        let id = String(cString: idCString)
        let name = String(cString: nameCString)
        let language = String(cString: languageCString)
        
        var nameAlt: String? = nil
        if let nameAltCString = sqlite3_column_text(statement, 2) {
            nameAlt = String(cString: nameAltCString)
        }
        
        let hasTranslations = Int(sqlite3_column_int(statement, 4))
        
        return Author(id: id, name: name, nameAlt: nameAlt, language: language, hasTranslations: hasTranslations)
    }
    
    private func workFromStatement(_ statement: OpaquePointer) -> Work? {
        guard let idCString = sqlite3_column_text(statement, 0),
              let authorIdCString = sqlite3_column_text(statement, 1),
              let titleCString = sqlite3_column_text(statement, 2) else {
            return nil
        }
        
        let id = String(cString: idCString)
        let authorId = String(cString: authorIdCString)
        let title = String(cString: titleCString)
        
        var titleAlt: String? = nil
        if let titleAltCString = sqlite3_column_text(statement, 3) {
            titleAlt = String(cString: titleAltCString)
        }
        
        var titleEnglish: String? = nil
        if let titleEnglishCString = sqlite3_column_text(statement, 4) {
            titleEnglish = String(cString: titleEnglishCString)
        }
        
        var type: String? = nil
        if let typeCString = sqlite3_column_text(statement, 5) {
            type = String(cString: typeCString)
        }
        
        var urn: String? = nil
        if let urnCString = sqlite3_column_text(statement, 6) {
            urn = String(cString: urnCString)
        }
        
        var description: String? = nil
        if let descriptionCString = sqlite3_column_text(statement, 7) {
            description = String(cString: descriptionCString)
        }
        
        return Work(id: id, authorId: authorId, title: title, titleAlt: titleAlt, titleEnglish: titleEnglish, type: type, urn: urn, description: description)
    }
}