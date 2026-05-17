import Foundation
import SQLite3

// SQLite needs a destructor marker when binding text; the standard Swift value.
private let RHETORIC_SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)

private func rhetoricColumnText(_ statement: OpaquePointer, _ index: Int32) -> String? {
    guard let cString = sqlite3_column_text(statement, index) else { return nil }
    return String(cString: cString)
}

// MARK: - Models

struct RhetoricSection: Identifiable {
    let id: String
    let title: String
    let entryCount: Int
}

struct RhetoricEntryRef: Identifiable {
    let id: String
    let name: String
}

struct RhetoricEntry: Identifiable {
    let id: String
    let sectionId: String
    let name: String
    let etymologyGreek: String?
    let etymology: String?
    let definition: String
    let examples: String?
}

struct RhetoricCrossRef: Identifiable {
    let toId: String
    let toName: String
    let kind: String          // "related" | "see_also"
    let note: String?
    var id: String { "\(kind)/\(toId)" }
}

enum RhetoricError: LocalizedError {
    case resourceMissing
    case cannotOpen(String)
    case query(String)

    var errorDescription: String? {
        switch self {
        case .resourceMissing:
            return "rhetoric.db.zip is missing from the app bundle."
        case .cannotOpen(let detail):
            return "Could not open the rhetoric database: \(detail)"
        case .query(let detail):
            return "Rhetoric query failed: \(detail)"
        }
    }
}

/// Read-only access to the bundled rhetoric reference database (rhetoric.db).
///
/// Self-contained: a separate SQLite file with its own connection, opened with
/// the raw sqlite3 C API. It does not touch the Perseus text database or its
/// DatabaseManagerAsync. rhetoric.db.zip ships in the app bundle and is
/// extracted to Application Support on first use / after an app update.
actor RhetoricDatabase {
    static let shared = RhetoricDatabase()
    private var handle: OpaquePointer?

    // MARK: - Connection

    private func connection() throws -> OpaquePointer {
        if let handle { return handle }
        let dbURL = try Self.extractedDatabaseURL()
        var db: OpaquePointer?
        guard sqlite3_open_v2(dbURL.path, &db, SQLITE_OPEN_READONLY, nil) == SQLITE_OK,
              let db else {
            throw RhetoricError.cannotOpen(dbURL.lastPathComponent)
        }
        handle = db
        return db
    }

    /// Extract rhetoric.db from the bundled ZIP on first use, and re-extract
    /// after an app update (CFBundleVersion change).
    private static func extractedDatabaseURL() throws -> URL {
        let fm = FileManager.default
        let support = fm.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        try? fm.createDirectory(at: support, withIntermediateDirectories: true)
        let dbURL = support.appendingPathComponent("rhetoric.db")

        let version = (Bundle.main.infoDictionary?["CFBundleVersion"] as? String) ?? "0"
        let versionKey = "rhetoricDbExtractedVersion"
        if fm.fileExists(atPath: dbURL.path),
           UserDefaults.standard.string(forKey: versionKey) == version {
            return dbURL
        }
        guard let zipURL = Bundle.main.url(forResource: "rhetoric.db", withExtension: "zip") else {
            throw RhetoricError.resourceMissing
        }
        try? fm.removeItem(at: dbURL)
        try ZIPHandler.extractDatabase(from: zipURL, to: dbURL)
        UserDefaults.standard.set(version, forKey: versionKey)
        return dbURL
    }

    // MARK: - Query helper

    private func run<T>(_ sql: String, _ params: [String] = [],
                        _ map: (OpaquePointer) -> T?) throws -> [T] {
        let db = try connection()
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK,
              let statement else {
            throw RhetoricError.query(String(cString: sqlite3_errmsg(db)))
        }
        defer { sqlite3_finalize(statement) }
        for (i, value) in params.enumerated() {
            sqlite3_bind_text(statement, Int32(i + 1), value, -1, RHETORIC_SQLITE_TRANSIENT)
        }
        var rows: [T] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            if let row = map(statement) { rows.append(row) }
        }
        return rows
    }

    // MARK: - Queries

    /// Sections, in display order, each with its entry count.
    func sections() throws -> [RhetoricSection] {
        try run("""
            SELECT s.id, s.title, COUNT(e.id)
            FROM rhetoric_sections s
            LEFT JOIN rhetoric_entries e ON e.section_id = s.id
            GROUP BY s.id, s.title, s.sort_order
            ORDER BY s.sort_order
        """) { statement in
            guard let id = rhetoricColumnText(statement, 0),
                  let title = rhetoricColumnText(statement, 1) else { return nil }
            return RhetoricSection(id: id, title: title,
                                   entryCount: Int(sqlite3_column_int(statement, 2)))
        }
    }

    /// Entry id + name for one section, alphabetical by name.
    func entries(sectionId: String) throws -> [RhetoricEntryRef] {
        try run("""
            SELECT id, name FROM rhetoric_entries
            WHERE section_id = ? ORDER BY name COLLATE NOCASE
        """, [sectionId]) { statement in
            guard let id = rhetoricColumnText(statement, 0),
                  let name = rhetoricColumnText(statement, 1) else { return nil }
            return RhetoricEntryRef(id: id, name: name)
        }
    }

    /// A single entry, or nil if the id is unknown (defensive guard).
    func entry(id: String) throws -> RhetoricEntry? {
        try run("""
            SELECT id, section_id, name, etymology_greek, etymology, definition, examples
            FROM rhetoric_entries WHERE id = ?
        """, [id]) { statement in
            guard let eid = rhetoricColumnText(statement, 0),
                  let sid = rhetoricColumnText(statement, 1),
                  let name = rhetoricColumnText(statement, 2),
                  let definition = rhetoricColumnText(statement, 5) else { return nil }
            return RhetoricEntry(id: eid, sectionId: sid, name: name,
                                 etymologyGreek: rhetoricColumnText(statement, 3),
                                 etymology: rhetoricColumnText(statement, 4),
                                 definition: definition,
                                 examples: rhetoricColumnText(statement, 6))
        }.first
    }

    /// Cross-references out of an entry, joined to the target name.
    func crossRefs(fromId: String) throws -> [RhetoricCrossRef] {
        try run("""
            SELECT cr.to_id, e.name, cr.kind, cr.note
            FROM rhetoric_cross_refs cr
            JOIN rhetoric_entries e ON e.id = cr.to_id
            WHERE cr.from_id = ?
            ORDER BY cr.kind, e.name COLLATE NOCASE
        """, [fromId]) { statement in
            guard let toId = rhetoricColumnText(statement, 0),
                  let toName = rhetoricColumnText(statement, 1),
                  let kind = rhetoricColumnText(statement, 2) else { return nil }
            return RhetoricCrossRef(toId: toId, toName: toName, kind: kind,
                                    note: rhetoricColumnText(statement, 3))
        }
    }
}
