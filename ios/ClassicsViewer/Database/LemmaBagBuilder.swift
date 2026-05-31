import Foundation

/// Swift port of build_topical_pack.py's interlinear parsers. Used at runtime
/// to construct the TF-IDF query vector from the source passage's interlinear
/// text, so it must match the Python parsers token-for-token.
enum LemmaBagBuilder {

    static func forLanguage(_ language: String) -> (String) -> [String] {
        switch language.lowercased() {
        case "greek": return parseGreek
        case "latin": return parseLatin
        default: return { _ in [] }
        }
    }

    static func translatorFor(_ language: String) -> String? {
        switch language.lowercased() {
        case "greek": return "Interlinear (Beta, generated from app dictionary and treebank)"
        // Post LATIN_POS_PLAN.md Latin uses the same string as Greek — the
        // formats are now identical.
        case "latin": return "Interlinear (Beta, generated from app dictionary and treebank)"
        default: return nil
        }
    }

    /// Whether a `translation_segments.translator` value is one of our
    /// app-generated interlinear translators (any language, any version).
    /// Used to exclude interlinear rows from the English-translation slot
    /// in topical-links results — matches all current names and the
    /// legacy Latin "...AI-generated from app dictionary" still present
    /// in unrebuilt on-device DBs.
    static func isInterlinearTranslator(_ translator: String?) -> Bool {
        translator?.hasPrefix("Interlinear (Beta") == true
    }

    private static let CONTENT_POS: Set<String> = ["NOUN", "PROPN", "VERB", "ADJ"]

    private static let LIGHT_LEMMATA_GREEK: Set<String> = Set([
        "εἰμί", "ἔχω", "γίγνομαι", "λέγω", "ποιέω", "ὁράω", "ἔρχομαι",
        "φημί", "οἶδα", "βούλομαι", "δοκέω", "δίδωμι", "λαμβάνω",
        "δύναμαι", "γιγνώσκω", "θέλω", "ἀκούω", "ζάω", "πάσχω",
        "καλέω", "τίθημι", "ἵστημι", "ἡγέομαι", "νομίζω",
    ].map { $0.precomposedStringWithCanonicalMapping })

    private static let LIGHT_LEMMATA_LATIN: Set<String> = [
        "sum", "habeo", "facio", "dico", "video", "do", "duco", "ago",
        "venio", "eo", "puto", "scio", "volo", "possum", "debeo",
        "oporteo", "necesse", "res", "homo", "vir", "pars", "modo",
    ]

    static func parseGreek(_ text: String) -> [String] {
        var out: [String] = []
        for part in text.split(separator: "|", omittingEmptySubsequences: false) {
            guard let tildeIdx = part.firstIndex(of: "~") else { continue }
            let left = String(part[..<tildeIdx])
            var right = String(part[part.index(after: tildeIdx)...])
            if right.hasPrefix("*") { right.removeFirst() }
            let lt = left.split(whereSeparator: { $0.isWhitespace })
                .map(String.init).filter { !$0.isEmpty }
            let rt = right.split(whereSeparator: { $0.isWhitespace })
                .map(String.init).filter { !$0.isEmpty }
            guard !lt.isEmpty, !rt.isEmpty, CONTENT_POS.contains(rt[0]) else { continue }
            let lem = lt[0].precomposedStringWithCanonicalMapping
            if lem.isEmpty || lem == "?" || lem == "???" || lem == "-" { continue }
            if LIGHT_LEMMATA_GREEK.contains(lem) { continue }
            out.append(lem)
        }
        return out
    }

    static func parseLatin(_ text: String) -> [String] {
        // Post LATIN_POS_PLAN.md: Latin interlinear uses the same Greek-shaped
        // POS-bearing format. Each token's data block is:
        //   LEMMA MORPH ~  POS DEPREL HEAD sent_pos sent_id   (Stanza)
        //   LEMMA MORPH ~* POS DEPREL HEAD sent_pos sent_id   (LDT)
        // Identical structure to parseGreek; only the stoplist differs.
        var out: [String] = []
        for part in text.split(separator: "|", omittingEmptySubsequences: false) {
            guard let tildeIdx = part.firstIndex(of: "~") else { continue }
            let left = String(part[..<tildeIdx])
            var right = String(part[part.index(after: tildeIdx)...])
            if right.hasPrefix("*") { right.removeFirst() }
            let lt = left.split(whereSeparator: { $0.isWhitespace })
                .map(String.init).filter { !$0.isEmpty }
            let rt = right.split(whereSeparator: { $0.isWhitespace })
                .map(String.init).filter { !$0.isEmpty }
            guard !lt.isEmpty, !rt.isEmpty, CONTENT_POS.contains(rt[0]) else { continue }
            var lem = lt[0].precomposedStringWithCanonicalMapping.lowercased()
            if lem.isEmpty || lem == "?" || lem == "???" || lem == "-" { continue }
            if LIGHT_LEMMATA_LATIN.contains(lem) { continue }
            // Trim trailing punctuation Stanza occasionally glues on.
            while let last = lem.last, ".,;:!?".contains(last) {
                lem.removeLast()
            }
            if lem.count >= 2 && lem.allSatisfy({ $0.isLetter }) {
                out.append(lem)
            }
        }
        return out
    }
}
