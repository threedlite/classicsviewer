import Foundation
import SQLite3

/// Data structure matching the prefix_assimilation_rules table schema
/// Schema defined in: data-prep/build_modules/load_combined_dictionaries.py:191-201
struct PrefixAssimilationRule {
    let id: Int
    let language: String           // NOT NULL
    let basePrefix: String         // NOT NULL
    let assimilatedForm: String    // NOT NULL
    let meaning: String?           // NULLABLE
    let phonologicalRule: String?  // NULLABLE
    let priority: Int              // NOT NULL
    let examples: String?          // NULLABLE
}

/// Grouped prefix structure for algorithm use
/// Contains a base prefix with all its assimilated forms
struct PrefixGroup {
    let basePrefix: String
    let meaning: String
    let assimilatedForms: [String]  // Sorted by priority (ascending)
}

/// DAO for reading prefix assimilation rules from the Perseus database
/// Used for compound word decomposition (e.g., κατορθόω → κατα + ορθόω)
/// Matches Android PerseusRepository.kt lines 53-88
actor PrefixAssimilationRuleDAO {

    // MARK: - Cache

    /// Thread-safe cache of loaded prefix rules by language
    private var ruleCache: [String: [PrefixGroup]] = [:]

    // MARK: - Public Methods

    /// Get prefix assimilation rules grouped by base prefix for a language
    /// Caches results to avoid repeated database queries
    /// - Parameter language: "greek" or "latin"
    /// - Returns: Array of PrefixGroups sorted by base prefix length (longest first)
    func getPrefixAssimilationRules(language: String) async throws -> [PrefixGroup] {
        // Check cache first (actor provides automatic synchronization)
        if let cached = ruleCache[language] {
            return cached
        }

        // Query database - EXACT column names from schema
        let query = """
            SELECT base_prefix, assimilated_form, meaning, priority
            FROM prefix_assimilation_rules
            WHERE language = ?
            ORDER BY base_prefix, priority ASC
        """

        var rules: [PrefixAssimilationRule] = []
        rules = try await DatabaseManagerAsync.shared.executeQuery(
            query,
            parameters: [language]
        ) { statement in
            // Column 0: base_prefix (TEXT NOT NULL)
            guard let basePrefixCString = sqlite3_column_text(statement, 0) else {
                return nil
            }
            let basePrefix = String(cString: basePrefixCString)

            // Column 1: assimilated_form (TEXT NOT NULL)
            guard let assimilatedFormCString = sqlite3_column_text(statement, 1) else {
                return nil
            }
            let assimilatedForm = String(cString: assimilatedFormCString)

            // Column 2: meaning (TEXT NULLABLE)
            var meaning: String? = nil
            if let meaningCString = sqlite3_column_text(statement, 2) {
                meaning = String(cString: meaningCString)
            }

            // Column 3: priority (INTEGER NOT NULL)
            let priority = Int(sqlite3_column_int(statement, 3))

            return PrefixAssimilationRule(
                id: 0,  // Not needed for algorithm
                language: language,
                basePrefix: basePrefix,
                assimilatedForm: assimilatedForm,
                meaning: meaning,
                phonologicalRule: nil,  // Not queried for performance
                priority: priority,
                examples: nil  // Not queried for performance
            )
        }

        // Group by base prefix
        var grouped: [String: (meaning: String?, forms: [(form: String, priority: Int)])] = [:]
        for rule in rules {
            if grouped[rule.basePrefix] == nil {
                grouped[rule.basePrefix] = (meaning: rule.meaning, forms: [])
            }
            grouped[rule.basePrefix]?.forms.append((form: rule.assimilatedForm, priority: rule.priority))
        }

        // Convert to PrefixGroups
        var groups: [PrefixGroup] = []
        for (basePrefix, data) in grouped {
            // Sort forms by priority (ascending - lower priority number = higher precedence)
            let sortedForms = data.forms.sorted { $0.priority < $1.priority }.map { $0.form }

            groups.append(PrefixGroup(
                basePrefix: basePrefix,
                meaning: data.meaning ?? "",
                assimilatedForms: sortedForms
            ))
        }

        // Sort by base prefix length (longest first) for greedy matching
        groups.sort { $0.basePrefix.count > $1.basePrefix.count }

        // Cache results (actor provides automatic synchronization)
        ruleCache[language] = groups

        return groups
    }

    /// Check if prefix assimilation rules exist for a language
    /// - Parameter language: "greek" or "latin"
    /// - Returns: True if at least one rule exists
    func hasRules(for language: String) async throws -> Bool {
        let query = """
            SELECT COUNT(*) FROM prefix_assimilation_rules WHERE language = ?
        """

        let counts = try await DatabaseManagerAsync.shared.executeQuery(query, parameters: [language]) { statement in
            Int(sqlite3_column_int(statement, 0))
        }

        return (counts.first ?? 0) > 0
    }

    /// Clear cache (useful for testing or memory management)
    func clearCache() {
        ruleCache.removeAll()
    }

    /// Get all available languages that have prefix rules
    /// - Returns: Array of language codes
    func getAvailableLanguages() async throws -> [String] {
        let query = """
            SELECT DISTINCT language FROM prefix_assimilation_rules ORDER BY language
        """

        return try await DatabaseManagerAsync.shared.executeQuery(query, parameters: []) { statement in
            guard let languageCString = sqlite3_column_text(statement, 0) else {
                return nil
            }
            return String(cString: languageCString)
        }
    }
}
