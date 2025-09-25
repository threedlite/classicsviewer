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
        // Remove any existing language with the same ID
        languages.removeAll { $0.id == language.id }
        // Add the new/updated language
        languages.append(language)
        customLanguages = languages
    }

    func removeCustomLanguage(withId id: String) {
        var languages = customLanguages
        languages.removeAll { $0.id == id }
        customLanguages = languages
    }
}