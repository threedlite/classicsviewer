import SwiftUI

// Matches Android's CustomLanguageConfig data class
struct CustomLanguageConfig: Codable, Identifiable, Equatable {
    let id: String
    let displayName: String
    let color: Int

    // Convert Android color Int to SwiftUI Color
    var swiftUIColor: Color {
        let red = Double((color >> 16) & 0xFF) / 255.0
        let green = Double((color >> 8) & 0xFF) / 255.0
        let blue = Double(color & 0xFF) / 255.0
        return Color(red: red, green: green, blue: blue)
    }

    // Convert SwiftUI Color components to Android color Int
    static func colorToInt(red: Double, green: Double, blue: Double) -> Int {
        let r = Int(red * 255)
        let g = Int(green * 255)
        let b = Int(blue * 255)
        return (0xFF << 24) | (r << 16) | (g << 8) | b
    }
}

// Extension to manage custom languages in UserDefaults (matches Android's PreferencesManager)
extension UserDefaults {
    private static let customLanguagesKey = "customLanguages"
    private static let suppressedLanguagesKey = "suppressedLanguages"
    private static let hasFixedLanguageOrderKey = "hasFixedLanguageOrder"

    var customLanguages: [CustomLanguageConfig] {
        get {
            guard let data = data(forKey: Self.customLanguagesKey),
                  let languages = try? JSONDecoder().decode([CustomLanguageConfig].self, from: data) else {
                return []
            }
            return languages
        }
        set {
            if let data = try? JSONEncoder().encode(newValue) {
                set(data, forKey: Self.customLanguagesKey)
            }
        }
    }

    func addCustomLanguage(_ language: CustomLanguageConfig) {
        var languages = customLanguages

        // Find the position of existing language with same ID (if any)
        if let existingIndex = languages.firstIndex(where: { $0.id == language.id }) {
            // Update in place to preserve order (matches Android behavior)
            languages[existingIndex] = language
            print("Updated existing language at position \(existingIndex)")
        } else {
            // New language - add to end
            languages.append(language)
            print("Added new language at end")
        }

        customLanguages = languages

        // Remove from suppressed list (user is manually adding it back)
        removeSuppressedLanguage(language.id)
    }

    func removeCustomLanguage(withId id: String) {
        var languages = customLanguages
        languages.removeAll { $0.id == id }
        customLanguages = languages

        // Add to suppressed list so it won't be auto-detected again (matches Android)
        addSuppressedLanguage(id)
    }

    // Suppressed languages (explicitly deleted, won't be auto-added) - matches Android
    var suppressedLanguages: Set<String> {
        get {
            guard let array = array(forKey: Self.suppressedLanguagesKey) as? [String] else {
                return []
            }
            return Set(array)
        }
        set {
            set(Array(newValue), forKey: Self.suppressedLanguagesKey)
        }
    }

    func addSuppressedLanguage(_ languageId: String) {
        var suppressed = suppressedLanguages
        suppressed.insert(languageId)
        suppressedLanguages = suppressed
        print("Added \(languageId) to suppressed languages")
    }

    func removeSuppressedLanguage(_ languageId: String) {
        var suppressed = suppressedLanguages
        suppressed.remove(languageId)
        suppressedLanguages = suppressed
        print("Removed \(languageId) from suppressed languages")
    }

    // Language ordering - matches Android
    func reorderLanguagesByPreferredOrder(_ preferredOrder: [String]) {
        var languages = customLanguages

        // Sort by preferred order, with unknown languages at the end
        languages.sort { lang1, lang2 in
            let index1 = preferredOrder.firstIndex(of: lang1.id) ?? Int.max
            let index2 = preferredOrder.firstIndex(of: lang2.id) ?? Int.max
            return index1 < index2
        }

        customLanguages = languages
        print("Reordered languages by preferred order")
    }

    // Migration flag for one-time language order fix - matches Android
    var hasFixedLanguageOrder: Bool {
        get {
            return bool(forKey: Self.hasFixedLanguageOrderKey)
        }
        set {
            set(newValue, forKey: Self.hasFixedLanguageOrderKey)
        }
    }
}